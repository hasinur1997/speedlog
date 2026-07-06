# NST-801 — PDF generator (highlighted header, table, footer)

- **Epic:** EPIC-08 PDF Export
- **Type:** Feature
- **Priority:** P1
- **Estimate:** L
- **Status:** TODO
- **Depends on:** NST-203

## Description
`export/pdf_report.py` (reportlab): renders the filtered record set to PDF per
architecture-context.md ("PDF export") and ui-context.md.

## Acceptance criteria
- [ ] `generate_report(records: Iterable[SpeedRecord], filter_label: str,
      full_name: str, out_path: Path) -> None`
- [ ] Header band: ACCENT_COLOR background, white text — line 1 "Internet Speed Report",
      line 2 full name, line 3 human-readable date/date-time range
- [ ] Body table: Date | Time Range | Download | Upload; header row repeats on every
      page; zebra striping; uses the SAME formatting helpers as the table (NST-603)
- [ ] Footer: "Page N of M" + "Generated <local datetime>"
- [ ] Handles 0 records ("No records for this range.") and 10,000+ records
      (streamed via fetch_all_records, memory-bounded)
- [ ] `platform/userinfo.py`: `get_full_name()` — pw_gecos on mac/Linux,
      GetUserNameExW on Windows, getpass fallback; returned name used in header
- [ ] No Qt imports in export module (pure, reusable)

## Test plan
Unit: generate to tmp_path for 0 / 25 / 500 records — file exists, page count sane
(pypdf in dev-deps to introspect), header text present via text extraction.
userinfo: monkeypatched pwd fallback chain.

## Implementation notes (fill after DONE)
