"""
Simple Flask web app for Headache Tracking Chatbot.
Clean, minimal UI - no fancy stuff.
"""

import os
from flask import Flask, render_template, request, jsonify, session
from dotenv import load_dotenv
from openai import OpenAI

from fetch_headache_data import HeadacheDataFetcher

from datetime import datetime, timedelta
from collections import defaultdict, Counter

# Load environment variables
load_dotenv()

app = Flask(__name__, static_folder='static')
app.secret_key = os.urandom(24)

# Initialize OpenAI
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None

# System message
SYSTEM_MESSAGE = """You are a helpful assistant for headache tracking. 
Analyze the user's headache data and provide clear, practical insights.
Be concise and friendly. Use simple language. and you are a gangster background but you are a nice person now.
user is called "Emily" and do a bit flirty with her.
"""


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


def parse_date(date_str):
    """Parse date string in MM/DD/YYYY format."""
    try:
        if not date_str:
            return None

        # Handle various date formats
        if isinstance(date_str, str):
            # Try MM/DD/YYYY format (e.g., "11/5/2025")
            if "/" in date_str:
                # Split by space first to handle timestamps
                date_part = date_str.split()[0] if " " in date_str else date_str
                parts = date_part.split("/")
                if len(parts) == 3:
                    month, day, year = parts
                    return datetime(int(year), int(month), int(day))
        return None
    except Exception as e:
        print(f"Error parsing date '{date_str}': {e}")
        return None


def extract_pain_level(record):
    """Extract pain level from record, trying multiple field name variations."""
    # Try various field name combinations
    field_names = [
        "Pain Level",
        "pain level",
        "PAIN LEVEL",
        "Pain Level ",
        "Pain",
        "pain",
        "PAIN",
        "Pain Level:",
        "Pain level",
        "Pain_Level",
        "pain_level",
    ]

    for field_name in field_names:
        pain_str = record.get(field_name, "")
        if pain_str:
            # Strip whitespace and try to convert
            pain_str = str(pain_str).strip()
            if pain_str:  # Make sure it's not empty after stripping
                try:
                    pain = float(pain_str)
                    if pain >= 0:  # Accept 0 or positive values
                        return pain
                except (ValueError, TypeError):
                    continue

    # If no field found, try to find any field that might contain a number
    # This is a fallback for unknown field names
    for key, value in record.items():
        if "pain" in key.lower() and value:
            try:
                pain = float(str(value).strip())
                if pain >= 0:
                    return pain
            except (ValueError, TypeError):
                continue

    return None


def extract_drug(record):
    """Extract drug/medication from record, trying multiple field name variations."""
    # Try various field name combinations
    field_names = [
        "Medication",
        "medication",
        "MEDICATION",
        "Medication ",
        "Drug",
        "drug",
        "DRUG",
        "Drug ",
        "Medication:",
        "Drug:",
        "medicine",
        "Medicine",
    ]

    for field_name in field_names:
        drug = record.get(field_name, "")
        if drug:
            drug = str(drug).strip()
            if drug:  # Make sure it's not empty after stripping
                return drug

    # If no field found, try to find any field that might contain drug info
    for key, value in record.items():
        if (
            any(
                term in key.lower()
                for term in ["drug", "medication", "medicine", "med"]
            )
            and value
        ):
            drug = str(value).strip()
            if drug:
                return drug

    return None


def analyze_weekly_data(data):
    """Analyze data for weekly view."""
    if not data:
        return {
            "total_headaches": 0,
            "headache_days": 0,
            "avg_pain": 0,
            "consistency": 0,
            "total_drugs": 0,
            "drugs_by_type": {},
            "daily_data": [],
            "weekly_trend": [],
        }

    # Get current week (last 7 days)
    today = datetime.now()
    week_start = today - timedelta(days=7)

    # Filter data for this week
    week_data = []
    for record in data:
        # Try multiple possible date field names
        date_str = (
            record.get("Date", "")
            or record.get("date", "")
            or record.get("Timestamp", "")
            or record.get("timestamp", "")
        )
        parsed_date = parse_date(date_str)
        if parsed_date and parsed_date >= week_start:
            week_data.append(record)

    # Count unique days with headaches
    headache_days_set = set()
    pain_levels = []
    drug_counts = defaultdict(int)  # Count per drug type
    daily_counts = defaultdict(int)  # Headaches per day
    daily_drug_counts = defaultdict(int)  # Drugs per day
    daily_pain_levels = defaultdict(list)  # Pain levels per day

    for record in week_data:
        date_str = (
            record.get("Date", "")
            or record.get("date", "")
            or record.get("Timestamp", "")
            or record.get("timestamp", "")
        )
        parsed_date = parse_date(date_str)
        if parsed_date:
            date_key = parsed_date.date()
            headache_days_set.add(date_key)
            daily_counts[date_key] += 1

            # Pain level
            pain = extract_pain_level(record)
            if pain is not None:
                pain_levels.append(pain)
                daily_pain_levels[date_key].append(pain)

            # Drugs - count per drug type
            drug = extract_drug(record)
            if drug:
                drug_counts[drug] += 1
                daily_drug_counts[date_key] += 1

    # Build daily data for charts (chronological order for charts)
    daily_data = []
    for i in range(7):
        day = week_start + timedelta(days=i)
        day_key = day.date()
        count = daily_counts.get(day_key, 0)
        has_headache = 1 if day_key in headache_days_set else 0
        drug_count = daily_drug_counts.get(day_key, 0)
        day_pain_levels = daily_pain_levels.get(day_key, [])
        avg_pain_for_day = (
            sum(day_pain_levels) / len(day_pain_levels) if day_pain_levels else 0
        )

        daily_data.append(
            {
                "date": day_key,
                "day_name": day.strftime("%a"),
                "count": count,
                "has_headache": has_headache,
                "drug_count": drug_count,
                "pain_level": round(avg_pain_for_day, 1) if avg_pain_for_day > 0 else 0,
            }
        )

    # Create sorted version for table (descending)
    daily_data_sorted = sorted(daily_data, key=lambda x: x["date"], reverse=True)

    # Calculate metrics
    total_headaches = len(week_data)
    headache_days = len(headache_days_set)
    avg_pain = sum(pain_levels) / len(pain_levels) if pain_levels else 0
    consistency = (headache_days / 7) * 100 if headache_days > 0 else 0
    total_drugs = sum(drug_counts.values())

    return {
        "total_headaches": total_headaches,
        "headache_days": headache_days,
        "avg_pain": round(avg_pain, 1),
        "consistency": round(consistency, 1),
        "total_drugs": total_drugs,
        "drugs_by_type": dict(drug_counts),
        "daily_data": daily_data,  # Chronological order for charts
        "daily_data_sorted": daily_data_sorted,  # Descending order for table
        "weekly_trend": [],
    }


def analyze_monthly_data(data):
    """Analyze data for monthly view."""
    if not data:
        return {
            "total_headaches": 0,
            "headache_days": 0,
            "avg_pain": 0,
            "consistency": 0,
            "total_drugs": 0,
            "drugs_by_type": {},
            "weekly_data": [],
            "monthly_trend": [],
        }

    # Get current month
    today = datetime.now()
    month_start = datetime(today.year, today.month, 1)
    days_in_month = (
        month_start.replace(month=month_start.month % 12 + 1, day=1) - timedelta(days=1)
    ).day

    # Filter data for this month
    month_data = []
    for record in data:
        date_str = (
            record.get("Date", "")
            or record.get("date", "")
            or record.get("Timestamp", "")
            or record.get("timestamp", "")
        )
        parsed_date = parse_date(date_str)
        if parsed_date and parsed_date >= month_start:
            month_data.append(record)

    # Count unique days with headaches
    headache_days_set = set()
    pain_levels = []
    drug_counts = defaultdict(int)
    weekly_counts = defaultdict(int)  # Headaches per week

    for record in month_data:
        date_str = (
            record.get("Date", "")
            or record.get("date", "")
            or record.get("Timestamp", "")
            or record.get("timestamp", "")
        )
        parsed_date = parse_date(date_str)
        if parsed_date:
            date_key = parsed_date.date()
            headache_days_set.add(date_key)

            # Calculate week number (1-4)
            week_num = ((parsed_date - month_start).days // 7) + 1
            if week_num > 4:
                week_num = 4
            weekly_counts[week_num] += 1

            # Pain level
            pain = extract_pain_level(record)
            if pain is not None:
                pain_levels.append(pain)

            # Drugs - count per drug type
            drug = extract_drug(record)
            if drug:
                drug_counts[drug] += 1

    # Build weekly data for charts
    weekly_data = []
    for week in range(1, 5):
        count = weekly_counts.get(week, 0)
        weekly_data.append({"week": week, "count": count})

    # Calculate metrics
    total_headaches = len(month_data)
    headache_days = len(headache_days_set)
    avg_pain = sum(pain_levels) / len(pain_levels) if pain_levels else 0
    consistency = (headache_days / days_in_month) * 100 if headache_days > 0 else 0
    total_drugs = sum(drug_counts.values())

    return {
        "total_headaches": total_headaches,
        "headache_days": headache_days,
        "avg_pain": round(avg_pain, 1),
        "consistency": round(consistency, 1),
        "total_drugs": total_drugs,
        "drugs_by_type": dict(drug_counts),
        "weekly_data": weekly_data,
        "monthly_trend": [],
    }


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
        data_count=session.get("data_count", 0),
    )


@app.route("/api/load-data", methods=["POST"])
def api_load_data():
    """Load headache data."""
    data = load_headache_data()
    if data:
        session["data_loaded"] = True
        session["headache_data"] = format_data_for_context(data)
        session["data_count"] = len(data)
        session.modified = True
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


@app.route("/analysis")
def analysis():
    """Render the analysis dashboard page."""
    # Always load fresh data when opening the dashboard
    data = load_headache_data()

    # Get view type (weekly or monthly)
    view = request.args.get("view", "weekly")

    if view == "weekly":
        analysis_data = analyze_weekly_data(data)
    else:
        analysis_data = analyze_monthly_data(data)

    return render_template(
        "analysis.html", view=view, data_loaded=data is not None, **analysis_data
    )


@app.route("/api/analysis/data")
def api_analysis_data():
    """API endpoint for analysis data."""
    data = load_headache_data()
    view = request.args.get("view", "weekly")

    if view == "weekly":
        analysis_data = analyze_weekly_data(data)
    else:
        analysis_data = analyze_monthly_data(data)

    return jsonify(analysis_data)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5514))
    app.run(host="0.0.0.0", port=port, debug=False)
