"""Connection factory, migrations, PRAGMAs (NST-201).

Each thread must create its OWN connection via :func:`get_connection`
(see docs/architecture-context.md, "Threading rules").
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

_MIGRATION_V1: tuple[str, ...] = (
    """
    CREATE TABLE sessions (
      id         INTEGER PRIMARY KEY AUTOINCREMENT,
      start_ts   INTEGER NOT NULL,          -- UTC epoch seconds
      end_ts     INTEGER,                   -- NULL while open
      end_reason TEXT                       -- 'disconnect' | 'quit' | NULL
    )
    """,
    """
    CREATE TABLE speed_records (
      id            INTEGER PRIMARY KEY AUTOINCREMENT,
      session_id    INTEGER NOT NULL REFERENCES sessions(id),
      start_ts      INTEGER NOT NULL,       -- UTC epoch seconds
      end_ts        INTEGER NOT NULL,
      download_bps  REAL NOT NULL,          -- bytes/sec, representative (mean of segment)
      upload_bps    REAL NOT NULL
    )
    """,
    "CREATE INDEX idx_records_start ON speed_records(start_ts)",
    "CREATE INDEX idx_records_session ON speed_records(session_id)",
)

# Ordered forward migrations: index 0 upgrades the schema to version 1, etc.
# Append new migrations here; never modify or reorder released entries.
_MIGRATIONS: tuple[tuple[str, ...], ...] = (_MIGRATION_V1,)


def get_connection(path: Path | str) -> sqlite3.Connection:
    """Open a connection to the SQLite DB at ``path`` with required PRAGMAs set."""
    conn = sqlite3.connect(path)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.execute("PRAGMA synchronous=NORMAL")
    return conn


def _current_version(conn: sqlite3.Connection) -> int:
    table = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='schema_version'"
    ).fetchone()
    if table is None:
        return 0
    row = conn.execute("SELECT version FROM schema_version").fetchone()
    return int(row[0]) if row is not None else 0


def migrate(conn: sqlite3.Connection) -> None:
    """Apply pending forward migrations atomically; no-op when already up to date."""
    version = _current_version(conn)
    target = len(_MIGRATIONS)
    if version >= target:
        return
    with conn:
        conn.execute("CREATE TABLE IF NOT EXISTS schema_version (version INTEGER NOT NULL)")
        for migration in _MIGRATIONS[version:]:
            for statement in migration:
                conn.execute(statement)
        conn.execute("DELETE FROM schema_version")
        conn.execute("INSERT INTO schema_version (version) VALUES (?)", (target,))
