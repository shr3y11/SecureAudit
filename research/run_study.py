"""Reproduce the finite-state SecureAudit reporting study using Python 3.10+.

This program evaluates an abstract result model derived from development logs.
It does not run Windows commands or measure the SecureAudit executable.
"""

from __future__ import annotations

import csv
import hashlib
import itertools
import json
import platform
import sys
from collections import Counter
from fractions import Fraction
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "results"
CHECKS = ("WIN-FW-001", "WIN-DEF-001", "WIN-BL-001", "WIN-GUEST-001", "WIN-SMB1-001")
THRESHOLDS = (Fraction(3, 5), Fraction(4, 5), Fraction(1))
STATUS = {"Pass": "P", "Fail": "F", "Error": "E"}


def metrics(states: tuple[str, ...]) -> dict:
    if not states or any(s not in {"P", "F", "E", "O"} for s in states):
        raise ValueError("States must be a nonempty tuple of P, F, E, O")
    c = Counter(states)
    n = len(states)
    p, f, e, o = (c[s] for s in "PFEO")
    s, a = p + f + e, p + f
    return {
        "P": p, "F": f, "E": e, "O": o, "N": n, "S": s,
        "R": Fraction(p, a) if a else None,
        "Cs": Fraction(a, s) if s else None,
        "Cc": Fraction(a, n),
        "L": Fraction(p, n), "U": Fraction(p + e + o, n),
    }


def decision(m: dict, threshold: Fraction) -> str:
    if not 0 < threshold <= 1:
        raise ValueError("Threshold must be in (0, 1]")
    if m["L"] >= threshold:
        return "ABOVE"
    if m["U"] < threshold:
        return "BELOW"
    return "UNRESOLVED"


def completions(states: tuple[str, ...]):
    # Independent oracle: replace each unresolved position with each binary state.
    positions = [i for i, s in enumerate(states) if s in "EO"]
    for values in itertools.product("PF", repeat=len(positions)):
        completed = list(states)
        for i, value in zip(positions, values):
            completed[i] = value
        yield tuple(completed)


def evidence_report(catalog: tuple[str, ...], selected: tuple[str, ...], results: list[dict],
                    threshold: Fraction = Fraction(4, 5)) -> dict:
    """Offline adapter for records in SecureAudit's documented JSON contract.

    Reject inconsistent IDs; synthesize Error for selected IDs with absent records.
    Omitted controls remain members of the fixed audit baseline.
    """
    if not catalog or len(set(catalog)) != len(catalog):
        raise ValueError("Catalog must contain unique IDs")
    if not selected or len(set(selected)) != len(selected) or not set(selected) <= set(catalog):
        raise ValueError("Selection must be nonempty, unique, and within the catalog")
    by_id = {}
    for row in results:
        cid = row["check_id"]
        if cid not in selected or cid in by_id or row["status"] not in STATUS:
            raise ValueError("Unexpected ID, duplicate result, or unsupported status")
        by_id[cid] = row
    states = tuple("O" if cid not in selected else STATUS[by_id[cid]["status"]]
                   if cid in by_id else "E" for cid in catalog)
    m = metrics(states)
    return {"states": "".join(states), "decision": decision(m, threshold),
            "missing_selected_records": [cid for cid in selected if cid not in by_id],
            **{key: number(value) for key, value in m.items()}}


def number(value):
    return round(float(value) * 100, 8) if isinstance(value, Fraction) else value


def write_csv(path: Path, rows: list[dict]):
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def evaluate_space(alphabet: str, skip_all_omitted: bool) -> tuple[list[dict], list[dict], dict]:
    rows, summaries = [], {int(t * 100): Counter() for t in THRESHOLDS}
    completions_checked = oracle_mismatches = containment_violations = 0
    count_classes = set()
    for states in itertools.product(alphabet, repeat=5):
        if skip_all_omitted and set(states) == {"O"}:
            continue
        m = metrics(states)
        count_classes.add(tuple(m[s] for s in "PFEO"))
        truths = [Fraction(c.count("P"), 5) for c in completions(states)]
        completions_checked += len(truths)
        containment_violations += sum(not m["L"] <= t <= m["U"] for t in truths)
        assert min(truths) == m["L"] and max(truths) == m["U"], states
        row = {"states": "".join(states), **{key: number(value) for key, value in m.items()}}
        for threshold in THRESHOLDS:
            key = int(threshold * 100)
            summary = summaries[key]
            summary["states"] += 1
            label = decision(m, threshold)
            oracle = ("ABOVE" if all(t >= threshold for t in truths) else
                      "BELOW" if all(t < threshold for t in truths) else "UNRESOLVED")
            oracle_mismatches += label != oracle
            row[f"decision_{key}"] = label
            summary[label] += 1
            if m["R"] is None:
                summary["rate_undefined"] += 1
            elif m["R"] >= threshold:
                summary["rate_positive"] += 1
                summary["unsupported_positive"] += (m["L"] < threshold)
            else:
                summary["rate_negative"] += 1
                summary["unsupported_negative"] += (m["U"] >= threshold)
            selected_gate = m["R"] is not None and m["R"] >= threshold and m["Cs"] == 1
            catalog_gate = m["R"] is not None and m["R"] >= threshold and m["Cc"] == 1
            if selected_gate:
                summary["selected_gate_positive"] += 1
                summary["selected_gate_unsupported"] += (m["L"] < threshold)
            if catalog_gate:
                summary["catalog_gate_positive"] += 1
            if label == "ABOVE" and not catalog_gate:
                summary["stable_positive_with_incomplete_catalog"] += 1
        rows.append(row)
    summary_rows = [{"threshold_percent": key, **dict(value)} for key, value in summaries.items()]
    # Fill zero counters so the CSV schema is stable across thresholds.
    keys = sorted(set().union(*(set(row) for row in summary_rows)))
    summary_rows = [{key: row.get(key, 0) for key in keys} for row in summary_rows]
    return rows, summary_rows, {
        "states": len(rows), "count_classes": len(count_classes),
        "binary_completions_checked": completions_checked,
        "oracle_classifications_checked": len(rows) * len(THRESHOLDS),
        "oracle_mismatches": oracle_mismatches,
        "containment_violations": containment_violations,
    }


def selection_experiment() -> tuple[list[dict], list[dict]]:
    rows = []
    summary = {int(t * 100): Counter() for t in THRESHOLDS}
    for truth in itertools.product("PF", repeat=5):
        complete_rate = Fraction(truth.count("P"), 5)
        for mask in itertools.product((False, True), repeat=5):
            if not any(mask):
                continue
            observed = tuple(s if include else "O" for s, include in zip(truth, mask))
            m = metrics(observed)
            row = {"truth": "".join(truth), "observed": "".join(observed),
                   "complete_rate": number(complete_rate), "selected_rate": number(m["R"]),
                   "overstatement_pp": number(m["R"] - complete_rate),
                   "selected_coverage": number(m["Cs"]), "catalog_coverage": number(m["Cc"])}
            for threshold in THRESHOLDS:
                key = int(threshold * 100)
                baseline = m["R"] >= threshold
                actual = complete_rate >= threshold
                summary[key]["pairs"] += 1
                summary[key]["positive_disagreements"] += baseline and not actual
                summary[key]["negative_disagreements"] += not baseline and actual
                safe = decision(m, threshold)
                summary[key]["incorrect_stable_decisions"] += (
                    safe == "ABOVE" and not actual or safe == "BELOW" and actual)
                row[f"decision_{key}"] = safe
            rows.append(row)
    return rows, [{"threshold_percent": key, **dict(value)} for key, value in summary.items()]


def resolution_checks() -> dict:
    edges = violations = reversals = 0
    for states in itertools.product("PFEO", repeat=5):
        if set(states) == {"O"}:
            continue
        before = metrics(states)
        for i, state in enumerate(states):
            if state not in "EO":
                continue
            for replacement in "PF":
                new = list(states)
                new[i] = replacement
                after = metrics(tuple(new))
                edges += 1
                violations += not (after["L"] >= before["L"] and after["U"] <= before["U"])
                for threshold in THRESHOLDS:
                    first, second = decision(before, threshold), decision(after, threshold)
                    reversals += first != "UNRESOLVED" and first != second
    return {"resolution_edges": edges, "nesting_violations": violations, "stable_decision_reversals": reversals}


def adapter_checks() -> dict:
    passed = 0
    for _ in (0,):
        row = evidence_report(CHECKS, CHECKS, [{"check_id": c, "status": "Pass"} for c in CHECKS[:3]])
        assert row["states"] == "PPPEE" and row["decision"] == "UNRESOLVED"
        assert row["L"] == 60 and row["U"] == 100 and len(row["missing_selected_records"]) == 2
        passed += 1
        row = evidence_report(CHECKS, CHECKS[:1], [{"check_id": CHECKS[0], "status": "Pass"}])
        assert row["states"] == "POOOO" and row["Cs"] == 100 and row["Cc"] == 20
        passed += 1
    invalid = [
        (CHECKS, (), []),
        (CHECKS, (CHECKS[0], CHECKS[0]), []),
        (CHECKS, ("OTHER",), []),
        (CHECKS, CHECKS[:1], [{"check_id": CHECKS[1], "status": "Pass"}]),
        (CHECKS, CHECKS[:1], [{"check_id": CHECKS[0], "status": "Pass"}] * 2),
        (CHECKS, CHECKS[:1], [{"check_id": CHECKS[0], "status": "Unknown"}]),
        ((CHECKS[0], CHECKS[0]), CHECKS[:1], []),
    ]
    for args in invalid:
        try:
            evidence_report(*args)
        except ValueError:
            passed += 1
        else:
            raise AssertionError("Invalid records were accepted")
    return {"adapter_cases": passed, "valid_cases": 2, "rejected_invalid_cases": 7}


def main():
    DATA.mkdir(exist_ok=True)
    full_rows, full_summary, full_verify = evaluate_space("PFE", False)
    all_rows, all_summary, all_verify = evaluate_space("PFEO", True)
    selection_rows, selection_summary = selection_experiment()
    resolution = resolution_checks()
    adapter = adapter_checks()
    assert full_verify["states"] == 243 and full_verify["count_classes"] == 21
    assert all_verify["states"] == 1023 and all_verify["count_classes"] == 55
    assert full_verify["binary_completions_checked"] == 1024
    assert all_verify["binary_completions_checked"] == 7744
    assert len(selection_rows) == 992 and resolution["resolution_edges"] == 5110
    for v in (full_verify, all_verify):
        assert v["oracle_mismatches"] == v["containment_violations"] == 0
    assert resolution["nesting_violations"] == resolution["stable_decision_reversals"] == 0
    assert all(row["incorrect_stable_decisions"] == 0 for row in selection_summary)
    for filename, rows in [
        ("full_selection_states.csv", full_rows), ("all_selection_states.csv", all_rows),
        ("full_selection_summary.csv", full_summary), ("all_selection_summary.csv", all_summary),
        ("selection_truth_pairs.csv", selection_rows), ("selection_truth_summary.csv", selection_summary),
    ]:
        write_csv(DATA / filename, rows)
    summary = {
        "study_type": "finite-state computational evaluation; no Windows scans",
        "python_version": platform.python_version(), "platform": sys.platform,
        "catalog": CHECKS, "thresholds_percent": [60, 80, 100],
        "full_selection": full_summary, "selection_and_errors": all_summary,
        "selection_truth": selection_summary,
        "max_selection_overstatement_pp": max(row["overstatement_pp"] for row in selection_rows),
        "verification": {"full_selection": full_verify, "selection_and_errors": all_verify,
                         "resolution": resolution, "adapter": adapter},
    }
    (DATA / "summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    files = [Path(__file__), *sorted(DATA.glob("*.csv")), DATA / "summary.json"]
    hashes = {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
    (DATA / "sha256.json").write_text(json.dumps(hashes, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
