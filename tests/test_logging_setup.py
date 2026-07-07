"""Tests for speedlog.logging_setup (NST-103)."""

from __future__ import annotations

import logging
import re
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

import pytest

from speedlog import logging_setup


@pytest.fixture(autouse=True)
def clean_logging_state(monkeypatch: pytest.MonkeyPatch) -> None:
    root_logger = logging.getLogger()
    original_handlers = root_logger.handlers[:]
    original_level = root_logger.level
    original_excepthook = sys.excepthook

    monkeypatch.delenv("NST_DEBUG", raising=False)

    yield

    sys.excepthook = original_excepthook
    root_logger.setLevel(original_level)
    for handler in root_logger.handlers[:]:
        if handler not in original_handlers:
            root_logger.removeHandler(handler)
            handler.close()


def _configured_handler(name: str) -> logging.Handler | None:
    root_logger = logging.getLogger()
    for handler in root_logger.handlers:
        if handler.get_name() == name:
            return handler
    return None


def _flush_speedlog_handlers() -> None:
    for handler_name in (
        logging_setup._FILE_HANDLER_NAME,
        logging_setup._CONSOLE_HANDLER_NAME,
    ):
        handler = _configured_handler(handler_name)
        if handler is not None:
            handler.flush()


def test_configure_adds_rotating_file_handler_and_writes_records(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(logging_setup.config, "log_dir", lambda: tmp_path)

    logging_setup.configure(debug=False)

    file_handler = _configured_handler(logging_setup._FILE_HANDLER_NAME)
    assert isinstance(file_handler, RotatingFileHandler)
    assert Path(file_handler.baseFilename) == tmp_path / logging_setup.config.LOG_FILE_NAME
    assert file_handler.maxBytes == logging_setup.config.LOG_FILE_MAX_BYTES
    assert file_handler.backupCount == logging_setup.config.LOG_FILE_BACKUP_COUNT
    assert _configured_handler(logging_setup._CONSOLE_HANDLER_NAME) is None

    logger = logging.getLogger("speedlog.tests.logging_setup")
    logger.info("file handler writes records")
    _flush_speedlog_handlers()

    log_path = tmp_path / logging_setup.config.LOG_FILE_NAME
    assert log_path.is_file()
    content = log_path.read_text(encoding="utf-8")
    assert "file handler writes records" in content
    assert "INFO" in content
    assert "test_logging_setup" in content
    assert "MainThread" in content
    assert re.search(r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}", content, re.MULTILINE)


def test_configure_adds_console_handler_when_debug_enabled(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(logging_setup.config, "log_dir", lambda: tmp_path)

    logging_setup.configure(debug=True)

    console_handler = _configured_handler(logging_setup._CONSOLE_HANDLER_NAME)
    assert isinstance(console_handler, logging.StreamHandler)


def test_configure_uses_nst_debug_env_for_console(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(logging_setup.config, "log_dir", lambda: tmp_path)
    monkeypatch.setenv("NST_DEBUG", "1")

    logging_setup.configure(debug=False)

    console_handler = _configured_handler(logging_setup._CONSOLE_HANDLER_NAME)
    assert isinstance(console_handler, logging.StreamHandler)


def test_configure_is_idempotent(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(logging_setup.config, "log_dir", lambda: tmp_path)

    logging_setup.configure(debug=True)
    handlers_after_first_call = [
        handler.get_name()
        for handler in logging.getLogger().handlers
        if (handler.get_name() or "").startswith("speedlog.")
    ]
    excepthook = sys.excepthook

    logging_setup.configure(debug=True)

    handlers_after_second_call = [
        handler.get_name()
        for handler in logging.getLogger().handlers
        if (handler.get_name() or "").startswith("speedlog.")
    ]
    assert handlers_after_first_call == handlers_after_second_call
    assert handlers_after_second_call == [
        logging_setup._FILE_HANDLER_NAME,
        logging_setup._CONSOLE_HANDLER_NAME,
    ]
    assert sys.excepthook is excepthook


def test_configure_logs_uncaught_exceptions(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(logging_setup.config, "log_dir", lambda: tmp_path)

    logging_setup.configure(debug=False)

    try:
        raise RuntimeError("boom")
    except RuntimeError as exc:
        sys.excepthook(type(exc), exc, exc.__traceback__)

    _flush_speedlog_handlers()

    content = (tmp_path / logging_setup.config.LOG_FILE_NAME).read_text(encoding="utf-8")
    assert "Uncaught exception" in content
    assert "RuntimeError: boom" in content
