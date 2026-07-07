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
# Tray/menu-bar template icon (live speed lives in the tray menu's first row)
TRAY_PIXMAP_HEIGHT = 22  # logical px; matches the macOS status bar image height
TRAY_PIXMAP_SCALE = 2  # retina backing scale for crisp menu-bar rendering
REPORTS_SURFACE_PADDING = 24
REPORTS_SECTION_SPACING = 18
REPORTS_FILTER_BAR_SPACING = 10
REPORTS_TABLE_ROW_HEIGHT = 42
# Tray tooltip refresh throttle: just under the 1s sample cadence so timing
# jitter in signal delivery doesn't drop every other update.
TRAY_TOOLTIP_MIN_INTERVAL_SECS = 0.9

# PDF export
PDF_PAGE_WIDTH = 612.0  # US Letter width in points
PDF_PAGE_HEIGHT = 792.0  # US Letter height in points
PDF_MARGIN_LEFT = 40.0
PDF_MARGIN_RIGHT = 40.0
PDF_MARGIN_TOP = 36.0
PDF_MARGIN_BOTTOM = 28.0
PDF_HEADER_HEIGHT = 88.0
PDF_SECTION_SPACING = 18.0
PDF_TABLE_CELL_PADDING = 10.0
PDF_TABLE_HEADER_HEIGHT = 24.0
PDF_TABLE_ROW_HEIGHT = 24.0
PDF_FOOTER_HEIGHT = 20.0
PDF_HEADER_TITLE_FONT_SIZE = 18
PDF_HEADER_NAME_FONT_SIZE = 12
PDF_HEADER_RANGE_FONT_SIZE = 10
PDF_TABLE_HEADER_FONT_SIZE = 10
PDF_TABLE_BODY_FONT_SIZE = 10
PDF_EMPTY_STATE_FONT_SIZE = 11
PDF_FOOTER_FONT_SIZE = 9
PDF_TABLE_HEADER_COLOR = "#EAF1FE"
PDF_TABLE_BORDER_COLOR = "#D6E2F5"
PDF_ROW_STRIPE_COLOR = "#F7FAFF"
PDF_FOOTER_TEXT_COLOR = "#5C6B7F"
EXPORT_NOTIFY_TIMEOUT_MS = 5000  # how long the export-finished tray notification stays up

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
