"""SQLite persistence for SecureAudit scan history.

This module stores scan summaries and their individual technical-assessment
results. It deliberately contains no GUI code, allowing the same persistence
logic to be reused later by a desktop interface or FastAPI service.
"""

from __future__ import annotations

import json
import sqlite3
import uuid
from collections.abc import Mapping, Sequence
from contextlib import closing
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Final


DEFAULT_DATABASE_PATH: Final[Path] = (
    Path(__file__).resolve().parents[1] / "data" / "secureaudit.db"
)

ALLOWED_STATUSES: Final[frozenset[str]] = frozenset(
    {
        "Pass",
        "Fail",
        "Error",
    }
)


class DatabaseError(RuntimeError):
    """Raised when SecureAudit data cannot be stored or retrieved safely."""


def _utc_now() -> str:
    """Return the current UTC timestamp in ISO 8601 format."""

    return datetime.now(UTC).isoformat()


def _parse_utc_timestamp(
    value: str,
    field_name: str,
) -> datetime:
    """Parse and validate an ISO 8601 timezone-aware timestamp."""

    try:
        parsed = datetime.fromisoformat(value)
    except ValueError as exc:
        raise DatabaseError(
            f"{field_name!r} must be a valid ISO 8601 timestamp."
        ) from exc

    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise DatabaseError(
            f"{field_name!r} must include timezone information."
        )

    return parsed.astimezone(UTC)
    """Return the current UTC timestamp in ISO 8601 format."""

    return datetime.now(UTC).isoformat()


def _connect(database_path: str | Path) -> sqlite3.Connection:
    """Create a configured SQLite connection."""

    path = Path(database_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")

    return connection


def initialize_database(
    database_path: str | Path = DEFAULT_DATABASE_PATH,
) -> None:
    """Create the SecureAudit database schema when it does not exist."""

    schema = """
    CREATE TABLE IF NOT EXISTS scans (
        scan_id TEXT PRIMARY KEY,
        started_at_utc TEXT NOT NULL,
        completed_at_utc TEXT NOT NULL,
        hostname TEXT NOT NULL,
        selected_count INTEGER NOT NULL CHECK (selected_count >= 0),
        passed_count INTEGER NOT NULL CHECK (passed_count >= 0),
        failed_count INTEGER NOT NULL CHECK (failed_count >= 0),
        error_count INTEGER NOT NULL CHECK (error_count >= 0),
        assessed_count INTEGER NOT NULL CHECK (assessed_count >= 0),
        unassessed_count INTEGER NOT NULL CHECK (unassessed_count >= 0),
        compliance_score REAL,
        coverage_percentage REAL NOT NULL
            CHECK (coverage_percentage >= 0 AND coverage_percentage <= 100),
        CHECK (
            compliance_score IS NULL
            OR (
                compliance_score >= 0
                AND compliance_score <= 100
            )
        ),
        CHECK (
            selected_count =
            passed_count + failed_count + error_count
        ),
        CHECK (
            assessed_count =
            passed_count + failed_count
        ),
        CHECK (
            unassessed_count = error_count
        )
    );

    CREATE TABLE IF NOT EXISTS scan_results (
        result_id INTEGER PRIMARY KEY AUTOINCREMENT,
        scan_id TEXT NOT NULL,
        check_id TEXT NOT NULL,
        check_name TEXT NOT NULL,
        expected_value TEXT NOT NULL,
        observed_value TEXT NOT NULL,
        status TEXT NOT NULL
            CHECK (status IN ('Pass', 'Fail', 'Error')),
        evidence_json TEXT NOT NULL,
        error_message TEXT,
        timestamp_utc TEXT NOT NULL,
        FOREIGN KEY (scan_id)
            REFERENCES scans(scan_id)
            ON DELETE CASCADE,
        UNIQUE (scan_id, check_id)
    );

    CREATE INDEX IF NOT EXISTS idx_scans_completed_at
        ON scans(completed_at_utc DESC);

    CREATE INDEX IF NOT EXISTS idx_scan_results_scan_id
        ON scan_results(scan_id);
    """

    try:
        with closing(_connect(database_path)) as connection:
            connection.executescript(schema)
            connection.commit()
    except sqlite3.Error as exc:
        raise DatabaseError(
            f"Could not initialize SecureAudit database: {exc}"
        ) from exc


def _require_non_empty_string(
    value: Any,
    field_name: str,
) -> str:
    """Validate and return a required non-empty string."""

    if not isinstance(value, str) or not value.strip():
        raise DatabaseError(
            f"{field_name!r} must be a non-empty string."
        )

    return value


def _validate_summary(
    summary: Mapping[str, Any],
) -> None:
    """Validate the scoring summary before opening a write transaction."""

    required_fields = (
        "selected_count",
        "passed_count",
        "failed_count",
        "error_count",
        "assessed_count",
        "unassessed_count",
        "compliance_score",
        "coverage_percentage",
    )

    for field_name in required_fields:
        if field_name not in summary:
            raise DatabaseError(
                f"Scoring summary is missing {field_name!r}."
            )

    integer_fields = (
        "selected_count",
        "passed_count",
        "failed_count",
        "error_count",
        "assessed_count",
        "unassessed_count",
    )

    for field_name in integer_fields:
        value = summary[field_name]

        if (
            not isinstance(value, int)
            or isinstance(value, bool)
            or value < 0
        ):
            raise DatabaseError(
                f"Scoring summary field {field_name!r} "
                "must be a non-negative integer."
            )

    selected_count = summary["selected_count"]
    passed_count = summary["passed_count"]
    failed_count = summary["failed_count"]
    error_count = summary["error_count"]
    assessed_count = summary["assessed_count"]
    unassessed_count = summary["unassessed_count"]

    if selected_count != passed_count + failed_count + error_count:
        raise DatabaseError(
            "Scoring summary counts are inconsistent."
        )

    if assessed_count != passed_count + failed_count:
        raise DatabaseError(
            "Scoring summary assessed count is inconsistent."
        )

    if unassessed_count != error_count:
        raise DatabaseError(
            "Scoring summary unassessed count is inconsistent."
        )

    compliance_score = summary["compliance_score"]

    if compliance_score is not None:
        if (
            not isinstance(compliance_score, (int, float))
            or isinstance(compliance_score, bool)
            or not 0 <= compliance_score <= 100
        ):
            raise DatabaseError(
                "Compliance score must be null or between 0 and 100."
            )

    coverage_percentage = summary["coverage_percentage"]

    if (
        not isinstance(coverage_percentage, (int, float))
        or isinstance(coverage_percentage, bool)
        or not 0 <= coverage_percentage <= 100
    ):
        raise DatabaseError(
            "Coverage percentage must be between 0 and 100."
        )


def _validate_result(
    result: Mapping[str, Any],
    index: int,
) -> None:
    """Validate one normalized scanner result."""

    required_string_fields = (
        "check_id",
        "check_name",
        "expected_value",
        "observed_value",
        "status",
        "timestamp_utc",
    )

    for field_name in required_string_fields:
        if field_name not in result:
            raise DatabaseError(
                f"Result at index {index} is missing {field_name!r}."
            )

        _require_non_empty_string(
            result[field_name],
            f"result[{index}].{field_name}",
        )

    if result["status"] not in ALLOWED_STATUSES:
        raise DatabaseError(
            f"Result at index {index} has unsupported status: "
            f"{result['status']!r}"
        )

    if "evidence" not in result:
        raise DatabaseError(
            f"Result at index {index} is missing 'evidence'."
        )

    try:
        json.dumps(
            result["evidence"],
            ensure_ascii=False,
            allow_nan=False,
        )
    except (TypeError, ValueError) as exc:
        raise DatabaseError(
            f"Result at index {index} contains "
            "non-JSON-serializable evidence."
        ) from exc

    error_message = result.get("error_message")

    if error_message is not None and not isinstance(error_message, str):
        raise DatabaseError(
            f"Result at index {index} has an invalid error_message."
        )


def save_scan(
    *,
    hostname: str,
    results: Sequence[Mapping[str, Any]],
    summary: Mapping[str, Any],
    started_at_utc: str,
    completed_at_utc: str | None = None,
    scan_id: str | None = None,
    database_path: str | Path = DEFAULT_DATABASE_PATH,
) -> str:
    """Store one complete scan and return its scan identifier.

    The scan summary and all result rows are inserted in one transaction.
    A failure while inserting any result rolls back the entire scan.
    """

    hostname = _require_non_empty_string(hostname, "hostname")

    started_at_utc = _require_non_empty_string(
        started_at_utc,
        "started_at_utc",
    )
    started_at = _parse_utc_timestamp(
        started_at_utc,
        "started_at_utc",
    )

    if completed_at_utc is None:
        completed_at_utc = _utc_now()
    else:
        completed_at_utc = _require_non_empty_string(
            completed_at_utc,
            "completed_at_utc",
        )

    completed_at = _parse_utc_timestamp(
        completed_at_utc,
        "completed_at_utc",
    )

    if completed_at < started_at:
        raise DatabaseError(
            "completed_at_utc cannot be earlier than started_at_utc."
        )

    if scan_id is None:
        scan_id = str(uuid.uuid4())
    else:
        scan_id = _require_non_empty_string(
            scan_id,
            "scan_id",
        )

    if isinstance(results, (str, bytes, Mapping)):
        raise DatabaseError(
            "Results must be a sequence of scanner-result mappings."
        )

    result_list = list(results)

    _validate_summary(summary)

    if summary["selected_count"] != len(result_list):
        raise DatabaseError(
            "Scoring summary selected count does not match result count."
        )

    seen_check_ids: set[str] = set()

    for index, result in enumerate(result_list):
        if not isinstance(result, Mapping):
            raise DatabaseError(
                f"Result at index {index} must be a mapping."
            )

        _validate_result(result, index)

        check_id = result["check_id"]

        if check_id in seen_check_ids:
            raise DatabaseError(
                f"Duplicate check ID in scan results: {check_id!r}"
            )

        seen_check_ids.add(check_id)

    initialize_database(database_path)

    insert_scan_sql = """
    INSERT INTO scans (
        scan_id,
        started_at_utc,
        completed_at_utc,
        hostname,
        selected_count,
        passed_count,
        failed_count,
        error_count,
        assessed_count,
        unassessed_count,
        compliance_score,
        coverage_percentage
    )
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """

    insert_result_sql = """
    INSERT INTO scan_results (
        scan_id,
        check_id,
        check_name,
        expected_value,
        observed_value,
        status,
        evidence_json,
        error_message,
        timestamp_utc
    )
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """

    try:
        with closing(_connect(database_path)) as connection:
            with connection:
                connection.execute(
                    insert_scan_sql,
                    (
                        scan_id,
                        started_at_utc,
                        completed_at_utc,
                        hostname,
                        summary["selected_count"],
                        summary["passed_count"],
                        summary["failed_count"],
                        summary["error_count"],
                        summary["assessed_count"],
                        summary["unassessed_count"],
                        summary["compliance_score"],
                        summary["coverage_percentage"],
                    ),
                )

                for result in result_list:
                    connection.execute(
                        insert_result_sql,
                        (
                            scan_id,
                            result["check_id"],
                            result["check_name"],
                            result["expected_value"],
                            result["observed_value"],
                            result["status"],
                            json.dumps(
                                result["evidence"],
                                ensure_ascii=False,
                                allow_nan=False,
                                separators=(",", ":"),
                            ),
                            result.get("error_message"),
                            result["timestamp_utc"],
                        ),
                    )
    except sqlite3.Error as exc:
        raise DatabaseError(
            f"Could not store scan {scan_id!r}: {exc}"
        ) from exc

    return scan_id


def get_scan(
    scan_id: str,
    database_path: str | Path = DEFAULT_DATABASE_PATH,
) -> dict[str, Any] | None:
    """Return one stored scan with its results, or ``None`` if absent."""

    scan_id = _require_non_empty_string(scan_id, "scan_id")

    initialize_database(database_path)

    scan_sql = """
    SELECT *
    FROM scans
    WHERE scan_id = ?
    """

    results_sql = """
    SELECT
        check_id,
        check_name,
        expected_value,
        observed_value,
        status,
        evidence_json,
        error_message,
        timestamp_utc
    FROM scan_results
    WHERE scan_id = ?
    ORDER BY result_id ASC
    """

    try:
        with closing(_connect(database_path)) as connection:
            scan_row = connection.execute(
                scan_sql,
                (scan_id,),
            ).fetchone()

            if scan_row is None:
                return None

            result_rows = connection.execute(
                results_sql,
                (scan_id,),
            ).fetchall()
    except sqlite3.Error as exc:
        raise DatabaseError(
            f"Could not retrieve scan {scan_id!r}: {exc}"
        ) from exc

    scan = dict(scan_row)
    scan["results"] = []

    for row in result_rows:
        result = dict(row)
        evidence_json = result.pop("evidence_json")

        try:
            result["evidence"] = json.loads(evidence_json)
        except json.JSONDecodeError as exc:
            raise DatabaseError(
                f"Stored evidence for scan {scan_id!r} is invalid JSON."
            ) from exc

        scan["results"].append(result)

    return scan


def list_scans(
    database_path: str | Path = DEFAULT_DATABASE_PATH,
    *,
    limit: int = 50,
) -> list[dict[str, Any]]:
    """Return recent scan summaries, newest first."""

    if (
        not isinstance(limit, int)
        or isinstance(limit, bool)
        or limit < 1
        or limit > 1000
    ):
        raise DatabaseError(
            "Limit must be an integer between 1 and 1000."
        )

    initialize_database(database_path)

    query = """
    SELECT *
    FROM scans
    ORDER BY completed_at_utc DESC, scan_id DESC
    LIMIT ?
    """

    try:
        with closing(_connect(database_path)) as connection:
            rows = connection.execute(
                query,
                (limit,),
            ).fetchall()
    except sqlite3.Error as exc:
        raise DatabaseError(
            f"Could not list stored scans: {exc}"
        ) from exc

    return [dict(row) for row in rows]