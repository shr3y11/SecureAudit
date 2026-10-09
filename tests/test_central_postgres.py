"""Run against an explicitly supplied disposable PostgreSQL database."""
import os
import time
from datetime import datetime, timezone
from uuid import uuid4
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from secureaudit_central.api import create_app


@pytest.mark.skipif(not os.environ.get("SECUREAUDIT_TEST_POSTGRES_URL"), reason="Disposable PostgreSQL URL not supplied")
def test_postgres_full_flow_and_restart():
    url = os.environ["SECUREAUDIT_TEST_POSTGRES_URL"]
    token = "integration-test-" + "x" * 48
    headers = {"Authorization": "Bearer " + token}
    hostname = "PG-TEST-" + uuid4().hex[:12]
    with TestClient(create_app(url, token, worker_enabled=False)) as client:
        client.headers.update(headers)
        assert client.get("/health").json()["database"] == "postgresql"
        endpoint = client.post("/api/endpoints", json={"hostname": hostname}).json()["id"]
        evidence = {"submission_id": uuid4().hex, "collected_at": datetime.now(timezone.utc).isoformat(),
                    "checks": [{"check_id": "WIN-FW-001", "title": "Firewall", "status": "Pass", "detail": "Integration test fixture"},
                               {"check_id": "WIN-BL-001", "title": "Encryption", "status": "Error", "detail": "Test unavailable evidence"}]}
        result = client.post(f"/api/endpoints/{endpoint}/evidence", json=evidence)
        assert result.status_code == 200, result.text
        assert result.json()["score"] == 100 and result.json()["coverage"] == 50
        assert not client.post(f"/api/endpoints/{endpoint}/evidence", json=evidence).json()["created"]
        client.post("/api/demo/seed", json={"count": 10})
        simulated = [e["id"] for e in client.get("/api/endpoints").json() if e["simulated"]]
        client.post("/api/demo/jobs", json={"endpoint_ids": simulated})
    with TestClient(create_app(url, token)) as client:
        client.headers.update(headers)
        deadline = time.monotonic() + 20
        while time.monotonic() < deadline:
            jobs = client.get("/api/jobs").json()
            if all(job["status"] == "completed" for job in jobs): break
            time.sleep(.1)
        assert all(job["status"] == "completed" for job in jobs)
        assert client.get(f"/api/endpoints/{endpoint}/history").json()[0]["source"] == "imported"
        assert len(client.get("/api/export").json()["assessments"]) >= 11
        assert client.get("/api/export.csv").status_code == 200
        assert client.get("/api/summary").json()["database"] == "postgresql"
