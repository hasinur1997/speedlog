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

# Data layer
DB_FETCH_CHUNK_SIZE = 500  # rows per fetchmany() batch when streaming full result sets

# UI
PAGE_SIZE = 20  # report rows per page
ACCENT_COLOR = "#2E7CF6"


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
