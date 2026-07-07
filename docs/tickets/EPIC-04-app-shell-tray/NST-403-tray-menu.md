# NST-403 — Tray menu (Open, Quit with confirmation)

- **Epic:** EPIC-04 App Shell & Tray
- **Type:** Feature
- **Priority:** P1
- **Estimate:** S
- **Status:** DONE
- **Depends on:** NST-402

## Description
Context menu on the tray icon per ui-context.md.

## Acceptance criteria
- [x] Menu: "Open Speedlog" | separator | "Quit"
- [x] Open shows/raises MainWindow
- [x] Quit shows confirm dialog: "Quitting stops speed tracking. Quit?" (Quit/Cancel)
- [x] Confirmed quit triggers the shutdown path (NST-404); cancel does nothing

## Test plan
pytest-qt with dialog monkeypatched: cancel keeps app alive; confirm calls quit handler.

## Implementation notes
- **Files:** `app/ui/tray.py` (tray context menu, quit confirmation, `quit_confirmed`
  signal), `app/main.py` (wire `quit_confirmed` to `QApplication.quit()` so confirmed
  quits enter the app shutdown path), `tests/test_tray.py` (menu/open/quit behavior),
  `tests/test_main.py` (sandbox-safe guard test helper for repo verification).
- Tray menu now follows `docs/ui-context.md`: `Open Speedlog`, separator, `Quit`.
  Both the menu action and tray trigger path open the existing `MainWindow` through
  `MainWindow.bring_to_front()`.
- Quit confirmation is owned by `SpeedTrayIcon._confirm_quit()` and uses a modal
  `QMessageBox` with `Quit` and `Cancel`; only the destructive confirmation emits
  `quit_confirmed`.
- `NST-404` remains the place to attach `QApplication.aboutToQuit` to
  `CollectorService.stop()`/`wait()`. `NST-403` only routes the confirmed tray action
  into that future shutdown path via `app.quit()`.
- Repo verification in this sandbox required a small `tests/test_main.py` guard:
  the single-instance activation assertion skips only when `QLocalServer.listen()`
  is unavailable in the execution environment.
