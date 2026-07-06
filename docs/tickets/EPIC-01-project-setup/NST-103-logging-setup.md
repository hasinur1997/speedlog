# NST-103 — Logging setup

- **Epic:** EPIC-01 Project Setup
- **Type:** Task
- **Priority:** P2
- **Estimate:** S
- **Status:** TODO
- **Depends on:** NST-101

## Description
Central logging configuration: rotating file handler + console in dev.

## Acceptance criteria
- [ ] `logging_setup.configure(debug: bool)` sets root logger once (idempotent)
- [ ] Rotating file at `config.log_dir()/app.log`, 5 MB x 3 backups
- [ ] Format includes timestamp, level, module, thread name
- [ ] Console handler only when debug=True (or env NST_DEBUG=1)
- [ ] Uncaught exceptions hooked (`sys.excepthook`) and logged

## Test plan
Unit test: configure with tmp log dir, emit records, assert file written and handler config.

## Implementation notes (fill after DONE)
