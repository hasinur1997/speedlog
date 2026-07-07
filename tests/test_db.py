"""Tests for speedlog.data.db (NST-201)."""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from speedlog.data import db


@pytest.fixture()
def conn(tmp_path: Path) -> sqlite3.Connection:
    connection = db.get_connection(tmp_path / "data.db")
    yield connection
    connection.close()


def _table_names(conn: sqlite3.Connection) -> set[str]:
    rows = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
    ).fetchall()
    return {row[0] for row in rows}


def _index_names(conn: sqlite3.Connection) -> set[str]:
    rows = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='index' AND name NOT LIKE 'sqlite_%'"
    ).fetchall()
    return {row[0] for row in rows}


def test_get_connection_sets_pragmas(conn: sqlite3.Connection) -> None:
    assert conn.execute("PRAGMA journal_mode").fetchone()[0] == "wal"
    assert conn.execute("PRAGMA foreign_keys").fetchone()[0] == 1
    assert conn.execute("PRAGMA synchronous").fetchone()[0] == 1  # NORMAL


def test_migrate_creates_schema(conn: sqlite3.Connection) -> None:
    db.migrate(conn)

    assert _table_names(conn) == {"sessions", "speed_records", "schema_version"}
    assert {"idx_records_start", "idx_records_session"} <= _index_names(conn)
    assert conn.execute("SELECT version FROM schema_version").fetchall() == [(1,)]


def test_migrate_twice_is_noop(conn: sqlite3.Connection) -> None:
    db.migrate(conn)
    schema_before = conn.execute(
        "SELECT type, name, sql FROM sqlite_master ORDER BY name"
    ).fetchall()

    db.migrate(conn)

    schema_after = conn.execute(
        "SELECT type, name, sql FROM sqlite_master ORDER BY name"
    ).fetchall()
    assert schema_after == schema_before
    assert conn.execute("SELECT version FROM schema_version").fetchall() == [(1,)]


def test_migrate_is_noop_on_reopened_db(tmp_path: Path) -> None:
    path = tmp_path / "data.db"
    first = db.get_connection(path)
    db.migrate(first)
    first.execute(
        "INSERT INTO sessions (start_ts, end_ts, end_reason) VALUES (?, ?, ?)",
        (1_700_000_000, 1_700_000_600, "quit"),
    )
    first.commit()
    first.close()

    second = db.get_connection(path)
    db.migrate(second)

    assert second.execute("SELECT COUNT(*) FROM sessions").fetchone()[0] == 1
    assert second.execute("SELECT version FROM schema_version").fetchall() == [(1,)]
    second.close()


def test_schema_column_types(conn: sqlite3.Connection) -> None:
    db.migrate(conn)

    session_cols = {row[1]: row[2] for row in conn.execute("PRAGMA table_info(sessions)")}
    assert session_cols["start_ts"] == "INTEGER"
    assert session_cols["end_ts"] == "INTEGER"
    assert session_cols["end_reason"] == "TEXT"

    record_cols = {row[1]: row[2] for row in conn.execute("PRAGMA table_info(speed_records)")}
    assert record_cols["session_id"] == "INTEGER"
    assert record_cols["start_ts"] == "INTEGER"
    assert record_cols["end_ts"] == "INTEGER"
    assert record_cols["download_bps"] == "REAL"
    assert record_cols["upload_bps"] == "REAL"


def test_foreign_key_violation_raises(conn: sqlite3.Connection) -> None:
    db.migrate(conn)

    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(
            "INSERT INTO speed_records (session_id, start_ts, end_ts, download_bps, upload_bps)"
            " VALUES (?, ?, ?, ?, ?)",
            (999, 1_700_000_000, 1_700_000_060, 5_000_000.0, 1_200_000.0),
        )


def test_valid_insert_with_foreign_key(conn: sqlite3.Connection) -> None:
    db.migrate(conn)

    cursor = conn.execute("INSERT INTO sessions (start_ts) VALUES (?)", (1_700_000_000,))
    session_id = cursor.lastrowid
    conn.execute(
        "INSERT INTO speed_records (session_id, start_ts, end_ts, download_bps, upload_bps)"
        " VALUES (?, ?, ?, ?, ?)",
        (session_id, 1_700_000_000, 1_700_000_060, 5_000_000.0, 1_200_000.0),
    )
    conn.commit()

    assert conn.execute("SELECT COUNT(*) FROM speed_records").fetchone()[0] == 1
