# NST-901 — Autostart at login (macOS LaunchAgent)

- **Epic:** EPIC-09 Autostart & Packaging
- **Type:** Feature
- **Priority:** P1
- **Estimate:** M
- **Status:** TODO
- **Depends on:** NST-401

## Description
Product rule "default app will automatically run": install a per-user LaunchAgent so
the app starts at login. User quit still fully stops it until next login (RunAtLoad
only, KeepAlive=false — a quit app must NOT be resurrected).

## Acceptance criteria
- [ ] `platform/autostart_macos.py`: `enable()`, `disable()`, `is_enabled()`
- [ ] Writes `~/Library/LaunchAgents/com.speedlog.app.plist` with RunAtLoad=true,
      KeepAlive=false, ProcessType=Interactive, program path resolved for both
      dev (python -m) and bundled .app modes
- [ ] Loaded/unloaded via `launchctl bootstrap/bootout gui/$UID` (modern syntax)
- [ ] First-run prompt: "Start Speedlog automatically at login?" (remembered
      in QSettings); toggle also available in tray menu ("Start at Login" checkable)
- [ ] Enable/disable idempotent; failures logged, surfaced as non-fatal message

## Technical notes
Alternative for bundled app: SMAppService via pyobjc — note as v1.1 option; plist
approach is fine for v1. Linux (.desktop autostart) / Windows (Run key) tracked later.

## Test plan
Unit: plist content generated correctly (path, keys) to tmp dir; launchctl calls
mocked and asserted. Manual checklist in ticket for real login test.

## Implementation notes (fill after DONE)
