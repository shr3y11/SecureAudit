"""Tests for the experimental Linux collectors (item #22).

The collectors were written fresh; the archived prototype scanner
files are empty. These tests run the real scripts on the test host:
statuses depend on that host's configuration, so the contract (fields,
check IDs, allowed statuses, Error-never-Fail semantics) is what is
asserted, plus the one environment-independent case (guest account via
the readable /etc/passwd).
"""
import json
import os
import subprocess
from pathlib import Path

import pytest

from core.scanner import load_catalog
from tools.run_linux_checks import run_linux_check

ROOT = Path(__file__).resolve().parents[1]
CATALOG_PATH = ROOT / "checks" / "linux" / "catalog.json"
SCRIPTS = ROOT / "checks" / "linux" / "bash"

pytestmark = pytest.mark.skipif(os.name != "posix", reason="Linux collectors run on POSIX hosts")


@pytest.fixture(scope="module")
def catalog():
    return load_catalog(CATALOG_PATH)


def test_linux_catalog_is_valid_and_unmapped(catalog):
    assert len(catalog["checks"]) == 5
    for check in catalog["checks"]:
        assert check["id"].startswith("LIN-")
        assert (SCRIPTS / check["script"]).is_file()
        # No framework mapping may be claimed for these yet.
        assert check["mapping_type"] == "Pending validation"
        assert check["mapped_safeguard"] is None


@pytest.mark.parametrize("script", sorted(p.name for p in SCRIPTS.glob("*.sh")))
def test_each_collector_emits_the_result_contract(script, catalog):
    process = subprocess.run(["bash", str(SCRIPTS / script)], capture_output=True, text=True, timeout=30)
    assert process.returncode == 0, process.stderr
    result = json.loads(process.stdout)
    expected = {c["script"]: c for c in catalog["checks"]}[script]
    assert result["check_id"] == expected["id"]
    assert result["status"] in ("Pass", "Fail", "Error")
    for field in ("check_name", "expected_value", "observed_value", "evidence", "error_message", "timestamp_utc"):
        assert field in result
    if result["status"] == "Error":
        assert result["error_message"], "an Error result must explain itself"


def test_guest_check_is_conclusive_on_any_posix_host(catalog):
    check = next(c for c in catalog["checks"] if c["id"] == "LIN-GUEST-001")
    result = run_linux_check(check)
    assert result["status"] in ("Pass", "Fail"), "/etc/passwd is always readable; this check must not be Error"


def test_runner_rejects_unknown_ids():
    process = subprocess.run(
        ["python3", str(ROOT / "tools" / "run_linux_checks.py"), "LIN-NOPE-999"],
        capture_output=True, text=True, timeout=30,
    )
    assert process.returncode == 2
