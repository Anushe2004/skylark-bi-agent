import os
import uuid
from flask import Flask, request, jsonify, send_from_directory
from agent import Agent

app = Flask(__name__, static_folder="static")

# Simple in-memory session store — fine for a single-instance prototype.
# Documented limitation in Decision Log: resets on redeploy, doesn't scale
# across multiple server instances.
SESSIONS = {}


@app.route("/")
def index():
    return send_from_directory(app.static_folder, "index.html")


@app.route("/api/chat", methods=["POST"])
def chat():
    data = request.get_json(force=True)
    message = (data or {}).get("message", "").strip()
    session_id = (data or {}).get("session_id")

    if not message:
        return jsonify({"error": "message is required"}), 400

    if not session_id or session_id not in SESSIONS:
        session_id = str(uuid.uuid4())
        SESSIONS[session_id] = Agent()

    agent = SESSIONS[session_id]
    try:
        reply = agent.ask(message)
    except Exception as e:
        return jsonify({"error": str(e), "session_id": session_id}), 500

    return jsonify({"reply": reply, "session_id": session_id})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
