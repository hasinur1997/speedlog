"""Tests for app.data.models and app.data.repository (NST-202/NST-203)."""

from __future__ import annotations

import sqlite3

import pytest

from app.data import db
from app.data.models import ReportFilter, SpeedRecord
from app.data.repository import Repository


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


# --- Read path (NST-203) -------------------------------------------------------------

BASE_TS = 1_700_000_000
SEGMENT_SECS = 60


def _seed_records(repo: Repository, count: int = 50) -> list[int]:
    """Insert ``count`` back-to-back 60s records; return their row ids in insert order."""
    session_id = repo.start_session(BASE_TS)
    ids = []
    for i in range(count):
        start = BASE_TS + i * SEGMENT_SECS
        ids.append(
            repo.insert_record(
                SpeedRecord(
                    session_id=session_id,
                    start_ts=start,
                    end_ts=start + SEGMENT_SECS,
                    download_bps=5_000_000.0 + i,
                    upload_bps=1_200_000.0 + i,
                )
            )
        )
    return ids


def test_count_records_empty_filter_counts_all(repo: Repository) -> None:
    _seed_records(repo)

    assert repo.count_records(ReportFilter()) == 50


def test_count_records_empty_table(repo: Repository) -> None:
    assert repo.count_records(ReportFilter()) == 0


def test_fetch_records_page_boundaries(repo: Repository) -> None:
    _seed_records(repo)
    empty = ReportFilter()

    page1 = repo.fetch_records(empty, page=1, page_size=20)
    page2 = repo.fetch_records(empty, page=2, page_size=20)
    page3 = repo.fetch_records(empty, page=3, page_size=20)
    page4 = repo.fetch_records(empty, page=4, page_size=20)

    assert [len(page1), len(page2), len(page3), len(page4)] == [20, 20, 10, 0]
    all_starts = [r.start_ts for r in page1 + page2 + page3]
    assert all_starts == sorted(all_starts, reverse=True)
    assert page1[0].start_ts == BASE_TS + 49 * SEGMENT_SECS  # newest first
    assert page3[-1].start_ts == BASE_TS  # oldest last


def test_fetch_records_pages_do_not_overlap(repo: Repository) -> None:
    _seed_records(repo)
    empty = ReportFilter()

    ids = [r.id for page in (1, 2, 3) for r in repo.fetch_records(empty, page=page, page_size=20)]

    assert len(ids) == 50
    assert len(set(ids)) == 50


def test_overlap_filter_includes_edge_straddling_records(repo: Repository) -> None:
    _seed_records(repo)
    # Range starts/ends mid-record: records 10 (ends at +11*60 > start) and
    # 20 (starts at +20*60 < end) straddle the edges and must be included.
    report_filter = ReportFilter(
        range_start_ts=BASE_TS + 10 * SEGMENT_SECS + 30,
        range_end_ts=BASE_TS + 20 * SEGMENT_SECS + 30,
    )

    records = repo.fetch_records(report_filter, page=1, page_size=50)

    starts = sorted(r.start_ts for r in records)
    assert starts == [BASE_TS + i * SEGMENT_SECS for i in range(10, 21)]
    assert repo.count_records(report_filter) == 11


def test_overlap_filter_excludes_records_outside_range(repo: Repository) -> None:
    _seed_records(repo)
    # Range exactly between record 4's end and record 6's start boundary
    # instants: touching counts as overlap (<= / >=).
    report_filter = ReportFilter(
        range_start_ts=BASE_TS + 5 * SEGMENT_SECS,
        range_end_ts=BASE_TS + 6 * SEGMENT_SECS,
    )

    starts = sorted(r.start_ts for r in repo.fetch_records(report_filter, page=1, page_size=50))
    # Record 4 ends AT range_start, record 6 starts AT range_end → both touch.
    assert starts == [BASE_TS + i * SEGMENT_SECS for i in (4, 5, 6)]


def test_half_open_filters(repo: Repository) -> None:
    _seed_records(repo)

    only_start = ReportFilter(range_start_ts=BASE_TS + 45 * SEGMENT_SECS)
    only_end = ReportFilter(range_end_ts=BASE_TS + 4 * SEGMENT_SECS)

    # end_ts >= range_start → records 44..49 (record 44 ends at +45*60).
    assert repo.count_records(only_start) == 6
    # start_ts <= range_end → records 0..4.
    assert repo.count_records(only_end) == 5


def test_fetch_all_records_streams_everything_in_order(repo: Repository) -> None:
    _seed_records(repo)
    report_filter = ReportFilter(range_start_ts=BASE_TS, range_end_ts=BASE_TS + 50 * SEGMENT_SECS)

    records = list(repo.fetch_all_records(report_filter))

    assert len(records) == 50
    starts = [r.start_ts for r in records]
    assert starts == sorted(starts, reverse=True)
    assert all(isinstance(r, SpeedRecord) for r in records)


def test_fetch_all_records_chunks_across_batches(
    repo: Repository, monkeypatch: pytest.MonkeyPatch
) -> None:
    from app import config

    _seed_records(repo)
    monkeypatch.setattr(config, "DB_FETCH_CHUNK_SIZE", 7)  # force multiple fetchmany batches

    records = list(repo.fetch_all_records(ReportFilter()))

    assert len(records) == 50
    assert len({r.id for r in records}) == 50


def test_fetch_records_uses_start_ts_index(repo: Repository, conn: sqlite3.Connection) -> None:
    _seed_records(repo)

    plan = conn.execute(
        "EXPLAIN QUERY PLAN "
        "SELECT id, session_id, start_ts, end_ts, download_bps, upload_bps "
        "FROM speed_records WHERE start_ts <= :range_end AND end_ts >= :range_start "
        "ORDER BY start_ts DESC LIMIT :limit OFFSET :offset",
        {"range_end": BASE_TS + 1000, "range_start": BASE_TS, "limit": 20, "offset": 0},
    ).fetchall()

    plan_text = " ".join(row[3] for row in plan)
    assert "idx_records_start" in plan_text
