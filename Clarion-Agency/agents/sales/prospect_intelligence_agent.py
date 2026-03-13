"""
prospect_intelligence_agent.py
Clarion Agent Office — Prospect Intelligence Agent
Version: 1.0 | 2026-03-12

Identifies 5–10 real, ICP-fit law firm prospects every run using public sources.
Writes one prospect_target_list artifact to the approval queue per run.
Runs before Outbound Sales so the sales agent has fresh, qualified targets.

Artifact type: prospect_target_list
Minimum output: 1 artifact containing >= 5 prospects per run.
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

AGENT_KEY   = "prospect_intelligence_agent"
AGENT_TITLE = "Clarion Prospect Intelligence Agent"
PROMPT_REL  = "agents/sales/prospect_intelligence_agent.md"

# ── Artifact enforcement ───────────────────────────────────────────────────────
MINIMUM_ARTIFACTS = 1       # at least 1 prospect_target_list per run
MINIMUM_PROSPECTS = 5       # at least 5 prospects inside that list


def _data_context() -> str:
    """Build data context string passed to the LLM agent."""
    parts = []
    for label, path in [
        ("ICP Definition",            MEMORY / "icp_definition.md"),
        ("Lead Sources",              MEMORY / "lead_sources.md"),
        ("Product Truth",             MEMORY / "product_truth.md"),
        ("Do Not Chase",              MEMORY / "do_not_chase.md"),
        ("Positioning Guardrails",    MEMORY / "positioning_guardrails.md"),
        ("Prelaunch Activation Mode", MEMORY / "prelaunch_activation_mode.md"),
        ("Existing Pipeline",         DATA   / "revenue/leads_pipeline.csv"),
        ("Lead Research Queue",       DATA   / "revenue/lead_research_queue.csv"),
    ]:
        parts.append(f"### {label}\n{_load_file(Path(path), label)}\n")
    return "\n".join(parts)


def _enforce_minimum(item_id: str, prospects: list) -> tuple[bool, str]:
    """Return (passed, reason). Called after the LLM writes its artifact."""
    if not item_id:
        return False, "No prospect_target_list artifact was queued this run."
    if len(prospects) < MINIMUM_PROSPECTS:
        return False, (
            f"Artifact queued but contains only {len(prospects)} prospects "
            f"(minimum required: {MINIMUM_PROSPECTS})."
        )
    return True, "OK"


def run() -> dict:
    """
    Execute the Prospect Intelligence Agent.

    Returns a result dict:
        {
          "item_id": str | None,
          "prospect_count": int,
          "enforcement_passed": bool,
          "enforcement_reason": str,
          "report_path": Path | None,
        }
    """
    print(f"\n  [ProspectIntel] Running — {DATE}")
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    result = {
        "item_id": None,
        "prospect_count": 0,
        "enforcement_passed": False,
        "enforcement_reason": "Agent did not complete.",
        "report_path": None,
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
        print(f"  [ProspectIntel] Report written → {report_path.name}")
    except Exception as e:
        print(f"  [ProspectIntel] FAILED: {e}")
        traceback.print_exc()
        result["enforcement_reason"] = f"Agent run failed: {e}"
        return result


    # ── Read back what the agent queued ───────────────────────────────────────
    # The LLM agent writes the queue item inside its prompt execution.
    # We find the most recently added prospect_target_list item to verify output.
    pending = get_pending(item_type="prospect_target_list")
    if pending:
        latest = pending[-1]   # last appended = this run's artifact
        result["item_id"] = latest["id"]
        prospects = latest.get("payload", {}).get("prospects", [])
        result["prospect_count"] = len(prospects)
        passed, reason = _enforce_minimum(latest["id"], prospects)
        result["enforcement_passed"] = passed
        result["enforcement_reason"] = reason
        if passed:
            print(f"  [ProspectIntel] ✓ Artifact {latest['id']} — {len(prospects)} prospects queued.")
        else:
            print(f"  [ProspectIntel] ✗ Enforcement FAILED: {reason}")
    else:
        # Agent ran but produced no queue artifact — enforcement fails
        result["enforcement_passed"] = False
        result["enforcement_reason"] = (
            "LLM agent completed but wrote no prospect_target_list item to the queue. "
            "Verify the prompt instructs the agent to call queue_item()."
        )
        print(f"  [ProspectIntel] ✗ No prospect_target_list found in queue after agent run.")

    return result


# ── Standalone execution ──────────────────────────────────────────────────────

if __name__ == "__main__":
    r = run()
    print(json.dumps(r, indent=2, default=str))
