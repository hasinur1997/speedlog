# NST-501 — Live tab: current speeds + session info

- **Epic:** EPIC-05 Live Speed View
- **Type:** Feature
- **Priority:** P2
- **Estimate:** S
- **Status:** TODO
- **Depends on:** NST-401, NST-305

## Description
`ui/live_view.py`: big readable current download/upload numbers plus
"Connected since <time>" line.

## Acceptance criteria
- [ ] Large labels `↓ X MB/s` / `↑ Y MB/s` updating on speed_sampled (only when visible)
- [ ] Session line from session_changed: "Connected since 10:01 AM" / "Offline"
- [ ] Uses shared format_speed; local time formatting via zoneinfo
- [ ] Layout survives resize; dark mode legible

## Test plan
pytest-qt: signals update labels; offline state; hidden tab skips repaint work.

## Implementation notes (fill after DONE)
