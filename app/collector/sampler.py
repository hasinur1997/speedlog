"""Per-second network byte-counter sampling (NST-301).

Pure delta/elapsed math separated from timing: :class:`Sampler` is synchronous
and deterministic; the QThread loop that drives it comes in NST-305. Counter
reads are abstracted behind :class:`SamplerSource` so tests use a fake instead
of psutil.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Protocol

import psutil

from app import config

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class Sample:
    """One tick's throughput in bytes/sec (download, upload)."""

    dl_bps: float
    ul_bps: float


class SamplerSource(Protocol):
    """Provider of cumulative OS network byte counters."""

    def read_counters(self) -> tuple[int, int]:
        """Return cumulative (total bytes_recv, total bytes_sent)."""
        ...


class PsutilSource:
    """Sums psutil counters over active, non-virtual interfaces.

    Interfaces whose ``isup`` flag is false are skipped, as are loopback and
    macOS virtual interfaces (``lo*``, ``awdl*``, ``utun*``) — unless the
    excluded ones are the only active interfaces, in which case they are the
    only route and are counted.
    """

    def read_counters(self) -> tuple[int, int]:
        counters = psutil.net_io_counters(pernic=True)
        stats = psutil.net_if_stats()
        active = {name: nic for name, nic in counters.items() if name in stats and stats[name].isup}
        preferred = {
            name: nic
            for name, nic in active.items()
            if not name.startswith(config.EXCLUDED_INTERFACE_PREFIXES)
        }
        selected = preferred or active
        bytes_recv = sum(nic.bytes_recv for nic in selected.values())
        bytes_sent = sum(nic.bytes_sent for nic in selected.values())
        return bytes_recv, bytes_sent


class Sampler:
    """Turns cumulative counter reads into per-tick bytes/sec deltas.

    ``tick(now)`` returns ``None`` when no throughput can be derived (first
    tick, non-positive or sleep/wake-sized elapsed); in every case the
    baseline is resynced to the current counters so the next tick is clean.
    """

    def __init__(
        self,
        source: SamplerSource,
        interval: float = config.SAMPLE_INTERVAL,
        gap_factor: float = config.SAMPLE_GAP_FACTOR,
    ) -> None:
        self._source = source
        self._max_elapsed = interval * gap_factor
        self._last_ts: float | None = None
        self._last_recv: int = 0
        self._last_sent: int = 0

    def tick(self, now: float) -> Sample | None:
        """Read counters and return this tick's speeds, or ``None`` to discard."""
        recv, sent = self._source.read_counters()
        last_ts = self._last_ts
        last_recv, last_sent = self._last_recv, self._last_sent
        self._last_ts, self._last_recv, self._last_sent = now, recv, sent

        if last_ts is None:
            return None  # first tick: baseline only

        elapsed = now - last_ts
        if elapsed <= 0 or elapsed > self._max_elapsed:
            logger.debug("Discarding tick: elapsed %.3fs out of range", elapsed)
            return None

        dl_delta = recv - last_recv
        ul_delta = sent - last_sent
        if dl_delta < 0 or ul_delta < 0:
            # Counter reset/rollover (or an interface vanished): no valid delta
            # this tick; baseline is already resynced to the new counters.
            logger.debug(
                "Counter went backwards (dl_delta=%d, ul_delta=%d); emitting 0",
                dl_delta,
                ul_delta,
            )
            return Sample(dl_bps=0.0, ul_bps=0.0)
        return Sample(dl_bps=dl_delta / elapsed, ul_bps=ul_delta / elapsed)
