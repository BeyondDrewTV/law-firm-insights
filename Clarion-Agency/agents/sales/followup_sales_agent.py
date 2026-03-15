"""
agents/sales/followup_sales_agent.py
Clarion Agent Office — Follow-Up Sales Agent
Version: 1.0 | 2026-03-13

Reads leads_pipeline.csv for firms that:
  - status == outreach_sent
  - follow_up_count == 0
  - last_contact_date >= 7 days ago

Sends each candidate to the LLM to draft a short follow-up email.
Queues each draft as a followup_email artifact (Level 2 — requires DLA approval to send).
"""

import sys
import json
import datetime
import traceback
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(BASE_DIR))

from shared.agent_runner import run_agent, _load_file
from shared.queue_writer import queue_item
from shared.pipeline_manager import get_followup_candidates

REPORTS_DIR = BASE_DIR / "reports" / "sales"
MEMORY      = BASE_DIR / "memory"
DATE        = datetime.date.today().isoformat()

AGENT_KEY   = "followup_sales_agent"
AGENT_TITLE = "Clarion Follow-Up Sales Agent"
PROMPT_REL  = "agents/sales/followup_sales_agent.md"

FOLLOWUP_THRESHOLD_DAYS = 7


def _data_context(candidates: list[dict]) -> str:
    """Build the LLM context: memory files + live follow-up candidates."""
    parts = []
    for label, path in [
        ("Product Truth",          MEMORY / "product_truth.md"),
        ("Brand Voice",            MEMORY / "brand_voice.md"),
        ("Positioning Guardrails", MEMORY / "positioning_guardrails.md"),
        ("Pilot Offer",            MEMORY / "pilot_offer.md"),
        ("Outreach Templates",     MEMORY / "sales_outreach_templates.md"),
    ]:
        parts.append(f"### {label}\n{_load_file(Path(path), label)}\n")

    # Serialize candidates as a readable table for the LLM
    if candidates:
        lines = ["### FOLLOW-UP CANDIDATES", ""]
        lines.append("These firms received an initial cold email and have not been followed up.")
        lines.append("Generate one followup_email QUEUE_JSON block per firm.")
        lines.append("")
        for c in candidates:
            last = c.get("last_contact_date", "unknown")
            try:
                days_ago = (datetime.date.today() -
                            datetime.date.fromisoformat(last)).days
            except ValueError:
                days_ago = "unknown"
            lines.append(f"FIRM: {c['firm_name']}")
            lines.append(f"  email:             {c.get('contact_email', '')}")
            lines.append(f"  practice_area:     {c.get('practice_area', 'unknown')}")
            lines.append(f"  location:          {c.get('location', 'unknown')}")
            lines.append(f"  last_contact_date: {last} ({days_ago} days ago)")
            lines.append(f"  follow_up_count:   {c.get('follow_up_count', '0')}")
            lines.append(f"  notes:             {c.get('notes', '')}")
            lines.append("")
        parts.append("\n".join(lines))
    else:
        parts.append("### FOLLOW-UP CANDIDATES\n\nNo candidates meet the follow-up criteria this run.")

    return "\n".join(parts)


def run() -> dict:
    print(f"\n  [FollowUp] Running — {DATE}")
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    result = {
        "candidates_found": 0,
        "drafts_queued":    0,
        "item_ids":         [],
        "enforcement_passed": False,
        "enforcement_reason": "Agent did not complete.",
        "report_path":      None,
    }

    # ── 1. Load follow-up candidates from pipeline ────────────────────────────
    try:
        candidates = get_followup_candidates(days_threshold=FOLLOWUP_THRESHOLD_DAYS)
        result["candidates_found"] = len(candidates)
        print(f"  [FollowUp] {len(candidates)} follow-up candidate(s) found in pipeline.")
    except Exception as e:
        print(f"  [FollowUp] Pipeline read failed: {e}")
        result["enforcement_reason"] = f"Pipeline read failed: {e}"
        return result

    # ── 2. Run LLM agent ──────────────────────────────────────────────────────
    try:
        report_path = run_agent(
            agent_key       = AGENT_KEY,
            prompt_rel_path = PROMPT_REL,
            report_subdir   = "sales",
            data_context    = _data_context(candidates),
            agent_title     = AGENT_TITLE,
        )
        result["report_path"] = report_path
        print(f"  [FollowUp] Report written -> {report_path.name}")
    except Exception as e:
        print(f"  [FollowUp] LLM agent FAILED: {e}")
        traceback.print_exc()
        result["enforcement_reason"] = f"LLM agent failed: {e}"
        return result

    # ── 3. Parse QUEUE_JSON blocks ────────────────────────────────────────────
    report_text = report_path.read_text(encoding="utf-8", errors="replace")

    from shared.report_parser import parse_and_queue
    queued_ids = parse_and_queue(
        report_text,
        default_agent="Follow-Up Sales Agent",
        allowed_types={"followup_email"},
    )

    result["drafts_queued"] = len(queued_ids)
    result["item_ids"]      = queued_ids

    # ── 4. Enforce: if candidates exist, at least one draft must be produced ──
    if len(candidates) == 0:
        result["enforcement_passed"] = True
        result["enforcement_reason"] = "No candidates — nothing to follow up on."
        print(f"  [FollowUp] No candidates. Nothing queued — OK.")
    elif len(queued_ids) == 0:
        result["enforcement_passed"] = False
        result["enforcement_reason"] = (
            f"{len(candidates)} candidate(s) present but 0 followup_email blocks queued. "
            "Agent must emit one QUEUE_JSON block per candidate."
        )
        print(f"  [FollowUp] FAIL: candidates present but no blocks produced.")
    else:
        result["enforcement_passed"] = True
        result["enforcement_reason"] = (
            f"OK — {len(queued_ids)}/{len(candidates)} follow-up drafts queued."
        )
        print(f"  [FollowUp] OK — {len(queued_ids)} follow-up draft(s) queued: "
              f"{', '.join(queued_ids)}")

    return result


if __name__ == "__main__":
    r = run()
    print(json.dumps(r, indent=2, default=str))
