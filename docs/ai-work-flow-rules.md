# AI Workflow Rules — How Claude Code must work in this repo

## Session startup (every session, in order)
1. Read `docs/project-overview.md`
2. Read `docs/architecture-context.md`
3. Read `docs/code-standards.md`
4. Read `docs/progress-tracker.md` to find the current ticket
5. Read the ticket file in `tickets/` before writing any code
6. Read `docs/ui-context.md` when the ticket touches `ui/` or `export/`

## Ticket execution rules
- Work on ONE ticket at a time, in dependency order from the progress tracker.
- Do not start a ticket whose `Depends on` tickets are not `DONE`.
- Stay strictly inside the ticket's scope. If you discover needed work outside scope,
  do NOT do it — create a new ticket file (copy `tickets/_TEMPLATE.md`, next free ID)
  and add it to the progress tracker as `TODO`.
- Before coding, restate the plan in 3–6 bullets and list files you will create/modify.
  If the plan conflicts with architecture-context.md, stop and raise it instead of coding.

## Coding rules
- Follow `docs/code-standards.md` exactly (types, config constants, SQL location,
  threading rules, formatting).
- Every logic ticket includes its tests in the same change. Run `pytest -q` and
  `ruff check .` and fix failures before declaring the ticket done.
- Never delete or rewrite existing modules wholesale to "clean up" — smallest diff that
  satisfies acceptance criteria.
- Never add a new third-party dependency without an explicit note in the ticket or
  asking the user first.

## Ticket completion checklist (all required)
- [ ] All acceptance criteria demonstrably met
- [ ] Tests added/updated and passing
- [ ] Lint & format clean
- [ ] `docs/progress-tracker.md` updated: status → DONE, date, one-line note
- [ ] Ticket file updated: status field → DONE, add "Implementation notes" section
      (files touched, decisions made, anything the next ticket should know)
- [ ] Docs updated if behavior/architecture changed

## Communication rules
- If acceptance criteria are ambiguous, ask the user BEFORE implementing; record the
  answer in the ticket under "Decisions".
- If a task turns out infeasible as specified, propose the closest feasible alternative
  with trade-offs; wait for approval.
- Summaries at the end of a ticket: what was built, how it was tested, what's next.
- If All acceptance criteria passed check all the criteria

## Forbidden
- Working on multiple tickets in one change set
- Placing SQL outside `data/repository.py`
- Touching UI widgets from the collector thread
- Importing PyQt (must be PySide6)
- Skipping the progress tracker update
- Committing failing tests or commented-out test skips without a ticket
