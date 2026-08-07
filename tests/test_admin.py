"""Tests for Windows administrator privilege helpers."""

from unittest.mock import patch

import pytest

from core.admin import AdminPrivilegeError, is_admin, is_windows


def test_is_windows_returns_boolean():
    """Platform detection always returns a boolean."""

    assert isinstance(is_windows(), bool)


@patch("core.admin.is_windows", return_value=False)
def test_is_admin_rejects_non_windows_platform(mock_is_windows):
    """Administrator detection must not silently run on unsupported platforms."""

    with pytest.raises(
        AdminPrivilegeError,
        match="supported only on Windows",
    ):
        is_admin()

    mock_is_windows.assert_called_once_with()


@patch("core.admin.is_windows", return_value=True)
@patch("core.admin.ctypes.windll.shell32.IsUserAnAdmin", return_value=1)
def test_is_admin_returns_true_when_windows_reports_admin(
    mock_is_user_an_admin,
    mock_is_windows,
):
    """A non-zero Windows result represents an elevated process."""

    assert is_admin() is True

    mock_is_windows.assert_called_once_with()
    mock_is_user_an_admin.assert_called_once_with()


@patch("core.admin.is_windows", return_value=True)
@patch("core.admin.ctypes.windll.shell32.IsUserAnAdmin", return_value=0)
def test_is_admin_returns_false_when_windows_reports_standard_user(
    mock_is_user_an_admin,
    mock_is_windows,
):
    """A zero Windows result represents a non-elevated process."""

    assert is_admin() is False

    mock_is_windows.assert_called_once_with()
    mock_is_user_an_admin.assert_called_once_with()


@patch("core.admin.is_windows", return_value=True)
@patch(
    "core.admin.ctypes.windll.shell32.IsUserAnAdmin",
    side_effect=OSError("Windows API failure"),
)
def test_is_admin_wraps_windows_api_failure(
    mock_is_user_an_admin,
    mock_is_windows,
):
    """Windows API failures must produce a controlled SecureAudit error."""

    with pytest.raises(
        AdminPrivilegeError,
        match="could not determine",
    ):
        is_admin()

    mock_is_windows.assert_called_once_with()
    mock_is_user_an_admin.assert_called_once_with()