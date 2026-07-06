# Speedlog — Claude Code entry point

You are working on Speedlog: a PySide6 macOS menu-bar app that passively tracks
internet speed, records same-speed time segments to SQLite, shows a filterable paginated
report table (20/page), and exports PDF reports.

## Before doing ANYTHING, read in this order
1. `docs/ai-work-flow-rules.md`  — how you must work in this repo (mandatory)
2. `docs/project-overview.md`    — scope and product rules
3. `docs/architecture-context.md`— components, schema, algorithms, threading rules
4. `docs/code-standards.md`      — style, testing, definition of done
5. `docs/progress-tracker.md`    — pick the next TODO ticket (respect dependencies)
6. The ticket file under `tickets/` — your task specification
7. `docs/ui-context.md`          — required for any ui/ or export/ work

## Hard rules (short version)
- One ticket at a time; smallest diff; tests in the same change.
- PySide6 only (never PyQt). SQL only in `data/repository.py`. UTC internally.
- Collector thread never touches widgets; communicate via Qt signals.
- On user quit: flush open segment + close session BEFORE exit.
- Update `docs/progress-tracker.md` and the ticket file when a ticket is DONE.
- New scope discovered → new ticket file from `tickets/_TEMPLATE.md`, don't just do it.
