"""Tests for cross-platform full-name lookup (NST-801)."""

from __future__ import annotations

from types import SimpleNamespace

import app.platform.userinfo as userinfo_module


def test_get_full_name_uses_pw_gecos_on_posix(monkeypatch) -> None:
    monkeypatch.setattr(userinfo_module.platform, "system", lambda: "Darwin")
    monkeypatch.setattr(userinfo_module.os, "getuid", lambda: 501)
    monkeypatch.setattr(
        userinfo_module,
        "pwd",
        SimpleNamespace(
            getpwuid=lambda uid: SimpleNamespace(pw_gecos="Taylor Example,Room 4"),
        ),
    )
    monkeypatch.setattr(userinfo_module.getpass, "getuser", lambda: "fallback-user")

    assert userinfo_module.get_full_name() == "Taylor Example"


def test_get_full_name_falls_back_to_getpass_when_gecos_is_blank(monkeypatch) -> None:
    monkeypatch.setattr(userinfo_module.platform, "system", lambda: "Linux")
    monkeypatch.setattr(userinfo_module.os, "getuid", lambda: 501)
    monkeypatch.setattr(
        userinfo_module,
        "pwd",
        SimpleNamespace(getpwuid=lambda uid: SimpleNamespace(pw_gecos="")),
    )
    monkeypatch.setattr(userinfo_module.getpass, "getuser", lambda: "fallback-user")

    assert userinfo_module.get_full_name() == "fallback-user"


def test_get_full_name_uses_windows_display_name_when_available(monkeypatch) -> None:
    monkeypatch.setattr(userinfo_module.platform, "system", lambda: "Windows")
    monkeypatch.setattr(userinfo_module, "_windows_full_name", lambda: "Ada Lovelace")
    monkeypatch.setattr(userinfo_module.getpass, "getuser", lambda: "fallback-user")

    assert userinfo_module.get_full_name() == "Ada Lovelace"


def test_get_full_name_falls_back_to_getpass_on_windows(monkeypatch) -> None:
    monkeypatch.setattr(userinfo_module.platform, "system", lambda: "Windows")
    monkeypatch.setattr(userinfo_module, "_windows_full_name", lambda: None)
    monkeypatch.setattr(userinfo_module.getpass, "getuser", lambda: "fallback-user")

    assert userinfo_module.get_full_name() == "fallback-user"
