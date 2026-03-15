"""
prospect_intelligence_agent.py
Clarion Agent Office — Prospect Intelligence Agent
Version: 3.0 | 2026-03-13

Identifies 5–10 real, ICP-fit law firm prospects every run using public sources.
Writes one prospect_target_list artifact to the approval queue per run.
Runs before Outbound Sales so the sales agent has fresh, qualified targets.

NEW in v3.0:
  - Email discovery phase added AFTER LLM run.
  - shared.email_discoverer fetches each firm's public pages and extracts
    visible email addresses (mailto links, visible text).
  - Never guesses or synthesizes emails — only uses what is explicitly in HTML.
  - Each prospect now carries: recipient_email, recipient_email_source,
    recipient_email_type ("partner" | "firm_general" | "not_found").
  - Outbound Sales agent can read recipient_email directly from the payload.
  - Email discovery is deterministic Python — LLM is not involved.

Artifact type: prospect_target_list
Minimum output: 1 artifact containing >= 3 prospects per run.
"""

import sys
import json
import datetime
import traceback
import re
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent   # Clarion-Agency/
sys.path.insert(0, str(BASE_DIR))

from shared.agent_runner import run_agent, _load_file
from shared.queue_writer import queue_item, get_pending

REPORTS_DIR = BASE_DIR / "reports" / "sales"
MEMORY      = BASE_DIR / "memory"
DATA        = BASE_DIR / "data"
DATE        = datetime.date.today().isoformat()

AGENT_KEY   = "prospect_intelligence_agent"
AGENT_TITLE = "Clarion Prospect Intelligence Agent"
PROMPT_REL  = "agents/sales/prospect_intelligence_agent.md"

MINIMUM_ARTIFACTS = 1
MINIMUM_PROSPECTS = 3   # minimum *verified* prospects (with evidence fields) required per run


def _count_verified(prospects: list[dict]) -> int:
    """Count prospects that have all required evidence fields populated."""
    required = {"firm_website", "review_source_url", "review_count_observed",
                "average_rating_observed", "evidence_note"}
    verified = 0
    for p in prospects:
        if all(p.get(f) for f in required):
            verified += 1
    return verified


def _validate_email_fields(prospects: list[dict]) -> list[dict]:
    """
    Ensure every prospect has the three email fields.
    Clears any email value that doesn't contain '@' (catches names accidentally
    placed in the email field by the LLM).
    Sets email_type to 'not_found' when email is empty or invalid.
    """
    for p in prospects:
        email = p.get("recipient_email", "")
        if email and "@" not in email:
            # LLM put a name instead of an address — clear it
            p["recipient_email"]        = ""
            p["recipient_email_source"] = ""
            p["recipient_email_type"]   = "not_found"
        elif not email:
            p.setdefault("recipient_email",        "")
            p.setdefault("recipient_email_source", "")
            p.setdefault("recipient_email_type",   "not_found")
    return prospects


def _data_context() -> str:
    """
    Minimal context — agent_runner.py already injects product_truth + standing_orders.
    Only send what's unique to prospect research.
    """
    parts = []
    for label, path in [
        ("ICP Definition",            MEMORY / "icp_definition.md"),
        ("Lead Sources",              MEMORY / "lead_sources.md"),
        ("Do Not Chase",              MEMORY / "do_not_chase.md"),
        ("Positioning Guardrails",    MEMORY / "positioning_guardrails.md"),
        ("Prelaunch Activation Mode", MEMORY / "prelaunch_activation_mode.md"),
        ("Existing Pipeline",         DATA   / "revenue/leads_pipeline.csv"),
        ("Lead Research Queue",       DATA   / "revenue/lead_research_queue.csv"),
    ]:
        parts.append(f"### {label}\n{_load_file(Path(path), label)}\n")
    return "\n".join(parts)


def _extract_prospects_from_narrative(text: str) -> list[dict]:
    """
    Fallback: attempt to extract firm blocks from narrative prose when no
    QUEUE_JSON block is present. Looks for 'Firm:' patterns.
    Returns a list of minimal prospect dicts.
    """
    prospects = []
    # Match blocks starting with "Firm:" and capture several following lines
    blocks = re.split(r"\nFirm:", text)
    for block in blocks[1:]:  # first element is before the first "Firm:"
        lines = block.strip().splitlines()
        firm_name = lines[0].strip() if lines else "Unknown Firm"
        p = {
            "firm_name": firm_name,
            "location": "Unknown",
            "practice_area": "Unknown",
            "attorney_count_estimate": 0,
            "google_review_count": 0,
            "average_rating": 0.0,
            "review_activity": "Extracted from narrative",
            "website": "",
            "contact_targets": "See contact page",
            "outreach_priority": "MEDIUM",
            "reasoning": "Extracted from narrative report — verify manually.",
        }
        for line in lines[1:]:
            low = line.lower()
            if low.startswith("location:"):
                p["location"] = line.split(":", 1)[1].strip()
            elif low.startswith("practice:"):
                p["practice_area"] = line.split(":", 1)[1].strip()
            elif low.startswith("priority:"):
                p["outreach_priority"] = line.split(":", 1)[1].strip().upper()
            elif low.startswith("attorneys"):
                m = re.search(r"\d+", line)
                if m:
                    p["attorney_count_estimate"] = int(m.group())
            elif low.startswith("google reviews"):
                m = re.search(r"(\d+)\s*@\s*([\d.]+)", line)
                if m:
                    p["google_review_count"] = int(m.group(1))
                    p["average_rating"] = float(m.group(2))
            elif low.startswith("reasoning:"):
                p["reasoning"] = line.split(":", 1)[1].strip()
        if firm_name and firm_name != "Unknown Firm":
            prospects.append(p)
    return prospects


def _synthesize_queue_item(prospects: list[dict], text: str) -> str | None:
    """
    When QUEUE_JSON is absent, synthesize the artifact from narrative-extracted
    prospects and queue it. Returns the item_id or None on failure.
    """
    if not prospects:
        return None
    # Try to extract markets from text
    markets = re.findall(r"\b([A-Z][a-zA-Z]+(?:,\s*[A-Z]{2})?)\b", text[:500])
    try:
        item_id = queue_item(
            item_type="prospect_target_list",
            title=f"Prospect Target List — {len(prospects)} firms (synthesized) — {DATE}",
            summary=(
                f"Synthesized from narrative — {len(prospects)} prospects extracted. "
                "QUEUE_JSON block was absent; verify firm data manually."
            ),
            payload={
                "artifact_type": "prospect_target_list",
                "run_date": DATE,
                "markets_worked": markets[:4] if markets else ["Unknown"],
                "sources_used": ["narrative_extraction"],
                "synthesis_warning": (
                    "This artifact was synthesized from prose because the LLM did not "
                    "emit a QUEUE_JSON block. Firm data may be incomplete. "
                    "Review and verify before passing to Outbound Sales."
                ),
                "prospects": prospects,
            },
            created_by_agent="Prospect Intelligence Agent (synthesized fallback)",
            risk_level="medium",
            recommended_action=(
                "Review synthesized prospect list. Verify firm data. "
                "Approve if prospects are real and accurate."
            ),
        )
        print(f"  [ProspectIntel] Fallback synthesized {item_id} with {len(prospects)} prospects.")
        return item_id
    except Exception as e:
        print(f"  [ProspectIntel] Fallback synthesis failed: {e}")
        return None


def _enforce_minimum(item_id: str | None, prospects: list) -> tuple[bool, str]:
    if not item_id:
        return False, "No prospect_target_list artifact was queued this run."
    verified = _count_verified(prospects)
    total = len(prospects)
    if verified < MINIMUM_PROSPECTS:
        return False, (
            f"Artifact queued but only {verified}/{total} prospects have all required "
            f"evidence fields (firm_website, review_source_url, review_count_observed, "
            f"average_rating_observed, evidence_note). Minimum required: {MINIMUM_PROSPECTS} verified."
        )
    return True, f"OK — {verified}/{total} verified prospects."


def run() -> dict:
    print(f"\n  [ProspectIntel] Running — {DATE}")
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    result = {
        "item_id": None,
        "prospect_count": 0,
        "enforcement_passed": False,
        "enforcement_reason": "Agent did not complete.",
        "report_path": None,
        "synthesis_used": False,
        "email_discovery": {
            "partner_email_found": 0,
            "firm_general_email_found": 0,
            "not_found": 0,
            "total": 0,
        },
    }

    try:
        report_path = run_agent(
            agent_key       = AGENT_KEY,
            prompt_rel_path = PROMPT_REL,
            report_subdir   = "sales",
            data_context    = _data_context(),
            agent_title     = AGENT_TITLE,
        )
        result["report_path"] = report_path
        print(f"  [ProspectIntel] Report written -> {report_path.name}")
    except Exception as e:
        print(f"  [ProspectIntel] FAILED: {e}")
        traceback.print_exc()
        result["enforcement_reason"] = f"Agent run failed: {e}"
        return result

    report_text = report_path.read_text(encoding="utf-8", errors="replace")

    # ── Primary: parse QUEUE_JSON blocks ─────────────────────────────────────
    from shared.report_parser import parse_and_queue
    queued_ids = parse_and_queue(
        report_text,
        default_agent="Prospect Intelligence Agent",
        allowed_types={"prospect_target_list"},
    )

    if queued_ids:
        item_id = queued_ids[0]
        result["item_id"] = item_id
        from shared.queue_writer import _load as _load_all
        all_items = _load_all()
        match = next((i for i in all_items if i["id"] == item_id), None)
        prospects = match.get("payload", {}).get("prospects", []) if match else []

        # ── Email discovery phase ─────────────────────────────────────────────
        # Runs on the Python side — deterministic, never fabricates.
        # Enriches each prospect with recipient_email, recipient_email_source,
        # recipient_email_type before the item is considered final.
        print(f"  [ProspectIntel] Phase 2: email discovery for {len(prospects)} prospect(s)...")
        try:
            from shared.email_discoverer import enrich_prospects_with_emails
            prospects = _validate_email_fields(prospects)
            prospects, email_stats = enrich_prospects_with_emails(prospects)
            result["email_discovery"] = email_stats
            print(f"  [ProspectIntel] Email discovery: "
                  f"{email_stats['partner_email_found']} partner, "
                  f"{email_stats['firm_general_email_found']} firm-general, "
                  f"{email_stats['not_found']} not found")

            # Write enriched prospects back to the queued item
            if match:
                match["payload"]["prospects"] = prospects
                from shared.queue_writer import _save as _save_queue
                _save_queue(all_items)
                print(f"  [ProspectIntel] Enriched payload saved back to queue item {item_id}")
        except Exception as email_err:
            print(f"  [ProspectIntel] Email discovery error (non-fatal): {email_err}")
            import traceback as _tb
            _tb.print_exc()

        result["prospect_count"] = len(prospects)
        passed, reason = _enforce_minimum(item_id, prospects)
        result["enforcement_passed"] = passed
        result["enforcement_reason"] = reason
        result["verified_count"] = _count_verified(prospects)
        if passed:
            print(f"  [ProspectIntel] OK {item_id} -- {result['verified_count']}/{len(prospects)} verified prospects queued.")
        else:
            print(f"  [ProspectIntel] FAIL Enforcement: {reason}")

    else:
        # ── Fallback: synthesize from narrative ───────────────────────────────
        print("  [ProspectIntel] No QUEUE_JSON block found — attempting narrative synthesis.")
        result["synthesis_used"] = True
        prospects = _extract_prospects_from_narrative(report_text)
        print(f"  [ProspectIntel] Narrative extraction found {len(prospects)} firm(s).")

        # Email discovery on synthesized prospects too
        if prospects:
            print(f"  [ProspectIntel] Phase 2: email discovery for {len(prospects)} synthesized prospect(s)...")
            try:
                from shared.email_discoverer import enrich_prospects_with_emails
                prospects = _validate_email_fields(prospects)
                prospects, email_stats = enrich_prospects_with_emails(prospects)
                result["email_discovery"] = email_stats
            except Exception as email_err:
                print(f"  [ProspectIntel] Email discovery error (non-fatal): {email_err}")

        item_id = _synthesize_queue_item(prospects, report_text)
        result["item_id"] = item_id
        result["prospect_count"] = len(prospects)
        passed, reason = _enforce_minimum(item_id, prospects)
        result["enforcement_passed"] = passed
        result["enforcement_reason"] = (
            reason if passed else
            f"Fallback synthesis: {reason}. "
            "Agent must emit a QUEUE_JSON block in future runs."
        )
        if not passed:
            print(f"  [ProspectIntel] FAIL: {result['enforcement_reason']}")

    return result


if __name__ == "__main__":
    r = run()
    print(json.dumps(r, indent=2, default=str))
