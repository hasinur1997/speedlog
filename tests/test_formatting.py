"""Tests for shared formatting helpers (NST-402/NST-603)."""

from __future__ import annotations

from datetime import UTC, datetime
from zoneinfo import ZoneInfo

import pytest

import app.export.pdf_report as pdf_report_module
import app.formatting as formatting_module
import app.ui.reports.table_model as table_model_module
from app.formatting import format_date, format_speed, format_time_range


def _ts(dt: datetime) -> int:
    return int(dt.astimezone(UTC).timestamp())


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


def test_format_time_range_formats_same_day_values_in_local_time(monkeypatch) -> None:
    monkeypatch.setattr(formatting_module, "_local_zone", lambda: ZoneInfo("UTC"))

    start_ts = int(datetime(2026, 7, 7, 10, 20, tzinfo=UTC).timestamp())

    assert format_date(start_ts) == "2026-07-07"
    assert format_time_range(start_ts, start_ts + 600) == "10:20 AM – 10:30 AM"


def test_format_time_range_marks_midnight_rollover_on_start_date(monkeypatch) -> None:
    local_zone = ZoneInfo("America/New_York")
    monkeypatch.setattr(formatting_module, "_local_zone", lambda: local_zone)

    start_ts = _ts(datetime(2026, 7, 6, 23, 58, tzinfo=local_zone))
    end_ts = _ts(datetime(2026, 7, 7, 0, 4, tzinfo=local_zone))

    assert format_date(start_ts) == "2026-07-06"
    assert format_time_range(start_ts, end_ts) == "11:58 PM – 12:04 AM (+1)"


def test_format_time_range_handles_dst_transition_day(monkeypatch) -> None:
    local_zone = ZoneInfo("America/New_York")
    monkeypatch.setattr(formatting_module, "_local_zone", lambda: local_zone)

    start_ts = _ts(datetime(2026, 3, 8, 1, 55, tzinfo=local_zone))
    end_ts = _ts(datetime(2026, 3, 8, 3, 5, tzinfo=local_zone))

    assert format_date(start_ts) == "2026-03-08"
    assert format_time_range(start_ts, end_ts) == "1:55 AM – 3:05 AM"


def test_reports_table_and_pdf_import_shared_helpers() -> None:
    assert table_model_module.format_date is formatting_module.format_date
    assert table_model_module.format_time_range is formatting_module.format_time_range
    assert table_model_module.format_speed is formatting_module.format_speed
    assert pdf_report_module.format_date is formatting_module.format_date
    assert pdf_report_module.format_time_range is formatting_module.format_time_range
    assert pdf_report_module.format_speed is formatting_module.format_speed
