# NST-203 — Repository read path: pagination + filter queries

- **Epic:** EPIC-02 Data Layer
- **Type:** Feature
- **Priority:** P1
- **Estimate:** M
- **Status:** TODO
- **Depends on:** NST-202

## Description
Read API used by the reports table and PDF export: filtered, paginated record queries.

## Acceptance criteria
- [ ] `ReportFilter` dataclass: `range_start_ts: int | None`, `range_end_ts: int | None`
      (already resolved to UTC by the UI layer — repository is timezone-agnostic)
- [ ] `count_records(filter) -> int`
- [ ] `fetch_records(filter, page: int, page_size: int) -> list[SpeedRecord]`
      ordered by start_ts DESC, LIMIT/OFFSET
- [ ] `fetch_all_records(filter) -> Iterator[SpeedRecord]` for PDF export (chunked)
- [ ] Overlap semantics: `start_ts <= :range_end AND end_ts >= :range_start`
- [ ] Uses idx_records_start (verify with EXPLAIN QUERY PLAN in a test)

## Test plan
Seed 50 records: page boundaries exact (20/20/10); overlap filter includes records
straddling the range edges; empty filter returns all; count matches.

## Implementation notes (fill after DONE)
