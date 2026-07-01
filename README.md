# Verkeer SEO Opportunity Engine

A working Python prototype: Google Search Console + Claude AI + a dashboard.
Built for the Verkeer AI & Automation Engineer technical assessment.

## What it does
Finds pages on verkeer.co already ranking on page 1–2 of Google (positions 4–15)
that are under-clicking relative to their visibility, then uses Claude to turn
that into a prioritised, plain-English action list — automatically, every week.

## Quick start (works immediately, no setup required)

```bash
pip install -r requirements.txt
python app.py
```

Open http://localhost:5000 — it runs in **demo mode** with realistic sample
data so the full workflow (dashboard → AI analysis → downloadable report) is
visible right away.

## Connecting real data (optional, for the live demo)

1. **Google Search Console + OAuth**
   - Go to console.cloud.google.com → create a project → enable the
     "Search Console API"
   - Create an OAuth 2.0 Client ID (Web application), add redirect URI:
     `http://localhost:5000/oauth2callback`
   - Set environment variables:
     ```
     GOOGLE_CLIENT_ID=...
     GOOGLE_CLIENT_SECRET=...
     GOOGLE_REDIRECT_URI=http://localhost:5000/oauth2callback
     GSC_SITE_URL=https://www.verkeer.co/
     ```
   - Restart the app, click "Connect Google account" on the dashboard, sign
     in with the Gmail account that was given access.

2. **Claude AI**
   ```
   ANTHROPIC_API_KEY=sk-ant-...
   ```
   Without this, the app still works using a rule-based fallback analysis
   (so the demo never breaks), but the recommendations are richer with a
   real key.

## Automating it weekly (zero manual effort)

`scheduler.py` re-runs the whole pipeline and saves a report to `/reports`.
Point any scheduler at it, e.g. a cron job:
```
0 8 * * MON  python scheduler.py
```
In a production setup this would also post the summary to Slack/email — the
hooks for that are noted in `scheduler.py`.

## Project structure
```
app.py            Flask routes / web server
gsc_client.py      Google OAuth + Search Console API calls (+ demo fallback)
ai_engine.py        Claude API analysis (+ rule-based fallback)
scheduler.py        Standalone script for automated weekly runs
templates/dashboard.html   The dashboard UI
```

## Why this design
See `Verkeer_Assessment_Documentation.docx` for the full write-up (problem,
architecture, decisions, assumptions, future improvements).
# verkeer-seo-engine
