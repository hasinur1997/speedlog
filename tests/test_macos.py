"""Tests for app.macos (NST-406)."""

from __future__ import annotations

import platform

import pytest

from app import config, macos

darwin_only = pytest.mark.skipif(platform.system() != "Darwin", reason="macOS-only behavior")


@darwin_only
def test_set_app_menu_name_patches_bundle_name() -> None:
    try:
        assert macos.set_app_menu_name("SpeedlogTestName") is True
        assert macos.current_app_menu_name() == "SpeedlogTestName"
    finally:
        macos.set_app_menu_name(config.APP_NAME)


@darwin_only
def test_set_app_menu_name_defaults_to_app_name() -> None:
    assert macos.set_app_menu_name() is True
    assert macos.current_app_menu_name() == config.APP_NAME


def test_set_app_menu_name_is_noop_off_macos(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(macos.platform, "system", lambda: "Linux")
    assert macos.set_app_menu_name() is False
    assert macos.current_app_menu_name() is None
