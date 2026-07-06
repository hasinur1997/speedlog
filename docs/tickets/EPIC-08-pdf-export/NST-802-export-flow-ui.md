# NST-802 — Export flow in UI (save dialog, busy state, result)

- **Epic:** EPIC-08 PDF Export
- **Type:** Feature
- **Priority:** P1
- **Estimate:** M
- **Status:** TODO
- **Depends on:** NST-801, NST-702

## Description
"Export PDF" button on the Reports tab exporting the FULL current filtered set.

## Acceptance criteria
- [ ] QFileDialog.getSaveFileName, default name
      `Speedlog-Report-<from>_<to>.pdf` (or `-all` when unfiltered)
- [ ] Generation runs in a worker (QThreadPool/QRunnable) — UI stays responsive;
      button disabled + statusbar "Exporting…" during run
- [ ] Success: statusbar message + "Reveal in Finder" action
      (`QDesktopServices` / `open -R` on macOS)
- [ ] Failure: QMessageBox with friendly text; full traceback in log
- [ ] Exports ALL filtered records, not just the visible page (uses fetch_all_records)

## Test plan
pytest-qt with dialog + generator monkeypatched: worker path, button re-enable,
error path shows message; verify full-set (not page) query used.

## Implementation notes (fill after DONE)
