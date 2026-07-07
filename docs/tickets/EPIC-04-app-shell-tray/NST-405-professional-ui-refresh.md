# NST-405 — Professional UI refresh: segmented tabs & cohesive chrome

- **Epic:** EPIC-04 App shell & tray
- **Type:** Task
- **Priority:** P2
- **Estimate:** S
- **Status:** DONE
- **Depends on:** NST-605, NST-802

## Description
User feedback: the overall interface looks unprofessional, and the tab design in
particular reads poorly (bordered pills that shift vertically between states, muddy
inactive text on the same background as the window). Rework the stylesheet into a
cohesive, professional light design: tabs as a true quiet segmented control, a soft
app background so the white surfaces read as elevated cards, and unified control
styling (radius, heights, hover/pressed/focus states) across filter bar, buttons,
table, and pagination.

## Acceptance criteria
- [x] Tabs render as a subtle segmented control: inactive tabs are quiet (no border,
      muted text), the active tab is a white segment with a hairline border and dark
      text; no vertical jump between selected/unselected states.
- [x] Window content background is visually distinct from the white card surfaces.
- [x] All buttons/inputs share one control radius and consistent hover, pressed,
      focus, and disabled states; the accent (`#2E7CF6` from config) stays the single
      primary color.
- [x] Table header is visually quieter than body text; row selection uses a soft
      accent tint with readable dark text instead of a saturated fill.
- [x] Change is stylesheet-only (`app/ui/styles.qss`); no widget code changes; all
      existing objectName styling hooks keep working.
- [x] `pytest -q` and `ruff check .` pass.

## Technical notes
- `docs/ui-context.md` → Styling: tabs "should read like a subtle segmented control";
  keep accent `#2E7CF6`; single stylesheet loaded in `app/main.py::load_styles`.
- The existing sheet already commits to a hardcoded light design (white surfaces), so
  this ticket refines that design consistently rather than introducing palette() mixes
  that clash with it. Full dark-mode support would be its own ticket.
- `qproperty-drawBase: 0` on the QTabBar removes the document-mode base line under tabs.

## Test plan
- Existing pytest-qt styling-hook tests (objectNames in `test_main_window.py`,
  `test_reports_page.py`) continue to pass — they pin every selector this sheet uses.
- Manual visual check of both tabs, filter modes, pagination, and export button states.

## Implementation notes (fill after DONE)
- Files touched: `app/ui/styles.qss` only (plus this ticket + progress tracker).
- Introduced a documented token set at the top of the stylesheet (backgrounds,
  borders, text tiers, accent states, radii 16/12/8) — future styling should reuse it.
- Tabs: `qproperty-drawBase: 0` on the QTabBar removes the document-mode base line;
  every tab keeps a 1px (transparent when inactive) border and identical padding so
  selection never shifts geometry. Active = white segment on the `#EEF1F6` app bg.
- Table selection changed from saturated accent fill to accent tint `#E2EDFE` with
  dark text; header is 12px muted `#64748B` on white with a hairline underline.
- Verified visually via offscreen `window.grab()` screenshots of both tabs, plus
  `pytest -q` (174 passed) and `ruff check .` clean.
- Deliberately NOT done (own tickets if wanted): dark-mode variant of the sheet;
  the hardcoded-light look predates this ticket (NST-503/605).
