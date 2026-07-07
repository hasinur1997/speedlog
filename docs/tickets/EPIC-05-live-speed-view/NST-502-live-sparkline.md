# NST-502 — Live 60s sparkline chart (nice-to-have)

- **Epic:** EPIC-05 Live Speed View
- **Type:** Feature
- **Priority:** P3
- **Estimate:** M
- **Status:** DONE
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

## Implementation notes
- Added `pyqtgraph==0.13.7` to `requirements.txt` for the sparkline dependency required by this ticket.
- Extended `app/ui/live_view.py` with a rolling 60-sample download/upload sparkline that auto-scales its Y range and redraws only while the Live tab is visible.
- The sparkline buffer continues collecting samples while hidden, then redraws once on re-show so label/chart state catches up without background repaint churn.
- Added pytest-qt coverage in `tests/test_live_view.py` for the 60-sample cap, repeated sample pushes, and hidden-tab redraw pausing.
