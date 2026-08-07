"""SecureAudit local Windows scan workflow.

This module is the application orchestration layer.

It connects the reusable scanner, scoring, database, and reporting modules
without duplicating their internal security or compliance logic.
"""

from __future__ import annotations

import socket
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Iterable

from core.database import get_scan, save_scan
from core.reporting import write_html_report
from core.scanner import run_check
from core.scoring import calculate_score


class ScanWorkflowError(RuntimeError):
    """Raised when the complete local scan workflow cannot be completed."""


def _utc_now() -> str:
    """Return the current UTC time as a timezone-aware ISO 8601 string."""

    return datetime.now(UTC).isoformat()


def _validate_selected_check_ids(
    selected_check_ids: Iterable[str],
) -> list[str]:
    """Validate application-level structure for selected check identifiers.

    Approval and script security are intentionally not checked here.
    Those security decisions remain the responsibility of core.scanner.
    """

    if isinstance(selected_check_ids, (str, bytes)):
        raise ValueError(
            "selected_check_ids must be an iterable of check IDs, "
            "not a single string."
        )

    check_ids = list(selected_check_ids)

    if not check_ids:
        raise ValueError("At least one check must be selected.")

    for check_id in check_ids:
        if not isinstance(check_id, str):
            raise ValueError("Every selected check ID must be a string.")

        if not check_id.strip():
            raise ValueError("Selected check IDs cannot be empty.")

    if len(check_ids) != len(set(check_ids)):
        raise ValueError("Duplicate check IDs are not allowed.")

    return check_ids


def run_local_scan(
    selected_check_ids: Iterable[str],
) -> dict[str, Any]:
    """Run the complete local SecureAudit assessment workflow.

    Workflow:

        selected approved IDs
            -> scanner
            -> normalized results
            -> scoring
            -> SQLite persistence
            -> stored scan retrieval
            -> HTML reporting

    The scanner remains responsible for deciding whether a check ID is
    approved and whether its PowerShell script may execute.
    """

    check_ids = _validate_selected_check_ids(selected_check_ids)

    hostname = socket.gethostname()
    started_at_utc = _utc_now()

    results: list[dict[str, Any]] = []

    for check_id in check_ids:
        result = run_check(check_id)
        results.append(result)

    completed_at_utc = _utc_now()

    summary = calculate_score(results)

    scan_id = save_scan(
        hostname=hostname,
        results=results,
        summary=summary,
        started_at_utc=started_at_utc,
        completed_at_utc=completed_at_utc,
    )

    stored_scan = get_scan(scan_id)

    if stored_scan is None:
        raise ScanWorkflowError(
            f"Scan {scan_id!r} was saved but could not be read back "
            "from the database."
        )

    report_path = write_html_report(stored_scan)

    return {
        "scan_id": scan_id,
        "scan": stored_scan,
        "report_path": Path(report_path),
    }


def main() -> None:
    """Run a small command-line integration demonstration.

    The Tkinter interface will replace this temporary entry point during
    the next UI commit.
    """

    selected_check_ids = [
        "WIN-FW-001",
        "WIN-DEF-001",
        "WIN-BL-001",
        "WIN-GUEST-001",
        "WIN-SMB1-001",
    ]

    workflow_result = run_local_scan(selected_check_ids)

    scan = workflow_result["scan"]
    report_path = workflow_result["report_path"]

    score = scan["compliance_score"]
    coverage = scan["coverage_percentage"]

    print()
    print("SecureAudit scan completed")
    print(f"Scan ID: {scan['scan_id']}")
    print(f"Hostname: {scan['hostname']}")
    print(f"Selected: {scan['selected_count']}")
    print(f"Passed: {scan['passed_count']}")
    print(f"Failed: {scan['failed_count']}")
    print(f"Errors: {scan['error_count']}")

    if score is None:
        print("Compliance score: Not available")
    else:
        print(f"Compliance score: {score:.2f}%")

    print(f"Assessment coverage: {coverage:.2f}%")
    print(f"Report: {report_path.resolve()}")


if __name__ == "__main__":
    main()