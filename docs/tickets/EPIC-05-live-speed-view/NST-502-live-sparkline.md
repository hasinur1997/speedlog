# NST-502 — Live 60s sparkline chart (nice-to-have)

- **Epic:** EPIC-05 Live Speed View
- **Type:** Feature
- **Priority:** P3
- **Estimate:** M
- **Status:** TODO
- **Depends on:** NST-501

## Description
Rolling 60-sample chart of download/upload under the live numbers.

## Acceptance criteria
- [ ] pyqtgraph line chart, two series, fixed 60s window, auto-scaled Y
- [ ] Paused (no redraws) while Live tab not visible
- [ ] Dependency `pyqtgraph` added to requirements with a note in this ticket
- [ ] CPU stays negligible (<2% on idle traffic)

## Test plan
pytest-qt smoke: widget accepts 200 pushes without error; buffer capped at 60.

## Implementation notes (fill after DONE)
