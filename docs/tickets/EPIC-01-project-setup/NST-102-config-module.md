# NST-102 — Config module & application constants

- **Epic:** EPIC-01 Project Setup
- **Type:** Task
- **Priority:** P1
- **Estimate:** S
- **Status:** DONE (2026-07-07)
- **Depends on:** NST-101

## Description
Single source of truth for all tunables and paths in `config.py`.

## Acceptance criteria
- [x] Constants: SAMPLE_INTERVAL=1.0, SMOOTH_WINDOW=5, BAND_TOLERANCE_PCT=0.10,
      BAND_TOLERANCE_FLOOR_BPS=250_000, HYSTERESIS_TICKS=5, MIN_SEGMENT_SECS=5,
      PAGE_SIZE=20, ACCENT_COLOR="#2E7CF6", APP_NAME="Speedlog"
- [x] `data_dir()` returns platform-correct app data dir (macOS:
      ~/Library/Application Support/Speedlog; Linux: XDG; Windows: %APPDATA%)
      and creates it if missing
- [x] `db_path()`, `log_dir()` helpers
- [x] No other module hardcodes these values

## Technical notes
Use `platform.system()` branching now so Linux/Windows support comes free later.

## Test plan
Unit tests for dir helpers (monkeypatched HOME/platform); constants importable.

## Implementation notes (fill after DONE)
- **Files touched:** `app/config.py` (implemented), `tests/test_config.py` (new),
  `app/main.py` (window title now uses `config.APP_NAME` instead of a hardcoded string).
- **Path decisions:**
  - `data_dir()`: macOS `~/Library/Application Support/Speedlog`; Linux
    `$XDG_DATA_HOME/Speedlog` (fallback `~/.local/share`); Windows `%APPDATA%\Speedlog`
    (fallback `~/AppData/Roaming`). Created with `mkdir(parents=True, exist_ok=True)`.
  - `log_dir()`: macOS `~/Library/Logs/Speedlog` (matches code-standards logging path);
    Linux `$XDG_STATE_HOME/Speedlog/logs` (fallback `~/.local/state`, per XDG spec for
    state/log data); Windows `data_dir()/logs`. Also created if missing.
  - `db_path()` = `data_dir() / "data.db"` (matches architecture-context.md).
- **Tests:** 15 tests; platform branches via monkeypatched `config.platform.system` and
  `Path.home`, env overrides (`XDG_DATA_HOME`, `XDG_STATE_HOME`, `APPDATA`) exercised.
- **For next tickets:** NST-103 should use `config.log_dir()`; NST-201 should use
  `config.db_path()`. Helpers return `pathlib.Path` and are safe to call repeatedly.
