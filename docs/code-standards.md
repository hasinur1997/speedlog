# Code Standards — Speedlog

## Language & tooling
- Python 3.11+. Type hints REQUIRED on all public functions, methods, dataclasses.
- Formatter: `black` (line length 100). Linter: `ruff` (rules: E, F, I, UP, B).
- Imports sorted by ruff/isort. No wildcard imports.
- Dependency pinning in `requirements.txt` (exact versions) + `requirements-dev.txt`.

## Project conventions
- PySide6 only. Never import from PyQt5/PyQt6 (licensing). Signal syntax: `Signal(...)`,
  `Slot(...)` from `PySide6.QtCore`.
- All SQL lives in `data/repository.py`. No SQL strings anywhere else. Always
  parameterized queries (`?` / named params). String-formatted SQL is forbidden.
- All tunable numbers (sample interval, tolerance, hysteresis, page size, colors, paths)
  live in `config.py` as UPPER_CASE constants. No magic numbers in logic code.
- Timestamps: UTC epoch `int` everywhere internally. Local-time conversion and
  formatting happen only in `ui/` and `export/`. Use `zoneinfo`, never manual offsets.
- Speed values: bytes/sec `float` internally. Formatting helper
  `format_speed(bps) -> str` in one shared module; used by tray, table, PDF.
- Dataclasses for models (`SpeedRecord`, `Session`, `ReportFilter`). No dict-passing
  between layers.

## Qt rules
- No widget access from non-main threads. Collector communicates via Signals only.
- Long operations (PDF generation for large ranges) run in a worker, UI shows busy state.
- Every `QThread` has a clean `stop()` with a join timeout; no `terminate()`.
- Object names set for testability: `setObjectName("reportsTable")` etc.

## Error handling & logging
- `logging_setup.py` configures rotating file log at
  `~/Library/Logs/Speedlog/app.log` (5 MB × 3) + console in dev.
- Never bare `except:`. Catch specific exceptions; log with `logger.exception`.
- Collector loop must never die silently: top-level try/except per tick, log and continue.
- DB writes wrapped in transactions; failures logged, sample dropped, loop continues.

## Testing (pytest)
- Every ticket that adds logic ships unit tests in the same PR/commit.
- Pure-logic modules (smoother, segmenter, filter→query builder, formatters) must have
  ≥ 90% branch coverage — they are the product.
- Segmenter tests use synthetic sample streams (steady, ramp, spike, flap around band edge)
  and assert exact segment boundaries.
- DB tests use `:memory:` or tmp_path SQLite.
- UI logic tested via `pytest-qt` (`qtbot`) for: table model row count/formatting,
  pagination math, filter panel → ReportFilter object.
- No network access in tests. psutil is mocked/faked behind a `SamplerSource` interface.

## Git
- Conventional commits: `feat:`, `fix:`, `test:`, `docs:`, `refactor:`, `chore:`.
- One ticket = one branch `ticket/NST-XXX-short-name` = one focused commit series.
- Commit message body references the ticket ID.

## Definition of Done (applies to every ticket)
1. Acceptance criteria in the ticket all pass.
2. Tests written and green (`pytest -q`), lint clean (`ruff check .`, `black --check .`).
3. No TODOs left without a ticket reference.
4. `docs/progress-tracker.md` updated (status + date + notes).
5. If behavior/architecture changed: relevant docs file updated in the same commit.
