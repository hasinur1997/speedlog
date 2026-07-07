"""Shared value formatting used by the tray, reports table and PDF export (NST-402)."""

from __future__ import annotations

# SI units per docs/architecture-context.md: 1 MB = 1,000,000 bytes.
_BPS_PER_KB = 1_000
_BPS_PER_MB = 1_000_000


def format_speed(bps: float) -> str:
    """Format bytes/sec as ``X.XX MB/s`` (``X.XX KB/s`` below 1 MB/s), 2 decimals."""
    if bps < _BPS_PER_MB:
        return f"{bps / _BPS_PER_KB:.2f} KB/s"
    return f"{bps / _BPS_PER_MB:.2f} MB/s"
