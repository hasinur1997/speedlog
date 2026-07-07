# NST-404 — Quit behavior: stop tracking, flush, exit clean

- **Epic:** EPIC-04 App Shell & Tray
- **Type:** Feature
- **Priority:** P1
- **Estimate:** S
- **Status:** DONE
- **Depends on:** NST-403, NST-305

## Description
Product rule: user quit stops tracking entirely; the open segment and session MUST be
persisted before exit. No orphan process remains.

## Acceptance criteria
- [x] `QApplication.aboutToQuit` connected to CollectorService.stop() + wait(3000)
- [x] After quit: last speed_records row end_ts ~= quit time; session end_reason='quit'
- [x] Force-kill scenario recovered next start via close_dangling_sessions (verify)
- [x] No non-daemon threads or timers leak (app process exits, verified in test)

## Test plan
Integration test: run app headless (offscreen platform), feed fake samples, quit,
reopen DB, assert flushed segment + session closed.

## Implementation notes
- `app/main.py` now installs an `aboutToQuit` shutdown hook that calls `CollectorService.stop()` and waits `config.COLLECTOR_JOIN_TIMEOUT_MS` before Qt exits; the single-instance guard is still released on app shutdown.
- `tests/test_main.py` verifies the `aboutToQuit` hook directly and runs a headless quit integration test against a real `CollectorService` + temp SQLite DB, asserting the final `speed_records.end_ts` matches the session `end_ts` and `end_reason='quit'`.
- `tests/test_service.py` adds startup recovery coverage for a dangling session left open by a simulated crash, proving the next collector launch closes it via `close_dangling_sessions()` before opening a new session.
- Verification run: `QT_QPA_PLATFORM=offscreen .venv/bin/pytest -q` (127 passed, 1 skipped), `.venv/bin/ruff check .`, `.venv/bin/black --check .`.
