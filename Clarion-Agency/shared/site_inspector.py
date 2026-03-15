"""
shared/site_inspector.py
Clarion Agent Office — Live Site Inspector

Fetches the real production site before the Product Experience agent runs.
Implements Render cold-start retry logic with honest failure reporting.

Fetch config:
  timeout  : 25 seconds per attempt
  attempts : 5
  sleep    : 20 seconds between attempts

A successful fetch requires:
  - HTTP 200
  - Non-trivial HTML (>= MIN_HTML_BYTES, real DOM markers present)
  - Not a loading spinner / empty shell / error page

Routes fetched (in order):
  1. / (homepage)  — REQUIRED for success
  2. /login        — opportunistic, logged if homepage succeeded
  3. /feedback     — opportunistic, logged if homepage succeeded

Outputs:
  data/ux/live_homepage_snapshot.html   — homepage HTML (if successful)
  data/ux/live_login_snapshot.html      — login page HTML (if successful)
  data/ux/live_feedback_snapshot.html   — feedback page HTML (if successful)
  data/ux/inspection_meta.json          — fetch metadata for data context injection

Usage:
  from shared.site_inspector import run_inspection
  result = run_inspection()
  # result["success"]          bool
  # result["attempts_needed"]  int (1-5, or 5 if failed)
  # result["homepage_bytes"]   int
  # result["routes_fetched"]   list[str]
  # result["failure_reason"]   str | None
  # result["snapshot_path"]    Path | None
  # result["context_block"]    str  (ready to inject into agent data_context)
"""

import json
import time
import urllib.request
import urllib.error
from datetime import datetime, timezone
from pathlib import Path

# ── Config ────────────────────────────────────────────────────────────────────

BASE_URL    = "https://law-firm-feedback-saas.onrender.com"
TIMEOUT_S   = 25
MAX_ATTEMPTS = 5
SLEEP_S     = 20
MIN_HTML_BYTES = 800

# Markers that confirm a real page (not a loading shell or empty document)
NON_TRIVIAL_MARKERS = [
    b"<body", b"<div", b"<main", b"<nav",
    b"<header", b"<section", b"<form", b"<h1",
]

# Markers that indicate a loading fallback / error page — reject these
REJECT_MARKERS = [
    b"loading...",
    b"please wait",
    b"application error",
    b"502 bad gateway",
    b"503 service unavailable",
    b"<html></html>",
    b"<!doctype html><html></html>",
]

# Routes to attempt after homepage succeeds
SECONDARY_ROUTES = [
    ("/login",    "live_login_snapshot.html"),
    ("/feedback", "live_feedback_snapshot.html"),
]


BASE_DIR = Path(__file__).resolve().parent.parent
UX_DIR   = BASE_DIR / "data" / "ux"


# ── Helpers ───────────────────────────────────────────────────────────────────

def _is_non_trivial(html_bytes: bytes) -> bool:
    """Return True if the HTML looks like a real rendered page."""
    if len(html_bytes) < MIN_HTML_BYTES:
        return False
    lower = html_bytes.lower()
    has_dom = any(m in lower for m in NON_TRIVIAL_MARKERS)
    is_shell = any(m in lower[:2000] for m in REJECT_MARKERS)
    return has_dom and not is_shell


def _fetch_url(url: str) -> tuple[int | None, bytes, float, str | None]:
    """
    Single HTTP GET. Returns (status, body, elapsed_s, error_str).
    error_str is None on success.
    """
    t0 = time.time()
    try:
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "ClarionInspector/1.0 (internal UX audit, read-only)"},
        )
        with urllib.request.urlopen(req, timeout=TIMEOUT_S) as resp:
            body = resp.read()
            return resp.status, body, round(time.time() - t0, 2), None
    except urllib.error.HTTPError as e:
        return e.code, b"", round(time.time() - t0, 2), f"HTTP {e.code} {e.reason}"
    except urllib.error.URLError as e:
        # e.reason may itself be an exception (SSLError, OSError, etc.)
        reason = str(e.reason) if e.reason else str(e)
        return None, b"", round(time.time() - t0, 2), f"URLError: {reason}"
    except UnicodeEncodeError as e:
        # Proxy or tunnel returned non-ASCII in the error response
        return None, b"", round(time.time() - t0, 2), f"Network/proxy encoding error: {e}"
    except Exception as e:
        return None, b"", round(time.time() - t0, 2), f"Error: {type(e).__name__}: {e}"


def _save_snapshot(filename: str, html_bytes: bytes) -> Path:
    UX_DIR.mkdir(parents=True, exist_ok=True)
    path = UX_DIR / filename
    path.write_bytes(html_bytes)
    return path


def _save_meta(meta: dict) -> None:
    UX_DIR.mkdir(parents=True, exist_ok=True)
    (UX_DIR / "inspection_meta.json").write_text(
        json.dumps(meta, indent=2, default=str), encoding="utf-8"
    )


# ── Main inspection ───────────────────────────────────────────────────────────

def run_inspection() -> dict:
    """
    Attempt to fetch the live site with retry logic.
    Returns a result dict suitable for injecting into agent data_context.
    """
    now_iso = datetime.now(timezone.utc).isoformat()
    homepage_url = BASE_URL + "/"

    print(f"  [SiteInspector] Starting live site inspection: {homepage_url}")
    print(f"  [SiteInspector] Config: timeout={TIMEOUT_S}s, attempts={MAX_ATTEMPTS}, sleep={SLEEP_S}s")

    attempts_log = []
    success = False
    homepage_bytes = b""
    snapshot_path  = None
    failure_reason = None
    attempts_needed = MAX_ATTEMPTS

    # ── Homepage fetch with retry ─────────────────────────────────────────────
    for attempt in range(1, MAX_ATTEMPTS + 1):
        print(f"  [SiteInspector] Attempt {attempt}/{MAX_ATTEMPTS}...", flush=True)
        status, body, elapsed, error = _fetch_url(homepage_url)

        attempt_log = {
            "attempt": attempt,
            "status": status,
            "bytes": len(body),
            "elapsed_s": elapsed,
            "error": error,
        }

        if status == 200 and _is_non_trivial(body):
            attempt_log["result"] = "success"
            attempts_log.append(attempt_log)
            attempts_needed = attempt
            success = True
            homepage_bytes = body
            snapshot_path = _save_snapshot("live_homepage_snapshot.html", body)
            print(f"  [SiteInspector] SUCCESS on attempt {attempt} — "
                  f"{len(body):,} bytes in {elapsed}s")
            break
        elif status == 200:
            attempt_log["result"] = "trivial_response"
            print(f"  [SiteInspector] Attempt {attempt}: HTTP 200 but trivial/shell page "
                  f"({len(body)} bytes) — retrying")
        elif status is not None:
            attempt_log["result"] = f"http_error_{status}"
            print(f"  [SiteInspector] Attempt {attempt}: HTTP {status} after {elapsed}s — "
                  f"may be cold-starting, retrying")
        else:
            attempt_log["result"] = f"network_error"
            print(f"  [SiteInspector] Attempt {attempt}: {error} after {elapsed}s")

        attempts_log.append(attempt_log)

        if attempt < MAX_ATTEMPTS:
            print(f"  [SiteInspector] Sleeping {SLEEP_S}s (Render cold-start tolerance)...")
            time.sleep(SLEEP_S)

    if not success:
        failure_reason = (
            f"Homepage unreachable after {MAX_ATTEMPTS} attempts "
            f"({MAX_ATTEMPTS * SLEEP_S + MAX_ATTEMPTS * TIMEOUT_S}s total window). "
            "Render may be cold-starting or experiencing downtime."
        )
        print(f"  [SiteInspector] FAILED: {failure_reason}")

    # ── Secondary routes (only if homepage succeeded) ─────────────────────────
    routes_fetched = ["/"] if success else []
    secondary_results = {}

    if success:
        for route, filename in SECONDARY_ROUTES:
            url = BASE_URL + route
            print(f"  [SiteInspector] Fetching secondary route: {route}")
            s_status, s_body, s_elapsed, s_error = _fetch_url(url)
            if s_status == 200 and _is_non_trivial(s_body):
                _save_snapshot(filename, s_body)
                routes_fetched.append(route)
                secondary_results[route] = {
                    "status": s_status, "bytes": len(s_body),
                    "elapsed_s": s_elapsed, "saved": filename,
                }
                print(f"  [SiteInspector] {route}: OK — {len(s_body):,} bytes")
            else:
                secondary_results[route] = {
                    "status": s_status, "bytes": len(s_body),
                    "elapsed_s": s_elapsed, "error": s_error or "trivial response",
                }
                print(f"  [SiteInspector] {route}: skipped — {s_error or 'trivial response'}")

    # ── Save inspection metadata ──────────────────────────────────────────────
    meta = {
        "inspection_timestamp": now_iso,
        "live_url": BASE_URL,
        "success": success,
        "attempts_needed": attempts_needed if success else MAX_ATTEMPTS,
        "attempts_log": attempts_log,
        "homepage_bytes": len(homepage_bytes),
        "routes_fetched": routes_fetched,
        "secondary_results": secondary_results,
        "snapshot_path": str(snapshot_path) if snapshot_path else None,
        "failure_reason": failure_reason,
    }
    _save_meta(meta)

    # ── Build context block for injection into agent data_context ─────────────
    if success:
        # Truncate HTML to a meaningful but bounded size for the LLM
        # 120KB of raw HTML → trim to first 60KB (captures full above-fold + structure)
        html_str = homepage_bytes.decode("utf-8", errors="replace")
        html_excerpt = html_str[:60_000]
        if len(html_str) > 60_000:
            html_excerpt += f"\n\n[... HTML truncated — full snapshot at data/ux/live_homepage_snapshot.html ...]"

        secondary_note = ""
        for route in routes_fetched[1:]:
            sr = secondary_results.get(route, {})
            secondary_note += (
                f"\n### Live Site Snapshot — {route}\n"
                f"Status: HTTP {sr.get('status')} | {sr.get('bytes', 0):,} bytes\n"
                f"Snapshot saved: data/ux/{[f for r, f in SECONDARY_ROUTES if r == route][0]}\n"
            )

        context_block = (
            f"### Live Site Inspection — SUCCESSFUL\n"
            f"Inspection timestamp : {now_iso}\n"
            f"URL inspected        : {BASE_URL}/\n"
            f"Attempts needed      : {attempts_needed} of {MAX_ATTEMPTS}\n"
            f"Homepage bytes       : {len(homepage_bytes):,}\n"
            f"Routes fetched       : {', '.join(routes_fetched)}\n"
            f"Snapshot path        : data/ux/live_homepage_snapshot.html\n\n"
            f"**You MUST base all homepage observations on the HTML below.**\n"
            f"Do NOT invent load times, CTA text, visible sections, or dashboard access.\n"
            f"Only describe what is present in the HTML below.\n\n"
            f"### Live Homepage HTML Snapshot\n"
            f"```html\n{html_excerpt}\n```\n"
            f"{secondary_note}"
        )
    else:
        context_block = (
            f"### Live Site Inspection — FAILED\n"
            f"Inspection timestamp : {now_iso}\n"
            f"URL attempted        : {BASE_URL}/\n"
            f"Attempts made        : {MAX_ATTEMPTS}\n"
            f"Failure reason       : {failure_reason}\n\n"
            f"**MANDATORY:** Because live inspection failed, you must write exactly:\n"
            f"'Live site inspection not possible this cycle.'\n"
            f"in the PRODUCT ACCESS STATUS section of your report.\n\n"
            f"You must NOT:\n"
            f"- Claim to have inspected the live site\n"
            f"- Describe load times, CTA text, or visible sections\n"
            f"- Fabricate any homepage observation\n\n"
            f"You MAY:\n"
            f"- Base findings on memory/ux_review_access.md, product_truth.md, and "
            f"previous product_experience_log.md entries\n"
            f"- Queue conversion_friction_report or landing_page_revision artifacts "
            f"based on documented prior findings only\n"
            f"- Recommend a retry next cycle\n"
        )

    meta["context_block_length"] = len(context_block)
    _save_meta(meta)

    return {
        "success": success,
        "attempts_needed": attempts_needed if success else MAX_ATTEMPTS,
        "homepage_bytes": len(homepage_bytes),
        "routes_fetched": routes_fetched,
        "failure_reason": failure_reason,
        "snapshot_path": snapshot_path,
        "context_block": context_block,
        "meta": meta,
    }


# ── Standalone test ───────────────────────────────────────────────────────────
if __name__ == "__main__":
    result = run_inspection()
    print(f"\nResult summary:")
    print(f"  success         : {result['success']}")
    print(f"  attempts_needed : {result['attempts_needed']}")
    print(f"  homepage_bytes  : {result['homepage_bytes']:,}")
    print(f"  routes_fetched  : {result['routes_fetched']}")
    print(f"  failure_reason  : {result['failure_reason']}")
    print(f"  snapshot_path   : {result['snapshot_path']}")
