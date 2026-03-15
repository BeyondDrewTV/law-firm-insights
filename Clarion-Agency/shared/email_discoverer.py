"""
shared/email_discoverer.py
Clarion Agent Office — Deterministic Email Discovery

Attempts to find a real, publicly visible outreach email for a law firm
by fetching its public web pages and extracting mailto links and visible
email addresses from HTML.

RULES (enforced in code, not just in prompts):
  - Only returns emails found verbatim in public HTML
  - Never guesses or synthesizes emails from domain patterns
  - Never returns a name as an email address
  - Validates that every returned string contains "@" and a "."
  - Prefers named partner/attorney emails over generic inboxes
  - Falls back to generic firm inboxes (info@, contact@, office@, hello@)
    only if found explicitly in the HTML

Discovery sequence per firm:
  1. Firm website homepage
  2. /contact or /contact-us
  3. /about or /about-us
  4. /team or /our-team or /attorneys or /lawyers

Cost: up to 5 HTTP fetches per firm, 10s timeout each.
No browser automation. Standard urllib only.

Usage:
    from shared.email_discoverer import discover_email
    result = discover_email("https://www.smithlawfirm.com")
    # result = {
    #   "email": "john@smithlawfirm.com",
    #   "email_source": "https://www.smithlawfirm.com/contact",
    #   "email_type": "partner",     # or "firm_general" or "not_found"
    #   "attempts": 3,
    #   "pages_checked": [...],
    # }
"""

import re
import time
import urllib.request
import urllib.error
from urllib.parse import urljoin, urlparse
from pathlib import Path

# ── Config ────────────────────────────────────────────────────────────────────

FETCH_TIMEOUT = 10      # seconds per page
MAX_PAGES_PER_FIRM = 5  # homepage + up to 4 sub-pages

# Sub-pages to attempt, in priority order
CANDIDATE_PATHS = [
    "/contact",
    "/contact-us",
    "/about",
    "/about-us",
    "/team",
    "/our-team",
    "/attorneys",
    "/lawyers",
    "/people",
    "/staff",
]

# Generic inbox prefixes — accept as fallback only if found in HTML
GENERIC_PREFIXES = {"info", "contact", "office", "hello", "admin", "mail", "law"}

# Email regex — matches explicit mailto: links and bare addresses in text
EMAIL_RE = re.compile(
    r'[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}',
    re.IGNORECASE,
)

# Reject addresses that look like placeholder / no-reply / tracking
REJECT_PATTERNS = re.compile(
    r'(noreply|no-reply|unsubscribe|example\.com|test@|placeholder|@sentry|'
    r'@cloudflare|wordpress|webmaster|postmaster|abuse@)',
    re.IGNORECASE,
)

# ── Helpers ───────────────────────────────────────────────────────────────────

def _fetch_page(url: str) -> tuple[str, str | None]:
    """
    Fetch a URL. Returns (html_text, error_string).
    html_text is "" on failure.
    """
    try:
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "ClarionProspect/1.0 (internal research, read-only)"},
        )
        with urllib.request.urlopen(req, timeout=FETCH_TIMEOUT) as resp:
            charset = "utf-8"
            ct = resp.headers.get("Content-Type", "")
            m = re.search(r"charset=([^\s;]+)", ct)
            if m:
                charset = m.group(1).strip()
            return resp.read().decode(charset, errors="replace"), None
    except urllib.error.HTTPError as e:
        return "", f"HTTP {e.code}"
    except urllib.error.URLError as e:
        return "", f"URLError: {e.reason}"
    except Exception as e:
        return "", f"{type(e).__name__}: {e}"


def _extract_emails_from_html(html: str, base_domain: str) -> list[tuple[str, str]]:
    """
    Extract valid email addresses from HTML.

    Returns list of (email, email_type) pairs, sorted so partner/attorney
    addresses come before generic inboxes.

    Only returns addresses on the same domain or a subdomain of base_domain,
    OR explicitly found in a mailto: link (since those are always intentional).
    """
    found: dict[str, str] = {}  # email → type

    # 1. Extract from mailto: links (highest signal — firm intentionally published these)
    mailto_re = re.compile(r'mailto:([a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,})',
                           re.IGNORECASE)
    for match in mailto_re.finditer(html):
        email = match.group(1).lower().strip()
        if not _is_valid_email(email, base_domain):
            continue
        prefix = email.split("@")[0]
        etype = "firm_general" if prefix in GENERIC_PREFIXES else "partner"
        found[email] = etype

    # 2. Extract bare emails from visible text
    # Strip script/style blocks first to avoid matching minified JS strings
    clean = re.sub(r'<(script|style)[^>]*>.*?</\1>', ' ', html, flags=re.DOTALL | re.IGNORECASE)
    # Remove remaining tags
    clean = re.sub(r'<[^>]+>', ' ', clean)
    for match in EMAIL_RE.finditer(clean):
        email = match.group(0).lower().strip()
        if email in found:
            continue
        if not _is_valid_email(email, base_domain):
            continue
        prefix = email.split("@")[0]
        etype = "firm_general" if prefix in GENERIC_PREFIXES else "partner"
        found[email] = etype

    # Sort: partner first, then firm_general
    result = sorted(found.items(), key=lambda x: (0 if x[1] == "partner" else 1, x[0]))
    return result


def _is_valid_email(email: str, base_domain: str) -> bool:
    """
    True if email is plausibly real and on the correct domain (or a mailto discovery).
    Rejects placeholders, tracking, and off-domain addresses.
    """
    if "@" not in email or "." not in email.split("@")[-1]:
        return False
    if REJECT_PATTERNS.search(email):
        return False
    domain_part = email.split("@")[-1].lower()
    # Only accept addresses on the firm's own domain or common legal directories
    # (avvo.com etc are excluded — they'd be avvo staff addresses)
    # Accept if domain matches or is a subdomain
    if base_domain and (domain_part == base_domain or domain_part.endswith("." + base_domain)):
        return True
    # Also accept if domain was not determinable (base_domain is empty)
    if not base_domain:
        return True
    return False


def _base_domain(url: str) -> str:
    """Extract bare domain from a URL, e.g. 'smithlaw.com' from 'https://www.smithlaw.com/'."""
    try:
        parsed = urlparse(url)
        host = parsed.netloc.lower()
        host = host.removeprefix("www.")
        return host
    except Exception:
        return ""

# ── Main API ──────────────────────────────────────────────────────────────────

def discover_email(firm_website: str) -> dict:
    """
    Attempt email discovery for a firm website.

    Args:
        firm_website: The firm's public website URL (e.g. "https://smithlaw.com")

    Returns:
        {
          "email":        str — the discovered email, or "" if not found
          "email_source": str — URL where the email was found, or ""
          "email_type":   "partner" | "firm_general" | "not_found"
          "attempts":     int — number of pages fetched
          "pages_checked": list[str] — URLs attempted
          "pages_yielded": list[str] — URLs that returned email(s)
          "error":        str | None — last error if all pages failed
        }
    """
    if not firm_website or not firm_website.startswith("http"):
        return _not_found([], 0, "No website URL provided")

    # Normalize URL
    base = firm_website.rstrip("/")
    domain = _base_domain(base)

    pages_checked = []
    pages_yielded = []
    last_error = None
    attempts = 0

    # Build ordered list of pages to try
    urls_to_try = [base]  # homepage first
    for path in CANDIDATE_PATHS:
        candidate = base + path
        if candidate not in urls_to_try:
            urls_to_try.append(candidate)
        if len(urls_to_try) >= MAX_PAGES_PER_FIRM + 1:
            break

    best_email = ""
    best_source = ""
    best_type = "not_found"

    for url in urls_to_try[:MAX_PAGES_PER_FIRM]:
        pages_checked.append(url)
        attempts += 1
        html, error = _fetch_page(url)

        if error:
            last_error = f"{url}: {error}"
            continue  # try next page

        candidates = _extract_emails_from_html(html, domain)
        if not candidates:
            continue

        pages_yielded.append(url)
        # Pick best email from this page
        for email, etype in candidates:
            if etype == "partner":
                # Named partner/attorney email — best possible result, stop immediately
                return {
                    "email": email,
                    "email_source": url,
                    "email_type": "partner",
                    "attempts": attempts,
                    "pages_checked": pages_checked,
                    "pages_yielded": pages_yielded,
                    "error": None,
                }
            elif etype == "firm_general" and best_type != "partner":
                # Generic inbox — keep looking for a partner email, but only store
                # source on the FIRST page that found it (don't overwrite with later pages)
                if not best_email:
                    best_email = email
                    best_source = url
                    best_type = "firm_general"

    if best_email:
        return {
            "email": best_email,
            "email_source": best_source,
            "email_type": best_type,
            "attempts": attempts,
            "pages_checked": pages_checked,
            "pages_yielded": pages_yielded,
            "error": None,
        }

    return _not_found(pages_checked, attempts, last_error)


def _not_found(pages_checked: list, attempts: int, error: str | None) -> dict:
    return {
        "email": "",
        "email_source": "",
        "email_type": "not_found",
        "attempts": attempts,
        "pages_checked": pages_checked,
        "pages_yielded": [],
        "error": error,
    }


def enrich_prospects_with_emails(prospects: list[dict]) -> tuple[list[dict], dict]:
    """
    Run email discovery for each prospect in the list.

    Modifies each prospect dict in-place to add:
        recipient_email, recipient_email_source, recipient_email_type

    Returns (enriched_prospects, summary_stats).

    summary_stats = {
        "partner_email_found": N,
        "firm_general_email_found": N,
        "not_found": N,
        "total": N,
    }
    """
    stats = {"partner_email_found": 0, "firm_general_email_found": 0,
             "not_found": 0, "total": len(prospects)}

    for p in prospects:
        website = p.get("firm_website") or p.get("website") or ""
        if not website:
            p["recipient_email"]        = ""
            p["recipient_email_source"] = ""
            p["recipient_email_type"]   = "not_found"
            stats["not_found"] += 1
            print(f"    [EmailDiscovery] {p.get('firm_name', '?')}: no website — skipped")
            continue

        print(f"    [EmailDiscovery] {p.get('firm_name', '?')}: checking {website}")
        result = discover_email(website)
        p["recipient_email"]        = result["email"]
        p["recipient_email_source"] = result["email_source"]
        p["recipient_email_type"]   = result["email_type"]

        if result["email_type"] == "partner":
            stats["partner_email_found"] += 1
            print(f"      [OK] partner email: {result['email']} (from {result['email_source']})")
        elif result["email_type"] == "firm_general":
            stats["firm_general_email_found"] += 1
            print(f"      [OK] firm general: {result['email']} (from {result['email_source']})")
        else:
            stats["not_found"] += 1
            print(f"      [--] not found ({result['attempts']} pages checked"
                  + (f", last error: {result['error']}" if result["error"] else "") + ")")

    return prospects, stats


# ── Standalone test ───────────────────────────────────────────────────────────
if __name__ == "__main__":
    import sys
    url = sys.argv[1] if len(sys.argv) > 1 else "https://example.com"
    print(f"Testing email discovery for: {url}")
    result = discover_email(url)
    import json
    print(json.dumps(result, indent=2))
