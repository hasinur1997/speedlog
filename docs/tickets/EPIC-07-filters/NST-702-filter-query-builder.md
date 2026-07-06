# NST-702 — Filter -> query builder (local time -> UTC range)

- **Epic:** EPIC-07 Filters
- **Type:** Feature
- **Priority:** P1
- **Estimate:** M
- **Status:** TODO
- **Depends on:** NST-701, NST-203

## Description
Pure function converting UI filter state into the repository's `ReportFilter`
(UTC epoch range) with the overlap semantics from architecture-context.md.

## Acceptance criteria
- [ ] Date D            -> [D 00:00:00, D 23:59:59] local -> UTC
- [ ] Date range D1..D2 -> [D1 00:00:00, D2 23:59:59]; auto-swap if D1 > D2
- [ ] Date + time T     -> instant query: records whose span CONTAINS T
      (range_start = range_end = T)
- [ ] Date + time range T1..T2 -> overlap query on [T1, T2]; swap if reversed
- [ ] Pure, no Qt imports; fully unit-testable
- [ ] Wired: panel Apply -> builder -> repository -> table reload -> page reset

## Test plan
Unit: each mode; timezone conversion (fixed tz); DST boundary date; reversed inputs.
Integration (pytest-qt): applying Date filter narrows seeded table rows correctly.

## Implementation notes (fill after DONE)
