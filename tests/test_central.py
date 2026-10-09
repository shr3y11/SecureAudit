"""Regression tests at the central trust boundary and persistence layer."""
import copy
import hashlib
import json
import time
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from secureaudit_central.api import create_app
from secureaudit_central.models import Assessment, Job
from secureaudit_central.scanner_bridge import collect_local_evidence

TOKEN = "test-key-" + "a" * 56
HEADERS = {"Authorization": "Bearer " + TOKEN}


@pytest.fixture
def client(tmp_path):
    app = create_app("sqlite:///" + (tmp_path / "central.db").as_posix(), TOKEN, worker_enabled=False)
    with TestClient(app) as c:
        c.headers.update(HEADERS)
        yield c


@pytest.fixture
def endpoint(client):
    response = client.post("/api/endpoints", json={"hostname": "TEST-PC-01", "group_name": "Test"})
    assert response.status_code == 201
    return response.json()["id"]


def payload(statuses=("Pass", "Fail", "Error")):
    return {"submission_id": "submission-001", "collected_at": datetime.now(timezone.utc).isoformat(),
            "checks": [{"check_id": f"WIN-TEST-{i}", "title": f"Control {i}", "status": status,
                        "detail": "Test evidence", "severity": "High"} for i, status in enumerate(statuses)]}


@pytest.mark.parametrize("path", ["/api/summary", "/api/endpoints", "/api/jobs", "/api/events", "/api/export", "/api/export.csv"])
def test_evidence_routes_require_key(client, path):
    client.headers.pop("Authorization")
    assert client.get(path).status_code == 401


@pytest.mark.parametrize("path,body", [("/api/endpoints", {"hostname": "X"}), ("/api/demo/seed", {"count": 1}), ("/api/demo/jobs", {"endpoint_ids": ["x"]}), ("/api/local/scan", {})])
def test_mutations_require_key(client, path, body):
    client.headers["Authorization"] = "Bearer wrong-key"
    assert client.post(path, json=body).status_code == 401


def test_short_key_rejected(tmp_path):
    with pytest.raises(ValueError):
        create_app("sqlite:///" + (tmp_path / "db").as_posix(), "short")


def test_registration_duplicate_and_unknown_fields(client, endpoint):
    assert client.post("/api/endpoints", json={"hostname": "TEST-PC-01"}).status_code == 409
    assert client.post("/api/endpoints", json={"hostname": "PC", "simulated": True}).status_code == 422
    assert client.post("/api/endpoints", json={"hostname": "<script>alert(1)</script>"}).status_code == 422


def test_mixed_results_reuse_scoring_and_keep_errors_separate(client, endpoint):
    response = client.post(f"/api/endpoints/{endpoint}/evidence", json=payload())
    assert response.status_code == 200
    result = response.json()
    assert result["score"] == 50
    assert result["coverage"] == 66.67
    assert (result["passed"], result["failed"], result["errors"]) == (1, 1, 1)
    assert result["source"] == "imported"
    assert client.get("/api/summary").json()["at_risk_endpoints"] == 1


def test_all_errors_do_not_produce_a_false_compliance_score(client, endpoint):
    result = client.post(f"/api/endpoints/{endpoint}/evidence", json=payload(["Error", "Error"])).json()
    assert result["score"] is None and result["risk"] is None and result["coverage"] == 0


def test_hash_matches_canonical_stored_evidence(client, endpoint):
    result = client.post(f"/api/endpoints/{endpoint}/evidence", json=payload()).json()
    with Session(client.app.state.engine) as session:
        row = session.get(Assessment, result["id"])
        assert hashlib.sha256(row.evidence_json.encode()).hexdigest() == result["sha256"]


def test_retries_are_idempotent_and_changed_retries_conflict(client, endpoint):
    evidence = payload()
    first = client.post(f"/api/endpoints/{endpoint}/evidence", json=evidence).json()
    repeated = client.post(f"/api/endpoints/{endpoint}/evidence", json=evidence).json()
    assert first["created"] and not repeated["created"] and first["id"] == repeated["id"]
    evidence["checks"][0]["status"] = "Fail"
    assert client.post(f"/api/endpoints/{endpoint}/evidence", json=evidence).status_code == 409
    assert len(client.get(f"/api/endpoints/{endpoint}/history").json()) == 1


def test_submission_id_cannot_be_reused_for_a_different_endpoint(client, endpoint):
    evidence = payload()
    client.post(f"/api/endpoints/{endpoint}/evidence", json=evidence)
    other = client.post("/api/endpoints", json={"hostname": "OTHER"}).json()["id"]
    assert client.post(f"/api/endpoints/{other}/evidence", json=evidence).status_code == 409


@pytest.mark.parametrize("invalid", ["status", "duplicates", "unknown", "empty", "naive", "future", "scanner-mismatch"])
def test_invalid_evidence_is_rejected_without_storage(client, endpoint, invalid):
    evidence = payload()
    if invalid == "status": evidence["checks"][0]["status"] = "Compliant"
    if invalid == "duplicates": evidence["checks"][1]["check_id"] = evidence["checks"][0]["check_id"]
    if invalid == "unknown": evidence["command"] = "arbitrary PowerShell"
    if invalid == "empty": evidence["checks"] = []
    if invalid == "naive": evidence["collected_at"] = "2026-01-01T00:00:00"
    if invalid == "future": evidence["collected_at"] = (datetime.now(timezone.utc) + timedelta(days=1)).isoformat()
    if invalid == "scanner-mismatch": evidence["checks"][0]["scanner_result"] = {"check_id": "OTHER", "status": "Pass"}
    assert client.post(f"/api/endpoints/{endpoint}/evidence", json=evidence).status_code == 422
    assert client.get(f"/api/endpoints/{endpoint}/history").json() == []


def test_unknown_endpoint_returns_404(client):
    assert client.post("/api/endpoints/missing/evidence", json=payload()).status_code == 404
    assert client.get("/api/endpoints/missing/history").status_code == 404


def test_old_import_does_not_replace_newer_collected_posture(client, endpoint):
    recent = payload(["Pass"])
    client.post(f"/api/endpoints/{endpoint}/evidence", json=recent)
    older = payload(["Fail"])
    older["submission_id"] = "older"
    older["collected_at"] = "2025-01-01T00:00:00Z"
    client.post(f"/api/endpoints/{endpoint}/evidence", json=older)
    assert client.get("/api/summary").json()["score"] == 100


def test_demo_seed_is_idempotent_and_bounded(client):
    assert client.post("/api/demo/seed", json={"count": 100}).json()["created"] == 100
    assert client.post("/api/demo/seed", json={"count": 100}).json()["created"] == 0
    assert client.post("/api/demo/seed", json={"count": 501}).status_code == 422
    assert all(e["simulated"] for e in client.get("/api/endpoints").json())


def test_demo_jobs_cannot_target_real_endpoints_or_unknown_ids(client, endpoint):
    assert client.post("/api/demo/jobs", json={"endpoint_ids": [endpoint]}).status_code == 409
    assert client.post("/api/demo/jobs", json={"endpoint_ids": ["missing"]}).status_code == 404
    assert client.post("/api/demo/jobs", json={"endpoint_ids": [endpoint, endpoint]}).status_code == 422
    assert client.get("/api/jobs").json() == []


def test_body_limit_applies_without_trusting_content_length(client, endpoint):
    response = client.post(f"/api/endpoints/{endpoint}/evidence", content=b"x" * 2_000_001)
    assert response.status_code == 413


def test_host_boundary_and_security_headers(client):
    assert client.get("/", headers={"Host": "attacker.example"}).status_code == 400
    response = client.get("/")
    assert response.status_code == 200
    assert response.headers["X-Frame-Options"] == "DENY"
    assert "frame-ancestors 'none'" in response.headers["Content-Security-Policy"]
    assert response.headers["Cache-Control"] == "no-store"


def test_csv_neutralizes_spreadsheet_formulas(client):
    client.post("/api/endpoints", json={"hostname": "SAFE-PC", "group_name": "=HYPERLINK(\"bad\")"})
    assert "'=HYPERLINK" in client.get("/api/export.csv").text


def test_scanner_bridge_preserves_original_result_and_approved_ids():
    catalog = {"checks": [{"id": "WIN-FW-001", "enabled": True, "severity": "High"},
                           {"id": "DISABLED", "enabled": False}]}
    raw = {"check_id": "WIN-FW-001", "check_name": "Firewall", "expected_value": "Enabled",
           "observed_value": "Enabled", "status": "Pass", "evidence": [{"Profile": "Domain"}],
           "error_message": None, "timestamp_utc": datetime.now(timezone.utc).isoformat()}
    with patch("secureaudit_central.scanner_bridge.load_catalog", return_value=catalog), patch(
        "secureaudit_central.scanner_bridge.run_check", return_value=raw) as run:
        result = collect_local_evidence("test-scan")
    run.assert_called_once_with("WIN-FW-001")
    assert result.checks[0].scanner_result == raw


def test_local_scan_accepts_no_arbitrary_command_and_prevents_duplicate_queue(client):
    assert client.post("/api/local/scan", json={"command": "whoami"}).status_code == 422
    first = client.post("/api/local/scan", json={}).json()
    assert "job_id" in first
    assert client.post("/api/local/scan", json={}).status_code == 409
    assert client.get("/api/jobs").json()[0]["kind"] == "local"


def test_demo_jobs_and_evidence_survive_restart(tmp_path):
    url = "sqlite:///" + (tmp_path / "persistent.db").as_posix()
    with TestClient(create_app(url, TOKEN, worker_enabled=False)) as c:
        c.headers.update(HEADERS)
        c.post("/api/demo/seed", json={"count": 8})
        ids = [e["id"] for e in c.get("/api/endpoints").json()]
        queued = c.post("/api/demo/jobs", json={"endpoint_ids": ids}).json()
        assert queued["count"] == 8
    with TestClient(create_app(url, TOKEN)) as c:
        c.headers.update(HEADERS)
        deadline = time.monotonic() + 12
        while time.monotonic() < deadline:
            jobs = c.get("/api/jobs").json()
            if all(j["status"] == "completed" for j in jobs): break
            time.sleep(.1)
        assert all(j["status"] == "completed" for j in jobs)
        assert c.get("/api/summary").json()["assessed_endpoints"] == 8
        assert all(a["source"] == "simulated" for a in c.get("/api/export").json()["assessments"])
    with TestClient(create_app(url, TOKEN, worker_enabled=False)) as c:
        c.headers.update(HEADERS)
        assert c.get("/api/summary").json()["assessed_endpoints"] == 8


def test_future_scheduled_jobs_wait(tmp_path):
    app = create_app("sqlite:///" + (tmp_path / "scheduled.db").as_posix(), TOKEN)
    with TestClient(app) as c:
        c.headers.update(HEADERS)
        c.post("/api/demo/seed", json={"count": 1})
        ids = [e["id"] for e in c.get("/api/endpoints").json()]
        c.post("/api/demo/jobs", json={"endpoint_ids": ids, "delay_seconds": 60})
        time.sleep(.7)
        assert c.get("/api/jobs").json()[0]["status"] == "queued"
        assert c.get("/api/summary").json()["assessed_endpoints"] == 0


def test_failed_scanner_creates_failed_job_not_false_evidence(tmp_path):
    app = create_app("sqlite:///" + (tmp_path / "failed.db").as_posix(), TOKEN)
    with patch("secureaudit_central.api.collect_local_evidence", side_effect=RuntimeError("Failure")):
        with TestClient(app) as c:
            c.headers.update(HEADERS)
            c.post("/api/local/scan", json={})
            deadline = time.monotonic() + 8
            while time.monotonic() < deadline:
                jobs = c.get("/api/jobs").json()
                if jobs[0]["status"] == "failed": break
                time.sleep(.1)
            assert jobs[0]["status"] == "failed"
            assert c.get("/api/export").json()["assessments"] == []
