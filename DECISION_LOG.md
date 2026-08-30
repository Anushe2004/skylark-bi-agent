# Decision Log

## Key assumptions

- "This quarter" and similar relative time phrases are left for the agent
  to interpret against today's date at query time rather than hardcoded,
  since the assignment data has no fixed "current date" — the agent will
  ask for clarification if a date range materially changes the answer.
- Monetary fields marked "Masked" in the source data are still valid for
  relative comparisons (stage-to-stage, sector-to-sector) even though
  absolute values are anonymized; the agent treats them as real numbers.
- Rows with a missing primary name (Deal Name / Deal name masked) or an
  obviously leaked header row (e.g. a data row literally containing the
  string "Deal Status" as its status value) were excluded at import time
  and logged to `*_skipped.csv`, since they can't be meaningfully queried.

## Trade-offs chosen and why

- **Read monday.com's rendered `text` column value instead of raw JSON.**
  Faster to build and easier for Claude to reason over directly, at the
  cost of losing structured metadata (e.g. status label colors). For a
  read-only BI agent, the text values are sufficient.
- **Cleaning happens at query time (data_utils.py), not at import time.**
  This means one bug fix improves every future answer without needing to
  re-run the CSV import, and it keeps the import script simple/inspectable
  — a deliberate trade of import-time simplicity for query-time robustness.
- **Quantity fields (e.g. "5360 HA", "40MW") are kept as raw text plus a
  parsed (number, unit) pair, never force-summed into one column.** Summing
  hectares and megawatts together would produce a meaningless number; the
  agent instead groups by unit before aggregating.
- **In-memory session store instead of a database.** Sufficient for a
  single-instance prototype under evaluation; documented as a limitation
  rather than hidden.
- **Three general-purpose tools (get_deals, get_work_orders, sum_field)
  instead of one tool per business question.** Keeps the tool surface small
  and lets Claude compose them for questions we didn't anticipate, which
  matters more than covering a fixed report list.

## What I'd do differently with more time

- Add a caching layer (e.g. 60-second TTL) so repeated questions in one
  session don't refetch the full board every time.
- Track column relation links between Deals and Work Orders explicitly
  (e.g. by client code) instead of relying on Claude to join them by
  matching text fields, which is more fragile on messier real data.
- Add automated tests for `data_utils.py`'s date/number/quantity parsers
  against the actual skipped-row edge cases found during import.
- Build a small "leadership update" export mode (see below) that renders a
  formatted summary rather than only conversational answers.

## How I interpreted "leadership updates"

Interpreted as: the agent should be able to produce a structured,
copy-pasteable summary (pipeline by sector, work orders by execution
status, flagged data-quality issues) when asked directly — e.g. "give me a
leadership update on the energy sector" — rather than a separate scheduled
report feature. This keeps it inside the same conversational interface
rather than adding a second UI surface, given the time budget.
