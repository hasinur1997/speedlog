# NST-402 — System tray icon with live speed

- **Epic:** EPIC-04 App Shell & Tray
- **Type:** Feature
- **Priority:** P1
- **Estimate:** M
- **Status:** DONE
- **Depends on:** NST-401, NST-305

## Description
`ui/tray.py`: QSystemTrayIcon showing current speeds, updated from CollectorService.

## Acceptance criteria
- [x] Tray icon visible at startup; tooltip `↓ 5.02 MB/s  ↑ 1.20 MB/s` updated on
      speed_sampled signal (throttle UI update to 1/s)
- [x] macOS: template icon so it adapts to light/dark menu bar
- [x] Shared `format_speed(bps)` helper used (KB/s below 1 MB/s, 2 decimals)
- [x] Offline state shows `— offline` (session_changed signal)
- [x] Double-click / trigger opens MainWindow (show + raise + activate)

## Test plan
pytest-qt: emit fake speed_sampled -> tooltip text; session_changed(False) -> offline text.
format_speed unit tests (0, 999 KB/s, 1.0 MB/s, 125 MB/s).

## Implementation notes (fill after DONE)
- **Files:** `app/ui/tray.py` (new `SpeedTrayIcon` + `tray_icon()`), `app/formatting.py`
  (new shared `format_speed()`), `app/config.py` (`TRAY_TOOLTIP_MIN_INTERVAL_SECS`),
  `app/main.py` (tray wiring; CollectorService now started here per NST-401 handoff),
  `docs/architecture-context.md` (formatting.py added to package layout),
  `tests/test_tray.py`, `tests/test_formatting.py`.
- `format_speed` lives in `app/formatting.py` (not under `ui/`) because `export/pdf_report.py`
  will also use it (code-standards: one shared module). SI units: 1 MB = 1,000,000 bytes.
- Template icon: monochrome black glyph pixmap with `QIcon.setIsMask(True)` — macOS renders
  it as a template (light/dark adaptive); harmless no-op on other platforms.
- Throttle uses `time.monotonic()` with `TRAY_TOOLTIP_MIN_INTERVAL_SECS = 0.9` (just under
  the 1s sample cadence so signal-delivery jitter doesn't drop alternate updates). Going
  offline resets the throttle so the first sample after reconnect shows immediately.
- Tooltip starts as `— offline` until the first `speed_sampled` arrives.
- `SpeedTrayIcon.activated` opens the window for both `Trigger` and `DoubleClick` reasons
  via `MainWindow.bring_to_front()`; `Context` reserved for the NST-403 menu.
- For NST-403/404: the tray is parented to the QApplication in `main()`; the collector is
  running and still needs stop()+flush on quit (NST-404).
