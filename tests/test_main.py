"""Tests for app.main bootstrap pieces (NST-401, NST-404)."""

from __future__ import annotations

import re
import sqlite3
import time
import uuid
from collections.abc import Callable, Mapping
from pathlib import Path

import pytest
from PySide6.QtNetwork import QLocalServer
from PySide6.QtWidgets import QApplication

from app import config
from app.collector.service import CollectorService
from app.main import (
    SingleInstanceGuard,
    configure_application,
    install_quit_shutdown,
    load_styles,
)

SIGNAL_TIMEOUT_MS = 3000
INTERVAL = 0.05


class FakeShutdownService:
    def __init__(self) -> None:
        self.stop_calls = 0
        self.wait_calls: list[int] = []

    def stop(self) -> None:
        self.stop_calls += 1

    def wait(self, msecs: int) -> bool:
        self.wait_calls.append(msecs)
        return True


class FakeCounters:
    def __init__(self, step: int = 100_000) -> None:
        self._step = step
        self._recv = 0
        self._sent = 0

    def read_counters(self) -> tuple[int, int]:
        self._recv += self._step
        self._sent += self._step
        return self._recv, self._sent


class FakeIfStats:
    def __init__(self, online: bool = True) -> None:
        self.online = online

    def read_if_stats(self) -> Mapping[str, bool]:
        return {"en0": self.online, "lo0": True}


def _guard_key() -> str:
    """Short unique key keeps the macOS local-socket path under AF_UNIX limits."""
    return f"sl-{uuid.uuid4().hex[:8]}"


def _local_server_supported() -> bool:
    """Sandboxed runs may disallow QLocalServer entirely; skip activation tests there."""
    key = _guard_key()
    server = QLocalServer()
    try:
        return server.listen(key)
    finally:
        server.close()
        QLocalServer.removeServer(key)


@pytest.fixture
def make_guard() -> Callable[[str], SingleInstanceGuard]:
    """Build guards on a per-test unique key; always release at teardown."""
    guards: list[SingleInstanceGuard] = []

    def _make(key: str) -> SingleInstanceGuard:
        guard = SingleInstanceGuard(key)
        guards.append(guard)
        return guard

    yield _make
    for guard in guards:
        guard.release()


def _disconnect_about_to_quit_handler(qapp: QApplication, handler: Callable[[], None]) -> None:
    try:
        qapp.aboutToQuit.disconnect(handler)
    except (RuntimeError, TypeError):
        pass


def _run_quit_cycle(qtbot, qapp: QApplication) -> None:
    with qtbot.waitSignal(qapp.aboutToQuit, timeout=SIGNAL_TIMEOUT_MS):
        qapp.aboutToQuit.emit()


def test_configure_application_sets_quit_policy_and_styles(qapp: QApplication) -> None:
    configure_application(qapp)

    assert QApplication.quitOnLastWindowClosed() is False
    assert qapp.styleSheet() == load_styles()
    assert not qapp.windowIcon().isNull()


def test_load_styles_reads_qss_file() -> None:
    styles = load_styles()
    assert "Speedlog" in styles


def test_load_styles_resolves_icon_urls_to_existing_files() -> None:
    styles = load_styles()
    assert "url(icons/" not in styles
    icon_paths = re.findall(r"url\(([^)]+\.svg)\)", styles)
    assert icon_paths, "expected the stylesheet to reference svg icons"
    for icon_path in icon_paths:
        assert Path(icon_path).is_file(), f"missing icon referenced by styles.qss: {icon_path}"


def test_first_instance_acquires(make_guard) -> None:
    key = _guard_key()
    assert make_guard(key).try_acquire() is True


def test_second_instance_does_not_acquire_and_activates_first(qtbot, make_guard) -> None:
    if not _local_server_supported():
        pytest.skip("QLocalServer listen is unavailable in this environment")

    key = _guard_key()
    first = make_guard(key)
    assert first.try_acquire() is True

    second = make_guard(key)
    with qtbot.waitSignal(first.activate_requested, timeout=SIGNAL_TIMEOUT_MS):
        assert second.try_acquire() is False


def test_release_allows_reacquisition(make_guard) -> None:
    key = _guard_key()
    first = make_guard(key)
    assert first.try_acquire() is True
    first.release()

    second = make_guard(key)
    assert second.try_acquire() is True


def test_install_quit_shutdown_stops_and_waits_on_about_to_quit(qtbot, qapp: QApplication) -> None:
    service = FakeShutdownService()
    handler = install_quit_shutdown(qapp, service)

    try:
        _run_quit_cycle(qtbot, qapp)
    finally:
        _disconnect_about_to_quit_handler(qapp, handler)

    assert service.stop_calls == 1
    assert service.wait_calls == [config.COLLECTOR_JOIN_TIMEOUT_MS]


def test_about_to_quit_flushes_open_segment_and_quit_session(
    qtbot, qapp: QApplication, tmp_path: Path
) -> None:
    db_file = tmp_path / "data.db"
    service = CollectorService(
        db_path=db_file,
        sampler_source=FakeCounters(),
        if_stats_source=FakeIfStats(),
        interval=INTERVAL,
    )
    handler = install_quit_shutdown(qapp, service)

    try:
        with qtbot.waitSignal(service.speed_sampled, timeout=SIGNAL_TIMEOUT_MS):
            service.start()

        quit_started_at = int(time.time())
        _run_quit_cycle(qtbot, qapp)
        quit_finished_at = int(time.time())

        assert service.isFinished()
        assert not service.isRunning()

        conn = sqlite3.connect(db_file)
        try:
            session = conn.execute(
                "SELECT end_ts, end_reason FROM sessions ORDER BY id DESC LIMIT 1"
            ).fetchone()
            record = conn.execute(
                "SELECT end_ts FROM speed_records ORDER BY id DESC LIMIT 1"
            ).fetchone()
        finally:
            conn.close()
    finally:
        service.stop()
        service.wait(config.COLLECTOR_JOIN_TIMEOUT_MS)
        _disconnect_about_to_quit_handler(qapp, handler)

    assert session is not None
    assert record is not None
    session_end_ts, end_reason = session
    (record_end_ts,) = record
    assert end_reason == "quit"
    assert quit_started_at <= session_end_ts <= quit_finished_at
    assert quit_started_at <= record_end_ts <= quit_finished_at
    assert record_end_ts == session_end_ts
