"""Online/offline detection & session lifecycle (NST-304).

Interface-level connectivity: online iff at least one non-loopback,
non-virtual interface is up (``psutil.net_if_stats``). A state change is
confirmed only after ``CONNECTIVITY_DEBOUNCE_TICKS`` consecutive identical
checks, so brief flaps don't churn sessions. The watcher owns the session
lifecycle: confirmed online opens a session row; confirmed offline flushes
the segmenter, closes the session (``'disconnect'``) and resets the smoother.

Interface status is abstracted behind :class:`IfStatsSource` so tests use a
fake instead of psutil. Session transitions are reported via plain callbacks
(like ``Segmenter.on_segment_closed``); the CollectorService (NST-305) wires
them to Qt signals.
"""

from __future__ import annotations

import logging
from collections.abc import Callable, Mapping
from typing import Protocol

import psutil

from app import config
from app.collector.segmenter import Segmenter
from app.collector.smoother import Smoother
from app.data.repository import Repository

logger = logging.getLogger(__name__)


class IfStatsSource(Protocol):
    """Provider of per-interface up/down status."""

    def read_if_stats(self) -> Mapping[str, bool]:
        """Return ``{interface name: isup}``."""
        ...


class PsutilIfStatsSource:
    """Reads interface status from ``psutil.net_if_stats()``."""

    def read_if_stats(self) -> Mapping[str, bool]:
        return {name: stats.isup for name, stats in psutil.net_if_stats().items()}


class ConnectivityWatcher:
    """Debounced online/offline state machine that opens/closes sessions.

    Drive it with ``start(now)`` once at collector startup, then ``tick(now)``
    every sample interval. ``on_session_started`` / ``on_session_ended`` are
    invoked with ``(session_id, ts)`` after the repository has been updated.
    """

    def __init__(
        self,
        source: IfStatsSource,
        repository: Repository,
        segmenter: Segmenter,
        smoother: Smoother,
        debounce_ticks: int = config.CONNECTIVITY_DEBOUNCE_TICKS,
        on_session_started: Callable[[int, int], None] = lambda session_id, ts: None,
        on_session_ended: Callable[[int, int], None] = lambda session_id, ts: None,
    ) -> None:
        self._source = source
        self._repository = repository
        self._segmenter = segmenter
        self._smoother = smoother
        self._debounce_ticks = debounce_ticks
        self._on_session_started = on_session_started
        self._on_session_ended = on_session_ended
        self._online = False
        self._pending_count = 0
        self._session_id: int | None = None

    @property
    def online(self) -> bool:
        """Current confirmed (debounced) connectivity state."""
        return self._online

    @property
    def session_id(self) -> int | None:
        """Id of the open session, or ``None`` while offline."""
        return self._session_id

    def check(self) -> bool:
        """Raw, undebounced check: any non-loopback, non-virtual interface up?"""
        return any(
            isup and not name.startswith(config.EXCLUDED_INTERFACE_PREFIXES)
            for name, isup in self._source.read_if_stats().items()
        )

    def start(self, now: int) -> None:
        """Initialize at collector startup (``now`` is UTC epoch seconds).

        Closes sessions left dangling by a crash, then — if currently online —
        opens a session immediately (no debounce on the initial state).
        """
        closed = self._repository.close_dangling_sessions(now)
        if closed:
            logger.warning("Closed %d dangling session(s) at startup", closed)
        self._online = self.check()
        self._pending_count = 0
        if self._online:
            self._open_session(now)

    def tick(self, now: int) -> None:
        """Run one debounced check at ``now`` (UTC epoch seconds)."""
        if self.check() == self._online:
            self._pending_count = 0
            return
        self._pending_count += 1
        if self._pending_count < self._debounce_ticks:
            return
        self._pending_count = 0
        self._online = not self._online
        if self._online:
            self._open_session(now)
        else:
            self._close_session(now)

    def _open_session(self, now: int) -> None:
        self._session_id = self._repository.start_session(now)
        logger.info("Session %d started", self._session_id)
        self._on_session_started(self._session_id, now)

    def _close_session(self, now: int) -> None:
        session_id = self._session_id
        self._session_id = None
        if session_id is None:
            return
        self._segmenter.flush(now, session_id)
        self._repository.end_session(session_id, now, reason="disconnect")
        logger.info("Session %d ended (disconnect)", session_id)
        self._on_session_ended(session_id, now)
        self._smoother.reset()
