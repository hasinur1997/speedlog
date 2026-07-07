# NST-605 — Reports table and tabs visual polish

- **Epic:** EPIC-06 Reports Table
- **Type:** Feature
- **Priority:** P2
- **Estimate:** M
- **Status:** DONE
- **Depends on:** NST-604, NST-401

## Description
Polish the main window tabs and the reports table presentation so the app looks more
professional while still preserving the native macOS feel described in `docs/ui-context.md`.

## Acceptance criteria
- [x] Main tabs present as a more polished segmented control with clearer active/inactive states
- [x] Reports tab uses stronger visual hierarchy (surface, heading, spacing) without changing
      the existing pagination/data-loading behavior
- [x] Reports table styling is refined (header, row rhythm, empty state, pagination controls)
      while staying read-only and keyboard reachable
- [x] Existing reports behaviors remain intact and covered by pytest-qt checks

## Technical notes
- Keep styling in `ui/styles.qss` plus small widget-structure adjustments in
  `ui/main_window.py` and `ui/reports/reports_page.py`.
- Preserve current object names and add new ones where needed so tests can assert the
  presence of styling hooks without relying on screenshots.
- Favor palette-aware QSS so the result stays compatible with the native light/dark feel.

## Decisions
- Assumption for this ticket: "professional" means a subtle, native-feeling refresh rather
  than a heavily custom/branded redesign.

## Test plan
- pytest-qt checks for the tab container structure/styling hooks
- pytest-qt checks for the reports surface/header/pagination container and refined table config
- Existing reports pagination tests remain green

## Implementation notes
- Files touched: `app/config.py`, `app/ui/main_window.py`, `app/ui/reports/reports_page.py`,
  `app/ui/styles.qss`, `tests/test_main_window.py`, `tests/test_reports_page.py`,
  `docs/ui-context.md`, `docs/progress-tracker.md`
- Added a padded `mainWindowContent` wrapper and enabled `documentMode` on the tab widget so
  the stylesheet can render the main tabs as cleaner segmented controls without changing tab
  behavior.
- `ReportsPage` now renders inside a surfaced panel with a title/subtitle, a named table area,
  and a named pagination bar while preserving the existing pagination/query logic.
- Refined the report table configuration with a fixed row rhythm, no grid lines, word-wrap off,
  and palette-aware QSS for headers, rows, empty state, and pagination controls.
- Added pytest-qt assertions for the new main-window/report-page styling hooks so the visual
  structure stays covered even though the ticket is mostly presentation-focused.
