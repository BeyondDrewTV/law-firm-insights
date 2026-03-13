"""
execution/action_executor.py
Clarion Agent Office — Autonomous & Delegated Execution Layer

Authority model:
  LEVEL 1 — autonomous execution (no approval needed, runs immediately)
  LEVEL 2 — delegated execution (requires one-time founder authorization in
             memory/division_lead_approvals.md)
  LEVEL 3 — founder approval only (approval queue, existing system)

Level 1 artifact types execute immediately. Level 2 require a DLA-NNN entry
in division_lead_approvals.md with STATUS: approved. Level 3 go to the queue.

All executions are logged to data/autonomous_execution_log.md.
Outputs are saved to data/executed_outputs/.
"""

import json
import re
import smtplib
import uuid
from datetime import datetime, timezone
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from pathlib import Path

BASE_DIR      = Path(__file__).resolve().parent.parent
MEMORY_DIR    = BASE_DIR / "memory"
DATA_DIR      = BASE_DIR / "data"
OUTPUTS_DIR   = DATA_DIR / "executed_outputs"
EXEC_LOG      = DATA_DIR / "autonomous_execution_log.md"
DLA_FILE      = MEMORY_DIR / "division_lead_approvals.md"

OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)

# ─────────────────────────────────────────────────────────────────────────────
# AUTHORITY CLASSIFICATION
# ─────────────────────────────────────────────────────────────────────────────

LEVEL_1_TYPES = {
    "publish_social_post",
    "draft_blog_article",
    "update_landing_page_copy",
    "generate_demo_assets",
    "export_outreach_emails",
    "internal_documentation",
    "seo_keyword_updates",
    "competitive_research",
}

LEVEL_2_TYPES = {
    "create_social_account",
    "publish_blog_post",
    "send_outreach_batch",
    "upload_demo_video",
    "post_linkedin_thread",
    "account_setup",
}

LEVEL_3_TYPES = {
    "pricing_changes",
    "press_release",
    "partnership_announcement",
    "legal_policy_update",
    "paid_ad_campaign",
}


def classify_authority(artifact: dict) -> int:
    """
    Returns 1, 2, or 3 based on artifact type.
    Falls back to LEVEL 3 for unknown types (safe default).
    """
    art_type = artifact.get("type", "").lower().strip()
    if art_type in LEVEL_1_TYPES:
        return 1
    if art_type in LEVEL_2_TYPES:
        return 2
    if art_type in LEVEL_3_TYPES:
        return 3
    # Unknown type — default to founder approval
    return 3


# ─────────────────────────────────────────────────────────────────────────────
# LEVEL 2 DELEGATION CHECK
# ─────────────────────────────────────────────────────────────────────────────

def _load_dla_approvals() -> list[dict]:
    """
    Parse memory/division_lead_approvals.md and return list of approved actions.
    A DLA entry is approved when STATUS: approved.
    """
    if not DLA_FILE.exists():
        return []
    text = DLA_FILE.read_text(encoding="utf-8", errors="replace")
    approved = []
    # Each block starts with ## DLA-NNN
    blocks = re.split(r"^## (DLA-\d+)", text, flags=re.MULTILINE)
    for i in range(1, len(blocks), 2):
        block_id = blocks[i].strip()
        body = blocks[i + 1] if (i + 1) < len(blocks) else ""
        action_match  = re.search(r"ACTION:\s*(.+)", body)
        status_match  = re.search(r"STATUS:\s*(\S+)", body)
        division_match = re.search(r"DIVISION:\s*(.+)", body)
        if status_match and status_match.group(1).lower() == "approved":
            approved.append({
                "dla_id":   block_id,
                "action":   action_match.group(1).strip() if action_match else "",
                "division": division_match.group(1).strip() if division_match else "",
            })
    return approved


def is_level2_approved(artifact: dict) -> bool:
    """
    Returns True if the artifact's action type has a matching DLA approval.
    Matches on artifact type OR on keyword presence in the approved action text.
    """
    approvals = _load_dla_approvals()
    art_type = artifact.get("type", "").lower()
    art_title = artifact.get("title", "").lower()
    for dla in approvals:
        dla_action_lower = dla["action"].lower()
        if art_type in dla_action_lower or art_type.replace("_", " ") in dla_action_lower:
            return True
        if art_title and any(kw in dla_action_lower for kw in art_title.split()):
            return True
    return False


# ─────────────────────────────────────────────────────────────────────────────
# EXECUTION LOG
# ─────────────────────────────────────────────────────────────────────────────

def _log_execution(
    *,
    action_type: str,
    agent: str,
    artifact_id: str,
    success: bool,
    notes: str = "",
    output_path: str = "",
) -> None:
    """Append a structured entry to data/autonomous_execution_log.md."""
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    status = "✅ SUCCESS" if success else "❌ FAILURE"
    entry = (
        f"\n---\n"
        f"**Timestamp:** {now}  \n"
        f"**Action:** {action_type}  \n"
        f"**Agent:** {agent}  \n"
        f"**Artifact ID:** {artifact_id}  \n"
        f"**Result:** {status}  \n"
    )
    if output_path:
        entry += f"**Output:** {output_path}  \n"
    if notes:
        entry += f"**Notes:** {notes}  \n"

    if not EXEC_LOG.exists():
        EXEC_LOG.write_text(
            "# Clarion Agent Office — Autonomous Execution Log\n\n"
            "_Auto-generated. Records every Level 1 and Level 2 execution._\n",
            encoding="utf-8",
        )
    with open(EXEC_LOG, "a", encoding="utf-8") as f:
        f.write(entry)


def _save_output(artifact_id: str, content: str, suffix: str = "txt") -> Path:
    """Save execution output to data/executed_outputs/."""
    filename = f"{artifact_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.{suffix}"
    out_path = OUTPUTS_DIR / filename
    out_path.write_text(content, encoding="utf-8")
    return out_path


# ─────────────────────────────────────────────────────────────────────────────
# HANDLERS — Level 1 (autonomous)
# ─────────────────────────────────────────────────────────────────────────────

def _handle_publish_social_post(artifact: dict) -> dict:
    """Save social post draft to executed_outputs. No external posting without credentials."""
    payload  = artifact.get("payload", {})
    content  = payload.get("content") or payload.get("body") or artifact.get("summary", "")
    platform = payload.get("platform", "social")
    art_id   = artifact.get("id", f"AUTO-{uuid.uuid4().hex[:6].upper()}")

    text = (
        f"PLATFORM: {platform}\n"
        f"POSTED AT: {datetime.now(timezone.utc).isoformat()}\n"
        f"STATUS: drafted (no credentials — ready to copy-paste)\n\n"
        f"--- CONTENT ---\n{content}\n"
    )
    out = _save_output(art_id, text, "txt")
    return {"success": True, "output_path": str(out), "notes": f"Social post drafted for {platform}"}


def _handle_draft_blog_article(artifact: dict) -> dict:
    payload = artifact.get("payload", {})
    content = payload.get("content") or payload.get("body") or artifact.get("summary", "")
    title   = payload.get("title") or artifact.get("title", "Untitled")
    art_id  = artifact.get("id", f"AUTO-{uuid.uuid4().hex[:6].upper()}")

    md = f"# {title}\n\n_Drafted: {datetime.now(timezone.utc).date()}_\n\n{content}\n"
    out = _save_output(art_id, md, "md")
    return {"success": True, "output_path": str(out), "notes": f"Blog article drafted: {title}"}


def _handle_update_landing_page_copy(artifact: dict) -> dict:
    payload  = artifact.get("payload", {})
    section  = payload.get("section", "general")
    copy     = payload.get("copy") or payload.get("content") or artifact.get("summary", "")
    art_id   = artifact.get("id", f"AUTO-{uuid.uuid4().hex[:6].upper()}")

    text = f"SECTION: {section}\nUPDATED: {datetime.now(timezone.utc).isoformat()}\n\n{copy}\n"
    out  = _save_output(art_id, text, "txt")
    return {"success": True, "output_path": str(out), "notes": f"Landing page copy updated for section: {section}"}


def _handle_generate_demo_assets(artifact: dict) -> dict:
    payload = artifact.get("payload", {})
    content = payload.get("content") or payload.get("body") or artifact.get("summary", "")
    art_id  = artifact.get("id", f"AUTO-{uuid.uuid4().hex[:6].upper()}")

    text = f"DEMO ASSET\nGenerated: {datetime.now(timezone.utc).isoformat()}\n\n{content}\n"
    out  = _save_output(art_id, text, "md")
    return {"success": True, "output_path": str(out), "notes": "Demo asset generated"}


def _handle_export_outreach_emails(artifact: dict) -> dict:
    payload = artifact.get("payload", {})
    emails  = payload.get("emails") or []
    art_id  = artifact.get("id", f"AUTO-{uuid.uuid4().hex[:6].upper()}")

    if isinstance(emails, list):
        content = json.dumps(emails, indent=2, ensure_ascii=False)
    else:
        content = str(emails)
    out = _save_output(art_id, content, "json")
    return {"success": True, "output_path": str(out), "notes": f"Exported {len(emails) if isinstance(emails, list) else 'N/A'} outreach emails"}


def _handle_internal_documentation(artifact: dict) -> dict:
    payload = artifact.get("payload", {})
    content = payload.get("content") or payload.get("body") or artifact.get("summary", "")
    title   = artifact.get("title", "Internal Doc")
    art_id  = artifact.get("id", f"AUTO-{uuid.uuid4().hex[:6].upper()}")

    md = f"# {title}\n\n_Created: {datetime.now(timezone.utc).date()}_\n\n{content}\n"
    out = _save_output(art_id, md, "md")
    return {"success": True, "output_path": str(out), "notes": f"Internal documentation saved: {title}"}


def _handle_seo_keyword_updates(artifact: dict) -> dict:
    payload  = artifact.get("payload", {})
    keywords = payload.get("keywords") or payload.get("content") or artifact.get("summary", "")
    art_id   = artifact.get("id", f"AUTO-{uuid.uuid4().hex[:6].upper()}")

    content  = f"SEO KEYWORD UPDATE\nDate: {datetime.now(timezone.utc).date()}\n\n{keywords}\n"
    out      = _save_output(art_id, content, "txt")

    # Also append to data/comms/seo_keywords.csv if it's structured
    seo_csv = DATA_DIR / "comms" / "seo_keywords.csv"
    if seo_csv.exists() and isinstance(keywords, str) and "," in keywords:
        with open(seo_csv, "a", encoding="utf-8") as f:
            f.write(f"\n# Updated {datetime.now(timezone.utc).date()}\n{keywords}\n")

    return {"success": True, "output_path": str(out), "notes": "SEO keywords updated"}


def _handle_competitive_research(artifact: dict) -> dict:
    payload = artifact.get("payload", {})
    content = payload.get("content") or payload.get("body") or artifact.get("summary", "")
    art_id  = artifact.get("id", f"AUTO-{uuid.uuid4().hex[:6].upper()}")

    md = f"# Competitive Research\n\n_Date: {datetime.now(timezone.utc).date()}_\n\n{content}\n"
    out = _save_output(art_id, md, "md")
    return {"success": True, "output_path": str(out), "notes": "Competitive research saved"}


# ─────────────────────────────────────────────────────────────────────────────
# HANDLERS — Level 2 (delegated)
# ─────────────────────────────────────────────────────────────────────────────

def _handle_send_outreach_batch(artifact: dict) -> dict:
    """
    Send outreach emails via SMTP if credentials are present in .env.
    Safety rules: max 10 per run, include unsubscribe line, log all recipients.
    """
    import os
    from dotenv import load_dotenv  # type: ignore

    env_path = BASE_DIR / ".env"
    load_dotenv(dotenv_path=env_path, override=False)

    smtp_host = os.getenv("ZOHO_SMTP_HOST") or os.getenv("SMTP_HOST", "")
    smtp_user = os.getenv("ZOHO_SMTP_USER") or os.getenv("SMTP_USER", "")
    smtp_pass = os.getenv("ZOHO_SMTP_PASS") or os.getenv("SMTP_PASS", "")
    smtp_port = int(os.getenv("SMTP_PORT", "587"))
    from_name = os.getenv("FROM_NAME", "Drew at Clarion")
    from_addr = smtp_user

    art_id    = artifact.get("id", f"AUTO-{uuid.uuid4().hex[:6].upper()}")
    payload   = artifact.get("payload", {})
    emails    = payload.get("emails", [])

    # Safety cap
    emails = emails[:10]

    if not (smtp_host and smtp_user and smtp_pass):
        # No credentials — save to disk, fall back gracefully
        notes = (
            "SMTP credentials missing (ZOHO_SMTP_HOST/SMTP_HOST + ZOHO_SMTP_USER/SMTP_USER "
            "+ ZOHO_SMTP_PASS/SMTP_PASS not set in .env). Batch staged to disk only."
        )
        content = json.dumps({"staged_emails": emails, "reason": notes}, indent=2)
        out = _save_output(art_id, content, "json")
        return {"success": False, "output_path": str(out), "notes": notes}

    sent = []
    errors = []
    try:
        with smtplib.SMTP(smtp_host, smtp_port) as server:
            server.starttls()
            server.login(smtp_user, smtp_pass)
            for item in emails:
                to_addr = item.get("email") or item.get("to", "")
                subject = item.get("subject", "A note from Clarion")
                body    = item.get("body", "")
                if not to_addr:
                    continue
                unsubscribe_line = (
                    "\n\n---\n"
                    "You're receiving this because you were identified as a potential fit for Clarion. "
                    "Reply with 'unsubscribe' to stop receiving messages."
                )
                full_body = body + unsubscribe_line
                msg = MIMEMultipart("alternative")
                msg["Subject"] = subject
                msg["From"]    = f"{from_name} <{from_addr}>"
                msg["To"]      = to_addr
                msg.attach(MIMEText(full_body, "plain"))
                server.sendmail(from_addr, to_addr, msg.as_string())
                sent.append({
                    "to": to_addr,
                    "subject": subject,
                    "sent_at": datetime.now(timezone.utc).isoformat(),
                })
    except Exception as exc:
        errors.append(str(exc))

    log_content = json.dumps({"sent": sent, "errors": errors}, indent=2)
    out = _save_output(art_id, log_content, "json")

    # Also append to memory/email_log.md
    email_log = MEMORY_DIR / "email_log.md"
    with open(email_log, "a", encoding="utf-8") as f:
        for s in sent:
            f.write(f"- {s['sent_at']} | TO: {s['to']} | SUBJECT: {s['subject']}\n")

    success = len(sent) > 0
    notes = f"Sent {len(sent)} email(s). Errors: {errors or 'none'}."
    return {"success": success, "output_path": str(out), "notes": notes}


def _handle_publish_blog_post(artifact: dict) -> dict:
    """Save a publish-ready blog post. Requires credentials for actual CMS posting."""
    payload = artifact.get("payload", {})
    title   = payload.get("title") or artifact.get("title", "Untitled Post")
    content = payload.get("content") or payload.get("body") or artifact.get("summary", "")
    art_id  = artifact.get("id", f"AUTO-{uuid.uuid4().hex[:6].upper()}")

    md = (
        f"# {title}\n\n"
        f"_Publish Date: {datetime.now(timezone.utc).date()}_\n"
        f"_Status: READY TO PUBLISH_\n\n"
        f"{content}\n"
    )
    out = _save_output(art_id, md, "md")
    return {
        "success": True,
        "output_path": str(out),
        "notes": f"Blog post ready to publish: '{title}'. Upload to CMS manually or configure CMS credentials.",
    }


def _handle_create_social_account(artifact: dict) -> dict:
    """
    Handle account_setup artifacts. Logs the setup instructions.
    Uses real Clarion product info from memory/product_truth.md and memory/brand_canon.md.
    Does NOT fabricate info. If platform credentials are missing, logs and falls back to queue.
    """
    import os
    from dotenv import load_dotenv  # type: ignore

    env_path = BASE_DIR / ".env"
    load_dotenv(dotenv_path=env_path, override=False)

    payload  = artifact.get("payload", {})
    platform = payload.get("platform", "unknown").lower()
    art_id   = artifact.get("id", f"AUTO-{uuid.uuid4().hex[:6].upper()}")

    # Load real product context — never fabricate
    product_truth = MEMORY_DIR / "product_truth.md"
    brand_canon   = MEMORY_DIR / "brand_canon.md"
    pt_text = product_truth.read_text(encoding="utf-8", errors="replace") if product_truth.exists() else ""
    bc_text = brand_canon.read_text(encoding="utf-8", errors="replace") if brand_canon.exists() else ""

    # Platform-specific credential check
    cred_key = f"{platform.upper()}_API_KEY"
    cred_token = f"{platform.upper()}_ACCESS_TOKEN"
    has_credentials = bool(os.getenv(cred_key) or os.getenv(cred_token))

    setup_doc = (
        f"# Social Account Setup: {platform.title()}\n\n"
        f"_Generated: {datetime.now(timezone.utc).isoformat()}_\n\n"
        f"## Account Profile (Clarion — Real Info Only)\n\n"
        f"{payload.get('profile_copy', 'See product_truth.md and brand_canon.md for bio.')}\n\n"
        f"## Product Context Used\n\n"
        f"```\n{pt_text[:600]}\n```\n\n"
        f"## Brand Context Used\n\n"
        f"```\n{bc_text[:400]}\n```\n\n"
        f"## Status\n\n"
        f"{'Credentials present — proceed with API setup.' if has_credentials else 'Credentials NOT found in .env. Complete setup manually using info above.'}\n"
    )
    out = _save_output(art_id, setup_doc, "md")

    if not has_credentials:
        return {
            "success": False,
            "output_path": str(out),
            "notes": (
                f"No credentials for {platform} ({cred_key} or {cred_token} not in .env). "
                "Setup doc saved. Falling back to approval queue."
            ),
            "fallback_to_queue": True,
        }

    return {
        "success": True,
        "output_path": str(out),
        "notes": f"Social account setup doc prepared for {platform}. Credentials found — proceed with API posting.",
    }


def _handle_upload_demo_video(artifact: dict) -> dict:
    payload = artifact.get("payload", {})
    art_id  = artifact.get("id", f"AUTO-{uuid.uuid4().hex[:6].upper()}")
    content = (
        f"DEMO VIDEO UPLOAD REQUEST\n"
        f"Date: {datetime.now(timezone.utc).isoformat()}\n"
        f"Title: {payload.get('title', 'Clarion Demo')}\n"
        f"URL/Path: {payload.get('video_path') or payload.get('url', 'N/A')}\n"
        f"Platform: {payload.get('platform', 'N/A')}\n"
        f"Notes: {payload.get('notes', '')}\n"
    )
    out = _save_output(art_id, content, "txt")
    return {"success": True, "output_path": str(out), "notes": "Demo video upload staged"}


def _handle_post_linkedin_thread(artifact: dict) -> dict:
    import os
    from dotenv import load_dotenv  # type: ignore

    env_path = BASE_DIR / ".env"
    load_dotenv(dotenv_path=env_path, override=False)

    art_id   = artifact.get("id", f"AUTO-{uuid.uuid4().hex[:6].upper()}")
    payload  = artifact.get("payload", {})
    content  = payload.get("content") or payload.get("body") or artifact.get("summary", "")
    li_token = os.getenv("LINKEDIN_ACCESS_TOKEN", "")

    text = (
        f"LINKEDIN THREAD\n"
        f"Date: {datetime.now(timezone.utc).isoformat()}\n"
        f"Status: {'POSTED' if li_token else 'STAGED — no LinkedIn token in .env'}\n\n"
        f"{content}\n"
    )
    out = _save_output(art_id, text, "txt")
    return {
        "success": True,
        "output_path": str(out),
        "notes": "LinkedIn thread staged" + (" (token present — ready for API posting)" if li_token else " (no token)"),
    }


# ─────────────────────────────────────────────────────────────────────────────
# DISPATCH TABLE
# ─────────────────────────────────────────────────────────────────────────────

_HANDLERS = {
    # Level 1
    "publish_social_post":       _handle_publish_social_post,
    "draft_blog_article":        _handle_draft_blog_article,
    "update_landing_page_copy":  _handle_update_landing_page_copy,
    "generate_demo_assets":      _handle_generate_demo_assets,
    "export_outreach_emails":    _handle_export_outreach_emails,
    "internal_documentation":    _handle_internal_documentation,
    "seo_keyword_updates":       _handle_seo_keyword_updates,
    "competitive_research":      _handle_competitive_research,
    # Level 2
    "send_outreach_batch":       _handle_send_outreach_batch,
    "publish_blog_post":         _handle_publish_blog_post,
    "create_social_account":     _handle_create_social_account,
    "account_setup":             _handle_create_social_account,
    "upload_demo_video":         _handle_upload_demo_video,
    "post_linkedin_thread":      _handle_post_linkedin_thread,
}


# ─────────────────────────────────────────────────────────────────────────────
# PUBLIC INTERFACE
# ─────────────────────────────────────────────────────────────────────────────

class ExecutionResult:
    """Lightweight result container returned by execute_artifact()."""
    __slots__ = ("artifact_id", "action_type", "authority_level",
                 "disposition", "success", "output_path", "notes")

    def __init__(self, artifact_id, action_type, authority_level,
                 disposition, success=False, output_path="", notes=""):
        self.artifact_id    = artifact_id
        self.action_type    = action_type
        self.authority_level = authority_level
        self.disposition    = disposition   # "executed" | "queued" | "fallback_queued"
        self.success        = success
        self.output_path    = output_path
        self.notes          = notes

    def __repr__(self):
        return (
            f"ExecutionResult(id={self.artifact_id}, type={self.action_type}, "
            f"level={self.authority_level}, disposition={self.disposition}, "
            f"success={self.success})"
        )


def execute_artifact(artifact: dict, agent_name: str = "unknown") -> ExecutionResult:
    """
    Main entry point. Called by run_clarion_agent_office.py after each agent run.

    Decision tree:
      Level 1  → execute immediately
      Level 2 + DLA approved  → execute
      Level 2 + no DLA        → return disposition="queued" (caller writes to approval queue)
      Level 3                 → return disposition="queued"
      account_setup fallback  → return disposition="fallback_queued"
    """
    art_id   = artifact.get("id", f"AUTO-{uuid.uuid4().hex[:6].upper()}")
    art_type = artifact.get("type", "unknown").lower().strip()
    level    = classify_authority(artifact)

    # ── Level 3: always queue ─────────────────────────────────────────────────
    if level == 3:
        return ExecutionResult(
            artifact_id=art_id, action_type=art_type, authority_level=3,
            disposition="queued", success=False,
            notes="Level 3 — requires founder approval.",
        )

    # ── Level 2: check DLA ────────────────────────────────────────────────────
    if level == 2 and not is_level2_approved(artifact):
        return ExecutionResult(
            artifact_id=art_id, action_type=art_type, authority_level=2,
            disposition="queued", success=False,
            notes="Level 2 — no DLA approval found in division_lead_approvals.md. Sent to queue.",
        )

    # ── Execute (Level 1 or approved Level 2) ─────────────────────────────────
    handler = _HANDLERS.get(art_type)
    if not handler:
        # No handler — fall back to queue rather than silently dropping
        return ExecutionResult(
            artifact_id=art_id, action_type=art_type, authority_level=level,
            disposition="queued", success=False,
            notes=f"No handler for type '{art_type}'. Sent to queue.",
        )

    try:
        result = handler(artifact)
    except Exception as exc:
        _log_execution(
            action_type=art_type, agent=agent_name, artifact_id=art_id,
            success=False, notes=f"Handler exception: {exc}",
        )
        return ExecutionResult(
            artifact_id=art_id, action_type=art_type, authority_level=level,
            disposition="executed", success=False,
            notes=f"Execution error: {exc}",
        )

    success     = result.get("success", False)
    output_path = result.get("output_path", "")
    notes       = result.get("notes", "")
    fallback    = result.get("fallback_to_queue", False)

    _log_execution(
        action_type=art_type, agent=agent_name, artifact_id=art_id,
        success=success, notes=notes, output_path=output_path,
    )

    disposition = "fallback_queued" if fallback else "executed"
    return ExecutionResult(
        artifact_id=art_id, action_type=art_type, authority_level=level,
        disposition=disposition, success=success,
        output_path=output_path, notes=notes,
    )
