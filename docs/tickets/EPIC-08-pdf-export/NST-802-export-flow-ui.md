# NST-802 — Export flow in UI (save dialog, busy state, result)

- **Epic:** EPIC-08 PDF Export
- **Type:** Feature
- **Priority:** P1
- **Estimate:** M
- **Status:** DONE
- **Depends on:** NST-801, NST-702

## Description
"Export PDF" button on the Reports tab exporting the FULL current filtered set.

## Acceptance criteria
- [x] QFileDialog.getSaveFileName, default name
      `Speedlog-Report-<from>_<to>.pdf` (or `-all` when unfiltered)
- [x] Generation runs in a worker (QThreadPool/QRunnable) — UI stays responsive;
      button disabled + statusbar "Exporting…" during run
- [x] Success: statusbar message + "Reveal in Finder" action
      (`QDesktopServices` / `open -R` on macOS)
- [x] Failure: QMessageBox with friendly text; full traceback in log
- [x] Exports ALL filtered records, not just the visible page (uses fetch_all_records)

## Test plan
pytest-qt with dialog + generator monkeypatched: worker path, button re-enable,
error path shows message; verify full-set (not page) query used.

## Implementation notes
- Files touched: `app/ui/reports/filter_panel.py`, `app/ui/reports/reports_page.py`,
  `app/ui/main_window.py`, `app/ui/styles.qss`, `tests/test_reports_page.py`,
  `tests/test_main_window.py`, `docs/progress-tracker.md`
- The Reports filter bar now includes an `Export PDF` button aligned to the right.
  Clicking it opens `QFileDialog.getSaveFileName()` with `Speedlog-Report-all.pdf`
  when no filter is applied, or local-time `from_to` bounds derived from the active
  filter when one is applied.
- Export generation runs on a `QRunnable` submitted to `QThreadPool.globalInstance()`.
  The worker opens its own SQLite connection, calls `Repository.fetch_all_records()`,
  and streams those rows into `generate_report()` so the visible page is never reused
  for export.
- While export is running, the button is disabled, a wait cursor is shown, and the
  main-window status bar displays `Exporting…`. Success updates the status bar and
  shows a `Reveal in Finder` action; failure shows a friendly `QMessageBox` while the
  worker logs the full traceback with `logger.exception(...)`.
- Verification: `env QT_QPA_PLATFORM=offscreen ./.venv/bin/pytest -q`,
  `./.venv/bin/ruff check .`, and `./.venv/bin/black --check .`
