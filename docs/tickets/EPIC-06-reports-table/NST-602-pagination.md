# NST-602 — Pagination (20 per page)

- **Epic:** EPIC-06 Reports Table
- **Type:** Feature
- **Priority:** P1
- **Estimate:** S
- **Status:** DONE
- **Depends on:** NST-601

## Description
Pagination bar under the table: Prev / "Page X of Y" / Next + total record count.

## Acceptance criteria
- [x] PAGE_SIZE from config (20); Y = ceil(count/PAGE_SIZE), min 1
- [x] Prev disabled on page 1; Next disabled on last page
- [x] Changing filter resets to page 1
- [x] Count label: "231 records" (singular handled: "1 record")
- [x] Page state survives tab switch, resets on filter change

## Test plan
pytest-qt with seeded 50 records: 3 pages (20/20/10); button enablement at edges;
filter change resets page.

## Implementation notes
- Files touched: `app/ui/reports/reports_page.py`, `tests/test_reports_page.py`,
  `docs/progress-tracker.md`
- `ReportsPage.reload_page()` now uses `Repository.count_records()` plus
  `config.PAGE_SIZE` to keep `current_page`, total pages, and the count label in sync,
  clamping out-of-range pages back to the last valid page.
- Added pagination controls with testable object names:
  `reportsPrevButton`, `reportsPageLabel`, `reportsNextButton`, `reportsCountLabel`.
- Existing guarded auto-refresh behavior remains unchanged: only page 1 at the default
  position auto-refreshes when a segment closes.
- Added pytest-qt coverage for empty-state counts, 50-record pagination (20/20/10),
  edge-button enablement, tab-switch page persistence, and filter-reset-to-page-1.
