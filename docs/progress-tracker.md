# Progress Tracker — Speedlog

Statuses: `TODO` → `IN PROGRESS` → `DONE` (or `BLOCKED` with reason).
Update this file at the end of EVERY ticket. Work top-to-bottom unless dependencies say otherwise.

## Milestone 1 — Foundation
| ID | Title | Status | Depends on | Done date | Notes |
|---|---|---|---|---|---|
| NST-101 | Project scaffold, venv, dependencies | DONE | — | 2026-07-06 | Package tree + stubs, pinned deps (PySide6 6.11.1), runnable main.py, smoke test; lint/format/tests green |
| NST-102 | Config module & constants | DONE | NST-101 | 2026-07-07 | All tunables + APP_NAME/ACCENT_COLOR in config.py; platform-branched data_dir()/db_path()/log_dir(); 15 tests |
| NST-103 | Logging setup | TODO | NST-101 | | |
| NST-201 | SQLite schema & migrations | TODO | NST-102 | | |
| NST-202 | Models & repository (writes) | TODO | NST-201 | | |
| NST-203 | Repository read/pagination/filter queries | TODO | NST-202 | | |

## Milestone 2 — Collector (tracking engine)
| ID | Title | Status | Depends on | Done date | Notes |
|---|---|---|---|---|---|
| NST-301 | Sampler: psutil 1s byte-counter loop | TODO | NST-102, NST-103 | | |
| NST-302 | Smoother: moving average | TODO | NST-301 | | |
| NST-303 | Segmenter: bucketing + hysteresis | TODO | NST-302 | | |
| NST-304 | Connectivity watcher & sessions | TODO | NST-301, NST-202 | | |
| NST-305 | CollectorService thread + graceful shutdown | TODO | NST-303, NST-304 | | |

## Milestone 3 — App shell & live view
| ID | Title | Status | Depends on | Done date | Notes |
|---|---|---|---|---|---|
| NST-401 | App bootstrap & main window shell | TODO | NST-102 | | |
| NST-402 | System tray icon + live speed text | TODO | NST-401, NST-305 | | |
| NST-403 | Tray menu (open, quit w/ confirm) | TODO | NST-402 | | |
| NST-404 | Quit behavior: stop tracking, flush segment | TODO | NST-403, NST-305 | | |
| NST-501 | Live tab: current speeds + session info | TODO | NST-401, NST-305 | | |
| NST-502 | Live sparkline chart (nice-to-have) | TODO | NST-501 | | |

## Milestone 4 — Reports
| ID | Title | Status | Depends on | Done date | Notes |
|---|---|---|---|---|---|
| NST-601 | Reports table model + view | TODO | NST-203, NST-401 | | |
| NST-602 | Pagination (20/page) | TODO | NST-601 | | |
| NST-603 | Formatting: time ranges, units, empty state | TODO | NST-601 | | |
| NST-701 | Filter panel UI (4 modes) | TODO | NST-601 | | |
| NST-702 | Filter → query builder | TODO | NST-701, NST-203 | | |
| NST-703 | Filter validation, reset, edge cases | TODO | NST-702 | | |

## Milestone 5 — Export & platform
| ID | Title | Status | Depends on | Done date | Notes |
|---|---|---|---|---|---|
| NST-801 | PDF generator (header, table, footer) | TODO | NST-203 | | |
| NST-802 | Export flow in UI (dialog, busy state) | TODO | NST-801, NST-702 | | |
| NST-901 | Autostart at login (macOS LaunchAgent) | TODO | NST-401 | | |
| NST-902 | PyInstaller macOS .app packaging | TODO | all M1–M4 | | |
| NST-903 | Code signing & notarization guide | TODO | NST-902 | | |
| NST-905 | Feature gate module (Free vs Pro) | TODO | NST-802 | | |
| NST-904 | Free-tier 7-day retention cleanup | TODO | NST-202, NST-905 | | |

## Decisions log
| Date | Decision | Ticket |
|---|---|---|
| 2026-07-06 | PySide6 (not PyQt) for LGPL licensing | — |
| 2026-07-06 | Passive monitoring only in v1; no active speed tests | — |
| 2026-07-06 | Tracking stops on user quit; autostart at login | — |
| 2026-07-06 | Product name: Speedlog (pending trademark/domain check); bundle id com.speedlog.app | — |
| 2026-07-06 | Free/Pro split: Free = live + 7-day history; Pro = unlimited history + PDF export | NST-904/905 |
| 2026-07-06 | Positioning: reliability logger / ISP evidence, not a speed meter | — |
