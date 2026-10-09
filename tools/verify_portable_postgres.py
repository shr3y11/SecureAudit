"""Exercise the actual portable EXE against a fresh PostgreSQL test database."""
import json
import os
from pathlib import Path
import subprocess
import tempfile
import time
import urllib.error
import urllib.request
from uuid import uuid4
import psycopg
from psycopg import sql

root = Path(__file__).resolve().parent.parent
password = (root / ".tools/pg-password").read_text().strip()
name = "secureaudit_portable_test_" + uuid4().hex[:12]
conninfo = {"host": "127.0.0.1", "port": 55432, "user": "secureaudit", "password": password, "dbname": "postgres"}
base = "http://127.0.0.1:8766"

def request(token, path, payload=None):
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(base + path, data=data, headers={"Authorization": "Bearer " + token, "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=10) as response:
        return json.load(response)

with psycopg.connect(**conninfo, autocommit=True) as connection:
    connection.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(name)))
    try:
        with tempfile.TemporaryDirectory(prefix="secureaudit-packaged-pg-") as folder:
            env = os.environ.copy()
            env.update(SECUREAUDIT_DATABASE_URL=f"postgresql+psycopg://secureaudit:{password}@127.0.0.1:55432/{name}",
                       SECUREAUDIT_DATA_DIR=folder, SECUREAUDIT_PORT="8766", SECUREAUDIT_HEADLESS="1")
            process = subprocess.Popen([str(root / "dist/SecureAudit-M5/SecureAuditCentral.exe")], env=env)
            try:
                deadline = time.monotonic() + 30
                while time.monotonic() < deadline:
                    try:
                        token = (Path(folder) / "access.key").read_text().strip()
                        health = request(token, "/health")
                        break
                    except (OSError, urllib.error.URLError):
                        if process.poll() is not None:
                            raise RuntimeError("Portable PostgreSQL server exited during startup")
                        time.sleep(.1)
                else:
                    raise RuntimeError("Portable PostgreSQL API did not become ready")
                assert health["database"] == "postgresql"
                request(token, "/api/demo/seed", {"count": 10})
                endpoints = request(token, "/api/endpoints")
                request(token, "/api/demo/jobs", {"endpoint_ids": [e["id"] for e in endpoints]})
                while time.monotonic() < deadline:
                    summary = request(token, "/api/summary")
                    if summary["assessed_endpoints"] == 10:
                        break
                    time.sleep(.1)
                assert summary["assessed_endpoints"] == 10
                assert len(request(token, "/api/export")["assessments"]) == 10
                result = {"portable_postgresql": "passed", "health": health, "assessed_endpoints": 10}
                (root / "release-qa/portable-postgres.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
                print(json.dumps(result))
            finally:
                process.terminate()
                process.wait(timeout=15)
    finally:
        if not name.startswith("secureaudit_portable_test_"):
            raise RuntimeError("Refusing cleanup outside the disposable test database")
        connection.execute(sql.SQL("DROP DATABASE {} WITH (FORCE)").format(sql.Identifier(name)))
