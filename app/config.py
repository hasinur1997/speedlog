"""Constants, paths, and settings — single source of truth for all tunables (NST-102)."""

import os
import platform
from pathlib import Path

APP_NAME = "Speedlog"
LOG_FILE_NAME = "app.log"
LOG_FILE_MAX_BYTES = 5_000_000
LOG_FILE_BACKUP_COUNT = 3

# Collector tunables (see docs/architecture-context.md, "Segmenter algorithm")
SAMPLE_INTERVAL = 1.0  # seconds between psutil samples
SAMPLE_GAP_FACTOR = 3.0  # elapsed > factor * interval means sleep/wake: discard tick, resync
# Virtual/loopback interfaces excluded from counter sums unless they are the only active ones
EXCLUDED_INTERFACE_PREFIXES = ("lo", "awdl", "utun")
SMOOTH_WINDOW = 5  # samples in the moving average
BAND_TOLERANCE_PCT = 0.10  # band = max(pct * mean, floor)
BAND_TOLERANCE_FLOOR_BPS = 250_000  # 0.25 MB/s absolute floor, bytes/sec
HYSTERESIS_TICKS = 5  # consecutive out-of-band samples to split a segment
MIN_SEGMENT_SECS = 5  # shorter segments merge into a neighbor
CONNECTIVITY_DEBOUNCE_TICKS = 3  # consecutive identical checks to confirm an online/offline change
COLLECTOR_JOIN_TIMEOUT_MS = 3000  # max wait for the collector thread to exit after stop()

# Data layer
DB_FETCH_CHUNK_SIZE = 500  # rows per fetchmany() batch when streaming full result sets

# UI
PAGE_SIZE = 20  # report rows per page
PAGINATION_MAX_VISIBLE_BUTTONS = 7  # numbered page buttons before collapsing with ellipses
ACCENT_COLOR = "#2E7CF6"
MAIN_WINDOW_WIDTH = 900
MAIN_WINDOW_HEIGHT = 620
MAIN_WINDOW_CONTENT_MARGIN = 20
LIVE_VIEW_MARGIN = 36
LIVE_VIEW_SPACING = 12
LIVE_SPEED_LABEL_POINT_SIZE = 32
LIVE_SESSION_LABEL_POINT_SIZE = 14
LIVE_SPARKLINE_WINDOW_SAMPLES = 60  # fixed 60-second chart at the 1 Hz sample cadence
LIVE_SPARKLINE_HEIGHT = 140
LIVE_SPARKLINE_LINE_WIDTH = 2
LIVE_SPARKLINE_DOWNLOAD_COLOR = ACCENT_COLOR
LIVE_SPARKLINE_UPLOAD_COLOR = "#22A06B"
LIVE_SPARKLINE_MIN_Y_MAX_BPS = 1.0
LIVE_SPARKLINE_Y_PADDING_RATIO = 0.12
APP_ICON_SIZE = 64  # px, square pixmap painted at startup (no bundled asset yet)
APP_ICON_GLYPH = "S"
APP_ICON_GLYPH_COLOR = "#FFFFFF"
REPORTS_SURFACE_PADDING = 24
REPORTS_SECTION_SPACING = 18
REPORTS_TABLE_ROW_HEIGHT = 42
# Tray tooltip refresh throttle: just under the 1s sample cadence so timing
# jitter in signal delivery doesn't drop every other update.
TRAY_TOOLTIP_MIN_INTERVAL_SECS = 0.9

# Single-instance guard (QLocalServer name; second launch connects and asks to activate)
SINGLE_INSTANCE_KEY = "com.speedlog.app.single-instance"
SINGLE_INSTANCE_TIMEOUT_MS = 200  # connect/write timeout when pinging the first instance


def data_dir() -> Path:
    """Platform-correct application data directory, created if missing."""
    system = platform.system()
    if system == "Darwin":
        path = Path.home() / "Library" / "Application Support" / APP_NAME
    elif system == "Windows":
        appdata = os.environ.get("APPDATA")
        base = Path(appdata) if appdata else Path.home() / "AppData" / "Roaming"
        path = base / APP_NAME
    else:  # Linux and other POSIX: XDG Base Directory spec
        xdg = os.environ.get("XDG_DATA_HOME")
        base = Path(xdg) if xdg else Path.home() / ".local" / "share"
        path = base / APP_NAME
    path.mkdir(parents=True, exist_ok=True)
    return path


def db_path() -> Path:
    """Path to the SQLite database file."""
    return data_dir() / "data.db"


def log_dir() -> Path:
    """Platform-correct log directory, created if missing."""
    system = platform.system()
    if system == "Darwin":
        path = Path.home() / "Library" / "Logs" / APP_NAME
    elif system == "Windows":
        path = data_dir() / "logs"
    else:  # Linux and other POSIX: XDG Base Directory spec (state data)
        xdg = os.environ.get("XDG_STATE_HOME")
        base = Path(xdg) if xdg else Path.home() / ".local" / "state"
        path = base / APP_NAME / "logs"
    path.mkdir(parents=True, exist_ok=True)
    return path
