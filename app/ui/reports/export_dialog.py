"""Export scope confirmation dialog for the reports page (NST-803)."""

from __future__ import annotations

from datetime import date, time

from PySide6.QtCore import QDate, QTime, Slot
from PySide6.QtWidgets import (
    QComboBox,
    QDateEdit,
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QLabel,
    QTimeEdit,
    QVBoxLayout,
    QWidget,
)

from app import config
from app.data.models import ReportFilterMode, ReportFilterUiState
from app.ui.reports.filter_panel import (
    DATE_EDIT_DISPLAY_FORMAT,
    RANGE_SEPARATOR_TEXT,
    TIME_EDIT_DISPLAY_FORMAT,
)

EXPORT_SCOPE_ITEMS: tuple[tuple[str, ReportFilterMode | None], ...] = (
    ("Date", ReportFilterMode.DATE),
    ("Date Range", ReportFilterMode.DATE_RANGE),
    ("Date + Time Range", ReportFilterMode.DATE_TIME_RANGE),
    ("All records", None),
)
EXPORT_OPTIONS_TITLE = "Export PDF"
EXPORT_OPTIONS_PROMPT = "Choose which records to export. Today's records are exported by default."
EXPORT_ACCEPT_TEXT = "Export"


class ExportOptionsDialog(QDialog):
    """Modal popup asking which records the PDF export should cover."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("reportsExportOptionsDialog")
        self.setWindowTitle(EXPORT_OPTIONS_TITLE)
        self.setModal(True)

        layout = QVBoxLayout(self)
        layout.setSpacing(config.REPORTS_FILTER_BAR_SPACING)

        self.prompt_label = QLabel(EXPORT_OPTIONS_PROMPT, self)
        self.prompt_label.setObjectName("reportsExportPromptLabel")
        self.prompt_label.setWordWrap(True)
        layout.addWidget(self.prompt_label)

        self.scope_combo = QComboBox(self)
        self.scope_combo.setObjectName("reportsExportScopeCombo")
        self.scope_combo.setToolTip("Choose which records the exported PDF should include.")
        for label, mode in EXPORT_SCOPE_ITEMS:
            self.scope_combo.addItem(label, mode)
        self.scope_combo.currentIndexChanged.connect(self._update_editor_visibility)
        layout.addWidget(self.scope_combo)

        editors_row = QWidget(self)
        editors_row.setObjectName("reportsExportEditorsRow")
        editors_layout = QHBoxLayout(editors_row)
        editors_layout.setContentsMargins(0, 0, 0, 0)
        editors_layout.setSpacing(config.REPORTS_FILTER_BAR_SPACING)

        self.primary_date_edit = self._create_date_edit(
            "reportsExportPrimaryDateEdit",
            "Pick the date (or range start) to export.",
        )
        editors_layout.addWidget(self.primary_date_edit)

        self.date_range_separator = self._create_range_separator("reportsExportDateRangeSeparator")
        editors_layout.addWidget(self.date_range_separator)

        self.end_date_edit = self._create_date_edit(
            "reportsExportEndDateEdit",
            "Pick the end date when exporting a date range.",
        )
        editors_layout.addWidget(self.end_date_edit)

        self.start_time_edit = self._create_time_edit(
            "reportsExportStartTimeEdit",
            "Pick the start time for the selected day.",
            default_time=QTime(0, 0),
        )
        editors_layout.addWidget(self.start_time_edit)

        self.time_range_separator = self._create_range_separator("reportsExportTimeRangeSeparator")
        editors_layout.addWidget(self.time_range_separator)

        self.end_time_edit = self._create_time_edit(
            "reportsExportEndTimeEdit",
            "Pick the end time for the selected day.",
            default_time=QTime(23, 59),
        )
        editors_layout.addWidget(self.end_time_edit)

        editors_layout.addStretch(1)
        layout.addWidget(editors_row)

        self.button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Cancel | QDialogButtonBox.StandardButton.Ok,
            self,
        )
        self.button_box.setObjectName("reportsExportButtonBox")
        export_button = self.button_box.button(QDialogButtonBox.StandardButton.Ok)
        export_button.setText(EXPORT_ACCEPT_TEXT)
        export_button.setDefault(True)
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        layout.addWidget(self.button_box)

        self._update_editor_visibility(self.scope_combo.currentIndex())

    @property
    def current_mode(self) -> ReportFilterMode | None:
        """Return the selected export scope; ``None`` means all records."""
        mode = self.scope_combo.currentData()
        assert mode is None or isinstance(mode, ReportFilterMode)
        return mode

    def selected_state(self) -> ReportFilterUiState:
        """Return the chosen export scope as a filter UI state."""
        mode = self.current_mode
        if mode is None:
            return ReportFilterUiState()
        if mode is ReportFilterMode.DATE:
            return ReportFilterUiState(
                mode=mode,
                start_date=self._date_from_edit(self.primary_date_edit),
            )
        if mode is ReportFilterMode.DATE_RANGE:
            return ReportFilterUiState(
                mode=mode,
                start_date=self._date_from_edit(self.primary_date_edit),
                end_date=self._date_from_edit(self.end_date_edit),
            )
        assert mode is ReportFilterMode.DATE_TIME_RANGE
        return ReportFilterUiState(
            mode=mode,
            start_date=self._date_from_edit(self.primary_date_edit),
            start_time=self._time_from_edit(self.start_time_edit),
            end_time=self._time_from_edit(self.end_time_edit),
        )

    @Slot(int)
    def _update_editor_visibility(self, _index: int) -> None:
        mode = self.current_mode
        self.primary_date_edit.setVisible(mode is not None)
        self.end_date_edit.setVisible(mode is ReportFilterMode.DATE_RANGE)
        self.date_range_separator.setVisible(mode is ReportFilterMode.DATE_RANGE)
        self.start_time_edit.setVisible(mode is ReportFilterMode.DATE_TIME_RANGE)
        self.time_range_separator.setVisible(mode is ReportFilterMode.DATE_TIME_RANGE)
        self.end_time_edit.setVisible(mode is ReportFilterMode.DATE_TIME_RANGE)

    def _create_date_edit(self, object_name: str, tooltip: str) -> QDateEdit:
        edit = QDateEdit(QDate.currentDate(), self)
        edit.setObjectName(object_name)
        edit.setCalendarPopup(True)
        edit.setDisplayFormat(DATE_EDIT_DISPLAY_FORMAT)
        edit.setToolTip(tooltip)
        return edit

    def _create_time_edit(self, object_name: str, tooltip: str, default_time: QTime) -> QTimeEdit:
        edit = QTimeEdit(default_time, self)
        edit.setObjectName(object_name)
        edit.setDisplayFormat(TIME_EDIT_DISPLAY_FORMAT)
        edit.setToolTip(tooltip)
        return edit

    def _create_range_separator(self, object_name: str) -> QLabel:
        label = QLabel(RANGE_SEPARATOR_TEXT, self)
        label.setObjectName(object_name)
        return label

    def _date_from_edit(self, edit: QDateEdit) -> date:
        selected_date = edit.date()
        return date(selected_date.year(), selected_date.month(), selected_date.day())

    def _time_from_edit(self, edit: QTimeEdit) -> time:
        selected_time = edit.time()
        return time(selected_time.hour(), selected_time.minute(), selected_time.second())
