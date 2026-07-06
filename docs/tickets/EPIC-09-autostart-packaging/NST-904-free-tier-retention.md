# NST-904 — Free-tier history retention (7-day cleanup)

- **Epic:** EPIC-09 Autostart & Packaging (Commercial)
- **Type:** Feature
- **Priority:** P2
- **Estimate:** S
- **Status:** TODO
- **Depends on:** NST-202, NST-905

## Description
Free tier keeps only the last 7 days of records (project-overview.md "Commercial model").
Pro keeps everything.

## Acceptance criteria
- [ ] `FREE_RETENTION_DAYS = 7` in config
- [ ] Repository method `purge_records_older_than(ts)` (SQL in repository.py only)
- [ ] Cleanup runs at app start and once per 24h in the collector thread, ONLY when
      gate.is_pro() is False
- [ ] Sessions with no remaining records purged too
- [ ] Purge is logged (count deleted); wrapped in a transaction

## Test plan
Seed records across 10 days: purge keeps exactly the last 7; Pro mode purges nothing;
orphan sessions removed.

## Implementation notes (fill after DONE)
