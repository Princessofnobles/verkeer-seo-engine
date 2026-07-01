"""
The AI layer. Takes raw, numeric Search Console data and asks Claude to turn
it into specific, prioritised, plain-English recommendations a marketer
(not a developer) can act on immediately.

If no ANTHROPIC_API_KEY is set, falls back to a rule-based "demo analysis"
so the rest of the prototype still works end-to-end.
"""

import os
import json
import datetime
from anthropic import Anthropic

API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
MODEL = "claude-sonnet-4-6"

client = Anthropic(api_key=API_KEY) if API_KEY else None


SYSTEM_PROMPT = """You are an SEO strategist writing for a marketing agency's leadership team.
You will be given real Google Search Console data: search queries, the page that ranks for them,
clicks, impressions, click-through-rate (CTR) and average position.

Your job: identify the highest-value "quick win" opportunities — pages already ranking on page 1-2
(positions 4-15) that are getting impressions but underperforming on clicks — and explain in plain,
non-technical English:
1. Why each one matters (in terms of traffic/revenue potential, not jargon)
2. What specifically to do about it (e.g. rewrite title tag, add FAQ schema, internal linking,
   improve meta description, expand content depth, target featured snippet)
3. A priority ranking (High / Medium / Low) based on impressions x how close it is to page 1

Always reply with valid JSON only, no markdown formatting, no commentary outside the JSON.
"""


def analyze_opportunities(opportunities):
    if not opportunities:
        return {"source": "none", "recommendations": [], "summary": "No opportunities found in the selected date range."}

    if client is None:
        return _demo_analysis(opportunities)

    user_prompt = f"""Here are the SEO opportunities (positions 4-15, page-1/2 rankings):

{json.dumps(opportunities[:15], indent=2)}

Return JSON in this exact shape:
{{
  "summary": "2-3 sentence plain-English summary of the overall opportunity",
  "recommendations": [
    {{
      "query": "...",
      "page": "...",
      "priority": "High|Medium|Low",
      "why_it_matters": "plain English, 1-2 sentences",
      "recommended_action": "specific, concrete next step",
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
        fallback = _demo_analysis(opportunities)
        fallback["error"] = f"Claude API call failed, showing rule-based analysis instead: {e}"
        return fallback


def generate_weekly_report(gsc_data, site_url):
    quick_wins = gsc_data.get("quick_wins", [])
    analysis = analyze_opportunities(quick_wins)

    total_impressions = sum(r["impressions"] for r in quick_wins)
    total_clicks = sum(r["clicks"] for r in quick_wins)

    report = {
        "generated_at": datetime.datetime.utcnow().isoformat(),
        "site_url": site_url,
        "date_range_days": gsc_data.get("date_range_days", 28),
        "data_source": gsc_data.get("source"),
        "headline_stats": {
            "quick_win_pages": len(quick_wins),
            "total_impressions_at_risk": total_impressions,
            "total_clicks_currently": total_clicks,
        },
        "summary": analysis.get("summary", ""),
        "recommendations": analysis.get("recommendations", []),
    }
    return report


def _demo_analysis(opportunities):
    """Rule-based fallback when no Claude API key is configured."""
    recs = []
    for o in opportunities[:15]:
        position = o["position"]
        impressions = o["impressions"]

        if position <= 7:
            priority = "High" if impressions > 300 else "Medium"
            action = "On page 1 but not top 3 — strengthen the title tag and add the keyword naturally to the first paragraph to push toward position 1-3."
        elif position <= 10:
            priority = "High" if impressions > 500 else "Medium"
            action = "Bottom of page 1 — improve content depth and add internal links from related pages to build relevance."
        else:
            priority = "Medium" if impressions > 500 else "Low"
            action = "Top of page 2 — a small relevance boost (better meta description, FAQ section) can push this onto page 1."

        recs.append({
            "query": o["query"],
            "page": o["page"],
            "priority": priority,
            "why_it_matters": f"This page is already getting {impressions} impressions for this search but only converting {o['ctr']}% into clicks — meaning visibility exists but the listing isn't compelling enough yet.",
            "recommended_action": action,
            "estimated_effort": "Medium",
        })

    summary = (
        f"There are {len(opportunities)} pages ranking on page 1-2 of Google that are already "
        f"visible to searchers but under-converting on clicks. Fixing the highest-impression ones "
        f"first is the fastest way to grow organic traffic without creating any new content."
    )
    return {"source": "rule-based", "summary": summary, "recommendations": recs}
