"""
shared/pipeline_manager.py
Clarion Agent Office — Persistent Sales Pipeline Manager
Version: 1.0 | 2026-03-13

Provides read/write access to data/revenue/leads_pipeline.csv so every
agent that touches a prospect can record and retrieve that state.

The pipeline is the office's memory of who has been contacted, when, and
what happened. Without it, every run is stateless and will duplicate work.

Columns (must match CSV header exactly):
  firm_name        — canonical firm name (used as the lookup key)
  website          — firm website URL
  practice_area    — e.g. "Family Law"
  location         — "City, State"
  source           — where the lead was discovered (e.g. "prospect_intelligence")
  status           — lifecycle state (see STATUS VALUES below)
  contact_email    — email address used or found
  last_contact_date — ISO date of last outreach or contact
  follow_up_count  — number of follow-up messages sent
  pilot_status     — blank | offered | in_progress | complete | declined
  notes            — freeform notes
  created_at       — ISO date when the record was first added

STATUS VALUES (use these exact strings):
  prospect_discovered  — found by intel, not yet contacted
  email_missing        — no email found; cannot send until address is located
  outreach_sent        — first cold email sent
  follow_up_sent       — follow-up message sent
  replied              — prospect replied (any response)
  pilot_offered        — pilot analysis offered
  pilot_in_progress    — pilot running
  pilot_complete       — pilot brief delivered
  closed_won           — converted to customer
  closed_lost          — decided not to proceed
  do_not_contact       — removed from outreach
"""

import csv
import datetime
from pathlib import Path

BASE_DIR      = Path(__file__).resolve().parent.parent
PIPELINE_PATH = BASE_DIR / "data" / "revenue" / "leads_pipeline.csv"

COLUMNS = [
    "firm_name",
    "website",
    "practice_area",
    "location",
    "source",
    "status",
    "contact_email",
    "last_contact_date",
    "follow_up_count",
    "pilot_status",
    "notes",
    "created_at",
]

def _ensure_file() -> None:
    """Create the pipeline CSV with header row if it does not exist."""
    PIPELINE_PATH.parent.mkdir(parents=True, exist_ok=True)
    if not PIPELINE_PATH.exists():
        with open(PIPELINE_PATH, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=COLUMNS)
            writer.writeheader()


def _normalise(name: str) -> str:
    """Lowercase + strip for comparison — avoids duplicate entries from
    minor capitalisation differences."""
    return name.strip().lower()


# ── Public API ─────────────────────────────────────────────────────────────────

def load_pipeline() -> list[dict]:
    """
    Return all rows in the pipeline as a list of dicts.
    Returns an empty list if the file is missing or empty.
    """
    _ensure_file()
    with open(PIPELINE_PATH, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        return [row for row in reader]


def lead_exists(firm_name: str) -> bool:
    """Return True if a row with this firm_name already exists."""
    key = _normalise(firm_name)
    return any(_normalise(row["firm_name"]) == key for row in load_pipeline())


def append_lead(record: dict) -> bool:
    """
    Append a new lead row.  Silently skips if the firm already exists
    (use update_lead_status to modify existing rows).

    record: dict with any subset of COLUMNS.  Missing keys default to "".
    Returns True if appended, False if skipped (already exists).
    """
    if lead_exists(record.get("firm_name", "")):
        return False

    _ensure_file()
    row = {col: record.get(col, "") for col in COLUMNS}
    if not row["created_at"]:
        row["created_at"] = datetime.date.today().isoformat()
    if not row["follow_up_count"]:
        row["follow_up_count"] = "0"

    with open(PIPELINE_PATH, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=COLUMNS)
        writer.writerow(row)
    return True


def update_lead_status(firm_name: str, updates: dict) -> bool:
    """
    Find the row for firm_name and apply updates dict in-place.
    Rewrites the entire file.  Returns True if a row was found and updated,
    False if no matching row exists.

    Example:
        update_lead_status("Smith Law", {
            "status": "outreach_sent",
            "contact_email": "info@smithlaw.com",
            "last_contact_date": "2026-03-13",
            "follow_up_count": "0",
        })
    """
    rows = load_pipeline()
    key = _normalise(firm_name)
    found = False
    for row in rows:
        if _normalise(row["firm_name"]) == key:
            for col, val in updates.items():
                if col in COLUMNS:
                    row[col] = str(val)
            found = True
            break

    if not found:
        return False

    _ensure_file()
    with open(PIPELINE_PATH, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=COLUMNS)
        writer.writeheader()
        writer.writerows(rows)
    return True


def get_followup_candidates(days_threshold: int = 7) -> list[dict]:
    """
    Return rows where:
      - status == "outreach_sent"
      - last_contact_date is at least days_threshold days ago
      - contact_email is not empty
      - follow_up_count is 0 (never followed up)

    These are firms that received a first cold email and have not yet been
    followed up on.  The outbound agent should draft a follow-up for each.
    """
    candidates = []
    cutoff = datetime.date.today() - datetime.timedelta(days=days_threshold)

    for row in load_pipeline():
        if row.get("status") != "outreach_sent":
            continue
        if not row.get("contact_email"):
            continue
        try:
            count = int(row.get("follow_up_count", "0"))
        except ValueError:
            count = 0
        if count > 0:
            continue
        try:
            last = datetime.date.fromisoformat(row["last_contact_date"])
        except (ValueError, KeyError):
            continue
        if last <= cutoff:
            candidates.append(row)

    return candidates
