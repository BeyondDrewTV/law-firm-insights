"""
outbound_sales_agent.py
Clarion Agent Office — Outbound Sales Agent (Python runner)
Version: 1.0 | 2026-03-12

Reads the latest prospect_target_list from the approval queue.
For each HIGH-priority prospect, generates a tailored outreach_email artifact
that references the specific firm, its review patterns, and Clarion's governance
value to that exact situation.

Artifact type : outreach_email
Minimum output: 3 outreach_email artifacts per run
Authority      : LEVEL 1 — drafts only. No send without Level 2 approval.
"""

import sys
import json
import datetime
import traceback
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent   # Clarion-Agency/
sys.path.insert(0, str(BASE_DIR))

from shared.agent_runner import run_agent, _load_file
from shared.queue_writer import queue_item, get_pending

REPORTS_DIR = BASE_DIR / "reports" / "sales"
MEMORY      = BASE_DIR / "memory"
DATA        = BASE_DIR / "data"
DATE        = datetime.date.today().isoformat()

AGENT_KEY   = "outbound_sales_agent"
AGENT_TITLE = "Clarion Outbound Sales Agent"
PROMPT_REL  = "agents/sales/outbound_sales_agent.md"

# ── Enforcement constants ─────────────────────────────────────────────────────
MINIMUM_OUTREACH_ARTIFACTS = 3


def _get_latest_prospect_list() -> list[dict]:
    """
    Pull the most recent approved or pending prospect_target_list from the queue.
    Returns the prospects list (may be empty if none found).
    """
    items = get_pending(item_type="prospect_target_list")
    if not items:
        # Also check released items — prospect intel may have been approved already
        from shared.queue_writer import _load as _load_all
        all_items = _load_all()
        items = [i for i in all_items
                 if i.get("type") == "prospect_target_list"
                 and i.get("status") in ("pending", "released")]
    if not items:
        return []
    latest = sorted(items, key=lambda x: x.get("created_at", ""), reverse=True)[0]
    return latest.get("payload", {}).get("prospects", [])


def _high_priority_prospects(prospects: list[dict]) -> list[dict]:
    """Return prospects marked HIGH priority, then MEDIUM, to reach minimum 3."""
    high   = [p for p in prospects if p.get("outreach_priority") == "HIGH"]
    medium = [p for p in prospects if p.get("outreach_priority") == "MEDIUM"]
    combined = high + medium
    # Need at least 3 targets for the agent to draft against
    return combined[:max(6, len(combined))]   # pass up to 6, agent picks best 3


def _data_context(prospects: list[dict]) -> str:
    """Build data context injected into the LLM prompt."""
    parts = []

    # Core memory files
    for label, path in [
        ("Product Truth",             MEMORY / "product_truth.md"),
        ("Sales Outreach Templates",  MEMORY / "sales_outreach_templates.md"),
        ("Brand Voice",               MEMORY / "brand_voice.md"),
        ("Positioning Guardrails",    MEMORY / "positioning_guardrails.md"),
        ("Pilot Offer",               MEMORY / "pilot_offer.md"),
        ("Conversion Friction",       MEMORY / "conversion_friction.md"),
        ("Do Not Chase",              MEMORY / "do_not_chase.md"),
        ("Prelaunch Activation Mode", MEMORY / "prelaunch_activation_mode.md"),
    ]:
        parts.append(f"### {label}\n{_load_file(Path(path), label)}\n")

    # Inject prospect intelligence output — the core input for this agent
    if prospects:
        parts.append(
            "### Prospect Intelligence Output (target these firms — HIGH priority first)\n"
            + json.dumps(prospects, indent=2)
            + "\n"
        )
    else:
        parts.append(
            "### Prospect Intelligence Output\n"
            "[No prospect_target_list found in queue this run. "
            "Fall back to leads_pipeline.csv and draft outreach for any new prospects.]\n"
        )
        parts.append(
            f"### Leads Pipeline\n"
            f"{_load_file(DATA / 'revenue/leads_pipeline.csv', 'Leads Pipeline')}\n"
        )

    return "\n".join(parts)


def _count_outreach_artifacts_this_run(before_count: int) -> list[dict]:
    """Return outreach_email items added to queue after before_count items existed."""
    from shared.queue_writer import _load as _load_all
    all_items = _load_all()
    outreach = [i for i in all_items if i.get("type") == "outreach_email"]
    return outreach[before_count:]


def run(pi_result: dict | None = None) -> dict:
    """
    Execute the Outbound Sales Agent.
    pi_result: optional dict from prospect_intelligence_agent.run() — used for
               logging / handoff context but not required.

    Returns:
        {
          "artifacts_queued": int,
          "artifact_ids": list[str],
          "enforcement_passed": bool,
          "enforcement_reason": str,
          "report_path": Path | None,
        }
    """
    print(f"\n  [OutboundSales] Running — {DATE}")
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    result = {
        "artifacts_queued": 0,
        "artifact_ids": [],
        "enforcement_passed": False,
        "enforcement_reason": "Agent did not complete.",
        "report_path": None,
    }

    # Snapshot queue depth before this agent runs (to detect new items)
    from shared.queue_writer import _load as _load_all
    outreach_before = len([i for i in _load_all() if i.get("type") == "outreach_email"])

    # Load and filter prospects
    prospects = _get_latest_prospect_list()
    targets   = _high_priority_prospects(prospects)
    if not targets:
        print("  [OutboundSales] No prospect intelligence found — falling back to pipeline.")

    try:
        report_path = run_agent(
            agent_key       = AGENT_KEY,
            prompt_rel_path = PROMPT_REL,
            report_subdir   = "sales",
            data_context    = _data_context(targets),
            agent_title     = AGENT_TITLE,
        )
        result["report_path"] = report_path
        print(f"  [OutboundSales] Report written → {report_path.name}")
    except Exception as e:
        print(f"  [OutboundSales] FAILED: {e}")
        traceback.print_exc()
        result["enforcement_reason"] = f"Agent run failed: {e}"
        return result

    # ── Enforcement check ─────────────────────────────────────────────────────
    new_items = _count_outreach_artifacts_this_run(outreach_before)
    count = len(new_items)
    result["artifacts_queued"] = count
    result["artifact_ids"] = [i["id"] for i in new_items]

    if count >= MINIMUM_OUTREACH_ARTIFACTS:
        result["enforcement_passed"] = True
        result["enforcement_reason"] = "OK"
        print(f"  [OutboundSales] ✓ {count} outreach_email artifact(s) queued: "
              f"{', '.join(result['artifact_ids'])}")
    else:
        result["enforcement_passed"] = False
        result["enforcement_reason"] = (
            f"Only {count} outreach_email artifact(s) queued "
            f"(minimum required: {MINIMUM_OUTREACH_ARTIFACTS})."
        )
        print(f"  [OutboundSales] ✗ Enforcement FAILED: {result['enforcement_reason']}")

    return result


# ── Standalone execution ──────────────────────────────────────────────────────

if __name__ == "__main__":
    r = run()
    print(json.dumps(r, indent=2, default=str))
