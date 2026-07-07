"""Tests for speedlog.data.models and speedlog.data.repository (NST-202)."""

from __future__ import annotations

import sqlite3

import pytest

from speedlog.data import db
from speedlog.data.models import SpeedRecord
from speedlog.data.repository import Repository


@pytest.fixture()
def conn() -> sqlite3.Connection:
    connection = sqlite3.connect(":memory:")
    connection.execute("PRAGMA foreign_keys=ON")
    db.migrate(connection)
    yield connection
    connection.close()


@pytest.fixture()
def repo(conn: sqlite3.Connection) -> Repository:
    return Repository(conn)


def test_start_session_inserts_open_session(repo: Repository, conn: sqlite3.Connection) -> None:
    session_id = repo.start_session(1_700_000_000)

    row = conn.execute(
        "SELECT start_ts, end_ts, end_reason FROM sessions WHERE id = ?", (session_id,)
    ).fetchone()
    assert row == (1_700_000_000, None, None)


def test_end_session_sets_end_ts_and_reason(repo: Repository, conn: sqlite3.Connection) -> None:
    session_id = repo.start_session(1_700_000_000)

    repo.end_session(session_id, 1_700_000_600, "disconnect")

    row = conn.execute(
        "SELECT end_ts, end_reason FROM sessions WHERE id = ?", (session_id,)
    ).fetchone()
    assert row == (1_700_000_600, "disconnect")


def test_insert_record_roundtrip(repo: Repository, conn: sqlite3.Connection) -> None:
    session_id = repo.start_session(1_700_000_000)
    record = SpeedRecord(
        session_id=session_id,
        start_ts=1_700_000_000,
        end_ts=1_700_000_060,
        download_bps=5_000_000.0,
        upload_bps=1_200_000.0,
    )

    record_id = repo.insert_record(record)

    row = conn.execute(
        "SELECT session_id, start_ts, end_ts, download_bps, upload_bps"
        " FROM speed_records WHERE id = ?",
        (record_id,),
    ).fetchone()
    assert row == (session_id, 1_700_000_000, 1_700_000_060, 5_000_000.0, 1_200_000.0)


def test_insert_record_unknown_session_raises_and_leaves_db_clean(
    repo: Repository, conn: sqlite3.Connection
) -> None:
    record = SpeedRecord(
        session_id=999,
        start_ts=1_700_000_000,
        end_ts=1_700_000_060,
        download_bps=5_000_000.0,
        upload_bps=1_200_000.0,
    )

    with pytest.raises(sqlite3.IntegrityError):
        repo.insert_record(record)

    assert conn.execute("SELECT COUNT(*) FROM speed_records").fetchone()[0] == 0


def test_close_dangling_sessions_closes_only_open_sessions(
    repo: Repository, conn: sqlite3.Connection
) -> None:
    closed_id = repo.start_session(1_700_000_000)
    repo.end_session(closed_id, 1_700_000_600, "quit")
    dangling_a = repo.start_session(1_700_001_000)
    dangling_b = repo.start_session(1_700_002_000)

    count = repo.close_dangling_sessions(1_700_003_000)

    assert count == 2
    rows = conn.execute("SELECT id, end_ts, end_reason FROM sessions ORDER BY id").fetchall()
    assert rows == [
        (closed_id, 1_700_000_600, "quit"),
        (dangling_a, 1_700_003_000, "quit"),
        (dangling_b, 1_700_003_000, "quit"),
    ]


def test_close_dangling_sessions_noop_when_none_open(repo: Repository) -> None:
    session_id = repo.start_session(1_700_000_000)
    repo.end_session(session_id, 1_700_000_600, "quit")

    assert repo.close_dangling_sessions(1_700_001_000) == 0
