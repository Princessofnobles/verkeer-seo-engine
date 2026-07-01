"""
Handles everything related to Google: OAuth login, pulling real data from the
Search Console API, and a realistic DEMO MODE so the app works instantly even
before Google credentials are configured (useful for the interview demo).
"""

import os
import random
import datetime
from google_auth_oauthlib.flow import Flow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
import requests

SCOPES = [
    "https://www.googleapis.com/auth/webmasters.readonly",
    "https://www.googleapis.com/auth/analytics.readonly",
]

CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID", "")
CLIENT_SECRET = os.environ.get("GOOGLE_CLIENT_SECRET", "")
REDIRECT_URI = os.environ.get("GOOGLE_REDIRECT_URI", "http://localhost:5000/oauth2callback")
GA4_PROPERTY_ID = os.environ.get("GA4_PROPERTY_ID", "")


def _client_config():
    return {
        "web": {
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": [REDIRECT_URI],
        }
    }


def get_auth_url():
    flow = Flow.from_client_config(_client_config(), scopes=SCOPES, redirect_uri=REDIRECT_URI)
    auth_url, _ = flow.authorization_url(access_type="offline", include_granted_scopes="true", prompt="consent")
    return auth_url


def exchange_code_for_token(code):
    flow = Flow.from_client_config(_client_config(), scopes=SCOPES, redirect_uri=REDIRECT_URI)
    flow.fetch_token(code=code)
    creds = flow.credentials
    return {
        "token": creds.token,
        "refresh_token": creds.refresh_token,
        "token_uri": creds.token_uri,
        "client_id": creds.client_id,
        "client_secret": creds.client_secret,
        "scopes": creds.scopes,
    }


def has_valid_credentials(session):
    return bool(CLIENT_ID and CLIENT_SECRET and session.get("credentials"))


def _credentials_from_session(session):
    info = session.get("credentials")
    if not info:
        return None
    creds = Credentials(
        token=info["token"],
        refresh_token=info.get("refresh_token"),
        token_uri=info["token_uri"],
        client_id=info["client_id"],
        client_secret=info["client_secret"],
        scopes=info["scopes"],
    )
    if not creds.valid and creds.refresh_token:
        creds.refresh(Request())
        session["credentials"]["token"] = creds.token
    return creds


def get_search_console_data(session, site_url, days=28):
    """
    Returns:
    {
      "source": "live" | "demo",
      "site_url": ...,
      "date_range_days": 28,
      "rows": [ {query, page, clicks, impressions, ctr, position}, ... ],
      "quick_wins": [ ...rows where position is 4-15... ]
    }
    """
    creds = _credentials_from_session(session)

    if creds is None:
        return _demo_data(site_url, days)

    try:
        end_date = datetime.date.today() - datetime.timedelta(days=2)
        start_date = end_date - datetime.timedelta(days=days)

        url = f"https://www.googleapis.com/webmasters/v3/sites/{requests.utils.quote(site_url, safe='')}/searchAnalytics/query"
        headers = {"Authorization": f"Bearer {creds.token}", "Content-Type": "application/json"}
        body = {
            "startDate": start_date.isoformat(),
            "endDate": end_date.isoformat(),
            "dimensions": ["query", "page"],
            "rowLimit": 1000,
        }
        resp = requests.post(url, headers=headers, json=body, timeout=20)
        resp.raise_for_status()
        raw_rows = resp.json().get("rows", [])

        rows = []
        for r in raw_rows:
            query, page = r["keys"]
            rows.append({
                "query": query,
                "page": page,
                "clicks": r.get("clicks", 0),
                "impressions": r.get("impressions", 0),
                "ctr": round(r.get("ctr", 0) * 100, 2),
                "position": round(r.get("position", 0), 1),
            })

        quick_wins = [r for r in rows if 4 <= r["position"] <= 15 and r["impressions"] >= 10]
        quick_wins.sort(key=lambda r: r["impressions"], reverse=True)

        return {
            "source": "live",
            "site_url": site_url,
            "date_range_days": days,
            "rows": rows,
            "quick_wins": quick_wins[:25],
        }
    except Exception as e:
        demo = _demo_data(site_url, days)
        demo["error"] = f"Live API call failed, showing demo data instead: {e}"
        return demo


def _demo_data(site_url, days):
    """Realistic sample data so the prototype is fully demonstrable without live credentials."""
    random.seed(42)
    sample_queries = [
        ("digital marketing agency london", "/services/digital-marketing/"),
        ("seo agency near me", "/services/seo/"),
        ("ppc management agency", "/services/ppc/"),
        ("how much does seo cost uk", "/blog/seo-pricing-guide/"),
        ("best digital marketing agency for ecommerce", "/industries/ecommerce/"),
        ("content marketing services london", "/services/content-marketing/"),
        ("local seo services", "/services/local-seo/"),
        ("marketing automation agency", "/services/marketing-automation/"),
        ("google ads management company", "/services/google-ads/"),
        ("social media marketing agency uk", "/services/social-media/"),
        ("link building services", "/services/link-building/"),
        ("technical seo audit", "/services/technical-seo/"),
        ("b2b digital marketing agency", "/industries/b2b/"),
        ("ecommerce ppc agency", "/industries/ecommerce-ppc/"),
        ("seo consultant london", "/about/seo-consultant/"),
        ("digital marketing case studies", "/case-studies/"),
        ("conversion rate optimisation agency", "/services/cro/"),
        ("hubspot agency partner uk", "/partners/hubspot/"),
        ("shopify seo agency", "/industries/shopify-seo/"),
        ("email marketing agency london", "/services/email-marketing/"),
    ]

    rows = []
    for query, page in sample_queries:
        position = round(random.uniform(3.5, 18), 1)
        impressions = random.randint(80, 2400)
        ctr_pct = round(random.uniform(0.5, 9.0), 2)
        clicks = max(0, round(impressions * (ctr_pct / 100)))
        rows.append({
            "query": query, "page": site_url.rstrip("/") + page,
            "clicks": clicks, "impressions": impressions, "ctr": ctr_pct, "position": position,
        })

    quick_wins = [r for r in rows if 4 <= r["position"] <= 15]
    quick_wins.sort(key=lambda r: r["impressions"], reverse=True)

    return {
        "source": "demo",
        "site_url": site_url,
        "date_range_days": days,
        "rows": rows,
        "quick_wins": quick_wins,
    }
