"""Tests for SecureAudit SQLite scan-history storage."""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any

import pytest

from core.database import (
    DatabaseError,
    get_scan,
    initialize_database,
    list_scans,
    save_scan,
)


def scanner_result(
    check_id: str,
    status: str,
) -> dict[str, Any]:
    """Return a representative normalized scanner result."""

    return {
        "check_id": check_id,
        "check_name": f"Test check {check_id}",
        "expected_value": "Secure expected state",
        "observed_value": f"Observed status={status}",
        "status": status,
        "evidence": [
            {
                "source": "unit-test",
                "enabled": status == "Pass",
            }
        ],
        "error_message": (
            "Assessment failed"
            if status == "Error"
            else None
        ),
        "timestamp_utc": "2026-08-06T12:00:00+00:00",
    }


def scoring_summary() -> dict[str, int | float]:
    """Return a summary for one pass, one failure, and one error."""

    return {
        "selected_count": 3,
        "passed_count": 1,
        "failed_count": 1,
        "error_count": 1,
        "assessed_count": 2,
        "unassessed_count": 1,
        "compliance_score": 50.0,
        "coverage_percentage": 66.67,
    }


@pytest.fixture
def database_path(tmp_path: Path) -> Path:
    """Return an isolated database path for one test."""

    return tmp_path / "secureaudit-test.db"


def test_initialize_database_creates_required_tables(
    database_path: Path,
) -> None:
    """Initialization should create both storage tables."""

    initialize_database(database_path)

    with sqlite3.connect(database_path) as connection:
        table_names = {
            row[0]
            for row in connection.execute(
                """
                SELECT name
                FROM sqlite_master
                WHERE type = 'table'
                """
            )
        }

    assert "scans" in table_names
    assert "scan_results" in table_names


def test_initialize_database_is_idempotent(
    database_path: Path,
) -> None:
    """The schema may be initialized repeatedly without data loss."""

    initialize_database(database_path)
    initialize_database(database_path)

    assert database_path.exists()


def test_save_and_get_scan_round_trip(
    database_path: Path,
) -> None:
    """A stored scan should be reconstructed with its evidence."""

    results = [
        scanner_result("WIN-FW-001", "Pass"),
        scanner_result("WIN-BL-001", "Fail"),
        scanner_result("WIN-SMB1-001", "Error"),
    ]

    scan_id = save_scan(
        scan_id="scan-round-trip",
        hostname="TEST-WINDOWS-01",
        results=results,
        summary=scoring_summary(),
        started_at_utc="2026-08-06T11:59:00+00:00",
        completed_at_utc="2026-08-06T12:00:01+00:00",
        database_path=database_path,
    )

    stored_scan = get_scan(scan_id, database_path)

    assert scan_id == "scan-round-trip"
    assert stored_scan is not None
    assert stored_scan["scan_id"] == scan_id
    assert stored_scan["hostname"] == "TEST-WINDOWS-01"
    assert stored_scan["selected_count"] == 3
    assert stored_scan["passed_count"] == 1
    assert stored_scan["failed_count"] == 1
    assert stored_scan["error_count"] == 1
    assert stored_scan["compliance_score"] == 50.0
    assert stored_scan["coverage_percentage"] == 66.67

    assert [
        result["check_id"]
        for result in stored_scan["results"]
    ] == [
        "WIN-FW-001",
        "WIN-BL-001",
        "WIN-SMB1-001",
    ]

    assert stored_scan["results"][0]["evidence"] == [
        {
            "source": "unit-test",
            "enabled": True,
        }
    ]

    assert stored_scan["results"][2]["error_message"] == (
        "Assessment failed"
    )


def test_save_scan_generates_identifier(
    database_path: Path,
) -> None:
    """A UUID identifier should be generated when none is supplied."""

    scan_id = save_scan(
        hostname="TEST-WINDOWS-01",
        results=[],
        summary={
            "selected_count": 0,
            "passed_count": 0,
            "failed_count": 0,
            "error_count": 0,
            "assessed_count": 0,
            "unassessed_count": 0,
            "compliance_score": None,
            "coverage_percentage": 0.0,
        },
        started_at_utc="2026-08-06T12:00:00+00:00",
        database_path=database_path,
    )

    assert isinstance(scan_id, str)
    assert scan_id
    assert get_scan(scan_id, database_path) is not None


def test_get_scan_returns_none_for_unknown_identifier(
    database_path: Path,
) -> None:
    """A missing scan should not be reported as a database failure."""

    assert get_scan(
        "missing-scan",
        database_path,
    ) is None


def test_list_scans_returns_newest_first(
    database_path: Path,
) -> None:
    """History should place the most recently completed scan first."""

    empty_summary = {
        "selected_count": 0,
        "passed_count": 0,
        "failed_count": 0,
        "error_count": 0,
        "assessed_count": 0,
        "unassessed_count": 0,
        "compliance_score": None,
        "coverage_percentage": 0.0,
    }

    save_scan(
        scan_id="older-scan",
        hostname="HOST-A",
        results=[],
        summary=empty_summary,
        started_at_utc="2026-08-06T10:00:00+00:00",
        completed_at_utc="2026-08-06T10:01:00+00:00",
        database_path=database_path,
    )

    save_scan(
        scan_id="newer-scan",
        hostname="HOST-B",
        results=[],
        summary=empty_summary,
        started_at_utc="2026-08-06T11:00:00+00:00",
        completed_at_utc="2026-08-06T11:01:00+00:00",
        database_path=database_path,
    )

    history = list_scans(database_path)

    assert [
        scan["scan_id"]
        for scan in history
    ] == [
        "newer-scan",
        "older-scan",
    ]


def test_list_scans_honors_limit(
    database_path: Path,
) -> None:
    """The history query should enforce the requested maximum."""

    empty_summary = {
        "selected_count": 0,
        "passed_count": 0,
        "failed_count": 0,
        "error_count": 0,
        "assessed_count": 0,
        "unassessed_count": 0,
        "compliance_score": None,
        "coverage_percentage": 0.0,
    }

    for number in range(3):
        save_scan(
            scan_id=f"scan-{number}",
            hostname="TEST-HOST",
            results=[],
            summary=empty_summary,
            started_at_utc=f"2026-08-06T10:0{number}:00+00:00",
            completed_at_utc=f"2026-08-06T10:0{number}:30+00:00",
            database_path=database_path,
        )

    history = list_scans(
        database_path,
        limit=2,
    )

    assert len(history) == 2


def test_invalid_limit_is_rejected(
    database_path: Path,
) -> None:
    """History limits outside the accepted range should be rejected."""

    with pytest.raises(
        DatabaseError,
        match="between 1 and 1000",
    ):
        list_scans(
            database_path,
            limit=0,
        )


def test_summary_result_count_mismatch_is_rejected(
    database_path: Path,
) -> None:
    """The selected count must match the number of result rows."""

    with pytest.raises(
        DatabaseError,
        match="does not match result count",
    ):
        save_scan(
            hostname="TEST-HOST",
            results=[
                scanner_result("WIN-FW-001", "Pass"),
            ],
            summary=scoring_summary(),
            started_at_utc="2026-08-06T12:00:00+00:00",
            database_path=database_path,
        )


def test_inconsistent_summary_is_rejected(
    database_path: Path,
) -> None:
    """Contradictory summary counts must not be persisted."""

    summary = scoring_summary()
    summary["assessed_count"] = 3

    with pytest.raises(
        DatabaseError,
        match="assessed count is inconsistent",
    ):
        save_scan(
            hostname="TEST-HOST",
            results=[
                scanner_result("WIN-FW-001", "Pass"),
                scanner_result("WIN-BL-001", "Fail"),
                scanner_result("WIN-SMB1-001", "Error"),
            ],
            summary=summary,
            started_at_utc="2026-08-06T12:00:00+00:00",
            database_path=database_path,
        )


def test_unsupported_result_status_is_rejected(
    database_path: Path,
) -> None:
    """Only normalized Pass, Fail, and Error statuses are accepted."""

    invalid_result = scanner_result(
        "WIN-FW-001",
        "Skipped",
    )

    with pytest.raises(
        DatabaseError,
        match="unsupported status",
    ):
        save_scan(
            hostname="TEST-HOST",
            results=[invalid_result],
            summary={
                "selected_count": 1,
                "passed_count": 0,
                "failed_count": 0,
                "error_count": 1,
                "assessed_count": 0,
                "unassessed_count": 1,
                "compliance_score": None,
                "coverage_percentage": 0.0,
            },
            started_at_utc="2026-08-06T12:00:00+00:00",
            database_path=database_path,
        )


def test_duplicate_check_ids_are_rejected(
    database_path: Path,
) -> None:
    """One scan must not contain duplicate evidence for one check."""

    duplicate_results = [
        scanner_result("WIN-FW-001", "Pass"),
        scanner_result("WIN-FW-001", "Fail"),
    ]

    with pytest.raises(
        DatabaseError,
        match="Duplicate check ID",
    ):
        save_scan(
            hostname="TEST-HOST",
            results=duplicate_results,
            summary={
                "selected_count": 2,
                "passed_count": 1,
                "failed_count": 1,
                "error_count": 0,
                "assessed_count": 2,
                "unassessed_count": 0,
                "compliance_score": 50.0,
                "coverage_percentage": 100.0,
            },
            started_at_utc="2026-08-06T12:00:00+00:00",
            database_path=database_path,
        )


def test_non_serializable_evidence_is_rejected(
    database_path: Path,
) -> None:
    """Evidence must be valid JSON before persistence."""

    invalid_result = scanner_result(
        "WIN-FW-001",
        "Pass",
    )
    invalid_result["evidence"] = {
        "unsupported": object(),
    }

    with pytest.raises(
        DatabaseError,
        match="non-JSON-serializable evidence",
    ):
        save_scan(
            hostname="TEST-HOST",
            results=[invalid_result],
            summary={
                "selected_count": 1,
                "passed_count": 1,
                "failed_count": 0,
                "error_count": 0,
                "assessed_count": 1,
                "unassessed_count": 0,
                "compliance_score": 100.0,
                "coverage_percentage": 100.0,
            },
            started_at_utc="2026-08-06T12:00:00+00:00",
            database_path=database_path,
        )


def test_duplicate_scan_id_does_not_overwrite_existing_scan(
    database_path: Path,
) -> None:
    """A repeated scan ID must fail rather than replace evidence."""

    empty_summary = {
        "selected_count": 0,
        "passed_count": 0,
        "failed_count": 0,
        "error_count": 0,
        "assessed_count": 0,
        "unassessed_count": 0,
        "compliance_score": None,
        "coverage_percentage": 0.0,
    }

    save_scan(
        scan_id="duplicate-scan",
        hostname="ORIGINAL-HOST",
        results=[],
        summary=empty_summary,
        started_at_utc="2026-08-06T12:00:00+00:00",
        database_path=database_path,
    )

    with pytest.raises(
        DatabaseError,
        match="Could not store scan",
    ):
        save_scan(
            scan_id="duplicate-scan",
            hostname="REPLACEMENT-HOST",
            results=[],
            summary=empty_summary,
            started_at_utc="2026-08-06T12:05:00+00:00",
            database_path=database_path,
        )

    stored_scan = get_scan(
        "duplicate-scan",
        database_path,
    )

    assert stored_scan is not None
    assert stored_scan["hostname"] == "ORIGINAL-HOST"

def test_completed_time_before_start_time_is_rejected(
    database_path: Path,
) -> None:
    """A scan cannot complete before it starts."""

    with pytest.raises(
        DatabaseError,
        match="cannot be earlier",
    ):
        save_scan(
            hostname="TEST-HOST",
            results=[],
            summary={
                "selected_count": 0,
                "passed_count": 0,
                "failed_count": 0,
                "error_count": 0,
                "assessed_count": 0,
                "unassessed_count": 0,
                "compliance_score": None,
                "coverage_percentage": 0.0,
            },
            started_at_utc="2026-08-06T12:00:00+00:00",
            completed_at_utc="2026-08-06T11:59:59+00:00",
            database_path=database_path,
        )


def test_timestamp_without_timezone_is_rejected(
    database_path: Path,
) -> None:
    """Stored timestamps must identify their timezone."""

    with pytest.raises(
        DatabaseError,
        match="must include timezone information",
    ):
        save_scan(
            hostname="TEST-HOST",
            results=[],
            summary={
                "selected_count": 0,
                "passed_count": 0,
                "failed_count": 0,
                "error_count": 0,
                "assessed_count": 0,
                "unassessed_count": 0,
                "compliance_score": None,
                "coverage_percentage": 0.0,
            },
            started_at_utc="2026-08-06T12:00:00",
            completed_at_utc="2026-08-06T12:01:00+00:00",
            database_path=database_path,
        )