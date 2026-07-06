# NST-701 — Filter panel UI (4 modes)

- **Epic:** EPIC-07 Filters
- **Type:** Feature
- **Priority:** P1
- **Estimate:** M
- **Status:** TODO
- **Depends on:** NST-601

## Description
`ui/reports/filter_panel.py`: mode selector + date/time editors per ui-context.md.

## Acceptance criteria
- [ ] Mode combo: Date | Date Range | Date + Time | Date + Time Range
- [ ] Widget visibility per mode: 1 QDateEdit / 2 QDateEdits / QDateEdit+QTimeEdit /
      QDateEdit + 2 QTimeEdits (time range applies within ONE date for v1)
- [ ] Apply button emits `filter_applied(uiFilterState)`; Reset returns to
      "no filter" (all records) and emits
- [ ] Calendar popups on date editors; sensible defaults (today)
- [ ] Time is optional by design: plain Date / Date Range modes ignore time entirely

## Test plan
pytest-qt: mode switch shows/hides correct editors; Apply emits state; Reset clears.

## Implementation notes (fill after DONE)
