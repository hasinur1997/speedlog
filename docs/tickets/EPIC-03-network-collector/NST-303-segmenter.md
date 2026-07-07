# NST-303 — Segmenter: bucketing + hysteresis state machine

- **Epic:** EPIC-03 Network Collector
- **Type:** Feature
- **Priority:** P1
- **Estimate:** L
- **Status:** DONE
- **Depends on:** NST-302

## Description
`collector/segmenter.py`: THE core algorithm. Groups consecutive smoothed samples into
same-speed segments per architecture-context.md ("Segmenter algorithm").

## Acceptance criteria
- [x] `Segmenter(params, on_segment_closed: Callable[[SpeedRecord], None])`
- [x] Band: within tolerance = max(BAND_TOLERANCE_PCT * segment mean,
      BAND_TOLERANCE_FLOOR_BPS) checked independently for download AND upload
- [x] Split only after HYSTERESIS_TICKS consecutive out-of-band samples; the new
      segment's start is backdated to the first out-of-band tick
- [x] Running means updated incrementally (no sample list kept)
- [x] `flush(now, session_id)` closes the open segment (used on disconnect/quit)
- [x] Segments shorter than MIN_SEGMENT_SECS at flush time are still persisted
      (merging is a possible v1.1 refinement — note in code)
- [x] Emitted SpeedRecord carries segment mean dl/ul, start_ts, end_ts, session_id

## Test plan (most important test file in the repo)
Synthetic streams asserting EXACT boundaries:
- steady 5 MB/s for 60s -> 1 segment
- step 5 -> 10 MB/s -> 2 segments, split backdated correctly
- 2-tick spike then return -> NO split (hysteresis absorbs it)
- oscillation just inside band edges -> 1 segment
- upload-only change splits even when download steady
- flush mid-segment persists partial segment

## Implementation notes (fill after DONE)
- Files: `app/collector/segmenter.py` (new implementation), `tests/test_segmenter.py` (11 tests).
- API: `SegmenterParams` frozen dataclass (defaults from `config`);
  `Segmenter.push(now, sample: SmoothedSample, session_id)` per tick;
  `Segmenter.flush(now, session_id)` closes + resets (no-op if no open segment).
  `on_segment_closed` receives the `SpeedRecord`; DB persistence is NST-305's job.
- Backdating: the actual timestamp of the first out-of-band tick is tracked
  (`oob_start_ts`) rather than computing `now - HYSTERESIS_TICKS` as in the
  architecture pseudocode — exact per this ticket's wording and robust to
  irregular tick spacing. Old segment ends and new segment starts at that instant.
- The pending out-of-band run is kept as running sums (no list); on split it
  seeds the new segment's mean/count. If a sample returns in-band before the
  threshold, the pending run is discarded (absorbed spikes do not pollute the
  segment mean, per the architecture pseudocode).
- Short segments at flush are persisted as-is; merging into a neighbor is noted
  in the `flush` docstring as a v1.1 refinement.

## Decisions
- `push` also takes `session_id` (stamped on the segment at open) since records
  emitted on mid-stream splits need it, not just at flush; `flush(now, session_id)`
  keeps the ticket's signature and overrides the stamp for the final record.
