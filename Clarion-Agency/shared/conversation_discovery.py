"""
conversation_discovery.py
Clarion — Conversation Discovery Module

Discovers public discussions related to the problem areas Clarion solves.
Writes findings to data/comms/discovered_conversations.md for the Comms agent.

SAFETY CONTRACT:
  - Read-only. No posting, no login, no account creation, no interaction.
  - Uses only Reddit's public JSON search API (no auth required).
  - Generates manual-review search links for LinkedIn and legal forums.
  - Writes one local file. No other side effects.

Dependencies:
  - requests (already installed via openrouter_client.py requirements)

Usage (called automatically by run_clarion_agent_office.py):
  from shared.conversation_discovery import run as run_conversation_discovery
  run_conversation_discovery()
"""

import json
import time
import datetime
import traceback
from pathlib import Path

import requests

BASE_DIR = Path(__file__).resolve().parent.parent
OUTPUT_PATH = BASE_DIR / "data" / "comms" / "discovered_conversations.md"

DATE = datetime.date.today().isoformat()

# ── Search configuration ───────────────────────────────────────────────────────

# Reddit subreddits most likely to contain law firm operator discussions
REDDIT_SUBREDDITS = [
    "lawfirm",
    "legaladvice",
    "LegalTech",
    "smallbusiness",
    "Lawyertalk",
]

# Query terms mapped to the problem area they represent
REDDIT_QUERIES = [
    ("law firm client reviews",          "Client Reviews & Feedback"),
    ("law firm negative reviews",        "Client Reviews & Feedback"),
    ("attorney client feedback",         "Client Reviews & Feedback"),
    ("law firm reputation management",   "Reputation Management"),
    ("law firm client communication",    "Client Communication"),
    ("legal practice management issues", "Practice Management"),
    ("law firm operations problems",     "Firm Operations"),
    ("law firm client satisfaction",     "Client Experience"),
]

# Request headers — identify as a research bot, not a browser
HEADERS = {
    "User-Agent": "ClarionResearchBot/1.0 (internal market research; read-only; no posting)",
}

# Reddit rate limit: stay well under their 60 req/min limit
REQUEST_DELAY_SECONDS = 2

# Maximum results to collect total (to keep the report scannable)
MAX_RESULTS = 10

# Minimum score to include a Reddit post (filters out zero-engagement noise)
MIN_REDDIT_SCORE = 2


# ── Reddit discovery ───────────────────────────────────────────────────────────

def _reddit_search(query: str, topic_label: str) -> list[dict]:
    """
    Search Reddit's public JSON API for a query.
    Returns a list of discovery signal dicts.
    No auth required. Read-only.
    """
    url = "https://www.reddit.com/search.json"
    params = {
        "q": query,
        "sort": "relevance",
        "t": "month",      # past month only — keep signals fresh
        "limit": 5,
        "type": "link",
    }

    try:
        response = requests.get(
            url,
            params=params,
            headers=HEADERS,
            timeout=15,
        )
        if response.status_code != 200:
            print(f"  [DISCOVERY] Reddit returned {response.status_code} for query: {query!r}")
            return []

        data = response.json()
        posts = data.get("data", {}).get("children", [])
        results = []

        for post in posts:
            p = post.get("data", {})
            score = p.get("score", 0)
            if score < MIN_REDDIT_SCORE:
                continue

            title     = p.get("title", "").strip()
            permalink = p.get("permalink", "")
            subreddit = p.get("subreddit", "")
            selftext  = p.get("selftext", "").strip()
            num_comments = p.get("num_comments", 0)
            created_utc  = p.get("created_utc", 0)

            if not title or not permalink:
                continue

            # Build the full URL
            link = f"https://www.reddit.com{permalink}"

            # Derive a short summary from title + first 200 chars of body
            body_preview = selftext[:200].replace("\n", " ").strip() if selftext else ""
            summary = title
            if body_preview:
                summary += f" — {body_preview}..."

            # Date string
            post_date = datetime.datetime.utcfromtimestamp(created_utc).strftime("%Y-%m-%d") \
                if created_utc else "unknown"

            results.append({
                "platform":     "Reddit",
                "subreddit":    f"r/{subreddit}",
                "topic_area":   topic_label,
                "title":        title,
                "link":         link,
                "summary":      summary,
                "score":        score,
                "num_comments": num_comments,
                "post_date":    post_date,
                "query_used":   query,
            })

        return results

    except Exception as e:
        print(f"  [DISCOVERY] Reddit search failed for {query!r}: {e}")
        return []


# ── Manual search links (LinkedIn, legal forums) ──────────────────────────────

def _build_manual_search_links() -> list[dict]:
    """
    Build a list of manual-review search links for platforms that
    require authentication or don't offer a public JSON API.
    These are NOT fetched — they are surfaced as discovery hints for Comms.
    """
    import urllib.parse

    manual_queries = [
        ("LinkedIn",       "law firm client reviews software",          "Client Reviews"),
        ("LinkedIn",       "law firm reputation management",            "Reputation Management"),
        ("LinkedIn",       "attorney client feedback process",          "Client Feedback"),
        ("Google Groups",  "law firm client feedback tool site:groups.google.com", "Legal Communities"),
        ("MyCase Community", "client reviews feedback",                 "Practice Management"),
    ]

    links = []
    for platform, query, topic_area in manual_queries:
        if platform == "LinkedIn":
            encoded = urllib.parse.quote_plus(query)
            url = f"https://www.linkedin.com/search/results/content/?keywords={encoded}"
        else:
            encoded = urllib.parse.quote_plus(query)
            url = f"https://www.google.com/search?q={encoded}"

        links.append({
            "platform":   platform,
            "topic_area": topic_area,
            "query":      query,
            "link":       url,
            "note":       "Manual review required — not auto-fetched",
        })

    return links


# ── Relevance scoring ──────────────────────────────────────────────────────────

# Keywords that signal high relevance to Clarion's value proposition
_HIGH_RELEVANCE_KEYWORDS = [
    "review", "feedback", "reputation", "client", "complaint",
    "google review", "negative review", "respond", "rating",
    "satisfaction", "communication", "tracking", "pattern",
    "recurring", "manage", "oversight", "governance",
]

def _score_relevance(signal: dict) -> int:
    """
    Return a simple relevance score based on keyword presence in title/summary.
    Higher = more relevant to Clarion's core problems.
    """
    text = (signal.get("title", "") + " " + signal.get("summary", "")).lower()
    return sum(1 for kw in _HIGH_RELEVANCE_KEYWORDS if kw in text)


def _why_it_matters(signal: dict) -> str:
    """
    Generate a brief 'Why It Matters' string based on topic area.
    """
    area = signal.get("topic_area", "")
    mapping = {
        "Client Reviews & Feedback": (
            "Directly related to Clarion's core value: surfacing patterns "
            "in client reviews law firms currently manage manually."
        ),
        "Reputation Management": (
            "Signals a firm actively thinking about reputation — "
            "a strong entry point for Clarion's governance brief."
        ),
        "Client Communication": (
            "Client communication gaps are upstream of the review problems "
            "Clarion helps firms diagnose and fix."
        ),
        "Practice Management": (
            "Practice management frustrations often include feedback blind spots — "
            "a category Clarion speaks directly to."
        ),
        "Firm Operations": (
            "Operational pain at law firms frequently surfaces in client experience data "
            "that Clarion classifies and acts on."
        ),
        "Client Experience": (
            "Client experience discussions are the exact ICP pain point "
            "Clarion was built to address."
        ),
    }
    return mapping.get(area, "Relevant to Clarion's problem domain.")


def _participation_angle(signal: dict) -> str:
    """
    Suggest a non-promotional participation angle for Comms to evaluate.
    """
    area = signal.get("topic_area", "")
    mapping = {
        "Client Reviews & Feedback": (
            "Share insight on identifying recurring patterns in client complaints "
            "rather than treating each review as a one-off event."
        ),
        "Reputation Management": (
            "Offer a perspective on how systematic feedback analysis differs from "
            "reactive reputation monitoring — educate, don't promote."
        ),
        "Client Communication": (
            "Contribute a concrete observation about how communication gaps "
            "show up in review language before they escalate."
        ),
        "Practice Management": (
            "Ask a clarifying question or share a relevant operational insight — "
            "position as a practitioner, not a vendor."
        ),
        "Firm Operations": (
            "Share a specific, useful observation about turning operational signals "
            "into decision-ready information for firm leadership."
        ),
        "Client Experience": (
            "Engage with the specific pain described. Share what others in similar "
            "firms have found useful without naming Clarion directly."
        ),
    }
    return mapping.get(area, "Contribute a useful, educational observation relevant to the discussion.")


# ── Report writer ──────────────────────────────────────────────────────────────

def _write_report(signals: list[dict], manual_links: list[dict], errors: list[str]) -> None:
    """
    Write the discovered conversations to data/comms/discovered_conversations.md.
    Always writes the file — never crashes if signals are empty.
    """
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)

    lines = [
        f"# Discovered Conversations",
        f"# Clarion — Conversation Discovery Output",
        f"# Generated: {DATE}",
        f"# Source: shared/conversation_discovery.py",
        f"# SAFETY: Read-only discovery. No posting. No login. No external interaction.",
        f"",
        f"---",
        f"",
    ]

    if not signals:
        lines += [
            "## DISCOVERED CONVERSATIONS",
            "",
            "No relevant conversations detected during this cycle.",
            "",
            "> Discovery ran successfully. No Reddit posts met the relevance threshold.",
            "> This may reflect low recent activity on the search topics,",
            "> or Reddit rate limiting. Manual search links are provided below.",
            "",
        ]
    else:
        lines += [
            f"## DISCOVERED CONVERSATIONS",
            f"",
            f"Total signals found: {len(signals)} (ranked by relevance)",
            f"",
        ]
        for i, s in enumerate(signals, 1):
            lines += [
                f"---",
                f"",
                f"### DISCOVERY SIGNAL {i}",
                f"Platform:   {s['platform']} — {s.get('subreddit', '')}",
                f"Topic Area: {s['topic_area']}",
                f"Posted:     {s['post_date']}",
                f"Engagement: {s['score']} upvotes · {s['num_comments']} comments",
                f"Link:       {s['link']}",
                f"",
                f"**Summary:**",
                f"{s['summary']}",
                f"",
                f"**Why It Matters:**",
                f"{_why_it_matters(s)}",
                f"",
                f"**Suggested Participation Angle:**",
                f"{_participation_angle(s)}",
                f"",
                f"*Query used: `{s['query_used']}`*",
                f"",
            ]

    # Manual search links section
    lines += [
        "---",
        "",
        "## MANUAL DISCOVERY LINKS",
        "",
        "These platforms require manual review. Links below are pre-formed search queries.",
        "Comms: open each link, review results, and select discussions worth participating in.",
        "",
    ]
    for m in manual_links:
        lines += [
            f"- **{m['platform']}** ({m['topic_area']})",
            f"  Query: `{m['query']}`",
            f"  Link: {m['link']}",
            f"",
        ]

    # Error log (transparent — agents should know if discovery was degraded)
    if errors:
        lines += [
            "---",
            "",
            "## DISCOVERY ERRORS THIS RUN",
            "",
            "> The following errors occurred during discovery.",
            "> Signals may be incomplete. This does not block the agent run.",
            "",
        ]
        for e in errors:
            lines += [f"- {e}"]
        lines += [""]

    lines += [
        "---",
        f"*End of discovery output — {DATE}*",
    ]

    OUTPUT_PATH.write_text("\n".join(lines), encoding="utf-8")


# ── Main entry point ───────────────────────────────────────────────────────────

def run() -> Path:
    """
    Run conversation discovery. Always returns OUTPUT_PATH.
    Never raises — all errors are caught and written to the report.
    """
    print(f"\n  [DISCOVERY] Starting conversation discovery...")
    print(f"  [DISCOVERY] Output → {OUTPUT_PATH.relative_to(BASE_DIR)}")

    all_signals: list[dict] = []
    errors: list[str] = []

    # ── Reddit search ──────────────────────────────────────────────────────────
    for query, topic_label in REDDIT_QUERIES:
        if len(all_signals) >= MAX_RESULTS:
            break
        try:
            results = _reddit_search(query, topic_label)
            all_signals.extend(results)
            print(f"  [DISCOVERY] Reddit '{query}' → {len(results)} result(s)")
        except Exception as e:
            msg = f"Reddit search error for '{query}': {e}"
            errors.append(msg)
            print(f"  [DISCOVERY] {msg}")
        time.sleep(REQUEST_DELAY_SECONDS)

    # ── Deduplicate by link ────────────────────────────────────────────────────
    seen_links: set[str] = set()
    deduped: list[dict] = []
    for s in all_signals:
        if s["link"] not in seen_links:
            seen_links.add(s["link"])
            deduped.append(s)

    # ── Rank by relevance score, then engagement ───────────────────────────────
    deduped.sort(key=lambda s: (_score_relevance(s), s.get("score", 0)), reverse=True)
    top_signals = deduped[:MAX_RESULTS]

    # ── Manual search links ────────────────────────────────────────────────────
    manual_links = _build_manual_search_links()

    # ── Write report ───────────────────────────────────────────────────────────
    _write_report(top_signals, manual_links, errors)

    print(f"  [DISCOVERY] Complete — {len(top_signals)} signal(s) written.")
    return OUTPUT_PATH
