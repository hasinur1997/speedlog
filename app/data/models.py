"""Dataclasses and enums shared by the data and report-filter layers."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, time
from enum import Enum


class ReportFilterMode(Enum):
    """UI filter modes supported by the reports filter bar."""

    DATE = "date"
    DATE_RANGE = "date_range"
    DATE_TIME = "date_time"
    DATE_TIME_RANGE = "date_time_range"


@dataclass(slots=True)
class ReportFilterUiState:
    """Raw UI state captured from the reports filter panel.

    ``mode=None`` represents "no filter" after Reset. Otherwise the active mode
    determines which fields are meaningful:

    - ``DATE``: ``start_date``
    - ``DATE_RANGE``: ``start_date`` + ``end_date``
    - ``DATE_TIME``: ``start_date`` + ``start_time``
    - ``DATE_TIME_RANGE``: ``start_date`` + ``start_time`` + ``end_time``
    """

    mode: ReportFilterMode | None = None
    start_date: date | None = None
    end_date: date | None = None
    start_time: time | None = None
    end_time: time | None = None


@dataclass(slots=True)
class Session:
    """A connectivity session (row in ``sessions``).

    Timestamps are UTC epoch seconds. ``end_ts``/``end_reason`` are ``None``
    while the session is open; ``end_reason`` is ``'disconnect'`` or ``'quit'``.
    """

    start_ts: int
    end_ts: int | None = None
    end_reason: str | None = None
    id: int | None = None


@dataclass(slots=True)
class SpeedRecord:
    """A same-speed time segment (row in ``speed_records``).

    Timestamps are UTC epoch seconds; speeds are representative bytes/sec
    means for the segment.
    """

    session_id: int
    start_ts: int
    end_ts: int
    download_bps: float
    upload_bps: float
    id: int | None = None


@dataclass(slots=True)
class ReportFilter:
    """UTC time-range filter for report queries.

    Bounds are UTC epoch seconds, already resolved from local time by the UI
    layer — the repository is timezone-agnostic. ``None`` means unbounded on
    that side; both ``None`` selects all records. A record matches when its
    time range OVERLAPS the filter range
    (``start_ts <= range_end_ts AND end_ts >= range_start_ts``).
    """

    range_start_ts: int | None = None
    range_end_ts: int | None = None
