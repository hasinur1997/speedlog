# UI Context — Speedlog

## UX principles
- Menu-bar-first utility: the app lives in the macOS menu bar; the main window is opened
  on demand from the tray menu.
- Closing the main window hides it (app keeps tracking). Quitting from the tray menu
  stops tracking and exits (per product rule).
- Native macOS feel: system font (SF via Qt default), light/dark aware, no custom chrome.
- Speeds displayed in MB/s with 2 decimals (< 1 MB/s may show KB/s). Down arrow ↓ for
  download, up arrow ↑ for upload.

## Surfaces

### 1) System tray (menu bar)
- Icon + compact text if space allows: `↓ 5.02  ↑ 1.20 MB/s` (updates every 1s).
- Menu items: `Open Speedlog`, separator, `Pause/Resume Tracking` (v1 optional),
  separator, `Quit` (confirm dialog: "Quitting stops speed tracking. Quit?").

### 2) Main window (900×620 default, resizable)
Sidebar-less, two tabs (QTabWidget or segmented control):

**Tab A — Live**
- Large current speeds: `↓ 5.02 MB/s` / `↑ 1.20 MB/s`
- Session info line: "Connected since 10:01 AM"
- (Nice-to-have, own ticket) rolling 60s sparkline chart, pyqtgraph.

**Tab B — Reports**
Layout top→bottom:
1. **Filter bar** (one row):
   - Mode selector: `Date` | `Date Range` | `Date + Time` | `Date + Time Range`
   - QDateEdit / two QDateEdits / + QTimeEdit(s) shown per mode (others hidden)
   - `Apply` and `Reset` buttons
   - `Export PDF` button aligned right (exports the FULL filtered set, not just page)
2. **Table** (QTableView):
   Columns: `Date` | `Time` (e.g. `10:20 AM – 10:30 AM`) | `Download` | `Upload`
   - Sorted by start time DESC by default
   - Read-only, row selection, alternating row colors
   - Empty state label: "No records for the selected filter."
3. **Pagination bar**: `◀ Prev  Page 3 of 12  Next ▶` + total count label
   ("231 records"). Page size fixed at 20 for v1 (constant `PAGE_SIZE = 20`).

### 3) Export flow
- Click Export PDF → `QFileDialog.getSaveFileName` default name
  `Speedlog-Report-<YYYY-MM-DD>_<YYYY-MM-DD>.pdf`
- Busy cursor / disabled button during generation → success toast/statusbar message with
  "Reveal in Finder" option; failure → QMessageBox with logged error reference.

## Time & formatting rules
- Times shown as 12-hour with AM/PM (`10:05 AM`), dates as `YYYY-MM-DD` in table,
  human-readable (`July 6, 2026`) in PDF header.
- A record spanning midnight displays on its START date; time column shows
  `11:58 PM – 12:04 AM (+1)`.
- All conversions via `zoneinfo` from stored UTC.

## Styling
- Single `ui/styles.qss` loaded at startup; keep minimal — respect native look.
- Accent color: `#2E7CF6`. PDF header highlight uses the same accent.
- No hardcoded colors in Python; reference constants in `config.py`.

## Accessibility / quality bar
- All interactive widgets keyboard-reachable; tab order set on Reports tab.
- Tooltips on filter mode selector and Export button.
- Window remembers size/position (QSettings) — small ticket, v1 nice-to-have.
