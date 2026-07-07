"""macOS app-menu naming via the Objective-C runtime (NST-406).

An unbundled Python process shows "Python" as the application-menu title
(top-left of the menu bar) because macOS reads it from the running bundle's
``CFBundleName`` — the venv's Python.app — not from Qt. Until NST-902 ships a
real .app bundle, patch the in-memory info dictionary of the main bundle.
Must run before QApplication is created (i.e. before the process registers
with the window server). Pure ctypes; no new dependency.
"""

from __future__ import annotations

import ctypes
import ctypes.util
import logging
import platform

from app import config

logger = logging.getLogger(__name__)

_UTF8 = 0x08000100  # kCFStringEncodingUTF8
_BUNDLE_NAME_KEY = "CFBundleName"
_NAME_BUFFER_SIZE = 256


class _ObjCRuntime:
    """Thin ctypes bridge to the parts of libobjc/CoreFoundation we need."""

    def __init__(self) -> None:
        self._objc = self._load("objc")
        self._core_foundation = self._load("CoreFoundation")

        self._objc.objc_getClass.restype = ctypes.c_void_p
        self._objc.objc_getClass.argtypes = [ctypes.c_char_p]
        self._objc.sel_registerName.restype = ctypes.c_void_p
        self._objc.sel_registerName.argtypes = [ctypes.c_char_p]

        self._core_foundation.CFStringCreateWithCString.restype = ctypes.c_void_p
        self._core_foundation.CFStringCreateWithCString.argtypes = [
            ctypes.c_void_p,
            ctypes.c_char_p,
            ctypes.c_uint32,
        ]
        self._core_foundation.CFStringGetCString.restype = ctypes.c_bool
        self._core_foundation.CFStringGetCString.argtypes = [
            ctypes.c_void_p,
            ctypes.c_char_p,
            ctypes.c_long,
            ctypes.c_uint32,
        ]

        # objc_msgSend must be called through a prototype matching the target
        # method signature (mandatory on arm64), one per shape used below.
        self.send = ctypes.CFUNCTYPE(ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p)(
            ("objc_msgSend", self._objc)
        )
        self.send_get = ctypes.CFUNCTYPE(
            ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p
        )(("objc_msgSend", self._objc))
        self.send_responds = ctypes.CFUNCTYPE(
            ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p
        )(("objc_msgSend", self._objc))
        self.send_set = ctypes.CFUNCTYPE(
            None, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p
        )(("objc_msgSend", self._objc))

    @staticmethod
    def _load(name: str) -> ctypes.CDLL:
        path = ctypes.util.find_library(name)
        if path is None:
            raise OSError(f"library not found: {name}")
        return ctypes.CDLL(path)

    def get_class(self, name: bytes) -> int:
        return self._objc.objc_getClass(name)

    def sel(self, name: bytes) -> int:
        return self._objc.sel_registerName(name)

    def cfstring(self, value: str) -> int:
        ref = self._core_foundation.CFStringCreateWithCString(None, value.encode("utf-8"), _UTF8)
        if not ref:
            raise ValueError(f"CFString creation failed for {value!r}")
        return ref

    def cfstring_to_str(self, ref: int) -> str | None:
        buffer = ctypes.create_string_buffer(_NAME_BUFFER_SIZE)
        if not self._core_foundation.CFStringGetCString(ref, buffer, _NAME_BUFFER_SIZE, _UTF8):
            return None
        return buffer.value.decode("utf-8")

    def main_bundle_info(self) -> int | None:
        """The main bundle's (localized, else plain) info dictionary, or None."""
        bundle = self.send(self.get_class(b"NSBundle"), self.sel(b"mainBundle"))
        if not bundle:
            return None
        info = self.send(bundle, self.sel(b"localizedInfoDictionary")) or self.send(
            bundle, self.sel(b"infoDictionary")
        )
        return info or None


def set_app_menu_name(name: str = config.APP_NAME) -> bool:
    """Set the macOS application-menu title; True when applied, False when skipped."""
    if platform.system() != "Darwin":
        return False
    try:
        runtime = _ObjCRuntime()
        info = runtime.main_bundle_info()
        if info is None:
            return False
        set_selector = runtime.sel(b"setObject:forKey:")
        # Only patchable when the in-memory dictionary is actually mutable.
        if not runtime.send_responds(info, runtime.sel(b"respondsToSelector:"), set_selector):
            return False
        runtime.send_set(
            info, set_selector, runtime.cfstring(name), runtime.cfstring(_BUNDLE_NAME_KEY)
        )
        return True
    except (OSError, ValueError):
        logger.exception("Could not set the macOS app menu name")
        return False


def current_app_menu_name() -> str | None:
    """Read back CFBundleName from the main bundle (macOS only; None elsewhere)."""
    if platform.system() != "Darwin":
        return None
    try:
        runtime = _ObjCRuntime()
        info = runtime.main_bundle_info()
        if info is None:
            return None
        value = runtime.send_get(
            info, runtime.sel(b"objectForKey:"), runtime.cfstring(_BUNDLE_NAME_KEY)
        )
        if not value:
            return None
        return runtime.cfstring_to_str(value)
    except (OSError, ValueError):
        logger.exception("Could not read the macOS app menu name")
        return None
