"""Tests for the reports table model and page (NST-601)."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from PySide6.QtCore import Qt

import app.ui.reports.table_model as table_model_module
from app.data import db
from app.data.models import SpeedRecord
from app.data.repository import Repository
from app.ui.reports.reports_page import ReportsPage
from app.ui.reports.table_model import ReportsTableModel


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


def test_reports_table_model_exposes_headers_and_page_data(monkeypatch) -> None:
    monkeypatch.setattr(table_model_module, "_local_zone", lambda: ZoneInfo("UTC"))
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


def test_reports_page_shows_empty_state_and_auto_refreshes_top_page(qtbot, tmp_path: Path) -> None:
    db_file = tmp_path / "reports.db"
    page = ReportsPage(db_path=db_file)
    qtbot.addWidget(page)
    page.show()
    qtbot.waitExposed(page)

    assert page.model.rowCount() == 0
    assert page.empty_state_label.isVisible()
    assert not page.table.isVisible()

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
