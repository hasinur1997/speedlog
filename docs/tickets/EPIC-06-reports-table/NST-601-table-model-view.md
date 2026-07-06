# NST-601 — Reports table model + view

- **Epic:** EPIC-06 Reports Table
- **Type:** Feature
- **Priority:** P1
- **Estimate:** M
- **Status:** TODO
- **Depends on:** NST-203, NST-401

## Description
`ui/reports/table_model.py` (QAbstractTableModel over a page of SpeedRecords) and
`ui/reports/reports_page.py` (QTableView wiring) — the Reports tab body.

## Acceptance criteria
- [ ] Columns: Date | Time | Download | Upload (headers exactly)
- [ ] Model exposes `set_page(records: list[SpeedRecord])`; view is read-only,
      row-select, alternating colors, sorted newest-first (data pre-sorted by query)
- [ ] Reads via a UI-thread repository connection (its own, per threading rules)
- [ ] Auto-refresh: segment_closed signal reloads current page IF user is on page 1
      with no manual position (don't yank the user around)
- [ ] Empty state label when 0 rows

## Test plan
pytest-qt: model rowCount/columnCount/data for a seeded page; empty state toggles.

## Implementation notes (fill after DONE)
