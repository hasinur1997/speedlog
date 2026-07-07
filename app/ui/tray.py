"""QSystemTrayIcon with live speed readout and context menu (NST-402/NST-403).

Lives on the Qt main thread. Collector signals (``speed_sampled``,
``session_changed``) are connected to the slots below; the collector thread
never touches this widget directly.
"""

from __future__ import annotations

import math
import time
from pathlib import Path
from typing import TYPE_CHECKING

from PySide6.QtCore import QObject, QPointF, QRectF, Qt, Signal, Slot
from PySide6.QtGui import QIcon, QPainter, QPen, QPixmap
from PySide6.QtWidgets import QMenu, QMessageBox, QSystemTrayIcon

from app import config
from app.formatting import format_speed

if TYPE_CHECKING:
    from app.ui.main_window import MainWindow

OFFLINE_TEXT = "— offline"
EXPORT_NOTIFY_TEXT_TEMPLATE = "Report exported: {name}"
OPEN_ACTION_TEXT = "Open Speedlog"
QUIT_ACTION_TEXT = "Quit"
QUIT_CONFIRM_TEXT = "Quitting stops speed tracking. Quit?"

_OPEN_REASONS = (
    QSystemTrayIcon.ActivationReason.Trigger,
    QSystemTrayIcon.ActivationReason.DoubleClick,
)


# Speed-gauge glyph geometry, as ratios of the square glyph cell.
_GAUGE_PAD_RATIO = 0.14
_GAUGE_STROKE_RATIO = 0.10
_GAUGE_START_ANGLE = -30  # Qt angles: 0° at 3 o'clock, CCW positive; gap at the bottom
_GAUGE_SPAN_ANGLE = 240
_GAUGE_NEEDLE_ANGLE = 60  # needle points up-right, "fast" side of the dial
_GAUGE_NEEDLE_RATIO = 0.62  # needle length relative to the arc radius


def _paint_gauge(painter: QPainter, rect: QRectF) -> None:
    """Speedometer glyph: open arc with a needle, drawn in mask black."""
    pad = rect.height() * _GAUGE_PAD_RATIO
    arc_rect = rect.adjusted(pad, pad, -pad, -pad)
    pen = QPen(Qt.GlobalColor.black)
    pen.setWidthF(rect.height() * _GAUGE_STROKE_RATIO)
    pen.setCapStyle(Qt.PenCapStyle.RoundCap)
    painter.setPen(pen)
    painter.setBrush(Qt.BrushStyle.NoBrush)
    painter.drawArc(arc_rect, _GAUGE_START_ANGLE * 16, _GAUGE_SPAN_ANGLE * 16)
    center = arc_rect.center()
    radius = (arc_rect.width() / 2) * _GAUGE_NEEDLE_RATIO
    angle = math.radians(_GAUGE_NEEDLE_ANGLE)
    tip = QPointF(center.x() + radius * math.cos(angle), center.y() - radius * math.sin(angle))
    painter.drawLine(center, tip)


def tray_icon() -> QIcon:
    """Monochrome mask icon so macOS renders it as a light/dark-adaptive template."""
    scale = config.TRAY_PIXMAP_SCALE
    size = config.TRAY_PIXMAP_HEIGHT * scale
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    _paint_gauge(painter, QRectF(0, 0, size, size))
    painter.end()
    pixmap.setDevicePixelRatio(scale)
    icon = QIcon(pixmap)
    icon.setIsMask(True)
    return icon


class SpeedTrayIcon(QSystemTrayIcon):
    """Menu-bar presence: live speed tooltip, offline marker, opens the main window."""

    quit_confirmed = Signal()

    def __init__(self, window: MainWindow, parent: QObject | None = None) -> None:
        super().__init__(tray_icon(), parent)
        self.setObjectName("trayIcon")
        self._window = window
        self._last_tooltip_monotonic = float("-inf")
        self.setToolTip(OFFLINE_TEXT)
        self.activated.connect(self._on_activated)

        self._menu = QMenu()
        self._menu.setObjectName("trayMenu")
        # Status row, not clickable: live speed readout at the top of the menu.
        self.speed_action = self._menu.addAction(OFFLINE_TEXT)
        self.speed_action.setObjectName("traySpeedAction")
        self.speed_action.setEnabled(False)
        self._menu.addSeparator()
        open_action = self._menu.addAction(OPEN_ACTION_TEXT)
        open_action.setObjectName("trayOpenAction")
        open_action.triggered.connect(self._on_open)
        self._menu.addSeparator()
        quit_action = self._menu.addAction(QUIT_ACTION_TEXT)
        quit_action.setObjectName("trayQuitAction")
        quit_action.triggered.connect(self._on_quit)
        self.setContextMenu(self._menu)

    @Slot(float, float)
    def on_speed_sampled(self, download_bps: float, upload_bps: float) -> None:
        """Refresh the menu speed row and tooltip with the latest smoothed speeds, ≤ 1/s."""
        now = time.monotonic()
        if now - self._last_tooltip_monotonic < config.TRAY_TOOLTIP_MIN_INTERVAL_SECS:
            return
        self._last_tooltip_monotonic = now
        status_text = f"↓ {format_speed(download_bps)}  ↑ {format_speed(upload_bps)}"
        self.setToolTip(status_text)
        self.speed_action.setText(status_text)

    @Slot(bool, int, int)
    def on_session_changed(self, online: bool, session_id: int, changed_at: int) -> None:
        """Show the offline marker; reset the throttle so the next sample shows at once."""
        del session_id, changed_at
        if online:
            return
        self._last_tooltip_monotonic = float("-inf")
        self.setToolTip(OFFLINE_TEXT)
        self.speed_action.setText(OFFLINE_TEXT)

    @Slot(str)
    def on_export_succeeded(self, out_path_str: str) -> None:
        """Show a simple system notification when a PDF export finishes."""
        self.showMessage(
            config.APP_NAME,
            EXPORT_NOTIFY_TEXT_TEMPLATE.format(name=Path(out_path_str).name),
            QSystemTrayIcon.MessageIcon.Information,
            config.EXPORT_NOTIFY_TIMEOUT_MS,
        )

    def _on_activated(self, reason: QSystemTrayIcon.ActivationReason) -> None:
        if reason in _OPEN_REASONS:
            self._window.bring_to_front()

    def _on_open(self) -> None:
        self._window.bring_to_front()

    def _on_quit(self) -> None:
        if self._confirm_quit():
            self.quit_confirmed.emit()

    def _confirm_quit(self) -> bool:
        """Modal confirm dialog; True only when the user picks Quit."""
        box = QMessageBox(self._window)
        box.setObjectName("quitConfirmDialog")
        box.setWindowTitle(config.APP_NAME)
        box.setIcon(QMessageBox.Icon.Question)
        box.setText(QUIT_CONFIRM_TEXT)
        quit_button = box.addButton(QUIT_ACTION_TEXT, QMessageBox.ButtonRole.DestructiveRole)
        cancel_button = box.addButton(QMessageBox.StandardButton.Cancel)
        box.setDefaultButton(cancel_button)
        box.exec()
        return box.clickedButton() is quit_button
