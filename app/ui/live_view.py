"""Live tab: current speeds + session info (NST-501)."""

from __future__ import annotations

from datetime import UTC, datetime
from zoneinfo import ZoneInfo

from PySide6.QtCore import Qt, Slot
from PySide6.QtGui import QFont, QShowEvent
from PySide6.QtWidgets import QLabel, QSizePolicy, QVBoxLayout, QWidget

from app import config
from app.formatting import format_speed

OFFLINE_TEXT = "Offline"
CONNECTED_SINCE_PREFIX = "Connected since "


def _local_zone() -> ZoneInfo | None:
    """Best-effort local timezone; prefer a real ``ZoneInfo`` when available."""
    tzinfo = datetime.now().astimezone().tzinfo
    if isinstance(tzinfo, ZoneInfo):
        return tzinfo
    key = getattr(tzinfo, "key", None)
    if isinstance(key, str):
        return ZoneInfo(key)
    return None


def _format_connected_since(ts: int) -> str:
    """Render a UTC epoch timestamp as local ``10:01 AM`` text."""
    local_zone = _local_zone()
    local_dt = datetime.fromtimestamp(ts, tz=UTC)
    if local_zone is not None:
        local_dt = local_dt.astimezone(local_zone)
    else:
        local_dt = local_dt.astimezone()
    return local_dt.strftime("%I:%M %p").lstrip("0")


class LiveView(QWidget):
    """Large current speeds and current session status for the Live tab."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("liveTab")
        self._latest_download_bps = 0.0
        self._latest_upload_bps = 0.0
        self._speed_update_pending = False

        layout = QVBoxLayout(self)
        layout.setContentsMargins(
            config.LIVE_VIEW_MARGIN,
            config.LIVE_VIEW_MARGIN,
            config.LIVE_VIEW_MARGIN,
            config.LIVE_VIEW_MARGIN,
        )
        layout.setSpacing(config.LIVE_VIEW_SPACING)
        layout.addStretch(1)

        self.download_label = self._build_speed_label("downloadSpeedLabel")
        self.upload_label = self._build_speed_label("uploadSpeedLabel")
        self.session_label = QLabel(OFFLINE_TEXT, self)
        self.session_label.setObjectName("sessionStatusLabel")
        self.session_label.setAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop)
        session_font = QFont(self.session_label.font())
        session_font.setPointSize(config.LIVE_SESSION_LABEL_POINT_SIZE)
        self.session_label.setFont(session_font)
        self.session_label.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Preferred,
        )

        layout.addWidget(self.download_label)
        layout.addWidget(self.upload_label)
        layout.addWidget(self.session_label)
        layout.addStretch(1)

        self._set_speed_labels(0.0, 0.0)

    @Slot(float, float)
    def on_speed_sampled(self, download_bps: float, upload_bps: float) -> None:
        """Cache the latest speeds; only repaint labels while the tab is visible."""
        self._latest_download_bps = download_bps
        self._latest_upload_bps = upload_bps
        self._speed_update_pending = True
        if self.isVisible():
            self._apply_pending_speed_update()

    @Slot(bool, int, int)
    def on_session_changed(self, online: bool, session_id: int, changed_at: int) -> None:
        """Show the session start time while online, or ``Offline`` when disconnected."""
        del session_id
        if online:
            self.session_label.setText(
                f"{CONNECTED_SINCE_PREFIX}{_format_connected_since(changed_at)}"
            )
            return
        self.session_label.setText(OFFLINE_TEXT)
        self.on_speed_sampled(0.0, 0.0)

    def showEvent(self, event: QShowEvent) -> None:
        super().showEvent(event)
        self._apply_pending_speed_update()

    def _build_speed_label(self, object_name: str) -> QLabel:
        label = QLabel(self)
        label.setObjectName(object_name)
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        speed_font = QFont(label.font())
        speed_font.setPointSize(config.LIVE_SPEED_LABEL_POINT_SIZE)
        speed_font.setBold(True)
        label.setFont(speed_font)
        return label

    def _apply_pending_speed_update(self) -> None:
        if not self._speed_update_pending:
            return
        self._speed_update_pending = False
        self._set_speed_labels(self._latest_download_bps, self._latest_upload_bps)

    def _set_speed_labels(self, download_bps: float, upload_bps: float) -> None:
        self.download_label.setText(f"↓ {format_speed(download_bps)}")
        self.upload_label.setText(f"↑ {format_speed(upload_bps)}")
