"""Local-first central API. SQLite demo; PostgreSQL via DATABASE_URL."""
import csv
import hashlib
import hmac
import io
import json
import os
import socket
import threading
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException
from fastapi.responses import FileResponse, Response
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import create_engine, event, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from starlette.middleware.trustedhost import TrustedHostMiddleware

from . import __version__
from .models import Assessment, Base, Endpoint, Event, Job, now
from .schemas import DemoSeed, EndpointInput, EvidenceInput, JobInput, LocalScanInput
from core.scoring import calculate_score
from .scanner_bridge import collect_local_evidence

ASSETS = Path(__file__).parent / "static"
DEMO_CHECKS = [
    ("WIN-FW-001", "Windows firewall", "High"),
    ("WIN-BL-001", "Disk encryption", "High"),
    ("WIN-SMB1-001", "SMBv1 disabled", "High"),
    ("WIN-AV-001", "Antivirus protection", "High"),
    ("WIN-GUEST-001", "Guest account disabled", "Medium"),
    ("WIN-UPDATE-001", "Security update posture", "Medium"),
]


def metrics(passed, failed, errors):
    summary = calculate_score([{"status": "Pass"}] * passed + [{"status": "Fail"}] * failed + [{"status": "Error"}] * errors)
    assessed = passed + failed
    return {"passed": passed, "failed": failed, "errors": errors,
            "score": summary["compliance_score"], "coverage": summary["coverage_percentage"],
            "risk": round(100 * failed / assessed, 2) if assessed else None}


def assessment_dict(row, include_checks=False):
    result = {"id": row.id, "endpoint_id": row.endpoint_id,
              "submission_id": row.submission_id, "collected_at": row.collected_at,
              "received_at": row.received_at, "sha256": row.sha256,
              "source": row.source,
              **metrics(row.passed, row.failed, row.errors)}
    if include_checks:
        result["checks"] = json.loads(row.evidence_json)["checks"]
    return result


def record_evidence(session, endpoint, payload, source="imported"):
    canonical = json.dumps(payload.model_dump(mode="json"), sort_keys=True,
                           separators=(",", ":"), ensure_ascii=False)
    digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    existing = session.scalar(select(Assessment).where(Assessment.submission_id == payload.submission_id))
    if existing:
        if existing.endpoint_id != endpoint.id or existing.sha256 != digest:
            raise HTTPException(409, "Submission ID already has different evidence")
        return existing, False
    counts = {status: sum(c.status == status for c in payload.checks) for status in ("Pass", "Fail", "Error")}
    assessment = Assessment(endpoint_id=endpoint.id, submission_id=payload.submission_id,
                            collected_at=payload.collected_at.isoformat(), evidence_json=canonical,
                            sha256=digest, passed=counts["Pass"], failed=counts["Fail"], errors=counts["Error"])
    assessment.source = source
    endpoint.last_seen = now()
    session.add(assessment)
    session.flush()
    session.add(Event(action="evidence.received", detail=f"{endpoint.hostname}: {assessment.id}"))
    return assessment, True


def demo_payload(endpoint, job_id):
    # Synthetic fixtures are intentionally stable across repeated scans.
    checks = []
    for check_id, title, severity in DEMO_CHECKS:
        value = int(hashlib.sha256(f"{endpoint.hostname}:{check_id}".encode()).hexdigest()[:8], 16) % 20
        status = "Error" if value == 0 else "Fail" if value < 6 else "Pass"
        checks.append({"check_id": check_id, "title": title, "severity": severity,
                       "status": status, "detail": f"SIMULATED evidence: {title} fixture is {status}. No device was scanned."})
    return EvidenceInput(submission_id=f"demo-{job_id}", collected_at=datetime.now(timezone.utc), checks=checks)


class BodyLimitMiddleware:
    def __init__(self, app, maximum=2_000_000):
        self.app, self.maximum = app, maximum

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http" or scope["method"] not in ("POST", "PUT", "PATCH"):
            return await self.app(scope, receive, send)
        messages, length = [], 0
        while True:
            message = await receive()
            if message["type"] == "http.disconnect":
                return
            length += len(message.get("body", b""))
            if length > self.maximum:
                response = Response('{"detail":"Request too large"}', status_code=413, media_type="application/json")
                return await response(scope, receive, send)
            messages.append(message)
            if not message.get("more_body", False):
                break
        async def replay():
            if messages:
                return messages.pop(0)
            return await receive()
        await self.app(scope, replay, send)


def create_app(database_url, api_token, *, worker_enabled=True):
    if len(api_token) < 32:
        raise ValueError("API token must contain at least 32 characters")
    options = {"connect_args": {"check_same_thread": False, "timeout": 30}} if database_url.startswith("sqlite") else {}
    engine = create_engine(database_url, pool_pre_ping=True, **options)
    if database_url.startswith("sqlite"):
        @event.listens_for(engine, "connect")
        def sqlite_setup(connection, _):
            connection.execute("PRAGMA foreign_keys=ON")
            connection.execute("PRAGMA journal_mode=WAL")
    stop = threading.Event()

    def process_demo_jobs():
        while not stop.wait(0.5):
            try:
                with Session(engine) as session:
                    jobs = session.scalars(select(Job).join(Endpoint).where(
                        Job.status == "queued", Job.due_at <= now()
                    ).order_by(Job.created_at, Job.id).limit(5)).all()
                    for job in jobs:
                        job.status = "running"
                    session.commit()
                    ids = [job.id for job in jobs]
                for job_id in ids:
                    if stop.is_set():
                        break
                    with Session(engine) as session:
                        job = session.get(Job, job_id)
                        endpoint = session.get(Endpoint, job.endpoint_id)
                        try:
                            if job.kind == "local":
                                if endpoint.hostname != socket.gethostname() or endpoint.simulated:
                                    raise ValueError("Local scan identity mismatch")
                                payload = collect_local_evidence(f"local-{job.id}")
                                source = "local-scanner"
                            else:
                                if not endpoint.simulated:
                                    raise ValueError("Demo job requires a simulated endpoint")
                                payload, source = demo_payload(endpoint, job.id), "simulated"
                            assessment, _ = record_evidence(session, endpoint, payload, source)
                            job.status, job.completed_at, job.assessment_id = "completed", now(), assessment.id
                            session.commit()
                        except Exception as exc:
                            session.rollback()
                            job = session.get(Job, job_id)
                            job.status, job.completed_at = "failed", now()
                            session.add(Event(action="job.failed", detail=f"{job.id}: {type(exc).__name__}; no valid evidence stored"))
                            session.commit()
            except Exception:
                # Preserve queued work; do not crash the desktop process on an unavailable DB.
                import logging
                logging.getLogger("secureaudit").exception("Demo worker failed")
                stop.wait(2)

    @asynccontextmanager
    async def lifespan(app):
        Base.metadata.create_all(engine)
        with Session(engine) as session:
            session.execute(update(Job).where(Job.status == "running").values(status="queued"))
            session.commit()
        thread = threading.Thread(target=process_demo_jobs, daemon=True, name="SecureAuditDemoWorker")
        if worker_enabled:
            thread.start()
        yield
        stop.set()
        if worker_enabled:
            thread.join(timeout=5)
        engine.dispose()

    app = FastAPI(title="SecureAudit Central", version=__version__, lifespan=lifespan)
    app.state.engine = engine
    app.add_middleware(BodyLimitMiddleware)
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=["localhost", "127.0.0.1", "[::1]", "testserver"])
    bearer = HTTPBearer(auto_error=False)

    def authorized(credentials: HTTPAuthorizationCredentials | None = Depends(bearer)):
        if credentials is None or not hmac.compare_digest(credentials.credentials.encode(), api_token.encode()):
            raise HTTPException(401, "Valid API access key required", headers={"WWW-Authenticate": "Bearer"})

    def db():
        with Session(engine) as session:
            yield session

    @app.middleware("http")
    async def secure_headers(request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Cache-Control"] = "no-store"
        response.headers["X-Frame-Options"] = "DENY"
        if request.url.path in ("/", "/app.js", "/style.css"):
            response.headers["Content-Security-Policy"] = "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'"
        return response

    @app.get("/", include_in_schema=False)
    def dashboard_page():
        return FileResponse(ASSETS / "index.html")

    @app.get("/app.js", include_in_schema=False)
    def dashboard_js():
        return FileResponse(ASSETS / "app.js", media_type="application/javascript")

    @app.get("/style.css", include_in_schema=False)
    def dashboard_css():
        return FileResponse(ASSETS / "style.css", media_type="text/css")

    @app.get("/health")
    def health(session: Session = Depends(db)):
        session.execute(select(1))
        return {"status": "ok", "version": __version__, "database": engine.dialect.name,
                "mode": "local-central", "scanner_connected": True}

    protected = [Depends(authorized)]

    def endpoint_rows(session):
        endpoints = session.scalars(select(Endpoint).order_by(Endpoint.hostname)).all()
        assessments = session.scalars(select(Assessment).order_by(Assessment.collected_at.desc(), Assessment.received_at.desc())).all()
        latest = {}
        for assessment in assessments:
            latest.setdefault(assessment.endpoint_id, assessment)
        return [{"id": e.id, "hostname": e.hostname, "group_name": e.group_name,
                 "platform": e.platform, "simulated": e.simulated, "last_seen": e.last_seen,
                 "registered_at": e.registered_at,
                 "latest": assessment_dict(latest[e.id]) if e.id in latest else None} for e in endpoints]

    @app.get("/api/endpoints", dependencies=protected)
    def list_endpoints(session: Session = Depends(db)):
        return endpoint_rows(session)

    @app.post("/api/endpoints", dependencies=protected, status_code=201)
    def register(payload: EndpointInput, session: Session = Depends(db)):
        endpoint = Endpoint(**payload.model_dump())
        session.add(endpoint)
        try:
            session.flush()
            session.add(Event(action="endpoint.registered", detail=endpoint.hostname))
            session.commit()
        except IntegrityError:
            session.rollback()
            raise HTTPException(409, "Hostname already registered")
        return {"id": endpoint.id, "hostname": endpoint.hostname, "simulated": endpoint.simulated}

    @app.post("/api/endpoints/{endpoint_id}/evidence", dependencies=protected)
    def submit(endpoint_id: str, payload: EvidenceInput, session: Session = Depends(db)):
        endpoint = session.get(Endpoint, endpoint_id)
        if endpoint is None:
            raise HTTPException(404, "Endpoint not found")
        try:
            assessment, created = record_evidence(session, endpoint, payload)
            session.commit()
        except IntegrityError:
            session.rollback()
            raise HTTPException(409, "Concurrent submission conflict; retry the same submission")
        return {"created": created, **assessment_dict(assessment, True)}

    @app.get("/api/endpoints/{endpoint_id}/history", dependencies=protected)
    def history(endpoint_id: str, session: Session = Depends(db)):
        if session.get(Endpoint, endpoint_id) is None:
            raise HTTPException(404, "Endpoint not found")
        return [assessment_dict(a, True) for a in session.scalars(select(Assessment).where(
            Assessment.endpoint_id == endpoint_id).order_by(Assessment.collected_at.desc(), Assessment.received_at.desc()).limit(100))]

    @app.post("/api/demo/seed", dependencies=protected)
    def seed(payload: DemoSeed, session: Session = Depends(db)):
        created = 0
        groups = ["Engineering", "Finance", "Operations", "IT"]
        for index in range(1, payload.count + 1):
            hostname = f"DEMO-PC-{index:03}"
            if session.scalar(select(Endpoint).where(Endpoint.hostname == hostname)) is None:
                session.add(Endpoint(hostname=hostname, group_name=groups[(index-1) % 4], simulated=True))
                created += 1
        session.add(Event(action="demo.seeded", detail=f"{created} simulated endpoints created; no physical devices scanned"))
        session.commit()
        return {"created": created, "simulated": True}

    @app.post("/api/demo/jobs", dependencies=protected, status_code=201)
    def queue(payload: JobInput, session: Session = Depends(db)):
        endpoints = session.scalars(select(Endpoint).where(Endpoint.id.in_(payload.endpoint_ids))).all()
        if len(endpoints) != len(payload.endpoint_ids):
            raise HTTPException(404, "One or more endpoints do not exist")
        if any(not e.simulated for e in endpoints):
            raise HTTPException(409, "Demo jobs can run only on simulated endpoints; real agent execution is not connected")
        due = (datetime.now(timezone.utc) + timedelta(seconds=payload.delay_seconds)).isoformat()
        jobs = []
        for endpoint in endpoints:
            jobs.append(Job(endpoint_id=endpoint.id, due_at=due))
        session.add_all(jobs)
        session.add(Event(action="demo.jobs.queued", detail=f"{len(jobs)} synthetic assessments scheduled for {due}"))
        session.commit()
        return {"job_ids": [j.id for j in jobs], "due_at": due, "count": len(jobs)}

    @app.post("/api/local/scan", dependencies=protected, status_code=201)
    def local_scan(payload: LocalScanInput, session: Session = Depends(db)):
        if os.name != "nt":
            raise HTTPException(409, "Local scanner requires Windows")
        if session.scalar(select(Job).where(Job.kind == "local", Job.status.in_(["queued", "running"]))) is not None:
            raise HTTPException(409, "A local scan is already queued or running")
        hostname = socket.gethostname()
        endpoint = session.scalar(select(Endpoint).where(Endpoint.hostname == hostname))
        if endpoint and endpoint.simulated:
            raise HTTPException(409, "This computer's hostname is reserved by a simulated endpoint")
        if endpoint is None:
            endpoint = Endpoint(hostname=hostname, group_name="This computer", platform="Windows", simulated=False)
            session.add(endpoint)
            session.flush()
        job = Job(endpoint_id=endpoint.id, kind="local", due_at=now())
        session.add(job)
        session.add(Event(action="local.scan.queued", detail=f"{hostname}: existing allow-listed Windows scanner"))
        session.commit()
        return {"job_id": job.id, "endpoint_id": endpoint.id, "hostname": hostname,
                "notice": "Checks requiring Administrator may return Error when the app is not elevated"}

    @app.get("/api/jobs", dependencies=protected)
    def list_jobs(session: Session = Depends(db)):
        return [{"id": j.id, "endpoint_id": j.endpoint_id, "status": j.status,
                 "kind": j.kind,
                 "created_at": j.created_at, "due_at": j.due_at, "completed_at": j.completed_at,
                 "assessment_id": j.assessment_id} for j in session.scalars(select(Job).order_by(Job.created_at.desc(), Job.id).limit(2000))]

    @app.get("/api/summary", dependencies=protected)
    def summary(session: Session = Depends(db)):
        rows = endpoint_rows(session)
        latest = [e["latest"] for e in rows if e["latest"]]
        p, f, er = (sum(a[key] for a in latest) for key in ("passed", "failed", "errors"))
        return {"endpoint_count": len(rows), "simulated_count": sum(e["simulated"] for e in rows),
                "assessed_endpoints": len(latest), "at_risk_endpoints": sum(a["failed"] > 0 for a in latest),
                "database": engine.dialect.name, **metrics(p, f, er)}

    @app.get("/api/events", dependencies=protected)
    def events(session: Session = Depends(db)):
        return [{"id": e.id, "at": e.at, "action": e.action, "detail": e.detail} for e in session.scalars(
            select(Event).order_by(Event.at.desc(), Event.id).limit(100))]

    @app.get("/api/export", dependencies=protected)
    def export(session: Session = Depends(db)):
        return {"product": "SecureAudit Central", "version": __version__, "exported_at": now(),
                "notice": "Simulated endpoints are synthetic fixtures. Imported evidence is not independently verified.",
                "endpoints": endpoint_rows(session),
                "assessments": [assessment_dict(a, True) for a in session.scalars(select(Assessment).order_by(Assessment.received_at))]}

    @app.get("/api/export.csv", dependencies=protected)
    def export_csv(session: Session = Depends(db)):
        buffer = io.StringIO(newline="")
        writer = csv.writer(buffer)
        writer.writerow(["Hostname", "Group", "Simulated", "Score", "Coverage", "Pass", "Fail", "Error", "Collected UTC"])
        def safe(value):
            text = str(value)
            return "'" + text if text.startswith(("=", "+", "-", "@", "\t", "\r", "\n")) else text
        for row in endpoint_rows(session):
            latest = row["latest"] or {}
            writer.writerow([safe(row["hostname"]), safe(row["group_name"]), row["simulated"],
                             *[latest.get(k, "") for k in ("score", "coverage", "passed", "failed", "errors", "collected_at")]])
        return Response(buffer.getvalue(), media_type="text/csv", headers={"Content-Disposition": 'attachment; filename="SecureAudit-summary.csv"'})

    return app
