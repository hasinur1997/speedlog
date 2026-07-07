"""QAbstractTableModel over one page of report records (NST-601)."""

from __future__ import annotations

from datetime import UTC, datetime
from zoneinfo import ZoneInfo

from PySide6.QtCore import QAbstractTableModel, QModelIndex, Qt

from app.data.models import SpeedRecord
from app.formatting import format_speed

_HEADERS = ("Date", "Time", "Download", "Upload")


def _local_zone() -> ZoneInfo | None:
    """Best-effort local timezone; prefer a real ``ZoneInfo`` when available."""
    tzinfo = datetime.now().astimezone().tzinfo
    if isinstance(tzinfo, ZoneInfo):
        return tzinfo
    key = getattr(tzinfo, "key", None)
    if isinstance(key, str):
        return ZoneInfo(key)
    return None


def _local_datetime(ts: int) -> datetime:
    dt = datetime.fromtimestamp(ts, tz=UTC)
    local_zone = _local_zone()
    if local_zone is not None:
        return dt.astimezone(local_zone)
    return dt.astimezone()


def _format_date(ts: int) -> str:
    return _local_datetime(ts).strftime("%Y-%m-%d")


def _format_time(ts: int) -> str:
    return _local_datetime(ts).strftime("%I:%M %p").lstrip("0")


def _format_time_range(start_ts: int, end_ts: int) -> str:
    return f"{_format_time(start_ts)} – {_format_time(end_ts)}"


class ReportsTableModel(QAbstractTableModel):
    """Qt table model for one already-sorted page of :class:`SpeedRecord` rows."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._records: list[SpeedRecord] = []

    def rowCount(self, parent: QModelIndex | None = None) -> int:
        if parent is not None and parent.isValid():
            return 0
        return len(self._records)

    def columnCount(self, parent: QModelIndex | None = None) -> int:
        if parent is not None and parent.isValid():
            return 0
        return len(_HEADERS)

    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole) -> str | None:
        if not index.isValid():
            return None
        record = self._records[index.row()]
        column = index.column()

        if role == Qt.ItemDataRole.DisplayRole:
            if column == 0:
                return _format_date(record.start_ts)
            if column == 1:
                return _format_time_range(record.start_ts, record.end_ts)
            if column == 2:
                return format_speed(record.download_bps)
            if column == 3:
                return format_speed(record.upload_bps)
            return None

        if role == Qt.ItemDataRole.TextAlignmentRole:
            if column in (2, 3):
                return int(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            return int(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)

        return None

    def headerData(
        self,
        section: int,
        orientation: Qt.Orientation,
        role: int = Qt.ItemDataRole.DisplayRole,
    ) -> str | None:
        if role != Qt.ItemDataRole.DisplayRole:
            return None
        if orientation == Qt.Orientation.Horizontal and 0 <= section < len(_HEADERS):
            return _HEADERS[section]
        return None

    def flags(self, index: QModelIndex) -> Qt.ItemFlag:
        if not index.isValid():
            return Qt.ItemFlag.NoItemFlags
        return Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable

    def set_page(self, records: list[SpeedRecord]) -> None:
        """Replace the currently displayed page of records."""
        self.beginResetModel()
        self._records = list(records)
        self.endResetModel()
