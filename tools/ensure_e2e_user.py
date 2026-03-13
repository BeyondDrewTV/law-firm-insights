import os
import sqlite3
from datetime import datetime, timezone

from werkzeug.security import generate_password_hash


def _db_path() -> str:
    env_path = (os.environ.get("DATABASE_PATH") or "").strip()
    if env_path:
        return os.path.abspath(env_path)
    return os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend", "feedback.db"))


def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def main() -> None:
    email = os.environ.get("E2E_SMOKE_EMAIL", "smoke.e2e@lawfirminsights.local").strip().lower()
    password = os.environ.get("E2E_SMOKE_PASSWORD", "SmokeTest123")
    full_name = os.environ.get("E2E_SMOKE_NAME", "Smoke Tester")
    firm_name = os.environ.get("E2E_SMOKE_FIRM", "Smoke LLP")
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
        cur.execute("UPDATE firms SET name = ? WHERE id = ?", (firm_name, firm_id))
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
    print(f"[e2e-bootstrap] ensured user={email} firm_id={firm_id} db={db_path}")


if __name__ == "__main__":
    main()
