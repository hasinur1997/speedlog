# NST-703 — Filter validation, reset, edge cases

- **Epic:** EPIC-07 Filters
- **Type:** Task
- **Priority:** P2
- **Estimate:** S
- **Status:** TODO
- **Depends on:** NST-702

## Description
Hardening pass on filtering UX.

## Acceptance criteria
- [ ] Future dates allowed but produce a clean empty state (no error)
- [ ] Instant (date+time) query matching a record boundary exactly is INCLUSIVE
- [ ] Reset restores mode=Date-Range covering all data? NO — Reset = no filter,
      show everything, page 1 (documented in code)
- [ ] Filter state persists while switching tabs; cleared on app restart
- [ ] Status line shows active filter summary, e.g. "Filtered: 2026-07-01 – 2026-07-06"

## Test plan
pytest-qt: each criterion; boundary-inclusive test with crafted record.

## Implementation notes (fill after DONE)
