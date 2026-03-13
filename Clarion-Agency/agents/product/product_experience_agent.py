"""
product_experience_agent.py
Clarion Agent Office — Product Experience Agent (Python runner)
Version: 1.0 | 2026-03-12

Evaluates landing page clarity, onboarding friction, dashboard narrative,
and demo experience. Queues conversion_friction_report and
landing_page_revision artifacts for founder review.

Artifact types : conversion_friction_report, landing_page_revision
Minimum output : 1 artifact per run (HIGH finding triggers at least one)
Authority       : LEVEL 1 — audit and recommend only. No implementation.
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

REPORTS_DIR = BASE_DIR / "reports" / "product"
MEMORY      = BASE_DIR / "memory"
DATA        = BASE_DIR / "data"
DATE        = datetime.date.today().isoformat()

AGENT_KEY   = "product_experience_agent"
AGENT_TITLE = "Clarion Product Experience Agent"
PROMPT_REL  = "agents/product/prelaunch_conversion.md"

MINIMUM_ARTIFACTS = 1
PRODUCT_ARTIFACT_TYPES = {"conversion_friction_report", "landing_page_revision", "product_improvement"}

def _data_context() -> str:
    parts = []
    for label, path in [
        ("Product Truth",             MEMORY / "product_truth.md"),
        ("UX Review Access",          MEMORY / "ux_review_access.md"),
        ("Brand QA",                  MEMORY / "brand_qa.md"),
        ("Positioning Guardrails",    MEMORY / "positioning_guardrails.md"),
        ("Proof Assets",              MEMORY / "proof_assets.md"),
        ("Conversion Friction",       MEMORY / "conversion_friction.md"),
        ("Product Experience Log",    MEMORY / "product_experience_log.md"),
        ("Pilot Offer",               MEMORY / "pilot_offer.md"),
        ("Claude Handoff Format",     MEMORY / "claude_handoff_format.md"),
        ("Prelaunch Activation Mode", MEMORY / "prelaunch_activation_mode.md"),
        ("Product Narrative",         MEMORY / "product_narrative.md"),
    ]:
        parts.append(f"### {label}\n{_load_file(Path(path), label)}\n")
    return "\n".join(parts)


def _collect_new_product_artifacts(before_ids: set) -> list[dict]:
    """Return product artifacts added to the queue after this run started."""
    from shared.queue_writer import _load as _load_all
    return [
        i for i in _load_all()
        if i.get("type") in PRODUCT_ARTIFACT_TYPES
        and i.get("id") not in before_ids
    ]


def run() -> dict:
    """
    Execute the Product Experience Agent.

    Returns:
        {
          "artifacts_queued": int,
          "artifact_ids": list[str],
          "artifact_types": list[str],
          "enforcement_passed": bool,
          "enforcement_reason": str,
          "report_path": Path | None,
        }
    """
    print(f"\n  [ProductExperience] Running — {DATE}")
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    result = {
        "artifacts_queued": 0,
        "artifact_ids": [],
        "artifact_types": [],
        "enforcement_passed": False,
        "enforcement_reason": "Agent did not complete.",
        "report_path": None,
    }

    # Snapshot before run
    from shared.queue_writer import _load as _load_all
    before_ids = {
        i["id"] for i in _load_all()
        if i.get("type") in PRODUCT_ARTIFACT_TYPES
    }

    try:
        report_path = run_agent(
            agent_key       = AGENT_KEY,
            prompt_rel_path = PROMPT_REL,
            report_subdir   = "product",
            data_context    = _data_context(),
            agent_title     = AGENT_TITLE,
        )
        result["report_path"] = report_path
        print(f"  [ProductExperience] Report written → {report_path.name}")
    except Exception as e:
        print(f"  [ProductExperience] FAILED: {e}")
        traceback.print_exc()
        result["enforcement_reason"] = f"Agent run failed: {e}"
        return result

    # Enforcement check
    new_items = _collect_new_product_artifacts(before_ids)
    count = len(new_items)
    result["artifacts_queued"] = count
    result["artifact_ids"]    = [i["id"] for i in new_items]
    result["artifact_types"]  = [i.get("type") for i in new_items]

    if count >= MINIMUM_ARTIFACTS:
        result["enforcement_passed"] = True
        result["enforcement_reason"] = "OK"
        types_str = ", ".join(result["artifact_types"])
        print(f"  [ProductExperience] ✓ {count} artifact(s) queued ({types_str}): "
              f"{', '.join(result['artifact_ids'])}")
    else:
        result["enforcement_passed"] = False
        result["enforcement_reason"] = (
            f"Only {count} product artifact(s) queued "
            f"(minimum required: {MINIMUM_ARTIFACTS}). "
            "Agent must produce at least one conversion_friction_report, "
            "landing_page_revision, or product_improvement item."
        )
        print(f"  [ProductExperience] ✗ Enforcement FAILED: {result['enforcement_reason']}")

    return result


# ── Standalone ────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    r = run()
    print(json.dumps(r, indent=2, default=str))
