"""CollectorService(QThread) wiring Sampler → Smoother → Segmenter → Repository (NST-305).

The single collector thread: all psutil sampling and DB writes happen here,
on a connection created inside :meth:`run` (never shared with the UI thread).
UI communication is exclusively via Qt signals. ``stop()`` only requests
shutdown; the thread itself flushes the open segment, closes the session
(``'quit'``) and closes its connection before exiting — the caller then joins
with ``wait(config.COLLECTOR_JOIN_TIMEOUT_MS)``.
"""

from __future__ import annotations

import logging
import threading
import time
from pathlib import Path

from PySide6.QtCore import QThread, Signal

from app import config
from app.collector.connectivity import ConnectivityWatcher, IfStatsSource, PsutilIfStatsSource
from app.collector.sampler import PsutilSource, Sampler, SamplerSource
from app.collector.segmenter import Segmenter
from app.collector.smoother import Smoother
from app.data import db
from app.data.models import SpeedRecord
from app.data.repository import Repository

logger = logging.getLogger(__name__)


class CollectorService(QThread):
    """Collector thread: samples every second, records segments and sessions.

    Sources, interval and DB path are injectable for tests; defaults are the
    production psutil sources and :func:`config.db_path`.
    """

    speed_sampled = Signal(float, float)  # smoothed (download_bps, upload_bps)
    segment_closed = Signal()  # a segment row was persisted
    session_changed = Signal(bool, int, int)  # (online, session_id, changed_at_utc_ts)

    def __init__(
        self,
        db_path: Path | str | None = None,
        sampler_source: SamplerSource | None = None,
        if_stats_source: IfStatsSource | None = None,
        interval: float = config.SAMPLE_INTERVAL,
    ) -> None:
        super().__init__()
        self._db_path = db_path if db_path is not None else config.db_path()
        self._sampler_source = sampler_source if sampler_source is not None else PsutilSource()
        self._if_stats_source = (
            if_stats_source if if_stats_source is not None else PsutilIfStatsSource()
        )
        self._interval = interval
        self._stop_event = threading.Event()

    def stop(self) -> None:
        """Request shutdown (thread-safe, non-blocking).

        The run loop exits, flushes the open segment, ends the session with
        ``reason='quit'`` and closes its connection. The caller must then join
        via ``wait(config.COLLECTOR_JOIN_TIMEOUT_MS)``.
        """
        self._stop_event.set()

    def run(self) -> None:
        """Thread entry point: build the pipeline on this thread and tick until stopped."""
        try:
            conn = db.get_connection(self._db_path)
        except Exception:
            logger.exception("Collector failed to open database %s", self._db_path)
            return
        try:
            db.migrate(conn)
            repository = Repository(conn)
            smoother = Smoother()
            segmenter = Segmenter(
                on_segment_closed=lambda record: self._persist_record(repository, record)
            )
            watcher = ConnectivityWatcher(
                source=self._if_stats_source,
                repository=repository,
                segmenter=segmenter,
                smoother=smoother,
                on_session_started=lambda session_id, ts: self.session_changed.emit(
                    True, session_id, ts
                ),
                on_session_ended=lambda session_id, ts: self.session_changed.emit(
                    False, session_id, ts
                ),
            )
            sampler = Sampler(self._sampler_source, interval=self._interval)
            watcher.start(int(time.time()))
            self._loop(sampler, smoother, segmenter, watcher)
            self._shutdown(repository, segmenter, watcher)
        except Exception:
            logger.exception("Collector thread crashed")
        finally:
            conn.close()

    def _loop(
        self,
        sampler: Sampler,
        smoother: Smoother,
        segmenter: Segmenter,
        watcher: ConnectivityWatcher,
    ) -> None:
        """Fixed-cadence tick loop paced by the monotonic clock."""
        next_tick = time.monotonic() + self._interval
        while not self._stop_event.is_set():
            try:
                self._tick(sampler, smoother, segmenter, watcher)
            except Exception:
                logger.exception("Collector tick failed; continuing")
            delay = next_tick - time.monotonic()
            if delay > 0:
                self._stop_event.wait(delay)
                next_tick += self._interval
            else:
                # Fell behind (sleep/wake, long tick): resync instead of bursting.
                next_tick = time.monotonic() + self._interval

    def _tick(
        self,
        sampler: Sampler,
        smoother: Smoother,
        segmenter: Segmenter,
        watcher: ConnectivityWatcher,
    ) -> None:
        now = int(time.time())
        watcher.tick(now)
        sample = sampler.tick(time.monotonic())
        if sample is None:
            return
        session_id = watcher.session_id
        if session_id is None:
            return
        smoothed = smoother.push(sample)
        self.speed_sampled.emit(smoothed.dl_bps, smoothed.ul_bps)
        segmenter.push(now, smoothed, session_id)

    def _persist_record(self, repository: Repository, record: SpeedRecord) -> None:
        repository.insert_record(record)
        self.segment_closed.emit()

    def _shutdown(
        self, repository: Repository, segmenter: Segmenter, watcher: ConnectivityWatcher
    ) -> None:
        """Flush the open segment and close the session before the thread exits."""
        session_id = watcher.session_id
        if session_id is None:
            return
        now = int(time.time())
        try:
            segmenter.flush(now, session_id)
            repository.end_session(session_id, now, reason="quit")
        except Exception:
            logger.exception("Failed to persist final segment/session on quit")
            return
        logger.info("Session %d ended (quit)", session_id)
        self.session_changed.emit(False, session_id, now)
