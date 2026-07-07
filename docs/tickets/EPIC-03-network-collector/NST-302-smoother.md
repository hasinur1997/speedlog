# NST-302 — Smoother: moving average

- **Epic:** EPIC-03 Network Collector
- **Type:** Feature
- **Priority:** P1
- **Estimate:** S
- **Status:** DONE
- **Depends on:** NST-301

## Description
`collector/smoother.py`: simple moving average over SMOOTH_WINDOW samples for both
directions, feeding the segmenter and the tray display.

## Acceptance criteria
- [x] `Smoother(window)` with `push(sample) -> SmoothedSample`
- [x] Warm-up: averages over however many samples exist (1..window)
- [x] `reset()` clears state (called on session end / resync)
- [x] O(1) per push (running sum + deque)

## Test plan
Known sequences produce exact expected averages; warm-up behavior; reset.

## Implementation notes (fill after DONE)
- Files: `app/collector/smoother.py` (implementation), `tests/test_smoother.py` (8 tests).
- `Smoother(window=config.SMOOTH_WINDOW)` holds `deque(maxlen=window)` + running
  dl/ul sums; oldest sample's contribution is subtracted before append, so each
  push is O(1). `window < 1` raises `ValueError`.
- Input type is `Sample` from `app/collector/sampler.py`; output is a new
  `SmoothedSample` dataclass (same shape: `dl_bps`, `ul_bps`) so the segmenter
  (NST-303) can distinguish smoothed values from raw ticks in signatures.
- Warm-up divides by the current sample count (1..window), no zero-padding.
- `reset()` clears the deque and zeroes both sums; a drift test over 100 pushes
  asserts the running sums match a recomputed average.
- For NST-303/NST-305: call `smoother.reset()` on session end and whenever the
  sampler discards a tick (returns `None`) due to gap/resync.
