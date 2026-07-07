"""Reports table body with empty state and guarded auto-refresh (NST-601)."""

from __future__ import annotations

import logging
import platform
import sqlite3
import subprocess
from datetime import UTC, datetime, time
from pathlib import Path
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from PySide6.QtCore import QObject, QRunnable, Qt, QThreadPool, QUrl, Signal, Slot
from PySide6.QtGui import QDesktopServices, QShowEvent
from PySide6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QFileDialog,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QStackedLayout,
    QStatusBar,
    QTableView,
    QVBoxLayout,
    QWidget,
)

from app import config
from app.data import db
from app.data.models import ReportFilter, ReportFilterUiState
from app.data.repository import Repository
from app.export.pdf_report import generate_report
from app.platform.userinfo import get_full_name
from app.ui.reports.filter_builder import (
    build_report_filter,
    summarize_filter_state,
    summarize_report_filter,
)
from app.ui.reports.filter_panel import FilterPanel
from app.ui.reports.table_model import ReportsTableModel

EMPTY_STATE_TEXT = "No records for the selected filter."
PAGE_ELLIPSIS_TEXT = "..."
PAGE_BUTTON_OBJECT_NAME_PREFIX = "reportsPageNumberButton"
PAGE_ELLIPSIS_OBJECT_NAME = "reportsPageEllipsisLabel"
EXPORT_DIALOG_TITLE = "Export PDF"
EXPORT_FILE_FILTER = "PDF Files (*.pdf)"
EXPORT_BUSY_TEXT = "Exporting…"
EXPORT_FAILURE_STATUS_TEXT = "Export failed."
EXPORT_FAILURE_TITLE = "Export Failed"
EXPORT_FAILURE_TEXT = (
    "Speedlog couldn't export the PDF. Please try again or choose a different location. "
    "Details were written to the app log."
)
EXPORT_REVEAL_TEXT = "Reveal in Finder"
EXPORT_REVEAL_BUTTON_OBJECT_NAME = "reportsRevealExportButton"
FILTERED_PREFIX = "Filtered: "
UNFILTERED_SUMMARY = "Showing all records"
UNFILTERED_EXPORT_LABEL = "All records"
DAY_START = time(0, 0, 0)
DAY_END = time(23, 59, 59)
EXPORT_FILENAME_DATE_FORMAT = "%Y-%m-%d"
EXPORT_FILENAME_MOMENT_FORMAT = "%Y-%m-%dT%H%M%S"
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


class _PdfExportSignals(QObject):
    """Qt signals used by the background PDF export runnable."""

    succeeded = Signal(str)
    failed = Signal()
    finished = Signal()


class _PdfExportRunnable(QRunnable):
    """Export the current filtered report to PDF on a thread-pool worker."""

    def __init__(
        self,
        *,
        db_path: Path | str,
        report_filter: ReportFilter,
        filter_label: str,
        out_path: Path,
    ) -> None:
        super().__init__()
        self.signals = _PdfExportSignals()
        self._db_path = Path(db_path)
        self._report_filter = ReportFilter(
            range_start_ts=report_filter.range_start_ts,
            range_end_ts=report_filter.range_end_ts,
        )
        self._filter_label = filter_label
        self._out_path = out_path

    def run(self) -> None:
        """Open a worker-thread repository, stream the full set, and build the PDF."""
        conn: sqlite3.Connection | None = None
        try:
            conn = db.get_connection(self._db_path)
            db.migrate(conn)
            repository = Repository(conn)
            generate_report(
                repository.fetch_all_records(self._report_filter),
                self._filter_label,
                get_full_name(),
                self._out_path,
            )
        except Exception:
            logger.exception("Failed to export PDF report to %s", self._out_path)
            self.signals.failed.emit()
        else:
            self.signals.succeeded.emit(str(self._out_path))
        finally:
            if conn is not None:
                conn.close()
            self.signals.finished.emit()


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


def _local_datetime(ts: int) -> datetime:
    """Convert a UTC epoch timestamp to a local ``datetime``."""
    return datetime.fromtimestamp(ts, tz=UTC).astimezone(_local_zone())


def _is_full_day_range(start_dt: datetime, end_dt: datetime) -> bool:
    return (
        start_dt.timetz().replace(tzinfo=None) == DAY_START
        and end_dt.timetz().replace(tzinfo=None) == DAY_END
    )


def _format_export_filter_label(summary: str) -> str:
    """Normalize filter summaries for the PDF header line."""
    if summary == UNFILTERED_SUMMARY:
        return UNFILTERED_EXPORT_LABEL
    if summary.startswith(FILTERED_PREFIX):
        return summary[len(FILTERED_PREFIX) :]
    return summary


def _format_export_moment(moment: datetime) -> str:
    return moment.strftime(EXPORT_FILENAME_MOMENT_FORMAT)


def _export_filename_tokens(report_filter: ReportFilter) -> tuple[str, str] | None:
    """Return filename-safe local from/to tokens for ``report_filter``."""
    if report_filter.range_start_ts is None and report_filter.range_end_ts is None:
        return None

    if report_filter.range_start_ts is not None and report_filter.range_end_ts is not None:
        start_dt = _local_datetime(report_filter.range_start_ts)
        end_dt = _local_datetime(report_filter.range_end_ts)
        if _is_full_day_range(start_dt, end_dt):
            return (
                start_dt.strftime(EXPORT_FILENAME_DATE_FORMAT),
                end_dt.strftime(EXPORT_FILENAME_DATE_FORMAT),
            )
        return _format_export_moment(start_dt), _format_export_moment(end_dt)

    if report_filter.range_start_ts is not None:
        return _format_export_moment(_local_datetime(report_filter.range_start_ts)), "open"

    assert report_filter.range_end_ts is not None
    return "start", _format_export_moment(_local_datetime(report_filter.range_end_ts))


def _default_export_filename(report_filter: ReportFilter) -> str:
    """Build the default save name required by the export-flow ticket."""
    tokens = _export_filename_tokens(report_filter)
    if tokens is None:
        return f"{config.APP_NAME}-Report-all.pdf"

    from_token, to_token = tokens
    return f"{config.APP_NAME}-Report-{from_token}_{to_token}.pdf"


def _default_export_path(report_filter: ReportFilter) -> Path:
    """Return the default save location for a PDF export."""
    return Path.home() / _default_export_filename(report_filter)


def _normalize_export_path(selected_path: str) -> Path:
    """Ensure the chosen export path ends with ``.pdf``."""
    out_path = Path(selected_path)
    if out_path.suffix.lower() == ".pdf":
        return out_path
    return out_path.with_suffix(".pdf")


def _reveal_exported_file(path: Path) -> bool:
    """Reveal the exported file in Finder on macOS, or open its folder elsewhere."""
    if platform.system() == "Darwin":
        try:
            result = subprocess.run(
                ["open", "-R", str(path)],
                check=False,
                capture_output=True,
            )
        except OSError:
            logger.exception("Failed to reveal exported PDF in Finder: %s", path)
            return False
        if result.returncode == 0:
            return True
        logger.warning(
            "Finder reveal command failed for %s with exit code %s", path, result.returncode
        )

    return QDesktopServices.openUrl(QUrl.fromLocalFile(str(path.parent)))


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
        self._active_filter_ui_state: ReportFilterUiState | None = ReportFilterUiState()
        self._current_page = 1
        self._total_pages = 1
        self._total_records = 0
        self._loaded_once = False
        self._export_thread_pool = QThreadPool.globalInstance()
        self._active_export: _PdfExportRunnable | None = None
        self._last_export_path: Path | None = None
        self._reveal_export_button: QPushButton | None = None

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

        self.controls_card = QWidget(self.surface)
        self.controls_card.setObjectName("reportsControlsCard")
        self.controls_card.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        controls_layout = QVBoxLayout(self.controls_card)
        controls_layout.setContentsMargins(
            config.REPORTS_SECTION_SPACING,
            config.REPORTS_SECTION_SPACING,
            config.REPORTS_SECTION_SPACING,
            config.REPORTS_SECTION_SPACING,
        )
        controls_layout.setSpacing(config.REPORTS_FILTER_BAR_SPACING)

        self.filter_panel = FilterPanel(self.controls_card)
        self.filter_panel.filter_applied.connect(self._apply_filter_state)
        self.filter_panel.export_requested.connect(self.export_pdf)
        controls_layout.addWidget(self.filter_panel)

        self.filter_status_row = QWidget(self.controls_card)
        self.filter_status_row.setObjectName("reportsFilterStatusRow")
        status_layout = QHBoxLayout(self.filter_status_row)
        status_layout.setContentsMargins(0, 0, 0, 0)
        status_layout.setSpacing(config.REPORTS_FILTER_BAR_SPACING)

        self.filter_status_caption_label = QLabel("Current scope", self.filter_status_row)
        self.filter_status_caption_label.setObjectName("reportsFilterStatusCaptionLabel")
        status_layout.addWidget(self.filter_status_caption_label)

        self.filter_status_label = QLabel(self.filter_status_row)
        self.filter_status_label.setObjectName("reportsFilterStatusLabel")
        self.filter_status_label.setWordWrap(True)
        status_layout.addWidget(self.filter_status_label, 1)
        controls_layout.addWidget(self.filter_status_row)
        surface_layout.addWidget(self.controls_card)

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
        self._update_filter_status_label()
        self._update_empty_state()
        self._update_pagination_controls()

    @property
    def current_page(self) -> int:
        return self._current_page

    def showEvent(self, event: QShowEvent) -> None:
        super().showEvent(event)
        if not self._loaded_once:
            self.reload_page()

    def set_filter(
        self, report_filter: ReportFilter, ui_state: ReportFilterUiState | None = None
    ) -> None:
        """Set the active report filter, refresh the status line, and reset to page 1."""
        self._report_filter = report_filter
        if ui_state is not None:
            self._active_filter_ui_state = ui_state
        elif _is_unbounded_filter(report_filter):
            self._active_filter_ui_state = ReportFilterUiState()
        else:
            self._active_filter_ui_state = None
        self._update_filter_status_label()
        self.reload_page(page=1)

    @Slot(object)
    def _apply_filter_state(self, ui_state: ReportFilterUiState) -> None:
        """Convert the filter panel's local-time state into a repository filter."""
        self.set_filter(build_report_filter(ui_state), ui_state=ui_state)

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

    @Slot()
    def export_pdf(self) -> None:
        """Prompt for a save path and export the full current filtered result set."""
        if self._active_export is not None:
            return

        selected_path, _selected_filter = QFileDialog.getSaveFileName(
            self,
            EXPORT_DIALOG_TITLE,
            str(_default_export_path(self._report_filter)),
            EXPORT_FILE_FILTER,
        )
        if not selected_path:
            return

        self._start_export(_normalize_export_path(selected_path))

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

    def _update_filter_status_label(self) -> None:
        if self._active_filter_ui_state is not None:
            summary = summarize_filter_state(self._active_filter_ui_state)
        else:
            summary = summarize_report_filter(self._report_filter)
        self.filter_status_label.setText(summary)

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

    def _current_filter_summary(self) -> str:
        if self._active_filter_ui_state is not None:
            return summarize_filter_state(self._active_filter_ui_state)
        return summarize_report_filter(self._report_filter)

    def _start_export(self, out_path: Path) -> None:
        self._hide_reveal_export_button()
        self._last_export_path = None
        self.filter_panel.export_button.setEnabled(False)
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        status_bar = self._status_bar()
        if status_bar is not None:
            status_bar.showMessage(EXPORT_BUSY_TEXT)

        export_job = _PdfExportRunnable(
            db_path=self._db_path,
            report_filter=self._report_filter,
            filter_label=_format_export_filter_label(self._current_filter_summary()),
            out_path=out_path,
        )
        export_job.signals.succeeded.connect(self._on_export_succeeded)
        export_job.signals.failed.connect(self._on_export_failed)
        export_job.signals.finished.connect(self._on_export_finished)
        self._active_export = export_job
        self._export_thread_pool.start(export_job)

    @Slot(str)
    def _on_export_succeeded(self, out_path_str: str) -> None:
        out_path = Path(out_path_str)
        self._last_export_path = out_path
        status_bar = self._status_bar()
        if status_bar is not None:
            status_bar.showMessage(f"Exported PDF to {out_path.name}")
        self._show_reveal_export_button()

    @Slot()
    def _on_export_failed(self) -> None:
        status_bar = self._status_bar()
        if status_bar is not None:
            status_bar.showMessage(EXPORT_FAILURE_STATUS_TEXT)
        QMessageBox.critical(self, EXPORT_FAILURE_TITLE, EXPORT_FAILURE_TEXT)

    @Slot()
    def _on_export_finished(self) -> None:
        self._active_export = None
        self.filter_panel.export_button.setEnabled(True)
        if QApplication.overrideCursor() is not None:
            QApplication.restoreOverrideCursor()

    @Slot()
    def _reveal_last_export(self) -> None:
        if self._last_export_path is None:
            return
        if not _reveal_exported_file(self._last_export_path):
            logger.warning("Failed to reveal exported PDF at %s", self._last_export_path)

    def _status_bar(self) -> QStatusBar | None:
        window = self.window()
        if isinstance(window, QMainWindow):
            return window.statusBar()
        return None

    def _ensure_reveal_export_button(self) -> QPushButton | None:
        if self._reveal_export_button is not None:
            return self._reveal_export_button

        status_bar = self._status_bar()
        if status_bar is None:
            return None

        button = QPushButton(EXPORT_REVEAL_TEXT, status_bar)
        button.setObjectName(EXPORT_REVEAL_BUTTON_OBJECT_NAME)
        button.setFlat(True)
        button.setVisible(False)
        button.clicked.connect(self._reveal_last_export)
        status_bar.addPermanentWidget(button)
        self._reveal_export_button = button
        return button

    def _show_reveal_export_button(self) -> None:
        button = self._ensure_reveal_export_button()
        if button is not None:
            button.setVisible(True)

    def _hide_reveal_export_button(self) -> None:
        if self._reveal_export_button is not None:
            self._reveal_export_button.setVisible(False)


def _is_unbounded_filter(report_filter: ReportFilter) -> bool:
    return report_filter.range_start_ts is None and report_filter.range_end_ts is None
