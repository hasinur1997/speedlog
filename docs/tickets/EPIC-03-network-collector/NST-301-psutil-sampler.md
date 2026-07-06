# NST-301 — Sampler: psutil byte-counter loop (1s)

- **Epic:** EPIC-03 Network Collector
- **Type:** Feature
- **Priority:** P1
- **Estimate:** M
- **Status:** TODO
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
