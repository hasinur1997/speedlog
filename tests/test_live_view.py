"""Tests for app.ui.live_view (NST-501/NST-502)."""

from __future__ import annotations

from datetime import UTC, datetime
from zoneinfo import ZoneInfo

import pytest
from PySide6.QtCore import Qt

import app.ui.live_view as live_view_module
from app import config
from app.ui.live_view import LiveView
from app.ui.main_window import MainWindow


@pytest.fixture
def live_view(qtbot) -> LiveView:
    widget = LiveView()
    qtbot.addWidget(widget)
    widget.show()
    qtbot.waitExposed(widget)
    return widget


def test_speed_sampled_updates_labels_when_visible(live_view: LiveView) -> None:
    live_view.on_speed_sampled(5_020_000.0, 500_000.0)

    assert live_view.download_label.text() == "↓ 5.02 MB/s"
    assert live_view.upload_label.text() == "↑ 500.00 KB/s"


def test_live_view_exposes_surface_and_chart_styling_hooks(live_view: LiveView) -> None:
    assert live_view.surface.objectName() == "liveSurface"
    assert live_view.surface.testAttribute(Qt.WidgetAttribute.WA_StyledBackground)
    assert live_view.sparkline.parentWidget() is live_view.surface
    assert live_view.sparkline.testAttribute(Qt.WidgetAttribute.WA_StyledBackground)


def test_session_changed_updates_connected_since_and_offline(
    live_view: LiveView, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(live_view_module, "_local_zone", lambda: ZoneInfo("UTC"))
    live_view.on_speed_sampled(5_020_000.0, 1_200_000.0)

    connected_at = int(datetime(2026, 7, 7, 10, 1, tzinfo=UTC).timestamp())
    live_view.on_session_changed(True, 1, connected_at)
    assert live_view.session_label.text() == "Connected since 10:01 AM"

    live_view.on_session_changed(False, 1, connected_at + 60)
    assert live_view.session_label.text() == "Offline"
    assert live_view.download_label.text() == "↓ 0.00 KB/s"
    assert live_view.upload_label.text() == "↑ 0.00 KB/s"


def test_hidden_tab_skips_speed_repaint_until_visible(qtbot) -> None:
    window = MainWindow()
    qtbot.addWidget(window)
    window.show()
    qtbot.waitExposed(window)

    live_view = window.live_view
    live_view.on_speed_sampled(1_000_000.0, 500_000.0)
    assert live_view.download_label.text() == "↓ 1.00 MB/s"
    assert live_view.upload_label.text() == "↑ 500.00 KB/s"

    window.tabs.setCurrentIndex(1)
    qtbot.waitUntil(lambda: not live_view.isVisible(), timeout=1000)

    live_view.on_speed_sampled(5_020_000.0, 1_200_000.0)
    assert live_view.download_label.text() == "↓ 1.00 MB/s"
    assert live_view.upload_label.text() == "↑ 500.00 KB/s"

    window.tabs.setCurrentIndex(0)
    qtbot.waitUntil(lambda: live_view.isVisible(), timeout=1000)
    qtbot.waitUntil(
        lambda: live_view.download_label.text() == "↓ 5.02 MB/s",
        timeout=1000,
    )
    assert live_view.upload_label.text() == "↑ 1.20 MB/s"


def test_sparkline_caps_buffer_at_60_samples(live_view: LiveView) -> None:
    for sample in range(200):
        live_view.on_speed_sampled(float(sample), float(sample * 2))

    assert live_view.sparkline.sample_count == config.LIVE_SPARKLINE_WINDOW_SAMPLES
    assert live_view.sparkline.download_samples[0] == 140.0
    assert live_view.sparkline.download_samples[-1] == 199.0
    assert live_view.sparkline.upload_samples[0] == 280.0
    assert live_view.sparkline.upload_samples[-1] == 398.0


def test_hidden_tab_skips_sparkline_redraw_until_visible(qtbot) -> None:
    window = MainWindow()
    qtbot.addWidget(window)
    window.show()
    qtbot.waitExposed(window)

    live_view = window.live_view
    live_view.on_speed_sampled(1.0, 2.0)
    visible_redraw_count = live_view.sparkline.redraw_count

    window.tabs.setCurrentIndex(1)
    qtbot.waitUntil(lambda: not live_view.isVisible(), timeout=1000)

    live_view.on_speed_sampled(3.0, 4.0)
    live_view.on_speed_sampled(5.0, 6.0)

    assert live_view.sparkline.sample_count == 3
    assert live_view.sparkline.redraw_count == visible_redraw_count

    window.tabs.setCurrentIndex(0)
    qtbot.waitUntil(lambda: live_view.isVisible(), timeout=1000)
    qtbot.waitUntil(
        lambda: live_view.sparkline.redraw_count == visible_redraw_count + 1,
        timeout=1000,
    )
