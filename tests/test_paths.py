"""Tests for SecureAudit application path handling."""

from pathlib import Path
import sys

import pytest

import core.paths as paths
from core.paths import PathConfigurationError


def test_source_mode_uses_repository_as_resource_root(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Source execution should load resources from the repository."""

    monkeypatch.delattr(
        sys,
        "frozen",
        raising=False,
    )

    expected_root = (
        Path(paths.__file__)
        .resolve()
        .parent
        .parent
    )

    assert paths.resource_root() == expected_root


def test_frozen_mode_uses_pyinstaller_resource_root(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Frozen execution should load bundled files from _MEIPASS."""

    monkeypatch.setattr(
        sys,
        "frozen",
        True,
        raising=False,
    )

    monkeypatch.setattr(
        sys,
        "_MEIPASS",
        str(tmp_path),
        raising=False,
    )

    assert (
        paths.resource_root()
        == tmp_path.resolve()
    )


def test_frozen_mode_requires_pyinstaller_resource_root(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """An inconsistent frozen environment must fail clearly."""

    monkeypatch.setattr(
        sys,
        "frozen",
        True,
        raising=False,
    )

    monkeypatch.delattr(
        sys,
        "_MEIPASS",
        raising=False,
    )

    with pytest.raises(
        PathConfigurationError,
        match="PyInstaller resource directory",
    ):
        paths.resource_root()


def test_catalog_and_powershell_paths_remain_inside_resources(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Trusted scanner resources must resolve inside the resource root."""

    monkeypatch.setattr(
        paths,
        "resource_root",
        lambda: tmp_path,
    )

    assert paths.catalog_path() == (
        tmp_path
        / "checks"
        / "catalog.json"
    ).resolve()

    assert paths.powershell_directory() == (
        tmp_path
        / "checks"
        / "powershell"
    ).resolve()


def test_resource_path_rejects_escape_from_trusted_root(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Resource resolution must not allow traversal outside its base."""

    trusted_root = (
        tmp_path
        / "trusted"
    )

    trusted_root.mkdir()

    monkeypatch.setattr(
        paths,
        "resource_root",
        lambda: trusted_root,
    )

    with pytest.raises(
        PathConfigurationError,
        match="escaped",
    ):
        paths.resource_path(
            "..",
            "outside.txt",
        )


def test_source_mode_uses_repository_as_runtime_root(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Development runs should preserve the existing repo-local data layout."""

    monkeypatch.delattr(
        sys,
        "frozen",
        raising=False,
    )

    assert (
        paths.runtime_root()
        == paths.source_root()
    )


def test_frozen_runtime_uses_localappdata(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Packaged execution should store persistent state in LOCALAPPDATA."""

    monkeypatch.setattr(
        sys,
        "frozen",
        True,
        raising=False,
    )

    monkeypatch.setenv(
        "LOCALAPPDATA",
        str(tmp_path),
    )

    assert paths.runtime_root() == (
        tmp_path.resolve()
        / "SecureAudit"
    )


def test_frozen_runtime_requires_localappdata(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Packaged execution must fail clearly without a writable base."""

    monkeypatch.setattr(
        sys,
        "frozen",
        True,
        raising=False,
    )

    monkeypatch.delenv(
        "LOCALAPPDATA",
        raising=False,
    )

    with pytest.raises(
        PathConfigurationError,
        match="LOCALAPPDATA",
    ):
        paths.runtime_root()


def test_database_path_creates_data_directory(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Database resolution should create its persistent parent directory."""

    monkeypatch.setattr(
        paths,
        "runtime_root",
        lambda: tmp_path,
    )

    database = paths.database_path()

    assert database == (
        tmp_path
        / "data"
        / "secureaudit.db"
    ).resolve()

    assert database.parent.is_dir()


def test_reports_directory_can_be_created(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """The report directory should be creatable in the writable runtime root."""

    monkeypatch.setattr(
        paths,
        "runtime_root",
        lambda: tmp_path,
    )

    directory = paths.reports_directory(
        create=True
    )

    assert directory == (
        tmp_path
        / "reports"
    ).resolve()

    assert directory.is_dir()