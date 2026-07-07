"""Main window shell: Live / Reports tabs, hide-on-close behavior (NST-401)."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QCloseEvent, QColor, QIcon, QPainter, QPixmap
from PySide6.QtWidgets import QLabel, QMainWindow, QTabWidget, QVBoxLayout, QWidget

from app import config
from app.ui.live_view import LiveView


def app_icon() -> QIcon:
    """Accent-colored icon painted at runtime; shared by app, window and (later) tray."""
    size = config.APP_ICON_SIZE
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(QColor(config.ACCENT_COLOR))
    radius = size / 4
    painter.drawRoundedRect(0, 0, size, size, radius, radius)
    painter.setPen(QColor(config.APP_ICON_GLYPH_COLOR))
    font = painter.font()
    font.setBold(True)
    font.setPixelSize(int(size * 0.6))
    painter.setFont(font)
    painter.drawText(pixmap.rect(), Qt.AlignmentFlag.AlignCenter, config.APP_ICON_GLYPH)
    painter.end()
    return QIcon(pixmap)


def _placeholder_tab(object_name: str, text: str) -> QWidget:
    tab = QWidget()
    tab.setObjectName(object_name)
    layout = QVBoxLayout(tab)
    label = QLabel(text, tab)
    label.setAlignment(Qt.AlignmentFlag.AlignCenter)
    layout.addWidget(label)
    return tab


class MainWindow(QMainWindow):
    """Application window: Live / Reports tabs; closing hides it (tracking continues)."""

    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("mainWindow")
        self.setWindowTitle(config.APP_NAME)
        self.setWindowIcon(app_icon())
        self.resize(config.MAIN_WINDOW_WIDTH, config.MAIN_WINDOW_HEIGHT)

        self.tabs = QTabWidget(self)
        self.tabs.setObjectName("mainTabs")
        self.live_view = LiveView(self.tabs)
        self.tabs.addTab(self.live_view, "Live")
        self.tabs.addTab(
            _placeholder_tab("reportsTab", "Reports coming soon (NST-601)"),
            "Reports",
        )
        self.setCentralWidget(self.tabs)

    def closeEvent(self, event: QCloseEvent) -> None:
        """Hide instead of closing — the app keeps tracking in the tray."""
        event.ignore()
        self.hide()

    def bring_to_front(self) -> None:
        """Show, un-minimize and focus the window (tray open / second-launch activation)."""
        self.show()
        self.setWindowState(self.windowState() & ~Qt.WindowState.WindowMinimized)
        self.raise_()
        self.activateWindow()
