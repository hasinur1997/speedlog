# NST-302 — Smoother: moving average

- **Epic:** EPIC-03 Network Collector
- **Type:** Feature
- **Priority:** P1
- **Estimate:** S
- **Status:** TODO
- **Depends on:** NST-301

## Description
`collector/smoother.py`: simple moving average over SMOOTH_WINDOW samples for both
directions, feeding the segmenter and the tray display.

## Acceptance criteria
- [ ] `Smoother(window)` with `push(sample) -> SmoothedSample`
- [ ] Warm-up: averages over however many samples exist (1..window)
- [ ] `reset()` clears state (called on session end / resync)
- [ ] O(1) per push (running sum + deque)

## Test plan
Known sequences produce exact expected averages; warm-up behavior; reset.

## Implementation notes (fill after DONE)
