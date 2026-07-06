# NST-404 — Quit behavior: stop tracking, flush, exit clean

- **Epic:** EPIC-04 App Shell & Tray
- **Type:** Feature
- **Priority:** P1
- **Estimate:** S
- **Status:** TODO
- **Depends on:** NST-403, NST-305

## Description
Product rule: user quit stops tracking entirely; the open segment and session MUST be
persisted before exit. No orphan process remains.

## Acceptance criteria
- [ ] `QApplication.aboutToQuit` connected to CollectorService.stop() + wait(3000)
- [ ] After quit: last speed_records row end_ts ~= quit time; session end_reason='quit'
- [ ] Force-kill scenario recovered next start via close_dangling_sessions (verify)
- [ ] No non-daemon threads or timers leak (app process exits, verified in test)

## Test plan
Integration test: run app headless (offscreen platform), feed fake samples, quit,
reopen DB, assert flushed segment + session closed.

## Implementation notes (fill after DONE)
