"""
evidence_agent.py
Clarion Agent Office — Evidence & Insight Agent
Version: 1.0 | 2026-03-12

Analyzes review data and generates publishable insight statistics and case
insight briefs. Builds thought leadership proof and sales anchors.

Artifact types : insight_stat, case_insight_brief
Minimum output : 1 artifact per run (insight_stat OR case_insight_brief)
Authority       : LEVEL 1 — drafts only. No publish without founder approval.
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

REPORTS_DIR = BASE_DIR / "reports" / "strategy"
MEMORY      = BASE_DIR / "memory"
DATA        = BASE_DIR / "data"
DATE        = datetime.date.today().isoformat()

AGENT_KEY   = "evidence_agent"
AGENT_TITLE = "Clarion Evidence & Insight Agent"
PROMPT_REL  = "agents/strategy/evidence_agent.md"

MINIMUM_ARTIFACTS = 1
EVIDENCE_ARTIFACT_TYPES = {"insight_stat", "case_insight_brief"}

def _load_demo_reviews() -> str:
    """Load the canonical demo review dataset as formatted context."""
    demo_csv = BASE_DIR.parent / "backend" / "data" / "demo_reviews.csv"
    if demo_csv.exists():
        return _load_file(demo_csv, "Demo Reviews Dataset (40 law-firm client reviews)")
    # Fallback: look in data/ dir within Clarion-Agency
    alt = DATA / "demo_reviews.csv"
    return _load_file(alt, "Demo Reviews Dataset")


def _data_context() -> str:
    parts = []
    for label, path in [
        ("Product Truth",          MEMORY / "product_truth.md"),
        ("Positioning Guardrails", MEMORY / "positioning_guardrails.md"),
        ("ICP Definition",         MEMORY / "icp_definition.md"),
        ("Market Insights",        MEMORY / "market_insights.md"),
        ("Proof Assets",           MEMORY / "proof_assets.md"),
    ]:
        parts.append(f"### {label}\n{_load_file(Path(path), label)}\n")

    parts.append(f"### Demo Reviews Dataset\n{_load_demo_reviews()}\n")
    return "\n".join(parts)


def _collect_new_evidence_artifacts(before_ids: set) -> list[dict]:
    """Return evidence artifacts added to the queue after this run started."""
    from shared.queue_writer import _load as _load_all
    all_items = _load_all()
    return [
        i for i in all_items
        if i.get("type") in EVIDENCE_ARTIFACT_TYPES
        and i.get("id") not in before_ids
    ]


def run() -> dict:
    """
    Execute the Evidence & Insight Agent.

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
    print(f"\n  [Evidence] Running — {DATE}")
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    result = {
        "artifacts_queued": 0,
        "artifact_ids": [],
        "artifact_types": [],
        "enforcement_passed": False,
        "enforcement_reason": "Agent did not complete.",
        "report_path": None,
    }

    # Snapshot existing evidence artifact IDs before this run
    from shared.queue_writer import _load as _load_all
    before_ids = {
        i["id"] for i in _load_all()
        if i.get("type") in EVIDENCE_ARTIFACT_TYPES
    }

    try:
        report_path = run_agent(
            agent_key       = AGENT_KEY,
            prompt_rel_path = PROMPT_REL,
            report_subdir   = "strategy",
            data_context    = _data_context(),
            agent_title     = AGENT_TITLE,
        )
        result["report_path"] = report_path
        print(f"  [Evidence] Report written → {report_path.name}")
    except Exception as e:
        print(f"  [Evidence] FAILED: {e}")
        traceback.print_exc()
        result["enforcement_reason"] = f"Agent run failed: {e}"
        return result

    # Enforcement check
    new_items = _collect_new_evidence_artifacts(before_ids)
    count = len(new_items)
    result["artifacts_queued"] = count
    result["artifact_ids"]    = [i["id"] for i in new_items]
    result["artifact_types"]  = [i.get("type") for i in new_items]

    if count >= MINIMUM_ARTIFACTS:
        result["enforcement_passed"] = True
        result["enforcement_reason"] = "OK"
        types_str = ", ".join(result["artifact_types"])
        print(f"  [Evidence] ✓ {count} artifact(s) queued ({types_str}): "
              f"{', '.join(result['artifact_ids'])}")
    else:
        result["enforcement_passed"] = False
        result["enforcement_reason"] = (
            f"Only {count} evidence artifact(s) queued "
            f"(minimum required: {MINIMUM_ARTIFACTS}). "
            f"Agent must produce at least one insight_stat or case_insight_brief."
        )
        print(f"  [Evidence] ✗ Enforcement FAILED: {result['enforcement_reason']}")

    return result


# ── Standalone ────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    r = run()
    print(json.dumps(r, indent=2, default=str))
