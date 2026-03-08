"""
Clarion 1.0 Release Smoke Suite
Minimal trustworthy gate covering the critical launch paths.
Run: pytest -q backend/tests/test_release_smoke.py
"""
import os
import tempfile
import uuid

import pytest

os.environ.setdefault("SECRET_KEY", "test-secret")

from app import app, create_email_verification_token, db_connect, init_db
import app as _app_module
from db_compat import DatabaseConnector


@pytest.fixture
def client():
    db_fd, db_path = tempfile.mkstemp(suffix=".db")
    sqlite_url = f"sqlite:///{db_path}"

    # Override the module-level connector so db_connect() uses the temp DB.
    original_connector = _app_module._db_connector
    temp_connector = DatabaseConnector(sqlite_url)
    _app_module._db_connector = temp_connector

    app.config.update(
        DATABASE_URL=sqlite_url,
        TESTING=True,
        WTF_CSRF_ENABLED=False,
        MAIL_ENABLED=False,
    )
    with app.app_context():
        init_db()
    with app.test_client() as c:
        yield c

    _app_module._db_connector = original_connector
    os.close(db_fd)
    os.unlink(db_path)


# -------------------------------------------------------------------------
# Helpers
# -------------------------------------------------------------------------

def _register(client, email="smoke@example.com", password="SmokePass1!"):
    return client.post(
        "/register",
        data={
            "full_name": "Smoke User",
            "firm_name": "Smoke Firm",
            "email": email,
            "password": password,
            "confirm_password": password,
        },
        follow_redirects=False,
    )  # SPA handoff: successful POST redirects toward SPA; stop here


def _get_verification_token(email="smoke@example.com"):
    """Generate a valid verification token by creating it the same way the app does."""
    conn = db_connect()
    c = conn.cursor()
    c.execute("SELECT id FROM users WHERE email=?", (email,))
    row = c.fetchone()
    conn.close()
    if not row:
        return None
    user_id = row[0]
    with app.app_context():
        return create_email_verification_token(user_id, email)


def _verify_email(client, email="smoke@example.com"):
    token = _get_verification_token(email)
    assert token, "No verification token found for %s" % email
    return client.get("/api/auth/verify-email/%s" % token, follow_redirects=False)


def _login_api(client, email="smoke@example.com", password="SmokePass1!"):
    return client.post(
        "/api/auth/login",
        json={"email": email, "password": password},
    )


# -------------------------------------------------------------------------
# A. Signup + verification lifecycle
# -------------------------------------------------------------------------

def test_signup_creates_unverified_user(client):
    resp = _register(client)
    assert resp.status_code in (200, 302), f"Expected 200 or 302, got {resp.status_code}"
    conn = db_connect()
    c = conn.cursor()
    c.execute("SELECT email_verified FROM users WHERE email='smoke@example.com'")
    row = c.fetchone()
    conn.close()
    assert row is not None
    assert row[0] in (0, False, None), "User should not be verified on signup"


def test_verify_email_sets_verified(client):
    _register(client)
    token = _get_verification_token()
    assert token
    resp = client.get("/api/auth/verify-email/%s" % token, follow_redirects=False)
    assert resp.status_code in (200, 302)
    conn = db_connect()
    c = conn.cursor()
    c.execute("SELECT email_verified FROM users WHERE email='smoke@example.com'")
    row = c.fetchone()
    conn.close()
    assert row[0] in (1, True)


def test_verification_link_uses_spa_base_url(client):
    """Outbound email links must use _resolve_public_app_base_url, not request.host_url."""
    from app import _resolve_public_app_base_url
    with app.app_context():
        base = _resolve_public_app_base_url()
    assert isinstance(base, str)
    assert base.startswith("http")
    # Must not be a bare Flask host
    assert "localhost:5000" not in base or os.getenv("PUBLIC_APP_BASE_URL")


# -------------------------------------------------------------------------
# B. Post-verify onboarding redirect
# -------------------------------------------------------------------------

def test_post_verify_login_returns_onboarding_incomplete(client):
    _register(client)
    _verify_email(client)
    resp = _login_api(client)
    data = resp.get_json()
    assert data.get("success") is True
    user = data.get("user") or {}
    # Freshly verified users should not have onboarding complete
    assert not user.get("onboarding_complete")


# -------------------------------------------------------------------------
# C. Password reset lifecycle
# -------------------------------------------------------------------------

def test_forgot_password_never_reveals_existence(client):
    resp = client.post(
        "/api/auth/forgot-password",
        json={"email": "nonexistent@example.com"},
    )
    assert resp.status_code == 200
    data = resp.get_json()
    assert data.get("success") is True


def test_password_reset_full_cycle(client):
    email = "resetme@example.com"
    password = "OldPass1!"
    new_password = "NewPass2!"
    _register(client, email=email, password=password)
    _verify_email(client, email=email)

    # Request reset
    resp = client.post("/api/auth/forgot-password", json={"email": email})
    assert resp.get_json().get("success") is True

    # Get token from DB
    conn = db_connect()
    c = conn.cursor()
    c.execute("SELECT token FROM password_reset_tokens WHERE user_id=(SELECT id FROM users WHERE email=?) ORDER BY id DESC LIMIT 1", (email,))
    row = c.fetchone()
    conn.close()
    assert row, "No reset token created"
    token = row[0]

    # Validate token
    resp = client.get("/api/auth/reset-password/%s" % token)
    assert resp.status_code == 200
    assert resp.get_json().get("valid") is True

    # Submit new password
    resp = client.post(
        "/api/auth/reset-password/%s" % token,
        json={"password": new_password, "confirm_password": new_password},
    )
    assert resp.status_code == 200
    assert resp.get_json().get("success") is True

    # Token should now be used (single-use)
    resp = client.get("/api/auth/reset-password/%s" % token)
    result = resp.get_json()
    assert result.get("valid") is False
    assert result.get("reason") == "used"

    # Can log in with new password
    resp = _login_api(client, email=email, password=new_password)
    assert resp.get_json().get("success") is True


# -------------------------------------------------------------------------
# D. Protected mutation requires auth
# -------------------------------------------------------------------------

def test_upload_requires_auth(client):
    resp = client.post("/api/upload", data={})
    assert resp.status_code in (401, 403)


# -------------------------------------------------------------------------
# E. Anonymous support ticket creation
# -------------------------------------------------------------------------

def test_anonymous_support_ticket_create(client):
    resp = client.post(
        "/api/support/tickets",
        json={
            "name": "Test User",
            "email": "anon@example.com",
            "category": "other",
            "urgency": "normal",
            "subject": "Smoke test ticket",
            "message": "This is a smoke test for the anonymous support ticket path.",
            "source": "contact",
        },
    )
    assert resp.status_code in (200, 201)
    data = resp.get_json()
    assert data.get("success") is True


# -------------------------------------------------------------------------
# F. Invite endpoint returns unavailable (not 2xx success)
# -------------------------------------------------------------------------

def test_invite_endpoint_disabled(client):
    _register(client)
    _verify_email(client)
    # Login to get session
    with client.session_transaction() as sess:
        pass
    _login_api(client)
    # Try to invite
    resp = client.post(
        "/api/team/invite",
        json={"email": "newmember@example.com", "role": "member"},
    )
    data = resp.get_json()
    # Must not return success
    assert data.get("success") is not True
