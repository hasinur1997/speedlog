"""Pure report-filter helpers for query building and active-filter summaries."""

from __future__ import annotations

from datetime import UTC, date, datetime, time
from typing import TypeVar
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from app.data.models import ReportFilter, ReportFilterMode, ReportFilterUiState

_DAY_START = time(0, 0, 0)
_DAY_END = time(23, 59, 59)
_TIME_SUMMARY_FORMAT = "%I:%M %p"
_FILTERED_PREFIX = "Filtered: "
_UNFILTERED_SUMMARY = "Showing all records"
T = TypeVar("T")


def build_report_filter(
    ui_state: ReportFilterUiState, *, local_zone: ZoneInfo | None = None
) -> ReportFilter:
    """Convert ``ui_state`` into a UTC ``ReportFilter`` using local wall-clock values."""
    if ui_state.mode is None:
        return ReportFilter()

    zone = local_zone if local_zone is not None else _local_zone()

    if ui_state.mode is ReportFilterMode.DATE:
        selected_date = _require_value(ui_state.start_date, "start_date")
        range_start, range_end = _date_bounds(selected_date, selected_date, zone)
        return ReportFilter(range_start_ts=range_start, range_end_ts=range_end)

    if ui_state.mode is ReportFilterMode.DATE_RANGE:
        start_date = _require_value(ui_state.start_date, "start_date")
        end_date = _require_value(ui_state.end_date, "end_date")
        if end_date < start_date:
            start_date, end_date = end_date, start_date
        range_start, range_end = _date_bounds(start_date, end_date, zone)
        return ReportFilter(range_start_ts=range_start, range_end_ts=range_end)

    if ui_state.mode is ReportFilterMode.DATE_TIME:
        selected_date = _require_value(ui_state.start_date, "start_date")
        selected_time = _require_value(ui_state.start_time, "start_time")
        instant_ts = _to_epoch(_local_datetime(selected_date, selected_time, zone))
        return ReportFilter(range_start_ts=instant_ts, range_end_ts=instant_ts)

    if ui_state.mode is ReportFilterMode.DATE_TIME_RANGE:
        selected_date = _require_value(ui_state.start_date, "start_date")
        start_time = _require_value(ui_state.start_time, "start_time")
        end_time = _require_value(ui_state.end_time, "end_time")
        range_start = _local_datetime(selected_date, start_time, zone)
        range_end = _local_datetime(selected_date, end_time, zone)
        if range_end < range_start:
            range_start, range_end = range_end, range_start
        return ReportFilter(
            range_start_ts=_to_epoch(range_start),
            range_end_ts=_to_epoch(range_end),
        )

    raise ValueError(f"Unsupported report filter mode: {ui_state.mode!r}")


def summarize_filter_state(ui_state: ReportFilterUiState) -> str:
    """Return a user-facing summary of the currently applied UI filter state."""
    if ui_state.mode is None:
        return _UNFILTERED_SUMMARY

    if ui_state.mode is ReportFilterMode.DATE:
        selected_date = _require_value(ui_state.start_date, "start_date")
        return _date_summary(selected_date)

    if ui_state.mode is ReportFilterMode.DATE_RANGE:
        start_date = _require_value(ui_state.start_date, "start_date")
        end_date = _require_value(ui_state.end_date, "end_date")
        if end_date < start_date:
            start_date, end_date = end_date, start_date
        if start_date == end_date:
            return _date_summary(start_date)
        return f"{_FILTERED_PREFIX}{start_date.isoformat()} – {end_date.isoformat()}"

    if ui_state.mode is ReportFilterMode.DATE_TIME:
        selected_date = _require_value(ui_state.start_date, "start_date")
        selected_time = _require_value(ui_state.start_time, "start_time")
        return _instant_summary(selected_date, selected_time)

    if ui_state.mode is ReportFilterMode.DATE_TIME_RANGE:
        selected_date = _require_value(ui_state.start_date, "start_date")
        start_time = _require_value(ui_state.start_time, "start_time")
        end_time = _require_value(ui_state.end_time, "end_time")
        if end_time < start_time:
            start_time, end_time = end_time, start_time
        if start_time == end_time:
            return _instant_summary(selected_date, start_time)
        return (
            f"{_FILTERED_PREFIX}{selected_date.isoformat()},"
            f" {_format_summary_time(start_time)} – {_format_summary_time(end_time)}"
        )

    raise ValueError(f"Unsupported report filter mode: {ui_state.mode!r}")


def summarize_report_filter(
    report_filter: ReportFilter, *, local_zone: ZoneInfo | None = None
) -> str:
    """Return a fallback summary for already-built UTC query bounds."""
    if report_filter.range_start_ts is None and report_filter.range_end_ts is None:
        return _UNFILTERED_SUMMARY

    zone = local_zone if local_zone is not None else _local_zone()

    if report_filter.range_start_ts is not None and report_filter.range_end_ts is not None:
        start_dt = _epoch_to_local(report_filter.range_start_ts, zone)
        end_dt = _epoch_to_local(report_filter.range_end_ts, zone)
        start_time = start_dt.timetz().replace(tzinfo=None)
        end_time = end_dt.timetz().replace(tzinfo=None)

        if start_dt == end_dt:
            return _instant_summary(start_dt.date(), start_time)

        if start_dt.date() == end_dt.date():
            if start_time == _DAY_START and end_time == _DAY_END:
                return _date_summary(start_dt.date())
            return (
                f"{_FILTERED_PREFIX}{start_dt.date().isoformat()},"
                f" {_format_summary_time(start_time)} – {_format_summary_time(end_time)}"
            )

        return (
            f"{_FILTERED_PREFIX}{start_dt.date().isoformat()} {_format_summary_time(start_time)}"
            f" – {end_dt.date().isoformat()} {_format_summary_time(end_time)}"
        )

    if report_filter.range_start_ts is not None:
        start_dt = _epoch_to_local(report_filter.range_start_ts, zone)
        return (
            f"{_FILTERED_PREFIX}from {start_dt.date().isoformat()}"
            f" {_format_summary_time(start_dt.timetz().replace(tzinfo=None))}"
        )

    end_dt = _epoch_to_local(_require_value(report_filter.range_end_ts, "range_end_ts"), zone)
    return (
        f"{_FILTERED_PREFIX}through {end_dt.date().isoformat()}"
        f" {_format_summary_time(end_dt.timetz().replace(tzinfo=None))}"
    )


def _local_zone() -> ZoneInfo:
    """Best-effort local timezone as a ``ZoneInfo`` instance."""
    tzinfo = datetime.now().astimezone().tzinfo
    if isinstance(tzinfo, ZoneInfo):
        return tzinfo

    key = getattr(tzinfo, "key", None)
    if isinstance(key, str):
        try:
            return ZoneInfo(key)
        except ZoneInfoNotFoundError:
            pass

    return ZoneInfo("UTC")


def _date_bounds(start_date: date, end_date: date, local_zone: ZoneInfo) -> tuple[int, int]:
    range_start = _local_datetime(start_date, _DAY_START, local_zone)
    range_end = _local_datetime(end_date, _DAY_END, local_zone)
    return _to_epoch(range_start), _to_epoch(range_end)


def _local_datetime(local_date: date, local_time: time, local_zone: ZoneInfo) -> datetime:
    return datetime.combine(local_date, local_time, tzinfo=local_zone)


def _epoch_to_local(ts: int, local_zone: ZoneInfo) -> datetime:
    return datetime.fromtimestamp(ts, tz=UTC).astimezone(local_zone)


def _to_epoch(local_dt: datetime) -> int:
    return int(local_dt.astimezone(UTC).timestamp())


def _date_summary(selected_date: date) -> str:
    return f"{_FILTERED_PREFIX}{selected_date.isoformat()}"


def _instant_summary(selected_date: date, selected_time: time) -> str:
    return f"{_FILTERED_PREFIX}{selected_date.isoformat()} at {_format_summary_time(selected_time)}"


def _format_summary_time(selected_time: time) -> str:
    return datetime.combine(date.min, selected_time).strftime(_TIME_SUMMARY_FORMAT).lstrip("0")


def _require_value(value: T | None, field_name: str) -> T:
    if value is None:
        raise ValueError(f"Report filter state is missing required field: {field_name}")
    return value
