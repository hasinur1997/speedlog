# NST-704 — Date/time editor affordances: calendar icon, styled popup, time steppers

- **Epic:** EPIC-07 filters
- **Type:** Feature
- **Priority:** P2
- **Estimate:** M
- **Status:** DONE
- **Depends on:** NST-701, NST-803

## Description
User feedback on the Reports filter bar (and the export scope dialog, which reuses the
same editors):
1. Date fields don't advertise that clicking opens a calendar — add a **calendar icon**
   on the field so the popup affordance is obvious.
2. The calendar popup renders with stock Qt colors — its **navigation bar and selection
   colors must match the design system** (tokens in `ui/styles.qss`, accent `#2E7CF6`).
3. Time fields look like plain text boxes — style them as a recognizable **time picker**
   (clock icon + visible up/down steppers) while keeping **manual keyboard input**;
   date fields likewise keep manual input plus the calendar popup.

## Acceptance criteria
- [x] Every QDateEdit (filter panel + export dialog) shows a calendar glyph in its
      drop-down button; calendar popup stays enabled and typing in the field still works.
- [x] The QCalendarWidget popup matches the design tokens: light navigation bar, styled
      prev/next chevrons, accent-colored selected day, white grid, muted disabled days.
- [x] Every QTimeEdit shows a clock glyph and styled up/down chevron steppers; manual
      typing and stepping both work.
- [x] Icons are SVG assets under `app/ui/icons/`, referenced from `styles.qss` via a
      relative `url(icons/...)` that `load_styles()` resolves to an absolute path (QSS
      urls are cwd-relative otherwise). No hardcoded colors in Python.
- [x] Editor styling applies app-wide (class selectors), so both the reports filter
      panel and the export options dialog pick it up.

## Technical notes
- QSS subcontrols: `QDateEdit::drop-down` (image), `QTimeEdit::up-button/down-button`
  (chevron images), `QCalendarWidget QWidget#qt_calendar_navigationbar`,
  `QToolButton#qt_calendar_prevmonth/nextmonth` (qproperty-icon), calendar view
  selection colors.
- The clock glyph is drawn via `background-image` with the left padding built into the
  SVG viewBox (QSS background-position only supports keywords).

## Test plan
- `tests/test_main.py`: `load_styles()` leaves no unresolved `url(icons/`; every
  resolved icon path exists on disk.
- `tests/test_filter_panel.py` / `tests/test_export_dialog.py`: all date edits have
  `calendarPopup` enabled; time edits use up/down button symbols and remain editable.

## Implementation notes (fill after DONE)
- New SVGs in `app/ui/icons/`: calendar, clock (left padding baked into the viewBox so
  it works with QSS `background-position: left center`), chevron-up/down (time steppers
  + combo arrow), chevron-left/right (calendar nav, set via `qproperty-icon`).
- `styles.qss`: the filter-field rules were promoted from `#reportsFilterPanel` scope to
  class-wide `QComboBox/QDateEdit/QTimeEdit` so the export dialog inherits them; added
  `QDateEdit::drop-down` calendar image, `QTimeEdit` clock background + up/down button
  images, and a full `QCalendarWidget` section (light nav bar, hover states, accent
  selection, muted out-of-month days).
- `app.main.load_styles()` now rewrites `url(icons/` to the absolute
  `app/ui/icons/` path — QSS urls are otherwise cwd-relative and would break when the
  app is launched from outside the repo.
- No Python widget changes were needed: `setCalendarPopup(True)` and spin-button time
  edits already existed; only their affordances were invisible.
- Follow-up fix (user feedback, twice): glyphs read too large in the 30px fields. The
  SVGs are now authored with `viewBox` equal to the width/height attributes (geometry in
  final pixels: calendar 12x12, clock 20x12 with baked left padding, stepper chevrons
  8x5, calendar nav chevrons 8x8), so the renderer cannot fall back to the old 24-unit
  viewBox scale; QTimeEdit left padding 32 → 28px.
- Tests: stylesheet icon-resolution check in `tests/test_main.py`; picker-affordance
  assertions (calendarPopup, UpDownArrows, editable) in `tests/test_filter_panel.py`
  and `tests/test_export_dialog.py`. Verified visually via offscreen grabs of the
  filter panel, calendar popup, and export dialog.
