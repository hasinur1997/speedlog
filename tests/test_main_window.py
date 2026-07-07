"""Tests for app.ui.main_window (NST-401)."""

from __future__ import annotations

import pytest
from PySide6.QtWidgets import QTabWidget, QWidget

from app import config
from app.ui.live_view import LiveView
from app.ui.main_window import MainWindow, app_icon


@pytest.fixture
def window(qtbot) -> MainWindow:
    win = MainWindow()
    qtbot.addWidget(win)
    return win


def test_default_size_is_900_by_620(window: MainWindow) -> None:
    assert window.width() == config.MAIN_WINDOW_WIDTH == 900
    assert window.height() == config.MAIN_WINDOW_HEIGHT == 620


def test_window_title_and_icon(window: MainWindow) -> None:
    assert window.windowTitle() == config.APP_NAME
    assert not window.windowIcon().isNull()


def test_tabs_exist_by_object_name(window: MainWindow) -> None:
    tabs = window.findChild(QTabWidget, "mainTabs")
    assert tabs is not None
    assert tabs.count() == 2
    assert tabs.tabText(0) == "Live"
    assert tabs.tabText(1) == "Reports"
    live_tab = window.findChild(QWidget, "liveTab")
    assert live_tab is not None
    assert isinstance(live_tab, LiveView)
    assert window.findChild(QWidget, "reportsTab") is not None


def test_close_event_hides_window_instead_of_quitting(qtbot, window: MainWindow) -> None:
    window.show()
    qtbot.waitExposed(window)

    window.close()

    assert window.isHidden()
    # The widget survived (event ignored): it can be shown again.
    window.show()
    assert window.isVisible()


def test_bring_to_front_shows_hidden_window(window: MainWindow) -> None:
    window.hide()
    window.bring_to_front()
    assert window.isVisible()


def test_app_icon_is_painted() -> None:
    assert not app_icon().isNull()
