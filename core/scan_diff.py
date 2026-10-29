"""Compare two stored scans of the same machine (two-scan diff).

The diff is computed from the persisted result records only. When a scan
carries an evidence context (catalog version, catalog SHA-256, rational
threshold, baseline decision), that context is reported alongside, so a
reader can tell whether a change came from the machine or from the
catalog/threshold moving underneath it. Scans without a context simply
report ``None`` — no context is invented for them.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

ALLOWED_STATUSES = frozenset({"Pass", "Fail", "Error"})


def _results_by_id(scan: Mapping[str, Any], label: str) -> dict[str, str]:
    if not isinstance(scan, Mapping) or not isinstance(scan.get("results"), list):
        raise ValueError(f"{label} scan must be a mapping with a results list")
    by_id: dict[str, str] = {}
    for row in scan["results"]:
        if not isinstance(row, Mapping) or row.get("status") not in ALLOWED_STATUSES:
            raise ValueError(f"{label} scan contains an invalid result record")
        check_id = row.get("check_id")
        if not isinstance(check_id, str) or not check_id or check_id in by_id:
            raise ValueError(f"{label} scan contains a missing or duplicate check ID")
        by_id[check_id] = row["status"]
    return by_id


def _context_snapshot(scan: Mapping[str, Any]) -> dict[str, Any] | None:
    context = scan.get("evidence_context")
    if not isinstance(context, Mapping):
        return None
    snapshot = {
        "baseline_version": context.get("baseline_version"),
        "catalog_sha256": context.get("catalog_sha256"),
        "threshold": (
            f"{context['threshold_numerator']}/{context['threshold_denominator']}"
            if isinstance(context.get("threshold_numerator"), int)
            and isinstance(context.get("threshold_denominator"), int)
            else None
        ),
    }
    summary = scan.get("evidence_summary")
    if isinstance(summary, Mapping):
        snapshot["decision"] = summary.get("decision")
        snapshot["lower_bound"] = summary.get("lower_bound")
        snapshot["upper_bound"] = summary.get("upper_bound")
    return snapshot


def diff_scans(previous: Mapping[str, Any], current: Mapping[str, Any]) -> dict[str, Any]:
    """Return per-check transitions and context snapshots for two scans.

    Change kinds: ``fixed`` (Fail/Error -> Pass), ``regressed``
    (Pass -> Fail/Error), ``changed`` (Fail <-> Error), ``unchanged``,
    ``added`` (only in current), ``removed`` (only in previous).
    """

    before = _results_by_id(previous, "Previous")
    after = _results_by_id(current, "Current")

    transitions = []
    counts = {"fixed": 0, "regressed": 0, "changed": 0, "unchanged": 0, "added": 0, "removed": 0}
    for check_id in sorted(set(before) | set(after)):
        old, new = before.get(check_id), after.get(check_id)
        if old is None:
            kind = "added"
        elif new is None:
            kind = "removed"
        elif old == new:
            kind = "unchanged"
        elif new == "Pass":
            kind = "fixed"
        elif old == "Pass":
            kind = "regressed"
        else:
            kind = "changed"
        counts[kind] += 1
        transitions.append({"check_id": check_id, "before": old, "after": new, "change": kind})

    return {
        "previous_scan_id": previous.get("scan_id"),
        "current_scan_id": current.get("scan_id"),
        "previous_context": _context_snapshot(previous),
        "current_context": _context_snapshot(current),
        "counts": counts,
        "transitions": transitions,
    }
