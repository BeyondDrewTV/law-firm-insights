"""
routes/approval_queue.py
Clarion — Approval Queue API

Auth: Flask-Login session (same as the rest of the app — login_required).
      No custom bearer token needed.

Routes:
  GET    /api/approval-queue          — list items (filterable by status/type)
  POST   /api/approval-queue          — create/upsert item (agents write here)
  PATCH  /api/approval-queue/<id>     — update status/notes
  POST   /api/approval-queue/batch    — batch approve/reject/release/hold
  GET    /api/approval-queue/stats    — counts for nav badge

Storage:
  Queue:   CLARION_AGENCY_DIR/data/approval_queue.json
  Audit:   CLARION_AGENCY_DIR/data/approval_queue_audit.log
  Release outputs (written on release):
    outreach:      CLARION_AGENCY_DIR/data/outreach/released_outreach_queue.json
    content:       CLARION_AGENCY_DIR/data/growth/released_content_queue.json
    account_setup: CLARION_AGENCY_DIR/data/accounts/released_account_setup_queue.json
    other/fallback:CLARION_AGENCY_DIR/data/released_other_queue.json

ENV VARS:
  CLARION_AGENCY_DIR  — path to Clarion-Agency folder
                        Default: three levels up from this file (repo root)/Clarion-Agency
"""

import json
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path

from flask import Blueprint, jsonify, request
from flask_login import current_user, login_required

approval_queue_bp = Blueprint("approval_queue", __name__)

# ── Paths ─────────────────────────────────────────────────────────────────────

def _agency_dir() -> Path:
    base = os.environ.get(
        "CLARION_AGENCY_DIR",
        str(Path(__file__).resolve().parent.parent.parent / "Clarion-Agency"),
    )
    return Path(base)

def _queue_path() -> Path:
    p = _agency_dir() / "data" / "approval_queue.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    return p

def _audit_path() -> Path:
    p = _agency_dir() / "data" / "approval_queue_audit.log"
    p.parent.mkdir(parents=True, exist_ok=True)
    return p

_RELEASE_PATHS: dict[str, Path] = {}

def _release_path(item_type: str) -> Path:
    d = _agency_dir()
    mapping = {
        "outreach":     d / "data" / "outreach" / "released_outreach_queue.json",
        "content":      d / "data" / "growth"   / "released_content_queue.json",
        "account_setup":d / "data" / "accounts" / "released_account_setup_queue.json",
    }
    return mapping.get(item_type, d / "data" / "released_other_queue.json")

# ── Storage helpers ───────────────────────────────────────────────────────────

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

def _load_released(item_type: str) -> list[dict]:
    p = _release_path(item_type)
    if not p.exists():
        return []
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return []

def _append_released(item: dict) -> None:
    p = _release_path(item.get("type", "other"))
    p.parent.mkdir(parents=True, exist_ok=True)
    existing = _load_released(item.get("type", "other"))
    ids = {x.get("id") for x in existing}
    if item.get("id") not in ids:
        existing.append(item)
    else:
        existing = [item if x.get("id") == item.get("id") else x for x in existing]
    p.write_text(json.dumps(existing, indent=2, ensure_ascii=False), encoding="utf-8")

# ── Audit logging ─────────────────────────────────────────────────────────────

def _audit(
    actor: str,
    item_id: str,
    item_type: str,
    prev_status: str,
    new_status: str,
    action: str,
    extra: str = "",
) -> None:
    line = (
        f"[{datetime.now(timezone.utc).isoformat()}] "
        f"actor={actor} id={item_id} type={item_type} "
        f"{prev_status} → {new_status} action={action}"
    )
    if extra:
        line += f" | {extra}"
    try:
        with _audit_path().open("a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        pass

# ── Valid values ──────────────────────────────────────────────────────────────

VALID_TYPES  = {"outreach", "content", "account_setup", "pilot_invite", "other"}
VALID_STATUS = {"pending", "approved", "rejected", "released", "held"}

# ── Routes ────────────────────────────────────────────────────────────────────

@approval_queue_bp.route("/api/approval-queue", methods=["GET"])
@login_required
def list_items():
    items = _load()
    status_filter = request.args.get("status")
    type_filter   = request.args.get("type")
    if status_filter:
        items = [i for i in items if i.get("status") == status_filter]
    if type_filter:
        items = [i for i in items if i.get("type") == type_filter]
    items.sort(key=lambda x: x.get("created_at", ""), reverse=True)
    return jsonify(items)


@approval_queue_bp.route("/api/approval-queue/stats", methods=["GET"])
@login_required
def stats():
    items = _load()
    result = {
        "total_pending":  sum(1 for i in items if i.get("status") == "pending"),
        "total_approved": sum(1 for i in items if i.get("status") == "approved"),
        "total_released": sum(1 for i in items if i.get("status") == "released"),
        "total_held":     sum(1 for i in items if i.get("status") == "held"),
        "by_type": {
            t: {s: sum(1 for i in items if i.get("type") == t and i.get("status") == s)
                for s in VALID_STATUS}
            for t in VALID_TYPES
        },
    }
    return jsonify(result)


@approval_queue_bp.route("/api/approval-queue", methods=["POST"])
@login_required
def create_item():
    data = request.get_json(force=True) or {}
    now  = datetime.now(timezone.utc).isoformat()
    item = {
        "id":                 data.get("id") or f"AQ-{uuid.uuid4().hex[:8].upper()}",
        "type":               data.get("type", "other"),
        "created_at":         data.get("created_at") or now,
        "updated_at":         now,
        "created_by_agent":   data.get("created_by_agent", "unknown"),
        "title":              data.get("title", "Untitled"),
        "summary":            data.get("summary", ""),
        "payload":            data.get("payload") or {},
        "risk_level":         data.get("risk_level", "low"),
        "status":             "pending",
        "recommended_action": data.get("recommended_action", ""),
        "notes":              data.get("notes", ""),
        "released_at":        None,
        "released_by":        None,
    }
    items = _load()
    idx = next((i for i, x in enumerate(items) if x.get("id") == item["id"]), None)
    if idx is not None:
        # Keep existing status on upsert
        item["status"] = items[idx]["status"]
        items[idx] = item
    else:
        items.append(item)
    _save(items)
    return jsonify(item), 201

@approval_queue_bp.route("/api/approval-queue/<item_id>", methods=["PATCH"])
@login_required
def update_item(item_id):
    data  = request.get_json(force=True) or {}
    items = _load()
    idx   = next((i for i, x in enumerate(items) if x.get("id") == item_id), None)
    if idx is None:
        return jsonify({"error": "Not found"}), 404

    prev_status = items[idx].get("status", "unknown")
    new_status  = data.get("status", prev_status)

    # Guard: only approved items can be released
    if new_status == "released" and prev_status != "approved":
        return jsonify({"error": "Only approved items can be released"}), 400

    # Guard: already released items cannot be re-released
    if new_status == "released" and prev_status == "released":
        return jsonify(items[idx])  # idempotent, no-op

    actor = getattr(current_user, "email", None) or getattr(current_user, "name", "founder")
    now   = datetime.now(timezone.utc).isoformat()

    for k in ("status", "notes", "recommended_action"):
        if k in data:
            items[idx][k] = data[k]
    items[idx]["updated_at"] = now

    if new_status == "released":
        items[idx]["released_at"] = now
        items[idx]["released_by"] = actor
        _append_released(items[idx])

    _save(items)
    _audit(actor, item_id, items[idx].get("type","?"), prev_status, new_status,
           data.get("action", new_status))
    return jsonify(items[idx])


@approval_queue_bp.route("/api/approval-queue/batch", methods=["POST"])
@login_required
def batch_action():
    data   = request.get_json(force=True) or {}
    action = data.get("action")
    ids    = set(data.get("ids", []))
    if action not in {"approve", "reject", "release", "hold"}:
        return jsonify({"error": "Invalid action"}), 400

    status_map = {"approve": "approved", "reject": "rejected",
                  "release": "released", "hold": "held"}
    new_status = status_map[action]
    actor = getattr(current_user, "email", None) or getattr(current_user, "name", "founder")
    items = _load()
    now   = datetime.now(timezone.utc).isoformat()
    updated = []

    for item in items:
        if item.get("id") not in ids:
            continue
        prev = item.get("status", "unknown")
        # Release: only approved items; skip others silently
        if new_status == "released" and prev != "approved":
            continue
        # Skip already-released items
        if new_status == "released" and prev == "released":
            continue
        item["status"]     = new_status
        item["updated_at"] = now
        if new_status == "released":
            item["released_at"] = now
            item["released_by"] = actor
            _append_released(item)
        _audit(actor, item["id"], item.get("type","?"), prev, new_status, action)
        updated.append(item)

    _save(items)
    return jsonify({"updated": len(updated), "ids": [i["id"] for i in updated]})
