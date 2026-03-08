import os
import sqlite3
from datetime import datetime, timezone

from werkzeug.security import generate_password_hash

from app import app, init_db, db_connect


def _create_user(email, password, firm_name):
    conn = db_connect()
    c = conn.cursor()
    now_iso = datetime.now(timezone.utc).isoformat()
    c.execute(
        '''
        INSERT INTO users (email, username, password_hash, is_verified, created_at, firm_name, is_admin, subscription_type, subscription_status)
        VALUES (?, ?, ?, 1, ?, ?, 0, 'trial', 'trial')
        ''',
        (email, email, generate_password_hash(password), now_iso, firm_name),
    )
    user_id = int(c.lastrowid)
    conn.commit()
    conn.close()
    return user_id


def _login(client, email, password):
    resp = client.post('/api/auth/login', json={'email': email, 'password': password})
    if resp.status_code != 200:
        raise RuntimeError(f'Login failed for {email}: {resp.status_code} {resp.get_data(as_text=True)}')


def run():
    db_path = os.path.join(os.path.dirname(__file__), 'smoke_option_b.db')
    if os.path.exists(db_path):
        os.remove(db_path)
    app.config['DATABASE_PATH'] = db_path
    app.config['TESTING'] = True
    init_db()

    owner_email = 'owner@example.com'
    partner_email = 'partner@example.com'
    member_email = 'member@example.com'
    pwd = 'StrongPass1'
    firm_name = 'Smoke LLP'

    owner_id = _create_user(owner_email, pwd, firm_name)
    partner_id = _create_user(partner_email, pwd, firm_name)
    member_id = _create_user(member_email, pwd, firm_name)

    conn = db_connect()
    c = conn.cursor()
    now_iso = datetime.now(timezone.utc).isoformat()
    c.execute('INSERT INTO firms (name, created_at, created_by_user_id) VALUES (?, ?, ?)', (firm_name, now_iso, owner_id))
    firm_id = int(c.lastrowid)
    c.execute(
        "INSERT INTO firm_users (firm_id, user_id, role, status, invited_by_user_id, invited_at, joined_at) VALUES (?, ?, 'owner', 'active', ?, ?, ?)",
        (firm_id, owner_id, owner_id, now_iso, now_iso),
    )
    c.execute(
        "INSERT INTO firm_users (firm_id, user_id, role, status, invited_by_user_id, invited_at, joined_at) VALUES (?, ?, 'partner', 'active', ?, ?, ?)",
        (firm_id, partner_id, owner_id, now_iso, now_iso),
    )
    c.execute(
        "INSERT INTO firm_users (firm_id, user_id, role, status, invited_by_user_id, invited_at, joined_at) VALUES (?, ?, 'member', 'active', ?, ?, ?)",
        (firm_id, member_id, owner_id, now_iso, now_iso),
    )

    c.execute(
        '''
        INSERT INTO reports (user_id, firm_id, created_by_user_id, total_reviews, avg_rating, themes, top_praise, top_complaints, subscription_type_at_creation)
        VALUES (?, ?, ?, 20, 4.2, '{}', '[]', '[]', 'trial')
        ''',
        (owner_id, firm_id, owner_id),
    )
    c.execute(
        '''
        UPDATE users
        SET subscription_status = 'active', subscription_type = 'monthly'
        WHERE id IN (?, ?)
        ''',
        (owner_id, partner_id),
    )
    report_id = int(c.lastrowid)
    c.execute(
        '''
        INSERT INTO report_action_items (user_id, firm_id, report_id, title, owner, owner_user_id, status, created_by_user_id, updated_by_user_id)
        VALUES (?, ?, ?, ?, ?, ?, 'open', ?, ?)
        ''',
        (owner_id, firm_id, report_id, 'Partner-owned task', partner_email, partner_id, owner_id, owner_id),
    )
    partner_action_id = int(c.lastrowid)
    c.execute(
        '''
        INSERT INTO report_action_items (user_id, firm_id, report_id, title, owner, owner_user_id, status, created_by_user_id, updated_by_user_id)
        VALUES (?, ?, ?, ?, ?, ?, 'open', ?, ?)
        ''',
        (owner_id, firm_id, report_id, 'Member-owned task', member_email, member_id, owner_id, owner_id),
    )
    member_action_id = int(c.lastrowid)
    conn.commit()
    conn.close()

    owner_client = app.test_client()
    partner_client = app.test_client()
    member_client = app.test_client()

    _login(owner_client, owner_email, pwd)
    _login(partner_client, partner_email, pwd)
    _login(member_client, member_email, pwd)

    owner_reports = owner_client.get('/api/reports').get_json() or {}
    partner_reports = partner_client.get('/api/reports').get_json() or {}
    owner_ids = {int(r['id']) for r in owner_reports.get('reports', [])}
    partner_ids = {int(r['id']) for r in partner_reports.get('reports', [])}
    assert report_id in owner_ids and report_id in partner_ids, 'Firm-scoped report visibility failed.'

    delete_partner = partner_client.delete(f'/api/reports/{report_id}')
    assert delete_partner.status_code == 403, f'Partner delete expected 403, got {delete_partner.status_code}'

    export_partner = partner_client.get(f'/api/reports/{report_id}/pdf?refresh=1&export=1')
    assert export_partner.status_code == 200, f'Partner export expected 200, got {export_partner.status_code}'

    export_member = member_client.get(f'/api/reports/{report_id}/pdf?refresh=1&export=1')
    assert export_member.status_code == 403, f'Member export expected 403, got {export_member.status_code}'

    own_update = member_client.patch(
        f'/api/reports/{report_id}/actions/{member_action_id}',
        json={'status': 'in_progress'},
    )
    assert own_update.status_code == 200, f'Member own update expected 200, got {own_update.status_code}'
    other_update = member_client.patch(
        f'/api/reports/{report_id}/actions/{partner_action_id}',
        json={'status': 'in_progress'},
    )
    assert other_update.status_code == 403, f'Member other update expected 403, got {other_update.status_code}'

    assigned = partner_client.post(
        f'/api/reports/{report_id}/actions',
        json={'title': 'Assigned by partner', 'owner_user_id': member_id},
    )
    assert assigned.status_code == 201, f'Partner assign expected 201, got {assigned.status_code}'
    assigned_body = assigned.get_json() or {}
    assert (assigned_body.get('action') or {}).get('owner_user_id') == member_id, 'owner_user_id not persisted.'

    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute('SELECT COUNT(*) FROM governance_briefs WHERE firm_id = ?', (firm_id,))
    assert c.fetchone()[0] >= 1, 'Expected governance_briefs row missing.'
    c.execute("SELECT COUNT(*) FROM audit_log WHERE firm_id = ? AND event_type = 'GOVERNANCE_BRIEF_EXPORTED'", (firm_id,))
    assert c.fetchone()[0] >= 1, 'Expected audit export event missing.'
    conn.close()
    print('Option B smoke check passed.')


if __name__ == '__main__':
    run()
