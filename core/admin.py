"""Windows administrator privilege and UAC elevation helpers."""

from __future__ import annotations

import ctypes
from ctypes import wintypes
import os
from pathlib import Path
import subprocess
import sys
from typing import Literal


ERROR_CANCELLED = 1223
SW_SHOWNORMAL = 1

ElevationResult = Literal[
    "already_elevated",
    "started",
    "cancelled",
]


class AdminPrivilegeError(RuntimeError):
    """Raised when administrator privilege state cannot be determined."""


class ElevationRequestError(AdminPrivilegeError):
    """Raised when Windows cannot start an elevated SecureAudit process."""


class ShellExecuteInfoW(ctypes.Structure):
    """Windows SHELLEXECUTEINFOW structure used by ShellExecuteExW."""

    _fields_ = [
        ("cbSize", wintypes.DWORD),
        ("fMask", wintypes.ULONG),
        ("hwnd", wintypes.HWND),
        ("lpVerb", wintypes.LPCWSTR),
        ("lpFile", wintypes.LPCWSTR),
        ("lpParameters", wintypes.LPCWSTR),
        ("lpDirectory", wintypes.LPCWSTR),
        ("nShow", ctypes.c_int),
        ("hInstApp", wintypes.HINSTANCE),
        ("lpIDList", ctypes.c_void_p),
        ("lpClass", wintypes.LPCWSTR),
        ("hkeyClass", wintypes.HKEY),
        ("dwHotKey", wintypes.DWORD),
        ("hIconOrMonitor", ctypes.c_void_p),
        ("hProcess", wintypes.HANDLE),
    ]


def is_windows() -> bool:
    """Return True when SecureAudit is running on Windows."""

    return os.name == "nt"


def is_admin() -> bool:
    """
    Return whether the current SecureAudit process has Administrator privileges.

    Raises:
        AdminPrivilegeError:
            If SecureAudit is not running on Windows or Windows cannot determine
            the current privilege state.
    """

    if not is_windows():
        raise AdminPrivilegeError(
            "Administrator privilege detection is supported only on Windows."
        )

    try:
        result = ctypes.windll.shell32.IsUserAnAdmin()
    except (AttributeError, OSError) as exc:
        raise AdminPrivilegeError(
            "Windows could not determine the current Administrator privilege state."
        ) from exc

    return bool(result)


def _build_relaunch_command() -> tuple[str, str]:
    """
    Build the executable and parameter string used for elevation.

    Normal Python execution:
        python.exe app.py <original arguments>

    PyInstaller execution:
        SecureAudit.exe <original arguments>

    This allows the same elevation layer to be reused by the packaged
    Windows executable later.
    """

    executable = str(sys.executable)
    original_arguments = [str(argument) for argument in sys.argv[1:]]

    if getattr(sys, "frozen", False):
        parameters = subprocess.list2cmdline(
            original_arguments,
        )
        return executable, parameters

    if not sys.argv or not sys.argv[0]:
        raise ElevationRequestError(
            "SecureAudit could not determine the application entry point."
        )

    entry_point = str(
        Path(sys.argv[0]).resolve()
    )

    parameters = subprocess.list2cmdline(
        [
            entry_point,
            *original_arguments,
        ]
    )

    return executable, parameters


def _launch_elevated(
    executable: str,
    parameters: str,
) -> tuple[bool, int]:
    """
    Ask Windows to start a process using the normal UAC 'runas' mechanism.

    Returns:
        Tuple containing:
            success
            Windows error code
    """

    if not executable:
        raise ElevationRequestError(
            "An executable is required for administrator elevation."
        )

    try:
        shell32 = ctypes.WinDLL(
            "shell32",
            use_last_error=True,
        )
    except (AttributeError, OSError) as exc:
        raise ElevationRequestError(
            "Windows Shell API could not be loaded."
        ) from exc

    shell_execute_ex = shell32.ShellExecuteExW
    shell_execute_ex.argtypes = [
        ctypes.POINTER(ShellExecuteInfoW)
    ]
    shell_execute_ex.restype = wintypes.BOOL

    execute_info = ShellExecuteInfoW()
    execute_info.cbSize = ctypes.sizeof(
        ShellExecuteInfoW
    )
    execute_info.fMask = 0
    execute_info.hwnd = None
    execute_info.lpVerb = "runas"
    execute_info.lpFile = executable
    execute_info.lpParameters = parameters or None
    execute_info.lpDirectory = str(Path.cwd())
    execute_info.nShow = SW_SHOWNORMAL
    execute_info.hInstApp = None
    execute_info.lpIDList = None
    execute_info.lpClass = None
    execute_info.hkeyClass = None
    execute_info.dwHotKey = 0
    execute_info.hIconOrMonitor = None
    execute_info.hProcess = None

    ctypes.set_last_error(0)

    success = bool(
        shell_execute_ex(
            ctypes.byref(execute_info)
        )
    )

    error_code = ctypes.get_last_error()

    return success, error_code


def request_elevation() -> ElevationResult:
    """
    Request Administrator elevation through normal Windows UAC.

    This function does not terminate the current process. The application
    startup layer is responsible for exiting the non-elevated process after
    an elevated replacement has successfully started.

    Returns:
        "already_elevated":
            Current SecureAudit process already has Administrator privileges.

        "started":
            Windows accepted the elevation request and started the elevated
            replacement process.

        "cancelled":
            The user cancelled the Windows UAC prompt.

    Raises:
        ElevationRequestError:
            If elevation cannot be requested reliably for another reason.
    """

    if not is_windows():
        raise ElevationRequestError(
            "Administrator elevation is supported only on Windows."
        )

    if is_admin():
        return "already_elevated"

    executable, parameters = (
        _build_relaunch_command()
    )

    success, error_code = _launch_elevated(
        executable,
        parameters,
    )

    if success:
        return "started"

    if error_code == ERROR_CANCELLED:
        return "cancelled"

    raise ElevationRequestError(
        "Windows could not start SecureAudit with Administrator "
        f"privileges. Windows error code: {error_code}."
    )