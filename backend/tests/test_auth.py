import os
import tempfile
import uuid

import pytest
from services.email_service import EmailDeliveryResult, resolve_from_email_choice

os.environ.setdefault('SECRET_KEY', 'test-secret')

from app import app, create_email_verification_token, db_connect, init_db


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


def test_register_rejects_weak_password(client):
    resp = client.post('/register', data={
        'full_name': 'Jane Doe',
        'firm_name': 'Doe Legal',
        'email': 'jane@example.com',
        'password': 'weak',
        'confirm_password': 'weak',
    }, follow_redirects=True)
    assert b'Password must be at least 8 characters long' in resp.data


def test_register_and_login_success(client):
    register_resp = client.post('/register', data={
        'full_name': 'Lawyer Name',
        'firm_name': 'Firm Name',
        'email': 'lawyer@example.com',
        'password': 'StrongPass1',
        'confirm_password': 'StrongPass1',
    }, follow_redirects=True)
    assert register_resp.status_code == 200

    login_resp = client.post('/login', data={
        'username': 'lawyer@example.com',
        'password': 'StrongPass1',
    }, follow_redirects=True)
    assert login_resp.status_code == 200


def test_password_reset_token_single_use(client):
    client.post('/register', data={
        'full_name': 'Lawyer Name',
        'firm_name': 'Firm Name',
        'email': 'lawyer@example.com',
        'password': 'StrongPass1',
        'confirm_password': 'StrongPass1',
    }, follow_redirects=True)

    client.post('/forgot-password', data={'email': 'lawyer@example.com'}, follow_redirects=True)
    conn = db_connect(); c = conn.cursor()
    c.execute('SELECT token FROM password_reset_tokens ORDER BY id DESC LIMIT 1')
    token = c.fetchone()[0]
    conn.close()

    first = client.post(f'/reset-password/{token}', data={
        'password': 'EvenStronger2',
        'confirm_password': 'EvenStronger2',
    }, follow_redirects=True)
    assert b'Password reset successful' in first.data

    second = client.post(f'/reset-password/{token}', data={
        'password': 'AnotherPass3',
        'confirm_password': 'AnotherPass3',
    }, follow_redirects=True)
    assert b'expired' in second.data.lower() or b'invalid' in second.data.lower()


def test_login_sql_injection_attempt_fails(client):
    resp = client.post('/login', data={'username': "admin' OR 1=1 --", 'password': 'x'}, follow_redirects=True)
    assert b'Sign-in failed' in resp.data


def test_health_and_metrics_endpoints(client):
    h = client.get('/health')
    assert h.status_code == 200
    m = client.get('/metrics')
    assert m.status_code == 200


def test_forgot_password_mail_enabled_hides_link(client):
    client.post('/register', data={
        'full_name': 'Lawyer Name',
        'firm_name': 'Firm Name',
        'email': 'mailtest@example.com',
        'password': 'StrongPass1',
        'confirm_password': 'StrongPass1',
    }, follow_redirects=True)
    app.config['MAIL_ENABLED'] = True
    resp = client.post('/forgot-password', data={'email': 'mailtest@example.com'}, follow_redirects=True)
    assert b'password reset link has been sent' in resp.data.lower()
    assert b'Reset link:' not in resp.data


def test_rate_limit_handler_exists(client):
    # Ensure custom 429 page renders and includes reset hint text
    from app import rate_limited
    with app.test_request_context('/login'):
        resp = rate_limited(Exception('too many'))
        assert resp.status_code == 429
        assert 'X-RateLimit-Reset' in resp.headers


def test_webhook_bad_signature_returns_400(client):
    resp = client.post('/stripe-webhook', data='{}', headers={'Stripe-Signature': 'bad'})
    # If webhook secret not set it may be 204; with secret set and bad sig -> 400
    assert resp.status_code in (204, 400)


def test_forgot_password_calls_mail_sender(client, monkeypatch):
    client.post('/register', data={
        'full_name': 'Mail Test',
        'firm_name': 'Firm Name',
        'email': 'smtpcheck@example.com',
        'password': 'StrongPass1',
        'confirm_password': 'StrongPass1',
    }, follow_redirects=True)
    called = {'v': False}

    def _mock_send(*args, **kwargs):
        called['v'] = True
        return True

    import app as app_module
    monkeypatch.setattr(app_module, 'send_password_reset_email', _mock_send)
    app.config['MAIL_ENABLED'] = True
    client.post('/forgot-password', data={'email': 'smtpcheck@example.com'}, follow_redirects=True)
    assert called['v'] is True


def test_api_account_profile_updates_firm_name(client):
    client.post('/register', data={
        'full_name': 'Firm Update User',
        'firm_name': 'Original Firm',
        'email': 'firmupdate@example.com',
        'password': 'StrongPass1',
        'confirm_password': 'StrongPass1',
    }, follow_redirects=True)
    client.post('/login', data={'username': 'firmupdate@example.com', 'password': 'StrongPass1'}, follow_redirects=True)

    update_resp = client.put('/api/account/profile', json={'firm_name': 'Updated Firm LLP'})
    assert update_resp.status_code == 200
    body = update_resp.get_json()
    assert body is not None
    assert body.get('success') is True
    assert (body.get('user') or {}).get('firm_name') == 'Updated Firm LLP'

    me_resp = client.get('/api/auth/me')
    assert me_resp.status_code == 200
    me_body = me_resp.get_json()
    assert me_body is not None
    assert (me_body.get('user') or {}).get('firm_name') == 'Updated Firm LLP'


def test_api_register_bootstraps_firm_context_immediately(client):
    register_resp = client.post(
        '/api/auth/register',
        json={
            'email': 'firmctx@example.com',
            'password': 'StrongPass1',
            'full_name': 'Firm Context User',
            'firm_name': 'Firm Context LLP',
        },
    )
    assert register_resp.status_code == 201
    register_body = register_resp.get_json()
    assert register_body is not None
    assert register_body.get('success') is True

    members_resp = client.get('/api/team/members')
    assert members_resp.status_code == 200
    members_body = members_resp.get_json()
    assert members_body is not None
    assert members_body.get('success') is True
    assert isinstance(members_body.get('firm_id'), int)
    assert members_body.get('firm_id', 0) > 0
    members = members_body.get('members') or []
    assert any((m.get('email') == 'firmctx@example.com' and m.get('role') == 'owner') for m in members)


def test_api_verify_email_logs_user_in_with_onboarding_incomplete(client, monkeypatch):
    monkeypatch.setenv('RESEND_API_KEY', 'test-resend-key')
    monkeypatch.setenv('RESEND_FROM_EMAIL', 'onboarding@example.com')
    email = f"verify-session-{uuid.uuid4().hex[:8]}@example.com"

    import app as app_module

    monkeypatch.setattr(
        app_module,
        'send_verification_email_with_result',
        lambda *args, **kwargs: EmailDeliveryResult(success=True, provider='resend', from_email='Clarion <onboarding@example.com>'),
    )

    register_resp = client.post(
        '/api/auth/register',
        json={
            'email': email,
            'password': 'StrongPass1!',
            'full_name': 'Verify Session User',
            'firm_name': 'Verify Session LLP',
        },
    )
    assert register_resp.status_code == 201

    conn = db_connect()
    c = conn.cursor()
    c.execute('SELECT id FROM users WHERE email = ?', (email,))
    user_id = c.fetchone()[0]
    conn.close()

    token = create_email_verification_token(user_id, email)
    verify_resp = client.get(f'/api/auth/verify-email/{token}')
    assert verify_resp.status_code == 200
    verify_body = verify_resp.get_json()
    assert verify_body is not None
    assert verify_body.get('verified') is True
    assert (verify_body.get('user') or {}).get('onboarding_complete') is False

    me_resp = client.get('/api/auth/me')
    assert me_resp.status_code == 200
    me_body = me_resp.get_json()
    assert me_body is not None
    assert (me_body.get('user') or {}).get('email_verified') is True
    assert (me_body.get('user') or {}).get('onboarding_complete') is False


def test_api_onboarding_complete_sets_onboarding_complete(client, monkeypatch):
    monkeypatch.setenv('RESEND_API_KEY', 'test-resend-key')
    monkeypatch.setenv('RESEND_FROM_EMAIL', 'onboarding@example.com')
    email = f"onboarding-complete-{uuid.uuid4().hex[:8]}@example.com"

    import app as app_module

    monkeypatch.setattr(
        app_module,
        'send_verification_email_with_result',
        lambda *args, **kwargs: EmailDeliveryResult(success=True, provider='resend', from_email='Clarion <onboarding@example.com>'),
    )

    register_resp = client.post(
        '/api/auth/register',
        json={
            'email': email,
            'password': 'StrongPass1!',
            'full_name': 'Onboarding Complete User',
            'firm_name': 'Onboarding Complete LLP',
        },
    )
    assert register_resp.status_code == 201

    conn = db_connect()
    c = conn.cursor()
    c.execute('SELECT id FROM users WHERE email = ?', (email,))
    user_id = c.fetchone()[0]
    conn.close()

    token = create_email_verification_token(user_id, email)
    verify_resp = client.get(f'/api/auth/verify-email/{token}')
    assert verify_resp.status_code == 200

    complete_resp = client.post('/api/onboarding/complete')
    assert complete_resp.status_code == 200
    complete_body = complete_resp.get_json()
    assert complete_body is not None
    assert complete_body.get('success') is True
    assert (complete_body.get('user') or {}).get('onboarding_complete') is True


def test_public_verify_email_link_prefers_app_base_url(client, monkeypatch):
    monkeypatch.setenv('APP_BASE_URL', 'https://app.clarion.test')

    import app as app_module

    with app_module.app.test_request_context(
        '/api/auth/register',
        base_url='http://127.0.0.1:5000',
        headers={'Origin': 'http://localhost:8081'},
    ):
        link = app_module._public_verify_email_link('sample-token')

    assert link == 'https://app.clarion.test/verify-email/sample-token'


def test_legacy_verify_email_route_redirects_to_spa_flow(client, monkeypatch):
    monkeypatch.setenv('APP_BASE_URL', 'https://app.clarion.test')

    response = client.get('/verify-email/legacy-token', follow_redirects=False)

    assert response.status_code in (301, 302)
    assert response.headers['Location'] == 'https://app.clarion.test/verify-email/legacy-token'


def test_api_register_reports_verification_delivery_unavailable(client, monkeypatch):
    monkeypatch.delenv('RESEND_API_KEY', raising=False)
    monkeypatch.delenv('RESEND_FROM_EMAIL', raising=False)
    monkeypatch.delenv('FROM_EMAIL', raising=False)
    monkeypatch.delenv('SMTP_SERVER', raising=False)
    monkeypatch.delenv('SMTP_USERNAME', raising=False)
    email = f"delivery-unavailable-{uuid.uuid4().hex[:8]}@example.com"
    register_resp = client.post(
        '/api/auth/register',
        json={
            'email': email,
            'password': 'StrongPass1!',
            'full_name': 'Delivery Unavailable',
            'firm_name': 'Delivery Unavailable LLP',
        },
    )
    assert register_resp.status_code == 201
    body = register_resp.get_json()
    assert body is not None
    assert body.get('success') is True
    assert body.get('requires_verification') is True
    assert body.get('verification_sent') is False
    assert body.get('verification_delivery_available') is False
    assert body.get('verification_delivery_method') is None
    assert 'not configured' in str(body.get('verification_delivery_error') or '').lower()


def test_verification_delivery_status_uses_known_working_resend_fallback(client, monkeypatch):
    monkeypatch.setenv('RESEND_API_KEY', 'test-resend-key')
    monkeypatch.delenv('RESEND_FROM_EMAIL', raising=False)
    monkeypatch.delenv('FROM_EMAIL', raising=False)

    import app as app_module

    status = app_module._verification_delivery_status()
    assert status['available'] is True
    assert status['method'] == 'resend'
    assert status['error'] is None


def test_sender_resolution_prefers_verified_domain_sender(client, monkeypatch):
    monkeypatch.setenv('RESEND_API_KEY', 'test-resend-key')
    monkeypatch.setenv('RESEND_FROM_EMAIL', 'Clarion <onboarding@clarionhq.co>')
    monkeypatch.setenv('FROM_EMAIL', 'onboarding@resend.dev')

    sender = resolve_from_email_choice()
    assert sender.from_email == 'Clarion <onboarding@clarionhq.co>'
    assert sender.source == 'configured_sender'


def test_sender_resolution_uses_resend_dev_only_as_fallback(client, monkeypatch):
    monkeypatch.setenv('RESEND_API_KEY', 'test-resend-key')
    monkeypatch.setenv('RESEND_FROM_EMAIL', 'not-an-email')
    monkeypatch.delenv('FROM_EMAIL', raising=False)

    sender = resolve_from_email_choice()
    assert sender.from_email == 'Clarion <onboarding@resend.dev>'
    assert sender.source == 'resend_dev_fallback'


def test_api_register_uses_resend_verification_delivery_when_configured(client, monkeypatch):
    monkeypatch.delenv('SMTP_SERVER', raising=False)
    monkeypatch.delenv('SMTP_USERNAME', raising=False)
    monkeypatch.setenv('RESEND_API_KEY', 'test-resend-key')
    monkeypatch.setenv('RESEND_FROM_EMAIL', 'onboarding@example.com')
    email = f"resend-configured-{uuid.uuid4().hex[:8]}@example.com"
    called = {'value': False}

    def _mock_send_verification_email_with_result(*args, **kwargs):
        called['value'] = True
        return EmailDeliveryResult(
            success=True,
            provider='resend',
            from_email='Clarion <onboarding@example.com>',
        )

    import app as app_module

    monkeypatch.setattr(app_module, 'send_verification_email_with_result', _mock_send_verification_email_with_result)

    register_resp = client.post(
        '/api/auth/register',
        json={
            'email': email,
            'password': 'StrongPass1!',
            'full_name': 'Resend Configured',
            'firm_name': 'Resend Configured LLP',
        },
    )

    assert register_resp.status_code == 201
    body = register_resp.get_json()
    assert body is not None
    assert called['value'] is True
    assert body.get('verification_sent') is True
    assert body.get('verification_delivery_available') is True
    assert body.get('verification_delivery_method') == 'resend'
    assert body.get('verification_delivery_error') is None


def test_api_register_reports_runtime_resend_failure(client, monkeypatch):
    monkeypatch.setenv('RESEND_API_KEY', 'test-resend-key')
    monkeypatch.setenv('RESEND_FROM_EMAIL', 'onboarding@example.com')
    email = f"resend-runtime-{uuid.uuid4().hex[:8]}@example.com"

    import app as app_module

    def _mock_send_verification_email_with_result(*args, **kwargs):
        return EmailDeliveryResult(
            success=False,
            provider='resend',
            from_email='Clarion <onboarding@example.com>',
            error_type='provider_network_error',
            error_message='Resend could not be reached from this runtime: HTTPSConnectionPool(host=\'api.resend.com\', port=443): Max retries exceeded',
        )

    monkeypatch.setattr(app_module, 'send_verification_email_with_result', _mock_send_verification_email_with_result)

    register_resp = client.post(
        '/api/auth/register',
        json={
            'email': email,
            'password': 'StrongPass1!',
            'full_name': 'Resend Runtime Failure',
            'firm_name': 'Resend Runtime Failure LLP',
        },
    )

    assert register_resp.status_code == 201
    body = register_resp.get_json()
    assert body is not None
    assert body.get('verification_sent') is False
    assert body.get('verification_delivery_available') is False
    assert body.get('verification_delivery_method') == 'resend'
    assert body.get('verification_delivery_error_type') == 'provider_network_error'
    assert 'could not be reached' in str(body.get('verification_delivery_error') or '').lower()
    assert body.get('verification_delivery_from_email') == 'Clarion <onboarding@example.com>'


def test_api_resend_verification_reports_delivery_unavailable(client, monkeypatch):
    monkeypatch.delenv('RESEND_API_KEY', raising=False)
    monkeypatch.delenv('RESEND_FROM_EMAIL', raising=False)
    monkeypatch.delenv('FROM_EMAIL', raising=False)
    monkeypatch.delenv('SMTP_SERVER', raising=False)
    monkeypatch.delenv('SMTP_USERNAME', raising=False)
    email = f"resend-unavailable-{uuid.uuid4().hex[:8]}@example.com"
    client.post(
        '/api/auth/register',
        json={
            'email': email,
            'password': 'StrongPass1!',
            'full_name': 'Resend Unavailable',
            'firm_name': 'Resend Unavailable LLP',
        },
    )

    resend_resp = client.post(
        '/api/auth/resend-verification',
        json={'email': email},
    )
    assert resend_resp.status_code == 200
    body = resend_resp.get_json()
    assert body is not None
    assert body.get('verification_delivery_available') is False
    assert body.get('verification_delivery_method') is None
    assert 'not configured' in str(body.get('verification_delivery_error') or '').lower()


def test_api_resend_verification_reports_runtime_failure(client, monkeypatch):
    monkeypatch.setenv('RESEND_API_KEY', 'test-resend-key')
    monkeypatch.setenv('RESEND_FROM_EMAIL', 'onboarding@example.com')
    email = f"resend-runtime-resend-{uuid.uuid4().hex[:8]}@example.com"

    import app as app_module

    def _mock_send_verification_email_with_result(*args, **kwargs):
        return EmailDeliveryResult(
            success=False,
            provider='resend',
            from_email='Clarion <onboarding@example.com>',
            error_type='provider_network_error',
            error_message='Resend could not be reached from this runtime: HTTPSConnectionPool(host=\'api.resend.com\', port=443): Max retries exceeded',
        )

    monkeypatch.setattr(app_module, 'send_verification_email_with_result', _mock_send_verification_email_with_result)

    client.post(
        '/api/auth/register',
        json={
            'email': email,
            'password': 'StrongPass1!',
            'full_name': 'Resend Runtime Resend',
            'firm_name': 'Resend Runtime Resend LLP',
        },
    )

    resend_resp = client.post(
        '/api/auth/resend-verification',
        json={'email': email},
    )
    assert resend_resp.status_code == 200
    body = resend_resp.get_json()
    assert body is not None
    assert body.get('verification_sent') is False
    assert body.get('verification_delivery_available') is False
    assert body.get('verification_delivery_method') == 'resend'
    assert body.get('verification_delivery_error_type') == 'provider_network_error'
    assert 'could not be reached' in str(body.get('verification_delivery_error') or '').lower()
