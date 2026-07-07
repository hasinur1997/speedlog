# NST-301 — Sampler: psutil byte-counter loop (1s)

- **Epic:** EPIC-03 Network Collector
- **Type:** Feature
- **Priority:** P1
- **Estimate:** M
- **Status:** DONE
- **Depends on:** NST-102, NST-103

## Description
`collector/sampler.py`: read per-second download/upload bytes-per-second from OS
interface counters. Foundation of the whole product.

## Acceptance criteria
- [ ] `SamplerSource` protocol/interface with `read_counters() -> tuple[int, int]`
      (total bytes_recv, bytes_sent) — allows a FakeSource in tests
- [ ] Default `PsutilSource` sums ACTIVE, non-loopback interfaces
      (`psutil.net_io_counters(pernic=True)` + `net_if_stats().isup`,
      exclude `lo*`, `awdl*`, `utun*` unless they are the only active route)
- [ ] `Sampler.tick(now) -> Sample(dl_bps, ul_bps)` computes deltas / elapsed
- [ ] Counter reset/rollover (delta < 0) handled: emit 0 for that tick, resync baseline
- [ ] Sleep/wake gap (elapsed >> interval) handled: discard tick, resync
- [ ] First tick after start emits nothing (no baseline yet)

## Technical notes
Pure logic separated from timing: the QThread loop comes in NST-305. Keep Sampler
synchronous and deterministic for testability.

## Test plan
FakeSource-driven: steady stream math exact; negative delta; huge elapsed gap;
interface set changes between ticks.

## Implementation notes (fill after DONE)
- **Files:** `app/collector/sampler.py` (implementation), `tests/test_sampler.py`
  (12 tests), `app/config.py` (added `SAMPLE_GAP_FACTOR = 3.0` and
  `EXCLUDED_INTERFACE_PREFIXES = ("lo", "awdl", "utun")`).
- `Sample(dl_bps, ul_bps)` dataclass; `SamplerSource` is a `typing.Protocol`, so
  test fakes need no inheritance.
- `PsutilSource` intersects `net_io_counters(pernic=True)` with `net_if_stats()`:
  only `isup` interfaces count; excluded prefixes are dropped unless nothing else
  is active (then they are the only route and are used as-is). Interfaces present
  in counters but missing from stats are skipped.
- `Sampler.tick(now)` returns `None` on: first tick (baseline only), elapsed <= 0,
  or elapsed > `SAMPLE_INTERVAL * SAMPLE_GAP_FACTOR` (sleep/wake). In all cases the
  baseline resyncs to the just-read counters.
- Negative delta on EITHER direction (rollover / interface removal) emits
  `Sample(0.0, 0.0)` for that tick — the summed-counter view can't attribute a
  partial delta, so the whole tick is zeroed and the baseline resyncs.
- For NST-305: `tick()` takes an explicit `now` (use `time.monotonic()` in the
  thread loop); `Sampler` is not thread-safe by design — construct and drive it
  entirely inside the collector thread.
