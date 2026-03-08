import os
import tempfile
from io import BytesIO

import pytest

os.environ.setdefault('SECRET_KEY', 'test-secret')

from app import app, db_connect, init_db


@pytest.fixture
def client():
    db_fd, db_path = tempfile.mkstemp()
    app.config.update(
        DATABASE_PATH=db_path,
        TESTING=True,
        WTF_CSRF_ENABLED=False,
        MAIL_ENABLED=False,
    )
    with app.app_context():
        init_db()
    with app.test_client() as c:
        yield c
    os.close(db_fd)
    os.unlink(db_path)


def login_admin(client):
    return client.post('/login', data={'username': 'admin', 'password': 'change-this-admin-password'}, follow_redirects=True)


def test_upload_requires_login(client):
    resp = client.get('/upload')
    assert resp.status_code == 302


def test_upload_blocked_until_verified(client):
    client.post('/register', data={
        'full_name': 'Lawyer Name',
        'firm_name': 'Firm Name',
        'email': 'lawyer@example.com',
        'password': 'StrongPass1',
        'confirm_password': 'StrongPass1',
    }, follow_redirects=True)
    client.post('/login', data={'username': 'lawyer@example.com', 'password': 'StrongPass1'}, follow_redirects=True)

    payload = b"date,rating,review_text\n2024-01-01,5,Great"
    resp = client.post('/upload', data={'file': (BytesIO(payload), 'reviews.csv')}, content_type='multipart/form-data', follow_redirects=True)
    assert b'Please verify your email before uploading data' in resp.data


def test_upload_success_after_verification(client):
    login_admin(client)
    conn = db_connect()
    c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO user_email_verification (user_id, verified_at) VALUES (1, '2024-01-01T00:00:00+00:00')")
    conn.commit(); conn.close()

    payload = b"date,rating,review_text\n2024-01-01,5,Great service"
    resp = client.post('/upload', data={'file': (BytesIO(payload), 'reviews.csv')}, content_type='multipart/form-data', follow_redirects=True)
    assert resp.status_code == 200


def test_api_upload_rejects_onetime_over_500_reviews(client):
    client.post('/register', data={
        'full_name': 'One Time User',
        'firm_name': 'One Time Firm',
        'email': 'onetime@example.com',
        'password': 'StrongPass1',
        'confirm_password': 'StrongPass1',
    }, follow_redirects=True)
    client.post('/login', data={'username': 'onetime@example.com', 'password': 'StrongPass1'}, follow_redirects=True)

    conn = db_connect()
    c = conn.cursor()
    c.execute("SELECT id FROM users WHERE email = ?", ('onetime@example.com',))
    row = c.fetchone()
    assert row is not None
    user_id = int(row[0])
    c.execute(
        """
        UPDATE users
        SET subscription_status = 'inactive',
            subscription_type = 'trial',
            one_time_reports_purchased = 1,
            one_time_reports_used = 0
        WHERE id = ?
        """
        ,
        (user_id,),
    )
    conn.commit()
    conn.close()

    rows = ["date,rating,review_text"]
    rows.extend([f"2026-02-{(idx % 28) + 1:02d},5,Sample review {idx}" for idx in range(1, 502)])
    payload = ("\n".join(rows)).encode("utf-8")

    resp = client.post(
        '/api/upload',
        data={'file': (BytesIO(payload), 'reviews.csv')},
        content_type='multipart/form-data',
    )

    assert resp.status_code == 400
    body = resp.get_json()
    assert body is not None
    assert body.get('success') is False
    assert 'up to 500 reviews per report' in (body.get('error') or '').lower()
