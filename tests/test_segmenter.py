"""Tests for app.collector.segmenter (NST-303).

Synthetic smoothed-sample streams asserting EXACT segment boundaries. Ticks
are 1 s apart; speeds in bytes/sec (5 MB/s = 5_000_000).
"""

from __future__ import annotations

import pytest

from app import config
from app.collector.segmenter import Segmenter, SegmenterParams
from app.collector.smoother import SmoothedSample
from app.data.models import SpeedRecord

MB = 1_000_000
SESSION = 7


def make_segmenter(records: list[SpeedRecord]) -> Segmenter:
    return Segmenter(on_segment_closed=records.append)


def feed(
    segmenter: Segmenter,
    values: list[tuple[float, float]],
    start: int = 0,
    session_id: int = SESSION,
) -> int:
    """Push one sample per second starting at ``start``; return the next tick's ts."""
    now = start
    for dl, ul in values:
        segmenter.push(now, SmoothedSample(dl_bps=dl, ul_bps=ul), session_id)
        now += 1
    return now


def test_default_params_come_from_config() -> None:
    params = SegmenterParams()
    assert params.band_tolerance_pct == config.BAND_TOLERANCE_PCT
    assert params.band_tolerance_floor_bps == config.BAND_TOLERANCE_FLOOR_BPS
    assert params.hysteresis_ticks == config.HYSTERESIS_TICKS
    assert params.min_segment_secs == config.MIN_SEGMENT_SECS


def test_steady_speed_yields_one_segment() -> None:
    records: list[SpeedRecord] = []
    segmenter = make_segmenter(records)

    now = feed(segmenter, [(5.0 * MB, 1.0 * MB)] * 60)
    assert records == []  # nothing closes while the stream stays in band
    segmenter.flush(now, SESSION)

    assert records == [
        SpeedRecord(
            session_id=SESSION, start_ts=0, end_ts=60, download_bps=5.0 * MB, upload_bps=1.0 * MB
        )
    ]


def test_step_change_splits_with_backdated_boundary() -> None:
    records: list[SpeedRecord] = []
    segmenter = make_segmenter(records)

    # 5 MB/s at t=0..9, then 10 MB/s from t=10. Out-of-band ticks at
    # t=10..14 reach HYSTERESIS_TICKS=5 at t=14 -> split backdated to t=10.
    now = feed(segmenter, [(5.0 * MB, 1.0 * MB)] * 10 + [(10.0 * MB, 1.0 * MB)] * 11)
    segmenter.flush(now, SESSION)

    assert records == [
        SpeedRecord(
            session_id=SESSION, start_ts=0, end_ts=10, download_bps=5.0 * MB, upload_bps=1.0 * MB
        ),
        SpeedRecord(
            session_id=SESSION, start_ts=10, end_ts=21, download_bps=10.0 * MB, upload_bps=1.0 * MB
        ),
    ]


def test_short_spike_absorbed_by_hysteresis() -> None:
    records: list[SpeedRecord] = []
    segmenter = make_segmenter(records)

    # 2-tick spike at t=10,11 (< HYSTERESIS_TICKS) then back in band: no split,
    # and the absorbed spike does not pollute the segment mean.
    values = [(5.0 * MB, 1.0 * MB)] * 10 + [(20.0 * MB, 1.0 * MB)] * 2 + [(5.0 * MB, 1.0 * MB)] * 10
    now = feed(segmenter, values)
    segmenter.flush(now, SESSION)

    assert records == [
        SpeedRecord(
            session_id=SESSION, start_ts=0, end_ts=22, download_bps=5.0 * MB, upload_bps=1.0 * MB
        )
    ]


def test_oscillation_inside_band_stays_one_segment() -> None:
    records: list[SpeedRecord] = []
    segmenter = make_segmenter(records)

    # Alternate +/-0.2 MB/s around 5 MB/s: well inside the 10% band (0.5 MB/s).
    values = [(5.0 * MB + (0.2 * MB if i % 2 else -0.2 * MB), 1.0 * MB) for i in range(40)]
    now = feed(segmenter, [(5.0 * MB, 1.0 * MB)] + values)
    segmenter.flush(now, SESSION)

    assert len(records) == 1
    assert records[0].start_ts == 0
    assert records[0].end_ts == 41
    assert records[0].download_bps == pytest.approx(5.0 * MB, rel=0.01)


def test_upload_only_change_splits() -> None:
    records: list[SpeedRecord] = []
    segmenter = make_segmenter(records)

    # Download steady; upload steps 1 -> 3 MB/s at t=10. Band around the
    # 1 MB/s upload mean is max(0.1 MB, 0.25 MB) = 0.25 MB/s -> out of band.
    now = feed(segmenter, [(5.0 * MB, 1.0 * MB)] * 10 + [(5.0 * MB, 3.0 * MB)] * 11)
    segmenter.flush(now, SESSION)

    assert records == [
        SpeedRecord(
            session_id=SESSION, start_ts=0, end_ts=10, download_bps=5.0 * MB, upload_bps=1.0 * MB
        ),
        SpeedRecord(
            session_id=SESSION, start_ts=10, end_ts=21, download_bps=5.0 * MB, upload_bps=3.0 * MB
        ),
    ]


def test_flush_mid_segment_persists_partial_segment() -> None:
    records: list[SpeedRecord] = []
    segmenter = make_segmenter(records)

    # 2 s segment, shorter than MIN_SEGMENT_SECS: still persisted at flush.
    now = feed(segmenter, [(5.0 * MB, 1.0 * MB)] * 2)
    segmenter.flush(now, SESSION)

    assert now - 0 < config.MIN_SEGMENT_SECS
    assert records == [
        SpeedRecord(
            session_id=SESSION, start_ts=0, end_ts=2, download_bps=5.0 * MB, upload_bps=1.0 * MB
        )
    ]


def test_flush_with_no_open_segment_emits_nothing() -> None:
    records: list[SpeedRecord] = []
    segmenter = make_segmenter(records)

    segmenter.flush(100, SESSION)

    assert records == []


def test_flush_resets_state_for_next_session() -> None:
    records: list[SpeedRecord] = []
    segmenter = make_segmenter(records)

    now = feed(segmenter, [(5.0 * MB, 1.0 * MB)] * 5)
    segmenter.flush(now, SESSION)
    # New session: a fresh segment opens at the new timestamp with new speeds.
    now = feed(segmenter, [(50.0 * MB, 9.0 * MB)] * 5, start=1000, session_id=SESSION + 1)
    segmenter.flush(now, SESSION + 1)

    assert len(records) == 2
    assert records[1] == SpeedRecord(
        session_id=SESSION + 1,
        start_ts=1000,
        end_ts=1005,
        download_bps=50.0 * MB,
        upload_bps=9.0 * MB,
    )


def test_absorbed_spike_resets_hysteresis_counter() -> None:
    records: list[SpeedRecord] = []
    segmenter = make_segmenter(records)

    # 4 out-of-band ticks (one short of the threshold), one in-band tick, then
    # 4 more out-of-band ticks: the counter must have reset, so still no split.
    values = (
        [(5.0 * MB, 1.0 * MB)] * 10
        + [(20.0 * MB, 1.0 * MB)] * 4
        + [(5.0 * MB, 1.0 * MB)]
        + [(20.0 * MB, 1.0 * MB)] * 4
        + [(5.0 * MB, 1.0 * MB)] * 5
    )
    now = feed(segmenter, values)
    segmenter.flush(now, SESSION)

    assert len(records) == 1
    assert records[0].start_ts == 0
    assert records[0].end_ts == now


def test_custom_hysteresis_of_one_splits_immediately() -> None:
    records: list[SpeedRecord] = []
    segmenter = Segmenter(
        params=SegmenterParams(hysteresis_ticks=1), on_segment_closed=records.append
    )

    feed(segmenter, [(5.0 * MB, 1.0 * MB)] * 3 + [(10.0 * MB, 1.0 * MB)])

    assert records == [
        SpeedRecord(
            session_id=SESSION, start_ts=0, end_ts=3, download_bps=5.0 * MB, upload_bps=1.0 * MB
        )
    ]
