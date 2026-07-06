# NST-403 — Tray menu (Open, Quit with confirmation)

- **Epic:** EPIC-04 App Shell & Tray
- **Type:** Feature
- **Priority:** P1
- **Estimate:** S
- **Status:** TODO
- **Depends on:** NST-402

## Description
Context menu on the tray icon per ui-context.md.

## Acceptance criteria
- [ ] Menu: "Open Speedlog" | separator | "Quit"
- [ ] Open shows/raises MainWindow
- [ ] Quit shows confirm dialog: "Quitting stops speed tracking. Quit?" (Quit/Cancel)
- [ ] Confirmed quit triggers the shutdown path (NST-404); cancel does nothing

## Test plan
pytest-qt with dialog monkeypatched: cancel keeps app alive; confirm calls quit handler.

## Implementation notes (fill after DONE)
