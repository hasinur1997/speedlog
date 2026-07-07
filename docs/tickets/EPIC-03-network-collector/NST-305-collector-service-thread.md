# NST-305 — CollectorService QThread + graceful shutdown

- **Epic:** EPIC-03 Network Collector
- **Type:** Feature
- **Priority:** P1
- **Estimate:** M
- **Status:** DONE
- **Depends on:** NST-303, NST-304

## Description
`collector/service.py`: the QThread that wires Sampler -> Smoother -> Segmenter ->
Repository, owns its own DB connection, and exposes Qt signals to the UI.

## Acceptance criteria
- [x] `CollectorService(QThread)` signals: `speed_sampled(float, float)`,
      `segment_closed()`, `session_changed(bool, int)`
- [x] 1s loop driven by monotonic clock; per-tick try/except keeps loop alive; errors logged
- [x] Creates its own sqlite connection inside run() (never shares the UI one)
- [x] `stop()`: sets flag -> loop exits -> segmenter.flush() -> end_session(reason='quit')
      -> connection closed; `wait(3000)` honored by caller
- [x] No UI imports in this module

## Test plan
pytest-qt: start service with fake source, qtbot.waitSignal(speed_sampled);
stop() persists open segment and session end_reason='quit'; thread joins < 3s.

## Implementation notes (fill after DONE)
- Files: `app/collector/service.py` (implementation), `tests/test_service.py` (6 tests),
  `app/config.py` (added `COLLECTOR_JOIN_TIMEOUT_MS = 3000`).
- `stop()` is non-blocking: it only sets a `threading.Event`; the flush →
  `end_session(reason='quit')` → `conn.close()` sequence runs inside `run()` on the
  collector thread (the connection belongs to that thread). Callers (NST-404) must do
  `service.stop(); service.wait(config.COLLECTOR_JOIN_TIMEOUT_MS)`.
- `run()` opens its own connection via `db.get_connection` and runs `db.migrate` —
  the collector never shares the UI connection. Migration is idempotent, so bootstrap
  order vs. the UI thread doesn't matter.
- Loop pacing: fixed cadence off `time.monotonic()`, sleeping via `Event.wait(delay)`
  so `stop()` wakes it immediately. If a tick overruns its slot the schedule resyncs
  (no burst catch-up). Wall-clock `int(time.time())` is used for all persisted
  timestamps; monotonic time only paces the loop and feeds `Sampler.tick` elapsed math.
- Per-tick `try/except Exception` + `logger.exception` keeps the loop alive; a failed
  `insert_record` inside `segmenter.push` is caught there too (sample dropped).
- Constructor takes injectable `sampler_source` / `if_stats_source` / `interval` /
  `db_path` for tests; defaults are `PsutilSource` / `PsutilIfStatsSource` /
  `config.SAMPLE_INTERVAL` / `config.db_path()`.
- `session_changed(False, id)` is also emitted on quit-shutdown (after persisting),
  mirroring the disconnect path.

## Decisions
- Added `COLLECTOR_JOIN_TIMEOUT_MS` to `config.py` (no-magic-numbers rule); NST-404
  should use it for the quit-time `wait()`.
