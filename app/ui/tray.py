"""QSystemTrayIcon with live speed readout (NST-402; menu + quit in NST-403).

Lives on the Qt main thread. Collector signals (``speed_sampled``,
``session_changed``) are connected to the slots below; the collector thread
never touches this widget directly.
"""

from __future__ import annotations

import time
from typing import TYPE_CHECKING

from PySide6.QtCore import QObject, Qt, Slot
from PySide6.QtGui import QIcon, QPainter, QPixmap
from PySide6.QtWidgets import QSystemTrayIcon

from app import config
from app.formatting import format_speed

if TYPE_CHECKING:
    from app.ui.main_window import MainWindow

OFFLINE_TEXT = "— offline"

_OPEN_REASONS = (
    QSystemTrayIcon.ActivationReason.Trigger,
    QSystemTrayIcon.ActivationReason.DoubleClick,
)


def tray_icon() -> QIcon:
    """Monochrome mask icon so macOS renders it as a light/dark-adaptive template."""
    size = config.APP_ICON_SIZE
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setPen(Qt.GlobalColor.black)
    font = painter.font()
    font.setBold(True)
    font.setPixelSize(int(size * 0.6))
    painter.setFont(font)
    painter.drawText(pixmap.rect(), Qt.AlignmentFlag.AlignCenter, config.APP_ICON_GLYPH)
    painter.end()
    icon = QIcon(pixmap)
    icon.setIsMask(True)
    return icon


class SpeedTrayIcon(QSystemTrayIcon):
    """Menu-bar presence: live speed tooltip, offline marker, opens the main window."""

    def __init__(self, window: MainWindow, parent: QObject | None = None) -> None:
        super().__init__(tray_icon(), parent)
        self.setObjectName("trayIcon")
        self._window = window
        self._last_tooltip_monotonic = float("-inf")
        self.setToolTip(OFFLINE_TEXT)
        self.activated.connect(self._on_activated)

    @Slot(float, float)
    def on_speed_sampled(self, download_bps: float, upload_bps: float) -> None:
        """Refresh the tooltip with the latest smoothed speeds, at most once per second."""
        now = time.monotonic()
        if now - self._last_tooltip_monotonic < config.TRAY_TOOLTIP_MIN_INTERVAL_SECS:
            return
        self._last_tooltip_monotonic = now
        self.setToolTip(f"↓ {format_speed(download_bps)}  ↑ {format_speed(upload_bps)}")

    @Slot(bool, int)
    def on_session_changed(self, online: bool, session_id: int) -> None:
        """Show the offline marker; reset the throttle so the next sample shows at once."""
        if online:
            return
        self._last_tooltip_monotonic = float("-inf")
        self.setToolTip(OFFLINE_TEXT)

    def _on_activated(self, reason: QSystemTrayIcon.ActivationReason) -> None:
        if reason in _OPEN_REASONS:
            self._window.bring_to_front()
