"""Tests for app.collector.sampler (NST-301)."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import patch

from app.collector.sampler import PsutilSource, Sample, Sampler


class FakeSource:
    """SamplerSource returning pre-set counter values."""

    def __init__(self, recv: int = 0, sent: int = 0) -> None:
        self.recv = recv
        self.sent = sent

    def set(self, recv: int, sent: int) -> None:
        self.recv = recv
        self.sent = sent

    def read_counters(self) -> tuple[int, int]:
        return self.recv, self.sent


def test_first_tick_emits_nothing() -> None:
    sampler = Sampler(FakeSource(recv=1_000, sent=500))

    assert sampler.tick(100.0) is None


def test_steady_stream_math_exact() -> None:
    source = FakeSource(recv=0, sent=0)
    sampler = Sampler(source)
    sampler.tick(100.0)

    source.set(5_000_000, 1_200_000)
    assert sampler.tick(101.0) == Sample(dl_bps=5_000_000.0, ul_bps=1_200_000.0)

    source.set(7_500_000, 1_800_000)
    assert sampler.tick(102.0) == Sample(dl_bps=2_500_000.0, ul_bps=600_000.0)


def test_fractional_elapsed_divides_delta() -> None:
    source = FakeSource(recv=0, sent=0)
    sampler = Sampler(source)
    sampler.tick(100.0)

    source.set(1_000_000, 500_000)
    assert sampler.tick(102.0) == Sample(dl_bps=500_000.0, ul_bps=250_000.0)


def test_negative_delta_emits_zero_and_resyncs() -> None:
    source = FakeSource(recv=9_000_000, sent=4_000_000)
    sampler = Sampler(source)
    sampler.tick(100.0)

    source.set(1_000, 500)  # counter reset/rollover
    assert sampler.tick(101.0) == Sample(dl_bps=0.0, ul_bps=0.0)

    source.set(1_001_000, 200_500)  # next tick is measured from the new baseline
    assert sampler.tick(102.0) == Sample(dl_bps=1_000_000.0, ul_bps=200_000.0)


def test_negative_delta_on_one_direction_zeroes_the_tick() -> None:
    source = FakeSource(recv=1_000, sent=4_000_000)
    sampler = Sampler(source)
    sampler.tick(100.0)

    source.set(2_000, 500)  # upload counter went backwards, download grew
    assert sampler.tick(101.0) == Sample(dl_bps=0.0, ul_bps=0.0)


def test_sleep_wake_gap_discards_tick_and_resyncs() -> None:
    source = FakeSource(recv=0, sent=0)
    sampler = Sampler(source, interval=1.0, gap_factor=3.0)
    sampler.tick(100.0)

    source.set(500_000_000, 100_000_000)  # machine slept; huge elapsed
    assert sampler.tick(100.0 + 3600.0) is None

    source.set(501_000_000, 100_200_000)  # normal tick after resync
    assert sampler.tick(100.0 + 3601.0) == Sample(dl_bps=1_000_000.0, ul_bps=200_000.0)


def test_elapsed_at_gap_threshold_is_kept() -> None:
    source = FakeSource(recv=0, sent=0)
    sampler = Sampler(source, interval=1.0, gap_factor=3.0)
    sampler.tick(100.0)

    source.set(3_000_000, 300_000)
    assert sampler.tick(103.0) == Sample(dl_bps=1_000_000.0, ul_bps=100_000.0)


def test_non_positive_elapsed_discards_tick() -> None:
    source = FakeSource(recv=0, sent=0)
    sampler = Sampler(source)
    sampler.tick(100.0)

    source.set(1_000_000, 200_000)
    assert sampler.tick(100.0) is None

    source.set(2_000_000, 400_000)
    assert sampler.tick(101.0) == Sample(dl_bps=1_000_000.0, ul_bps=200_000.0)


def test_interface_set_change_growing_totals_still_measures() -> None:
    # An interface appearing between ticks inflates the summed counters; the
    # sampler has no per-interface view, so the delta is simply measured.
    source = FakeSource(recv=1_000_000, sent=200_000)
    sampler = Sampler(source)
    sampler.tick(100.0)

    source.set(11_000_000, 1_200_000)  # new interface added its history to the sum
    assert sampler.tick(101.0) == Sample(dl_bps=10_000_000.0, ul_bps=1_000_000.0)

    source.set(1_000, 200)  # interface with most traffic disappeared: sum dropped
    assert sampler.tick(102.0) == Sample(dl_bps=0.0, ul_bps=0.0)


def _nic(recv: int, sent: int) -> SimpleNamespace:
    return SimpleNamespace(bytes_recv=recv, bytes_sent=sent)


def _stat(isup: bool) -> SimpleNamespace:
    return SimpleNamespace(isup=isup)


def test_psutil_source_sums_active_non_excluded_interfaces() -> None:
    counters = {
        "en0": _nic(1_000, 100),
        "en1": _nic(2_000, 200),
        "en2": _nic(50_000, 5_000),  # down: excluded
        "lo0": _nic(9_000, 900),  # loopback: excluded
        "awdl0": _nic(70, 7),  # excluded prefix
        "utun3": _nic(80, 8),  # excluded prefix
    }
    stats = {name: _stat(name != "en2") for name in counters}

    with (
        patch("app.collector.sampler.psutil.net_io_counters", return_value=counters),
        patch("app.collector.sampler.psutil.net_if_stats", return_value=stats),
    ):
        assert PsutilSource().read_counters() == (3_000, 300)


def test_psutil_source_falls_back_to_excluded_when_only_active_route() -> None:
    counters = {
        "en0": _nic(1_000, 100),  # down
        "utun2": _nic(500, 50),
        "lo0": _nic(300, 30),
    }
    stats = {"en0": _stat(False), "utun2": _stat(True), "lo0": _stat(True)}

    with (
        patch("app.collector.sampler.psutil.net_io_counters", return_value=counters),
        patch("app.collector.sampler.psutil.net_if_stats", return_value=stats),
    ):
        assert PsutilSource().read_counters() == (800, 80)


def test_psutil_source_skips_interfaces_missing_from_stats() -> None:
    counters = {"en0": _nic(1_000, 100), "ghost0": _nic(9_999, 999)}
    stats = {"en0": _stat(True)}  # ghost0 has counters but no stats entry

    with (
        patch("app.collector.sampler.psutil.net_io_counters", return_value=counters),
        patch("app.collector.sampler.psutil.net_if_stats", return_value=stats),
    ):
        assert PsutilSource().read_counters() == (1_000, 100)
