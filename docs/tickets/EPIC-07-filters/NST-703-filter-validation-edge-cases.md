# NST-703 — Filter validation, reset, edge cases

- **Epic:** EPIC-07 Filters
- **Type:** Task
- **Priority:** P2
- **Estimate:** S
- **Status:** DONE
- **Depends on:** NST-702

## Description
Hardening pass on filtering UX.

## Acceptance criteria
- [x] Future dates allowed but produce a clean empty state (no error)
- [x] Instant (date+time) query matching a record boundary exactly is INCLUSIVE
- [x] Reset restores mode=Date-Range covering all data? NO — Reset = no filter,
      show everything, page 1 (documented in code)
- [x] Filter state persists while switching tabs; cleared on app restart
- [x] Status line shows active filter summary, e.g. "Filtered: 2026-07-01 – 2026-07-06"

## Test plan
pytest-qt: each criterion; boundary-inclusive test with crafted record.

## Implementation notes
- Files touched: `app/ui/reports/filter_builder.py`, `app/ui/reports/filter_panel.py`,
  `app/ui/reports/reports_page.py`, `app/ui/styles.qss`, `tests/test_filter_builder.py`,
  `tests/test_reports_page.py`, `docs/progress-tracker.md`
- Added pure filter-summary helpers alongside the existing filter builder so the reports
  page can show stable, local-time summaries for applied filters while keeping the logic
  Qt-free and unit-testable.
- Reports now track the last applied UI filter state, show a dedicated status line, and
  keep Reset explicitly mapped to "no filter" / page 1 instead of synthesizing a broad
  date range.
- Added pytest and pytest-qt coverage for future-date empty states, inclusive instant
  boundaries at both record edges, reset-to-all behavior, tab-switch persistence, and
  fresh-window restart clearing.
- Verification run: `QT_QPA_PLATFORM=offscreen .venv/bin/pytest -q` (163 passed,
  1 skipped), `.venv/bin/ruff check .`, `.venv/bin/black --check .`
