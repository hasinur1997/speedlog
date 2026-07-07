"""QAbstractTableModel over one page of report records (NST-601)."""

from __future__ import annotations

from PySide6.QtCore import QAbstractTableModel, QModelIndex, Qt

from app.data.models import SpeedRecord
from app.formatting import format_date, format_speed, format_time_range

_HEADERS = ("Date", "Time", "Download", "Upload")


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
                return format_date(record.start_ts)
            if column == 1:
                return format_time_range(record.start_ts, record.end_ts)
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
