"""Governance brief HTML generator for scheduled email workflows."""

from __future__ import annotations

import json
import os
import sqlite3
from datetime import datetime


def _db_path() -> str:
    database_url = (os.getenv("DATABASE_URL") or "").strip()
    if database_url.startswith("sqlite:///"):
        return database_url.replace("sqlite:///", "", 1)
    return os.path.join(os.path.dirname(__file__), "lawfirm_feedback.db")


def _parse_themes(raw: str | None) -> str:
    if not raw:
        return "No dominant issue identified yet"
    try:
        parsed = json.loads(raw)
    except Exception:  # noqa: BLE001
        return "No dominant issue identified yet"
    if isinstance(parsed, dict) and parsed:
        ordered = sorted(parsed.items(), key=lambda item: int(item[1] or 0), reverse=True)
        return str(ordered[0][0])
    return "No dominant issue identified yet"


def _parse_top_quote(raw: str | None) -> str:
    if not raw:
        return "No client quote available yet."
    try:
        parsed = json.loads(raw)
    except Exception:  # noqa: BLE001
        return "No client quote available yet."
    if isinstance(parsed, list):
        for item in parsed:
            if isinstance(item, str) and item.strip():
                return item.strip()
            if isinstance(item, dict):
                quote = str(item.get("review_text") or "").strip()
                if quote:
                    return quote
    return "No client quote available yet."


def generate_governance_brief() -> str:
    """Build HTML summary from latest report for scheduled partner email."""
    conn = sqlite3.connect(_db_path())
    c = conn.cursor()
    c.execute(
        """
        SELECT r.id, r.created_at, r.avg_rating, r.themes, r.top_complaints, r.custom_name, f.name
        FROM reports r
        LEFT JOIN firms f ON f.id = r.firm_id
        WHERE r.deleted_at IS NULL
        ORDER BY r.created_at DESC
        LIMIT 1
        """
    )
    row = c.fetchone()
    conn.close()

    if not row:
        return """
        <h2>Clarion Client Experience Brief</h2>
        <p>No governance brief is available yet.</p>
        """

    report_id, created_at, avg_rating, themes_raw, complaints_raw, custom_name, firm_name = row
    top_issue = _parse_themes(themes_raw)
    quote = _parse_top_quote(complaints_raw)
    report_name = custom_name or f"Governance Brief #{report_id}"
    generated_label = created_at or datetime.utcnow().isoformat()
    avg_display = f"{float(avg_rating):.2f} / 5" if avg_rating is not None else "Not available"

    return f"""<!doctype html>
<html>
  <body style="font-family:Arial,sans-serif;line-height:1.5;color:#0D1B2A;">
    <h2>Clarion Client Experience Brief</h2>
    <p><strong>Firm:</strong> {firm_name or "Your Firm"}</p>
    <p><strong>Brief:</strong> {report_name}</p>
    <p><strong>Generated:</strong> {generated_label}</p>
    <p><strong>Average rating:</strong> {avg_display}</p>
    <p><strong>Top client issue:</strong> {top_issue}</p>
    <p><strong>Example quote:</strong> "{quote}"</p>
  </body>
</html>"""
