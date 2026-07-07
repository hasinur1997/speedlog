# Progress Tracker — Speedlog

Statuses: `TODO` → `IN PROGRESS` → `DONE` (or `BLOCKED` with reason).
Update this file at the end of EVERY ticket. Work top-to-bottom unless dependencies say otherwise.

## Milestone 1 — Foundation
| ID | Title | Status | Depends on | Done date | Notes |
|---|---|---|---|---|---|
| NST-101 | Project scaffold, venv, dependencies | DONE | — | 2026-07-06 | Package tree + stubs, pinned deps (PySide6 6.11.1), runnable main.py, smoke test; lint/format/tests green |
| NST-102 | Config module & constants | DONE | NST-101 | 2026-07-07 | All tunables + APP_NAME/ACCENT_COLOR in config.py; platform-branched data_dir()/db_path()/log_dir(); 15 tests |
| NST-103 | Logging setup | DONE | NST-101 | 2026-07-07 | Root logging config with config-backed rotating app.log (5 MB x 3) + opt-in console (`debug`/`NST_DEBUG=1`); uncaught exceptions logged; 5 unit tests |
| NST-201 | SQLite schema & migrations | DONE | NST-102 | 2026-07-07 | get_connection (WAL/FK/NORMAL PRAGMAs) + versioned atomic migrate() in data/db.py; 7 tests |
| NST-202 | Models & repository (writes) | DONE | NST-201 | 2026-07-07 | Session/SpeedRecord dataclasses + Repository write API (start/end_session, insert_record, close_dangling_sessions); transactional parameterized SQL; 6 tests |
| NST-203 | Repository read/pagination/filter queries | DONE | NST-202 | 2026-07-07 | ReportFilter + count_records/fetch_records (start_ts DESC, LIMIT/OFFSET)/fetch_all_records (chunked iterator); overlap semantics; index use verified via EXPLAIN; 10 tests |

## Milestone 2 — Collector (tracking engine)
| ID | Title | Status | Depends on | Done date | Notes |
|---|---|---|---|---|---|
| NST-301 | Sampler: psutil 1s byte-counter loop | DONE | NST-102, NST-103 | 2026-07-07 | SamplerSource protocol + PsutilSource (active non-virtual NICs, fallback) + pure Sampler.tick with rollover/gap handling; 12 tests |
| NST-302 | Smoother: moving average | DONE | NST-301 | 2026-07-07 | Smoother.push(Sample)->SmoothedSample: SMA over SMOOTH_WINDOW, warm-up 1..window, reset(); O(1) deque+running sums; 8 tests |
| NST-303 | Segmenter: bucketing + hysteresis | DONE | NST-302 | 2026-07-07 | SegmenterParams + Segmenter.push/flush: per-direction band, hysteresis split backdated to first out-of-band tick, incremental means, short segments persisted at flush; 11 tests |
| NST-304 | Connectivity watcher & sessions | DONE | NST-301, NST-202 | 2026-07-07 | IfStatsSource protocol + ConnectivityWatcher: debounced (3 ticks) online/offline, session open/close via repository, flush+reset on disconnect, dangling recovery at start; 12 tests |
| NST-305 | CollectorService thread + graceful shutdown | DONE | NST-303, NST-304 | 2026-07-07 | CollectorService(QThread): own DB conn in run(), monotonic 1s loop w/ per-tick try/except, non-blocking stop() → flush + end_session('quit') on collector thread; COLLECTOR_JOIN_TIMEOUT_MS in config; 6 pytest-qt tests |

## Milestone 3 — App shell & live view
| ID | Title | Status | Depends on | Done date | Notes |
|---|---|---|---|---|---|
| NST-401 | App bootstrap & main window shell | DONE | NST-102 | 2026-07-07 | Real main() (logging→single-instance→migrate→styles/icon→window→exec); MainWindow 900x620 Live/Reports tabs, close hides; QLocalServer single-instance w/ activate + stale-socket recovery; 11 tests |
| NST-402 | System tray icon + live speed text | DONE | NST-401, NST-305 | 2026-07-07 | SpeedTrayIcon (template/mask icon): tooltip `↓ x  ↑ y` throttled to 1/s, `— offline` on session end, trigger/double-click opens window; shared format_speed() in app/formatting.py; collector started + wired in main(); 17 tests |
| NST-403 | Tray menu (open, quit w/ confirm) | DONE | NST-402 | 2026-07-07 | Tray menu adds Open/Quit actions, quit confirmation, and `quit_confirmed -> app.quit` wiring; tray tests expanded |
| NST-404 | Quit behavior: stop tracking, flush segment | DONE | NST-403, NST-305 | 2026-07-07 | `aboutToQuit` now stops + joins the collector, flushes the final segment/session on quit, and startup recovery of dangling sessions is covered by integration tests |
| NST-501 | Live tab: current speeds + session info | DONE | NST-401, NST-305 | 2026-07-07 | Real LiveView widget with connected-since line, hidden-tab speed caching, and collector/tray signal timestamp wiring; 3 pytest-qt tests added |
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
