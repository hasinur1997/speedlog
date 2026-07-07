"""Shared value formatting used by the tray, reports table and PDF export."""

from __future__ import annotations

from datetime import UTC, datetime
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

# SI units per docs/architecture-context.md: 1 MB = 1,000,000 bytes.
_BPS_PER_KB = 1_000
_BPS_PER_MB = 1_000_000
_DATE_FORMAT = "%Y-%m-%d"
_TIME_FORMAT = "%I:%M %p"


def _local_zone() -> ZoneInfo:
    """Best-effort local timezone as a ``ZoneInfo`` instance."""
    tzinfo = datetime.now().astimezone().tzinfo
    if isinstance(tzinfo, ZoneInfo):
        return tzinfo

    key = getattr(tzinfo, "key", None)
    if isinstance(key, str):
        try:
            return ZoneInfo(key)
        except ZoneInfoNotFoundError:
            pass

    return ZoneInfo("UTC")


def _local_datetime(ts: int) -> datetime:
    """Convert a UTC epoch timestamp to local time using ``zoneinfo``."""
    return datetime.fromtimestamp(ts, tz=UTC).astimezone(_local_zone())


def _format_local_time(dt: datetime) -> str:
    return dt.strftime(_TIME_FORMAT).lstrip("0")


def format_date(ts: int) -> str:
    """Format a UTC epoch timestamp as a local ``YYYY-MM-DD`` date."""
    return _local_datetime(ts).strftime(_DATE_FORMAT)


def format_time_range(start_ts: int, end_ts: int) -> str:
    """Format a local 12-hour time range, marking next-day rollover when needed."""
    start_dt = _local_datetime(start_ts)
    end_dt = _local_datetime(end_ts)
    day_delta = (end_dt.date() - start_dt.date()).days
    suffix = f" (+{day_delta})" if day_delta > 0 else ""
    return f"{_format_local_time(start_dt)} – {_format_local_time(end_dt)}{suffix}"


def format_speed(bps: float) -> str:
    """Format bytes/sec as ``X.XX MB/s`` (``X.XX KB/s`` below 1 MB/s), 2 decimals."""
    if bps < _BPS_PER_MB:
        return f"{bps / _BPS_PER_KB:.2f} KB/s"
    return f"{bps / _BPS_PER_MB:.2f} MB/s"
