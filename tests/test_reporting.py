"""Tests for SecureAudit standalone HTML reporting."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from core.reporting import (
    ReportingError,
    build_html_report,
    write_html_report,
)


def stored_scan() -> dict[str, Any]:
    """Return a representative stored scan for report tests."""

    return {
        "scan_id": "scan-report-001",
        "started_at_utc": "2026-08-06T12:00:00+00:00",
        "completed_at_utc": "2026-08-06T12:01:00+00:00",
        "hostname": "TEST-WINDOWS-01",
        "selected_count": 3,
        "passed_count": 1,
        "failed_count": 1,
        "error_count": 1,
        "assessed_count": 2,
        "unassessed_count": 1,
        "compliance_score": 50.0,
        "coverage_percentage": 66.67,
        "results": [
            {
                "check_id": "WIN-FW-001",
                "check_name": "Windows Firewall Enabled",
                "expected_value": "All profiles enabled",
                "observed_value": "All profiles enabled",
                "status": "Pass",
                "evidence": [
                    {
                        "profile": "Domain",
                        "enabled": True,
                    }
                ],
                "error_message": None,
                "timestamp_utc": "2026-08-06T12:00:10+00:00",
            },
            {
                "check_id": "WIN-BL-001",
                "check_name": "BitLocker Protection Enabled",
                "expected_value": "System drive protected",
                "observed_value": "ProtectionStatus=Off",
                "status": "Fail",
                "evidence": [
                    {
                        "mount_point": "C:",
                        "protection_status": "Off",
                    }
                ],
                "error_message": None,
                "timestamp_utc": "2026-08-06T12:00:20+00:00",
            },
            {
                "check_id": "WIN-SMB1-001",
                "check_name": "SMBv1 Disabled",
                "expected_value": "SMBv1 disabled",
                "observed_value": "Could not assess",
                "status": "Error",
                "evidence": [
                    {
                        "error_type": "PermissionError",
                    }
                ],
                "error_message": "Administrator rights required",
                "timestamp_utc": "2026-08-06T12:00:30+00:00",
            },
        ],
    }


def test_build_report_contains_scan_summary() -> None:
    """The report should include scan-level metadata and scoring."""

    report = build_html_report(stored_scan())

    assert "<!DOCTYPE html>" in report
    assert "SecureAudit Compliance Report" in report
    assert "TEST-WINDOWS-01" in report
    assert "scan-report-001" in report
    assert "50.00%" in report
    assert "66.67%" in report


def test_build_report_contains_all_results() -> None:
    """Each stored technical result should be shown."""

    report = build_html_report(stored_scan())

    assert "WIN-FW-001" in report
    assert "WIN-BL-001" in report
    assert "WIN-SMB1-001" in report

    assert "Windows Firewall Enabled" in report
    assert "BitLocker Protection Enabled" in report
    assert "SMBv1 Disabled" in report

    assert "Pass" in report
    assert "Fail" in report
    assert "Error" in report


def test_build_report_contains_evidence() -> None:
    """Stored JSON evidence should be represented in the report."""

    report = build_html_report(stored_scan())

    assert "&quot;profile&quot;" in report
    assert "&quot;mount_point&quot;" in report
    assert "&quot;error_type&quot;" in report
    assert "Administrator rights required" in report


def test_html_special_characters_are_escaped() -> None:
    """Scanner-controlled text must not be interpreted as HTML."""

    scan = stored_scan()
    scan["hostname"] = "<script>alert('host')</script>"
    scan["results"][0]["observed_value"] = (
        "<img src=x onerror=alert(1)>"
    )
    scan["results"][0]["evidence"] = {
        "payload": "<script>alert(1)</script>",
    }

    report = build_html_report(scan)

    assert "<script>alert('host')</script>" not in report
    assert "&lt;script&gt;alert(&#x27;host&#x27;)&lt;/script&gt;" in report

    assert "<img src=x onerror=alert(1)>" not in report
    assert "&lt;img src=x onerror=alert(1)&gt;" in report

    assert "<script>alert(1)</script>" not in report
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in report


def test_none_compliance_score_is_not_reported_as_zero() -> None:
    """No assessment result should display as unavailable, not zero."""

    scan = stored_scan()
    scan["selected_count"] = 1
    scan["passed_count"] = 0
    scan["failed_count"] = 0
    scan["error_count"] = 1
    scan["assessed_count"] = 0
    scan["unassessed_count"] = 1
    scan["compliance_score"] = None
    scan["coverage_percentage"] = 0.0
    scan["results"] = [
        scan["results"][2],
    ]

    report = build_html_report(scan)

    assert "Not available" in report
    assert "0.00%" in report


def test_empty_scan_displays_empty_state() -> None:
    """A valid scan with no selected checks should still be reportable."""

    scan = stored_scan()
    scan["selected_count"] = 0
    scan["passed_count"] = 0
    scan["failed_count"] = 0
    scan["error_count"] = 0
    scan["assessed_count"] = 0
    scan["unassessed_count"] = 0
    scan["compliance_score"] = None
    scan["coverage_percentage"] = 0.0
    scan["results"] = []

    report = build_html_report(scan)

    assert "No checks were selected for this scan." in report


def test_write_report_creates_utf8_html_file(
    tmp_path: Path,
) -> None:
    """The report writer should create a readable HTML file."""

    report_path = write_html_report(
        stored_scan(),
        output_directory=tmp_path,
    )

    assert report_path.exists()
    assert report_path.name == (
        "secureaudit-scan-report-001.html"
    )

    content = report_path.read_text(
        encoding="utf-8",
    )

    assert "SecureAudit Compliance Report" in content
    assert "TEST-WINDOWS-01" in content


def test_custom_filename_gets_html_extension(
    tmp_path: Path,
) -> None:
    """A custom filename without an extension should receive .html."""

    report_path = write_html_report(
        stored_scan(),
        output_directory=tmp_path,
        filename="custom-report",
    )

    assert report_path.name == "custom-report.html"


def test_custom_filename_cannot_escape_output_directory(
    tmp_path: Path,
) -> None:
    """Directory components in a filename should be discarded."""

    report_path = write_html_report(
        stored_scan(),
        output_directory=tmp_path,
        filename="../outside-report.html",
    )

    assert report_path.parent == tmp_path
    assert report_path.name == "outside-report.html"


def test_missing_scan_field_is_rejected() -> None:
    """Required scan-level values must be present."""

    scan = stored_scan()
    del scan["hostname"]

    with pytest.raises(
        ReportingError,
        match="missing 'hostname'",
    ):
        build_html_report(scan)


def test_inconsistent_result_counts_are_rejected() -> None:
    """Summary counts must match their stated relationships."""

    scan = stored_scan()
    scan["passed_count"] = 2

    with pytest.raises(
        ReportingError,
        match="result counts are inconsistent",
    ):
        build_html_report(scan)


def test_result_count_mismatch_is_rejected() -> None:
    """Selected count must match the number of report results."""

    scan = stored_scan()
    scan["selected_count"] = 4
    scan["error_count"] = 2
    scan["unassessed_count"] = 2

    with pytest.raises(
        ReportingError,
        match="selected count does not match result count",
    ):
        build_html_report(scan)


def test_unsupported_status_is_rejected() -> None:
    """Only Pass, Fail, and Error may appear in a report."""

    scan = stored_scan()
    scan["results"][0]["status"] = "Skipped"

    with pytest.raises(
        ReportingError,
        match="unsupported status",
    ):
        build_html_report(scan)


def test_duplicate_check_ids_are_rejected() -> None:
    """A report should not show duplicate evidence for one check."""

    scan = stored_scan()
    scan["results"][1]["check_id"] = "WIN-FW-001"

    with pytest.raises(
        ReportingError,
        match="Duplicate check ID",
    ):
        build_html_report(scan)


def test_non_serializable_evidence_is_rejected() -> None:
    """Evidence must remain valid JSON for safe report rendering."""

    scan = stored_scan()
    scan["results"][0]["evidence"] = {
        "invalid": object(),
    }

    with pytest.raises(
        ReportingError,
        match="non-JSON-serializable evidence",
    ):
        build_html_report(scan)


def test_invalid_percentage_is_rejected() -> None:
    """Percentages outside zero to one hundred are invalid."""

    scan = stored_scan()
    scan["coverage_percentage"] = 101.0

    with pytest.raises(
        ReportingError,
        match="between 0 and 100",
    ):
        build_html_report(scan)


def test_non_mapping_scan_is_rejected() -> None:
    """Report input must be a stored-scan mapping."""

    with pytest.raises(
        ReportingError,
        match="provided as a mapping",
    ):
        build_html_report("not-a-scan")