# NST-202 — Models & repository (write path)

- **Epic:** EPIC-02 Data Layer
- **Type:** Feature
- **Priority:** P1
- **Estimate:** M
- **Status:** DONE
- **Depends on:** NST-201

## Description
Dataclasses (`SpeedRecord`, `Session`) in `data/models.py` and the write-side API in
`data/repository.py`. ALL SQL lives here.

## Acceptance criteria
- [x] `Repository(conn)` with: `start_session(ts) -> int`,
      `end_session(id, ts, reason)`, `insert_record(SpeedRecord) -> int`
- [x] `SpeedRecord`: session_id, start_ts, end_ts, download_bps, upload_bps (+ id opt.)
- [x] Parameterized SQL only; each write in a transaction
- [x] Recovery helper `close_dangling_sessions(ts)` for crash cleanup at startup
- [x] Type hints + docstrings on all public methods

## Test plan
In-memory DB: insert/read-back roundtrip; end_session sets reason; dangling-session
recovery closes open sessions.

## Implementation notes (fill after DONE)
- Files: `app/data/models.py`, `app/data/repository.py`, `tests/test_repository.py`.
- `Session` and `SpeedRecord` are `@dataclass(slots=True)` with `id: int | None = None`
  last so required fields stay positional.
- `Repository(conn)` wraps a caller-owned connection (one per thread per the
  architecture rules); every write uses `with self._conn:` so failures roll back —
  verified by a test that a foreign-key violation leaves `speed_records` empty.
- `close_dangling_sessions(ts)` closes all rows with `end_ts IS NULL`, sets
  `end_reason='quit'`, and returns the count. Intended for startup crash recovery
  (NST-304/NST-305 should call it before `start_session`).
- Read-side queries (pagination/filters) deliberately not added — that's NST-203.
- Tests use in-memory SQLite with `PRAGMA foreign_keys=ON` + `db.migrate`; 6 tests,
  `pytest -q` (33 total), `ruff check .`, `black --check .` all green.
