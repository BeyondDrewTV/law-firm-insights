"""
shared/queue_writer.py
Clarion Agent Office — Approval Queue Writer
Agents call queue_item() to stage work for founder approval instead of stopping at drafts.
Writes directly to Clarion-Agency/data/approval_queue.json (same file the backend API serves).
"""
import json
import uuid
from datetime import datetime, timezone
from pathlib import Path

QUEUE_PATH = Path(__file__).resolve().parent.parent / "data" / "approval_queue.json"


def _load() -> list[dict]:
    if not QUEUE_PATH.exists():
        return []
    try:
        return json.loads(QUEUE_PATH.read_text(encoding="utf-8"))
    except Exception:
        return []


def _save(items: list[dict]) -> None:
    QUEUE_PATH.parent.mkdir(parents=True, exist_ok=True)
    QUEUE_PATH.write_text(json.dumps(items, indent=2, ensure_ascii=False), encoding="utf-8")


def queue_item(
    *,
    item_type: str,
    title: str,
    summary: str,
    payload: dict,
    created_by_agent: str,
    risk_level: str = "low",
    recommended_action: str = "",
    notes: str = "",
) -> str:
    """
    Stage a work item for founder approval. Returns the assigned item ID.

    item_type: outreach | content | account_setup | pilot_invite | other
    risk_level: low | medium | high
    payload: execution-ready data (draft text, target, channel, etc.)
    """
    item_id = f"AQ-{uuid.uuid4().hex[:8].upper()}"
    now = datetime.now(timezone.utc).isoformat()
    item = {
        "id": item_id,
        "type": item_type,
        "created_at": now,
        "updated_at": now,
        "created_by_agent": created_by_agent,
        "title": title,
        "summary": summary,
        "payload": payload,
        "risk_level": risk_level,
        "status": "pending",
        "recommended_action": recommended_action,
        "notes": notes,
        "released_at": None,
        "released_by": None,
    }
    items = _load()
    items.append(item)
    _save(items)
    return item_id


def get_pending(item_type: str | None = None) -> list[dict]:
    items = _load()
    return [i for i in items if i.get("status") == "pending"
            and (item_type is None or i.get("type") == item_type)]
