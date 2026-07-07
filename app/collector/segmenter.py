"""Bucketing + hysteresis state machine (NST-303).

Groups consecutive smoothed samples into same-speed segments. A segment stays
open while both directions remain within the tolerance band around the
segment's running mean; only ``HYSTERESIS_TICKS`` consecutive out-of-band
samples split it, and the new segment is backdated to the first out-of-band
tick. Running means are cumulative — no sample list is kept.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from app import config
from app.collector.smoother import SmoothedSample
from app.data.models import SpeedRecord


@dataclass(frozen=True, slots=True)
class SegmenterParams:
    """Tunables for the segmenter, defaulting to the ``config`` constants."""

    band_tolerance_pct: float = config.BAND_TOLERANCE_PCT
    band_tolerance_floor_bps: float = config.BAND_TOLERANCE_FLOOR_BPS
    hysteresis_ticks: int = config.HYSTERESIS_TICKS
    min_segment_secs: int = config.MIN_SEGMENT_SECS


@dataclass(slots=True)
class _OpenSegment:
    """Mutable state of the segment currently being built."""

    session_id: int
    start_ts: int
    dl_mean: float
    ul_mean: float
    n: int = 1
    # Pending out-of-band run: consecutive samples outside the band. Kept as
    # running sums (not a list) so they can seed the next segment on a split;
    # discarded if a sample returns in-band before the hysteresis threshold.
    oob_count: int = 0
    oob_start_ts: int = 0
    oob_dl_sum: float = 0.0
    oob_ul_sum: float = 0.0


class Segmenter:
    """State machine turning smoothed samples into :class:`SpeedRecord` segments.

    ``on_segment_closed`` is invoked with each finished record (the collector
    service persists it via the repository).
    """

    def __init__(
        self,
        params: SegmenterParams | None = None,
        on_segment_closed: Callable[[SpeedRecord], None] = lambda record: None,
    ) -> None:
        self._params = params if params is not None else SegmenterParams()
        self._on_segment_closed = on_segment_closed
        self._segment: _OpenSegment | None = None

    def _band(self, mean_bps: float) -> float:
        return max(
            self._params.band_tolerance_pct * mean_bps, self._params.band_tolerance_floor_bps
        )

    def _in_band(self, segment: _OpenSegment, sample: SmoothedSample) -> bool:
        # Download AND upload checked independently; either breaking splits.
        return abs(sample.dl_bps - segment.dl_mean) <= self._band(segment.dl_mean) and abs(
            sample.ul_bps - segment.ul_mean
        ) <= self._band(segment.ul_mean)

    def push(self, now: int, sample: SmoothedSample, session_id: int) -> None:
        """Feed one smoothed sample taken at ``now`` (UTC epoch seconds)."""
        segment = self._segment
        if segment is None:
            self._segment = _OpenSegment(
                session_id=session_id,
                start_ts=now,
                dl_mean=sample.dl_bps,
                ul_mean=sample.ul_bps,
            )
            return

        if self._in_band(segment, sample):
            # Cumulative running mean; absorbed out-of-band spikes are dropped.
            segment.n += 1
            segment.dl_mean += (sample.dl_bps - segment.dl_mean) / segment.n
            segment.ul_mean += (sample.ul_bps - segment.ul_mean) / segment.n
            segment.oob_count = 0
            segment.oob_dl_sum = 0.0
            segment.oob_ul_sum = 0.0
            return

        if segment.oob_count == 0:
            segment.oob_start_ts = now
        segment.oob_count += 1
        segment.oob_dl_sum += sample.dl_bps
        segment.oob_ul_sum += sample.ul_bps
        if segment.oob_count >= self._params.hysteresis_ticks:
            split_ts = segment.oob_start_ts
            self._emit(segment, end_ts=split_ts)
            # New segment backdated to the first out-of-band tick, seeded with
            # the mean of the pending out-of-band run.
            self._segment = _OpenSegment(
                session_id=session_id,
                start_ts=split_ts,
                dl_mean=segment.oob_dl_sum / segment.oob_count,
                ul_mean=segment.oob_ul_sum / segment.oob_count,
                n=segment.oob_count,
            )

    def flush(self, now: int, session_id: int) -> None:
        """Close the open segment at ``now`` (disconnect / app quit) and reset.

        Segments shorter than MIN_SEGMENT_SECS are still persisted here —
        merging them into a neighbor is a possible v1.1 refinement.
        """
        segment = self._segment
        self._segment = None
        if segment is not None:
            segment.session_id = session_id
            self._emit(segment, end_ts=now)

    def _emit(self, segment: _OpenSegment, end_ts: int) -> None:
        self._on_segment_closed(
            SpeedRecord(
                session_id=segment.session_id,
                start_ts=segment.start_ts,
                end_ts=end_ts,
                download_bps=segment.dl_mean,
                upload_bps=segment.ul_mean,
            )
        )
