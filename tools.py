"""
Tool schemas + implementations exposed to Claude via tool use.

Kept deliberately small and composable: two "get raw rows" tools plus one
"aggregate" tool, rather than one tool per possible business question.
Claude decides how to combine them per query — that's the "query
understanding" and "business intelligence" requirement in practice.
"""

from monday_client import fetch_deals, fetch_work_orders
from data_utils import filter_rows, to_number, data_quality_summary

TOOLS = [
    {
        "name": "get_deals",
        "description": (
            "Fetch rows from the Deals (sales pipeline) board on monday.com, "
            "optionally filtered. Always returns a data_quality note about "
            "missing fields alongside the rows. Use this before answering any "
            "question about pipeline, sectors, deal stages, or revenue."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "sector_contains": {"type": "string", "description": "e.g. 'energy'"},
                "stage_contains": {"type": "string", "description": "Deal Stage substring filter"},
                "status_contains": {"type": "string", "description": "Deal Status substring filter"},
            },
        },
    },
    {
        "name": "get_work_orders",
        "description": (
            "Fetch rows from the Work Orders (project execution) board on "
            "monday.com, optionally filtered. Use this for questions about "
            "operational metrics, billing status, execution status, or "
            "project timelines."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "sector_contains": {"type": "string"},
                "execution_status_contains": {"type": "string"},
                "billing_status_contains": {"type": "string"},
            },
        },
    },
    {
        "name": "sum_field",
        "description": (
            "Sum a numeric field across a list of rows previously returned by "
            "get_deals or get_work_orders. Pass the exact rows back in (or a "
            "filtered subset of them). Non-numeric/missing values are "
            "excluded and reported separately rather than treated as zero."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "rows": {"type": "array", "items": {"type": "object"}},
                "field": {"type": "string"},
            },
            "required": ["rows", "field"],
        },
    },
]


def _run_get_deals(input_):
    result = fetch_deals()
    rows = result["items"]
    filters = {}
    if input_.get("sector_contains"):
        filters["Sector/service"] = input_["sector_contains"]
    if input_.get("stage_contains"):
        filters["Deal Stage"] = input_["stage_contains"]
    if input_.get("status_contains"):
        filters["Deal Status"] = input_["status_contains"]
    rows = filter_rows(rows, filters)
    dq = data_quality_summary(rows, ["Masked Deal value", "Tentative Close Date", "Sector/service"])
    return {"row_count": len(rows), "rows": rows, "data_quality": dq}


def _run_get_work_orders(input_):
    result = fetch_work_orders()
    rows = result["items"]
    filters = {}
    if input_.get("sector_contains"):
        filters["Sector"] = input_["sector_contains"]
    if input_.get("execution_status_contains"):
        filters["Execution Status"] = input_["execution_status_contains"]
    if input_.get("billing_status_contains"):
        filters["Billing Status"] = input_["billing_status_contains"]
    rows = filter_rows(rows, filters)
    dq = data_quality_summary(rows, ["Amount in Rupees (Incl of GST) (Masked)", "Execution Status"])
    return {"row_count": len(rows), "rows": rows, "data_quality": dq}


def _run_sum_field(input_):
    rows = input_.get("rows", [])
    field = input_.get("field")
    total = 0.0
    counted = 0
    excluded = 0
    for r in rows:
        n = to_number(r.get(field))
        if n is None:
            excluded += 1
        else:
            total += n
            counted += 1
    return {"total": total, "rows_counted": counted, "rows_excluded_non_numeric": excluded}


DISPATCH = {
    "get_deals": _run_get_deals,
    "get_work_orders": _run_get_work_orders,
    "sum_field": _run_sum_field,
}


def run_tool(name, input_):
    if name not in DISPATCH:
        return {"error": f"unknown tool {name}"}
    try:
        return DISPATCH[name](input_)
    except Exception as e:  # surface API/auth errors to the agent, not a crash
        return {"error": str(e)}
