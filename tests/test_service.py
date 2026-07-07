"""Tests for app.collector.service (NST-305).

The service runs with fake sampler/if-stats sources and a tmp_path SQLite
file; pytest-qt's ``qtbot.waitSignal`` observes the cross-thread signals.
Verification of persisted state uses a separate connection on the test
thread (each thread owns its own connection).
"""

from __future__ import annotations

import sqlite3
import time
from collections.abc import Callable, Mapping
from pathlib import Path

import pytest

from app import config
from app.collector.service import CollectorService
from app.data import db
from app.data.repository import Repository

INTERVAL = 0.05  # fast test cadence; gap factor keeps real-time jitter tolerable
SIGNAL_TIMEOUT_MS = 3000


class FakeCounters:
    """Byte counters increasing by a fixed step per read; can be told to fail."""

    def __init__(self, step: int = 100_000, failures: int = 0) -> None:
        self._step = step
        self._failures = failures
        self._recv = 0
        self._sent = 0

    def read_counters(self) -> tuple[int, int]:
        if self._failures > 0:
            self._failures -= 1
            raise OSError("simulated counter read failure")
        self._recv += self._step
        self._sent += self._step
        return self._recv, self._sent


class FakeIfStats:
    """Interface stats with a switchable online flag."""

    def __init__(self, online: bool = True) -> None:
        self.online = online

    def read_if_stats(self) -> Mapping[str, bool]:
        return {"en0": self.online, "lo0": True}


@pytest.fixture
def make_service(qtbot, tmp_path: Path) -> Callable[..., tuple[CollectorService, Path]]:
    """Build services against a tmp DB; always stop them at teardown."""
    services: list[CollectorService] = []

    def _make(
        counters: FakeCounters | None = None, if_stats: FakeIfStats | None = None
    ) -> tuple[CollectorService, Path]:
        db_file = tmp_path / "data.db"
        service = CollectorService(
            db_path=db_file,
            sampler_source=counters if counters is not None else FakeCounters(),
            if_stats_source=if_stats if if_stats is not None else FakeIfStats(),
            interval=INTERVAL,
        )
        services.append(service)
        return service, db_file

    yield _make
    for service in services:
        service.stop()
        service.wait(config.COLLECTOR_JOIN_TIMEOUT_MS)


def test_speed_sampled_emitted_with_smoothed_values(qtbot, make_service) -> None:
    service, _ = make_service()

    with qtbot.waitSignal(service.speed_sampled, timeout=SIGNAL_TIMEOUT_MS) as blocker:
        service.start()

    dl_bps, ul_bps = blocker.args
    assert dl_bps > 0
    assert ul_bps > 0


def test_session_changed_emitted_on_start(qtbot, make_service) -> None:
    service, _ = make_service()

    with qtbot.waitSignal(service.session_changed, timeout=SIGNAL_TIMEOUT_MS) as blocker:
        service.start()

    assert blocker.args == [True, 1]


def test_stop_persists_open_segment_and_quit_session_and_joins_fast(qtbot, make_service) -> None:
    service, db_file = make_service()
    with qtbot.waitSignal(service.speed_sampled, timeout=SIGNAL_TIMEOUT_MS):
        service.start()

    service.stop()
    joined_at = time.monotonic()
    assert service.wait(config.COLLECTOR_JOIN_TIMEOUT_MS)
    assert time.monotonic() - joined_at < 3.0

    conn = sqlite3.connect(db_file)
    try:
        sessions = conn.execute("SELECT id, end_ts, end_reason FROM sessions").fetchall()
        records = conn.execute("SELECT session_id, start_ts, end_ts FROM speed_records").fetchall()
    finally:
        conn.close()
    assert len(sessions) == 1
    session_id, end_ts, end_reason = sessions[0]
    assert end_reason == "quit"
    assert end_ts is not None
    assert len(records) >= 1
    assert all(record[0] == session_id for record in records)


def test_stop_while_offline_closes_no_session(qtbot, make_service) -> None:
    service, db_file = make_service(if_stats=FakeIfStats(online=False))
    with qtbot.waitSignal(service.started, timeout=SIGNAL_TIMEOUT_MS):
        service.start()
    qtbot.wait(int(INTERVAL * 1000 * 4))  # let a few offline ticks run

    service.stop()
    assert service.wait(config.COLLECTOR_JOIN_TIMEOUT_MS)

    conn = sqlite3.connect(db_file)
    try:
        session_count = conn.execute("SELECT COUNT(*) FROM sessions").fetchone()[0]
        record_count = conn.execute("SELECT COUNT(*) FROM speed_records").fetchone()[0]
    finally:
        conn.close()
    assert session_count == 0
    assert record_count == 0


def test_start_recovers_dangling_session_from_previous_crash(qtbot, tmp_path: Path) -> None:
    db_file = tmp_path / "data.db"
    conn = db.get_connection(db_file)
    try:
        db.migrate(conn)
        repo = Repository(conn)
        dangling_id = repo.start_session(1_700_000_000)
    finally:
        conn.close()

    service = CollectorService(
        db_path=db_file,
        sampler_source=FakeCounters(),
        if_stats_source=FakeIfStats(),
        interval=INTERVAL,
    )
    try:
        with qtbot.waitSignal(service.session_changed, timeout=SIGNAL_TIMEOUT_MS) as blocker:
            service.start()

        assert blocker.args == [True, dangling_id + 1]

        service.stop()
        assert service.wait(config.COLLECTOR_JOIN_TIMEOUT_MS)
    finally:
        service.stop()
        service.wait(config.COLLECTOR_JOIN_TIMEOUT_MS)

    conn = sqlite3.connect(db_file)
    try:
        sessions = conn.execute(
            "SELECT id, start_ts, end_ts, end_reason FROM sessions ORDER BY id"
        ).fetchall()
    finally:
        conn.close()

    assert len(sessions) == 2
    assert sessions[0][0] == dangling_id
    assert sessions[0][2] is not None
    assert sessions[0][3] == "quit"
    assert sessions[1][0] == dangling_id + 1
    assert sessions[1][1] >= sessions[0][2]
    assert sessions[1][2] is not None
    assert sessions[1][3] == "quit"


def test_tick_errors_are_survived(qtbot, make_service) -> None:
    service, _ = make_service(counters=FakeCounters(failures=3))

    with qtbot.waitSignal(service.speed_sampled, timeout=SIGNAL_TIMEOUT_MS):
        service.start()  # sampling recovers after the failing reads


def test_module_has_no_ui_imports() -> None:
    import app.collector.service as service_module

    source = Path(service_module.__file__).read_text(encoding="utf-8")
    assert "QtWidgets" not in source
    assert "QtGui" not in source
    assert "PyQt" not in source
