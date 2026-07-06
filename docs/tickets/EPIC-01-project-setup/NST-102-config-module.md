# NST-102 — Config module & application constants

- **Epic:** EPIC-01 Project Setup
- **Type:** Task
- **Priority:** P1
- **Estimate:** S
- **Status:** TODO
- **Depends on:** NST-101

## Description
Single source of truth for all tunables and paths in `config.py`.

## Acceptance criteria
- [ ] Constants: SAMPLE_INTERVAL=1.0, SMOOTH_WINDOW=5, BAND_TOLERANCE_PCT=0.10,
      BAND_TOLERANCE_FLOOR_BPS=250_000, HYSTERESIS_TICKS=5, MIN_SEGMENT_SECS=5,
      PAGE_SIZE=20, ACCENT_COLOR="#2E7CF6", APP_NAME="Speedlog"
- [ ] `data_dir()` returns platform-correct app data dir (macOS:
      ~/Library/Application Support/Speedlog; Linux: XDG; Windows: %APPDATA%)
      and creates it if missing
- [ ] `db_path()`, `log_dir()` helpers
- [ ] No other module hardcodes these values

## Technical notes
Use `platform.system()` branching now so Linux/Windows support comes free later.

## Test plan
Unit tests for dir helpers (monkeypatched HOME/platform); constants importable.

## Implementation notes (fill after DONE)
