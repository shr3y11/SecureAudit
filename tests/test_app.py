"""Tests for SecureAudit application startup orchestration."""

from unittest.mock import MagicMock, patch

from core.admin import ElevationRequestError

import app


@patch(
    "app.request_elevation",
    return_value="started",
)
@patch("app.tk.Tk")
def test_main_does_not_open_gui_after_starting_elevated_replacement(
    mock_tk,
    mock_request_elevation,
):
    """The original non-elevated process must stop after relaunch."""

    app.main()

    mock_request_elevation.assert_called_once_with()
    mock_tk.assert_not_called()


@patch("app.messagebox.showinfo")
@patch(
    "app.request_elevation",
    return_value="cancelled",
)
@patch("app.tk.Tk")
def test_main_exits_cleanly_when_uac_is_cancelled(
    mock_tk,
    mock_request_elevation,
    mock_showinfo,
):
    """Cancelling UAC must not launch the SecureAudit GUI."""

    app.main()

    mock_request_elevation.assert_called_once_with()
    mock_tk.assert_not_called()
    mock_showinfo.assert_called_once()


@patch("app.SecureAuditApp")
@patch(
    "app.request_elevation",
    return_value="already_elevated",
)
@patch("app.tk.Tk")
def test_main_launches_gui_when_already_elevated(
    mock_tk,
    mock_request_elevation,
    mock_secureaudit_app,
):
    """An elevated process should launch the normal Tkinter application."""

    root = MagicMock()
    mock_tk.return_value = root

    app.main()

    mock_request_elevation.assert_called_once_with()
    mock_tk.assert_called_once_with()
    mock_secureaudit_app.assert_called_once_with(root)
    root.mainloop.assert_called_once_with()


@patch("app.messagebox.showerror")
@patch(
    "app.request_elevation",
    side_effect=ElevationRequestError(
        "Test elevation failure"
    ),
)
@patch("app.tk.Tk")
def test_main_handles_elevation_failure_without_opening_gui(
    mock_tk,
    mock_request_elevation,
    mock_showerror,
):
    """Unexpected elevation failures must stop startup cleanly."""

    app.main()

    mock_request_elevation.assert_called_once_with()
    mock_tk.assert_not_called()
    mock_showerror.assert_called_once()