"""Compliance scoring for SecureAudit technical assessment results.

The compliance score is based only on successfully assessed checks:

    passed / (passed + failed) * 100

Errored checks are excluded from the compliance-score denominator because
their control state was not determined reliably. They remain visible through
the error count and reduce assessment coverage.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any, Final


ALLOWED_STATUSES: Final[frozenset[str]] = frozenset(
    {
        "Pass",
        "Fail",
        "Error",
    }
)


class ScoringError(ValueError):
    """Raised when assessment results cannot be scored reliably."""


def _round_percentage(value: float) -> float:
    """Round a percentage to two decimal places."""

    return round(value, 2)


def calculate_score(
    results: Iterable[Mapping[str, Any]],
) -> dict[str, int | float | None]:
    """Calculate SecureAudit compliance score and assessment coverage.

    Args:
        results: Iterable of normalized scanner-result mappings. Every result
            must include a status equal to Pass, Fail, or Error.

    Returns:
        A scoring summary containing:

        - selected_count
        - passed_count
        - failed_count
        - error_count
        - assessed_count
        - unassessed_count
        - compliance_score
        - coverage_percentage

        ``compliance_score`` is ``None`` when no checks were successfully
        assessed. Coverage remains calculable when checks were selected.

    Raises:
        ScoringError: If results are malformed or contain unsupported statuses.
    """

    if isinstance(results, (str, bytes, Mapping)):
        raise ScoringError(
            "Results must be an iterable of scanner-result mappings."
        )

    try:
        result_list = list(results)
    except TypeError as exc:
        raise ScoringError(
            "Results must be an iterable of scanner-result mappings."
        ) from exc

    passed_count = 0
    failed_count = 0
    error_count = 0

    for index, result in enumerate(result_list):
        if not isinstance(result, Mapping):
            raise ScoringError(
                f"Result at index {index} must be a mapping."
            )

        if "status" not in result:
            raise ScoringError(
                f"Result at index {index} is missing the 'status' field."
            )

        status = result["status"]

        if not isinstance(status, str):
            raise ScoringError(
                f"Result at index {index} has a non-string status."
            )

        if status not in ALLOWED_STATUSES:
            raise ScoringError(
                f"Result at index {index} contains unsupported status: "
                f"{status!r}"
            )

        if status == "Pass":
            passed_count += 1
        elif status == "Fail":
            failed_count += 1
        else:
            error_count += 1

    selected_count = len(result_list)
    assessed_count = passed_count + failed_count
    unassessed_count = error_count

    if assessed_count == 0:
        compliance_score: float | None = None
    else:
        compliance_score = _round_percentage(
            passed_count / assessed_count * 100
        )

    if selected_count == 0:
        coverage_percentage = 0.0
    else:
        coverage_percentage = _round_percentage(
            assessed_count / selected_count * 100
        )

    return {
        "selected_count": selected_count,
        "passed_count": passed_count,
        "failed_count": failed_count,
        "error_count": error_count,
        "assessed_count": assessed_count,
        "unassessed_count": unassessed_count,
        "compliance_score": compliance_score,
        "coverage_percentage": coverage_percentage,
    }