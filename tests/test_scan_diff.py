"""Tests for two-scan diff (add-list item #20)."""
import pytest

from core.reporting import build_html_report
from core.scan_diff import diff_scans
from tests.test_reporting import stored_scan


def scan_with(statuses, scan_id="s1", context=None):
    scan = {"scan_id": scan_id,
            "results": [{"check_id": cid, "status": status} for cid, status in statuses]}
    if context:
        scan["evidence_context"] = context
    return scan


def test_transitions_classify_fixed_regressed_changed_added_removed():
    previous = scan_with([("A", "Fail"), ("B", "Pass"), ("C", "Fail"), ("D", "Pass"), ("E", "Error")])
    current = scan_with([("A", "Pass"), ("B", "Fail"), ("C", "Error"), ("D", "Pass"), ("F", "Pass")], "s2")
    diff = diff_scans(previous, current)
    kinds = {t["check_id"]: t["change"] for t in diff["transitions"]}
    assert kinds == {"A": "fixed", "B": "regressed", "C": "changed",
                     "D": "unchanged", "E": "removed", "F": "added"}
    assert diff["counts"] == {"fixed": 1, "regressed": 1, "changed": 1,
                              "unchanged": 1, "added": 1, "removed": 1}
    assert diff["previous_scan_id"] == "s1" and diff["current_scan_id"] == "s2"


def test_context_snapshots_come_from_stored_contexts():
    context = {"baseline_version": "1.0.0", "catalog_sha256": "a" * 64,
               "threshold_numerator": 4, "threshold_denominator": 5}
    previous = scan_with([("A", "Pass")], context=context)
    current = scan_with([("A", "Pass")], "s2")
    diff = diff_scans(previous, current)
    assert diff["previous_context"]["catalog_sha256"] == "a" * 64
    assert diff["previous_context"]["threshold"] == "4/5"
    assert diff["current_context"] is None, "no context must be invented for a scan that has none"


def test_invalid_records_are_rejected():
    with pytest.raises(ValueError):
        diff_scans(scan_with([("A", "Bogus")]), scan_with([("A", "Pass")]))
    with pytest.raises(ValueError):
        diff_scans({"results": [{"check_id": "A", "status": "Pass"},
                                {"check_id": "A", "status": "Fail"}]},
                   scan_with([("A", "Pass")]))


def test_report_includes_diff_section_only_when_previous_scan_given():
    current = stored_scan()
    previous = stored_scan()
    previous["scan_id"] = "scan-report-000"
    previous["results"][1]["status"] = "Pass"  # BitLocker was Pass, now Fail: regressed

    plain = build_html_report(current)
    assert "Changes since previous scan" not in plain

    with_diff = build_html_report(current, previous_scan=previous)
    assert "Changes since previous scan" in with_diff
    assert "Regressed: 1" in with_diff
    assert "WIN-BL-001" in with_diff
