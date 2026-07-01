import os
import json
import datetime

API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
MODEL   = "claude-sonnet-4-6"

SYSTEM_PROMPT = """You are an SEO strategist writing for a marketing agency's leadership team.
You will be given real Google Search Console data and must identify quick-win opportunities.
Reply with valid JSON only — no markdown, no backticks, no commentary outside the JSON."""


def _get_client():
    if not API_KEY:
        return None
    try:
        from anthropic import Anthropic
        return Anthropic(api_key=API_KEY)
    except Exception:
        return None


def analyze_opportunities(opportunities):
    if not opportunities:
        return {"source": "none", "recommendations": [], "summary": "No opportunities found."}

    client = _get_client()
    if client is None:
        return _demo_analysis(opportunities)

    user_prompt = f"""Here are the SEO quick-win opportunities (positions 4-15):

{json.dumps(opportunities[:15], indent=2)}

Return JSON in this exact shape:
{{
  "summary": "2-3 sentence plain-English summary",
  "recommendations": [
    {{
      "query": "...",
      "page": "...",
      "priority": "High|Medium|Low",
      "why_it_matters": "plain English, 1-2 sentences",
      "recommended_action": "specific next step",
      "estimated_effort": "Low|Medium|High"
    }}
  ]
}}"""

    try:
        msg = client.messages.create(
            model=MODEL,
            max_tokens=2000,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_prompt}],
        )
        text = msg.content[0].text.strip()
        text = text.replace("```json", "").replace("```", "").strip()
        result = json.loads(text)
        result["source"] = "claude"
        return result
    except Exception as e:
        result = _demo_analysis(opportunities)
        result["error"] = str(e)
        return result


def generate_weekly_report(gsc_data, site_url):
    quick_wins = gsc_data.get("quick_wins", [])
    analysis   = analyze_opportunities(quick_wins)

    total_impressions = sum(r["impressions"] for r in quick_wins)
    total_clicks      = sum(r["clicks"] for r in quick_wins)

    return {
        "generated_at":    datetime.datetime.utcnow().isoformat(),
        "site_url":        site_url,
        "date_range_days": gsc_data.get("date_range_days", 28),
        "data_source":     gsc_data.get("source"),
        "headline_stats": {
            "quick_win_pages":            len(quick_wins),
            "total_impressions_at_risk":  total_impressions,
            "total_clicks_currently":     total_clicks,
        },
        "summary":         analysis.get("summary", ""),
        "recommendations": analysis.get("recommendations", []),
    }


def _demo_analysis(opportunities):
    recs = []
    for o in opportunities[:15]:
        position    = o["position"]
        impressions = o["impressions"]

        if position <= 7:
            priority = "High" if impressions > 300 else "Medium"
            action   = "Strengthen the title tag and add the keyword naturally to the first paragraph to push toward position 1-3."
        elif position <= 10:
            priority = "High" if impressions > 500 else "Medium"
            action   = "Improve content depth and add internal links from related pages to build relevance."
        else:
            priority = "Medium" if impressions > 500 else "Low"
            action   = "Add an FAQ section and improve the meta description to push onto page 1."

        recs.append({
            "query":              o["query"],
            "page":               o["page"],
            "priority":           priority,
            "why_it_matters":     f"This page gets {impressions} impressions but only a {o['ctr']}% click rate — visibility exists but the listing isn't compelling enough yet.",
            "recommended_action": action,
            "estimated_effort":   "Medium",
        })

    summary = (
        f"There are {len(opportunities)} pages ranking on page 1-2 of Google that are already "
        f"visible but under-converting on clicks. Fixing the highest-impression ones first is "
        f"the fastest way to grow organic traffic without creating new content."
    )
    return {"source": "rule-based", "summary": summary, "recommendations": recs}
