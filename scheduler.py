"""
Automation layer: generates and emails the weekly SEO report automatically.

Run manually:
    python scheduler.py

Or schedule it (e.g. every Monday 8am):
    0 8 * * MON  python scheduler.py

On Windows, use Task Scheduler pointing at this script.
"""
import os
import json
import datetime
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from dotenv import load_dotenv
load_dotenv()

from gsc_client import get_search_console_data
from ai_engine import generate_weekly_report

SITE_URL      = os.environ.get("GSC_SITE_URL", "https://www.verkeer.co/")
SMTP_EMAIL    = os.environ.get("SMTP_EMAIL", "")
SMTP_PASSWORD = os.environ.get("SMTP_PASSWORD", "")
REPORT_TO     = os.environ.get("REPORT_TO", "")


class _FakeSession(dict):
    pass


def send_email_report(report):
    if not all([SMTP_EMAIL, SMTP_PASSWORD, REPORT_TO]):
        print("Email not configured - skipping send. Add SMTP_EMAIL, SMTP_PASSWORD, REPORT_TO to .env")
        return

    subject = f"Verkeer Weekly SEO Report — {datetime.date.today().strftime('%d %B %Y')}"

    priority_colours = {"High": "#c0392b", "Medium": "#a05a00", "Low": "#16794d"}
    recs_html = ""
    for r in report.get("recommendations", [])[:10]:
        colour = priority_colours.get(r.get("priority", "Low"), "#333")
        recs_html += f"""
        <tr>
          <td style="padding:10px 8px;border-bottom:1px solid #eee;">
            <span style="background:{colour};color:#fff;padding:2px 8px;border-radius:10px;font-size:11px;font-weight:700;">{r.get('priority','')}</span>
          </td>
          <td style="padding:10px 8px;border-bottom:1px solid #eee;font-weight:600;">{r.get('query','')}</td>
          <td style="padding:10px 8px;border-bottom:1px solid #eee;color:#555;font-size:13px;">{r.get('why_it_matters','')}</td>
          <td style="padding:10px 8px;border-bottom:1px solid #eee;color:#1857a8;font-size:13px;">{r.get('recommended_action','')}</td>
        </tr>"""

    h = report.get("headline_stats", {})
    html_body = f"""
    <div style="font-family:Arial,sans-serif;max-width:700px;margin:0 auto;color:#1c1e21;">
      <div style="background:#1857a8;padding:20px 28px;border-radius:8px 8px 0 0;">
        <h1 style="color:#fff;margin:0;font-size:20px;">Verkeer — Weekly SEO Opportunity Report</h1>
        <p style="color:#c5d8f5;margin:6px 0 0;font-size:13px;">
          {report.get('site_url','')} &nbsp;·&nbsp; Last {report.get('date_range_days',28)} days &nbsp;·&nbsp; {datetime.date.today().strftime('%d %B %Y')}
        </p>
      </div>

      <div style="background:#eaf2fb;padding:16px 28px;text-align:center;">
        <span style="margin-right:40px;"><strong style="font-size:24px;color:#1857a8;">{h.get('quick_win_pages',0)}</strong><br><small style="color:#65676b;">Quick-win pages</small></span>
        <span style="margin-right:40px;"><strong style="font-size:24px;color:#1857a8;">{h.get('total_impressions_at_risk',0):,}</strong><br><small style="color:#65676b;">Impressions</small></span>
        <span><strong style="font-size:24px;color:#1857a8;">{h.get('total_clicks_currently',0):,}</strong><br><small style="color:#65676b;">Clicks earned</small></span>
      </div>

      <div style="padding:16px 28px;background:#fff;border-left:4px solid #1857a8;">
        <p style="margin:0;font-size:14px;line-height:1.6;">{report.get('summary','')}</p>
      </div>

      <div style="padding:20px 28px;background:#fff;">
        <h2 style="font-size:16px;margin:0 0 12px;">This week's recommended actions</h2>
        <table style="width:100%;border-collapse:collapse;font-size:13px;">
          <thead>
            <tr style="background:#f5f6f8;">
              <th style="text-align:left;padding:8px;color:#65676b;font-size:11px;">PRIORITY</th>
              <th style="text-align:left;padding:8px;color:#65676b;font-size:11px;">SEARCH TERM</th>
              <th style="text-align:left;padding:8px;color:#65676b;font-size:11px;">WHY IT MATTERS</th>
              <th style="text-align:left;padding:8px;color:#65676b;font-size:11px;">ACTION</th>
            </tr>
          </thead>
          <tbody>{recs_html}</tbody>
        </table>
      </div>

      <div style="padding:14px 28px;background:#f5f6f8;border-radius:0 0 8px 8px;font-size:12px;color:#65676b;text-align:center;">
        Generated automatically by Verkeer SEO Opportunity Engine · ParvinAI
      </div>
    </div>"""

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"]    = SMTP_EMAIL
    msg["To"]      = REPORT_TO
    msg.attach(MIMEText(html_body, "html"))

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(SMTP_EMAIL, SMTP_PASSWORD)
            server.sendmail(SMTP_EMAIL, REPORT_TO, msg.as_string())
        print(f"Report emailed to {REPORT_TO}")
    except Exception as e:
        print(f"Email failed: {e}")


def run():
    session = _FakeSession()
    data = get_search_console_data(session, SITE_URL, days=28)
    report = generate_weekly_report(data, SITE_URL)

    os.makedirs("reports", exist_ok=True)
    filename = f"reports/weekly-report-{datetime.date.today().isoformat()}.json"
    with open(filename, "w") as f:
        json.dump(report, f, indent=2)

    print(f"Report saved: {filename}")
    send_email_report(report)
    return report


if __name__ == "__main__":
    run()
