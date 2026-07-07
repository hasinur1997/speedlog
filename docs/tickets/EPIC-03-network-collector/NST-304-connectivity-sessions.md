# NST-304 — Connectivity watcher & session lifecycle

- **Epic:** EPIC-03 Network Collector
- **Type:** Feature
- **Priority:** P1
- **Estimate:** M
- **Status:** DONE
- **Depends on:** NST-301, NST-202

## Description
`collector/connectivity.py`: detect online/offline transitions; open/close session rows.

## Acceptance criteria
- [x] `ConnectivityWatcher.check() -> bool` — online iff at least one non-loopback,
      non-virtual interface is up (psutil.net_if_stats)
- [x] Debounce: state change confirmed after 3 consecutive identical checks
- [x] On offline->online: repository.start_session(now); emit session_started
- [x] On online->offline: segmenter.flush(); repository.end_session(reason='disconnect');
      emit session_ended; smoother.reset()
- [x] App start while online opens a session immediately
- [x] Startup calls close_dangling_sessions (crash recovery from NST-202)

## Test plan
Fake if-stats source: flapping is debounced; transitions call repository in order;
dangling recovery invoked once at start.

## Implementation notes (fill after DONE)
- Files: `app/collector/connectivity.py` (implementation), `app/config.py`
  (new `CONNECTIVITY_DEBOUNCE_TICKS = 3`), `tests/test_connectivity.py` (12 tests).
- `IfStatsSource` protocol + `PsutilIfStatsSource` mirror NST-301's `SamplerSource`
  pattern so tests inject a fake; non-loopback/non-virtual filtering reuses
  `config.EXCLUDED_INTERFACE_PREFIXES`.
- Session transitions are reported via plain callbacks `on_session_started` /
  `on_session_ended((session_id, ts))`, matching `Segmenter.on_segment_closed` —
  the collector modules stay Qt-free; NST-305's `CollectorService` must wire these
  callbacks to Qt signals and drive `start(now)` once, then `tick(now)` each second.
- `watcher.session_id` exposes the open session id (`None` while offline) for the
  service to pass into `segmenter.push`.
- Initial state at `start()` is applied without debounce (criterion: app start while
  online opens a session immediately); debounce applies only to subsequent `tick()`s.
- Transition timestamps use the confirming tick's `now` (not backdated by the
  debounce window), per the criterion `start_session(now)`.
