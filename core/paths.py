"""SecureAudit application resource and writable-runtime paths."""

from __future__ import annotations

import os
import sys
from pathlib import Path


APP_NAME = "SecureAudit"


class PathConfigurationError(RuntimeError):
    """Raised when SecureAudit cannot determine a safe runtime path."""


def is_frozen() -> bool:
    """Return True when running from a frozen executable such as PyInstaller."""

    return bool(
        getattr(
            sys,
            "frozen",
            False,
        )
    )


def source_root() -> Path:
    """Return the SecureAudit repository root during source execution."""

    return (
        Path(__file__)
        .resolve()
        .parent
        .parent
    )


def resource_root() -> Path:
    """Return the root containing bundled read-only application resources."""

    if not is_frozen():
        return source_root()

    bundle_root = getattr(
        sys,
        "_MEIPASS",
        None,
    )

    if not bundle_root:
        raise PathConfigurationError(
            "SecureAudit is running as a frozen application, "
            "but the PyInstaller resource directory is unavailable."
        )

    return Path(bundle_root).resolve()


def _safe_child(
    base_directory: Path,
    *parts: str,
) -> Path:
    """Resolve a path while preventing escape from its trusted base."""

    base_directory = base_directory.resolve()

    candidate = (
        base_directory
        .joinpath(*parts)
        .resolve()
    )

    try:
        candidate.relative_to(
            base_directory
        )
    except ValueError as exc:
        raise PathConfigurationError(
            "Resolved path escaped its trusted base directory."
        ) from exc

    return candidate


def resource_path(
    *parts: str,
) -> Path:
    """Return a path inside SecureAudit's bundled resource directory."""

    return _safe_child(
        resource_root(),
        *parts,
    )


def catalog_path() -> Path:
    """Return the approved Windows check-catalog path."""

    return resource_path(
        "checks",
        "catalog.json",
    )


def powershell_directory() -> Path:
    """Return the trusted PowerShell scanner-module directory."""

    return resource_path(
        "checks",
        "powershell",
    )


def runtime_root() -> Path:
    """Return the writable root used for persistent SecureAudit state."""

    if not is_frozen():
        return source_root()

    local_app_data = os.environ.get(
        "LOCALAPPDATA"
    )

    if not local_app_data:
        raise PathConfigurationError(
            "LOCALAPPDATA is unavailable. "
            "SecureAudit cannot determine a persistent writable directory."
        )

    return (
        Path(local_app_data)
        .expanduser()
        .resolve()
        / APP_NAME
    )


def data_directory(
    *,
    create: bool = False,
) -> Path:
    """Return the directory containing persistent SQLite data."""

    directory = _safe_child(
        runtime_root(),
        "data",
    )

    if create:
        directory.mkdir(
            parents=True,
            exist_ok=True,
        )

    return directory


def reports_directory(
    *,
    create: bool = False,
) -> Path:
    """Return the directory containing generated HTML reports."""

    directory = _safe_child(
        runtime_root(),
        "reports",
    )

    if create:
        directory.mkdir(
            parents=True,
            exist_ok=True,
        )

    return directory


def database_path(
    *,
    create_parent: bool = True,
) -> Path:
    """Return the persistent SecureAudit SQLite database path."""

    return (
        data_directory(
            create=create_parent,
        )
        / "secureaudit.db"
    )