# NST-401 — App bootstrap & main window shell

- **Epic:** EPIC-04 App Shell & Tray
- **Type:** Feature
- **Priority:** P1
- **Estimate:** M
- **Status:** DONE
- **Depends on:** NST-102

## Description
Real `main.py` bootstrap + `ui/main_window.py`: window with Live / Reports tabs (empty
placeholders), styles.qss loading, single-instance behavior.

## Acceptance criteria
- [x] main(): configure logging -> migrate DB -> create CollectorService (started in
      NST-402 wiring if not yet available, stub OK) -> tray -> exec()
- [x] MainWindow 900x620, QTabWidget: "Live", "Reports" placeholder widgets
- [x] Closing the window HIDES it (app keeps running in tray) — override closeEvent
- [x] `QApplication.setQuitOnLastWindowClosed(False)`
- [x] styles.qss loaded; app + window icon set
- [x] Single instance: second launch activates existing (QLockFile or local socket)

## Test plan
pytest-qt: closeEvent hides not quits; tabs exist by objectName.

## Implementation notes (fill after DONE)
- Files touched: `app/main.py` (rewritten bootstrap), `app/ui/main_window.py`,
  `app/ui/styles.qss`, `app/config.py` (window size, icon, single-instance constants),
  `tests/test_main.py`, `tests/test_main_window.py`.
- Single instance uses **QLocalServer/QLocalSocket** (not QLockFile): the first launch
  listens on `config.SINGLE_INSTANCE_KEY`; a second launch connects (which both detects
  the running instance and requests activation), then exits 0. `SingleInstanceGuard`
  in `app/main.py` emits `activate_requested` → `MainWindow.bring_to_front()`.
  A stale socket left by a crash (verified with SIGKILL) is removed via
  `QLocalServer.removeServer()` before listening.
- App/window icon is painted at runtime (`app_icon()` in `app/ui/main_window.py`,
  accent rounded rect + "S" glyph) — no bundled asset yet. NST-402 (tray) should reuse
  `app_icon()`; a real .icns asset can come with packaging (NST-902).
- `CollectorService` is instantiated in `main()` but NOT started; it is kept alive as
  `window.collector_service`. NST-402 wires signals + `start()`; tray creation also
  deferred to NST-402 per epic split.
- DB migration runs on a short-lived main-thread connection (`migrate_database()`),
  closed before the window shows; the collector opens its own connection when started.
- Verified end-to-end on macOS: real launch, window renders (900x620, segmented tabs),
  second launch exits 0 in ~0.16s and activates the first, close hides without quitting.
