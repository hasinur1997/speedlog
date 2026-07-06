"""Rotating file + console logging configuration (NST-103)."""

from __future__ import annotations

import logging
import os
import sys
from collections.abc import Callable
from logging.handlers import RotatingFileHandler
from types import TracebackType

from speedlog import config

_LOG_FILE_NAME = "app.log"
_MAX_LOG_BYTES = 5 * 1024 * 1024
_BACKUP_COUNT = 3
_LOG_FORMAT = "%(asctime)s %(levelname)s [%(module)s] [%(threadName)s] %(message)s"
_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"
_FILE_HANDLER_NAME = "speedlog.file"
_CONSOLE_HANDLER_NAME = "speedlog.console"

Excepthook = Callable[
    [type[BaseException], BaseException, TracebackType | None],
    object,
]


def configure(debug: bool) -> None:
    """Configure root logging once for file output and optional dev console output."""
    root_logger = logging.getLogger()
    if _find_handler(root_logger, _FILE_HANDLER_NAME) is not None:
        return

    formatter = logging.Formatter(fmt=_LOG_FORMAT, datefmt=_DATE_FORMAT)
    root_logger.setLevel(logging.DEBUG)

    file_handler = RotatingFileHandler(
        config.log_dir() / _LOG_FILE_NAME,
        maxBytes=_MAX_LOG_BYTES,
        backupCount=_BACKUP_COUNT,
        encoding="utf-8",
    )
    file_handler.set_name(_FILE_HANDLER_NAME)
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)
    root_logger.addHandler(file_handler)

    if _should_enable_console(debug):
        console_handler = logging.StreamHandler()
        console_handler.set_name(_CONSOLE_HANDLER_NAME)
        console_handler.setLevel(logging.DEBUG)
        console_handler.setFormatter(formatter)
        root_logger.addHandler(console_handler)

    previous_excepthook = sys.excepthook
    sys.excepthook = _build_excepthook(previous_excepthook)


def _build_excepthook(previous_excepthook: Excepthook) -> Excepthook:
    def log_uncaught_exception(
        exc_type: type[BaseException],
        exc_value: BaseException,
        exc_traceback: TracebackType | None,
    ) -> object:
        if issubclass(exc_type, KeyboardInterrupt):
            return previous_excepthook(exc_type, exc_value, exc_traceback)

        logging.getLogger(__name__).critical(
            "Uncaught exception",
            exc_info=(exc_type, exc_value, exc_traceback),
        )
        return None

    return log_uncaught_exception


def _find_handler(root_logger: logging.Logger, name: str) -> logging.Handler | None:
    for handler in root_logger.handlers:
        if handler.get_name() == name:
            return handler
    return None


def _should_enable_console(debug: bool) -> bool:
    return debug or os.environ.get("NST_DEBUG") == "1"
