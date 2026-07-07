# Project Overview — Speedlog

## What we are building
A macOS desktop application (Python + PySide6) that passively monitors real internet
throughput, records speed history as time-range segments, displays them in a filterable,
paginated report table, and exports reports as PDF.

Cross-platform support for Linux and Windows is planned later — all core code must stay
platform-agnostic; only OS integration (autostart, packaging) may be platform-specific.

## Product name
**Speedlog** (working name — trademark & domain check pending before public launch).
- Bundle ID: `com.speedlog.app` · App process/display name: "Speedlog"
- Python package name: `app` (used consistently in code, specs, and entry point)
- Data dir: `~/Library/Application Support/Speedlog` · Logs: `~/Library/Logs/Speedlog`

## Positioning (drives all marketing + feature priority)
Speedlog is NOT marketed as a "speed meter" (commodity, free competitors). It is an
**internet reliability logger and evidence generator**: continuous connection history as
readable time segments, filterable, exportable as a named PDF report.
Primary buyer stories:
1. "Prove to my ISP that my connection degrades every evening" (PDF evidence)
2. Remote workers documenting connectivity for employers/clients
3. Small offices wanting lightweight per-machine connection logging

## Commercial model — Free vs Pro (build with this split in mind)
| Capability | Free | Pro |
|---|---|---|
| Live speed in menu bar (F1, F7) | ✅ | ✅ |
| Automatic segment recording (F2) | ✅ | ✅ |
| History retention | Last **7 days** | Unlimited |
| Reports table + pagination (F3) | ✅ (within 7 days) | ✅ |
| Filters: date / range / time (F4) | ✅ (within 7 days) | ✅ |
| PDF export (F5) | ❌ (button visible, prompts upgrade) | ✅ |
| Autostart at login (F6) | ✅ | ✅ |
Implementation rule for v1: build everything unlocked; gating is a thin feature-flag
layer (`config.PRO_FEATURES_ENABLED`) added in ticket NST-905 — do NOT scatter
license checks through the codebase. One gate module, checked at the UI boundary only.
Retention limit = a scheduled DELETE of records older than N days when not Pro.

## Core behavior rules (source of truth)
1. **Passive monitoring**: speed = delta of network interface byte counters sampled every
   1 second via `psutil`. We measure actual traffic, NOT ISP capacity. No speed-test servers.
2. **Tracking lifecycle**:
   - App launches automatically at login (macOS Login Item / LaunchAgent).
   - Tracking runs while the app is running.
   - When the user quits the app, tracking STOPS. No background daemon survives quit.
   - On quit, the currently open segment must be closed and saved (no data loss).
3. **Session**: a session starts when internet connectivity is detected (or app starts with
   connectivity) and ends on disconnect or app quit.
4. **Segment (a "record")**: a continuous time range during which the smoothed speed stays
   within the same band. When speed moves out of the band (with hysteresis), the current
   segment closes and a new one opens.

## Record fields (every report row)
| Field | Example |
|---|---|
| download_speed | 5.0 MB/s |
| upload_speed | 1.2 MB/s |
| date | 2026-07-06 |
| time range | 10:20 AM – 10:30 AM |

Stored internally as UTC epoch integers (`start_ts`, `end_ts`); rendered in local time.

## Features (v1 scope)
- F1. Real-time upload & download speed (tray + live view, updates every 1s)
- F2. Automatic history recording as same-speed segments (bucketing + hysteresis)
- F3. Reports table with pagination — default 20 records per page
- F4. Filters: single date | date range | date + time | date + time range (time optional)
- F5. PDF export of the currently filtered report — highlighted header containing the
  computer user's full name and the selected date range
- F6. Autostart at login (macOS)
- F7. System tray (menu bar) presence with live speed readout

## Out of scope for v1
- Active speed tests (Ookla/Cloudflare) — planned v1.1: scheduled capacity tests
  materially strengthen the ISP-dispute (Pro) story
- Per-app traffic breakdown
- Linux/Windows packaging (code must remain compatible, packaging deferred)
- Cloud sync / accounts

## Tech stack (decided — do not change without discussion)
- Python 3.11+
- PySide6 (LGPL) — NOT PyQt
- psutil — network counters (cross-platform)
- sqlite3 (stdlib) — storage
- reportlab — PDF generation
- pyinstaller — macOS packaging
- pytest — tests

## Key documents
- `docs/architecture-context.md` — components, data flow, DB schema, algorithms
- `docs/code-standards.md` — style, structure, testing rules
- `docs/ui-context.md` — screens, widgets, UX rules
- `docs/ai-work-flow-rules.md` — how Claude Code must work in this repo
- `docs/progress-tracker.md` — ticket status board
- `tickets/` — one file per task, Jira-style
