"""Tests for app.formatting (NST-402)."""

from __future__ import annotations

import pytest

from app.formatting import format_speed


@pytest.mark.parametrize(
    ("bps", "expected"),
    [
        (0, "0.00 KB/s"),
        (999_000, "999.00 KB/s"),
        (999_999, "1000.00 KB/s"),
        (1_000_000, "1.00 MB/s"),
        (5_020_000, "5.02 MB/s"),
        (125_000_000, "125.00 MB/s"),
    ],
)
def test_format_speed(bps: float, expected: str) -> None:
    assert format_speed(bps) == expected
