# NST-305 — CollectorService QThread + graceful shutdown

- **Epic:** EPIC-03 Network Collector
- **Type:** Feature
- **Priority:** P1
- **Estimate:** M
- **Status:** TODO
- **Depends on:** NST-303, NST-304

## Description
`collector/service.py`: the QThread that wires Sampler -> Smoother -> Segmenter ->
Repository, owns its own DB connection, and exposes Qt signals to the UI.

## Acceptance criteria
- [ ] `CollectorService(QThread)` signals: `speed_sampled(float, float)`,
      `segment_closed()`, `session_changed(bool, int)`
- [ ] 1s loop driven by monotonic clock; per-tick try/except keeps loop alive; errors logged
- [ ] Creates its own sqlite connection inside run() (never shares the UI one)
- [ ] `stop()`: sets flag -> loop exits -> segmenter.flush() -> end_session(reason='quit')
      -> connection closed; `wait(3000)` honored by caller
- [ ] No UI imports in this module

## Test plan
pytest-qt: start service with fake source, qtbot.waitSignal(speed_sampled);
stop() persists open segment and session end_reason='quit'; thread joins < 3s.

## Implementation notes (fill after DONE)
