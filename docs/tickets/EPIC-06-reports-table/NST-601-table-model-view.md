# NST-601 — Reports table model + view

- **Epic:** EPIC-06 Reports Table
- **Type:** Feature
- **Priority:** P1
- **Estimate:** M
- **Status:** DONE
- **Depends on:** NST-203, NST-401

## Description
`ui/reports/table_model.py` (QAbstractTableModel over a page of SpeedRecords) and
`ui/reports/reports_page.py` (QTableView wiring) — the Reports tab body.

## Acceptance criteria
- [x] Columns: Date | Time | Download | Upload (headers exactly)
- [x] Model exposes `set_page(records: list[SpeedRecord])`; view is read-only,
      row-select, alternating colors, sorted newest-first (data pre-sorted by query)
- [x] Reads via a UI-thread repository connection (its own, per threading rules)
- [x] Auto-refresh: segment_closed signal reloads current page IF user is on page 1
      with no manual position (don't yank the user around)
- [x] Empty state label when 0 rows

## Test plan
pytest-qt: model rowCount/columnCount/data for a seeded page; empty state toggles.

## Implementation notes
- Files touched: `app/ui/reports/table_model.py`, `app/ui/reports/reports_page.py`,
  `app/ui/main_window.py`, `app/main.py`, `tests/test_main_window.py`,
  `tests/test_reports_page.py`, `docs/progress-tracker.md`
- `ReportsPage` owns a lazy-opened UI-thread SQLite connection + `Repository`; reads stay
  off the collector thread and the page opens cleanly in tests before the Reports tab is shown.
- Auto-refresh is wired from `CollectorService.segment_closed` and only runs on page 1 when
  the table is still at its default position (no row selection and scroll bar at the top).
- Report loading failures are logged and fall back to the empty state instead of crashing the
  main window when the reports DB path is unavailable in a sandboxed test run.
- Added pytest-qt coverage for table headers/data, empty-state toggling, and the guarded
  no-yank auto-refresh behavior.
