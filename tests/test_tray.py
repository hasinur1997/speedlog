"""Tests for app.ui.tray (NST-402, NST-403)."""

from __future__ import annotations

import pytest
from PySide6.QtCore import QObject, Signal
from PySide6.QtWidgets import QSystemTrayIcon

from app.ui.tray import (
    OFFLINE_TEXT,
    OPEN_ACTION_TEXT,
    QUIT_ACTION_TEXT,
    SpeedTrayIcon,
    tray_icon,
)


class FakeCollector(QObject):
    """Emits the same signals as CollectorService, from the test (main) thread."""

    speed_sampled = Signal(float, float)
    session_changed = Signal(bool, int, int)


class FakeWindow:
    def __init__(self) -> None:
        self.bring_to_front_calls = 0

    def bring_to_front(self) -> None:
        self.bring_to_front_calls += 1


@pytest.fixture
def window() -> FakeWindow:
    return FakeWindow()


@pytest.fixture
def tray(qtbot, window: FakeWindow) -> SpeedTrayIcon:
    return SpeedTrayIcon(window)


@pytest.fixture
def collector(tray: SpeedTrayIcon) -> FakeCollector:
    fake = FakeCollector()
    fake.speed_sampled.connect(tray.on_speed_sampled)
    fake.session_changed.connect(tray.on_session_changed)
    return fake


def test_initial_tooltip_is_offline(tray: SpeedTrayIcon) -> None:
    assert tray.toolTip() == OFFLINE_TEXT


def test_speed_sampled_updates_tooltip(tray: SpeedTrayIcon, collector: FakeCollector) -> None:
    collector.speed_sampled.emit(5_020_000.0, 1_200_000.0)
    assert tray.toolTip() == "↓ 5.02 MB/s  ↑ 1.20 MB/s"


def test_speed_sampled_uses_kb_below_one_mb(tray: SpeedTrayIcon, collector: FakeCollector) -> None:
    collector.speed_sampled.emit(999_000.0, 0.0)
    assert tray.toolTip() == "↓ 999.00 KB/s  ↑ 0.00 KB/s"


def test_tooltip_updates_throttled_to_one_per_second(
    tray: SpeedTrayIcon, collector: FakeCollector
) -> None:
    collector.speed_sampled.emit(5_020_000.0, 1_200_000.0)
    collector.speed_sampled.emit(9_990_000.0, 9_990_000.0)  # immediate second sample
    assert tray.toolTip() == "↓ 5.02 MB/s  ↑ 1.20 MB/s"


def test_session_changed_offline_shows_offline_text(
    tray: SpeedTrayIcon, collector: FakeCollector
) -> None:
    collector.speed_sampled.emit(5_020_000.0, 1_200_000.0)
    collector.session_changed.emit(False, 1, 1_700_000_000)
    assert tray.toolTip() == OFFLINE_TEXT


def test_session_changed_online_keeps_tooltip(
    tray: SpeedTrayIcon, collector: FakeCollector
) -> None:
    collector.speed_sampled.emit(5_020_000.0, 1_200_000.0)
    collector.session_changed.emit(True, 2, 1_700_000_000)
    assert tray.toolTip() == "↓ 5.02 MB/s  ↑ 1.20 MB/s"


def test_offline_resets_throttle_so_next_sample_shows_immediately(
    tray: SpeedTrayIcon, collector: FakeCollector
) -> None:
    collector.speed_sampled.emit(5_020_000.0, 1_200_000.0)
    collector.session_changed.emit(False, 1, 1_700_000_000)
    collector.speed_sampled.emit(2_500_000.0, 500_000.0)
    assert tray.toolTip() == "↓ 2.50 MB/s  ↑ 500.00 KB/s"


@pytest.mark.parametrize(
    "reason",
    [
        QSystemTrayIcon.ActivationReason.Trigger,
        QSystemTrayIcon.ActivationReason.DoubleClick,
    ],
)
def test_trigger_and_double_click_open_main_window(
    tray: SpeedTrayIcon,
    window: FakeWindow,
    reason: QSystemTrayIcon.ActivationReason,
) -> None:
    tray.activated.emit(reason)
    assert window.bring_to_front_calls == 1


def test_context_activation_does_not_open_main_window(
    tray: SpeedTrayIcon, window: FakeWindow
) -> None:
    tray.activated.emit(QSystemTrayIcon.ActivationReason.Context)
    assert window.bring_to_front_calls == 0


def test_tray_icon_is_a_template_mask(tray: SpeedTrayIcon) -> None:
    assert not tray.icon().isNull()
    assert tray_icon().isMask() is True


def test_menu_has_open_separator_quit(tray: SpeedTrayIcon) -> None:
    menu = tray.contextMenu()
    assert menu is not None
    actions = menu.actions()
    assert [a.text() for a in actions if not a.isSeparator()] == [
        OPEN_ACTION_TEXT,
        QUIT_ACTION_TEXT,
    ]
    assert len(actions) == 3
    assert actions[1].isSeparator()


def test_open_action_brings_window_to_front(tray: SpeedTrayIcon, window: FakeWindow) -> None:
    open_action = tray.contextMenu().actions()[0]
    open_action.trigger()
    assert window.bring_to_front_calls == 1


def test_quit_cancelled_does_not_emit_quit_confirmed(
    tray: SpeedTrayIcon, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(tray, "_confirm_quit", lambda: False)
    emitted: list[bool] = []
    tray.quit_confirmed.connect(lambda: emitted.append(True))

    tray.contextMenu().actions()[2].trigger()

    assert emitted == []


def test_quit_confirmed_emits_quit_confirmed(
    qtbot, tray: SpeedTrayIcon, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(tray, "_confirm_quit", lambda: True)

    with qtbot.waitSignal(tray.quit_confirmed, timeout=1000):
        tray.contextMenu().actions()[2].trigger()
