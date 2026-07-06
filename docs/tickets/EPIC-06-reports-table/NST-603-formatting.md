# NST-603 — Cell formatting: time ranges, units, midnight edge

- **Epic:** EPIC-06 Reports Table
- **Type:** Feature
- **Priority:** P2
- **Estimate:** S
- **Status:** TODO
- **Depends on:** NST-601

## Description
Presentation rules from ui-context.md applied in one formatting module shared with PDF.

## Acceptance criteria
- [ ] `format_time_range(start_ts, end_ts) -> "10:20 AM – 10:30 AM"` (local time)
- [ ] Midnight-spanning record: shown on START date, `11:58 PM – 12:04 AM (+1)`
- [ ] `format_date(ts) -> "2026-07-06"`; speeds via shared format_speed
- [ ] All conversions via zoneinfo; NO manual UTC offsets
- [ ] Same helpers imported by table model AND pdf_report (single source)

## Test plan
Unit tests with fixed tz (monkeypatched): normal range, midnight span, DST transition
day, sub-MB speed formatting.

## Implementation notes (fill after DONE)
