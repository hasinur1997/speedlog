"""Entry point: QApplication bootstrap.

Minimal for NST-101 — the real bootstrap (tray, collector wiring) lands in NST-401.
"""

import sys

from PySide6.QtWidgets import QApplication, QMainWindow

from speedlog import config


def main() -> int:
    """Start the Qt application with an empty main window."""
    app = QApplication(sys.argv)
    window = QMainWindow()
    window.setWindowTitle(config.APP_NAME)
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
