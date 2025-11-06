"""
Simple Flask web app for Headache Tracking Chatbot.
Clean, minimal UI - no fancy stuff.
"""

import os
from flask import Flask, render_template, request, jsonify, session
from dotenv import load_dotenv
from openai import OpenAI

from fetch_headache_data import HeadacheDataFetcher

# Load environment variables
load_dotenv()

app = Flask(__name__)
app.secret_key = os.urandom(24)

# Initialize OpenAI
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None

# System message
SYSTEM_MESSAGE = """You are a helpful assistant for headache tracking. 
Analyze the user's headache data and provide clear, practical insights.
Be concise and friendly. Use simple language."""


def load_headache_data():
    """Load headache data from Google Sheets."""
    try:
        service_account_path = os.getenv("SERVICE_ACCOUNT_PATH", "")
        drive_folder_id = os.getenv("DRIVE_FOLDER_ID")

        # Need either SERVICE_ACCOUNT_JSON (Docker) or SERVICE_ACCOUNT_PATH (local)
        has_credentials = os.getenv("SERVICE_ACCOUNT_JSON") or service_account_path
        if not has_credentials or not drive_folder_id:
            return None

        fetcher = HeadacheDataFetcher(
            service_account_path=service_account_path or "/tmp/dummy.json",
            drive_folder_id=drive_folder_id,
        )

        # Suppress print output
        import io
        from contextlib import redirect_stdout

        f = io.StringIO()
        with redirect_stdout(f):
            data = fetcher.get_headache_data()

        return data
    except Exception as e:
        print(f"Error loading data: {e}")
        return None


def format_data_for_context(data):
    """Format headache data for AI context."""
    if not data:
        return "No data available."

    formatted = f"User has {len(data)} headache records:\n\n"
    for i, record in enumerate(data, 1):
        formatted += f"Record {i}:\n"
        for key, value in record.items():
            if not key.startswith("_"):
                formatted += f"{key}: {value}\n"
        formatted += "\n"
    return formatted


@app.route("/")
def index():
    """Render the main page."""
    # Initialize session
    if "messages" not in session:
        session["messages"] = []
    
    # Auto-load data on first visit
    if "data_loaded" not in session:
        session["data_loaded"] = False
        data = load_headache_data()
        if data:
            session["data_loaded"] = True
            session["headache_data"] = format_data_for_context(data)
            session["data_count"] = len(data)
        else:
            session["data_count"] = 0

    return render_template(
        "index.html",
        data_loaded=session.get("data_loaded", False),
        data_count=session.get("data_count", 0)
    )


@app.route("/api/load-data", methods=["POST"])
def api_load_data():
    """Load headache data."""
    data = load_headache_data()
    if data:
        session["data_loaded"] = True
        session["headache_data"] = format_data_for_context(data)
        return jsonify(
            {
                "success": True,
                "count": len(data),
                "message": f"Loaded {len(data)} records",
            }
        )
    else:
        return jsonify({"success": False, "message": "Could not load data"})


@app.route("/api/chat", methods=["POST"])
def api_chat():
    """Handle chat messages."""
    if not client:
        return jsonify({"success": False, "message": "OpenAI API not configured"})

    user_message = request.json.get("message", "").strip()
    if not user_message:
        return jsonify({"success": False, "message": "Empty message"})

    # Build conversation
    messages = [{"role": "system", "content": SYSTEM_MESSAGE}]

    # Add data context if loaded
    if session.get("data_loaded") and "headache_data" in session:
        messages.append(
            {"role": "system", "content": f"User's data:\n{session['headache_data']}"}
        )

    # Add conversation history
    if "messages" not in session:
        session["messages"] = []

    for msg in session["messages"]:
        messages.append(msg)

    # Add current message
    messages.append({"role": "user", "content": user_message})

    try:
        # Get response from OpenAI
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            temperature=0.7,
            max_tokens=1000,
        )

        assistant_message = response.choices[0].message.content

        # Save to session
        session["messages"].append({"role": "user", "content": user_message})
        session["messages"].append({"role": "assistant", "content": assistant_message})
        session.modified = True

        return jsonify({"success": True, "message": assistant_message})
    except Exception as e:
        return jsonify({"success": False, "message": f"Error: {str(e)}"})


@app.route("/api/reset", methods=["POST"])
def api_reset():
    """Reset conversation."""
    session["messages"] = []
    session.modified = True
    return jsonify({"success": True})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5514))
    app.run(host="0.0.0.0", port=port, debug=False)
