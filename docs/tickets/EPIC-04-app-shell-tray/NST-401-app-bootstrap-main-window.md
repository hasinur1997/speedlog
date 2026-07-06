# NST-401 — App bootstrap & main window shell

- **Epic:** EPIC-04 App Shell & Tray
- **Type:** Feature
- **Priority:** P1
- **Estimate:** M
- **Status:** TODO
- **Depends on:** NST-102

## Description
Real `main.py` bootstrap + `ui/main_window.py`: window with Live / Reports tabs (empty
placeholders), styles.qss loading, single-instance behavior.

## Acceptance criteria
- [ ] main(): configure logging -> migrate DB -> create CollectorService (started in
      NST-402 wiring if not yet available, stub OK) -> tray -> exec()
- [ ] MainWindow 900x620, QTabWidget: "Live", "Reports" placeholder widgets
- [ ] Closing the window HIDES it (app keeps running in tray) — override closeEvent
- [ ] `QApplication.setQuitOnLastWindowClosed(False)`
- [ ] styles.qss loaded; app + window icon set
- [ ] Single instance: second launch activates existing (QLockFile or local socket)

## Test plan
pytest-qt: closeEvent hides not quits; tabs exist by objectName.

## Implementation notes (fill after DONE)
