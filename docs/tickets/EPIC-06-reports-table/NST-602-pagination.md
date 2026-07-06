# NST-602 — Pagination (20 per page)

- **Epic:** EPIC-06 Reports Table
- **Type:** Feature
- **Priority:** P1
- **Estimate:** S
- **Status:** TODO
- **Depends on:** NST-601

## Description
Pagination bar under the table: Prev / "Page X of Y" / Next + total record count.

## Acceptance criteria
- [ ] PAGE_SIZE from config (20); Y = ceil(count/PAGE_SIZE), min 1
- [ ] Prev disabled on page 1; Next disabled on last page
- [ ] Changing filter resets to page 1
- [ ] Count label: "231 records" (singular handled: "1 record")
- [ ] Page state survives tab switch, resets on filter change

## Test plan
pytest-qt with seeded 50 records: 3 pages (20/20/10); button enablement at edges;
filter change resets page.

## Implementation notes (fill after DONE)
