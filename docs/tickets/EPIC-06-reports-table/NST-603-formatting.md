# NST-603 — Cell formatting: time ranges, units, midnight edge

- **Epic:** EPIC-06 Reports Table
- **Type:** Feature
- **Priority:** P2
- **Estimate:** S
- **Status:** DONE
- **Depends on:** NST-601

## Description
Presentation rules from ui-context.md applied in one formatting module shared with PDF.

## Acceptance criteria
- [x] `format_time_range(start_ts, end_ts) -> "10:20 AM – 10:30 AM"` (local time)
- [x] Midnight-spanning record: shown on START date, `11:58 PM – 12:04 AM (+1)`
- [x] `format_date(ts) -> "2026-07-06"`; speeds via shared format_speed
- [x] All conversions via zoneinfo; NO manual UTC offsets
- [x] Same helpers imported by table model AND pdf_report (single source)

## Test plan
Unit tests with fixed tz (monkeypatched): normal range, midnight span, DST transition
day, sub-MB speed formatting.

## Implementation notes
- Files touched: `app/formatting.py`, `app/ui/reports/table_model.py`,
  `app/export/pdf_report.py`, `tests/test_formatting.py`, `tests/test_reports_page.py`,
  `docs/progress-tracker.md`
- Added shared `format_date()` and `format_time_range()` helpers beside `format_speed()`,
  with local-time conversion done through `zoneinfo` and `(+N)` rollover markers when a
  record ends on a later local date than it started.
- `ReportsTableModel` now imports the shared report formatters directly, and
  `app/export/pdf_report.py` re-exports the same helpers so NST-801 starts from the same
  source of truth instead of duplicating cell formatting rules.
- Tests cover normal local ranges, midnight rollover, a DST transition day, sub-MB speed
  formatting, and an identity check proving the table model and PDF module reference the
  same shared helper functions.
- Verification run: `QT_QPA_PLATFORM=offscreen .venv/bin/pytest -q` (145 passed, 1 skipped),
  `.venv/bin/ruff check .`, `.venv/bin/black --check .`
