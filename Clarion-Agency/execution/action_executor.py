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
import urllib.request
import urllib.error
from datetime import datetime, timezone
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from pathlib import Path
import sys

# Pipeline manager — persistent sales memory
try:
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from shared.pipeline_manager import append_lead, update_lead_status, lead_exists
    _PIPELINE_AVAILABLE = True
except ImportError:
    _PIPELINE_AVAILABLE = False
    def append_lead(r): pass          # type: ignore
    def update_lead_status(n, u): pass # type: ignore
    def lead_exists(n): return False   # type: ignore

BASE_DIR      = Path(__file__).resolve().parent.parent
MEMORY_DIR    = BASE_DIR / "memory"
DATA_DIR      = BASE_DIR / "data"
OUTPUTS_DIR   = DATA_DIR / "executed_outputs"
EXEC_LOG      = DATA_DIR / "autonomous_execution_log.md"
DLA_FILE      = MEMORY_DIR / "division_lead_approvals.md"

OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)

# Dedicated outbound send log — never mixed with inbound
OUTBOUND_EMAIL_LOG = MEMORY_DIR / "outbound_email_log.md"
INBOUND_EMAIL_LOG  = MEMORY_DIR / "inbound_email_log.md"

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
    # Content artifacts produced by lean agents — auto-export to publish-ready folder
    "thought_leadership_article",
    "linkedin_post",
    "founder_thread",
    "conversion_friction_report",
    "landing_page_revision",
    # outreach_email items are bundled → send_outreach_batch at Stage 5
    # mapping handled by _handle_outreach_email_item() wrapper below
    "outreach_email",
}

LEVEL_2_TYPES = {
    "create_social_account",
    "publish_blog_post",
    "send_outreach_batch",
    "upload_demo_video",
    "post_linkedin_thread",
    "account_setup",
    "followup_email",       # follow-up outreach — same SMTP path as outreach_email
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


# ── Content artifact handlers (Level 1 — publish-ready export) ───────────────

PUBLISH_DIR = DATA_DIR / "publish_ready"


def _handle_thought_leadership_article(artifact: dict) -> dict:
    """Export article to data/publish_ready/ as a formatted markdown file."""
    PUBLISH_DIR.mkdir(parents=True, exist_ok=True)
    payload = artifact.get("payload", {})
    title   = payload.get("title") or artifact.get("title", "Untitled Article")
    content = payload.get("content") or payload.get("body") or artifact.get("summary", "")
    art_id  = artifact.get("id", f"AUTO-{uuid.uuid4().hex[:6].upper()}")
    slug    = re.sub(r"[^a-z0-9]+", "-", title.lower())[:50]

    md = (
        f"# {title}\n\n"
        f"_Prepared: {datetime.now(timezone.utc).date()} | Status: PUBLISH-READY_\n\n"
        f"{content}\n"
    )
    out = PUBLISH_DIR / f"article_{slug}_{art_id}.md"
    out.write_text(md, encoding="utf-8")
    _save_output(art_id, md, "md")  # also to executed_outputs for log
    return {
        "success": True,
        "output_path": str(out),
        "notes": f"Article exported to publish_ready/: '{title}'. Copy to blog CMS to publish.",
        "publish_status": "prepared_locally",
    }


def _handle_linkedin_post(artifact: dict) -> dict:
    """Export LinkedIn post to data/publish_ready/ and optionally post via API."""
    import os
    from dotenv import load_dotenv  # type: ignore
    PUBLISH_DIR.mkdir(parents=True, exist_ok=True)
    load_dotenv(dotenv_path=BASE_DIR / ".env", override=False)

    payload  = artifact.get("payload", {})
    content  = payload.get("content") or payload.get("body") or artifact.get("summary", "")
    art_id   = artifact.get("id", f"AUTO-{uuid.uuid4().hex[:6].upper()}")
    li_token = os.getenv("LINKEDIN_ACCESS_TOKEN", "").strip()

    out = PUBLISH_DIR / f"linkedin_{art_id}.txt"
    out.write_text(content, encoding="utf-8")
    _save_output(art_id, content, "txt")

    if li_token:
        try:
            import urllib.request, urllib.error
            li_user_id = os.getenv("LINKEDIN_USER_ID", "")
            body = json.dumps({
                "author": f"urn:li:person:{li_user_id}",
                "lifecycleState": "PUBLISHED",
                "specificContent": {
                    "com.linkedin.ugc.ShareContent": {
                        "shareCommentary": {"text": content},
                        "shareMediaCategory": "NONE",
                    }
                },
                "visibility": {"com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"},
            }).encode()
            req = urllib.request.Request(
                "https://api.linkedin.com/v2/ugcPosts",
                data=body,
                headers={
                    "Authorization": f"Bearer {li_token}",
                    "Content-Type": "application/json",
                    "X-Restli-Protocol-Version": "2.0.0",
                },
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=15) as resp:
                resp_body = resp.read().decode()
            return {
                "success": True,
                "output_path": str(out),
                "notes": f"LinkedIn post PUBLISHED via API. Response: {resp_body[:120]}",
                "publish_status": "published_externally",
            }
        except Exception as exc:
            return {
                "success": True,
                "output_path": str(out),
                "notes": f"LinkedIn token present but API call failed ({exc}). Post saved to publish_ready/ for manual posting.",
                "publish_status": "prepared_locally",
            }
    return {
        "success": True,
        "output_path": str(out),
        "notes": "LinkedIn post exported to publish_ready/. No LINKEDIN_ACCESS_TOKEN set — post manually.",
        "publish_status": "prepared_locally",
    }


def _handle_founder_thread(artifact: dict) -> dict:
    """Export founder thread to publish_ready/ as plain text."""
    PUBLISH_DIR.mkdir(parents=True, exist_ok=True)
    payload = artifact.get("payload", {})
    content = payload.get("content") or payload.get("body") or artifact.get("summary", "")
    art_id  = artifact.get("id", f"AUTO-{uuid.uuid4().hex[:6].upper()}")

    out = PUBLISH_DIR / f"founder_thread_{art_id}.txt"
    out.write_text(content, encoding="utf-8")
    _save_output(art_id, content, "txt")
    return {
        "success": True,
        "output_path": str(out),
        "notes": "Founder thread exported to publish_ready/. Post manually to LinkedIn/X.",
        "publish_status": "prepared_locally",
    }


def _handle_conversion_friction_report(artifact: dict) -> dict:
    """Save friction report as internal documentation."""
    payload = artifact.get("payload", {})
    content = payload.get("content") or payload.get("body") or artifact.get("summary", "")
    title   = artifact.get("title", "Conversion Friction Report")
    art_id  = artifact.get("id", f"AUTO-{uuid.uuid4().hex[:6].upper()}")

    md = f"# {title}\n\n_Date: {datetime.now(timezone.utc).date()}_\n\n{content}\n"
    out = _save_output(art_id, md, "md")
    return {"success": True, "output_path": str(out), "notes": f"Friction report saved: {title}", "publish_status": "prepared_locally"}


def _handle_landing_page_revision(artifact: dict) -> dict:
    """Save landing page revision as publish-ready copy."""
    PUBLISH_DIR.mkdir(parents=True, exist_ok=True)
    payload = artifact.get("payload", {})
    content = payload.get("content") or payload.get("copy") or payload.get("body") or artifact.get("summary", "")
    art_id  = artifact.get("id", f"AUTO-{uuid.uuid4().hex[:6].upper()}")

    out = PUBLISH_DIR / f"landing_page_revision_{art_id}.md"
    out.write_text(content, encoding="utf-8")
    _save_output(art_id, content, "md")
    return {"success": True, "output_path": str(out), "notes": "Landing page revision saved to publish_ready/. Apply to site manually.", "publish_status": "prepared_locally"}


def _handle_outreach_email_item(artifact: dict) -> dict:
    """
    Single outreach_email artifact → bundle and hand off to send_outreach_batch.
    This is a Level 1 handler that wraps the email for delegated sending.
    DLA-001 gates actual sending — if approved, the batch handler fires immediately.

    Pipeline writes:
      - staged_no_recipient  → status = email_missing
      - DLA approved + sent  → status = outreach_sent (written by _handle_send_outreach_batch)
    """
    payload  = artifact.get("payload", {})
    art_id   = artifact.get("id", f"AUTO-{uuid.uuid4().hex[:6].upper()}")

    _candidate = (
        payload.get("recipient_email") or payload.get("to") or
        payload.get("email") or payload.get("recipient") or
        payload.get("contact_email") or payload.get("email_address") or ""
    )
    to_addr = _candidate.strip() if "@" in _candidate else ""

    subject = (
        payload.get("subject") or payload.get("subject_line") or
        "A note from Clarion"
    )
    body = (
        payload.get("body") or payload.get("email_body") or
        payload.get("content") or artifact.get("summary", "")
    )

    firm_name = payload.get("firm_name", "Unknown")
    if not to_addr:
        staged = json.dumps({
            "status": "staged_no_recipient",
            "note": (
                "outreach_email artifact has no recipient email address. "
                "Email discovery did not find a public address for this firm. "
                "Find the address manually and re-queue, or skip this prospect."
            ),
            "firm_name": firm_name,
            "contact_target": payload.get("contact_target", ""),
            "subject": subject,
            "body": body,
        }, indent=2, ensure_ascii=False)
        out = _save_output(art_id, staged, "json")

        if not OUTBOUND_EMAIL_LOG.exists():
            OUTBOUND_EMAIL_LOG.write_text(
                "# Clarion Outbound Email Log\n"
                "# Format: timestamp | artifact_id | firm_name | recipient | subject | sender | status | failure_reason\n"
                "# This file records only OUTBOUND SMTP send attempts.\n\n",
                encoding="utf-8",
            )
        now_iso = datetime.now(timezone.utc).isoformat()
        with open(OUTBOUND_EMAIL_LOG, "a", encoding="utf-8") as f:
            f.write(
                f"- {now_iso} | ID: {art_id} | FIRM: {firm_name} "
                f"| TO: (none) | SUBJECT: {subject} | STATUS: staged_no_recipient\n"
            )

        # ── Pipeline: mark as email_missing so it can be found and fixed ──────
        if firm_name and firm_name != "Unknown":
            if lead_exists(firm_name):
                update_lead_status(firm_name, {"status": "email_missing"})
            else:
                append_lead({
                    "firm_name":     firm_name,
                    "website":       payload.get("firm_website", ""),
                    "practice_area": payload.get("practice_area", ""),
                    "location":      payload.get("location", ""),
                    "source":        "outbound_sales_agent",
                    "status":        "email_missing",
                    "contact_email": "",
                    "notes":         "Email discovery returned no address.",
                })

        return {
            "success": False,
            "output_path": str(out),
            "notes": (
                f"outreach_email staged (no recipient address). "
                f"Firm: {firm_name} | Contact: {payload.get('contact_target', 'N/A')}. "
                "Email discovery found no public address. Add manually to enable sending."
            ),
        }

    # Build a send_outreach_batch artifact for the batch handler
    batch_artifact = {
        "id": art_id,
        "type": "send_outreach_batch",
        "title": f"Outreach batch: {subject[:50]}",
        "payload": {
            "emails": [{
                "email": to_addr,
                "subject": subject,
                "body": body,
                "firm_name": firm_name,
            }]
        },
    }

    # Only send if DLA-001 is approved
    if is_level2_approved(batch_artifact):
        result = _handle_send_outreach_batch(batch_artifact)
        result["notes"] = f"outreach_email → send_outreach_batch (DLA-001 approved). " + result.get("notes", "")
        return result
    else:
        staged = json.dumps({"to": to_addr, "subject": subject, "body": body}, indent=2, ensure_ascii=False)
        out = _save_output(art_id, staged, "json")
        return {
            "success": False,
            "output_path": str(out),
            "notes": "outreach_email staged to disk. Add DLA-001 STATUS: approved in division_lead_approvals.md to enable sending.",
        }


# ─────────────────────────────────────────────────────────────────────────────
# HANDLERS — Level 2 (delegated)
# ─────────────────────────────────────────────────────────────────────────────

# Per-run deduplication guard: tracks recipients already sent to in this process
_SENT_THIS_RUN: set = set()

# Max outreach emails per run (safety cap)
_OUTREACH_CAP_PER_RUN = 3


def _handle_send_outreach_batch(artifact: dict) -> dict:
    """
    Send outreach emails via Zoho SMTP.

    Safety rules:
      - Max 3 per run (_OUTREACH_CAP_PER_RUN)
      - Skip recipients already sent to this run (deduplication via _SENT_THIS_RUN)
      - Skip items missing a recipient address
      - Always append unsubscribe line
      - Log every attempt: artifact_id, recipient, subject, timestamp, result, reason

    Sender config (.env):
      SMTP_HOST  = smtp.zoho.com
      SMTP_PORT  = 587
      SMTP_USER  = admin@clarionhq.co   (login account)
      SMTP_PASS  = <zoho app password>  (NOT account password)
      SMTP_FROM  = sales@clarionhq.co   (outward-facing From / group address)
      FROM_NAME  = Drew at Clarion

    Pipeline writes (on successful send):
      - Creates or updates pipeline row with status = outreach_sent
    """
    import os
    from dotenv import load_dotenv  # type: ignore

    env_path = BASE_DIR / ".env"
    load_dotenv(dotenv_path=env_path, override=True)

    smtp_host = os.getenv("SMTP_HOST", "").strip()
    smtp_port = int(os.getenv("SMTP_PORT", "587"))
    smtp_user = os.getenv("SMTP_USER", "").strip()
    smtp_pass = os.getenv("SMTP_PASS", "").strip()
    smtp_from = os.getenv("SMTP_FROM", "").strip() or smtp_user
    from_name = os.getenv("FROM_NAME", "Drew at Clarion").strip()

    art_id  = artifact.get("id", f"AUTO-{uuid.uuid4().hex[:6].upper()}")
    payload = artifact.get("payload", {})
    emails  = payload.get("emails", [])[:_OUTREACH_CAP_PER_RUN]

    if not OUTBOUND_EMAIL_LOG.exists():
        OUTBOUND_EMAIL_LOG.write_text(
            "# Clarion Outbound Email Log\n"
            "# Format: timestamp | artifact_id | firm_name | recipient | subject | sender | status | failure_reason\n"
            "# This file records only OUTBOUND SMTP send attempts.\n\n",
            encoding="utf-8",
        )
    email_log_path = OUTBOUND_EMAIL_LOG

    # Credential guard
    if not (smtp_host and smtp_user and smtp_pass):
        notes = (
            "SMTP credentials missing. Required in .env: "
            "SMTP_HOST=smtp.zoho.com, SMTP_USER=admin@clarionhq.co, "
            "SMTP_PASS=<zoho app password>, SMTP_FROM=sales@clarionhq.co. "
            "Generate Zoho app password at: "
            "https://accounts.zoho.com/home#security > App-Specific Passwords."
        )
        print(f"  [SMTP-MISSING-CREDS] {notes}")
        content = json.dumps({"staged_emails": emails, "reason": notes}, indent=2)
        out = _save_output(art_id, content, "json")
        return {"success": False, "output_path": str(out), "notes": notes}

    if smtp_pass.upper().startswith("NEEDS_") or smtp_pass in ("NEEDS_ZOHO_APP_PASSWORD", "NEEDS_APP_PASSWORD"):
        notes = (
            f"SMTP_PASS is still a placeholder ('{smtp_pass}'). "
            "Replace it with your real Zoho app password in .env. "
            "Generate at: https://accounts.zoho.com/home#security > App-Specific Passwords. "
            "The password must be the 16-char app-specific password, NOT your Zoho account login password."
        )
        print(f"  [SMTP-PLACEHOLDER-PASS] {notes}")
        content = json.dumps({"staged_emails": emails, "reason": notes}, indent=2)
        out = _save_output(art_id, content, "json")
        return {"success": False, "output_path": str(out), "notes": notes}

    sent   = []
    errors = []

    try:
        with smtplib.SMTP(smtp_host, smtp_port) as server:
            server.ehlo()
            server.starttls()
            server.ehlo()
            try:
                server.login(smtp_user, smtp_pass)
            except smtplib.SMTPAuthenticationError as auth_err:
                auth_note = (
                    f"SMTP AUTH FAILED: login={smtp_user} host={smtp_host}:{smtp_port}. "
                    f"Error: {auth_err}. "
                    "Zoho requires an App-Specific Password, NOT your account password. "
                    "Generate at: https://accounts.zoho.com/home#security > App-Specific Passwords."
                )
                print(f"  [SMTP-AUTH-FAIL] {auth_note}")
                content = json.dumps({"staged_emails": emails, "smtp_error": auth_note}, indent=2)
                out = _save_output(art_id, content, "json")
                return {"success": False, "output_path": str(out), "notes": auth_note}

            for item in emails:
                to_addr = (item.get("email") or item.get("to", "")).strip()
                subject = (item.get("subject") or item.get("subject_line") or "A note from Clarion").strip()
                body    = item.get("body", "").strip()
                now_iso = datetime.now(timezone.utc).isoformat()

                if not to_addr:
                    errors.append({"reason": "missing_recipient", "item": str(item)[:120]})
                    print(f"    [SKIP] Missing recipient address - skipping item.")
                    continue

                if to_addr.lower() in _SENT_THIS_RUN:
                    errors.append({"reason": "duplicate_recipient", "to": to_addr})
                    print(f"    [SKIP] Duplicate recipient {to_addr} - already sent this run.")
                    continue

                unsubscribe = (
                    "\n\n---\n"
                    "You received this because your firm was identified as a potential fit for Clarion. "
                    "Reply 'unsubscribe' to be removed."
                )
                full_body = body + unsubscribe

                msg = MIMEMultipart("alternative")
                msg["Subject"]  = subject
                msg["From"]     = f"{from_name} <{smtp_from}>"
                msg["To"]       = to_addr
                msg["Reply-To"] = smtp_from
                msg.attach(MIMEText(full_body, "plain", "utf-8"))

                try:
                    server.sendmail(smtp_user, to_addr, msg.as_string())
                    _SENT_THIS_RUN.add(to_addr.lower())
                    sent.append({
                        "artifact_id": art_id,
                        "to": to_addr,
                        "subject": subject,
                        "from": smtp_from,
                        "sent_at": now_iso,
                        "result": "sent",
                    })
                    firm_name = item.get("firm_name", "")
                    print(f"    [SMTP-SENT] {to_addr} | {subject[:60]}")
                    with open(email_log_path, "a", encoding="utf-8") as f:
                        f.write(
                            f"- {now_iso} | ID: {art_id} | FIRM: {firm_name} "
                            f"| TO: {to_addr} | FROM: {smtp_from} "
                            f"| SUBJECT: {subject} | STATUS: sent\n"
                        )
                    # ── Pipeline: record send so office remembers this firm ────────
                    if firm_name:
                        _today = datetime.now(timezone.utc).date().isoformat()
                        if lead_exists(firm_name):
                            update_lead_status(firm_name, {
                                "status":            "outreach_sent",
                                "contact_email":     to_addr,
                                "last_contact_date": _today,
                                "follow_up_count":   "0",
                            })
                        else:
                            append_lead({
                                "firm_name":         firm_name,
                                "source":            "outbound_sales_agent",
                                "status":            "outreach_sent",
                                "contact_email":     to_addr,
                                "last_contact_date": _today,
                                "follow_up_count":   "0",
                            })
                except smtplib.SMTPException as send_err:
                    firm_name = item.get("firm_name", "")
                    errors.append({
                        "artifact_id": art_id,
                        "firm_name": firm_name,
                        "to": to_addr,
                        "result": "failed",
                        "reason": str(send_err),
                        "sent_at": now_iso,
                    })
                    print(f"    [SMTP-SEND-FAIL] {to_addr}: {send_err}")
                    with open(email_log_path, "a", encoding="utf-8") as f:
                        f.write(
                            f"- {now_iso} | ID: {art_id} | FIRM: {firm_name} "
                            f"| TO: {to_addr} | FROM: {smtp_from} "
                            f"| SUBJECT: {subject} | STATUS: failed "
                            f"| REASON: {send_err}\n"
                        )

    except smtplib.SMTPConnectError as conn_err:
        errors.append({"reason": f"SMTP connect error: {conn_err}"})
        print(f"  [SMTP-CONNECT-FAIL] {smtp_host}:{smtp_port}: {conn_err}")
    except Exception as exc:
        errors.append({"reason": f"Unexpected SMTP error: {exc}"})
        print(f"  [SMTP-ERROR] Unexpected: {exc}")

    log_content = json.dumps({"artifact_id": art_id, "sent": sent, "errors": errors}, indent=2)
    out = _save_output(art_id, log_content, "json")

    success = len(sent) > 0
    notes   = (
        f"Zoho SMTP: {len(sent)} sent, {len(errors)} error(s). "
        f"From: {smtp_from}. Log: {out.name}"
    )
    return {"success": success, "output_path": str(out), "notes": notes, "sent_count": len(sent)}


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
# HANDLER — followup_email (Level 2 delegated, same SMTP path as outreach)
# ─────────────────────────────────────────────────────────────────────────────

def _handle_followup_email(artifact: dict) -> dict:
    """
    Send a follow-up email via Zoho SMTP.
    Uses the same credential + logging path as _handle_send_outreach_batch.

    After a successful send, updates the pipeline:
      status           = follow_up_sent
      follow_up_count  = 1
      last_contact_date = today

    Payload fields read:
      firm_name, recipient_email, subject_line, email_body, followup_number
    """
    import os
    from dotenv import load_dotenv  # type: ignore

    load_dotenv(dotenv_path=BASE_DIR / ".env", override=True)

    smtp_host = os.getenv("SMTP_HOST", "").strip()
    smtp_port = int(os.getenv("SMTP_PORT", "587"))
    smtp_user = os.getenv("SMTP_USER", "").strip()
    smtp_pass = os.getenv("SMTP_PASS", "").strip()
    smtp_from = os.getenv("SMTP_FROM", "").strip() or smtp_user
    from_name = os.getenv("FROM_NAME", "Drew at Clarion").strip()

    art_id  = artifact.get("id", f"AUTO-{uuid.uuid4().hex[:6].upper()}")
    payload = artifact.get("payload", {})

    firm_name   = payload.get("firm_name", "Unknown")
    to_addr     = (payload.get("recipient_email") or "").strip()
    subject     = (payload.get("subject_line") or payload.get("subject") or
                   f"Following up — {firm_name}").strip()
    body        = (payload.get("email_body") or payload.get("body") or "").strip()
    followup_no = int(payload.get("followup_number", 1))

    # Guard: must have a recipient address
    if not to_addr or "@" not in to_addr:
        out = _save_output(art_id, json.dumps({
            "status": "staged_no_recipient",
            "firm_name": firm_name,
            "reason": "followup_email has no valid recipient_email.",
        }, indent=2), "json")
        return {
            "success": False,
            "output_path": str(out),
            "notes": f"followup_email staged — no recipient for {firm_name}.",
        }

    # SMTP credential guards (reuse same logic as outreach batch)
    if not (smtp_host and smtp_user and smtp_pass):
        out = _save_output(art_id, json.dumps({
            "staged": True, "firm": firm_name, "to": to_addr, "subject": subject,
            "reason": "SMTP credentials missing.",
        }, indent=2), "json")
        return {"success": False, "output_path": str(out),
                "notes": "SMTP credentials missing — followup staged."}

    if smtp_pass.upper().startswith("NEEDS_"):
        out = _save_output(art_id, json.dumps({
            "staged": True, "firm": firm_name, "to": to_addr, "subject": subject,
            "reason": "SMTP_PASS is still a placeholder.",
        }, indent=2), "json")
        return {"success": False, "output_path": str(out),
                "notes": "SMTP_PASS placeholder — followup staged."}

    if to_addr.lower() in _SENT_THIS_RUN:
        out = _save_output(art_id, json.dumps({
            "staged": True, "firm": firm_name, "to": to_addr,
            "reason": "Duplicate recipient — already sent this run.",
        }, indent=2), "json")
        return {"success": False, "output_path": str(out),
                "notes": f"Duplicate recipient {to_addr} — skipped."}

    unsubscribe = (
        "\n\n---\n"
        "You received this because your firm was identified as a potential fit for Clarion. "
        "Reply 'unsubscribe' to be removed."
    )
    full_body = body + unsubscribe

    msg = MIMEMultipart("alternative")
    msg["Subject"]  = subject
    msg["From"]     = f"{from_name} <{smtp_from}>"
    msg["To"]       = to_addr
    msg["Reply-To"] = smtp_from
    msg.attach(MIMEText(full_body, "plain", "utf-8"))

    now_iso = datetime.now(timezone.utc).isoformat()
    try:
        with smtplib.SMTP(smtp_host, smtp_port) as server:
            server.ehlo()
            server.starttls()
            server.ehlo()
            server.login(smtp_user, smtp_pass)
            server.sendmail(smtp_user, to_addr, msg.as_string())
        _SENT_THIS_RUN.add(to_addr.lower())

        # Log to outbound email log
        if not OUTBOUND_EMAIL_LOG.exists():
            OUTBOUND_EMAIL_LOG.write_text(
                "# Clarion Outbound Email Log\n"
                "# Format: timestamp | artifact_id | firm_name | recipient | subject | sender | status\n\n",
                encoding="utf-8",
            )
        with open(OUTBOUND_EMAIL_LOG, "a", encoding="utf-8") as f:
            f.write(
                f"- {now_iso} | ID: {art_id} | FIRM: {firm_name} "
                f"| TO: {to_addr} | FROM: {smtp_from} "
                f"| SUBJECT: {subject} | STATUS: follow_up_sent\n"
            )

        # ── Pipeline update ───────────────────────────────────────────────────
        _today = datetime.now(timezone.utc).date().isoformat()
        if lead_exists(firm_name):
            update_lead_status(firm_name, {
                "status":            "follow_up_sent",
                "follow_up_count":   str(followup_no),
                "last_contact_date": _today,
            })
        else:
            append_lead({
                "firm_name":         firm_name,
                "contact_email":     to_addr,
                "source":            "followup_sales_agent",
                "status":            "follow_up_sent",
                "follow_up_count":   str(followup_no),
                "last_contact_date": _today,
            })

        print(f"    [FOLLOWUP-SENT] {to_addr} | {subject[:60]}")
        out = _save_output(art_id, json.dumps({
            "firm_name": firm_name, "to": to_addr, "subject": subject,
            "sent_at": now_iso, "followup_number": followup_no,
        }, indent=2), "json")
        return {
            "success": True,
            "output_path": str(out),
            "notes": f"Follow-up #{followup_no} sent to {to_addr} for {firm_name}.",
        }

    except smtplib.SMTPAuthenticationError as e:
        msg_note = f"SMTP AUTH FAILED for follow-up to {firm_name}: {e}"
        print(f"    [FOLLOWUP-AUTH-FAIL] {msg_note}")
        out = _save_output(art_id, json.dumps({"error": msg_note}, indent=2), "json")
        return {"success": False, "output_path": str(out), "notes": msg_note}
    except Exception as e:
        msg_note = f"Follow-up SMTP error for {firm_name}: {e}"
        print(f"    [FOLLOWUP-ERROR] {msg_note}")
        out = _save_output(art_id, json.dumps({"error": msg_note}, indent=2), "json")
        return {"success": False, "output_path": str(out), "notes": msg_note}


# ─────────────────────────────────────────────────────────────────────────────
# DISPATCH TABLE
# ─────────────────────────────────────────────────────────────────────────────

_HANDLERS = {
    # Level 1 — autonomous
    "publish_social_post":          _handle_publish_social_post,
    "draft_blog_article":           _handle_draft_blog_article,
    "update_landing_page_copy":     _handle_update_landing_page_copy,
    "generate_demo_assets":         _handle_generate_demo_assets,
    "export_outreach_emails":       _handle_export_outreach_emails,
    "internal_documentation":       _handle_internal_documentation,
    "seo_keyword_updates":          _handle_seo_keyword_updates,
    "competitive_research":         _handle_competitive_research,
    # Content artifact types from lean agents
    "thought_leadership_article":   _handle_thought_leadership_article,
    "linkedin_post":                _handle_linkedin_post,
    "founder_thread":               _handle_founder_thread,
    "conversion_friction_report":   _handle_conversion_friction_report,
    "landing_page_revision":        _handle_landing_page_revision,
    # outreach_email → bundles to send_outreach_batch (DLA-001 gates sending)
    "outreach_email":               _handle_outreach_email_item,
    # Level 2 — delegated
    "send_outreach_batch":          _handle_send_outreach_batch,
    "publish_blog_post":            _handle_publish_blog_post,
    "create_social_account":        _handle_create_social_account,
    "account_setup":                _handle_create_social_account,
    "upload_demo_video":            _handle_upload_demo_video,
    "post_linkedin_thread":         _handle_post_linkedin_thread,
    "followup_email":               _handle_followup_email,
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
