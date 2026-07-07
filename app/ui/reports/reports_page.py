"""Reports table body with empty state and guarded auto-refresh (NST-601)."""

from __future__ import annotations

import logging
import sqlite3
from pathlib import Path

from PySide6.QtCore import Qt, Slot
from PySide6.QtGui import QShowEvent
from PySide6.QtWidgets import (
    QAbstractItemView,
    QHeaderView,
    QLabel,
    QStackedLayout,
    QTableView,
    QVBoxLayout,
    QWidget,
)

from app import config
from app.data import db
from app.data.models import ReportFilter
from app.data.repository import Repository
from app.ui.reports.table_model import ReportsTableModel

EMPTY_STATE_TEXT = "No records for the selected filter."
logger = logging.getLogger(__name__)


class ReportsPage(QWidget):
    """Reports tab body: a read-only table backed by repository page reads."""

    def __init__(self, parent: QWidget | None = None, db_path: Path | str | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("reportsTab")
        self._db_path = db_path if db_path is not None else config.db_path()
        self._conn: sqlite3.Connection | None = None
        self._repository: Repository | None = None
        self._report_filter = ReportFilter()
        self._current_page = 1
        self._loaded_once = False

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.model = ReportsTableModel(self)
        self.table = QTableView(self)
        self.table.setObjectName("reportsTable")
        self.table.setModel(self.model)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setAlternatingRowColors(True)
        self.table.setSortingEnabled(False)
        self.table.verticalHeader().setVisible(False)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)

        self.empty_state_label = QLabel(EMPTY_STATE_TEXT, self)
        self.empty_state_label.setObjectName("reportsEmptyStateLabel")
        self.empty_state_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self._stack = QStackedLayout()
        self._stack.addWidget(self.table)
        self._stack.addWidget(self.empty_state_label)
        layout.addLayout(self._stack)
        self._update_empty_state()

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

    def reload_page(self, page: int | None = None) -> None:
        """Load ``page`` (1-based) from the repository, defaulting to the current page."""
        if page is not None:
            self._current_page = max(1, page)
        try:
            self._ensure_repository()
            assert self._repository is not None
            records = self._repository.fetch_records(
                self._report_filter,
                page=self._current_page,
                page_size=config.PAGE_SIZE,
            )
        except sqlite3.Error:
            logger.exception("Failed to load reports page from %s", self._db_path)
            self.model.set_page([])
            self._update_empty_state()
            return
        self.model.set_page(records)
        self._loaded_once = True
        self._update_empty_state()

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
