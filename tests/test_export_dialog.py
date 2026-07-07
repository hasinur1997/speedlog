"""Tests for the export scope confirmation dialog (NST-803)."""

from __future__ import annotations

from datetime import date, time

from PySide6.QtCore import QDate, QTime
from PySide6.QtWidgets import QDialogButtonBox

from app.data.models import ReportFilterMode, ReportFilterUiState
from app.ui.reports.export_dialog import EXPORT_ACCEPT_TEXT, ExportOptionsDialog


def _shown_dialog(qtbot) -> ExportOptionsDialog:
    dialog = ExportOptionsDialog()
    qtbot.addWidget(dialog)
    dialog.show()
    qtbot.waitExposed(dialog)
    return dialog


def test_export_dialog_defaults_to_todays_records(qtbot) -> None:
    dialog = _shown_dialog(qtbot)

    assert dialog.current_mode is ReportFilterMode.DATE
    assert dialog.primary_date_edit.date() == QDate.currentDate()
    assert dialog.selected_state() == ReportFilterUiState(
        mode=ReportFilterMode.DATE,
        start_date=date.today(),
    )

    assert dialog.primary_date_edit.isVisible()
    assert not dialog.end_date_edit.isVisible()
    assert not dialog.start_time_edit.isVisible()
    assert not dialog.end_time_edit.isVisible()

    export_button = dialog.button_box.button(QDialogButtonBox.StandardButton.Ok)
    assert export_button.text() == EXPORT_ACCEPT_TEXT


def test_export_dialog_editors_keep_picker_affordances(qtbot) -> None:
    dialog = _shown_dialog(qtbot)

    assert dialog.primary_date_edit.calendarPopup()
    assert dialog.end_date_edit.calendarPopup()
    for time_edit in (dialog.start_time_edit, dialog.end_time_edit):
        assert time_edit.buttonSymbols() == time_edit.ButtonSymbols.UpDownArrows
        assert not time_edit.isReadOnly()


def test_export_dialog_date_range_scope(qtbot) -> None:
    dialog = _shown_dialog(qtbot)
    dialog.scope_combo.setCurrentText("Date Range")

    assert dialog.primary_date_edit.isVisible()
    assert dialog.end_date_edit.isVisible()
    assert not dialog.start_time_edit.isVisible()

    dialog.primary_date_edit.setDate(QDate(2026, 7, 1))
    dialog.end_date_edit.setDate(QDate(2026, 7, 7))
    assert dialog.selected_state() == ReportFilterUiState(
        mode=ReportFilterMode.DATE_RANGE,
        start_date=date(2026, 7, 1),
        end_date=date(2026, 7, 7),
    )


def test_export_dialog_date_time_range_scope(qtbot) -> None:
    dialog = _shown_dialog(qtbot)
    dialog.scope_combo.setCurrentText("Date + Time Range")

    assert dialog.primary_date_edit.isVisible()
    assert not dialog.end_date_edit.isVisible()
    assert dialog.start_time_edit.isVisible()
    assert dialog.end_time_edit.isVisible()
    assert dialog.start_time_edit.time() == QTime(0, 0)
    assert dialog.end_time_edit.time() == QTime(23, 59)

    dialog.primary_date_edit.setDate(QDate(2026, 7, 7))
    dialog.start_time_edit.setTime(QTime(9, 30))
    dialog.end_time_edit.setTime(QTime(17, 0))
    assert dialog.selected_state() == ReportFilterUiState(
        mode=ReportFilterMode.DATE_TIME_RANGE,
        start_date=date(2026, 7, 7),
        start_time=time(9, 30),
        end_time=time(17, 0),
    )


def test_export_dialog_all_records_scope(qtbot) -> None:
    dialog = _shown_dialog(qtbot)
    dialog.scope_combo.setCurrentText("All records")

    assert dialog.current_mode is None
    assert not dialog.primary_date_edit.isVisible()
    assert not dialog.end_date_edit.isVisible()
    assert not dialog.start_time_edit.isVisible()
    assert not dialog.end_time_edit.isVisible()
    assert dialog.selected_state() == ReportFilterUiState()
