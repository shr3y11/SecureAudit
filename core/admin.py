"""Windows administrator privilege helpers for SecureAudit."""

from __future__ import annotations

import ctypes
import os


class AdminPrivilegeError(RuntimeError):
    """Raised when administrator privilege state cannot be determined."""


def is_windows() -> bool:
    """Return True when SecureAudit is running on Windows."""

    return os.name == "nt"


def is_admin() -> bool:
    """
    Return whether the current SecureAudit process has Administrator privileges.

    SecureAudit currently supports Windows for administrator elevation.
    The Windows Shell API is queried directly instead of executing a
    PowerShell command or spawning another process.

    Raises:
        AdminPrivilegeError:
            If called on a non-Windows platform or Windows cannot determine
            the current process privilege state.
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