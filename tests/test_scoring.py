"""Tests for the SecureAudit compliance scoring model."""

from __future__ import annotations

import pytest

from core.scoring import ScoringError, calculate_score


def result(status: str) -> dict[str, str]:
    """Return a minimal normalized scanner result for scoring tests."""

    return {
        "status": status,
    }


def test_score_excludes_errors_from_compliance_denominator() -> None:
    """Three passes, one failure, and one error should score 75 percent."""

    summary = calculate_score(
        [
            result("Pass"),
            result("Pass"),
            result("Pass"),
            result("Fail"),
            result("Error"),
        ]
    )

    assert summary == {
        "selected_count": 5,
        "passed_count": 3,
        "failed_count": 1,
        "error_count": 1,
        "assessed_count": 4,
        "unassessed_count": 1,
        "compliance_score": 75.0,
        "coverage_percentage": 80.0,
    }


def test_all_passes_score_one_hundred_percent() -> None:
    """All successfully assessed checks passing should score 100 percent."""

    summary = calculate_score(
        [
            result("Pass"),
            result("Pass"),
            result("Pass"),
        ]
    )

    assert summary["selected_count"] == 3
    assert summary["passed_count"] == 3
    assert summary["failed_count"] == 0
    assert summary["error_count"] == 0
    assert summary["assessed_count"] == 3
    assert summary["compliance_score"] == 100.0
    assert summary["coverage_percentage"] == 100.0


def test_all_failures_score_zero_percent() -> None:
    """Assessed checks that all fail should produce a real zero score."""

    summary = calculate_score(
        [
            result("Fail"),
            result("Fail"),
        ]
    )

    assert summary["passed_count"] == 0
    assert summary["failed_count"] == 2
    assert summary["assessed_count"] == 2
    assert summary["compliance_score"] == 0.0
    assert summary["coverage_percentage"] == 100.0


def test_all_errors_have_no_compliance_score() -> None:
    """No score should be claimed when none of the checks were assessed."""

    summary = calculate_score(
        [
            result("Error"),
            result("Error"),
            result("Error"),
        ]
    )

    assert summary["selected_count"] == 3
    assert summary["passed_count"] == 0
    assert summary["failed_count"] == 0
    assert summary["error_count"] == 3
    assert summary["assessed_count"] == 0
    assert summary["unassessed_count"] == 3
    assert summary["compliance_score"] is None
    assert summary["coverage_percentage"] == 0.0


def test_empty_result_list_is_supported() -> None:
    """No selected checks should produce an empty neutral summary."""

    summary = calculate_score([])

    assert summary == {
        "selected_count": 0,
        "passed_count": 0,
        "failed_count": 0,
        "error_count": 0,
        "assessed_count": 0,
        "unassessed_count": 0,
        "compliance_score": None,
        "coverage_percentage": 0.0,
    }


def test_fractional_score_is_rounded_to_two_decimal_places() -> None:
    """Two passes and one failure should score 66.67 percent."""

    summary = calculate_score(
        [
            result("Pass"),
            result("Pass"),
            result("Fail"),
        ]
    )

    assert summary["compliance_score"] == 66.67
    assert summary["coverage_percentage"] == 100.0


def test_fractional_coverage_is_rounded_to_two_decimal_places() -> None:
    """Two assessed checks out of three should have 66.67 percent coverage."""

    summary = calculate_score(
        [
            result("Pass"),
            result("Fail"),
            result("Error"),
        ]
    )

    assert summary["compliance_score"] == 50.0
    assert summary["coverage_percentage"] == 66.67


def test_generator_input_is_supported() -> None:
    """The scoring function should accept any result iterable."""

    results = (
        result(status)
        for status in [
            "Pass",
            "Fail",
            "Error",
        ]
    )

    summary = calculate_score(results)

    assert summary["selected_count"] == 3
    assert summary["compliance_score"] == 50.0
    assert summary["coverage_percentage"] == 66.67


def test_missing_status_is_rejected() -> None:
    """Every normalized scanner result must contain a status."""

    with pytest.raises(
        ScoringError,
        match="missing the 'status' field",
    ):
        calculate_score(
            [
                {
                    "check_id": "WIN-FW-001",
                }
            ]
        )


def test_unsupported_status_is_rejected() -> None:
    """Unexpected status spelling must not silently affect scoring."""

    with pytest.raises(
        ScoringError,
        match="unsupported status",
    ):
        calculate_score(
            [
                result("Skipped"),
            ]
        )


def test_lowercase_status_is_rejected() -> None:
    """Status values must follow the normalized contract exactly."""

    with pytest.raises(
        ScoringError,
        match="unsupported status",
    ):
        calculate_score(
            [
                result("pass"),
            ]
        )


def test_non_mapping_result_is_rejected() -> None:
    """Each item must be a normalized scanner-result mapping."""

    with pytest.raises(
        ScoringError,
        match="must be a mapping",
    ):
        calculate_score(
            [
                "Pass",
            ]
        )


def test_string_input_is_rejected() -> None:
    """A string must not be treated as an iterable of results."""

    with pytest.raises(
        ScoringError,
        match="iterable of scanner-result mappings",
    ):
        calculate_score("Pass")


def test_mapping_input_is_rejected() -> None:
    """A single dictionary must be wrapped in a result collection."""

    with pytest.raises(
        ScoringError,
        match="iterable of scanner-result mappings",
    ):
        calculate_score(
            {
                "status": "Pass",
            }
        )


def test_non_string_status_is_rejected() -> None:
    """Status must be a normalized string value."""

    with pytest.raises(
        ScoringError,
        match="non-string status",
    ):
        calculate_score(
            [
                {
                    "status": 1,
                }
            ]
        )