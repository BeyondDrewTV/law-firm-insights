import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from werkzeug.security import generate_password_hash

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


def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def main() -> None:
    email = os.environ.get("E2E_SMOKE_EMAIL", "smoke.e2e@lawfirminsights.local").strip().lower()
    password = os.environ.get("E2E_SMOKE_PASSWORD", "SmokeTest123")
    full_name = os.environ.get("E2E_SMOKE_NAME", "Smoke Tester")
    firm_name = os.environ.get("E2E_SMOKE_FIRM", "Smoke LLP")
    firm_plan, subscription_type = _normalize_firm_plan(os.environ.get("E2E_SMOKE_PLAN"))
    now_iso = _iso_now()

    db_path = _db_path()
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    cur.execute(
        """
        SELECT id FROM users WHERE email = ? OR username = ?
        """,
        (email, email),
    )
    row = cur.fetchone()
    if row:
        user_id = int(row["id"])
        cur.execute(
            """
            UPDATE users
            SET password_hash = ?, firm_name = ?, two_factor_enabled = 0
            WHERE id = ?
            """,
            (generate_password_hash(password), firm_name, user_id),
        )
    else:
        cur.execute(
            """
            INSERT INTO users (
                username, email, firm_name, password_hash, is_admin,
                trial_reviews_used, trial_limit, subscription_status,
                subscription_type, created_at, two_factor_enabled
            )
            VALUES (?, ?, ?, ?, 0, 0, 3, 'trial', 'trial', ?, 0)
            """,
            (email, email, firm_name, generate_password_hash(password), now_iso),
        )
        user_id = int(cur.lastrowid)

    user_columns = {
        str(row["name"])
        for row in cur.execute("PRAGMA table_info(users)").fetchall()
    }
    user_sets: list[str] = [
        "username = ?",
        "email = ?",
        "password_hash = ?",
        "firm_name = ?",
        "two_factor_enabled = 0",
        "subscription_status = 'active'",
        "subscription_type = ?",
    ]
    user_params: list[object] = [
        email,
        email,
        generate_password_hash(password),
        firm_name,
        subscription_type,
    ]
    if "full_name" in user_columns:
        user_sets.append("full_name = ?")
        user_params.append(full_name)
    if "is_verified" in user_columns:
        user_sets.append("is_verified = 1")
    if "email_verified" in user_columns:
        user_sets.append("email_verified = 1")
    if "onboarding_complete" in user_columns:
        user_sets.append("onboarding_complete = 1")
    user_params.append(user_id)
    cur.execute(
        f"UPDATE users SET {', '.join(user_sets)} WHERE id = ?",
        tuple(user_params),
    )

    cur.execute(
        """
        SELECT firm_id FROM firm_users
        WHERE user_id = ? AND status = 'active'
        ORDER BY id ASC
        LIMIT 1
        """,
        (user_id,),
    )
    membership = cur.fetchone()
    if membership:
        firm_id = int(membership["firm_id"])
        firm_columns = {
            str(row["name"])
            for row in cur.execute("PRAGMA table_info(firms)").fetchall()
        }
        firm_sets: list[str] = ["name = ?"]
        firm_params: list[object] = [firm_name]
        if "plan" in firm_columns:
            firm_sets.append("plan = ?")
            firm_params.append(firm_plan)
        firm_params.append(firm_id)
        cur.execute(
            f"UPDATE firms SET {', '.join(firm_sets)} WHERE id = ?",
            tuple(firm_params),
        )
        cur.execute(
            """
            UPDATE firm_users
            SET role = 'owner', status = 'active', joined_at = COALESCE(joined_at, ?)
            WHERE firm_id = ? AND user_id = ?
            """,
            (now_iso, firm_id, user_id),
        )
    else:
        cur.execute(
            """
            INSERT INTO firms (name, created_at, created_by_user_id)
            VALUES (?, ?, ?)
            """,
            (firm_name, now_iso, user_id),
        )
        firm_id = int(cur.lastrowid)
        cur.execute(
            "UPDATE firms SET plan = ? WHERE id = ?",
            (firm_plan, firm_id),
        )
        cur.execute(
            """
            INSERT INTO firm_users (
                firm_id, user_id, role, status, invited_by_user_id, invited_at, joined_at
            )
            VALUES (?, ?, 'owner', 'active', ?, ?, ?)
            """,
            (firm_id, user_id, user_id, now_iso, now_iso),
        )

    conn.commit()
    conn.close()
    print(
        f"[e2e-bootstrap] ensured user={email} firm_id={firm_id} "
        f"plan={firm_plan} subscription_type={subscription_type} db={db_path}"
    )


if __name__ == "__main__":
    main()
