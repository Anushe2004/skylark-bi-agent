# Skylark Drones — monday.com Business Intelligence Agent

A conversational agent that answers founder-level BI questions by querying
two monday.com boards (Deals, Work Orders) live via the monday.com GraphQL
API — no CSV data is hardcoded.

## Architecture

```
Browser (static/index.html, plain JS chat UI)
      │  POST /api/chat {message, session_id}
      ▼
Flask app (app.py)  ── one Agent instance per session, in memory
      │
      ▼
Agent (agent.py) ── Claude (Sonnet) tool-use loop
      │  calls tools: get_deals / get_work_orders / sum_field
      ▼
tools.py ── filters + data-quality summary
      │
      ▼
monday_client.py ── paginated GraphQL reads from monday.com
      │
      ▼
data_utils.py ── number/date/quantity normalization, missing-value handling
```

The agent never hardcodes business logic like "energy sector" or "this
quarter" — it fetches rows and reasons over them with Claude, which is what
lets it handle open-ended founder questions instead of a fixed set of
reports.

## Setup

1. **Import your data into monday.com** (already done for this submission —
   see `import_to_monday.py` from the earlier step: 342 Deals items and 175
   Work Orders items created; a handful of rows with missing names or
   leaked header rows were logged to `*_skipped.csv` rather than silently
   dropped).

2. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

3. Set environment variables:
   ```
   export MONDAY_API_KEY="your monday.com personal API token"
   export ANTHROPIC_API_KEY="your Anthropic API key"
   export DEALS_BOARD_ID=5030966664
   export WORK_ORDERS_BOARD_ID=5030966666
   ```

4. Run locally:
   ```
   python app.py
   ```
   Open http://localhost:5000

## Deploying (hosted prototype requirement)

Simplest path: [Render.com](https://render.com) free web service.
- New Web Service → connect the GitHub repo
- Build command: `pip install -r requirements.txt`
- Start command: `gunicorn app:app`
- Add the four environment variables above in Render's dashboard
- Render gives you a public `https://<name>.onrender.com` URL — that's your
  hosted prototype link.

(Railway.app or Fly.io work the same way if you prefer.)

## Example queries to test with

- "How's our pipeline looking for the energy sector this quarter?"
- "Which work orders are still pending billing?"
- "What's our total deal value by stage?"
- "Are there any sectors where we have a lot of deals but few completed work orders?"

## Known limitations

- Sessions are stored in memory — a redeploy or server restart clears
  conversation history (fine for a prototype, not for production).
- The agent reads monday.com's rendered `text` field per column rather than
  raw column JSON, which is simpler to reason over but loses some structure
  (e.g. status colors, board relation links).
- No caching — every question re-fetches both boards. For ~500 rows this is
  fast; wouldn't scale to a very large board without pagination-aware
  caching.

## Challenges Faced

 - The live demo may show a billing/credit error depending on API balance at time of testing — the agent logic itself is complete and was    verified working locally; this is an account-funding issue, not a code defect.
