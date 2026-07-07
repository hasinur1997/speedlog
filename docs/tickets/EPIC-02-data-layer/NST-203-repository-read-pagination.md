# NST-203 — Repository read path: pagination + filter queries

- **Epic:** EPIC-02 Data Layer
- **Type:** Feature
- **Priority:** P1
- **Estimate:** M
- **Status:** DONE
- **Depends on:** NST-202

## Description
Read API used by the reports table and PDF export: filtered, paginated record queries.

## Acceptance criteria
- [x] `ReportFilter` dataclass: `range_start_ts: int | None`, `range_end_ts: int | None`
      (already resolved to UTC by the UI layer — repository is timezone-agnostic)
- [x] `count_records(filter) -> int`
- [x] `fetch_records(filter, page: int, page_size: int) -> list[SpeedRecord]`
      ordered by start_ts DESC, LIMIT/OFFSET
- [x] `fetch_all_records(filter) -> Iterator[SpeedRecord]` for PDF export (chunked)
- [x] Overlap semantics: `start_ts <= :range_end AND end_ts >= :range_start`
- [x] Uses idx_records_start (verify with EXPLAIN QUERY PLAN in a test)

## Test plan
Seed 50 records: page boundaries exact (20/20/10); overlap filter includes records
straddling the range edges; empty filter returns all; count matches.

## Implementation notes (fill after DONE)
- Files: `speedlog/data/models.py` (ReportFilter), `speedlog/data/repository.py`
  (read methods + `_filter_clause`/`_row_to_record` helpers), `speedlog/config.py`
  (`DB_FETCH_CHUNK_SIZE = 500`), `tests/test_repository.py`.
- `ReportFilter(range_start_ts=None, range_end_ts=None)` — both bounds optional;
  each overlap condition is applied independently, so half-open filters work and
  an empty filter compiles to no WHERE clause.
- Overlap is inclusive (`<=` / `>=`): a record touching the range boundary instant
  matches — asserted explicitly in tests.
- `fetch_records(filter, page, page_size)`: **page is 1-based**, ordered
  `start_ts DESC` (newest first), LIMIT/OFFSET. Callers (NST-601/602) should pass
  `config.PAGE_SIZE`.
- `fetch_all_records` is a generator streaming via `cursor.fetchmany(DB_FETCH_CHUNK_SIZE)`
  for PDF export; same ordering/filtering as the page query.
- Only the WHERE clause fragment (built from fixed condition strings) and the fixed
  column list are interpolated; all values go through named parameters.
- EXPLAIN QUERY PLAN test confirms the filtered+ordered page query uses
  `idx_records_start`. 10 new tests; `pytest -q` (43 total), ruff, black all green.
