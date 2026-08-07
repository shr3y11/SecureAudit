"""SecureAudit allow-listed PowerShell scanner engine.

This module loads approved checks from ``checks/catalog.json`` and runs only
the PowerShell script associated with a selected catalog check ID.

Security properties:
- No arbitrary PowerShell commands are accepted.
- No user-provided script paths are accepted.
- Check IDs must exist and be enabled in the trusted catalog.
- Resolved scripts must remain inside ``checks/powershell``.
- Script execution has a fixed timeout.
- PowerShell output must be valid JSON.
- Results are normalized into a consistent Python dictionary.
"""

from __future__ import annotations

import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Final

from core.paths import (
    catalog_path as default_catalog_path,
    powershell_directory as default_powershell_directory,
)

DEFAULT_TIMEOUT_SECONDS: Final[int] = 30
ALLOWED_STATUSES: Final[frozenset[str]] = frozenset({"Pass", "Fail", "Error"})

REQUIRED_CATALOG_FIELDS: Final[frozenset[str]] = frozenset(
    {
        "id",
        "name",
        "script",
        "expected_value",
        "enabled",
    }
)

REQUIRED_RESULT_FIELDS: Final[frozenset[str]] = frozenset(
    {
        "check_id",
        "check_name",
        "expected_value",
        "observed_value",
        "status",
        "evidence",
        "error_message",
        "timestamp_utc",
    }
)


class ScannerError(Exception):
    """Base exception for SecureAudit scanner-engine failures."""


class CatalogError(ScannerError):
    """Raised when the approved check catalog is missing or invalid."""


class UnknownCheckError(ScannerError):
    """Raised when a requested check ID is not in the approved catalog."""


class DisabledCheckError(ScannerError):
    """Raised when a requested catalog check is disabled."""


class ScriptSecurityError(ScannerError):
    """Raised when an approved script path violates the scanner boundary."""


class ScriptExecutionError(ScannerError):
    """Raised when PowerShell cannot execute the approved script."""


class ScriptTimeoutError(ScannerError):
    """Raised when an approved scanner script exceeds its timeout."""


class InvalidResultError(ScannerError):
    """Raised when a PowerShell script returns invalid or incomplete JSON."""


def utc_timestamp() -> str:
    """Return the current UTC timestamp using an ISO 8601 representation."""

    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def load_catalog(catalog_path: Path | None = None) -> dict[str, Any]:
    """Load and minimally validate the SecureAudit check catalog.

    Args:
        catalog_path: Optional custom path used mainly for testing. When omitted,
            the repository's ``checks/catalog.json`` file is used.

    Returns:
        The parsed catalog dictionary.

    Raises:
        CatalogError: If the file is missing, unreadable, malformed, or invalid.
    """

    if catalog_path is None:
        resolved_catalog_path = default_catalog_path()
    else:
        resolved_catalog_path = Path(catalog_path)

    path = resolved_catalog_path.resolve()

    if not path.is_file():
        raise CatalogError(f"Check catalog was not found: {path}")

    try:
        with path.open("r", encoding="utf-8-sig") as catalog_file:
            catalog = json.load(catalog_file)
    except json.JSONDecodeError as exc:
        raise CatalogError(
            f"Check catalog contains invalid JSON at line "
            f"{exc.lineno}, column {exc.colno}: {exc.msg}"
        ) from exc
    except OSError as exc:
        raise CatalogError(f"Check catalog could not be read: {exc}") from exc

    if not isinstance(catalog, dict):
        raise CatalogError("Check catalog root must be a JSON object.")

    checks = catalog.get("checks")

    if not isinstance(checks, list):
        raise CatalogError("Check catalog must contain a 'checks' array.")

    seen_ids: set[str] = set()

    for index, check in enumerate(checks):
        if not isinstance(check, dict):
            raise CatalogError(
                f"Catalog check at index {index} must be a JSON object."
            )

        missing_fields = REQUIRED_CATALOG_FIELDS - check.keys()

        if missing_fields:
            missing_text = ", ".join(sorted(missing_fields))
            raise CatalogError(
                f"Catalog check at index {index} is missing required fields: "
                f"{missing_text}"
            )

        check_id = check["id"]

        if not isinstance(check_id, str) or not check_id.strip():
            raise CatalogError(
                f"Catalog check at index {index} has an invalid ID."
            )

        if check_id in seen_ids:
            raise CatalogError(f"Duplicate check ID found in catalog: {check_id}")

        seen_ids.add(check_id)

        if not isinstance(check["script"], str) or not check["script"].strip():
            raise CatalogError(
                f"Catalog check {check_id} has an invalid script filename."
            )

        if not isinstance(check["enabled"], bool):
            raise CatalogError(
                f"Catalog check {check_id} must use a boolean 'enabled' value."
            )

    return catalog


def get_approved_check(
    check_id: str,
    catalog: dict[str, Any],
) -> dict[str, Any]:
    """Return one enabled catalog entry for an exact approved check ID.

    Args:
        check_id: SecureAudit check ID selected by the application.
        catalog: Catalog dictionary returned by :func:`load_catalog`.

    Returns:
        The matching catalog entry.

    Raises:
        UnknownCheckError: If the check ID is absent or invalid.
        DisabledCheckError: If the check exists but is disabled.
    """

    if not isinstance(check_id, str) or not check_id.strip():
        raise UnknownCheckError("A non-empty check ID is required.")

    normalized_id = check_id.strip()

    for check in catalog["checks"]:
        if check["id"] == normalized_id:
            if not check["enabled"]:
                raise DisabledCheckError(
                    f"Check {normalized_id} is disabled in the approved catalog."
                )

            return check

    raise UnknownCheckError(
        f"Check ID is not approved in the catalog: {normalized_id}"
    )


def resolve_approved_script(
    check: dict[str, Any],
    script_directory: Path | None = None,
) -> Path:
    """Resolve a catalog script while enforcing the scripts-directory boundary.

    The catalog stores only filenames. This function rejects absolute paths,
    nested paths, traversal components, non-PowerShell files, missing scripts,
    and any resolved path outside ``checks/powershell``.

    Args:
        check: Approved catalog entry.
        script_directory: Optional scanner directory used mainly for testing.

    Returns:
        The fully resolved approved script path.

    Raises:
        ScriptSecurityError: If the script path is unsafe or invalid.
    """

    if script_directory is None:
        resolved_script_directory = default_powershell_directory()
    else:
        resolved_script_directory = Path(script_directory)

    approved_directory = resolved_script_directory.resolve()

    script_value = check["script"]
    script_name = Path(script_value)

    if script_name.is_absolute():
        raise ScriptSecurityError(
            f"Absolute script paths are prohibited for check {check['id']}."
        )

    if script_name.name != script_value:
        raise ScriptSecurityError(
            f"Nested or traversing script paths are prohibited for "
            f"check {check['id']}: {script_value}"
        )

    if script_name.suffix.lower() != ".ps1":
        raise ScriptSecurityError(
            f"Check {check['id']} does not reference an approved .ps1 file."
        )

    script_path = (approved_directory / script_name).resolve()

    try:
        script_path.relative_to(approved_directory)
    except ValueError as exc:
        raise ScriptSecurityError(
            f"Resolved script escaped the approved scanner directory: "
            f"{script_path}"
        ) from exc

    if not script_path.is_file():
        raise ScriptSecurityError(
            f"Approved script was not found for check {check['id']}: "
            f"{script_path}"
        )

    return script_path


def build_error_result(
    check: dict[str, Any],
    error_message: str,
) -> dict[str, Any]:
    """Create a normalized Error result for a known approved check."""

    return {
        "check_id": check["id"],
        "check_name": check["name"],
        "expected_value": check["expected_value"],
        "observed_value": "Assessment could not be completed",
        "status": "Error",
        "evidence": [],
        "error_message": error_message,
        "timestamp_utc": utc_timestamp(),
    }


def validate_and_normalize_result(
    raw_result: Any,
    expected_check: dict[str, Any],
) -> dict[str, Any]:
    """Validate a script result and return a normalized Python dictionary.

    Args:
        raw_result: Parsed JSON value emitted by the PowerShell script.
        expected_check: Catalog entry that authorized execution.

    Returns:
        A normalized result dictionary.

    Raises:
        InvalidResultError: If the result contract is invalid or inconsistent.
    """

    if not isinstance(raw_result, dict):
        raise InvalidResultError(
            "PowerShell result must be one JSON object."
        )

    missing_fields = REQUIRED_RESULT_FIELDS - raw_result.keys()

    if missing_fields:
        missing_text = ", ".join(sorted(missing_fields))
        raise InvalidResultError(
            f"PowerShell result is missing required fields: {missing_text}"
        )

    if raw_result["check_id"] != expected_check["id"]:
        raise InvalidResultError(
            "PowerShell result check ID does not match the authorized "
            f"catalog check. Expected {expected_check['id']}, received "
            f"{raw_result['check_id']!r}."
        )

    status = raw_result["status"]

    if status not in ALLOWED_STATUSES:
        raise InvalidResultError(
            f"PowerShell result contains unsupported status: {status!r}"
        )

    evidence = raw_result["evidence"]

    if evidence is None:
        evidence = []

    if not isinstance(evidence, list):
        raise InvalidResultError(
            "PowerShell result 'evidence' must be a JSON array."
        )

    error_message = raw_result["error_message"]

    if error_message is None or error_message == "":
        normalized_error: str | None = None
    elif isinstance(error_message, str):
        normalized_error = error_message
    else:
        normalized_error = str(error_message)

    if status == "Error" and not normalized_error:
        normalized_error = "Scanner script returned Error without details."

    return {
        "check_id": raw_result["check_id"],
        "check_name": str(raw_result["check_name"]),
        "expected_value": str(raw_result["expected_value"]),
        "observed_value": str(raw_result["observed_value"]),
        "status": status,
        "evidence": evidence,
        "error_message": normalized_error,
        "timestamp_utc": str(raw_result["timestamp_utc"]),
    }


def execute_powershell_script(
    script_path: Path,
    timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS,
) -> subprocess.CompletedProcess[str]:
    """Execute an approved PowerShell script with a fixed argument list.

    The command does not contain ``shell=True`` and does not concatenate user
    input into a PowerShell expression.

    Args:
        script_path: Previously validated path from
            :func:`resolve_approved_script`.
        timeout_seconds: Maximum execution time in seconds.

    Returns:
        The completed subprocess result.

    Raises:
        ValueError: If the timeout is invalid.
        ScriptTimeoutError: If execution exceeds the timeout.
        ScriptExecutionError: If PowerShell cannot be started.
    """

    if not isinstance(timeout_seconds, int) or timeout_seconds <= 0:
        raise ValueError("timeout_seconds must be a positive integer.")

    command = [
        "powershell.exe",
        "-NoLogo",
        "-NoProfile",
        "-NonInteractive",
        "-ExecutionPolicy",
        "Bypass",
        "-File",
        str(script_path),
    ]

    try:
        return subprocess.run(
            command,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout_seconds,
            check=False,
            shell=False,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
    except subprocess.TimeoutExpired as exc:
        raise ScriptTimeoutError(
            f"Scanner script exceeded the {timeout_seconds}-second timeout."
        ) from exc
    except OSError as exc:
        raise ScriptExecutionError(
            f"PowerShell could not be started: {exc}"
        ) from exc


def parse_script_output(
    process: subprocess.CompletedProcess[str],
) -> Any:
    """Parse one JSON result from completed PowerShell execution.

    Args:
        process: Result returned by :func:`execute_powershell_script`.

    Returns:
        The decoded JSON value.

    Raises:
        ScriptExecutionError: If the process returned a non-zero exit code or
            emitted no standard output.
        InvalidResultError: If standard output is not valid JSON.
    """

    stdout = process.stdout.strip()
    stderr = process.stderr.strip()

    if process.returncode != 0:
        details = stderr or stdout or "No process error details were returned."
        raise ScriptExecutionError(
            f"PowerShell exited with code {process.returncode}: {details}"
        )

    if not stdout:
        details = f" PowerShell error output: {stderr}" if stderr else ""
        raise ScriptExecutionError(
            f"PowerShell script returned no JSON output.{details}"
        )

    try:
        return json.loads(stdout)
    except json.JSONDecodeError as exc:
        raise InvalidResultError(
            f"PowerShell script returned invalid JSON at line "
            f"{exc.lineno}, column {exc.colno}: {exc.msg}"
        ) from exc


def run_check(
    check_id: str,
    *,
    timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS,
    catalog_path: Path | None = None,
    script_directory: Path | None = None,
) -> dict[str, Any]:
    """Run one approved SecureAudit check and return a normalized result.

    Unknown or disabled check IDs are rejected rather than converted into
    scanner results because no approved assessment was authorized.

    Execution, timeout, and invalid-output problems for a known approved check
    are returned as normalized ``Error`` results.

    Args:
        check_id: Exact approved check ID, such as ``WIN-FW-001``.
        timeout_seconds: Maximum PowerShell execution time.
        catalog_path: Optional custom catalog path used mainly for testing.
        script_directory: Optional custom script directory used mainly for
            testing.

    Returns:
        A normalized Pass, Fail, or Error dictionary.

    Raises:
        CatalogError: If the trusted catalog itself is invalid.
        UnknownCheckError: If the selected ID is not approved.
        DisabledCheckError: If the selected check is disabled.
        ScriptSecurityError: If its catalog script path violates security
            requirements.
    """

    catalog = load_catalog(catalog_path)
    approved_check = get_approved_check(check_id, catalog)
    script_path = resolve_approved_script(
        approved_check,
        script_directory=script_directory,
    )

    try:
        process = execute_powershell_script(
            script_path,
            timeout_seconds=timeout_seconds,
        )
        raw_result = parse_script_output(process)
        return validate_and_normalize_result(
            raw_result,
            expected_check=approved_check,
        )
    except (
        ScriptExecutionError,
        ScriptTimeoutError,
        InvalidResultError,
    ) as exc:
        return build_error_result(
            approved_check,
            error_message=str(exc),
        )


if __name__ == "__main__":
    result = run_check("WIN-FW-001")
    print(json.dumps(result, indent=2))
