"""All SQL lives here (and only here). Write path implemented in NST-202.

Read/pagination/filter queries follow in NST-203. Each thread must own its
connection (see docs/architecture-context.md, "Threading rules"); a
:class:`Repository` therefore belongs to exactly one thread.
"""

from __future__ import annotations

import sqlite3

from speedlog.data.models import SpeedRecord


class Repository:
    """Data access layer over one SQLite connection.

    All writes run inside a transaction (``with conn``) so a failure leaves
    the database unchanged.
    """

    def __init__(self, conn: sqlite3.Connection) -> None:
        """Wrap ``conn``; the caller retains ownership and closes it."""
        self._conn = conn

    def start_session(self, ts: int) -> int:
        """Insert an open session starting at UTC epoch ``ts``; return its id."""
        with self._conn:
            cursor = self._conn.execute(
                "INSERT INTO sessions (start_ts) VALUES (?)",
                (ts,),
            )
        return int(cursor.lastrowid)  # type: ignore[arg-type]

    def end_session(self, session_id: int, ts: int, reason: str) -> None:
        """Close session ``session_id`` at UTC epoch ``ts`` with ``reason``.

        ``reason`` is ``'disconnect'`` or ``'quit'``.
        """
        with self._conn:
            self._conn.execute(
                "UPDATE sessions SET end_ts = ?, end_reason = ? WHERE id = ?",
                (ts, reason, session_id),
            )

    def insert_record(self, record: SpeedRecord) -> int:
        """Insert a closed speed segment; return the new row id."""
        with self._conn:
            cursor = self._conn.execute(
                "INSERT INTO speed_records"
                " (session_id, start_ts, end_ts, download_bps, upload_bps)"
                " VALUES (?, ?, ?, ?, ?)",
                (
                    record.session_id,
                    record.start_ts,
                    record.end_ts,
                    record.download_bps,
                    record.upload_bps,
                ),
            )
        return int(cursor.lastrowid)  # type: ignore[arg-type]

    def close_dangling_sessions(self, ts: int) -> int:
        """Close sessions left open by a crash, ending them at UTC epoch ``ts``.

        Called at startup before a new session begins. Returns the number of
        sessions closed. ``end_reason`` is set to ``'quit'``.
        """
        with self._conn:
            cursor = self._conn.execute(
                "UPDATE sessions SET end_ts = ?, end_reason = 'quit' WHERE end_ts IS NULL",
                (ts,),
            )
        return cursor.rowcount
