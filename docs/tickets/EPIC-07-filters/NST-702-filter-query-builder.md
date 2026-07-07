# NST-702 — Filter -> query builder (local time -> UTC range)

- **Epic:** EPIC-07 Filters
- **Type:** Feature
- **Priority:** P1
- **Estimate:** M
- **Status:** DONE
- **Depends on:** NST-701, NST-203

## Description
Pure function converting UI filter state into the repository's `ReportFilter`
(UTC epoch range) with the overlap semantics from architecture-context.md.

## Acceptance criteria
- [x] Date D            -> [D 00:00:00, D 23:59:59] local -> UTC
- [x] Date range D1..D2 -> [D1 00:00:00, D2 23:59:59]; auto-swap if D1 > D2
- [x] Date + time T     -> instant query: records whose span CONTAINS T
      (range_start = range_end = T)
- [x] Date + time range T1..T2 -> overlap query on [T1, T2]; swap if reversed
- [x] Pure, no Qt imports; fully unit-testable
- [x] Wired: panel Apply -> builder -> repository -> table reload -> page reset

## Test plan
Unit: each mode; timezone conversion (fixed tz); DST boundary date; reversed inputs.
Integration (pytest-qt): applying Date filter narrows seeded table rows correctly.

## Implementation notes
- Files touched: `app/ui/reports/filter_builder.py`, `app/ui/reports/reports_page.py`,
  `tests/test_filter_builder.py`, `tests/test_reports_page.py`,
  `docs/progress-tracker.md`
- Added a pure `build_report_filter()` helper in
  `app/ui/reports/filter_builder.py` that resolves local date/time UI state into
  UTC `ReportFilter` bounds, including reversed date/time auto-swaps and a
  best-effort local `ZoneInfo` fallback to UTC.
- Wired `FilterPanel.filter_applied` into `ReportsPage` so Apply/Reset now flow
  through the builder into repository-backed reloads using the existing page-1
  reset behavior.
- Added unit coverage for all four modes, fixed-timezone conversion, reversed
  inputs, and a DST transition day, plus a pytest-qt integration test proving a
  Date filter narrows the seeded reports table and resets pagination.
- Verification run: `QT_QPA_PLATFORM=offscreen .venv/bin/pytest -q` (155 passed,
  1 skipped), `.venv/bin/ruff check .`, `.venv/bin/black --check .`
