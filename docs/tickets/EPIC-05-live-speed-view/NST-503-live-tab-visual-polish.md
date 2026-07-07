# NST-503 — Live tab visual polish

- **Epic:** EPIC-05 Live Speed View
- **Type:** Bug
- **Priority:** P2
- **Estimate:** S
- **Status:** DONE
- **Depends on:** NST-502, NST-605

## Description
Refine the shared tab presentation and give the Live tab a surfaced white background so it
feels intentional alongside the already-polished Reports tab.

## Acceptance criteria
- [x] Main window tabs feel cleaner with clearer inactive/active states
- [x] Live tab content renders inside a white surfaced panel instead of a transparent page
- [x] Existing live-speed labels, session status, and sparkline behavior remain unchanged
- [x] pytest-qt coverage protects the new live-tab styling hooks/structure

## Technical notes
- Keep the change small: styling stays in `app/ui/styles.qss` with only the structural hooks
  needed in `app/ui/live_view.py`.
- Preserve the collector/UI signal wiring and hidden-tab redraw behavior from NST-501/NST-502.

## Test plan
- `QT_QPA_PLATFORM=offscreen .venv/bin/pytest -q tests/test_live_view.py tests/test_main_window.py`
- `QT_QPA_PLATFORM=offscreen .venv/bin/pytest -q`
- `.venv/bin/ruff check .`
- `.venv/bin/black --check .`

## Implementation notes
- Files touched: `app/ui/live_view.py`, `app/ui/styles.qss`, `tests/test_live_view.py`,
  `tests/test_main_window.py`, `docs/progress-tracker.md`
- Added a named `liveSurface` container so the Live tab can render as a white panel while
  leaving the existing speed/session/chart update behavior intact.
- Refined the main tab button spacing and selected-state border so the tab bar reads more
  cleanly without changing navigation behavior.
- Added pytest-qt assertions for the surfaced Live tab structure and styled sparkline hooks.
