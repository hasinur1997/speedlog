"""Reports table body with empty state and guarded auto-refresh (NST-601)."""

from __future__ import annotations

import logging
import sqlite3
from pathlib import Path

from PySide6.QtCore import Qt, Slot
from PySide6.QtGui import QShowEvent
from PySide6.QtWidgets import (
    QAbstractItemView,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QStackedLayout,
    QTableView,
    QVBoxLayout,
    QWidget,
)

from app import config
from app.data import db
from app.data.models import ReportFilter
from app.data.repository import Repository
from app.ui.reports.filter_panel import FilterPanel
from app.ui.reports.table_model import ReportsTableModel

EMPTY_STATE_TEXT = "No records for the selected filter."
PAGE_ELLIPSIS_TEXT = "..."
PAGE_BUTTON_OBJECT_NAME_PREFIX = "reportsPageNumberButton"
PAGE_ELLIPSIS_OBJECT_NAME = "reportsPageEllipsisLabel"
logger = logging.getLogger(__name__)


def _page_count(total_records: int) -> int:
    """Return the number of pages needed for ``total_records`` using ``config.PAGE_SIZE``."""
    if total_records <= 0:
        return 1
    return ((total_records - 1) // config.PAGE_SIZE) + 1


def _record_count_label(total_records: int) -> str:
    """Return the singular/plural record count label."""
    noun = "record" if total_records == 1 else "records"
    return f"{total_records} {noun}"


def _visible_page_items(
    current_page: int, total_pages: int, max_visible_buttons: int
) -> list[int | None]:
    """Return visible page numbers, using ``None`` entries for ellipsis gaps."""
    if total_pages <= 1:
        return [1]

    visible_buttons = max(5, max_visible_buttons)
    if total_pages <= visible_buttons:
        page_numbers = list(range(1, total_pages + 1))
    else:
        middle_count = visible_buttons - 2
        start = current_page - (middle_count // 2)
        end = start + middle_count - 1

        if start < 2:
            start = 2
            end = start + middle_count - 1
        if end > total_pages - 1:
            end = total_pages - 1
            start = end - middle_count + 1

        page_numbers = [1, *range(start, end + 1), total_pages]

    items: list[int | None] = []
    previous_page: int | None = None
    for page_number in page_numbers:
        if previous_page is not None and page_number - previous_page > 1:
            items.append(None)
        items.append(page_number)
        previous_page = page_number
    return items


class ReportsPage(QWidget):
    """Reports tab body: a read-only table backed by repository page reads."""

    def __init__(self, parent: QWidget | None = None, db_path: Path | str | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("reportsTab")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self._db_path = db_path if db_path is not None else config.db_path()
        self._conn: sqlite3.Connection | None = None
        self._repository: Repository | None = None
        self._report_filter = ReportFilter()
        self._current_page = 1
        self._total_pages = 1
        self._total_records = 0
        self._loaded_once = False

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.surface = QWidget(self)
        self.surface.setObjectName("reportsSurface")
        self.surface.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        surface_layout = QVBoxLayout(self.surface)
        surface_layout.setContentsMargins(
            config.REPORTS_SURFACE_PADDING,
            config.REPORTS_SURFACE_PADDING,
            config.REPORTS_SURFACE_PADDING,
            config.REPORTS_SURFACE_PADDING,
        )
        surface_layout.setSpacing(config.REPORTS_SECTION_SPACING)

        self.header_widget = QWidget(self.surface)
        self.header_widget.setObjectName("reportsHeader")
        header_layout = QVBoxLayout(self.header_widget)
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(4)

        self.title_label = QLabel("Connection History", self.header_widget)
        self.title_label.setObjectName("reportsTitleLabel")
        header_layout.addWidget(self.title_label)

        self.subtitle_label = QLabel(
            "Review recorded speed segments and move through pages without losing context.",
            self.header_widget,
        )
        self.subtitle_label.setObjectName("reportsSubtitleLabel")
        self.subtitle_label.setWordWrap(True)
        header_layout.addWidget(self.subtitle_label)
        surface_layout.addWidget(self.header_widget)

        self.filter_panel = FilterPanel(self.surface)
        surface_layout.addWidget(self.filter_panel)

        self.model = ReportsTableModel(self)
        self.table = QTableView(self)
        self.table.setObjectName("reportsTable")
        self.table.setModel(self.model)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setAlternatingRowColors(True)
        self.table.setShowGrid(False)
        self.table.setSortingEnabled(False)
        self.table.setWordWrap(False)
        self.table.verticalHeader().setVisible(False)
        self.table.verticalHeader().setDefaultSectionSize(config.REPORTS_TABLE_ROW_HEIGHT)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setDefaultAlignment(
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
        )

        self.empty_state_label = QLabel(EMPTY_STATE_TEXT, self)
        self.empty_state_label.setObjectName("reportsEmptyStateLabel")
        self.empty_state_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.empty_state_label.setWordWrap(True)

        self._stack = QStackedLayout()
        self._stack.addWidget(self.table)
        self._stack.addWidget(self.empty_state_label)
        self.table_area = QWidget(self.surface)
        self.table_area.setObjectName("reportsTableArea")
        self.table_area.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        table_area_layout = QVBoxLayout(self.table_area)
        table_area_layout.setContentsMargins(0, 0, 0, 0)
        table_area_layout.setSpacing(0)
        table_area_layout.addLayout(self._stack)
        surface_layout.addWidget(self.table_area, 1)

        self.pagination_bar = QWidget(self.surface)
        self.pagination_bar.setObjectName("reportsPaginationBar")
        pagination_layout = QHBoxLayout(self.pagination_bar)
        pagination_layout.setContentsMargins(0, 8, 0, 0)

        self.prev_button = QPushButton("Prev", self.pagination_bar)
        self.prev_button.setObjectName("reportsPrevButton")
        self.prev_button.setProperty("paginationButton", True)
        self.prev_button.clicked.connect(self.go_to_previous_page)
        pagination_layout.addWidget(self.prev_button)

        self._page_buttons_widget = QWidget(self.pagination_bar)
        self._page_buttons_widget.setObjectName("reportsPageButtonsWidget")
        self._page_buttons_layout = QHBoxLayout(self._page_buttons_widget)
        self._page_buttons_layout.setContentsMargins(0, 0, 0, 0)
        pagination_layout.addWidget(self._page_buttons_widget)

        self.next_button = QPushButton("Next", self.pagination_bar)
        self.next_button.setObjectName("reportsNextButton")
        self.next_button.setProperty("paginationButton", True)
        self.next_button.clicked.connect(self.go_to_next_page)
        pagination_layout.addWidget(self.next_button)

        self.page_label = QLabel(self.pagination_bar)
        self.page_label.setObjectName("reportsPageLabel")
        self.page_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        pagination_layout.addWidget(self.page_label)

        pagination_layout.addStretch(1)

        self.count_label = QLabel(self.pagination_bar)
        self.count_label.setObjectName("reportsCountLabel")
        pagination_layout.addWidget(self.count_label)

        surface_layout.addWidget(self.pagination_bar)
        layout.addWidget(self.surface)
        self._update_empty_state()
        self._update_pagination_controls()

    @property
    def current_page(self) -> int:
        return self._current_page

    def showEvent(self, event: QShowEvent) -> None:
        super().showEvent(event)
        if not self._loaded_once:
            self.reload_page()

    def set_filter(self, report_filter: ReportFilter) -> None:
        """Set the active report filter and reset paging to page 1."""
        self._report_filter = report_filter
        self.reload_page(page=1)

    @Slot()
    def go_to_previous_page(self) -> None:
        """Load the previous page when available."""
        if self._current_page > 1:
            self.reload_page(page=self._current_page - 1)

    @Slot()
    def go_to_next_page(self) -> None:
        """Load the next page when available."""
        if self._current_page < self._total_pages:
            self.reload_page(page=self._current_page + 1)

    def go_to_page(self, page: int) -> None:
        """Load ``page`` directly when it differs from the current page."""
        if page != self._current_page:
            self.reload_page(page=page)

    def reload_page(self, page: int | None = None) -> None:
        """Load ``page`` (1-based) from the repository, defaulting to the current page."""
        requested_page = self._current_page if page is None else max(1, page)
        try:
            self._ensure_repository()
            assert self._repository is not None
            self._total_records = self._repository.count_records(self._report_filter)
            self._total_pages = _page_count(self._total_records)
            self._current_page = min(requested_page, self._total_pages)
            records = self._repository.fetch_records(
                self._report_filter,
                page=self._current_page,
                page_size=config.PAGE_SIZE,
            )
        except sqlite3.Error:
            logger.exception("Failed to load reports page from %s", self._db_path)
            self._current_page = 1
            self._total_pages = 1
            self._total_records = 0
            self.model.set_page([])
            self._update_empty_state()
            self._update_pagination_controls()
            return
        self.model.set_page(records)
        self._loaded_once = True
        self._update_empty_state()
        self._update_pagination_controls()

    @Slot()
    def on_segment_closed(self) -> None:
        """Auto-refresh the top page only while the user is still at the default position."""
        if self._can_auto_refresh():
            self.reload_page()

    def _ensure_repository(self) -> None:
        if self._repository is not None:
            return
        self._conn = db.get_connection(self._db_path)
        db.migrate(self._conn)
        self._repository = Repository(self._conn)

    def _can_auto_refresh(self) -> bool:
        if self._current_page != 1:
            return False
        selection_model = self.table.selectionModel()
        if selection_model is not None and selection_model.hasSelection():
            return False
        scroll_bar = self.table.verticalScrollBar()
        return scroll_bar.value() == scroll_bar.minimum()

    def _update_empty_state(self) -> None:
        if self.model.rowCount() == 0:
            self._stack.setCurrentWidget(self.empty_state_label)
            return
        self._stack.setCurrentWidget(self.table)

    def _update_pagination_controls(self) -> None:
        self._rebuild_page_buttons()
        self.page_label.setText(f"Page {self._current_page} of {self._total_pages}")
        self.count_label.setText(_record_count_label(self._total_records))
        self.prev_button.setEnabled(self._current_page > 1)
        self.next_button.setEnabled(self._current_page < self._total_pages)

    def _rebuild_page_buttons(self) -> None:
        while self._page_buttons_layout.count():
            item = self._page_buttons_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.setParent(None)
                widget.deleteLater()

        for item in _visible_page_items(
            self._current_page,
            self._total_pages,
            config.PAGINATION_MAX_VISIBLE_BUTTONS,
        ):
            if item is None:
                label = QLabel(PAGE_ELLIPSIS_TEXT, self._page_buttons_widget)
                label.setObjectName(PAGE_ELLIPSIS_OBJECT_NAME)
                self._page_buttons_layout.addWidget(label)
                continue

            button = QPushButton(str(item), self._page_buttons_widget)
            button.setObjectName(f"{PAGE_BUTTON_OBJECT_NAME_PREFIX}{item}")
            button.setAutoDefault(False)
            button.setCheckable(True)
            button.setProperty("pageButton", True)
            button.setChecked(item == self._current_page)
            button.clicked.connect(lambda _checked=False, page=item: self.go_to_page(page))
            self._page_buttons_layout.addWidget(button)
