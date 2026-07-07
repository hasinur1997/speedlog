# NST-701 — Filter panel UI (4 modes)

- **Epic:** EPIC-07 Filters
- **Type:** Feature
- **Priority:** P1
- **Estimate:** M
- **Status:** DONE
- **Depends on:** NST-601

## Description
`ui/reports/filter_panel.py`: mode selector + date/time editors per ui-context.md.

## Acceptance criteria
- [x] Mode combo: Date | Date Range | Date + Time | Date + Time Range
- [x] Widget visibility per mode: 1 QDateEdit / 2 QDateEdits / QDateEdit+QTimeEdit /
      QDateEdit + 2 QTimeEdits (time range applies within ONE date for v1)
- [x] Apply button emits `filter_applied(uiFilterState)`; Reset returns to
      "no filter" (all records) and emits
- [x] Calendar popups on date editors; sensible defaults (today)
- [x] Time is optional by design: plain Date / Date Range modes ignore time entirely

## Test plan
pytest-qt: mode switch shows/hides correct editors; Apply emits state; Reset clears.

## Implementation notes
- Added `ReportFilterMode` and `ReportFilterUiState` in `app/data/models.py` so
  the filter panel can emit a typed, Qt-free state object that `NST-702` can
  convert into `ReportFilter` without depending on widgets.
- Implemented `FilterPanel` in `app/ui/reports/filter_panel.py` with the four
  ticketed modes, mode-driven editor visibility, calendar popups, today-based
  reset defaults, and `filter_applied` emission for both Apply and Reset.
- Mounted the panel into `ReportsPage` so the filter UI is visible in the
  reports tab now, but repository/query wiring is intentionally deferred to
  `NST-702` per the ticket split.
- Added pytest-qt coverage in `tests/test_filter_panel.py` and expanded
  `tests/test_reports_page.py` to assert the panel is present on the reports
  surface.
