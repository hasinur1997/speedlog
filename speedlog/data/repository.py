"""All SQL lives here (and only here). Writes: NST-202; reads: NST-203.

Each thread must own its connection (see docs/architecture-context.md,
"Threading rules"); a :class:`Repository` therefore belongs to exactly
one thread.
"""

from __future__ import annotations

import sqlite3
from collections.abc import Iterator

from speedlog import config
from speedlog.data.models import ReportFilter, SpeedRecord

_RECORD_COLUMNS = "id, session_id, start_ts, end_ts, download_bps, upload_bps"


def _filter_clause(report_filter: ReportFilter) -> tuple[str, dict[str, int]]:
    """Compile ``report_filter`` to a WHERE clause and named parameters.

    Overlap semantics: a record matches when
    ``start_ts <= :range_end AND end_ts >= :range_start``; each bound is
    applied independently when the other is ``None``. Returns an empty
    clause for an unbounded filter.
    """
    conditions: list[str] = []
    params: dict[str, int] = {}
    if report_filter.range_end_ts is not None:
        conditions.append("start_ts <= :range_end")
        params["range_end"] = report_filter.range_end_ts
    if report_filter.range_start_ts is not None:
        conditions.append("end_ts >= :range_start")
        params["range_start"] = report_filter.range_start_ts
    if not conditions:
        return "", {}
    return " WHERE " + " AND ".join(conditions), params


def _row_to_record(row: tuple) -> SpeedRecord:
    """Build a :class:`SpeedRecord` from a ``_RECORD_COLUMNS`` row."""
    record_id, session_id, start_ts, end_ts, download_bps, upload_bps = row
    return SpeedRecord(
        session_id=session_id,
        start_ts=start_ts,
        end_ts=end_ts,
        download_bps=download_bps,
        upload_bps=upload_bps,
        id=record_id,
    )


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

    def count_records(self, report_filter: ReportFilter) -> int:
        """Return the number of speed records matching ``report_filter``."""
        clause, params = _filter_clause(report_filter)
        row = self._conn.execute(
            f"SELECT COUNT(*) FROM speed_records{clause}",
            params,
        ).fetchone()
        return int(row[0])

    def fetch_records(
        self, report_filter: ReportFilter, page: int, page_size: int
    ) -> list[SpeedRecord]:
        """Return one page of matching records, newest first.

        ``page`` is 1-based; ordering is ``start_ts DESC`` with
        LIMIT/OFFSET pagination.
        """
        clause, params = _filter_clause(report_filter)
        rows = self._conn.execute(
            f"SELECT {_RECORD_COLUMNS} FROM speed_records{clause}"
            " ORDER BY start_ts DESC LIMIT :limit OFFSET :offset",
            {**params, "limit": page_size, "offset": (page - 1) * page_size},
        ).fetchall()
        return [_row_to_record(row) for row in rows]

    def fetch_all_records(self, report_filter: ReportFilter) -> Iterator[SpeedRecord]:
        """Yield ALL matching records, newest first, in chunks (for PDF export).

        Streams via ``fetchmany`` (:data:`config.DB_FETCH_CHUNK_SIZE` rows per
        batch) so large exports don't materialize the full result set at once.
        """
        clause, params = _filter_clause(report_filter)
        cursor = self._conn.execute(
            f"SELECT {_RECORD_COLUMNS} FROM speed_records{clause} ORDER BY start_ts DESC",
            params,
        )
        while rows := cursor.fetchmany(config.DB_FETCH_CHUNK_SIZE):
            for row in rows:
                yield _row_to_record(row)
