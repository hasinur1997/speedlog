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
- Speed-gauge template icon (light/dark adaptive); hover tooltip shows the live speeds.
- Menu items: disabled live-speed status row `↓ 5.02 MB/s  ↑ 1.20 MB/s` (updates every
  1s; `— offline` when disconnected), separator, `Open Speedlog`, separator, `Quit`
  (confirm dialog: "Quitting stops speed tracking. Quit?").
- Unbundled dev runs patch `CFBundleName` at startup (`app/macos.py`) so the macOS app
  menu reads "Speedlog", not "Python".
- `Pause/Resume Tracking` menu item remains a v1-optional idea (own ticket).

### 2) Main window (900×620 default, resizable)
Sidebar-less, two tabs (QTabWidget or segmented control):
- Tabs should read like a subtle segmented control with clear active/inactive states and
  comfortable outer padding around the main content.

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
   - Presented inside a rounded report surface with a short title/subtitle for context
   - Empty state label: "No records for the selected filter."
3. **Pagination bar**: `◀ Prev  1 2 3 4 5 6 ... 10  Next ▶  Page 3 of 10` +
   total count label (`"231 records"`). Page size fixed at 20 for v1
   (constant `PAGE_SIZE = 20`), with direct page links collapsing via ellipses when needed.

### 3) Export flow
- Click Export PDF → modal scope dialog first: `Date` (default, today) |
  `Date Range` | `Date + Time Range` | `All records`; Cancel aborts the export
- Accept → `QFileDialog.getSaveFileName` defaulting to the Downloads folder, name
  `Speedlog-Report-<YYYY-MM-DD>_<YYYY-MM-DD>.pdf` (from the chosen scope,
  `-all` for All records)
- Busy cursor / disabled button during generation → success statusbar message with
  "Reveal in Finder" option plus a tray notification naming the file;
  failure → QMessageBox with logged error reference (no notification).

## Time & formatting rules
- Times shown as 12-hour with AM/PM (`10:05 AM`), dates as `YYYY-MM-DD` in table,
  human-readable (`July 6, 2026`) in PDF header.
- A record spanning midnight displays on its START date; time column shows
  `11:58 PM – 12:04 AM (+1)`.
- All conversions via `zoneinfo` from stored UTC.

## Styling
- Single `ui/styles.qss` loaded at startup; keep minimal — respect native look.
- SVG glyphs for editors live in `ui/icons/` and are referenced as `url(icons/...)` in
  the QSS; `app.main.load_styles()` resolves them to absolute paths at startup.
- Date fields show a calendar glyph and open a design-matched QCalendarWidget popup;
  time fields show a clock glyph with chevron steppers. Both keep manual keyboard input.
- Accent color: `#2E7CF6`. PDF header highlight uses the same accent.
- Prefer palette-aware styling so the app still feels native in light/dark appearances.
- No hardcoded colors in Python; reference constants in `config.py`.

## Accessibility / quality bar
- All interactive widgets keyboard-reachable; tab order set on Reports tab.
- Tooltips on filter mode selector and Export button.
- Window remembers size/position (QSettings) — small ticket, v1 nice-to-have.
