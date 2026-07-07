# NST-103 — Logging setup

- **Epic:** EPIC-01 Project Setup
- **Type:** Task
- **Priority:** P2
- **Estimate:** S
- **Status:** DONE (2026-07-07)
- **Depends on:** NST-101

## Description
Central logging configuration: rotating file handler + console in dev.

## Acceptance criteria
- [x] `logging_setup.configure(debug: bool)` sets root logger once (idempotent)
- [x] Rotating file at `config.log_dir()/app.log`, 5 MB x 3 backups
- [x] Format includes timestamp, level, module, thread name
- [x] Console handler only when debug=True (or env NST_DEBUG=1)
- [x] Uncaught exceptions hooked (`sys.excepthook`) and logged

## Test plan
Unit test: configure with tmp log dir, emit records, assert file written and handler config.

## Implementation notes (fill after DONE)
- **Files touched:** `speedlog/config.py` (added logging constants), `speedlog/logging_setup.py`
  (implemented), `tests/test_logging_setup.py` (new), `pyproject.toml` (Black target
  version pinned to py311 so repo checks stay green under Python 3.12),
  `docs/progress-tracker.md` (status update).
- **Logging behavior:** `configure(debug: bool)` adds one named rotating file handler on the
  root logger writing to `config.log_dir() / config.LOG_FILE_NAME` with
  `config.LOG_FILE_MAX_BYTES` set to 5,000,000 bytes (5 MB) and
  `config.LOG_FILE_BACKUP_COUNT` set to 3. A named console handler is added only when
  `debug=True` or `NST_DEBUG=1`.
- **Idempotency:** Repeated calls detect the existing Speedlog file handler and return
  without adding duplicate handlers or replacing the installed `sys.excepthook`.
- **Exception hook:** Uncaught exceptions are logged at `CRITICAL` with traceback data;
  `KeyboardInterrupt` still falls through to the prior excepthook.
- **Tests:** 5 new unit tests cover file handler configuration, file output/format content,
  console enablement via `debug` and `NST_DEBUG`, idempotency, and uncaught exception
  logging. Assertions read the file name/rotation settings from `speedlog.config`.
  Verified with `pytest -q`, `ruff check .`, and `black --check .`.
