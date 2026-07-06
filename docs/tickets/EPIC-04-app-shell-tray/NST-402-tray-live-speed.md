# NST-402 — System tray icon with live speed

- **Epic:** EPIC-04 App Shell & Tray
- **Type:** Feature
- **Priority:** P1
- **Estimate:** M
- **Status:** TODO
- **Depends on:** NST-401, NST-305

## Description
`ui/tray.py`: QSystemTrayIcon showing current speeds, updated from CollectorService.

## Acceptance criteria
- [ ] Tray icon visible at startup; tooltip `↓ 5.02 MB/s  ↑ 1.20 MB/s` updated on
      speed_sampled signal (throttle UI update to 1/s)
- [ ] macOS: template icon so it adapts to light/dark menu bar
- [ ] Shared `format_speed(bps)` helper used (KB/s below 1 MB/s, 2 decimals)
- [ ] Offline state shows `— offline` (session_changed signal)
- [ ] Double-click / trigger opens MainWindow (show + raise + activate)

## Test plan
pytest-qt: emit fake speed_sampled -> tooltip text; session_changed(False) -> offline text.
format_speed unit tests (0, 999 KB/s, 1.0 MB/s, 125 MB/s).

## Implementation notes (fill after DONE)
