"""
product_experience_agent.py
Clarion Agent Office — Product Experience Agent (Python runner)
Version: 2.0 | 2026-03-13

Evaluates landing page clarity, onboarding friction, dashboard narrative,
and demo experience. Queues conversion_friction_report and
landing_page_revision artifacts for founder review.

NEW in v2.0:
  - Fetches the live site (https://law-firm-feedback-saas.onrender.com/)
    BEFORE calling the LLM using shared.site_inspector.
  - Render cold-start retry: 25s timeout, 5 attempts, 20s sleep between.
  - Passes real HTML snapshot into the agent data context.
  - If fetch fails, agent is instructed to write
    "Live site inspection not possible this cycle." — not fabricate.

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


def _run_live_inspection() -> dict:
    """
    Attempt live site fetch. Returns site_inspector result dict.
    Never raises — any failure returns a result with success=False.
    """
    try:
        from shared.site_inspector import run_inspection
        return run_inspection()
    except Exception as e:
        print(f"  [ProductExperience] site_inspector failed unexpectedly: {e}")
        return {
            "success": False,
            "attempts_needed": 5,
            "homepage_bytes": 0,
            "routes_fetched": [],
            "failure_reason": f"Inspector module error: {e}",
            "snapshot_path": None,
            "context_block": (
                "### Live Site Inspection — FAILED (module error)\n"
                f"Error: {e}\n\n"
                "MANDATORY: Write 'Live site inspection not possible this cycle.' "
                "in PRODUCT ACCESS STATUS. Do not fabricate any site observations.\n"
            ),
        }


def _data_context(inspection: dict) -> str:
    """
    Build data context for the LLM.
    Live inspection block comes FIRST so it is the most prominent input.
    Static memory files follow.
    """
    parts = []

    # ── Live inspection (first — highest priority) ────────────────────────────
    parts.append(inspection["context_block"])

    # ── Static memory files ───────────────────────────────────────────────────
    for label, path in [
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

    Phase 1: Live site inspection (shared.site_inspector)
    Phase 2: LLM run with real HTML in context
    Phase 3: Parse QUEUE_JSON artifacts, enforce minimum

    Returns:
        {
          "artifacts_queued"       : int,
          "artifact_ids"           : list[str],
          "artifact_types"         : list[str],
          "enforcement_passed"     : bool,
          "enforcement_reason"     : str,
          "report_path"            : Path | None,
          "inspection_success"     : bool,
          "inspection_attempts"    : int,
          "inspection_bytes"       : int,
          "routes_fetched"         : list[str],
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
        "inspection_success": False,
        "inspection_attempts": 0,
        "inspection_bytes": 0,
        "routes_fetched": [],
    }

    # ── Phase 1: Live site inspection ─────────────────────────────────────────
    print(f"  [ProductExperience] Phase 1: live site inspection...")
    inspection = _run_live_inspection()
    result["inspection_success"]  = inspection["success"]
    result["inspection_attempts"] = inspection["attempts_needed"]
    result["inspection_bytes"]    = inspection["homepage_bytes"]
    result["routes_fetched"]      = inspection["routes_fetched"]

    if inspection["success"]:
        print(f"  [ProductExperience] Inspection OK — "
              f"{inspection['homepage_bytes']:,} bytes, "
              f"{inspection['attempts_needed']} attempt(s), "
              f"routes: {inspection['routes_fetched']}")
    else:
        print(f"  [ProductExperience] Inspection FAILED — "
              f"{inspection['failure_reason']}. "
              f"Agent will use fallback docs only.")

    # ── Phase 2: LLM run ──────────────────────────────────────────────────────
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
            data_context    = _data_context(inspection),
            agent_title     = AGENT_TITLE,
        )
        result["report_path"] = report_path
        print(f"  [ProductExperience] Report written -> {report_path.name}")
    except Exception as e:
        print(f"  [ProductExperience] FAILED: {e}")
        traceback.print_exc()
        result["enforcement_reason"] = f"Agent run failed: {e}"
        return result

    # ── Phase 3: Parse QUEUE_JSON, enforce minimum ────────────────────────────
    from shared.report_parser import parse_and_queue
    import re as _re
    report_text = report_path.read_text(encoding="utf-8", errors="replace")
    parsed_ids = parse_and_queue(report_text, default_agent="Product Experience Agent",
                    allowed_types=PRODUCT_ARTIFACT_TYPES)

    # Fallback: synthesize a minimal artifact if nothing was queued
    if not parsed_ids:
        print("  [ProductExperience] No QUEUE_JSON blocks found — attempting synthesis fallback.")
        obs_match = _re.search(r"OBSERVATION:\s*(.+)", report_text)
        obs = obs_match.group(1).strip() if obs_match else "Unspecified friction found in audit."
        page_match = _re.search(r"AREA:\s*(.+)", report_text)
        page = page_match.group(1).strip().lower() if page_match else "landing_page"
        inspection_note = (
            f"Inspection: {'live HTML' if inspection['success'] else 'fallback docs only — live fetch failed'}"
        )
        try:
            iid = queue_item(
                item_type="conversion_friction_report",
                title=f"Friction: {page} — (synthesized from narrative) — {DATE}",
                summary="Synthesized from prose report — QUEUE_JSON block was absent.",
                payload={
                    "artifact_type": "conversion_friction_report",
                    "page": page,
                    "problem": obs,
                    "impact": "Unknown — extracted from narrative. Review agent report for details.",
                    "recommended_change": "See PROPOSED ACTIONS section of agent report.",
                    "priority": "medium",
                    "inspection_source": inspection_note,
                    "synthesis_warning": "LLM did not emit QUEUE_JSON block. Verify against full report.",
                },
                created_by_agent="Product Experience Agent (synthesized fallback)",
                risk_level="low",
                recommended_action="Review full agent report. Rewrite this item with specific details.",
            )
            parsed_ids.append(iid)
            print(f"  [ProductExperience] Synthesized placeholder: {iid}")
        except Exception as se:
            print(f"  [ProductExperience] Synthesis fallback error: {se}")

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
        print(f"  [ProductExperience] OK {count} artifact(s) queued ({types_str}): "
              f"{', '.join(result['artifact_ids'])}")
    else:
        result["enforcement_passed"] = False
        result["enforcement_reason"] = (
            f"Only {count} product artifact(s) queued "
            f"(minimum required: {MINIMUM_ARTIFACTS}). "
            "Agent must produce at least one conversion_friction_report, "
            "landing_page_revision, or product_improvement item."
        )
        print(f"  [ProductExperience] FAIL Enforcement: {result['enforcement_reason']}")

    return result


# ── Standalone ────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    r = run()
    print(json.dumps(r, indent=2, default=str))
