"""Entry point: QApplication bootstrap (NST-401).

Order: logging → single-instance guard → DB migrate → styles/icon →
CollectorService (created here; started with the tray wiring in NST-402) →
main window → exec(). Quitting is tray-driven (NST-403/404); closing the
window only hides it.
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

from PySide6.QtCore import QObject, Signal
from PySide6.QtNetwork import QLocalServer, QLocalSocket
from PySide6.QtWidgets import QApplication

from app import config, logging_setup
from app.collector.service import CollectorService
from app.data import db
from app.ui.main_window import MainWindow, app_icon

logger = logging.getLogger(__name__)

_STYLES_PATH = Path(__file__).parent / "ui" / "styles.qss"


class SingleInstanceGuard(QObject):
    """First launch listens on a QLocalServer; later launches ping it and exit.

    ``activate_requested`` fires (on the first instance) whenever a second
    launch connects, so the existing window can be brought to front.
    """

    activate_requested = Signal()

    def __init__(self, key: str = config.SINGLE_INSTANCE_KEY, parent: QObject | None = None):
        super().__init__(parent)
        self._key = key
        self._server: QLocalServer | None = None

    def try_acquire(self) -> bool:
        """Return True if this process is the single instance, else notify the first one."""
        socket = QLocalSocket()
        socket.connectToServer(self._key)
        if socket.waitForConnected(config.SINGLE_INSTANCE_TIMEOUT_MS):
            socket.disconnectFromServer()
            return False
        # No live instance: remove any socket file left by a crash, then listen.
        QLocalServer.removeServer(self._key)
        self._server = QLocalServer(self)
        self._server.newConnection.connect(self._on_new_connection)
        if not self._server.listen(self._key):
            logger.warning(
                "Single-instance server failed to listen (%s); continuing without guard",
                self._server.errorString(),
            )
        return True

    def release(self) -> None:
        """Close the local server (tests and shutdown)."""
        if self._server is not None:
            self._server.close()
            self._server = None
        QLocalServer.removeServer(self._key)

    def _on_new_connection(self) -> None:
        assert self._server is not None
        socket = self._server.nextPendingConnection()
        if socket is not None:
            socket.disconnected.connect(socket.deleteLater)
            socket.close()
        logger.info("Second launch detected; activating existing window")
        self.activate_requested.emit()


def load_styles() -> str:
    """Read the application stylesheet from ui/styles.qss."""
    return _STYLES_PATH.read_text(encoding="utf-8")


def configure_application(app: QApplication) -> None:
    """App-wide setup: name, keep-running-in-tray policy, stylesheet, icon."""
    app.setApplicationName(config.APP_NAME)
    QApplication.setQuitOnLastWindowClosed(False)
    app.setStyleSheet(load_styles())
    app.setWindowIcon(app_icon())


def migrate_database() -> None:
    """Apply pending schema migrations on a short-lived main-thread connection."""
    conn = db.get_connection(config.db_path())
    try:
        db.migrate(conn)
    finally:
        conn.close()


def main() -> int:
    """Start the Qt application."""
    logging_setup.configure(debug=False)
    app = QApplication(sys.argv)

    guard = SingleInstanceGuard()
    if not guard.try_acquire():
        logger.info("Speedlog is already running; asked it to activate and exiting")
        return 0

    configure_application(app)
    migrate_database()

    window = MainWindow()
    guard.activate_requested.connect(window.bring_to_front)

    # Created here per NST-401; started + tray-wired in NST-402.
    window.collector_service = CollectorService()

    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
