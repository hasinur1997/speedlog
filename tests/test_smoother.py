"""Tests for app.collector.smoother (NST-302)."""

from __future__ import annotations

import pytest

from app import config
from app.collector.sampler import Sample
from app.collector.smoother import SmoothedSample, Smoother


def test_default_window_comes_from_config() -> None:
    smoother = Smoother()
    for _ in range(config.SMOOTH_WINDOW):
        smoother.push(Sample(dl_bps=0.0, ul_bps=0.0))
    # One more push must evict the oldest zero, not grow the window
    result = smoother.push(Sample(dl_bps=float(config.SMOOTH_WINDOW), ul_bps=0.0))
    assert result.dl_bps == pytest.approx(1.0)


def test_window_below_one_rejected() -> None:
    with pytest.raises(ValueError):
        Smoother(window=0)


def test_warm_up_averages_over_existing_samples() -> None:
    smoother = Smoother(window=5)

    assert smoother.push(Sample(dl_bps=10.0, ul_bps=2.0)) == SmoothedSample(dl_bps=10.0, ul_bps=2.0)
    assert smoother.push(Sample(dl_bps=20.0, ul_bps=4.0)) == SmoothedSample(dl_bps=15.0, ul_bps=3.0)
    assert smoother.push(Sample(dl_bps=30.0, ul_bps=6.0)) == SmoothedSample(dl_bps=20.0, ul_bps=4.0)


def test_full_window_exact_average() -> None:
    smoother = Smoother(window=3)
    smoother.push(Sample(dl_bps=10.0, ul_bps=1.0))
    smoother.push(Sample(dl_bps=20.0, ul_bps=2.0))

    assert smoother.push(Sample(dl_bps=30.0, ul_bps=3.0)) == SmoothedSample(dl_bps=20.0, ul_bps=2.0)


def test_sliding_window_evicts_oldest() -> None:
    smoother = Smoother(window=3)
    for dl, ul in [(10.0, 1.0), (20.0, 2.0), (30.0, 3.0)]:
        smoother.push(Sample(dl_bps=dl, ul_bps=ul))

    # Window now [20, 30, 40] / [2, 3, 4]
    assert smoother.push(Sample(dl_bps=40.0, ul_bps=4.0)) == SmoothedSample(dl_bps=30.0, ul_bps=3.0)
    # Window now [30, 40, 50] / [3, 4, 5]
    assert smoother.push(Sample(dl_bps=50.0, ul_bps=5.0)) == SmoothedSample(dl_bps=40.0, ul_bps=4.0)


def test_directions_averaged_independently() -> None:
    smoother = Smoother(window=2)
    smoother.push(Sample(dl_bps=100.0, ul_bps=0.0))

    assert smoother.push(Sample(dl_bps=0.0, ul_bps=50.0)) == SmoothedSample(
        dl_bps=50.0, ul_bps=25.0
    )


def test_reset_clears_state() -> None:
    smoother = Smoother(window=3)
    smoother.push(Sample(dl_bps=100.0, ul_bps=100.0))
    smoother.push(Sample(dl_bps=200.0, ul_bps=200.0))

    smoother.reset()

    # Behaves exactly like a fresh smoother: first push is its own average
    assert smoother.push(Sample(dl_bps=8.0, ul_bps=4.0)) == SmoothedSample(dl_bps=8.0, ul_bps=4.0)


def test_long_stream_stays_exact() -> None:
    """Running sums must not drift from a recomputed average over many pushes."""
    smoother = Smoother(window=5)
    values = [(i * 1234.5, i * 67.8) for i in range(1, 101)]
    window: list[tuple[float, float]] = []

    for dl, ul in values:
        result = smoother.push(Sample(dl_bps=dl, ul_bps=ul))
        window.append((dl, ul))
        window = window[-5:]
        assert result.dl_bps == pytest.approx(sum(v[0] for v in window) / len(window))
        assert result.ul_bps == pytest.approx(sum(v[1] for v in window) / len(window))
