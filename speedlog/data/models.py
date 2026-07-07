"""Dataclasses for the data layer: :class:`Session` and :class:`SpeedRecord` (NST-202)."""

from __future__ import annotations

from dataclasses import dataclass


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
