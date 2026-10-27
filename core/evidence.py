"""Exact checklist bounds for unresolved evidence in a fixed approved baseline.

These aggregate labels concern a technical checklist threshold, not an audit
opinion, a probability, or a mandatory-control decision. P/F readings are
assumed correct. Errors and omitted baseline members may resolve either way.
"""
from collections.abc import Mapping
from fractions import Fraction
import hashlib
import json
import re

DECISION_VERSION = "1.0.0"
STATUS = {"Pass": "P", "Fail": "F", "Error": "E"}


def _ids(values, name):
    if not isinstance(values, (list, tuple)) or not values:
        raise ValueError(f"{name} must be a nonempty list of IDs")
    if any(not isinstance(v, str) or not v.strip() for v in values):
        raise ValueError(f"{name} contains an invalid ID")
    if len(values) != len(set(values)):
        raise ValueError(f"{name} contains duplicate IDs")
    return tuple(values)


def assess_evidence(baseline_ids, selected_ids, results, threshold=Fraction(4, 5)):
    """Return exact bounds before rounding any display percentages.

    A missing selected record becomes E and is listed separately. An unselected
    baseline member becomes O. Reject contradictory or out-of-scope records.
    """
    baseline = _ids(baseline_ids, "Baseline")
    selected = _ids(selected_ids, "Selection")
    if not set(selected) <= set(baseline):
        raise ValueError("Selection contains IDs outside the baseline")
    if not isinstance(threshold, Fraction) or not 0 < threshold <= 1:
        raise ValueError("Threshold must be a Fraction in (0, 1]")
    if not isinstance(results, (list, tuple)):
        raise ValueError("Results must be a list of mappings")
    by_id = {}
    for row in results:
        if not isinstance(row, Mapping):
            raise ValueError("Each result must be a mapping")
        cid, status = row.get("check_id"), row.get("status")
        if not isinstance(cid, str) or cid not in selected or cid in by_id:
            raise ValueError("Unexpected or duplicate result ID")
        if not isinstance(status, str) or status not in STATUS:
            raise ValueError("Unsupported result status")
        by_id[cid] = STATUS[status]
    states = {cid: "O" if cid not in selected else by_id.get(cid, "E")
              for cid in baseline}
    p, f, e, o = (list(states.values()).count(state) for state in "PFEO")
    n, s, a = len(baseline), len(selected), p + f
    lower, upper = Fraction(p, n), Fraction(p + e + o, n)
    decision = "ABOVE" if lower >= threshold else "BELOW" if upper < threshold else "UNRESOLVED"
    percent = lambda value: round(float(value * 100), 8)
    return {"decision_version": DECISION_VERSION, "states": states,
            "baseline_count": n, "selected_count": s, "passed_count": p,
            "failed_count": f, "error_count": e, "omitted_count": o,
            "missing_selected_records": [cid for cid in selected if cid not in by_id],
            "assessed_pass_rate": percent(Fraction(p, a)) if a else None,
            "selected_coverage": percent(Fraction(a, s)),
            "baseline_coverage": percent(Fraction(a, n)),
            "lower_bound": percent(lower), "upper_bound": percent(upper),
            "threshold_percentage": percent(threshold), "decision": decision}


def make_context(catalog, selected_ids, threshold=Fraction(4, 5)):
    """Snapshot enabled catalog membership; selection cannot shrink baseline.

    Applicability changes require an approved, versioned catalog. The digest
    identifies catalog bytes after canonical JSON encoding, not authenticity.
    """
    canonical = json.dumps(catalog, sort_keys=True, separators=(",", ":"), allow_nan=False)
    baseline = [c["id"] for c in catalog["checks"] if c.get("enabled") is True]
    assess_evidence(baseline, selected_ids, [], threshold)
    return {"decision_version": DECISION_VERSION,
            "baseline_version": str(catalog["catalog_version"]),
            "catalog_sha256": hashlib.sha256(canonical.encode("utf-8")).hexdigest(),
            "baseline_ids": baseline, "selected_ids": list(selected_ids),
            "threshold_numerator": threshold.numerator,
            "threshold_denominator": threshold.denominator}


def assess_context(context, results):
    """Validate persisted context and recompute derived values from records."""
    if not isinstance(context, Mapping) or context.get("decision_version") != DECISION_VERSION:
        raise ValueError("Unsupported evidence decision version")
    if not isinstance(context.get("baseline_version"), str) or not context["baseline_version"].strip():
        raise ValueError("Baseline version is required")
    if not isinstance(context.get("catalog_sha256"), str) or not re.fullmatch(r"[0-9a-f]{64}", context["catalog_sha256"]):
        raise ValueError("Invalid catalog digest")
    numerator, denominator = context.get("threshold_numerator"), context.get("threshold_denominator")
    if type(numerator) is not int or type(denominator) is not int or denominator <= 0:
        raise ValueError("Invalid rational threshold")
    summary = assess_evidence(context.get("baseline_ids"), context.get("selected_ids"),
                              results, Fraction(numerator, denominator))
    return {**summary, "baseline_version": context["baseline_version"],
            "catalog_sha256": context["catalog_sha256"]}
