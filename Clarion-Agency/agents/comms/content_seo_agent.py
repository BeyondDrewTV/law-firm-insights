"""
content_seo_agent.py
Clarion Agent Office — Content SEO Agent (Python runner)
Version: 1.0 | 2026-03-12

Produces thought leadership articles, LinkedIn posts, and founder threads.
Also queues account_setup items for missing social platforms.

Artifact types : thought_leadership_article, linkedin_post, founder_thread, account_setup
Minimum output : 2 content artifacts per run (excluding account_setup)
Authority       : LEVEL 1 — drafts only. No publish without CEO approval.
"""

import sys
import json
import datetime
import traceback
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(BASE_DIR))

from shared.agent_runner import run_agent, _load_file
from shared.queue_writer import get_pending

REPORTS_DIR = BASE_DIR / "reports" / "comms"
MEMORY      = BASE_DIR / "memory"
DATA        = BASE_DIR / "data"
REPORTS     = BASE_DIR / "reports"
DATE        = datetime.date.today().isoformat()

AGENT_KEY   = "content_seo"       # maps to existing config.json key
AGENT_TITLE = "Clarion Content & SEO Agent"
PROMPT_REL  = "agents/comms/content_seo.md"

MINIMUM_CONTENT_ARTIFACTS = 2
CONTENT_ARTIFACT_TYPES    = {"thought_leadership_article", "linkedin_post", "founder_thread"}
ALL_ARTIFACT_TYPES        = CONTENT_ARTIFACT_TYPES | {"account_setup"}

def _latest_report(subdir: str, prefix: str) -> Path:
    d = REPORTS / subdir
    matches = sorted(d.glob(f"{prefix}_*.md"), reverse=True) if d.exists() else []
    return matches[0] if matches else d / f"{prefix}_not_found.md"


def _data_context() -> str:
    parts = []
    for label, path in [
        ("Brand Voice",                              MEMORY / "brand_voice.md"),
        ("Brand Canon",                              MEMORY / "brand_canon.md"),
        ("Product Truth",                            MEMORY / "product_truth.md"),
        ("Product Narrative",                        MEMORY / "product_narrative.md"),
        ("Positioning Guardrails",                   MEMORY / "positioning_guardrails.md"),
        ("ICP Definition",                           MEMORY / "icp_definition.md"),
        ("Channel Strategy",                         MEMORY / "channel_strategy.md"),
        ("Social Posting Cadence",                   MEMORY / "social_posting_cadence.md"),
        ("Proof Assets",                             MEMORY / "proof_assets.md"),
        ("Prelaunch Activation Mode",                MEMORY / "prelaunch_activation_mode.md"),
        ("SEO Keywords",                             DATA   / "comms/seo_keywords.csv"),
        ("Published Content Log",                    DATA   / "comms/content_log.csv"),
        ("Discovered Conversations",                 DATA   / "comms/discovered_conversations.md"),
    ]:
        parts.append(f"### {label}\n{_load_file(Path(path), label)}\n")

    # Attach latest competitive intelligence if available
    ci_report = _latest_report("market", "competitive_intelligence")
    parts.append(f"### Competitive Intelligence (latest)\n{_load_file(ci_report, 'Competitive Intelligence')}\n")

    return "\n".join(parts)


def _collect_new_artifacts(before_ids: set) -> list[dict]:
    from shared.queue_writer import _load as _load_all
    return [
        i for i in _load_all()
        if i.get("type") in ALL_ARTIFACT_TYPES
        and i.get("id") not in before_ids
    ]


def run() -> dict:
    """
    Execute the Content SEO Agent.
    Returns:
        {
          "content_artifacts_queued": int,
          "total_artifacts_queued": int,
          "artifact_ids": list[str],
          "artifact_types": list[str],
          "enforcement_passed": bool,
          "enforcement_reason": str,
          "report_path": Path | None,
        }
    """
    print(f"\n  [ContentSEO] Running — {DATE}")
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    result = {
        "content_artifacts_queued": 0,
        "total_artifacts_queued": 0,
        "artifact_ids": [],
        "artifact_types": [],
        "enforcement_passed": False,
        "enforcement_reason": "Agent did not complete.",
        "report_path": None,
    }

    from shared.queue_writer import _load as _load_all
    before_ids = {i["id"] for i in _load_all() if i.get("type") in ALL_ARTIFACT_TYPES}

    try:
        report_path = run_agent(
            agent_key       = AGENT_KEY,
            prompt_rel_path = PROMPT_REL,
            report_subdir   = "comms",
            data_context    = _data_context(),
            agent_title     = AGENT_TITLE,
        )
        result["report_path"] = report_path
        print(f"  [ContentSEO] Report written -> {report_path.name}")
    except Exception as e:
        print(f"  [ContentSEO] FAILED: {e}")
        traceback.print_exc()
        result["enforcement_reason"] = f"Agent run failed: {e}"
        return result

    new_items = _collect_new_artifacts(before_ids)

    # ── Parse QUEUE_JSON blocks from report ───────────────────────────────────
    from shared.report_parser import parse_and_queue
    import re as _re
    report_text = report_path.read_text(encoding="utf-8", errors="replace")
    parsed_ids = parse_and_queue(report_text, default_agent="Content SEO Agent",
                                  allowed_types=ALL_ARTIFACT_TYPES)

    # ── Fallback: synthesize a minimal linkedin_post if nothing was queued ────
    if not parsed_ids:
        print("  [ContentSEO] No QUEUE_JSON blocks found — attempting synthesis fallback.")
        # Look for PRIORITY CONTENT PROPOSAL section to extract topic
        topic_match = _re.search(r"Topic:\s*(.+)", report_text)
        topic = topic_match.group(1).strip() if topic_match else "Law firm reputation management"
        try:
            from shared.queue_writer import queue_item as _qi
            iid = _qi(
                item_type="linkedin_post",
                title=f"LinkedIn Post: {topic[:60]} (synthesized)",
                summary=f"Synthesized minimal content artifact — QUEUE_JSON block absent.",
                payload={
                    "artifact_type": "linkedin_post",
                    "post_copy": (
                        f"Topic: {topic}\n\n"
                        "[Content agent produced narrative report but no QUEUE_JSON block. "
                        "This is a placeholder — review agent report and manually draft post.]"
                    ),
                    "format_type": "placeholder",
                    "approval_status": "DRAFT - PLACEHOLDER - REQUIRES REWRITE BEFORE PUBLISHING",
                    "synthesis_warning": "LLM did not emit QUEUE_JSON block. Content must be rewritten.",
                },
                created_by_agent="Content SEO Agent (synthesized fallback)",
                risk_level="low",
                recommended_action="Rewrite this placeholder with actual content from agent report.",
            )
            parsed_ids.append(iid)
            print(f"  [ContentSEO] Synthesized placeholder linkedin_post: {iid}")
        except Exception as se:
            print(f"  [ContentSEO] Synthesis fallback error: {se}")

    # Refresh after parsing
    new_items = _collect_new_artifacts(before_ids)
    content_items = [i for i in new_items if i.get("type") in CONTENT_ARTIFACT_TYPES]

    result["total_artifacts_queued"]   = len(new_items)
    result["content_artifacts_queued"] = len(content_items)
    result["artifact_ids"]   = [i["id"] for i in new_items]
    result["artifact_types"] = [i.get("type") for i in new_items]

    if len(content_items) >= MINIMUM_CONTENT_ARTIFACTS:
        result["enforcement_passed"] = True
        result["enforcement_reason"] = "OK"
        types_str = ", ".join(i.get("type") for i in new_items)
        print(f"  [ContentSEO] OK {len(new_items)} artifact(s) queued ({types_str}): "
              f"{', '.join(result['artifact_ids'])}")
    else:
        result["enforcement_passed"] = False
        result["enforcement_reason"] = (
            f"Only {len(content_items)} content artifact(s) queued "
            f"(minimum required: {MINIMUM_CONTENT_ARTIFACTS}). "
            "Agent must produce at least 2 of: thought_leadership_article, "
            "linkedin_post, founder_thread."
        )
        print(f"  [ContentSEO] FAIL Enforcement: {result['enforcement_reason']}")

    return result


if __name__ == "__main__":
    r = run()
    print(json.dumps(r, indent=2, default=str))
