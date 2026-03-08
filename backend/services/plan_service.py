"""Plan lookups and enforcement helpers.

All plan enforcement should read limits from backend.services.plan_limits.PLAN_LIMITS.
"""

from datetime import datetime, timedelta, timezone

from .plan_limits import PLAN_LIMITS


FIRM_PLAN_FREE = "free"
FIRM_PLAN_TEAM = "team"
FIRM_PLAN_FIRM = "firm"

_PLAN_ALIASES = {
    "trial": FIRM_PLAN_FREE,
    "professional": FIRM_PLAN_TEAM,
    "leadership": FIRM_PLAN_FIRM,
    "monthly": FIRM_PLAN_TEAM,
    "annual": FIRM_PLAN_FIRM,
}


def _normalize_plan(plan_value):
    raw = str(plan_value or FIRM_PLAN_FREE).strip().lower()
    normalized = _PLAN_ALIASES.get(raw, raw)
    if normalized in PLAN_LIMITS:
        return normalized
    return FIRM_PLAN_FREE


def get_firm_plan(firm_id, db_connect):
    conn = db_connect()
    c = conn.cursor()
    c.execute("SELECT plan FROM firms WHERE id = ?", (int(firm_id),))
    row = c.fetchone()
    conn.close()
    if not row:
        return FIRM_PLAN_FREE
    return _normalize_plan(row[0])


def get_plan_limits(firm_id, db_connect):
    plan = get_firm_plan(firm_id, db_connect)
    limits = PLAN_LIMITS.get(plan, PLAN_LIMITS[FIRM_PLAN_FREE])
    return {
        "plan": plan,
        "max_users": limits.get("max_users"),
        "max_reviews_per_upload": limits.get("max_reviews_per_upload"),
        "max_reports_per_month": limits.get("max_reports_per_month"),
        "history_days": limits.get("history_days"),
        "pdf_watermark": bool(limits.get("pdf_watermark", False)),
    }


def enforce_upload_limit(firm_id, review_count, db_connect):
    limits = get_plan_limits(firm_id, db_connect)
    max_reviews = limits.get("max_reviews_per_upload")
    if max_reviews is None:
        return None
    if int(review_count) > int(max_reviews):
        return {
            "error": "plan_limit",
            "message": f'{limits["plan"].title()} plan allows up to {int(max_reviews)} reviews per upload.',
        }
    return None


def enforce_monthly_report_limit(firm_id, db_connect, now_utc=None):
    limits = get_plan_limits(firm_id, db_connect)
    max_reports = limits.get("max_reports_per_month")
    if max_reports is None:
        return None

    now_utc = now_utc or datetime.now(timezone.utc)
    month_start = datetime(now_utc.year, now_utc.month, 1, tzinfo=timezone.utc).isoformat()
    conn = db_connect()
    c = conn.cursor()
    c.execute(
        """
        SELECT COUNT(*)
        FROM reports
        WHERE firm_id = ?
          AND deleted_at IS NULL
          AND created_at >= ?
        """,
        (int(firm_id), month_start),
    )
    used = int(c.fetchone()[0] or 0)
    conn.close()
    if used >= int(max_reports):
        return {
            "error": "plan_limit",
            "message": f'{limits["plan"].title()} plan allows up to {int(max_reports)} reports per month.',
        }
    return None


def enforce_history_access(firm_id, report_created_at, db_connect):
    limits = get_plan_limits(firm_id, db_connect)
    history_days = limits.get("history_days")
    if history_days is None:
        return None

    try:
        created_dt = datetime.fromisoformat(str(report_created_at).replace("Z", "+00:00"))
    except ValueError:
        return {"error": "Report outside plan history window"}

    if created_dt.tzinfo is None:
        created_dt = created_dt.replace(tzinfo=timezone.utc)
    else:
        created_dt = created_dt.astimezone(timezone.utc)

    cutoff = datetime.now(timezone.utc) - timedelta(days=int(history_days))
    if created_dt < cutoff:
        return {"error": "Report outside plan history window"}
    return None


def enforce_seat_limit(firm_id, db_connect):
    limits = get_plan_limits(firm_id, db_connect)
    max_users = limits.get("max_users")
    if max_users is None:
        return None

    conn = db_connect()
    c = conn.cursor()
    c.execute(
        """
        SELECT COUNT(*)
        FROM firm_users
        WHERE firm_id = ?
          AND status IN ('active', 'invited')
        """,
        (int(firm_id),),
    )
    current_seats = int(c.fetchone()[0] or 0)
    conn.close()
    if current_seats >= int(max_users):
        return {
            "error": "plan_limit",
            "message": f'{limits["plan"].title()} plan allows up to {int(max_users)} users.',
        }
    return None

