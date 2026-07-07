# NST-804 — Export defaults to Downloads + completion notification

- **Epic:** EPIC-08 PDF Export
- **Type:** Feature
- **Priority:** P2
- **Estimate:** S
- **Status:** DONE
- **Depends on:** NST-803

## Description
Two export-flow refinements: the save dialog should default to the user's
Downloads folder (currently the home directory), and finishing an export should
show a simple system notification so the user knows the file is ready even if
the window is hidden.

## Acceptance criteria
- [x] `QFileDialog.getSaveFileName` defaults to the platform Downloads folder
      (`QStandardPaths.DownloadLocation`), falling back to the home directory
- [x] Successful export shows a tray notification (`QSystemTrayIcon.showMessage`)
      naming the exported file; failures do NOT notify (existing QMessageBox stays)
- [x] Notification flows main-thread-only: `ReportsPage.export_succeeded` signal →
      tray slot, wired in `main()`

## Technical notes
- Notification timeout constant lives in `config.py`.
- ReportsPage has no tray reference by design; use a signal and connect it in
  `main()` next to the other tray wiring.

## Test plan
pytest-qt: default save directory is the Downloads location; `export_succeeded`
emitted with the exported path on success only; tray slot calls `showMessage`
with the file name.

## Implementation notes
- Files touched: `app/config.py`, `app/ui/reports/reports_page.py`, `app/ui/tray.py`,
  `app/main.py`, `tests/test_reports_page.py`, `tests/test_tray.py`, `docs/ui-context.md`,
  `docs/progress-tracker.md`
- `_downloads_dir()` in reports_page uses
  `QStandardPaths.writableLocation(DownloadLocation)` with a `Path.home()` fallback;
  `_default_export_path` now builds on it.
- `ReportsPage.export_succeeded = Signal(str)` is emitted from `_on_export_succeeded`
  (main thread, after the status-bar/reveal-button update); `SpeedTrayIcon.on_export_succeeded`
  shows `showMessage(APP_NAME, "Report exported: <name>", Information,
  config.EXPORT_NOTIFY_TIMEOUT_MS)`. Wired in `main()` alongside the other tray connections.
- New constant `EXPORT_NOTIFY_TIMEOUT_MS = 5000` in `config.py`.
- Tests: Downloads default + home fallback, `export_succeeded` emitted on success only,
  tray slot calls `showMessage` with the file name.
- Verification: `env QT_QPA_PLATFORM=offscreen ./.venv/bin/pytest -q` (182 passed),
  `./.venv/bin/ruff check .`, `./.venv/bin/black --check .`
