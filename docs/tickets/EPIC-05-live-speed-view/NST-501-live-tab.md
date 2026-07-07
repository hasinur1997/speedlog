# NST-501 — Live tab: current speeds + session info

- **Epic:** EPIC-05 Live Speed View
- **Type:** Feature
- **Priority:** P2
- **Estimate:** S
- **Status:** DONE
- **Depends on:** NST-401, NST-305

## Description
`ui/live_view.py`: big readable current download/upload numbers plus
"Connected since <time>" line.

## Acceptance criteria
- [x] Large labels `↓ X MB/s` / `↑ Y MB/s` updating on speed_sampled (only when visible)
- [x] Session line from session_changed: "Connected since 10:01 AM" / "Offline"
- [x] Uses shared format_speed; local time formatting via zoneinfo
- [x] Layout survives resize; dark mode legible

## Test plan
pytest-qt: signals update labels; offline state; hidden tab skips repaint work.

## Implementation notes
- **Files:** `app/ui/live_view.py` (new `LiveView` widget + local-time formatting helper),
  `app/ui/main_window.py` (real Live tab instead of placeholder), `app/main.py` (collector
  signal wiring into the live tab), `app/collector/service.py` (session_changed now emits
  the UTC change timestamp), `app/ui/tray.py` (updated slot signature), `app/config.py`
  (live-view spacing/font constants), `tests/test_live_view.py`, `tests/test_main_window.py`,
  `tests/test_service.py`, `tests/test_tray.py`, `docs/progress-tracker.md`.
- Speed labels use the shared `format_speed()` helper and default to `0.00 KB/s`; when the
  Live tab is hidden they cache the latest sample and defer `setText()` work until the tab
  becomes visible again.
- The session line is rendered on the UI thread from the collector's UTC timestamp using
  `zoneinfo`; offline transitions also reset the visible speeds to zero for clarity.
- Verification run: `QT_QPA_PLATFORM=offscreen .venv/bin/pytest -q` (130 passed, 1 skipped),
  `.venv/bin/ruff check .`, `.venv/bin/black --check .`.
