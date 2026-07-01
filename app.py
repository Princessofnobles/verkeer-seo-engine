"""
Verkeer SEO Opportunity Engine
------------------------------
A working AI + automation prototype for the Verkeer technical assessment.

What it does:
1. Connects to Google Search Console (via Google's official API) and pulls
   real query/page performance data for the last 28 days.
2. Finds "quick win" pages: ranking in positions 4-15, getting impressions,
   but not enough clicks -> these are the cheapest wins in SEO.
3. Sends that data to Claude (Anthropic API) and asks it to produce specific,
   prioritised, plain-English recommendations for each opportunity.
4. Renders everything in a simple web dashboard non-technical people can read,
   and can also generate a downloadable weekly report (HTML/PDF-ready).
5. Can run on a schedule (see scheduler.py) so the report is generated
   automatically every week with zero manual effort.

Run in DEMO MODE (no credentials needed) to see it working immediately:
    python app.py
Then visit http://localhost:5000

To connect REAL data, follow README.md (Google OAuth + Anthropic API key).
"""

import os
import json
import datetime
from dotenv import load_dotenv
load_dotenv()  # reads variables from a .env file in this folder, if present

from flask import Flask, render_template, jsonify, request, redirect, session, url_for

from gsc_client import get_search_console_data, get_auth_url, exchange_code_for_token, has_valid_credentials
from ai_engine import analyze_opportunities, generate_weekly_report

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "dev-secret-change-me")

SITE_URL = os.environ.get("GSC_SITE_URL", "https://www.verkeer.co/")


@app.route("/")
def home():
    connected = has_valid_credentials(session)
    return render_template("dashboard.html", connected=connected, site_url=SITE_URL)


@app.route("/connect")
def connect():
    """Kick off Google OAuth so the app can read the real Search Console data."""
    auth_url = get_auth_url()
    return redirect(auth_url)


@app.route("/oauth2callback")
def oauth2callback():
    code = request.args.get("code")
    if code:
        creds = exchange_code_for_token(code)
        session["credentials"] = creds
    return redirect(url_for("home"))


@app.route("/api/opportunities")
def api_opportunities():
    """
    Core endpoint: pulls GSC data, filters for positions 4-15,
    and returns the raw opportunity list (no AI yet - fast/cheap).
    """
    days = int(request.args.get("days", 28))
    data = get_search_console_data(session, SITE_URL, days=days)
    return jsonify(data)


@app.route("/api/analyze", methods=["POST"])
def api_analyze():
    """
    Takes the opportunity list and asks Claude to turn it into
    prioritised, plain-English recommendations.
    """
    payload = request.get_json(force=True)
    opportunities = payload.get("opportunities", [])
    result = analyze_opportunities(opportunities)
    return jsonify(result)


@app.route("/api/weekly-report", methods=["POST"])
def api_weekly_report():
    """
    Generates the full weekly leadership report: summary + top opportunities
    + recommended actions, written by Claude in plain English.
    """
    days = int(request.json.get("days", 28)) if request.is_json else 28
    data = get_search_console_data(session, SITE_URL, days=days)
    report = generate_weekly_report(data, SITE_URL)
    return jsonify(report)


@app.route("/healthz")
def healthz():
    return jsonify({"status": "ok", "time": datetime.datetime.utcnow().isoformat()})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
