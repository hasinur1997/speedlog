"""Cross-platform full-name lookup for report headers."""

from __future__ import annotations

import ctypes
import getpass
import os
import platform

try:  # pragma: no cover - unavailable on Windows.
    import pwd
except ImportError:  # pragma: no cover - exercised on Windows only.
    pwd = None  # type: ignore[assignment]

_NAME_DISPLAY = 3  # EXTENDED_NAME_FORMAT.NameDisplay


def _fallback_name() -> str:
    return getpass.getuser().strip() or "User"


def _posix_full_name() -> str | None:
    if pwd is None or not hasattr(os, "getuid"):
        return None

    try:
        gecos = pwd.getpwuid(os.getuid()).pw_gecos.split(",", 1)[0].strip()
    except (KeyError, OSError):
        return None
    return gecos or None


def _windows_full_name() -> str | None:
    windll = getattr(ctypes, "windll", None)
    if windll is None:
        return None

    try:
        name_size = ctypes.c_ulong(0)
        if windll.secur32.GetUserNameExW(_NAME_DISPLAY, None, ctypes.byref(name_size)):
            return None
        if name_size.value <= 0:
            return None

        buffer = ctypes.create_unicode_buffer(name_size.value)
        if not windll.secur32.GetUserNameExW(_NAME_DISPLAY, buffer, ctypes.byref(name_size)):
            return None
    except (AttributeError, OSError):
        return None

    full_name = buffer.value.strip()
    return full_name or None


def get_full_name() -> str:
    """Return the best available human-readable full name for the local user."""

    if platform.system() == "Windows":
        return _windows_full_name() or _fallback_name()
    return _posix_full_name() or _fallback_name()
