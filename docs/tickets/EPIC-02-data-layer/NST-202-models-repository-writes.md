# NST-202 — Models & repository (write path)

- **Epic:** EPIC-02 Data Layer
- **Type:** Feature
- **Priority:** P1
- **Estimate:** M
- **Status:** TODO
- **Depends on:** NST-201

## Description
Dataclasses (`SpeedRecord`, `Session`) in `data/models.py` and the write-side API in
`data/repository.py`. ALL SQL lives here.

## Acceptance criteria
- [ ] `Repository(conn)` with: `start_session(ts) -> int`,
      `end_session(id, ts, reason)`, `insert_record(SpeedRecord) -> int`
- [ ] `SpeedRecord`: session_id, start_ts, end_ts, download_bps, upload_bps (+ id opt.)
- [ ] Parameterized SQL only; each write in a transaction
- [ ] Recovery helper `close_dangling_sessions(ts)` for crash cleanup at startup
- [ ] Type hints + docstrings on all public methods

## Test plan
In-memory DB: insert/read-back roundtrip; end_session sets reason; dangling-session
recovery closes open sessions.

## Implementation notes (fill after DONE)
