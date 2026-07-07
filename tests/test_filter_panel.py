"""Tests for the reports filter panel UI (NST-701)."""

from __future__ import annotations

from datetime import date, time

from PySide6.QtCore import QDate, Qt, QTime

from app.data.models import ReportFilterMode, ReportFilterUiState
from app.ui.reports.filter_panel import FILTER_MODE_ITEMS, FilterPanel


def _set_mode(panel: FilterPanel, label: str) -> None:
    panel.mode_combo.setCurrentText(label)


def test_filter_panel_switches_visible_editors_by_mode(qtbot) -> None:
    panel = FilterPanel()
    qtbot.addWidget(panel)
    panel.show()
    qtbot.waitExposed(panel)

    assert [panel.mode_combo.itemText(index) for index in range(panel.mode_combo.count())] == [
        label for label, _mode in FILTER_MODE_ITEMS
    ]
    assert panel.primary_date_edit.calendarPopup()
    assert panel.end_date_edit.calendarPopup()
    for time_edit in (panel.primary_time_edit, panel.start_time_edit, panel.end_time_edit):
        assert time_edit.buttonSymbols() == time_edit.ButtonSymbols.UpDownArrows
        assert not time_edit.isReadOnly()
    assert panel.primary_date_edit.isVisible()
    assert not panel.end_date_edit.isVisible()
    assert not panel.primary_time_edit.isVisible()
    assert not panel.start_time_edit.isVisible()
    assert not panel.end_time_edit.isVisible()

    _set_mode(panel, "Date Range")
    assert panel.primary_date_edit.isVisible()
    assert panel.end_date_edit.isVisible()
    assert panel.date_range_separator.isVisible()
    assert not panel.primary_time_edit.isVisible()
    assert not panel.start_time_edit.isVisible()
    assert not panel.end_time_edit.isVisible()

    _set_mode(panel, "Date + Time")
    assert panel.primary_date_edit.isVisible()
    assert not panel.end_date_edit.isVisible()
    assert panel.primary_time_edit.isVisible()
    assert not panel.start_time_edit.isVisible()
    assert not panel.end_time_edit.isVisible()

    _set_mode(panel, "Date + Time Range")
    assert panel.primary_date_edit.isVisible()
    assert not panel.end_date_edit.isVisible()
    assert not panel.primary_time_edit.isVisible()
    assert panel.start_time_edit.isVisible()
    assert panel.time_range_separator.isVisible()
    assert panel.end_time_edit.isVisible()


def test_filter_panel_apply_emits_current_ui_state(qtbot) -> None:
    panel = FilterPanel()
    qtbot.addWidget(panel)
    panel.show()
    qtbot.waitExposed(panel)

    _set_mode(panel, "Date + Time Range")
    panel.primary_date_edit.setDate(QDate(2026, 7, 7))
    panel.start_time_edit.setTime(QTime(9, 15))
    panel.end_time_edit.setTime(QTime(10, 45))

    with qtbot.waitSignal(panel.filter_applied, timeout=1000) as blocker:
        qtbot.mouseClick(panel.apply_button, Qt.MouseButton.LeftButton)

    assert blocker.args == [
        ReportFilterUiState(
            mode=ReportFilterMode.DATE_TIME_RANGE,
            start_date=date(2026, 7, 7),
            start_time=time(9, 15),
            end_time=time(10, 45),
        )
    ]


def test_filter_panel_reset_emits_no_filter_and_restores_defaults(qtbot) -> None:
    panel = FilterPanel()
    qtbot.addWidget(panel)
    panel.show()
    qtbot.waitExposed(panel)

    _set_mode(panel, "Date Range")
    panel.primary_date_edit.setDate(QDate(2026, 7, 1))
    panel.end_date_edit.setDate(QDate(2026, 7, 4))

    with qtbot.waitSignal(panel.filter_applied, timeout=1000) as blocker:
        qtbot.mouseClick(panel.reset_button, Qt.MouseButton.LeftButton)

    assert blocker.args == [ReportFilterUiState()]
    assert panel.mode_combo.currentText() == "Date"
    assert panel.primary_date_edit.date() == QDate.currentDate()
    assert panel.end_date_edit.date() == QDate.currentDate()
    assert panel.primary_date_edit.isVisible()
    assert not panel.end_date_edit.isVisible()
    assert not panel.primary_time_edit.isVisible()
    assert not panel.start_time_edit.isVisible()
    assert not panel.end_time_edit.isVisible()
