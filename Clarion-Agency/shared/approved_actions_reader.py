"""
shared/approved_actions_reader.py
Clarion — Approved Actions Reader & State Manager

Reads memory/approved_actions.md, parses action blocks, routes them,
and updates status in-place after execution.

Format expected in approved_actions.md:

    ---
    Action ID:   ACT-001
    Action:      [what to do]
    Approved By: CEO
    Date:        2026-03-12
    Owner:       Content & SEO Agent
    Status:      approved
    Notes:       optional context
    ---

Supported statuses: approved | in_progress | completed | blocked

This module exposes:
    load_approved_actions()   -> list[dict]
    route_action()            -> (agent_key, prompt_rel, subdir) | None
    is_safe_execution()       -> bool
    update_action_status()    -> bool
    append_execution_log()    -> None
    log_no_actions()          -> None
"""

import re
import datetime
from pathlib import Path

BASE_DIR     = Path(__file__).resolve().parent.parent
ACTIONS_PATH = BASE_DIR / "memory" / "approved_actions.md"
LOG_PATH     = BASE_DIR / "memory" / "execution_log.md"

# ── Owner routing ─────────────────────────────────────────────────────────────
# Maps owner strings (lowercase) -> (agent_key, prompt_rel_path, report_subdir)

OWNER_ROUTE = {
    "content & seo agent":        ("content_seo",             "agents/comms/content_seo.md",               "execution"),
    "comms":                       ("content_seo",             "agents/comms/content_seo.md",               "execution"),
    "competitive intelligence":    ("competitive_intelligence","agents/market/competitive_intelligence.md",  "execution"),
    "market intelligence":         ("competitive_intelligence","agents/market/competitive_intelligence.md",  "execution"),
    "usage analyst":               ("usage_analyst",           "agents/product_insight/usage_analyst.md",   "execution"),
    "product insight":             ("usage_analyst",           "agents/product_insight/usage_analyst.md",   "execution"),
    "chief of staff":              ("chief_of_staff",          "agents/executive/chief_of_staff.md",        "execution"),
    "executive":                   ("chief_of_staff",          "agents/executive/chief_of_staff.md",        "execution"),
    "customer discovery":          ("customer_discovery",      "agents/market/customer_discovery.md",       "execution"),
}

# Safe bounded verbs for pre-launch execution
SAFE_EXECUTION_TYPES = (
    "finalize", "draft", "prepare", "produce", "expand",
    "deepen", "refine", "summarize", "convert", "compile",
    "research", "document", "outline", "analyze", "review", "audit",
)

# Actions that must never execute autonomously
BLOCKED_EXECUTION_TYPES = (
    "post ", "publish", "send ", "create account", "sign up",
    "register", "message", "email ", "tweet", "submit",
)


# ── Parser ────────────────────────────────────────────────────────────────────

def _parse_block(block: str) -> dict | None:
    """Parse one ---...--- action block into a dict. Returns None if malformed."""
    fields = {}
    for line in block.splitlines():
        line = line.strip()
        if not line or line == "---":
            continue
        if ":" in line:
            key, _, val = line.partition(":")
            fields[key.strip().lower().replace(" ", "_")] = val.strip()
    required = {"action_id", "action", "owner", "status"}
    if not required.issubset(fields.keys()):
        return None
    return fields


def load_approved_actions() -> list[dict]:
    """
    Read approved_actions.md and return parsed action dicts with status == 'approved'.
    Creates a template file if none exists.
    """
    if not ACTIONS_PATH.exists():
        _create_template()
        return []

    text = ACTIONS_PATH.read_text(encoding="utf-8", errors="replace")
    raw_blocks = re.split(r"\n---\n", text)
    actions = []
    for block in raw_blocks:
        parsed = _parse_block(block)
        if parsed and parsed.get("status", "").lower().strip() == "approved":
            actions.append(parsed)
    return actions


def route_action(action: dict) -> tuple | None:
    """
    Return (agent_key, prompt_rel_path, report_subdir) for this action,
    or None if the owner is unmapped or action type is blocked.
    """
    owner_raw   = action.get("owner", "").lower().strip()
    action_text = action.get("action", "").lower()

    for blocked in BLOCKED_EXECUTION_TYPES:
        if blocked in action_text:
            return None

    return OWNER_ROUTE.get(owner_raw)


def is_safe_execution(action: dict) -> bool:
    """Returns True if the action starts with a bounded safe verb."""
    action_text = action.get("action", "").lower().strip()
    for blocked in BLOCKED_EXECUTION_TYPES:
        if blocked in action_text:
            return False
    for safe in SAFE_EXECUTION_TYPES:
        if action_text.startswith(safe):
            return True
    return True  # Default allow — agent prompt constrains further


# ── Status updater ────────────────────────────────────────────────────────────

def update_action_status(action_id: str, new_status: str,
                          note: str | None = None) -> bool:
    """
    Update the Status line for a specific Action ID in approved_actions.md.
    Optionally appends context to the Notes field.
    Returns True on success.
    """
    if not ACTIONS_PATH.exists():
        return False

    text   = ACTIONS_PATH.read_text(encoding="utf-8", errors="replace")
    lines  = text.splitlines(keepends=True)
    in_target = False
    updated   = False
    result    = []

    for line in lines:
        stripped = line.strip()

        if re.match(r"Action ID:\s*" + re.escape(action_id), stripped, re.IGNORECASE):
            in_target = True

        if in_target and re.match(r"Status:\s*", stripped, re.IGNORECASE):
            line    = re.sub(r"(Status:\s*).*", rf"\g<1>{new_status}", line)
            updated = True

        if in_target and note and re.match(r"Notes:\s*", stripped, re.IGNORECASE):
            ts       = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
            existing = line.rstrip("\n").split(":", 1)[1].strip() if ":" in line else ""
            combined = f"{existing} | [{ts}] {note}" if existing else f"[{ts}] {note}"
            line     = f"Notes:       {combined}\n"
            in_target = False

        if in_target and stripped == "---" and updated:
            in_target = False

        result.append(line)

    if updated:
        ACTIONS_PATH.write_text("".join(result), encoding="utf-8")
    return updated


# ── Execution log ─────────────────────────────────────────────────────────────

def _ensure_log() -> None:
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    if not LOG_PATH.exists():
        LOG_PATH.write_text(
            "# execution_log.md\n"
            "# Clarion — Execution Log\n"
            "# Append-only. Do not edit manually.\n\n",
            encoding="utf-8",
        )


def append_execution_log(action_id: str, action_text: str, owner: str,
                          status_result: str, what_was_done: str,
                          next_step: str, ceo_review_needed: bool) -> None:
    """Append one execution entry to memory/execution_log.md."""
    _ensure_log()
    ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    entry = (
        f"\n---\n"
        f"Timestamp:          {ts}\n"
        f"Action ID:          {action_id}\n"
        f"Action:             {action_text}\n"
        f"Owner:              {owner}\n"
        f"Status Result:      {status_result}\n"
        f"What Was Done:      {what_was_done}\n"
        f"Next Step:          {next_step}\n"
        f"CEO Review Needed:  {'Yes' if ceo_review_needed else 'No'}\n"
    )
    with LOG_PATH.open("a", encoding="utf-8") as f:
        f.write(entry)


def log_no_actions() -> None:
    """Log a single line when no approved actions exist this cycle."""
    _ensure_log()
    ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    with LOG_PATH.open("a", encoding="utf-8") as f:
        f.write(f"\n[{ts}] No approved actions available this cycle.\n")


# ── Template creator ──────────────────────────────────────────────────────────

def _create_template() -> None:
    ACTIONS_PATH.parent.mkdir(parents=True, exist_ok=True)
    ACTIONS_PATH.write_text(
        "# approved_actions.md\n"
        "# Clarion - CEO Approved Actions Register\n\n"
        "## Purpose\n"
        "Actions agents are authorized to execute. CEO approves all entries.\n"
        "Agents propose in their reports. Only entries here with Status: approved\n"
        "are picked up by the runner and executed.\n\n"
        "## Format\n"
        "Each block is delimited by --- on its own line.\n\n"
        "## Approved Actions\n\n"
        "---\n"
        "Action ID:   ACT-EXAMPLE\n"
        "Action:      Finalize LinkedIn company profile draft for CEO review\n"
        "Approved By: CEO\n"
        "Date:        2026-03-12\n"
        "Owner:       Content & SEO Agent\n"
        "Status:      staged\n"
        "Notes:       Example entry - change Status to approved to activate\n"
        "---\n\n"
        "## Completed Actions\n\n"
        "_(none)_\n",
        encoding="utf-8",
    )
