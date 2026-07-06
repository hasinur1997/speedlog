# NST-303 — Segmenter: bucketing + hysteresis state machine

- **Epic:** EPIC-03 Network Collector
- **Type:** Feature
- **Priority:** P1
- **Estimate:** L
- **Status:** TODO
- **Depends on:** NST-302

## Description
`collector/segmenter.py`: THE core algorithm. Groups consecutive smoothed samples into
same-speed segments per architecture-context.md ("Segmenter algorithm").

## Acceptance criteria
- [ ] `Segmenter(params, on_segment_closed: Callable[[SpeedRecord], None])`
- [ ] Band: within tolerance = max(BAND_TOLERANCE_PCT * segment mean,
      BAND_TOLERANCE_FLOOR_BPS) checked independently for download AND upload
- [ ] Split only after HYSTERESIS_TICKS consecutive out-of-band samples; the new
      segment's start is backdated to the first out-of-band tick
- [ ] Running means updated incrementally (no sample list kept)
- [ ] `flush(now, session_id)` closes the open segment (used on disconnect/quit)
- [ ] Segments shorter than MIN_SEGMENT_SECS at flush time are still persisted
      (merging is a possible v1.1 refinement — note in code)
- [ ] Emitted SpeedRecord carries segment mean dl/ul, start_ts, end_ts, session_id

## Test plan (most important test file in the repo)
Synthetic streams asserting EXACT boundaries:
- steady 5 MB/s for 60s -> 1 segment
- step 5 -> 10 MB/s -> 2 segments, split backdated correctly
- 2-tick spike then return -> NO split (hysteresis absorbs it)
- oscillation just inside band edges -> 1 segment
- upload-only change splits even when download steady
- flush mid-segment persists partial segment

## Implementation notes (fill after DONE)
