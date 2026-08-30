"""
Normalization helpers applied at query time, not import time.

Design choice (see Decision Log): we imported monday.com columns mostly as
raw text/strings, and do the real cleaning here, live, every time a question
is asked. That means a single change to these functions improves every past
and future answer, instead of requiring a re-import.
"""

import re
from datetime import datetime

NUM_RE = re.compile(r"-?\d+(\.\d+)?")


def to_number(val):
    """Best-effort parse of a masked/messy numeric field. Returns None, not 0,
    when nothing usable is present — callers must treat None as 'unknown',
    never silently coerce it to zero (that would fabricate revenue)."""
    if val is None:
        return None
    s = str(val).strip().replace(",", "")
    if s == "" or s.upper() in ("NA", "N/A", "#VALUE!", "NONE"):
        return None
    m = NUM_RE.search(s)
    return float(m.group()) if m else None


def to_date(val):
    if not val:
        return None
    s = str(val).strip()
    for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y", "%m/%d/%Y"):
        try:
            return datetime.strptime(s, fmt)
        except ValueError:
            continue
    return None


def parse_quantity(raw):
    """Quantity fields mix free text and units ('5360 HA', '24 Months',
    '40MW'). Returns (number, unit) so callers can group by unit instead of
    silently summing incompatible units together."""
    if not raw:
        return None, None
    s = str(raw).strip()
    m = re.match(r"([\d,.]+)\s*([A-Za-z%]*)", s)
    if not m:
        return None, s or None
    num_str, unit = m.groups()
    try:
        num = float(num_str.replace(",", ""))
    except ValueError:
        num = None
    return num, (unit.strip() or None)


def filter_rows(rows, filters):
    """filters: dict of {column_name: substring}, case-insensitive contains
    match. Missing/None values never match a filter (explicit exclusion,
    not a crash)."""
    if not filters:
        return rows
    out = []
    for row in rows:
        ok = True
        for col, needle in filters.items():
            val = row.get(col)
            if not val or needle.lower() not in str(val).lower():
                ok = False
                break
        if ok:
            out.append(row)
    return out


def data_quality_summary(rows, key_fields):
    """Counts missing values per field so the agent can surface caveats
    ('42% of deals are missing a close date') instead of pretending the
    data is complete."""
    total = len(rows)
    if total == 0:
        return {}
    summary = {}
    for field in key_fields:
        missing = sum(1 for r in rows if not r.get(field))
        summary[field] = {
            "missing": missing,
            "missing_pct": round(100 * missing / total, 1),
        }
    return summary
