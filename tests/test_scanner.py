"""Tests for the SecureAudit allow-listed scanner engine."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from core.scanner import (
    CatalogError,
    DisabledCheckError,
    ScriptSecurityError,
    UnknownCheckError,
    load_catalog,
    run_check,
)


def write_catalog(
    path: Path,
    *,
    check_id: str,
    script: str,
    enabled: bool = True,
    name: str = "Test Check",
    expected_value: str = "Expected test state",
) -> Path:
    """Write a minimal valid SecureAudit catalog for a single test check."""

    catalog = {
        "catalog_version": "test",
        "application": "SecureAudit",
        "platform": "Windows",
        "checks": [
            {
                "id": check_id,
                "name": name,
                "script": script,
                "expected_value": expected_value,
                "enabled": enabled,
            }
        ],
    }

    path.write_text(
        json.dumps(catalog),
        encoding="utf-8",
    )

    return path


def write_script(
    directory: Path,
    filename: str,
    content: str,
) -> Path:
    """Create a temporary PowerShell scanner script."""

    directory.mkdir(parents=True, exist_ok=True)

    script_path = directory / filename
    script_path.write_text(content, encoding="utf-8")

    return script_path


def test_real_catalog_loads_five_initial_checks() -> None:
    """The committed MVP catalog should load and contain five unique checks."""

    catalog = load_catalog()
    checks = catalog["checks"]
    check_ids = [check["id"] for check in checks]

    assert len(checks) == 5
    assert len(check_ids) == len(set(check_ids))
    assert "WIN-FW-001" in check_ids


def test_unknown_check_id_is_rejected() -> None:
    """An unapproved ID must never cause a script to execute."""

    with pytest.raises(
        UnknownCheckError,
        match="not approved in the catalog",
    ):
        run_check("WIN-NOT-APPROVED")


def test_empty_check_id_is_rejected() -> None:
    """Blank identifiers are invalid application requests."""

    with pytest.raises(
        UnknownCheckError,
        match="non-empty check ID",
    ):
        run_check("   ")


def test_disabled_check_is_rejected(tmp_path: Path) -> None:
    """Disabled catalog entries must not execute."""

    catalog_path = write_catalog(
        tmp_path / "catalog.json",
        check_id="TEST-DISABLED-001",
        script="disabled.ps1",
        enabled=False,
    )

    with pytest.raises(
        DisabledCheckError,
        match="disabled in the approved catalog",
    ):
        run_check(
            "TEST-DISABLED-001",
            catalog_path=catalog_path,
            script_directory=tmp_path,
        )


def test_absolute_script_path_is_rejected(tmp_path: Path) -> None:
    """Catalog entries cannot authorize absolute filesystem paths."""

    catalog_path = write_catalog(
        tmp_path / "catalog.json",
        check_id="TEST-ABS-001",
        script=r"C:\Windows\Temp\unsafe.ps1",
    )

    with pytest.raises(
        ScriptSecurityError,
        match="Absolute script paths are prohibited",
    ):
        run_check(
            "TEST-ABS-001",
            catalog_path=catalog_path,
            script_directory=tmp_path,
        )


def test_traversal_script_path_is_rejected(tmp_path: Path) -> None:
    """Catalog entries cannot escape through parent-directory traversal."""

    catalog_path = write_catalog(
        tmp_path / "catalog.json",
        check_id="TEST-PATH-001",
        script=r"..\unsafe.ps1",
    )

    with pytest.raises(
        ScriptSecurityError,
        match="Nested or traversing script paths are prohibited",
    ):
        run_check(
            "TEST-PATH-001",
            catalog_path=catalog_path,
            script_directory=tmp_path,
        )


def test_non_powershell_script_is_rejected(tmp_path: Path) -> None:
    """Approved scanner modules must use the .ps1 extension."""

    catalog_path = write_catalog(
        tmp_path / "catalog.json",
        check_id="TEST-EXT-001",
        script="scanner.bat",
    )

    with pytest.raises(
        ScriptSecurityError,
        match=r"does not reference an approved \.ps1 file",
    ):
        run_check(
            "TEST-EXT-001",
            catalog_path=catalog_path,
            script_directory=tmp_path,
        )


def test_missing_script_is_rejected(tmp_path: Path) -> None:
    """A catalog mapping is invalid when its script does not exist."""

    catalog_path = write_catalog(
        tmp_path / "catalog.json",
        check_id="TEST-MISSING-001",
        script="missing.ps1",
    )

    with pytest.raises(
        ScriptSecurityError,
        match="Approved script was not found",
    ):
        run_check(
            "TEST-MISSING-001",
            catalog_path=catalog_path,
            script_directory=tmp_path,
        )


def test_invalid_json_becomes_error_result(tmp_path: Path) -> None:
    """Malformed scanner output must not crash the application."""

    script_directory = tmp_path / "scripts"

    write_script(
        script_directory,
        "invalid_json.ps1",
        'Write-Output "This is not JSON"\n',
    )

    catalog_path = write_catalog(
        tmp_path / "catalog.json",
        check_id="TEST-JSON-001",
        script="invalid_json.ps1",
        name="Invalid JSON Test",
        expected_value="Valid JSON",
    )

    result = run_check(
        "TEST-JSON-001",
        catalog_path=catalog_path,
        script_directory=script_directory,
    )

    assert result["check_id"] == "TEST-JSON-001"
    assert result["status"] == "Error"
    assert result["evidence"] == []
    assert "invalid JSON" in result["error_message"]


def test_timeout_becomes_error_result(tmp_path: Path) -> None:
    """Scripts exceeding the allowed duration must return Error."""

    script_directory = tmp_path / "scripts"

    write_script(
        script_directory,
        "timeout.ps1",
        (
            "Start-Sleep -Seconds 5\n"
            "Write-Output "
            '\'{\"check_id\":\"TEST-TIMEOUT-001\"}\'\n'
        ),
    )

    catalog_path = write_catalog(
        tmp_path / "catalog.json",
        check_id="TEST-TIMEOUT-001",
        script="timeout.ps1",
        name="Timeout Test",
        expected_value="Complete promptly",
    )

    result = run_check(
        "TEST-TIMEOUT-001",
        timeout_seconds=1,
        catalog_path=catalog_path,
        script_directory=script_directory,
    )

    assert result["check_id"] == "TEST-TIMEOUT-001"
    assert result["status"] == "Error"
    assert result["evidence"] == []
    assert result["error_message"] == (
        "Scanner script exceeded the 1-second timeout."
    )


def test_valid_result_is_normalized(tmp_path: Path) -> None:
    """Successful script output should produce the normalized result contract."""

    script_directory = tmp_path / "scripts"

    script_result = {
        "check_id": "TEST-PASS-001",
        "check_name": "Normalization Test",
        "expected_value": "Test state enabled",
        "observed_value": "Enabled=True",
        "status": "Pass",
        "evidence": [
            {
                "setting": "Example",
                "enabled": True,
            }
        ],
        "error_message": "",
        "timestamp_utc": "2026-08-06T10:00:00Z",
    }

    compressed_json = json.dumps(
        script_result,
        separators=(",", ":"),
    ).replace("'", "''")

    write_script(
        script_directory,
        "valid.ps1",
        f"Write-Output '{compressed_json}'\n",
    )

    catalog_path = write_catalog(
        tmp_path / "catalog.json",
        check_id="TEST-PASS-001",
        script="valid.ps1",
        name="Normalization Test",
        expected_value="Test state enabled",
    )

    result = run_check(
        "TEST-PASS-001",
        catalog_path=catalog_path,
        script_directory=script_directory,
    )

    assert result["check_id"] == "TEST-PASS-001"
    assert result["status"] == "Pass"
    assert result["observed_value"] == "Enabled=True"
    assert result["error_message"] is None
    assert len(result["evidence"]) == 1


def test_result_check_id_mismatch_becomes_error(tmp_path: Path) -> None:
    """A script cannot impersonate a different authorized check."""

    script_directory = tmp_path / "scripts"

    script_result = {
        "check_id": "DIFFERENT-ID",
        "check_name": "Mismatched Test",
        "expected_value": "Expected",
        "observed_value": "Observed",
        "status": "Pass",
        "evidence": [],
        "error_message": "",
        "timestamp_utc": "2026-08-06T10:00:00Z",
    }

    compressed_json = json.dumps(
        script_result,
        separators=(",", ":"),
    )

    write_script(
        script_directory,
        "mismatch.ps1",
        f"Write-Output '{compressed_json}'\n",
    )

    catalog_path = write_catalog(
        tmp_path / "catalog.json",
        check_id="TEST-MATCH-001",
        script="mismatch.ps1",
    )

    result = run_check(
        "TEST-MATCH-001",
        catalog_path=catalog_path,
        script_directory=script_directory,
    )

    assert result["check_id"] == "TEST-MATCH-001"
    assert result["status"] == "Error"
    assert "does not match" in result["error_message"]


def test_invalid_catalog_json_raises_catalog_error(
    tmp_path: Path,
) -> None:
    """Malformed trusted catalog data must stop scanner authorization."""

    catalog_path = tmp_path / "catalog.json"
    catalog_path.write_text("{not-valid-json", encoding="utf-8")

    with pytest.raises(
        CatalogError,
        match="contains invalid JSON",
    ):
        load_catalog(catalog_path)