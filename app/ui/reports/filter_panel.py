"""Filter panel UI (4 modes) for the reports page (NST-701)."""

from __future__ import annotations

from datetime import date, time

from PySide6.QtCore import QDate, Qt, QTime, Signal, Slot
from PySide6.QtWidgets import (
    QComboBox,
    QDateEdit,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTimeEdit,
    QWidget,
)

from app import config
from app.data.models import ReportFilterMode, ReportFilterUiState

FILTER_MODE_ITEMS: tuple[tuple[str, ReportFilterMode], ...] = (
    ("Date", ReportFilterMode.DATE),
    ("Date Range", ReportFilterMode.DATE_RANGE),
    ("Date + Time", ReportFilterMode.DATE_TIME),
    ("Date + Time Range", ReportFilterMode.DATE_TIME_RANGE),
)
RANGE_SEPARATOR_TEXT = "to"
TIME_EDIT_DISPLAY_FORMAT = "h:mm AP"
DATE_EDIT_DISPLAY_FORMAT = "yyyy-MM-dd"


class FilterPanel(QWidget):
    """Reports filter bar with mode-specific editors and Apply/Reset actions."""

    filter_applied = Signal(object)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("reportsFilterPanel")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(config.REPORTS_FILTER_BAR_SPACING)

        self.mode_combo = QComboBox(self)
        self.mode_combo.setObjectName("reportsFilterModeCombo")
        self.mode_combo.setToolTip("Choose how the reports table should be filtered.")
        for label, mode in FILTER_MODE_ITEMS:
            self.mode_combo.addItem(label, mode)
        self.mode_combo.currentIndexChanged.connect(self._update_editor_visibility)
        layout.addWidget(self.mode_combo)

        self.primary_date_edit = self._create_date_edit(
            "reportsFilterPrimaryDateEdit",
            "Pick the date used for the selected filter mode.",
        )
        layout.addWidget(self.primary_date_edit)

        self.date_range_separator = self._create_range_separator("reportsFilterDateRangeSeparator")
        layout.addWidget(self.date_range_separator)

        self.end_date_edit = self._create_date_edit(
            "reportsFilterEndDateEdit",
            "Pick the end date when using Date Range mode.",
        )
        layout.addWidget(self.end_date_edit)

        self.primary_time_edit = self._create_time_edit(
            "reportsFilterPrimaryTimeEdit",
            "Pick the time used when filtering by a specific instant.",
            default_time=QTime.currentTime(),
        )
        layout.addWidget(self.primary_time_edit)

        self.start_time_edit = self._create_time_edit(
            "reportsFilterStartTimeEdit",
            "Pick the start time for the selected day.",
            default_time=QTime(0, 0),
        )
        layout.addWidget(self.start_time_edit)

        self.time_range_separator = self._create_range_separator("reportsFilterTimeRangeSeparator")
        layout.addWidget(self.time_range_separator)

        self.end_time_edit = self._create_time_edit(
            "reportsFilterEndTimeEdit",
            "Pick the end time for the selected day.",
            default_time=QTime(23, 59),
        )
        layout.addWidget(self.end_time_edit)

        self.apply_button = QPushButton("Apply", self)
        self.apply_button.setObjectName("reportsFilterApplyButton")
        self.apply_button.setAutoDefault(False)
        self.apply_button.clicked.connect(self.apply_filter)
        layout.addWidget(self.apply_button)

        self.reset_button = QPushButton("Reset", self)
        self.reset_button.setObjectName("reportsFilterResetButton")
        self.reset_button.setAutoDefault(False)
        self.reset_button.clicked.connect(self.reset_filter)
        layout.addWidget(self.reset_button)

        layout.addStretch(1)
        self._set_tab_order()
        self._update_editor_visibility(self.mode_combo.currentIndex())

    @property
    def current_mode(self) -> ReportFilterMode:
        """Return the active UI filter mode."""
        mode = self.mode_combo.currentData()
        assert isinstance(mode, ReportFilterMode)
        return mode

    def current_state(self) -> ReportFilterUiState:
        """Return the current filter controls as a plain Python dataclass."""
        mode = self.current_mode
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
        if mode is ReportFilterMode.DATE_TIME:
            return ReportFilterUiState(
                mode=mode,
                start_date=self._date_from_edit(self.primary_date_edit),
                start_time=self._time_from_edit(self.primary_time_edit),
            )
        return ReportFilterUiState(
            mode=mode,
            start_date=self._date_from_edit(self.primary_date_edit),
            start_time=self._time_from_edit(self.start_time_edit),
            end_time=self._time_from_edit(self.end_time_edit),
        )

    @Slot()
    def apply_filter(self) -> None:
        """Emit the currently selected UI filter state."""
        self.filter_applied.emit(self.current_state())

    @Slot()
    def reset_filter(self) -> None:
        """Restore editor defaults and emit "no filter", not a widest-range preset."""
        self.mode_combo.setCurrentIndex(0)
        self._reset_editor_values()
        self._update_editor_visibility(self.mode_combo.currentIndex())
        # Reset means "show everything" downstream, so emit the empty UI state.
        self.filter_applied.emit(ReportFilterUiState())

    @Slot(int)
    def _update_editor_visibility(self, _index: int) -> None:
        mode = self.current_mode
        self.primary_date_edit.setVisible(True)
        self.end_date_edit.setVisible(mode is ReportFilterMode.DATE_RANGE)
        self.date_range_separator.setVisible(mode is ReportFilterMode.DATE_RANGE)
        self.primary_time_edit.setVisible(mode is ReportFilterMode.DATE_TIME)
        self.start_time_edit.setVisible(mode is ReportFilterMode.DATE_TIME_RANGE)
        self.time_range_separator.setVisible(mode is ReportFilterMode.DATE_TIME_RANGE)
        self.end_time_edit.setVisible(mode is ReportFilterMode.DATE_TIME_RANGE)

    def _reset_editor_values(self) -> None:
        today = QDate.currentDate()
        self.primary_date_edit.setDate(today)
        self.end_date_edit.setDate(today)
        self.primary_time_edit.setTime(QTime.currentTime())
        self.start_time_edit.setTime(QTime(0, 0))
        self.end_time_edit.setTime(QTime(23, 59))

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

    def _set_tab_order(self) -> None:
        QWidget.setTabOrder(self.mode_combo, self.primary_date_edit)
        QWidget.setTabOrder(self.primary_date_edit, self.end_date_edit)
        QWidget.setTabOrder(self.end_date_edit, self.primary_time_edit)
        QWidget.setTabOrder(self.primary_time_edit, self.start_time_edit)
        QWidget.setTabOrder(self.start_time_edit, self.end_time_edit)
        QWidget.setTabOrder(self.end_time_edit, self.apply_button)
        QWidget.setTabOrder(self.apply_button, self.reset_button)

    def _date_from_edit(self, edit: QDateEdit) -> date:
        selected_date = edit.date()
        return date(selected_date.year(), selected_date.month(), selected_date.day())

    def _time_from_edit(self, edit: QTimeEdit) -> time:
        selected_time = edit.time()
        return time(selected_time.hour(), selected_time.minute(), selected_time.second())
