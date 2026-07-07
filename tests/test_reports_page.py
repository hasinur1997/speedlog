"""Tests for the reports table model and page (NST-601/NST-602/NST-604/NST-605)."""

from __future__ import annotations

import logging
import threading
from collections.abc import Callable
from datetime import UTC, date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from PySide6.QtCore import QDate, Qt, QTime
from PySide6.QtWidgets import QDialog, QFileDialog, QMessageBox, QPushButton

import app.formatting as formatting_module
import app.ui.reports.filter_builder as filter_builder_module
import app.ui.reports.reports_page as reports_page_module
from app import config
from app.data import db
from app.data.models import ReportFilter, SpeedRecord
from app.data.repository import Repository
from app.ui.main_window import MainWindow
from app.ui.reports.export_dialog import ExportOptionsDialog
from app.ui.reports.filter_panel import FilterPanel
from app.ui.reports.reports_page import ReportsPage
from app.ui.reports.table_model import ReportsTableModel

BASE_TS = 1_700_000_000
RECORD_SPACING_SECS = 60
RECORD_DURATION_SECS = 30


def _page_strip_texts(page: ReportsPage) -> list[str]:
    texts: list[str] = []
    for index in range(page._page_buttons_layout.count()):
        item = page._page_buttons_layout.itemAt(index)
        widget = item.widget()
        if widget is not None:
            texts.append(widget.text())
    return texts


def _page_button(page: ReportsPage, page_number: int) -> QPushButton:
    button = page.findChild(QPushButton, f"reportsPageNumberButton{page_number}")
    assert button is not None
    return button


def _accept_export_dialog(
    monkeypatch, configure: Callable[[ExportOptionsDialog], None] | None = None
) -> None:
    """Make the export-scope dialog auto-accept, optionally adjusting its widgets first."""

    def fake_exec(dialog_self: ExportOptionsDialog) -> int:
        if configure is not None:
            configure(dialog_self)
        return QDialog.DialogCode.Accepted

    monkeypatch.setattr(ExportOptionsDialog, "exec", fake_exec)


def _select_scope(dialog: ExportOptionsDialog, scope_text: str) -> None:
    dialog.scope_combo.setCurrentText(scope_text)


def _show_reports_window(qtbot, db_file: Path) -> MainWindow:
    window = MainWindow(reports_db_path=db_file)
    qtbot.addWidget(window)
    window.show()
    qtbot.waitExposed(window)
    window.tabs.setCurrentWidget(window.reports_page)
    return window


def _insert_record(
    db_file: Path,
    *,
    start_ts: int,
    end_ts: int,
    download_bps: float,
    upload_bps: float,
) -> None:
    conn = db.get_connection(db_file)
    try:
        db.migrate(conn)
        repo = Repository(conn)
        session_id = repo.start_session(start_ts)
        repo.insert_record(
            SpeedRecord(
                session_id=session_id,
                start_ts=start_ts,
                end_ts=end_ts,
                download_bps=download_bps,
                upload_bps=upload_bps,
            )
        )
        repo.end_session(session_id, end_ts, "quit")
    finally:
        conn.close()


def _seed_records(db_file: Path, count: int) -> None:
    conn = db.get_connection(db_file)
    try:
        db.migrate(conn)
        repo = Repository(conn)
        if count == 0:
            return
        session_id = repo.start_session(BASE_TS)
        for index in range(count):
            start_ts = BASE_TS + (index * RECORD_SPACING_SECS)
            end_ts = start_ts + RECORD_DURATION_SECS
            repo.insert_record(
                SpeedRecord(
                    session_id=session_id,
                    start_ts=start_ts,
                    end_ts=end_ts,
                    download_bps=1_000_000.0 + (index * 100_000.0),
                    upload_bps=500_000.0 + (index * 25_000.0),
                )
            )
        repo.end_session(
            session_id,
            BASE_TS + ((count - 1) * RECORD_SPACING_SECS) + RECORD_DURATION_SECS,
            "quit",
        )
    finally:
        conn.close()


def _seed_filter_records(db_file: Path) -> None:
    conn = db.get_connection(db_file)
    try:
        db.migrate(conn)
        repo = Repository(conn)
        july_6_start = int(datetime(2026, 7, 6, 12, 0, tzinfo=UTC).timestamp())
        july_7_start = int(datetime(2026, 7, 7, 12, 0, tzinfo=UTC).timestamp())
        session_id = repo.start_session(july_6_start)

        for index in range(5):
            start_ts = july_6_start + (index * RECORD_SPACING_SECS)
            repo.insert_record(
                SpeedRecord(
                    session_id=session_id,
                    start_ts=start_ts,
                    end_ts=start_ts + RECORD_DURATION_SECS,
                    download_bps=1_000_000.0 + index,
                    upload_bps=500_000.0 + index,
                )
            )

        for index in range(config.PAGE_SIZE):
            start_ts = july_7_start + (index * RECORD_SPACING_SECS)
            repo.insert_record(
                SpeedRecord(
                    session_id=session_id,
                    start_ts=start_ts,
                    end_ts=start_ts + RECORD_DURATION_SECS,
                    download_bps=2_000_000.0 + index,
                    upload_bps=750_000.0 + index,
                )
            )

        repo.end_session(
            session_id,
            july_7_start + ((config.PAGE_SIZE - 1) * RECORD_SPACING_SECS) + RECORD_DURATION_SECS,
            "quit",
        )
    finally:
        conn.close()


def test_reports_table_model_exposes_headers_and_page_data(monkeypatch) -> None:
    monkeypatch.setattr(formatting_module, "_local_zone", lambda: ZoneInfo("UTC"))
    model = ReportsTableModel()
    start_ts = int(datetime(2026, 7, 7, 10, 20, tzinfo=UTC).timestamp())
    model.set_page(
        [
            SpeedRecord(
                session_id=1,
                start_ts=start_ts,
                end_ts=start_ts + 600,
                download_bps=5_020_000.0,
                upload_bps=500_000.0,
            )
        ]
    )

    assert model.rowCount() == 1
    assert model.columnCount() == 4
    assert [
        model.headerData(section, Qt.Orientation.Horizontal)
        for section in range(model.columnCount())
    ] == ["Date", "Time", "Download", "Upload"]
    assert model.data(model.index(0, 0), Qt.ItemDataRole.DisplayRole) == "2026-07-07"
    assert model.data(model.index(0, 1), Qt.ItemDataRole.DisplayRole) == "10:20 AM – 10:30 AM"
    assert model.data(model.index(0, 2), Qt.ItemDataRole.DisplayRole) == "5.02 MB/s"
    assert model.data(model.index(0, 3), Qt.ItemDataRole.DisplayRole) == "500.00 KB/s"
    assert not (model.flags(model.index(0, 0)) & Qt.ItemFlag.ItemIsEditable)


def test_reports_page_exposes_visual_polish_hooks(qtbot, tmp_path: Path) -> None:
    db_file = tmp_path / "reports.db"
    page = ReportsPage(db_path=db_file)
    qtbot.addWidget(page)

    assert page.surface.objectName() == "reportsSurface"
    assert page.header_widget.objectName() == "reportsHeader"
    assert page.controls_card.objectName() == "reportsControlsCard"
    assert isinstance(page.filter_panel, FilterPanel)
    assert page.filter_panel.objectName() == "reportsFilterPanel"
    assert page.filter_panel.parentWidget() is page.controls_card
    assert (
        page.filter_panel.mode_combo.toolTip() == "Choose how the reports table should be filtered."
    )
    assert page.filter_status_row.objectName() == "reportsFilterStatusRow"
    assert page.filter_status_caption_label.objectName() == "reportsFilterStatusCaptionLabel"
    assert page.filter_status_caption_label.text() == "Current scope"
    assert page.filter_status_label.objectName() == "reportsFilterStatusLabel"
    assert page.filter_status_label.text() == "Showing all records"
    assert page.title_label.text() == "Connection History"
    assert "move through pages" in page.subtitle_label.text()
    assert page.filter_panel.export_button.objectName() == "reportsExportButton"
    assert page.filter_panel.export_button.toolTip() == "Export the full filtered report as a PDF."
    assert page.table_area.objectName() == "reportsTableArea"
    assert page.pagination_bar.objectName() == "reportsPaginationBar"
    assert not page.table.showGrid()
    assert not page.table.wordWrap()
    assert page.table.verticalHeader().defaultSectionSize() == config.REPORTS_TABLE_ROW_HEIGHT
    assert page.prev_button.property("paginationButton") is True
    assert page.next_button.property("paginationButton") is True
    assert page.empty_state_label.wordWrap()


def test_reports_page_shows_empty_state_and_auto_refreshes_top_page(qtbot, tmp_path: Path) -> None:
    db_file = tmp_path / "reports.db"
    page = ReportsPage(db_path=db_file)
    qtbot.addWidget(page)
    page.show()
    qtbot.waitExposed(page)

    assert page.model.rowCount() == 0
    assert page.empty_state_label.isVisible()
    assert not page.table.isVisible()
    assert page.page_label.text() == "Page 1 of 1"
    assert page.count_label.text() == "0 records"
    assert _page_strip_texts(page) == ["1"]
    assert not page.prev_button.isEnabled()
    assert not page.next_button.isEnabled()

    _insert_record(
        db_file,
        start_ts=1_700_000_000,
        end_ts=1_700_000_060,
        download_bps=5_000_000.0,
        upload_bps=1_200_000.0,
    )

    page.on_segment_closed()

    qtbot.waitUntil(lambda: page.model.rowCount() == 1, timeout=1000)
    assert page.table.isVisible()
    assert not page.empty_state_label.isVisible()
    assert page.page_label.text() == "Page 1 of 1"
    assert page.count_label.text() == "1 record"
    assert _page_strip_texts(page) == ["1"]
    assert not page.prev_button.isEnabled()
    assert not page.next_button.isEnabled()


def test_reports_page_paginates_records_and_updates_edge_button_state(
    qtbot, tmp_path: Path
) -> None:
    db_file = tmp_path / "reports.db"
    _seed_records(db_file, 50)

    page = ReportsPage(db_path=db_file)
    qtbot.addWidget(page)
    page.show()
    qtbot.waitExposed(page)
    qtbot.waitUntil(lambda: page.model.rowCount() == config.PAGE_SIZE, timeout=1000)

    assert page.current_page == 1
    assert page.page_label.text() == "Page 1 of 3"
    assert page.count_label.text() == "50 records"
    assert _page_strip_texts(page) == ["1", "2", "3"]
    assert _page_button(page, 1).isChecked()
    assert not page.prev_button.isEnabled()
    assert page.next_button.isEnabled()

    qtbot.mouseClick(_page_button(page, 3), Qt.MouseButton.LeftButton)
    qtbot.waitUntil(lambda: page.current_page == 3, timeout=1000)
    assert page.model.rowCount() == 10
    assert page.page_label.text() == "Page 3 of 3"
    assert _page_strip_texts(page) == ["1", "2", "3"]
    assert _page_button(page, 3).isChecked()
    assert page.prev_button.isEnabled()
    assert not page.next_button.isEnabled()

    qtbot.mouseClick(page.prev_button, Qt.MouseButton.LeftButton)
    qtbot.waitUntil(lambda: page.current_page == 2, timeout=1000)
    assert page.page_label.text() == "Page 2 of 3"
    assert _page_button(page, 2).isChecked()


def test_reports_page_collapses_large_page_ranges_with_ellipsis(qtbot, tmp_path: Path) -> None:
    db_file = tmp_path / "reports.db"
    _seed_records(db_file, config.PAGE_SIZE * 10)

    page = ReportsPage(db_path=db_file)
    qtbot.addWidget(page)
    page.show()
    qtbot.waitExposed(page)
    qtbot.waitUntil(lambda: page.model.rowCount() == config.PAGE_SIZE, timeout=1000)

    assert page.page_label.text() == "Page 1 of 10"
    assert _page_strip_texts(page) == ["1", "2", "3", "4", "5", "6", "...", "10"]

    qtbot.mouseClick(_page_button(page, 6), Qt.MouseButton.LeftButton)
    qtbot.waitUntil(lambda: page.current_page == 6, timeout=1000)
    assert page.page_label.text() == "Page 6 of 10"
    assert _page_strip_texts(page) == ["1", "...", "4", "5", "6", "7", "8", "...", "10"]
    assert _page_button(page, 6).isChecked()

    qtbot.mouseClick(_page_button(page, 10), Qt.MouseButton.LeftButton)
    qtbot.waitUntil(lambda: page.current_page == 10, timeout=1000)
    assert page.page_label.text() == "Page 10 of 10"
    assert _page_strip_texts(page) == ["1", "...", "5", "6", "7", "8", "9", "10"]
    assert _page_button(page, 10).isChecked()


def test_reports_page_skips_auto_refresh_while_user_has_manual_position(
    qtbot, tmp_path: Path
) -> None:
    db_file = tmp_path / "reports.db"
    _insert_record(
        db_file,
        start_ts=1_700_000_000,
        end_ts=1_700_000_060,
        download_bps=5_000_000.0,
        upload_bps=1_000_000.0,
    )
    _insert_record(
        db_file,
        start_ts=1_700_000_120,
        end_ts=1_700_000_180,
        download_bps=6_000_000.0,
        upload_bps=1_500_000.0,
    )

    page = ReportsPage(db_path=db_file)
    qtbot.addWidget(page)
    page.show()
    qtbot.waitExposed(page)
    qtbot.waitUntil(lambda: page.model.rowCount() == 2, timeout=1000)

    assert page.model.data(page.model.index(0, 2), Qt.ItemDataRole.DisplayRole) == "6.00 MB/s"
    page.table.selectRow(1)
    qtbot.waitUntil(lambda: page.table.selectionModel().hasSelection(), timeout=1000)

    _insert_record(
        db_file,
        start_ts=1_700_000_240,
        end_ts=1_700_000_300,
        download_bps=7_000_000.0,
        upload_bps=2_000_000.0,
    )

    page.on_segment_closed()

    assert page.model.rowCount() == 2
    assert page.model.data(page.model.index(0, 2), Qt.ItemDataRole.DisplayRole) == "6.00 MB/s"
    assert page.count_label.text() == "2 records"


def test_reports_page_keeps_current_page_across_tab_switches(qtbot, tmp_path: Path) -> None:
    db_file = tmp_path / "reports.db"
    _seed_records(db_file, 50)

    window = MainWindow(reports_db_path=db_file)
    qtbot.addWidget(window)
    window.show()
    qtbot.waitExposed(window)

    window.tabs.setCurrentWidget(window.reports_page)
    qtbot.waitUntil(lambda: window.reports_page.model.rowCount() == config.PAGE_SIZE, timeout=1000)

    qtbot.mouseClick(window.reports_page.next_button, Qt.MouseButton.LeftButton)
    qtbot.waitUntil(lambda: window.reports_page.current_page == 2, timeout=1000)
    assert window.reports_page.page_label.text() == "Page 2 of 3"

    window.tabs.setCurrentWidget(window.live_view)
    window.tabs.setCurrentWidget(window.reports_page)

    assert window.reports_page.current_page == 2
    assert window.reports_page.page_label.text() == "Page 2 of 3"
    assert window.reports_page.model.rowCount() == config.PAGE_SIZE


def test_reports_page_filter_change_resets_to_first_page(qtbot, tmp_path: Path) -> None:
    db_file = tmp_path / "reports.db"
    _seed_records(db_file, 50)

    page = ReportsPage(db_path=db_file)
    qtbot.addWidget(page)
    page.show()
    qtbot.waitExposed(page)
    qtbot.waitUntil(lambda: page.model.rowCount() == config.PAGE_SIZE, timeout=1000)

    qtbot.mouseClick(page.next_button, Qt.MouseButton.LeftButton)
    qtbot.waitUntil(lambda: page.current_page == 2, timeout=1000)
    qtbot.mouseClick(page.next_button, Qt.MouseButton.LeftButton)
    qtbot.waitUntil(lambda: page.current_page == 3, timeout=1000)

    last_record_point = BASE_TS + (49 * RECORD_SPACING_SECS) + 1
    page.set_filter(
        ReportFilter(
            range_start_ts=last_record_point,
            range_end_ts=last_record_point,
        )
    )

    qtbot.waitUntil(lambda: page.current_page == 1, timeout=1000)
    assert page.model.rowCount() == 1
    assert page.page_label.text() == "Page 1 of 1"
    assert page.count_label.text() == "1 record"
    assert not page.prev_button.isEnabled()
    assert not page.next_button.isEnabled()


def test_reports_page_apply_date_filter_reloads_table_and_resets_page(
    qtbot, tmp_path: Path, monkeypatch
) -> None:
    db_file = tmp_path / "reports.db"
    _seed_filter_records(db_file)
    monkeypatch.setattr(filter_builder_module, "_local_zone", lambda: ZoneInfo("UTC"))

    page = ReportsPage(db_path=db_file)
    qtbot.addWidget(page)
    page.show()
    qtbot.waitExposed(page)
    qtbot.waitUntil(lambda: page.model.rowCount() == config.PAGE_SIZE, timeout=1000)

    assert page.count_label.text() == "25 records"

    qtbot.mouseClick(page.next_button, Qt.MouseButton.LeftButton)
    qtbot.waitUntil(lambda: page.current_page == 2, timeout=1000)
    assert page.model.rowCount() == 5
    assert page.page_label.text() == "Page 2 of 2"

    page.filter_panel.mode_combo.setCurrentText("Date")
    page.filter_panel.primary_date_edit.setDate(QDate(2026, 7, 7))
    qtbot.mouseClick(page.filter_panel.apply_button, Qt.MouseButton.LeftButton)

    qtbot.waitUntil(
        lambda: page.current_page == 1 and page.count_label.text() == "20 records",
        timeout=1000,
    )
    assert page.model.rowCount() == config.PAGE_SIZE
    assert page.page_label.text() == "Page 1 of 1"
    assert all(
        page.model.data(page.model.index(row, 0), Qt.ItemDataRole.DisplayRole) == "2026-07-07"
        for row in range(page.model.rowCount())
    )
    assert page.filter_status_label.text() == "Filtered: 2026-07-07"


def test_reports_page_reset_returns_to_no_filter_page_one(
    qtbot, tmp_path: Path, monkeypatch
) -> None:
    db_file = tmp_path / "reports.db"
    _seed_filter_records(db_file)
    monkeypatch.setattr(filter_builder_module, "_local_zone", lambda: ZoneInfo("UTC"))

    page = ReportsPage(db_path=db_file)
    qtbot.addWidget(page)
    page.show()
    qtbot.waitExposed(page)
    qtbot.waitUntil(lambda: page.model.rowCount() == config.PAGE_SIZE, timeout=1000)

    qtbot.mouseClick(page.next_button, Qt.MouseButton.LeftButton)
    qtbot.waitUntil(lambda: page.current_page == 2, timeout=1000)

    page.filter_panel.mode_combo.setCurrentText("Date")
    page.filter_panel.primary_date_edit.setDate(QDate(2026, 7, 7))
    qtbot.mouseClick(page.filter_panel.apply_button, Qt.MouseButton.LeftButton)
    qtbot.waitUntil(
        lambda: page.current_page == 1 and page.count_label.text() == "20 records",
        timeout=1000,
    )

    qtbot.mouseClick(page.filter_panel.reset_button, Qt.MouseButton.LeftButton)

    qtbot.waitUntil(
        lambda: page.current_page == 1 and page.count_label.text() == "25 records",
        timeout=1000,
    )
    assert page.model.rowCount() == config.PAGE_SIZE
    assert page.page_label.text() == "Page 1 of 2"
    assert page.filter_status_label.text() == "Showing all records"


def test_reports_page_future_date_filter_shows_clean_empty_state(
    qtbot, tmp_path: Path, monkeypatch
) -> None:
    db_file = tmp_path / "reports.db"
    _seed_filter_records(db_file)
    monkeypatch.setattr(filter_builder_module, "_local_zone", lambda: ZoneInfo("UTC"))

    page = ReportsPage(db_path=db_file)
    qtbot.addWidget(page)
    page.show()
    qtbot.waitExposed(page)
    qtbot.waitUntil(lambda: page.model.rowCount() == config.PAGE_SIZE, timeout=1000)

    page.filter_panel.mode_combo.setCurrentText("Date")
    page.filter_panel.primary_date_edit.setDate(QDate(2035, 1, 1))
    qtbot.mouseClick(page.filter_panel.apply_button, Qt.MouseButton.LeftButton)

    qtbot.waitUntil(lambda: page.count_label.text() == "0 records", timeout=1000)
    assert page.model.rowCount() == 0
    assert page.empty_state_label.isVisible()
    assert not page.table.isVisible()
    assert page.page_label.text() == "Page 1 of 1"
    assert page.filter_status_label.text() == "Filtered: 2035-01-01"


def test_reports_page_date_time_filter_is_inclusive_at_record_boundaries(
    qtbot, tmp_path: Path, monkeypatch
) -> None:
    db_file = tmp_path / "reports.db"
    start_ts = int(datetime(2026, 7, 7, 9, 15, tzinfo=UTC).timestamp())
    _insert_record(
        db_file,
        start_ts=start_ts,
        end_ts=int(datetime(2026, 7, 7, 9, 45, tzinfo=UTC).timestamp()),
        download_bps=5_000_000.0,
        upload_bps=1_000_000.0,
    )
    monkeypatch.setattr(filter_builder_module, "_local_zone", lambda: ZoneInfo("UTC"))

    page = ReportsPage(db_path=db_file)
    qtbot.addWidget(page)
    page.show()
    qtbot.waitExposed(page)
    qtbot.waitUntil(lambda: page.count_label.text() == "1 record", timeout=1000)

    page.filter_panel.mode_combo.setCurrentText("Date + Time")
    page.filter_panel.primary_date_edit.setDate(QDate(2026, 7, 7))
    page.filter_panel.primary_time_edit.setTime(QTime(9, 15))
    qtbot.mouseClick(page.filter_panel.apply_button, Qt.MouseButton.LeftButton)

    qtbot.waitUntil(lambda: page.count_label.text() == "1 record", timeout=1000)
    assert page.model.rowCount() == 1
    assert page.filter_status_label.text() == "Filtered: 2026-07-07 at 9:15 AM"

    page.filter_panel.primary_time_edit.setTime(QTime(9, 45))
    qtbot.mouseClick(page.filter_panel.apply_button, Qt.MouseButton.LeftButton)

    qtbot.waitUntil(lambda: page.count_label.text() == "1 record", timeout=1000)
    assert page.model.rowCount() == 1
    assert page.filter_status_label.text() == "Filtered: 2026-07-07 at 9:45 AM"


def test_reports_page_filter_state_persists_across_tabs_but_not_restart(
    qtbot, tmp_path: Path, monkeypatch
) -> None:
    db_file = tmp_path / "reports.db"
    _seed_filter_records(db_file)
    monkeypatch.setattr(filter_builder_module, "_local_zone", lambda: ZoneInfo("UTC"))

    window = MainWindow(reports_db_path=db_file)
    qtbot.addWidget(window)
    window.show()
    qtbot.waitExposed(window)

    window.tabs.setCurrentWidget(window.reports_page)
    qtbot.waitUntil(
        lambda: window.reports_page.count_label.text() == "25 records",
        timeout=1000,
    )

    window.reports_page.filter_panel.mode_combo.setCurrentText("Date + Time")
    window.reports_page.filter_panel.primary_date_edit.setDate(QDate(2026, 7, 7))
    window.reports_page.filter_panel.primary_time_edit.setTime(QTime(12, 5))
    qtbot.mouseClick(window.reports_page.filter_panel.apply_button, Qt.MouseButton.LeftButton)

    qtbot.waitUntil(
        lambda: window.reports_page.count_label.text() == "1 record",
        timeout=1000,
    )
    assert window.reports_page.filter_status_label.text() == "Filtered: 2026-07-07 at 12:05 PM"

    window.tabs.setCurrentWidget(window.live_view)
    window.tabs.setCurrentWidget(window.reports_page)

    assert window.reports_page.filter_panel.mode_combo.currentText() == "Date + Time"
    assert window.reports_page.filter_panel.primary_date_edit.date() == QDate(2026, 7, 7)
    assert window.reports_page.filter_panel.primary_time_edit.time() == QTime(12, 5)
    assert window.reports_page.count_label.text() == "1 record"
    assert window.reports_page.filter_status_label.text() == "Filtered: 2026-07-07 at 12:05 PM"

    restarted_window = MainWindow(reports_db_path=db_file)
    qtbot.addWidget(restarted_window)
    restarted_window.show()
    qtbot.waitExposed(restarted_window)
    restarted_window.tabs.setCurrentWidget(restarted_window.reports_page)

    qtbot.waitUntil(
        lambda: restarted_window.reports_page.count_label.text() == "25 records",
        timeout=1000,
    )
    assert restarted_window.reports_page.filter_panel.mode_combo.currentText() == "Date"
    assert restarted_window.reports_page.filter_status_label.text() == "Showing all records"


def test_reports_page_export_dialog_scope_drives_default_names(
    qtbot, tmp_path: Path, monkeypatch
) -> None:
    db_file = tmp_path / "reports.db"
    _seed_filter_records(db_file)
    monkeypatch.setattr(filter_builder_module, "_local_zone", lambda: ZoneInfo("UTC"))
    monkeypatch.setattr(reports_page_module, "_local_zone", lambda: ZoneInfo("UTC"))

    window = _show_reports_window(qtbot, db_file)
    qtbot.waitUntil(lambda: window.reports_page.count_label.text() == "25 records", timeout=1000)

    captured: dict[str, str] = {}

    def fake_get_save_file_name(
        _parent, _title: str, directory: str, _file_filter: str
    ) -> tuple[str, str]:
        captured["directory"] = directory
        return "", ""

    monkeypatch.setattr(QFileDialog, "getSaveFileName", fake_get_save_file_name)

    # Default dialog scope is today's records, saved to the Downloads folder.
    _accept_export_dialog(monkeypatch)
    qtbot.mouseClick(window.reports_page.filter_panel.export_button, Qt.MouseButton.LeftButton)
    today_token = date.today().isoformat()
    assert Path(captured["directory"]).name == f"Speedlog-Report-{today_token}_{today_token}.pdf"
    assert Path(captured["directory"]).parent == reports_page_module._downloads_dir()

    _accept_export_dialog(monkeypatch, lambda dialog: _select_scope(dialog, "All records"))
    qtbot.mouseClick(window.reports_page.filter_panel.export_button, Qt.MouseButton.LeftButton)
    assert Path(captured["directory"]).name == "Speedlog-Report-all.pdf"

    def pick_date_range(dialog: ExportOptionsDialog) -> None:
        _select_scope(dialog, "Date Range")
        dialog.primary_date_edit.setDate(QDate(2026, 7, 6))
        dialog.end_date_edit.setDate(QDate(2026, 7, 7))

    _accept_export_dialog(monkeypatch, pick_date_range)
    qtbot.mouseClick(window.reports_page.filter_panel.export_button, Qt.MouseButton.LeftButton)
    assert Path(captured["directory"]).name == "Speedlog-Report-2026-07-06_2026-07-07.pdf"


def test_reports_page_downloads_dir_falls_back_to_home(monkeypatch) -> None:
    monkeypatch.setattr(
        reports_page_module.QStandardPaths,
        "writableLocation",
        staticmethod(lambda _location: ""),
    )
    assert reports_page_module._downloads_dir() == Path.home()


def test_reports_page_export_dialog_cancel_aborts_export(
    qtbot, tmp_path: Path, monkeypatch
) -> None:
    db_file = tmp_path / "reports.db"
    _seed_records(db_file, 1)

    window = _show_reports_window(qtbot, db_file)
    qtbot.waitUntil(lambda: window.reports_page.count_label.text() == "1 record", timeout=1000)

    save_dialog_calls: list[str] = []
    monkeypatch.setattr(
        QFileDialog,
        "getSaveFileName",
        lambda *_args, **_kwargs: save_dialog_calls.append("called") or ("", ""),
    )
    monkeypatch.setattr(ExportOptionsDialog, "exec", lambda _self: QDialog.DialogCode.Rejected)

    qtbot.mouseClick(window.reports_page.filter_panel.export_button, Qt.MouseButton.LeftButton)

    assert save_dialog_calls == []
    assert window.reports_page._active_export is None
    assert window.reports_page.filter_panel.export_button.isEnabled()


def test_reports_page_export_uses_dialog_time_range_scope(
    qtbot, tmp_path: Path, monkeypatch
) -> None:
    db_file = tmp_path / "reports.db"
    _seed_filter_records(db_file)
    monkeypatch.setattr(filter_builder_module, "_local_zone", lambda: ZoneInfo("UTC"))
    monkeypatch.setattr(reports_page_module, "_local_zone", lambda: ZoneInfo("UTC"))

    window = _show_reports_window(qtbot, db_file)
    qtbot.waitUntil(lambda: window.reports_page.count_label.text() == "25 records", timeout=1000)

    captured: dict[str, object] = {}

    def fake_fetch_all_records(self, report_filter: ReportFilter):
        captured["report_filter"] = report_filter
        return iter([])

    def fake_generate_report(records, filter_label: str, _full_name: str, out_path: Path) -> None:
        list(records)
        captured["filter_label"] = filter_label
        out_path.write_text("pdf", encoding="utf-8")

    monkeypatch.setattr(
        QFileDialog,
        "getSaveFileName",
        lambda *_args, **_kwargs: (
            str(tmp_path / "scoped-report.pdf"),
            reports_page_module.EXPORT_FILE_FILTER,
        ),
    )
    monkeypatch.setattr(reports_page_module.Repository, "fetch_all_records", fake_fetch_all_records)
    monkeypatch.setattr(reports_page_module, "generate_report", fake_generate_report)
    monkeypatch.setattr(reports_page_module, "get_full_name", lambda: "Test User")

    def pick_time_range(dialog: ExportOptionsDialog) -> None:
        _select_scope(dialog, "Date + Time Range")
        dialog.primary_date_edit.setDate(QDate(2026, 7, 7))
        dialog.start_time_edit.setTime(QTime(12, 0))
        dialog.end_time_edit.setTime(QTime(13, 0))

    _accept_export_dialog(monkeypatch, pick_time_range)
    qtbot.mouseClick(window.reports_page.filter_panel.export_button, Qt.MouseButton.LeftButton)
    qtbot.waitUntil(lambda: "filter_label" in captured, timeout=1000)
    qtbot.waitUntil(
        lambda: window.reports_page.filter_panel.export_button.isEnabled(),
        timeout=1000,
    )

    report_filter = captured["report_filter"]
    assert isinstance(report_filter, ReportFilter)
    assert report_filter.range_start_ts == int(datetime(2026, 7, 7, 12, 0, tzinfo=UTC).timestamp())
    assert report_filter.range_end_ts == int(datetime(2026, 7, 7, 13, 0, tzinfo=UTC).timestamp())
    assert captured["filter_label"] == "2026-07-07, 12:00 PM – 1:00 PM"


def test_reports_page_export_runs_in_worker_and_uses_full_filtered_set(
    qtbot, tmp_path: Path, monkeypatch
) -> None:
    db_file = tmp_path / "reports.db"
    _seed_records(db_file, 25)

    window = _show_reports_window(qtbot, db_file)
    qtbot.waitUntil(lambda: window.reports_page.model.rowCount() == config.PAGE_SIZE, timeout=1000)

    qtbot.mouseClick(window.reports_page.next_button, Qt.MouseButton.LeftButton)
    qtbot.waitUntil(lambda: window.reports_page.current_page == 2, timeout=1000)
    assert window.reports_page.model.rowCount() == 5

    expected_records = [
        SpeedRecord(
            session_id=1,
            start_ts=BASE_TS + index,
            end_ts=BASE_TS + index + RECORD_DURATION_SECS,
            download_bps=1_000_000.0 + index,
            upload_bps=500_000.0 + index,
        )
        for index in range(25)
    ]
    captured: dict[str, object] = {}
    started = threading.Event()
    release = threading.Event()

    def fake_fetch_all_records(self, report_filter: ReportFilter):
        captured["report_filter"] = report_filter
        return iter(expected_records)

    def fake_generate_report(records, filter_label: str, full_name: str, out_path: Path) -> None:
        captured["record_count"] = sum(1 for _ in records)
        captured["filter_label"] = filter_label
        captured["full_name"] = full_name
        captured["out_path"] = out_path
        started.set()
        release.wait(timeout=2)
        out_path.write_text("pdf", encoding="utf-8")

    monkeypatch.setattr(
        QFileDialog,
        "getSaveFileName",
        lambda *_args, **_kwargs: (
            str(tmp_path / "full-report"),
            reports_page_module.EXPORT_FILE_FILTER,
        ),
    )
    monkeypatch.setattr(reports_page_module.Repository, "fetch_all_records", fake_fetch_all_records)
    monkeypatch.setattr(reports_page_module, "generate_report", fake_generate_report)
    monkeypatch.setattr(reports_page_module, "get_full_name", lambda: "Test User")
    _accept_export_dialog(monkeypatch, lambda dialog: _select_scope(dialog, "All records"))

    succeeded_paths: list[str] = []
    window.reports_page.export_succeeded.connect(succeeded_paths.append)

    qtbot.mouseClick(window.reports_page.filter_panel.export_button, Qt.MouseButton.LeftButton)

    qtbot.waitUntil(started.is_set, timeout=1000)
    assert not window.reports_page.filter_panel.export_button.isEnabled()
    assert window.statusBar().currentMessage() == reports_page_module.EXPORT_BUSY_TEXT

    release.set()
    qtbot.waitUntil(
        lambda: window.reports_page.filter_panel.export_button.isEnabled(),
        timeout=1000,
    )

    assert captured["record_count"] == 25
    report_filter = captured["report_filter"]
    assert isinstance(report_filter, ReportFilter)
    assert report_filter.range_start_ts is None
    assert report_filter.range_end_ts is None
    assert captured["filter_label"] == "All records"
    assert captured["full_name"] == "Test User"
    assert captured["out_path"] == tmp_path / "full-report.pdf"
    assert window.statusBar().currentMessage() == "Exported PDF to full-report.pdf"
    assert succeeded_paths == [str(tmp_path / "full-report.pdf")]

    reveal_button = window.findChild(
        QPushButton,
        reports_page_module.EXPORT_REVEAL_BUTTON_OBJECT_NAME,
    )
    assert reveal_button is not None
    assert reveal_button.isVisible()
    assert reveal_button.text() == reports_page_module.EXPORT_REVEAL_TEXT

    revealed: list[Path] = []
    monkeypatch.setattr(
        reports_page_module,
        "_reveal_exported_file",
        lambda path: revealed.append(path) or True,
    )
    qtbot.mouseClick(reveal_button, Qt.MouseButton.LeftButton)
    assert revealed == [tmp_path / "full-report.pdf"]


def test_reports_page_export_failure_shows_message_and_logs_traceback(
    qtbot, tmp_path: Path, monkeypatch, caplog
) -> None:
    db_file = tmp_path / "reports.db"
    _seed_records(db_file, 1)

    window = _show_reports_window(qtbot, db_file)
    qtbot.waitUntil(lambda: window.reports_page.count_label.text() == "1 record", timeout=1000)

    failures: list[tuple[str, str]] = []

    def fake_generate_report(records, _filter_label: str, _full_name: str, _out_path: Path) -> None:
        list(records)
        raise RuntimeError("boom")

    monkeypatch.setattr(
        QFileDialog,
        "getSaveFileName",
        lambda *_args, **_kwargs: (
            str(tmp_path / "broken-report.pdf"),
            reports_page_module.EXPORT_FILE_FILTER,
        ),
    )
    monkeypatch.setattr(reports_page_module, "generate_report", fake_generate_report)
    monkeypatch.setattr(reports_page_module, "get_full_name", lambda: "Test User")
    _accept_export_dialog(monkeypatch)
    monkeypatch.setattr(
        QMessageBox,
        "critical",
        lambda _parent, title, text: failures.append((title, text)),
    )

    succeeded_paths: list[str] = []
    window.reports_page.export_succeeded.connect(succeeded_paths.append)

    with caplog.at_level(logging.ERROR, logger=reports_page_module.__name__):
        qtbot.mouseClick(window.reports_page.filter_panel.export_button, Qt.MouseButton.LeftButton)
        qtbot.waitUntil(
            lambda: window.reports_page.filter_panel.export_button.isEnabled(),
            timeout=1000,
        )

    assert failures == [
        (
            reports_page_module.EXPORT_FAILURE_TITLE,
            reports_page_module.EXPORT_FAILURE_TEXT,
        )
    ]
    assert window.statusBar().currentMessage() == reports_page_module.EXPORT_FAILURE_STATUS_TEXT

    reveal_button = window.findChild(
        QPushButton,
        reports_page_module.EXPORT_REVEAL_BUTTON_OBJECT_NAME,
    )
    assert reveal_button is None or not reveal_button.isVisible()
    assert any(
        "Failed to export PDF report to" in record.getMessage() and record.exc_info is not None
        for record in caplog.records
    )
    assert succeeded_paths == []
