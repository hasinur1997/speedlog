"""Moving average over N samples (NST-302).

Simple moving average over the last ``SMOOTH_WINDOW`` samples for both
directions, feeding the segmenter and the tray display. During warm-up the
average covers however many samples have arrived (1..window). O(1) per push
via a bounded deque plus running sums.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass

from app import config
from app.collector.sampler import Sample


@dataclass(slots=True)
class SmoothedSample:
    """Moving-average throughput in bytes/sec (download, upload)."""

    dl_bps: float
    ul_bps: float


class Smoother:
    """Simple moving average of :class:`Sample` values over a fixed window."""

    def __init__(self, window: int = config.SMOOTH_WINDOW) -> None:
        if window < 1:
            raise ValueError(f"window must be >= 1, got {window}")
        self._samples: deque[Sample] = deque(maxlen=window)
        self._dl_sum: float = 0.0
        self._ul_sum: float = 0.0

    def push(self, sample: Sample) -> SmoothedSample:
        """Add one sample and return the average over the current window."""
        if len(self._samples) == self._samples.maxlen:
            evicted = self._samples[0]
            self._dl_sum -= evicted.dl_bps
            self._ul_sum -= evicted.ul_bps
        self._samples.append(sample)
        self._dl_sum += sample.dl_bps
        self._ul_sum += sample.ul_bps
        n = len(self._samples)
        return SmoothedSample(dl_bps=self._dl_sum / n, ul_bps=self._ul_sum / n)

    def reset(self) -> None:
        """Clear all state (called on session end / resync)."""
        self._samples.clear()
        self._dl_sum = 0.0
        self._ul_sum = 0.0
