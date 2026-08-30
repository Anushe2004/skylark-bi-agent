"""
monday.com read-only client for the BI agent.

Deliberately thin: one function to pull ALL items (with pagination) from a
board and flatten their column_values into a plain dict, so the agent layer
never has to think about monday.com's GraphQL shapes directly.

No data is cached to disk or hardcoded — every call hits the monday.com API
live, per the assignment's "do not hardcode CSV data" requirement.
"""

import os
import time
import requests

API_URL = "https://api.monday.com/v2"
API_KEY = os.environ.get("MONDAY_API_KEY")

DEALS_BOARD_ID = int(os.environ.get("DEALS_BOARD_ID", "5030966664"))
WORK_ORDERS_BOARD_ID = int(os.environ.get("WORK_ORDERS_BOARD_ID", "5030966666"))

ITEMS_QUERY = """
query ($boardId: ID!, $cursor: String) {
  boards(ids: [$boardId]) {
    name
    items_page(limit: 100, cursor: $cursor) {
      cursor
      items {
        id
        name
        column_values {
          id
          text
          value
          column {
            title
          }
        }
      }
    }
  }
}
"""


def _request(query, variables):
    if not API_KEY:
        raise RuntimeError("MONDAY_API_KEY environment variable is not set.")
    resp = requests.post(
        API_URL,
        json={"query": query, "variables": variables},
        headers={"Authorization": API_KEY, "Content-Type": "application/json"},
        timeout=30,
    )
    resp.raise_for_status()
    data = resp.json()
    if "errors" in data:
        raise RuntimeError(str(data["errors"]))
    return data["data"]


def fetch_board_items(board_id, max_pages=20):
    """Pull every item on a board, flattened into {column_title: text_value}.

    Uses monday.com's `text` field (the human-readable rendering of each
    column) rather than `value` (raw JSON) so the agent gets clean strings
    it can reason about directly, at the cost of losing some structure
    (e.g. status colors). That trade-off is documented in the Decision Log.
    """
    all_items = []
    cursor = None
    board_name = None

    for _ in range(max_pages):
        data = _request(ITEMS_QUERY, {"boardId": str(board_id), "cursor": cursor})
        boards = data.get("boards", [])
        if not boards:
            break
        board_name = boards[0]["name"]
        page = boards[0]["items_page"]

        for item in page["items"]:
            row = {"_item_id": item["id"], "Name": item["name"]}
            for cv in item["column_values"]:
                title = cv["column"]["title"]
                row[title] = cv["text"]
            all_items.append(row)

        cursor = page.get("cursor")
        if not cursor:
            break
        time.sleep(0.2)  # be polite to the API between pages

    return {"board_name": board_name, "items": all_items}


def fetch_deals():
    return fetch_board_items(DEALS_BOARD_ID)


def fetch_work_orders():
    return fetch_board_items(WORK_ORDERS_BOARD_ID)
