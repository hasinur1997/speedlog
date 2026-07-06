# NST-201 — SQLite schema & migrations

- **Epic:** EPIC-02 Data Layer
- **Type:** Feature
- **Priority:** P1
- **Estimate:** M
- **Status:** TODO
- **Depends on:** NST-102

## Description
Create `data/db.py`: connection factory and schema bootstrap for `sessions`,
`speed_records`, `schema_version` per architecture-context.md ("Database schema").

## Acceptance criteria
- [ ] `get_connection(path) -> sqlite3.Connection` sets PRAGMAs: journal_mode=WAL,
      foreign_keys=ON, synchronous=NORMAL
- [ ] `migrate(conn)` creates tables + indexes idempotently; writes schema_version=1
- [ ] Re-running migrate on an existing DB is a no-op
- [ ] Timestamps stored as INTEGER UTC epoch seconds; speeds as REAL bytes/sec
- [ ] Simple forward-migration mechanism (version check + ordered migration list)

## Technical notes
Each thread must create its OWN connection via this factory (see threading rules).

## Test plan
tmp_path DB: fresh migrate creates schema; double migrate safe; PRAGMAs verified;
FK violation raises.

## Implementation notes (fill after DONE)
