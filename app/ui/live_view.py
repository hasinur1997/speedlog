"""Live tab: current speeds, session info, and sparkline (NST-501/NST-502)."""

from __future__ import annotations

from collections import deque
from datetime import UTC, datetime
from zoneinfo import ZoneInfo

from PySide6.QtCore import Qt, Slot
from PySide6.QtGui import QColor, QFont, QShowEvent
from PySide6.QtWidgets import QLabel, QSizePolicy, QVBoxLayout, QWidget

from app import config
from app.formatting import format_speed

try:
    import pyqtgraph
except ImportError:  # pragma: no cover - exercised only when the optional dependency is absent
    pyqtgraph = None

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


class _LiveSparkline(QWidget):
    """Rolling download/upload sparkline with a fixed 60-sample history."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("liveSparkline")
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setFixedHeight(config.LIVE_SPARKLINE_HEIGHT)
        self._download_history: deque[float] = deque(maxlen=config.LIVE_SPARKLINE_WINDOW_SAMPLES)
        self._upload_history: deque[float] = deque(maxlen=config.LIVE_SPARKLINE_WINDOW_SAMPLES)
        self._redraw_count = 0
        self._plot_widget = None
        self._download_curve = None
        self._upload_curve = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        if pyqtgraph is None:
            fallback = QLabel("Live chart unavailable until pyqtgraph is installed.", self)
            fallback.setObjectName("liveSparklineFallback")
            fallback.setAlignment(Qt.AlignmentFlag.AlignCenter)
            fallback.setWordWrap(True)
            layout.addWidget(fallback)
            return

        self._plot_widget = pyqtgraph.PlotWidget(self)
        self._plot_widget.setObjectName("liveSparklinePlot")
        self._plot_widget.setBackground("transparent")
        self._plot_widget.setMenuEnabled(False)
        self._plot_widget.setMouseEnabled(x=False, y=False)
        self._plot_widget.hideButtons()
        self._plot_widget.hideAxis("bottom")
        self._plot_widget.hideAxis("left")
        self._plot_widget.enableAutoRange(x=False, y=False)
        self._plot_widget.setXRange(
            -config.LIVE_SPARKLINE_WINDOW_SAMPLES + 1,
            0,
            padding=0.0,
        )
        self._plot_widget.setYRange(0.0, config.LIVE_SPARKLINE_MIN_Y_MAX_BPS, padding=0.0)
        layout.addWidget(self._plot_widget)

        self._download_curve = self._plot_widget.plot(
            pen=pyqtgraph.mkPen(
                QColor(config.LIVE_SPARKLINE_DOWNLOAD_COLOR),
                width=config.LIVE_SPARKLINE_LINE_WIDTH,
            )
        )
        self._upload_curve = self._plot_widget.plot(
            pen=pyqtgraph.mkPen(
                QColor(config.LIVE_SPARKLINE_UPLOAD_COLOR),
                width=config.LIVE_SPARKLINE_LINE_WIDTH,
            )
        )

    @property
    def sample_count(self) -> int:
        return len(self._download_history)

    @property
    def redraw_count(self) -> int:
        return self._redraw_count

    @property
    def download_samples(self) -> tuple[float, ...]:
        return tuple(self._download_history)

    @property
    def upload_samples(self) -> tuple[float, ...]:
        return tuple(self._upload_history)

    def push_sample(self, download_bps: float, upload_bps: float) -> None:
        self._download_history.append(download_bps)
        self._upload_history.append(upload_bps)

    def redraw(self) -> None:
        self._redraw_count += 1
        if self._download_curve is None or self._upload_curve is None or self._plot_widget is None:
            return

        count = self.sample_count
        if count == 0:
            self._download_curve.setData([], [])
            self._upload_curve.setData([], [])
            self._plot_widget.setYRange(0.0, config.LIVE_SPARKLINE_MIN_Y_MAX_BPS, padding=0.0)
            return

        x_values = list(range(-count + 1, 1))
        download_values = list(self._download_history)
        upload_values = list(self._upload_history)
        self._download_curve.setData(x_values, download_values)
        self._upload_curve.setData(x_values, upload_values)

        y_max = max(
            max(download_values),
            max(upload_values),
            config.LIVE_SPARKLINE_MIN_Y_MAX_BPS,
        )
        self._plot_widget.setYRange(
            0.0,
            y_max,
            padding=config.LIVE_SPARKLINE_Y_PADDING_RATIO,
        )


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
        self.sparkline = _LiveSparkline(self)

        layout.addWidget(self.download_label)
        layout.addWidget(self.upload_label)
        layout.addWidget(self.session_label)
        layout.addWidget(self.sparkline)
        layout.addStretch(1)

        self._set_speed_labels(0.0, 0.0)

    @Slot(float, float)
    def on_speed_sampled(self, download_bps: float, upload_bps: float) -> None:
        """Cache the latest speeds; only repaint labels while the tab is visible."""
        self._latest_download_bps = download_bps
        self._latest_upload_bps = upload_bps
        self.sparkline.push_sample(download_bps, upload_bps)
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
        self.sparkline.redraw()

    def _set_speed_labels(self, download_bps: float, upload_bps: float) -> None:
        self.download_label.setText(f"↓ {format_speed(download_bps)}")
        self.upload_label.setText(f"↑ {format_speed(upload_bps)}")
