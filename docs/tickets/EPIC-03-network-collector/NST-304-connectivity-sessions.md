# NST-304 — Connectivity watcher & session lifecycle

- **Epic:** EPIC-03 Network Collector
- **Type:** Feature
- **Priority:** P1
- **Estimate:** M
- **Status:** TODO
- **Depends on:** NST-301, NST-202

## Description
`collector/connectivity.py`: detect online/offline transitions; open/close session rows.

## Acceptance criteria
- [ ] `ConnectivityWatcher.check() -> bool` — online iff at least one non-loopback,
      non-virtual interface is up (psutil.net_if_stats)
- [ ] Debounce: state change confirmed after 3 consecutive identical checks
- [ ] On offline->online: repository.start_session(now); emit session_started
- [ ] On online->offline: segmenter.flush(); repository.end_session(reason='disconnect');
      emit session_ended; smoother.reset()
- [ ] App start while online opens a session immediately
- [ ] Startup calls close_dangling_sessions (crash recovery from NST-202)

## Test plan
Fake if-stats source: flapping is debounced; transitions call repository in order;
dangling recovery invoked once at start.

## Implementation notes (fill after DONE)
