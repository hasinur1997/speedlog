# NST-801 — PDF generator (highlighted header, table, footer)

- **Epic:** EPIC-08 PDF Export
- **Type:** Feature
- **Priority:** P1
- **Estimate:** L
- **Status:** DONE
- **Depends on:** NST-203

## Description
`export/pdf_report.py` (reportlab): renders the filtered record set to PDF per
architecture-context.md ("PDF export") and ui-context.md.

## Acceptance criteria
- [x] `generate_report(records: Iterable[SpeedRecord], filter_label: str,
      full_name: str, out_path: Path) -> None`
- [x] Header band: ACCENT_COLOR background, white text — line 1 "Internet Speed Report",
      line 2 full name, line 3 human-readable date/date-time range
- [x] Body table: Date | Time Range | Download | Upload; header row repeats on every
      page; zebra striping; uses the SAME formatting helpers as the table (NST-603)
- [x] Footer: "Page N of M" + "Generated <local datetime>"
- [x] Handles 0 records ("No records for this range.") and 10,000+ records
      (streamed via fetch_all_records, memory-bounded)
- [x] `platform/userinfo.py`: `get_full_name()` — pw_gecos on mac/Linux,
      GetUserNameExW on Windows, getpass fallback; returned name used in header
- [x] No Qt imports in export module (pure, reusable)

## Test plan
Unit: generate to tmp_path for 0 / 25 / 500 records — file exists, page count sane
(pypdf in dev-deps to introspect), header text present via text extraction.
userinfo: monkeypatched pwd fallback chain.

## Implementation notes
- Files touched: `app/config.py`, `app/export/pdf_report.py`, `app/platform/userinfo.py`,
  `requirements-dev.txt`, `tests/test_pdf_report.py`, `tests/test_userinfo.py`
- The PDF renderer uses a streaming `reportlab` canvas path instead of materializing a
  giant table, so iterables from `fetch_all_records()` can be written row-by-row while a
  numbered-canvas replay adds the final "Page N of M" footer.
- Body cells reuse `format_date`, `format_time_range`, and `format_speed` from
  `app.formatting`; the export module remains Qt-free.
- Dev deps now pin `pypdf` for normal PDF introspection, and the PDF tests include a
  small reportlab-compatible fallback extractor so the suite still verifies output in
  environments where that extra package is not yet installed.
