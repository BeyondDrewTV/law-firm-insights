"""
shared/report_parser.py
Clarion — Report Queue Parser
Version: 2.0 | 2026-03-12

Extracts QUEUE_JSON blocks from agent report text and writes them to the
approval queue. Agents emit JSON in their text output; this module handles
the actual queue_item() calls. The LLM cannot call queue_item() directly.

Supports multiple QUEUE_JSON blocks per report. Malformed blocks are skipped
with a warning — they never crash the run.

Usage:
    from shared.report_parser import parse_and_queue
    queued_ids = parse_and_queue(report_text, default_agent="Content SEO Agent")
"""

import json
import re
from typing import Optional

from shared.queue_writer import queue_item

# Item types the system recognises — used for basic validation
KNOWN_ITEM_TYPES = {
    "prospect_target_list",
    "outreach_email",
    "thought_leadership_article",
    "linkedin_post",
    "founder_thread",
    "account_setup",
    "conversion_friction_report",
    "landing_page_revision",
    "product_improvement",
    "evidence_report",
    "market_signal",
    "content_brief",
}


def _fix_trailing_commas(raw: str) -> str:
    """Remove trailing commas before } or ] — a common LLM mistake."""
    return re.sub(r",\s*([}\]])", r"\1", raw)


def _try_parse_json(raw: str) -> tuple[Optional[dict], Optional[str]]:
    """Attempt to parse JSON, trying a cleanup pass on failure.
    Returns (parsed_dict, error_string). One of them is always None."""
    raw = raw.strip()
    try:
        return json.loads(raw), None
    except json.JSONDecodeError as e1:
        cleaned = _fix_trailing_commas(raw)
        try:
            return json.loads(cleaned), None
        except json.JSONDecodeError as e2:
            return None, f"Original: {e1}; After cleanup: {e2}"


def _validate_block(qdata: dict) -> tuple[bool, str]:
    """Basic validation. Returns (valid, reason)."""
    item_type = qdata.get("item_type", "")
    if not item_type:
        return False, "Missing 'item_type' field"
    if item_type not in KNOWN_ITEM_TYPES:
        # Allow unknown types but warn — don't block
        print(f"  [ReportParser] WARNING: unrecognised item_type '{item_type}' "
              f"(allowed: {sorted(KNOWN_ITEM_TYPES)}). Queuing anyway.")
    if not qdata.get("title"):
        return False, "Missing 'title' field"
    if not isinstance(qdata.get("payload", {}), dict):
        return False, "'payload' must be a JSON object"
    return True, "ok"


def parse_and_queue(
    report_text: str,
    default_agent: str = "Agent",
    allowed_types: Optional[set] = None,
) -> list[str]:
    """
    Find all ```QUEUE_JSON ... ``` blocks in report_text, parse each as JSON,
    and write to the approval queue.

    Returns list of item IDs queued. Empty list = nothing found or all failed.

    Args:
        report_text:   Full text of the agent report.
        default_agent: Used as created_by_agent when the block omits it.
        allowed_types: When set, blocks whose item_type is not in this set are skipped.
    """
    # Match fenced blocks: ```QUEUE_JSON\n...\n```
    blocks = re.findall(r"```QUEUE_JSON\s*\n(.*?)```", report_text, re.DOTALL)

    if not blocks:
        print(f"  [ReportParser] No QUEUE_JSON blocks found in report "
              f"(agent={default_agent}). Report length: {len(report_text)} chars.")
        return []

    print(f"  [ReportParser] Found {len(blocks)} QUEUE_JSON block(s) in report.")
    queued_ids: list[str] = []

    for idx, raw in enumerate(blocks, start=1):
        print(f"  [ReportParser] Parsing block {idx}/{len(blocks)} ...")

        qdata, parse_err = _try_parse_json(raw)
        if qdata is None:
            print(f"  [ReportParser] WARN block {idx}: JSON parse failed — {parse_err}")
            print(f"  [ReportParser] Skipping block {idx}.")
            continue

        valid, reason = _validate_block(qdata)
        if not valid:
            print(f"  [ReportParser] WARN block {idx}: validation failed — {reason}. Skipping.")
            continue

        item_type = qdata.get("item_type", "")

        if allowed_types and item_type not in allowed_types:
            print(f"  [ReportParser] Skipping block {idx}: type '{item_type}' "
                  f"not in allowed_types={allowed_types}")
            continue

        try:
            item_id = queue_item(
                item_type          = item_type,
                title              = qdata.get("title", f"Agent output — {item_type}"),
                summary            = qdata.get("summary", ""),
                payload            = qdata.get("payload", {}),
                created_by_agent   = qdata.get("created_by_agent", default_agent),
                risk_level         = qdata.get("risk_level", "low"),
                recommended_action = qdata.get("recommended_action", ""),
                notes              = qdata.get("notes", ""),
            )
            queued_ids.append(item_id)
            print(f"  [ReportParser] OK Queued {item_id} (type={item_type})")
        except Exception as e:
            print(f"  [ReportParser] ERROR block {idx}: queue_item() failed — {e}")

    if queued_ids:
        print(f"  [ReportParser] Total queued this call: {len(queued_ids)} "
              f"({', '.join(queued_ids)})")
    else:
        print(f"  [ReportParser] WARNING: 0 items queued from {len(blocks)} block(s). "
              f"Check agent prompt — ensure QUEUE_JSON blocks contain valid JSON.")

    return queued_ids
