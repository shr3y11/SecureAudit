"""Validate completion semantics and the real persistence/report workflow."""
from fractions import Fraction
from itertools import product
import sqlite3
from unittest.mock import patch

import pytest

from core.evidence import assess_evidence, assess_context, make_context
from core.database import DatabaseError, get_scan, initialize_database, save_scan
from core.reporting import build_html_report
from core.scanner import load_catalog
from core.scoring import calculate_score

IDS = tuple(c["id"] for c in load_catalog()["checks"] if c["enabled"])
STATUSES = {"P": "Pass", "F": "Fail", "E": "Error"}
NOW = "2026-10-20T00:00:00+00:00"


def records(states):
    return [{"check_id": cid, "status": STATUSES[state], "check_name": cid,
             "expected_value": "Expected", "observed_value": "Fixture",
             "evidence": {"source": "synthetic-test"}, "error_message": None,
             "timestamp_utc": NOW} for cid, state in zip(IDS, states) if state != "O"]


def test_all_1023_vectors_against_binary_completion_oracle():
    """The production implementation agrees with explicit complete states."""
    checked = 0
    for states in product("PFEO", repeat=5):
        if all(s == "O" for s in states):
            continue
        selected = [cid for cid, state in zip(IDS, states) if state != "O"]
        unresolved = [i for i, state in enumerate(states) if state in "EO"]
        truths = []
        for completion in product("PF", repeat=len(unresolved)):
            full = list(states)
            for index, value in zip(unresolved, completion):
                full[index] = value
            truths.append(Fraction(full.count("P"), 5))
        for threshold in (Fraction(3, 5), Fraction(4, 5), Fraction(1)):
            actual = assess_evidence(IDS, selected, records(states), threshold)
            expected = ("ABOVE" if all(v >= threshold for v in truths) else
                        "BELOW" if all(v < threshold for v in truths) else "UNRESOLVED")
            assert actual["decision"] == expected, states
            assert actual["lower_bound"] == float(min(truths) * 100)
            assert actual["upper_bound"] == float(max(truths) * 100)
        checked += 1
    assert checked == 1023


def test_selection_does_not_shrink_baseline_and_missing_record_is_error():
    report = assess_evidence(IDS, IDS[:2], records("POOOO"))
    assert report["states"][IDS[1]] == "E"
    assert report["missing_selected_records"] == [IDS[1]]
    assert (report["selected_coverage"], report["baseline_coverage"]) == (50, 20)
    assert (report["lower_bound"], report["upper_bound"], report["decision"]) == (20, 100, "UNRESOLVED")


@pytest.mark.parametrize("baseline,selected,rows,threshold", [
    ([], IDS, [], Fraction(4, 5)),
    (["x", "x"], ["x"], [], Fraction(4, 5)),
    (IDS, [], [], Fraction(4, 5)),
    (IDS, [IDS[0], IDS[0]], [], Fraction(4, 5)),
    (IDS, ["unknown"], [], Fraction(4, 5)),
    (IDS, IDS[:1], [{"check_id": IDS[1], "status": "Pass"}], Fraction(4, 5)),
    (IDS, IDS[:1], records("POOOO") * 2, Fraction(4, 5)),
    (IDS, IDS[:1], [{"check_id": IDS[0], "status": "Unknown"}], Fraction(4, 5)),
    (IDS, IDS[:1], [{"check_id": IDS[0], "status": []}], Fraction(4, 5)),
    (IDS, IDS[:1], [], Fraction(0)),
    (IDS, IDS[:1], [], Fraction(6, 5)),
    (IDS, IDS[:1], [], 0.8),
])
def test_invalid_inputs_rejected(baseline, selected, rows, threshold):
    with pytest.raises(ValueError):
        assess_evidence(baseline, selected, rows, threshold)


def test_exact_threshold_comparison_precedes_display_rounding():
    threshold = Fraction(80000000001, 100000000000)
    assert assess_evidence(IDS, IDS, records("PPPPE"), threshold)["decision"] == "UNRESOLVED"
    assert assess_evidence(IDS, IDS, records("PPPPE"))["decision"] == "ABOVE"


def save(tmp_path, rows, context=None):
    path = tmp_path / "scans.db"
    sid = save_scan(hostname="TEST", results=rows, summary=calculate_score(rows),
                    started_at_utc=NOW, completed_at_utc=NOW,
                    database_path=path, evidence_context=context)
    return get_scan(sid, path), path


def test_sqlite_roundtrip_uses_snapshot_after_catalog_changes(tmp_path):
    catalog = load_catalog()
    context = make_context(catalog, list(IDS[:1]))
    scan, path = save(tmp_path, records("POOOO"), context)
    catalog["checks"] = catalog["checks"][:1]
    assert scan["evidence_summary"]["baseline_count"] == 5
    assert scan["evidence_summary"]["decision"] == "UNRESOLVED"
    assert scan["evidence_context"] == context
    # Corrupt derived fields cannot change the report because it recomputes.
    scan["evidence_summary"]["decision"] = "ABOVE"
    report = build_html_report(scan)
    assert "<strong>UNRESOLVED</strong>" in report
    assert "20.00% to 100.00%" in report
    assert "Omitted required checks" in report
    assert context["catalog_sha256"] in report


def test_old_scan_has_no_invented_historical_baseline(tmp_path):
    scan, _ = save(tmp_path, records("POOOO"))
    assert "evidence_context" not in scan
    assert "Baseline evidence completeness" not in build_html_report(scan)


def test_report_escapes_baseline_and_omitted_id(tmp_path):
    catalog = load_catalog()
    catalog["catalog_version"] = '<script>alert("version")</script>'
    catalog["checks"][1]["id"] = '<img src=x onerror="bad()">'
    context = make_context(catalog, list(IDS[:1]))
    scan, _ = save(tmp_path, records("POOOO"), context)
    report = build_html_report(scan)
    assert "<script>" not in report and "<img src=x" not in report
    assert "&lt;script&gt;" in report and "&lt;img src=x" in report


def test_inconsistent_context_is_rejected_before_write(tmp_path):
    context = make_context(load_catalog(), list(IDS))
    with pytest.raises(DatabaseError, match="Selected records must be present"):
        save(tmp_path, records("POOOO"), context)
    context["decision_version"] = "future"
    with pytest.raises(ValueError, match="version"):
        assess_context(context, records("PPPPP"))


def test_local_scan_persists_context_and_report(tmp_path):
    import app
    db = tmp_path / "workflow.db"
    def save_local(**kwargs):
        return save_scan(**kwargs, database_path=db)
    with patch("app.run_check", return_value=records("POOOO")[0]), \
         patch("app.save_scan", side_effect=save_local), \
         patch("app.get_scan", side_effect=lambda sid: get_scan(sid, db)), \
         patch("app.write_html_report", side_effect=lambda scan: tmp_path / "report.html") as report:
        outcome = app.run_local_scan(IDS[:1])
    assert outcome["scan"]["evidence_summary"]["baseline_coverage"] == 20
    report.assert_called_once()


def test_additive_schema_upgrade_preserves_pre_extension_scan(tmp_path):
    scan, path = save(tmp_path, records("POOOO"))
    with sqlite3.connect(path) as connection:
        connection.execute("DROP TABLE scan_evidence_context")
    initialize_database(path)
    restored = get_scan(scan["scan_id"], path)
    assert restored["results"] == scan["results"]
    assert "evidence_context" not in restored


def test_windows_runner_writes_complete_capture_bundle_with_mock_collectors(tmp_path):
    """Exercise files and report generation, without claiming Windows execution."""
    import hashlib
    import json
    from types import SimpleNamespace
    from tools import validate_windows as runner
    output = tmp_path / "case"
    arguments = ["validate_windows.py", "--case-id", "test", "--snapshot-id", "fixture",
                 "--output", str(output), "--select", IDS[0], "--repeat", "2"]
    with patch.object(runner, "os", SimpleNamespace(name="nt")), \
         patch.object(runner, "reference", return_value={"source": "mock-test"}), \
         patch.object(runner, "run_check", return_value=records("POOOO")[0]), \
         patch.object(runner.sys, "argv", arguments):
        runner.main()
    manifest = json.loads((output / "sha256.json").read_text())
    for name, digest in manifest.items():
        assert hashlib.sha256((output / name).read_bytes()).hexdigest() == digest
    assert len(list(output.glob("repeat-*/*.html"))) == 2
    assert json.loads((output / "case.json").read_text())["review_status"] == "PENDING_INDEPENDENT_REVIEW"
    assert len((output / "manual-review.csv").read_text().splitlines()) == 3


def test_windows_runner_refuses_unsupported_host_before_creating_output(tmp_path):
    from types import SimpleNamespace
    from tools import validate_windows as runner
    output = tmp_path / "no-capture"
    arguments = ["validate_windows.py", "--case-id", "test", "--snapshot-id", "fixture", "--output", str(output)]
    with patch.object(runner, "os", SimpleNamespace(name="posix")), \
         patch.object(runner.sys, "argv", arguments), pytest.raises(SystemExit):
        runner.main()
    assert not output.exists()
