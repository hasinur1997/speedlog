# NST-604 — Numbered pagination links

- **Epic:** EPIC-06 Reports Table
- **Type:** Feature
- **Priority:** P2
- **Estimate:** S
- **Status:** DONE
- **Depends on:** NST-602

## Description
Add direct page-number links to the reports pagination bar so users can jump straight
to a page instead of stepping only with Prev/Next.

## Acceptance criteria
- [x] Pagination shows clickable page numbers in addition to Prev/Next and the total count
- [x] Clicking a page number loads that page directly and updates the active-page styling/state
- [x] For larger page counts, the page-number strip collapses with ellipses while keeping the
      first page, last page, and the current-page neighborhood visible
- [x] Existing NST-602 behavior remains intact: page state survives tab switches and resets to
      page 1 on filter change

## Technical notes
- Keep the implementation inside `ui/reports/reports_page.py`; repository pagination stays
  unchanged.
- Use object names on dynamic page buttons/ellipsis labels so pytest-qt can inspect the strip.
- Avoid hardcoded pagination limits in widget code; keep tunables in `config.py`.

## Test plan
pytest-qt with enough seeded rows for 10 pages: assert the initial strip matches
`1 2 3 4 5 6 ... 10`, direct-jump to a middle page, verify collapsed ellipsis behavior,
and confirm filter-reset/tab-switch behavior still passes.

## Implementation notes
- Files touched: `app/config.py`, `app/ui/reports/reports_page.py`,
  `tests/test_reports_page.py`, `docs/ui-context.md`, `docs/progress-tracker.md`
- Added `config.PAGINATION_MAX_VISIBLE_BUTTONS` so the page-link strip can collapse
  consistently without hardcoding the visible-button count in widget code.
- `ReportsPage` now rebuilds a dynamic numbered page-link strip on each reload, keeping
  direct jumps, the existing `Page X of Y` label, and the `Prev`/`Next` controls together.
- Large result sets collapse to a first/current-neighborhood/last pattern such as
  `1 2 3 4 5 6 ... 10` on the first page and `1 ... 4 5 6 7 8 ... 10` in the middle.
- Existing NST-602 behaviors remained green: tab switches preserve the current page, and
  filter changes still reset to page 1.
