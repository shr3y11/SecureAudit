"""Verify PostgreSQL against a new disposable database, never an existing DB."""
import json
import os
from pathlib import Path
import subprocess
from uuid import uuid4
import psycopg
from psycopg import sql

workspace = Path(__file__).resolve().parent.parent
password = (workspace / ".tools" / "pg-password").read_text().strip()
name = "secureaudit_m5_test_" + uuid4().hex[:12]
conninfo = {"host": "127.0.0.1", "port": 55432, "user": "secureaudit", "password": password, "dbname": "postgres"}
with psycopg.connect(**conninfo, autocommit=True) as connection:
    connection.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(name)))
    env = os.environ.copy()
    env["SECUREAUDIT_TEST_POSTGRES_URL"] = f"postgresql+psycopg://secureaudit:{password}@127.0.0.1:55432/{name}"
    try:
        result = subprocess.run([str(workspace / ".venv/Scripts/python.exe"), "-m", "pytest", "tests/test_central_postgres.py", "-q"], cwd=workspace, env=env)
        if result.returncode != 0:
            raise RuntimeError("PostgreSQL integration test failed")
        print(json.dumps({"postgresql": "passed", "database": name, "test": "full flow and restart persistence"}))
    finally:
        if not name.startswith("secureaudit_m5_test_"):
            raise RuntimeError("Refusing cleanup outside the disposable test database")
        connection.execute(sql.SQL("DROP DATABASE {} WITH (FORCE)").format(sql.Identifier(name)))
