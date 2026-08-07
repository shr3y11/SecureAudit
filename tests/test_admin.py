"""Tests for Windows administrator privilege helpers."""

from unittest.mock import patch

from pathlib import Path
import pytest

@patch("core.admin.sys.argv", [r"C:\SecureAudit\app.py"])
@patch("core.admin.sys.executable", r"C:\Python\python.exe")
@patch("core.admin.Path.is_file", return_value=False)
def test_build_relaunch_command_rejects_missing_pythonw(
    mock_is_file,
):
    """SecureAudit must fail clearly if pythonw.exe cannot be located."""

    from core.admin import _build_relaunch_command

    with pytest.raises(
        ElevationRequestError,
        match="could not locate pythonw.exe",
    ):
        _build_relaunch_command()

    mock_is_file.assert_called_once_with()

@patch("core.admin.sys.argv", [r"C:\SecureAudit\app.py"])
@patch("core.admin.sys.executable", r"C:\Python\python.exe")
@patch("core.admin.Path.is_file", return_value=True)
def test_build_relaunch_command_uses_pythonw_for_source_execution(
    mock_is_file,
):
    """Source execution should elevate through pythonw.exe."""

    from core.admin import _build_relaunch_command

    executable, parameters = _build_relaunch_command()

    assert executable == str(
        Path(r"C:\Python\python.exe").with_name("pythonw.exe")
    )
    assert "app.py" in parameters
    mock_is_file.assert_called_once_with()

from core.admin import (
    AdminPrivilegeError,
    ERROR_CANCELLED,
    ElevationRequestError,
    is_admin,
    is_windows,
    request_elevation,
)


def test_is_windows_returns_boolean():
    """Platform detection always returns a boolean."""

    assert isinstance(is_windows(), bool)


@patch(
    "core.admin.is_windows",
    return_value=False,
)
def test_is_admin_rejects_non_windows_platform(
    mock_is_windows,
):
    """Admin detection must reject unsupported platforms."""

    with pytest.raises(
        AdminPrivilegeError,
        match="supported only on Windows",
    ):
        is_admin()

    mock_is_windows.assert_called_once_with()


@patch(
    "core.admin.is_windows",
    return_value=True,
)
@patch(
    "core.admin.ctypes.windll.shell32.IsUserAnAdmin",
    return_value=1,
)
def test_is_admin_returns_true_when_windows_reports_admin(
    mock_is_user_an_admin,
    mock_is_windows,
):
    """A non-zero Windows result means the process is elevated."""

    assert is_admin() is True

    mock_is_windows.assert_called_once_with()
    mock_is_user_an_admin.assert_called_once_with()


@patch(
    "core.admin.is_windows",
    return_value=True,
)
@patch(
    "core.admin.ctypes.windll.shell32.IsUserAnAdmin",
    return_value=0,
)
def test_is_admin_returns_false_when_windows_reports_standard_user(
    mock_is_user_an_admin,
    mock_is_windows,
):
    """A zero Windows result means the process is not elevated."""

    assert is_admin() is False

    mock_is_windows.assert_called_once_with()
    mock_is_user_an_admin.assert_called_once_with()


@patch(
    "core.admin.is_windows",
    return_value=True,
)
@patch(
    "core.admin.ctypes.windll.shell32.IsUserAnAdmin",
    side_effect=OSError(
        "Windows API failure"
    ),
)
def test_is_admin_wraps_windows_api_failure(
    mock_is_user_an_admin,
    mock_is_windows,
):
    """Windows API failures become controlled SecureAudit errors."""

    with pytest.raises(
        AdminPrivilegeError,
        match="could not determine",
    ):
        is_admin()

    mock_is_windows.assert_called_once_with()
    mock_is_user_an_admin.assert_called_once_with()


@patch(
    "core.admin.is_windows",
    return_value=True,
)
@patch(
    "core.admin.is_admin",
    return_value=True,
)
def test_request_elevation_does_nothing_when_already_admin(
    mock_is_admin,
    mock_is_windows,
):
    """An already elevated process must not request elevation again."""

    assert request_elevation() == "already_elevated"

    mock_is_windows.assert_called_once_with()
    mock_is_admin.assert_called_once_with()


@patch(
    "core.admin._launch_elevated",
    return_value=(True, 0),
)
@patch(
    "core.admin._build_relaunch_command",
    return_value=(
        r"C:\Python\python.exe",
        r'"C:\SecureAudit\app.py"',
    ),
)
@patch(
    "core.admin.is_admin",
    return_value=False,
)
@patch(
    "core.admin.is_windows",
    return_value=True,
)
def test_request_elevation_reports_started_when_windows_accepts(
    mock_is_windows,
    mock_is_admin,
    mock_build_command,
    mock_launch_elevated,
):
    """Approved elevation starts an elevated replacement."""

    result = request_elevation()

    assert result == "started"

    mock_launch_elevated.assert_called_once_with(
        r"C:\Python\python.exe",
        r'"C:\SecureAudit\app.py"',
    )


@patch(
    "core.admin._launch_elevated",
    return_value=(False, ERROR_CANCELLED),
)
@patch(
    "core.admin._build_relaunch_command",
    return_value=(
        r"C:\Python\python.exe",
        r'"C:\SecureAudit\app.py"',
    ),
)
@patch(
    "core.admin.is_admin",
    return_value=False,
)
@patch(
    "core.admin.is_windows",
    return_value=True,
)
def test_request_elevation_handles_uac_cancellation_cleanly(
    mock_is_windows,
    mock_is_admin,
    mock_build_command,
    mock_launch_elevated,
):
    """Cancelling the UAC dialog is not an application crash."""

    assert request_elevation() == "cancelled"


@patch(
    "core.admin._launch_elevated",
    return_value=(False, 5),
)
@patch(
    "core.admin._build_relaunch_command",
    return_value=(
        r"C:\Python\python.exe",
        r'"C:\SecureAudit\app.py"',
    ),
)
@patch(
    "core.admin.is_admin",
    return_value=False,
)
@patch(
    "core.admin.is_windows",
    return_value=True,
)
def test_request_elevation_raises_for_unexpected_windows_failure(
    mock_is_windows,
    mock_is_admin,
    mock_build_command,
    mock_launch_elevated,
):
    """Unexpected Windows failures must not be treated as cancellation."""

    with pytest.raises(
        ElevationRequestError,
        match="Windows error code: 5",
    ):
        request_elevation()


@patch(
    "core.admin.is_windows",
    return_value=False,
)
def test_request_elevation_rejects_non_windows_platform(
    mock_is_windows,
):
    """SecureAudit must not attempt Windows elevation elsewhere."""

    with pytest.raises(
        ElevationRequestError,
        match="supported only on Windows",
    ):
        request_elevation()

@patch(
    "core.admin.sys.argv",
    [r"C:\Program Files\SecureAudit\SecureAudit.exe"],
)
@patch(
    "core.admin.sys.executable",
    r"C:\Program Files\SecureAudit\SecureAudit.exe",
)
@patch(
    "core.admin.sys.frozen",
    True,
    create=True,
)
def test_build_relaunch_command_uses_frozen_executable():
    """Frozen execution should elevate SecureAudit.exe directly."""

    from core.admin import _build_relaunch_command

    executable, parameters = _build_relaunch_command()

    assert executable == (
        r"C:\Program Files\SecureAudit\SecureAudit.exe"
    )
    assert parameters == ""


@patch(
    "core.admin.sys.argv",
    [
        r"C:\Program Files\SecureAudit\SecureAudit.exe",
        "--example",
        "value with spaces",
    ],
)
@patch(
    "core.admin.sys.executable",
    r"C:\Program Files\SecureAudit\SecureAudit.exe",
)
@patch(
    "core.admin.sys.frozen",
    True,
    create=True,
)
def test_build_relaunch_command_preserves_frozen_arguments():
    """Frozen relaunch should preserve and safely quote arguments."""

    from core.admin import _build_relaunch_command

    executable, parameters = _build_relaunch_command()

    assert executable == (
        r"C:\Program Files\SecureAudit\SecureAudit.exe"
    )
    assert "--example" in parameters
    assert '"value with spaces"' in parameters

