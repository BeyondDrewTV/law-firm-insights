"""
routes/approval_queue.py
Clarion — Approval Queue API
Serves the founder-facing approval dashboard for staged agent work.

Routes (all require Bearer token):
  GET    /api/approval-queue          — list all items (filterable)
  POST   /api/approval-queue          — create/upsert a queue item (agents write here)
  PATCH  /api/approval-queue/<id>     — update status, notes
  POST   /api/approval-queue/batch    — batch approve/reject/release
  GET    /api/approval-queue/stats    — counts by type/status for notification badge

Storage: CLARION_AGENCY_DIR/data/approval_queue.json (flat JSON list, append-friendly)
"""

import json
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from functools import wraps

from flask import Blueprint, jsonify, request, current_app

approval_queue_bp = Blueprint("approval_queue", __name__)

# ── Storage path ──────────────────────────────────────────────────────────────

def _queue_path() -> Path:
    base = os.environ.get(
        "CLARION_AGENCY_DIR",
        str(Path(__file__).resolve().parent.parent.parent / "Clarion-Agency"),
    )
    p = Path(base) / "data" / "approval_queue.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    return p

def _load() -> list[dict]:
    p = _queue_path()
    if not p.exists():
        return []
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return []

def _save(items: list[dict]) -> None:
    _queue_path().write_text(
        json.dumps(items, indent=2, ensure_ascii=False), encoding="utf-8"
    )

# ── Auth helper ───────────────────────────────────────────────────────────────

def _require_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth = request.headers.get("Authorization", "")
        token = auth.removeprefix("Bearer ").strip()
        # Reuse existing app secret or env var
        expected = os.environ.get("INTERNAL_TOKEN", "Themepark12")
        if token != expected:
            return jsonify({"error": "Unauthorized"}), 401
        return f(*args, **kwargs)
    return decorated

# ── Valid values ──────────────────────────────────────────────────────────────

VALID_TYPES   = {"outreach", "content", "account_setup", "pilot_invite", "other"}
VALID_RISK    = {"low", "medium", "high"}
VALID_STATUS  = {"pending", "approved", "rejected", "released", "held"}

# ── Routes ────────────────────────────────────────────────────────────────────

@approval_queue_bp.route("/api/approval-queue", methods=["GET"])
@_require_auth
def list_items():
    items = _load()
    status_filter = request.args.get("status")
    type_filter   = request.args.get("type")
    if status_filter:
        items = [i for i in items if i.get("status") == status_filter]
    if type_filter:
        items = [i for i in items if i.get("type") == type_filter]
    # newest first
    items.sort(key=lambda x: x.get("created_at", ""), reverse=True)
    return jsonify(items)


@approval_queue_bp.route("/api/approval-queue", methods=["POST"])
@_require_auth
def create_item():
    data = request.get_json(force=True) or {}
    now = datetime.now(timezone.utc).isoformat()
    item = {
        "id":                 data.get("id") or f"AQ-{uuid.uuid4().hex[:8].upper()}",
        "type":               data.get("type", "other"),
        "created_at":         data.get("created_at") or now,
        "updated_at":         now,
        "created_by_agent":   data.get("created_by_agent", "unknown"),
        "title":              data.get("title", "Untitled"),
        "summary":            data.get("summary", ""),
        "payload":            data.get("payload", {}),
        "risk_level":         data.get("risk_level", "low"),
        "status":             "pending",
        "recommended_action": data.get("recommended_action", ""),
        "notes":              data.get("notes", ""),
        "released_at":        None,
        "released_by":        None,
    }
    items = _load()
    # Upsert by id
    idx = next((i for i, x in enumerate(items) if x.get("id") == item["id"]), None)
    if idx is not None:
        items[idx] = {**items[idx], **item, "status": items[idx]["status"]}
    else:
        items.append(item)
    _save(items)
    return jsonify(item), 201

@approval_queue_bp.route("/api/approval-queue/<item_id>", methods=["PATCH"])
@_require_auth
def update_item(item_id):
    data  = request.get_json(force=True) or {}
    items = _load()
    idx   = next((i for i, x in enumerate(items) if x.get("id") == item_id), None)
    if idx is None:
        return jsonify({"error": "Not found"}), 404
    allowed = {"status", "notes", "recommended_action"}
    for k in allowed:
        if k in data:
            items[idx][k] = data[k]
    items[idx]["updated_at"] = datetime.now(timezone.utc).isoformat()
    if data.get("status") == "released":
        items[idx]["released_at"] = items[idx]["updated_at"]
        items[idx]["released_by"] = data.get("released_by", "founder")
    _save(items)
    return jsonify(items[idx])


@approval_queue_bp.route("/api/approval-queue/batch", methods=["POST"])
@_require_auth
def batch_action():
    data   = request.get_json(force=True) or {}
    action = data.get("action")          # approve | reject | release | hold
    ids    = data.get("ids", [])
    if action not in {"approve", "reject", "release", "hold"}:
        return jsonify({"error": "Invalid action"}), 400
    status_map = {
        "approve": "approved",
        "reject":  "rejected",
        "release": "released",
        "hold":    "held",
    }
    new_status = status_map[action]
    items = _load()
    now   = datetime.now(timezone.utc).isoformat()
    updated = []
    for item in items:
        if item.get("id") in ids:
            # Only allow releasing already-approved items
            if new_status == "released" and item.get("status") != "approved":
                continue
            item["status"]     = new_status
            item["updated_at"] = now
            if new_status == "released":
                item["released_at"] = now
                item["released_by"] = data.get("released_by", "founder")
            updated.append(item)
    _save(items)
    return jsonify({"updated": len(updated), "ids": [i["id"] for i in updated]})


@approval_queue_bp.route("/api/approval-queue/stats", methods=["GET"])
@_require_auth
def stats():
    items = _load()
    result = {
        "total_pending":  sum(1 for i in items if i.get("status") == "pending"),
        "total_approved": sum(1 for i in items if i.get("status") == "approved"),
        "total_released": sum(1 for i in items if i.get("status") == "released"),
        "total_held":     sum(1 for i in items if i.get("status") == "held"),
        "by_type": {},
    }
    for t in VALID_TYPES:
        result["by_type"][t] = {
            s: sum(1 for i in items if i.get("type") == t and i.get("status") == s)
            for s in VALID_STATUS
        }
    return jsonify(result)
