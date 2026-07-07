"""Tests for the pure report-filter helpers (NST-702/NST-703)."""

from __future__ import annotations

from datetime import UTC, date, datetime, time
from zoneinfo import ZoneInfo

from app.data.models import ReportFilter, ReportFilterMode, ReportFilterUiState
from app.ui.reports.filter_builder import (
    build_report_filter,
    summarize_filter_state,
    summarize_report_filter,
)


def _utc_ts(local_dt: datetime) -> int:
    return int(local_dt.astimezone(UTC).timestamp())


def test_build_report_filter_returns_unbounded_filter_for_reset_state() -> None:
    assert build_report_filter(ReportFilterUiState(), local_zone=ZoneInfo("UTC")) == ReportFilter()


def test_build_report_filter_date_mode_uses_local_day_bounds_in_fixed_timezone() -> None:
    local_zone = ZoneInfo("America/Los_Angeles")
    ui_state = ReportFilterUiState(
        mode=ReportFilterMode.DATE,
        start_date=date(2026, 7, 7),
    )

    report_filter = build_report_filter(ui_state, local_zone=local_zone)

    assert report_filter == ReportFilter(
        range_start_ts=_utc_ts(datetime(2026, 7, 7, 0, 0, 0, tzinfo=local_zone)),
        range_end_ts=_utc_ts(datetime(2026, 7, 7, 23, 59, 59, tzinfo=local_zone)),
    )


def test_build_report_filter_date_range_mode_swaps_reversed_dates() -> None:
    ui_state = ReportFilterUiState(
        mode=ReportFilterMode.DATE_RANGE,
        start_date=date(2026, 7, 10),
        end_date=date(2026, 7, 8),
    )

    report_filter = build_report_filter(ui_state, local_zone=ZoneInfo("UTC"))

    assert report_filter == ReportFilter(
        range_start_ts=_utc_ts(datetime(2026, 7, 8, 0, 0, 0, tzinfo=UTC)),
        range_end_ts=_utc_ts(datetime(2026, 7, 10, 23, 59, 59, tzinfo=UTC)),
    )


def test_build_report_filter_date_time_mode_builds_instant_query() -> None:
    local_zone = ZoneInfo("America/New_York")
    ui_state = ReportFilterUiState(
        mode=ReportFilterMode.DATE_TIME,
        start_date=date(2026, 7, 7),
        start_time=time(9, 15),
    )

    report_filter = build_report_filter(ui_state, local_zone=local_zone)
    instant_ts = _utc_ts(datetime(2026, 7, 7, 9, 15, 0, tzinfo=local_zone))

    assert report_filter == ReportFilter(
        range_start_ts=instant_ts,
        range_end_ts=instant_ts,
    )


def test_build_report_filter_date_time_range_mode_swaps_reversed_times() -> None:
    ui_state = ReportFilterUiState(
        mode=ReportFilterMode.DATE_TIME_RANGE,
        start_date=date(2026, 7, 7),
        start_time=time(17, 45),
        end_time=time(9, 30),
    )

    report_filter = build_report_filter(ui_state, local_zone=ZoneInfo("UTC"))

    assert report_filter == ReportFilter(
        range_start_ts=_utc_ts(datetime(2026, 7, 7, 9, 30, 0, tzinfo=UTC)),
        range_end_ts=_utc_ts(datetime(2026, 7, 7, 17, 45, 0, tzinfo=UTC)),
    )


def test_build_report_filter_date_mode_handles_dst_boundary_day() -> None:
    local_zone = ZoneInfo("America/New_York")
    ui_state = ReportFilterUiState(
        mode=ReportFilterMode.DATE,
        start_date=date(2026, 3, 8),
    )

    report_filter = build_report_filter(ui_state, local_zone=local_zone)

    assert report_filter == ReportFilter(
        range_start_ts=_utc_ts(datetime(2026, 3, 8, 0, 0, 0, tzinfo=local_zone)),
        range_end_ts=_utc_ts(datetime(2026, 3, 8, 23, 59, 59, tzinfo=local_zone)),
    )


def test_summarize_filter_state_returns_all_records_for_reset_state() -> None:
    assert summarize_filter_state(ReportFilterUiState()) == "Showing all records"


def test_summarize_filter_state_formats_reversed_date_range_in_applied_order() -> None:
    summary = summarize_filter_state(
        ReportFilterUiState(
            mode=ReportFilterMode.DATE_RANGE,
            start_date=date(2026, 7, 10),
            end_date=date(2026, 7, 8),
        )
    )

    assert summary == "Filtered: 2026-07-08 – 2026-07-10"


def test_summarize_filter_state_formats_time_range_summary() -> None:
    summary = summarize_filter_state(
        ReportFilterUiState(
            mode=ReportFilterMode.DATE_TIME_RANGE,
            start_date=date(2026, 7, 7),
            start_time=time(17, 45),
            end_time=time(9, 30),
        )
    )

    assert summary == "Filtered: 2026-07-07, 9:30 AM – 5:45 PM"


def test_summarize_report_filter_formats_full_day_bounds_as_single_date() -> None:
    report_filter = ReportFilter(
        range_start_ts=_utc_ts(datetime(2026, 7, 7, 0, 0, 0, tzinfo=UTC)),
        range_end_ts=_utc_ts(datetime(2026, 7, 7, 23, 59, 59, tzinfo=UTC)),
    )

    assert summarize_report_filter(report_filter, local_zone=ZoneInfo("UTC")) == "Filtered: 2026-07-07"
