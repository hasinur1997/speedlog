# NST-201 — SQLite schema & migrations

- **Epic:** EPIC-02 Data Layer
- **Type:** Feature
- **Priority:** P1
- **Estimate:** M
- **Status:** DONE
- **Depends on:** NST-102

## Description
Create `data/db.py`: connection factory and schema bootstrap for `sessions`,
`speed_records`, `schema_version` per architecture-context.md ("Database schema").

## Acceptance criteria
- [x] `get_connection(path) -> sqlite3.Connection` sets PRAGMAs: journal_mode=WAL,
      foreign_keys=ON, synchronous=NORMAL
- [x] `migrate(conn)` creates tables + indexes idempotently; writes schema_version=1
- [x] Re-running migrate on an existing DB is a no-op
- [x] Timestamps stored as INTEGER UTC epoch seconds; speeds as REAL bytes/sec
- [x] Simple forward-migration mechanism (version check + ordered migration list)

## Technical notes
Each thread must create its OWN connection via this factory (see threading rules).

## Test plan
tmp_path DB: fresh migrate creates schema; double migrate safe; PRAGMAs verified;
FK violation raises.

## Implementation notes (fill after DONE)
- Files touched: `app/data/db.py` (implementation), `tests/test_db.py` (7 tests).
- `_MIGRATIONS` is an ordered tuple of migrations; each migration is a tuple of
  individual SQL statements (not `executescript`) so every upgrade — DDL plus the
  `schema_version` write — runs atomically inside one `with conn:` transaction.
  To add schema version N, append one entry; never edit released entries.
- `_current_version()` returns 0 when `schema_version` is missing or empty, so
  `migrate()` is safe on a fresh file and a no-op on an up-to-date DB.
- `schema_version` holds a single row (DELETE + INSERT on upgrade).
- For NST-202: import `get_connection`/`migrate` from `app.data.db`; each
  thread must open its own connection via the factory. FK enforcement is ON —
  inserting a `speed_records` row with an unknown `session_id` raises
  `sqlite3.IntegrityError`.
