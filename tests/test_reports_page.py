"""Tests for the reports table model and page (NST-601/NST-602/NST-604/NST-605)."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QPushButton

import app.formatting as formatting_module
from app import config
from app.data import db
from app.data.models import ReportFilter, SpeedRecord
from app.data.repository import Repository
from app.ui.main_window import MainWindow
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
    assert page.title_label.text() == "Connection History"
    assert "move through pages" in page.subtitle_label.text()
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
