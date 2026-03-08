"""Governance signal monitor for creating firm-scoped alert records."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


def _parse_themes(raw_themes: Any) -> Dict[str, int]:
    if isinstance(raw_themes, dict):
        source = raw_themes
    else:
        try:
            source = json.loads(raw_themes or "{}")
        except Exception:
            source = {}
    out: Dict[str, int] = {}
    if not isinstance(source, dict):
        return out
    for key, value in source.items():
        try:
            out[str(key).strip().lower()] = int(value or 0)
        except Exception:
            continue
    return out


def _signal_key(title: str) -> str:
    normalized = (title or "").strip().lower()
    for suffix in (" risk",):
        if normalized.endswith(suffix):
            normalized = normalized[: -len(suffix)].strip()
    return normalized


def scan_recent_reviews_for_signals(db_connect, firm_id: Optional[int] = None) -> int:
    """Create de-duplicated active alerts when latest report signals worsen vs prior report."""
    conn = db_connect()
    c = conn.cursor()
    now_iso = datetime.now(timezone.utc).isoformat()

    if firm_id is None:
        c.execute("SELECT id FROM firms")
        firm_ids = [int(row[0]) for row in c.fetchall() if row and row[0] is not None]
    else:
        firm_ids = [int(firm_id)]

    created = 0
    for f_id in firm_ids:
        c.execute(
            """
            SELECT id, created_at, themes
            FROM reports
            WHERE firm_id = ?
              AND deleted_at IS NULL
            ORDER BY created_at DESC
            LIMIT 2
            """,
            (f_id,),
        )
        rows = c.fetchall()
        if len(rows) < 2:
            continue

        latest_report_id, _, latest_themes_raw = rows[0]
        _, _, previous_themes_raw = rows[1]
        latest_themes = _parse_themes(latest_themes_raw)
        previous_themes = _parse_themes(previous_themes_raw)

        c.execute(
            """
            SELECT title
            FROM governance_signals
            WHERE report_id = ?
            """,
            (int(latest_report_id),),
        )
        signal_rows = c.fetchall()
        for signal_row in signal_rows:
            title = str(signal_row[0] or "").strip()
            if not title:
                continue
            key = _signal_key(title)
            current = int(latest_themes.get(key) or 0)
            previous = int(previous_themes.get(key) or 0)
            delta = current - previous
            # Threshold: create alert only when pattern is meaningfully rising.
            if delta <= 0 or current < 3:
                continue

            message = f"{title.replace(' Risk', '')} complaints increasing"
            c.execute(
                """
                INSERT OR IGNORE INTO alerts (
                    firm_id, report_id, signal_type, message, occurrences, status, created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, 'active', ?, ?)
                """,
                (f_id, int(latest_report_id), key, message, int(delta), now_iso, now_iso),
            )
            if c.rowcount:
                created += 1

    conn.commit()
    conn.close()
    return created


def get_active_alerts(db_connect, firm_id: int, limit: int = 20) -> List[Dict[str, Any]]:
    conn = db_connect()
    c = conn.cursor()
    c.execute(
        """
        SELECT id, signal_type, message, occurrences, created_at, status
        FROM alerts
        WHERE firm_id = ?
          AND status = 'active'
        ORDER BY created_at DESC
        LIMIT ?
        """,
        (int(firm_id), int(max(1, min(limit, 100)))),
    )
    rows = c.fetchall()
    conn.close()
    return [
        {
            "id": int(row[0]),
            "signal_type": str(row[1] or ""),
            "message": str(row[2] or ""),
            "occurrences": int(row[3] or 0),
            "created_at": row[4],
            "status": str(row[5] or "active"),
        }
        for row in rows
    ]
