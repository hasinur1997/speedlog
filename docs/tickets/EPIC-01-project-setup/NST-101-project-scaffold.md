# NST-101 — Project scaffold, virtualenv, dependencies

- **Epic:** EPIC-01 Project Setup
- **Type:** Task
- **Priority:** P1
- **Estimate:** S
- **Status:** DONE
- **Depends on:** —

## Description
Create the repository skeleton exactly as defined in architecture-context.md
("Package layout"), with a runnable entry point and pinned dependencies.

## Acceptance criteria
- [x] Directory tree matches architecture-context.md (empty modules with docstrings OK)
- [x] `requirements.txt`: PySide6, psutil, reportlab (pinned versions)
- [x] `requirements-dev.txt`: pytest, pytest-qt, ruff, black, pyinstaller
- [x] `python -m app.main` opens an empty QApplication window and exits cleanly on close
- [x] `README.md` with setup instructions (venv, install, run, test)
- [x] `ruff check .` and `black --check .` pass; `pytest -q` runs (0 tests is fine)
- [x] `.gitignore` for Python/Qt/macOS artifacts

## Technical notes
Python 3.11+. Keep main.py minimal — real bootstrap comes in NST-401.

## Test plan
Smoke only: import test that `app` package imports.

## Implementation notes (fill after DONE)
- Completed 2026-07-06.
- Full package tree from architecture-context.md created under `app/` — all modules are
  docstring-only stubs except `main.py` (minimal QApplication + empty QMainWindow) and
  `__init__.py` (`__version__ = "0.1.0"`).
- Python 3.12 used (3.11 not installed on this machine; `requires-python = ">=3.11"` kept).
  Venv at `.venv/`.
- Pinned versions: PySide6 6.11.1, psutil 7.2.2, reportlab 5.0.0; dev: pytest 9.1.1,
  pytest-qt 4.5.0, ruff 0.15.20, black 26.5.1, pyinstaller 6.21.0.
  `requirements-dev.txt` includes `-r requirements.txt`.
- Added `pyproject.toml` with black (line 100), ruff (E, F, I, UP, B, py311) and pytest
  config — tool config only, packaging metadata deferred to NST-902.
- Smoke test `tests/test_import.py` passes; `ruff check .`, `black --check .` clean.
- Verified `python -m app.main` opens a window and returns exit code 0 on close
  (driven via a QTimer-triggered quit).
- Note for next tickets: black warns it formats for py3.15 by default under Python 3.12;
  harmless, but `target-version` can be set if it ever bites.
