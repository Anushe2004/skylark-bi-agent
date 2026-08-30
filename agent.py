"""
Conversational BI agent: wraps Claude's tool-use loop around the
monday.com read tools in tools.py.
"""

import os
import json
import anthropic
from tools import TOOLS, run_tool

MODEL = "claude-sonnet-4-6"

SYSTEM_PROMPT = """You are a business intelligence assistant for Skylark Drones \
founders and executives. You answer questions using LIVE data pulled from two \
monday.com boards: Deals (sales pipeline) and Work Orders (project execution).

Rules:
- Always call get_deals and/or get_work_orders to fetch current data before \
answering anything factual — never guess or use memory of a prior answer.
- The data is real-world messy: fields are sometimes missing, dates come in \
inconsistent formats, and numeric fields are masked/text. When you notice \
missing or ambiguous data relevant to the question, say so explicitly and \
give the best answer you can from what's available, rather than refusing.
- When a query is genuinely ambiguous (e.g. "this quarter" with no year, or \
a sector name that doesn't exactly match what's in the data), ask a brief \
clarifying question instead of guessing — but only when it would change the \
answer materially.
- Use sum_field for totals rather than adding numbers yourself, so masked/ \
non-numeric rows are excluded transparently.
- Give the founder the insight, not a data dump: lead with the answer, then \
back it up with a couple of supporting numbers, then flag any caveats about \
data quality that affect confidence in the answer.
"""


class Agent:
    def __init__(self):
        self.client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))
        self.history = []

    def ask(self, user_message):
        self.history.append({"role": "user", "content": user_message})

        for _ in range(6):  # cap tool-use hops so a bad loop can't run forever
            resp = self.client.messages.create(
                model=MODEL,
                max_tokens=1500,
                system=SYSTEM_PROMPT,
                tools=TOOLS,
                messages=self.history,
            )

            self.history.append({"role": "assistant", "content": resp.content})

            if resp.stop_reason != "tool_use":
                final_text = "".join(
                    block.text for block in resp.content if block.type == "text"
                )
                return final_text

            tool_results = []
            for block in resp.content:
                if block.type == "tool_use":
                    result = run_tool(block.name, block.input)
                    tool_results.append(
                        {
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": json.dumps(result, default=str)[:12000],
                        }
                    )
            self.history.append({"role": "user", "content": tool_results})

        return "I'm having trouble pulling a clean answer together — could you rephrase or narrow the question?"
