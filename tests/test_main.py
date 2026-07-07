"""Tests for app.main bootstrap pieces (NST-401)."""

from __future__ import annotations

import uuid
from collections.abc import Callable

import pytest
from PySide6.QtNetwork import QLocalServer
from PySide6.QtWidgets import QApplication

from app.main import SingleInstanceGuard, configure_application, load_styles

SIGNAL_TIMEOUT_MS = 3000


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


def test_configure_application_sets_quit_policy_and_styles(qapp: QApplication) -> None:
    configure_application(qapp)

    assert QApplication.quitOnLastWindowClosed() is False
    assert qapp.styleSheet() == load_styles()
    assert not qapp.windowIcon().isNull()


def test_load_styles_reads_qss_file() -> None:
    styles = load_styles()
    assert "Speedlog" in styles


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
