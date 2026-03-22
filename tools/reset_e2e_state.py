import hashlib
import os
import sqlite3
from pathlib import Path
from typing import Iterable

try:
    from dotenv import dotenv_values
except Exception:  # pragma: no cover - fallback when python-dotenv is unavailable
    dotenv_values = None


REPO_ROOT = Path(__file__).resolve().parents[1]
BACKEND_DIR = REPO_ROOT / "backend"
BACKEND_ENV_FILE = BACKEND_DIR / ".env"


def _load_backend_env() -> dict[str, str]:
    if dotenv_values is None or not BACKEND_ENV_FILE.exists():
        return {}
    values = dotenv_values(BACKEND_ENV_FILE)
    return {
        str(key): str(value)
        for key, value in values.items()
        if key and value is not None
    }


def _normalize_firm_plan(raw_value: str | None) -> tuple[str, str]:
    value = str(raw_value or "team").strip().lower()
    if value in {"firm", "annual", "firm_annual", "leadership"}:
        return ("firm", "annual")
    if value in {"team", "monthly", "team_monthly", "professional"}:
        return ("team", "monthly")
    return ("free", "trial")


def _db_path() -> str:
    backend_env = _load_backend_env()
    env_path = (os.environ.get("DATABASE_PATH") or backend_env.get("DATABASE_PATH") or "").strip()
    if env_path:
        return os.path.abspath(env_path)

    database_url = (os.environ.get("DATABASE_URL") or backend_env.get("DATABASE_URL") or "").strip()
    if database_url.startswith("sqlite:///"):
        sqlite_path = database_url.replace("sqlite:///", "", 1)
        return os.path.abspath(os.path.join(BACKEND_DIR, sqlite_path))

    return str((BACKEND_DIR / "feedback.db").resolve())


def _table_exists(cur: sqlite3.Cursor, table: str) -> bool:
    cur.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name = ?", (table,))
    return cur.fetchone() is not None


def _table_columns(cur: sqlite3.Cursor, table: str) -> set[str]:
    cur.execute(f"PRAGMA table_info({table})")
    return {str(row[1]) for row in cur.fetchall()}


def _delete_where_in(cur: sqlite3.Cursor, table: str, col: str, ids: Iterable[int]) -> int:
    values = [int(v) for v in ids]
    if not values:
        return 0
    placeholders = ",".join("?" for _ in values)
    sql = f"DELETE FROM {table} WHERE {col} IN ({placeholders})"
    cur.execute(sql, tuple(values))
    return int(cur.rowcount or 0)


def _delete_where_eq(cur: sqlite3.Cursor, table: str, col: str, value: int) -> int:
    cur.execute(f"DELETE FROM {table} WHERE {col} = ?", (int(value),))
    return int(cur.rowcount or 0)


def _reset_login_backoff_redis(email: str, client_ip: str = "127.0.0.1") -> bool:
    """
    Best-effort reset for Redis-backed login backoff keys.
    If Redis is not configured, this is a no-op.
    """
    redis_url = (os.environ.get("REDIS_URL") or "").strip()
    if not redis_url:
        return False
    try:
        import redis  # type: ignore
    except Exception:
        return False

    try:
        r = redis.Redis.from_url(redis_url, decode_responses=True)
        acct_hash = hashlib.sha256(email.encode()).hexdigest()[:16]
        keys = [f"login_fail:ip:{client_ip}", f"login_fail:acct:{acct_hash}"]
        r.delete(*keys)
        return True
    except Exception:
        return False


def main() -> None:
    email = (os.environ.get("E2E_SMOKE_EMAIL") or "smoke.e2e@lawfirminsights.local").strip().lower()
    firm_plan, subscription_type = _normalize_firm_plan(os.environ.get("E2E_SMOKE_PLAN"))
    db_path = _db_path()
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    cur.execute("SELECT id FROM users WHERE email = ? OR username = ? LIMIT 1", (email, email))
    user_row = cur.fetchone()
    if not user_row:
        conn.close()
        print("[e2e-reset] user found=false reports_deleted=0 actions_deleted=0 limiter_reset=false")
        return

    user_id = int(user_row["id"])
    reports_deleted = 0
    actions_deleted = 0

    firm_ids: list[int] = []
    if _table_exists(cur, "firm_users"):
        cur.execute("SELECT firm_id FROM firm_users WHERE user_id = ?", (user_id,))
        firm_ids = [int(row["firm_id"]) for row in cur.fetchall()]

    report_ids: list[int] = []
    if _table_exists(cur, "reports"):
        report_cols = _table_columns(cur, "reports")
        predicates: list[str] = []
        params: list[int] = []
        if "user_id" in report_cols:
            predicates.append("user_id = ?")
            params.append(user_id)
        if "firm_id" in report_cols and firm_ids:
            predicates.append(f"firm_id IN ({','.join('?' for _ in firm_ids)})")
            params.extend(firm_ids)
        if predicates:
            cur.execute(f"SELECT id FROM reports WHERE {' OR '.join(predicates)}", tuple(params))
            report_ids = [int(row["id"]) for row in cur.fetchall()]

    # Delete action rows first.
    if _table_exists(cur, "report_action_items"):
        cols = _table_columns(cur, "report_action_items")
        if "report_id" in cols:
            actions_deleted += _delete_where_in(cur, "report_action_items", "report_id", report_ids)
        if "user_id" in cols:
            actions_deleted += _delete_where_eq(cur, "report_action_items", "user_id", user_id)
        if "firm_id" in cols:
            for fid in firm_ids:
                actions_deleted += _delete_where_eq(cur, "report_action_items", "firm_id", fid)

    if _table_exists(cur, "report_actions"):
        actions_deleted += _delete_where_in(cur, "report_actions", "report_id", report_ids)

    if _table_exists(cur, "report_theme_metrics"):
        cols = _table_columns(cur, "report_theme_metrics")
        if "report_id" in cols:
            _delete_where_in(cur, "report_theme_metrics", "report_id", report_ids)
        if "user_id" in cols:
            _delete_where_eq(cur, "report_theme_metrics", "user_id", user_id)

    if _table_exists(cur, "report_pdf_artifacts"):
        cols = _table_columns(cur, "report_pdf_artifacts")
        if "report_id" in cols:
            _delete_where_in(cur, "report_pdf_artifacts", "report_id", report_ids)
        if "user_id" in cols:
            _delete_where_eq(cur, "report_pdf_artifacts", "user_id", user_id)

    # Optional snapshot tables if present in a given branch.
    for snapshot_table in ("report_snapshots", "exposure_snapshots"):
        if _table_exists(cur, snapshot_table):
            cols = _table_columns(cur, snapshot_table)
            if "report_id" in cols:
                _delete_where_in(cur, snapshot_table, "report_id", report_ids)
            if "user_id" in cols:
                _delete_where_eq(cur, snapshot_table, "user_id", user_id)
            if "firm_id" in cols:
                for fid in firm_ids:
                    _delete_where_eq(cur, snapshot_table, "firm_id", fid)

    if _table_exists(cur, "governance_briefs"):
        for fid in firm_ids:
            _delete_where_eq(cur, "governance_briefs", "firm_id", fid)

    if _table_exists(cur, "interest_events"):
        for fid in firm_ids:
            _delete_where_eq(cur, "interest_events", "firm_id", fid)
        _delete_where_eq(cur, "interest_events", "user_id", user_id)

    if _table_exists(cur, "audit_log"):
        for fid in firm_ids:
            _delete_where_eq(cur, "audit_log", "firm_id", fid)

    if _table_exists(cur, "security_events"):
        _delete_where_eq(cur, "security_events", "user_id", user_id)

    if _table_exists(cur, "theme_ledger"):
        _delete_where_eq(cur, "theme_ledger", "user_id", user_id)

    if _table_exists(cur, "report_pack_schedules"):
        _delete_where_eq(cur, "report_pack_schedules", "user_id", user_id)

    if _table_exists(cur, "account_branding"):
        _delete_where_eq(cur, "account_branding", "user_id", user_id)

    if _table_exists(cur, "email_verification_tokens"):
        _delete_where_eq(cur, "email_verification_tokens", "user_id", user_id)
    if _table_exists(cur, "password_reset_tokens"):
        _delete_where_eq(cur, "password_reset_tokens", "user_id", user_id)
    if _table_exists(cur, "two_factor_challenges"):
        _delete_where_eq(cur, "two_factor_challenges", "user_id", user_id)
    if _table_exists(cur, "processed_checkout_sessions"):
        _delete_where_eq(cur, "processed_checkout_sessions", "user_id", user_id)

    if _table_exists(cur, "reports"):
        reports_deleted += _delete_where_in(cur, "reports", "id", report_ids)

    # Reset usage counters and 2FA for deterministic login flow.
    if _table_exists(cur, "users"):
        user_cols = _table_columns(cur, "users")
        sets: list[str] = []
        params: list[object] = []
        if "trial_reviews_used" in user_cols:
            sets.append("trial_reviews_used = 0")
        if "trial_reports_used" in user_cols:
            sets.append("trial_reports_used = 0")
        if "one_time_reports_used" in user_cols:
            sets.append("one_time_reports_used = 0")
        if "two_factor_enabled" in user_cols:
            sets.append("two_factor_enabled = 0")
        if "subscription_status" in user_cols:
            sets.append("subscription_status = 'active'")
        if "subscription_type" in user_cols:
            sets.append("subscription_type = ?")
            params.append(subscription_type)
        if "is_verified" in user_cols:
            sets.append("is_verified = 1")
        if "email_verified" in user_cols:
            sets.append("email_verified = 1")
        if "onboarding_complete" in user_cols:
            sets.append("onboarding_complete = 1")
        # Reset auth/backoff counters where present.
        if "failed_login_attempts" in user_cols:
            sets.append("failed_login_attempts = 0")
        if "lockout_until" in user_cols:
            sets.append("lockout_until = NULL")
        if "last_failed_login_at" in user_cols:
            sets.append("last_failed_login_at = NULL")
        if "last_login_at" in user_cols:
            sets.append("last_login_at = NULL")
        if sets:
            sql = f"UPDATE users SET {', '.join(sets)} WHERE id = ?"
            params.append(user_id)
            cur.execute(sql, tuple(params))

    if _table_exists(cur, "firms"):
        firm_cols = _table_columns(cur, "firms")
        if "plan" in firm_cols:
            for fid in firm_ids:
                cur.execute("UPDATE firms SET plan = ? WHERE id = ?", (firm_plan, fid))

    limiter_rows_deleted = 0
    # Best-effort DB-backed limiter cleanup for common table names.
    for limiter_table in ("rate_limit_entries", "rate_limits", "flask_limiter", "limiter_storage"):
        if not _table_exists(cur, limiter_table):
            continue
        cols = _table_columns(cur, limiter_table)
        if "key" in cols:
            # Clear account and localhost keys if stored with serialized keys.
            cur.execute(
                f"DELETE FROM {limiter_table} WHERE key LIKE ? OR key LIKE ? OR key LIKE ?",
                (f"%{email}%", "%127.0.0.1%", "%login_fail%"),
            )
            limiter_rows_deleted += int(cur.rowcount or 0)
        elif "user_id" in cols:
            limiter_rows_deleted += _delete_where_eq(cur, limiter_table, "user_id", user_id)

    conn.commit()
    conn.close()

    # Flask-Limiter storage is memory:// by default in local dev; cannot clear from an external script.
    limiter_reset = _reset_login_backoff_redis(email) or limiter_rows_deleted > 0
    print(
        f"[e2e-reset] user found=true reports_deleted={reports_deleted} "
        f"actions_deleted={actions_deleted} limiter_reset={str(limiter_reset).lower()} "
        f"plan={firm_plan} subscription_type={subscription_type}"
    )


if __name__ == "__main__":
    main()
