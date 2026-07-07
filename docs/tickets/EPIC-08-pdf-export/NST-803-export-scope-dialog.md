# NST-803 — Export scope confirmation dialog

- **Epic:** EPIC-08 PDF Export
- **Type:** Feature
- **Priority:** P1
- **Estimate:** S
- **Status:** DONE
- **Depends on:** NST-802

## Description
Clicking "Export PDF" currently jumps straight to the save dialog and exports the
table's active filter. Users want to confirm WHAT gets exported first: a popup
should ask for the export scope, defaulting to today's records, with the option
to pick a date range or a date + time range instead (or everything).

## Acceptance criteria
- [x] Clicking `Export PDF` opens a modal confirmation dialog BEFORE the save dialog
- [x] Dialog scope options: `Date` (default, initialized to today), `Date Range`,
      `Date + Time Range`, `All records`; editors show/hide per scope like the filter bar
- [x] Accepting the dialog exports the CHOSEN scope (not the table filter): the scope is
      converted to a `ReportFilter` via the existing `build_report_filter`, drives the
      default save filename, and is passed to the export worker
- [x] Cancelling the dialog aborts the export (no save dialog, no worker)
- [x] PDF header filter label reflects the chosen scope (via `summarize_filter_state`)

## Technical notes
- Reuse `ReportFilterUiState` / `ReportFilterMode` and the pure helpers in
  `app/ui/reports/filter_builder.py`; no new SQL, no repository changes.
- Dialog lives in `app/ui/reports/export_dialog.py`; `ReportsPage.export_pdf()` gains a
  prompt step and `_start_export` takes the scope filter + label explicitly.
- Keep worker/threading behavior from NST-802 unchanged.

## Test plan
pytest-qt: dialog defaults (Date mode, today's date, editor visibility), per-scope
`selected_state()` values, cancel aborts export, accepted scope drives default
filename + worker `ReportFilter` + PDF filter label (dialog `exec` monkeypatched).

## Implementation notes
- Files touched: `app/ui/reports/export_dialog.py` (new), `app/ui/reports/reports_page.py`,
  `tests/test_export_dialog.py` (new), `tests/test_reports_page.py`, `docs/ui-context.md`,
  `docs/progress-tracker.md`
- `ExportOptionsDialog` (modal `QDialog`) reuses `ReportFilterMode`/`ReportFilterUiState`
  and the filter panel's display-format constants; scope combo data is the mode enum with
  `None` meaning "All records". Editors show/hide per scope; defaults are today's date and
  a 00:00–23:59 time range. OK button is relabeled "Export".
- `ReportsPage.export_pdf()` now runs `_prompt_export_state()` first; the accepted state is
  converted with `build_report_filter` and summarized with `summarize_filter_state`, then
  passed explicitly to `_start_export(out_path, report_filter=..., filter_label=...)`.
  The table's active filter no longer influences exports; `_current_filter_summary` was
  removed as dead code. Worker/threading behavior from NST-802 is unchanged.
- Tests monkeypatch `ExportOptionsDialog.exec` to accept/reject with optional widget setup;
  coverage: default today filename, all-records + date-range filenames, cancel aborts,
  date+time-range scope reaches the worker query and PDF label, dialog defaults/visibility.
- Verification: `env QT_QPA_PLATFORM=offscreen ./.venv/bin/pytest -q` (180 passed),
  `./.venv/bin/ruff check .`, `./.venv/bin/black --check .`
