"""

Clarion - Flask Application
Main application with routes for client feedback, admin CSV upload, analysis, and PDF generation

"""



import os
import csv
import json
import re
import secrets
import uuid
import hashlib
import time as time_module
import smtplib
import socket
from urllib.parse import urlparse
from io import StringIO, BytesIO
from datetime import datetime, timedelta, timezone
from collections import Counter
from time import perf_counter
from typing import Optional
import zoneinfo
import logging
from logging.handlers import RotatingFileHandler
from email.message import EmailMessage
import os
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), ".env"), override=False)

# -- Startup interpreter + env diagnostic ------------------------------------
# Printed to stderr on every process start. Detects wrong-interpreter startup
# (e.g. C:\Python314\python.exe instead of venv312\Scripts\python.exe) which
# causes python-dotenv and resend to be missing and email delivery to silently
# report provider_not_configured.
import sys as _sys
_resend_key = (os.getenv("RESEND_API_KEY") or "").strip()
_from_email = (os.getenv("RESEND_FROM_EMAIL") or os.getenv("FROM_EMAIL") or "").strip()
_any_env = bool(_resend_key or _from_email or (os.getenv("SECRET_KEY") or "").strip())
_from_email_display = repr(_from_email) if _from_email else 'MISSING'
print(
    f"[clarion:startup] interpreter={_sys.executable!r} "
    f"python={_sys.version.split()[0]} "
    f"env_vars_loaded={_any_env} "
    f"RESEND_API_KEY={'SET' if _resend_key else 'MISSING'} "
    f"from_email={_from_email_display}",
    file=_sys.stderr, flush=True,
)
if not _any_env:
    print(
        "[clarion:startup] WARNING: No expected env vars found after load_dotenv(). "
        "Wrong interpreter? Expected venv312\\Scripts\\python.exe. "
        "Run start.bat or invoke: venv312\\Scripts\\python.exe app.py",
        file=_sys.stderr, flush=True,
    )
del _sys, _resend_key, _from_email, _any_env
# ---------------------------------------------------------------------------

RESEND_API_KEY = os.getenv("RESEND_API_KEY")
FROM_EMAIL = os.getenv("FROM_EMAIL")
PARTNER_EMAILS = os.getenv("PARTNER_EMAILS", "").split(",")
PARTNER_EMAILS = [e for e in PARTNER_EMAILS if e]
SUPPORT_EMAIL = (os.getenv("SUPPORT_INBOX_EMAIL") or "support@clarionhq.co").strip().lower()
SECURITY_CONTACT_EMAIL = (os.getenv("SECURITY_CONTACT_EMAIL") or "security@clarionhq.co").strip().lower()

from flask import (

    Flask,

    render_template,

    request,

    redirect,

    url_for,

    flash,

    send_file,

    send_from_directory,

    jsonify,

    g,

    session,

)

from flask_login import (

    LoginManager,

    UserMixin,

    login_user,

    logout_user,

    login_required,

    current_user,

)

from flask_wtf.csrf import CSRFError, CSRFProtect, generate_csrf
try:
    from apscheduler.schedulers.background import BackgroundScheduler
    from apscheduler.triggers.cron import CronTrigger
    APSCHEDULER_AVAILABLE = True
except Exception:  # noqa: BLE001
    BackgroundScheduler = None  # type: ignore[assignment]
    CronTrigger = None  # type: ignore[assignment]
    APSCHEDULER_AVAILABLE = False
try:

    from flask_limiter import Limiter

    from flask_limiter.util import get_remote_address

    LIMITER_AVAILABLE = True

except Exception:  # noqa: BLE001

    class Limiter:

        def __init__(self, *args, **kwargs):

            pass



        def init_app(self, app):

            return None



        def limit(self, *args, **kwargs):

            def decorator(func):

                return func



            return decorator



        def request_filter(self, fn):

            return fn



    def get_remote_address():

        return request.remote_addr if 'request' in globals() else '127.0.0.1'



    LIMITER_AVAILABLE = False



from werkzeug.security import generate_password_hash, check_password_hash

from werkzeug.exceptions import RequestEntityTooLarge

from werkzeug.middleware.proxy_fix import ProxyFix  # F7/PR4: trusted-proxy IP resolution

from werkzeug.utils import secure_filename

import sqlite3
import stripe

# Unified DB operational error tuple: catches both SQLite and psycopg2 errors
# so except clauses work correctly regardless of which backend is active.
try:
    import psycopg2 as _psycopg2
    _DB_OPERATIONAL_ERRORS = (sqlite3.OperationalError, _psycopg2.OperationalError)
    _DB_INTEGRITY_ERRORS = (sqlite3.IntegrityError, _psycopg2.IntegrityError)
except ImportError:
    _psycopg2 = None
    _DB_OPERATIONAL_ERRORS = (sqlite3.OperationalError,)
    _DB_INTEGRITY_ERRORS = (sqlite3.IntegrityError,)

from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired
try:

    import bleach

except Exception:  # noqa: BLE001

    import html



    class bleach:

        @staticmethod

        def clean(value, strip=True):

            return html.escape(value or '')

from email.utils import parseaddr



from config import Config
from db_compat import DatabaseConnector
from pdf_generator import generate_pdf_report
from services.governance_insights import generate_governance_insights, compute_theme_trends
from services.plan_limits import PLAN_LIMITS
from services import plan_service
from services.signal_monitor import scan_recent_reviews_for_signals, get_active_alerts
from services.slack_service import send_slack_alert
from services.scheduler import start_scheduler as start_weekly_scheduler
from services.email_brief import (
    build_partner_brief_html,
    parse_partner_email_list,
    send_partner_brief_via_resend,
)
from services.meeting_summary import generate_partner_summary
from services.email_service import (
    EmailDeliveryResult,
    EmailPayload,
    KNOWN_WORKING_RESEND_EMAIL,
    send_email,
    send_email_batch,
    send_email_with_pdf,
    send_governance_email,

    init_mail,

    _known_working_resend_sender,
    _resolve_from_email,
    resolve_from_email_choice,
    send_templated_email,

    send_password_reset_email,

    send_verification_email,
    send_verification_email_with_result,
    uses_known_working_resend_sender,

    send_two_factor_code_email,

)



try:

    import sentry_sdk

    from sentry_sdk.integrations.flask import FlaskIntegration

except Exception:  # noqa: BLE001

    sentry_sdk = None



# Initialize Flask app
# Serve the built React SPA from frontend/dist when present
_REACT_DIST = os.path.abspath(
    os.path.join(os.path.dirname(__file__), '..', 'frontend', 'dist')
)
_react_dist_exists = os.path.isdir(_REACT_DIST)

app = Flask(
    __name__,
    static_folder=_REACT_DIST if _react_dist_exists else 'static',
    static_url_path='',
)
app.config.from_object(Config)
_db_connector = DatabaseConnector(app.config.get('DATABASE_URL', ''))
DEV_MODE = os.getenv("DEV_MODE", "false").strip().lower() == "true"
if DEV_MODE and os.getenv("FLASK_ENV") == "production":
    raise RuntimeError("DEV_MODE cannot be enabled in production")
app.config["DEV_MODE"] = DEV_MODE
app.config.setdefault('SESSION_COOKIE_HTTPONLY', True)
app.config.setdefault('SESSION_COOKIE_SAMESITE', 'Lax')
app.config.setdefault('SESSION_COOKIE_SECURE', not app.config.get('DEBUG', False))
app.permanent_session_lifetime = timedelta(
    seconds=app.config.get('PERMANENT_SESSION_LIFETIME_SECONDS', 60 * 60 * 12)
)
if DEV_MODE:
    print("WARNING: DEV MODE ENABLED - Email verification bypass active")
from time import time

EMAIL_VERIFICATION_SALT = 'clarion-email-verify-v1'
EMAIL_VERIFICATION_MAX_AGE_SECONDS = 24 * 60 * 60
RESEND_VERIFICATION_WINDOW_SECONDS = 10 * 60
RESEND_VERIFICATION_MAX_REQUESTS = 3
_resend_verification_attempts_by_ip = {}


# This service expects HTTPS to be terminated at the edge proxy/load balancer in production.



@app.context_processor

def inject_current_year():

    return {"current_year": datetime.utcnow().year, "asset_version": app.config.get("ASSET_VERSION", int(time()))}



# Initialize CSRF protection
#
# This SPA already sends explicit CSRF tokens on mutating API requests, and API
# origins are restricted separately in `_security_and_metrics_before_request`.
# Strict HTTPS referrer matching in Flask-WTF is brittle behind some proxy/host
# topologies and is currently blocking legitimate same-origin API writes.
app.config.setdefault('WTF_CSRF_SSL_STRICT', False)
csrf = CSRFProtect(app)

# Initialize basic rate limiting
_limiter_storage_uri = app.config.get('RATELIMIT_STORAGE_URI', 'memory://')
_is_prod = not app.config.get('DEBUG') and not app.config.get('TESTING')
if _is_prod and isinstance(_limiter_storage_uri, str) and _limiter_storage_uri.startswith('memory://'):
    raise RuntimeError('Rate limiter storage is memory:// in production. Set REDIS_URL/RATELIMIT_STORAGE_URI to redis://...')
if (not app.config.get('DEBUG')) and (not app.config.get('TESTING')) and isinstance(_limiter_storage_uri, str) and _limiter_storage_uri.startswith('memory://'):
    app.logger.warning('SECURITY WARNING: rate limiter storage is memory:// outside dev/test; abuse controls are process-local only.')
if isinstance(_limiter_storage_uri, str) and _limiter_storage_uri.startswith('redis://') and not _is_prod:
    try:
        parsed = urlparse(_limiter_storage_uri)
        redis_host = parsed.hostname or 'localhost'
        redis_port = int(parsed.port or 6379)
        with socket.create_connection((redis_host, redis_port), timeout=1.5):
            pass
    except Exception as _redis_probe_exc:  # noqa: BLE001
        app.logger.warning(
            'Rate limiter Redis storage unreachable (%s). Falling back to memory:// in non-production.',
            _redis_probe_exc,
        )
        _limiter_storage_uri = 'memory://'

try:
    limiter = Limiter(
        key_func=get_remote_address,
        storage_uri=_limiter_storage_uri,
        strategy='fixed-window',
        default_limits=["200 per day", "50 per hour"],

    )
    limiter.init_app(app)
except Exception as _limiter_exc:  # noqa: BLE001
    if _is_prod:
        raise
    app.logger.warning(

        'Rate limiter storage init failed for %s (%s). Falling back to memory:// in non-production.',

        _limiter_storage_uri,

        _limiter_exc,

    )

    limiter = Limiter(

        key_func=get_remote_address,

        storage_uri='memory://',

        strategy='fixed-window',

        default_limits=["200 per day", "50 per hour"],

    )

    limiter.init_app(app)



# PR4b: hop count is env-configurable (PROXY_HOPS); default 1 (Nginx-only).

# Set PROXY_HOPS=2 for Cloudflare+Nginx or ALB+Nginx, 3 for CF+ALB+Nginx.

# See config.py for the full decision table.

_proxy_hops = app.config.get('PROXY_HOPS', 1)

app.wsgi_app = ProxyFix(app.wsgi_app, x_for=_proxy_hops, x_proto=1, x_host=1, x_port=1)

app.logger.info('PR4: ProxyFix active with x_for=%d x_proto=1 x_host=1 x_port=1', _proxy_hops)



# F3/PR4: Redis client for shared brute-force tracking across workers.

# Import here so the try-block can handle missing package gracefully.

try:

    import redis as _redis_module

    _redis_url = app.config.get('REDIS_URL', '')

    if _redis_url:

        _redis_client = _redis_module.Redis.from_url(

            _redis_url,

            decode_responses=True,

            socket_connect_timeout=2,

            socket_timeout=2,

        )

        # Verify connectivity at startup; fail fast in production.

        try:

            _redis_client.ping()

            app.logger.info('PR4: Redis connected at %s', _redis_url)

        except Exception as _e:

            _redis_client = None

            _is_prod = not app.config.get('DEBUG') and not app.config.get('TESTING')

            if _is_prod:

                raise RuntimeError(

                    f'PR4: Redis required in production but unreachable ({_redis_url}): {_e}'

                ) from _e

            app.logger.warning(

                'PR4: Redis unavailable (%s) � falling back to in-memory login tracking. '

                'This is NOT safe under multi-worker deployment.', _e

            )

    else:

        _redis_client = None

        _is_prod = not app.config.get('DEBUG') and not app.config.get('TESTING')

        if _is_prod:

            raise RuntimeError(

                'PR4: REDIS_URL must be set in production for shared rate-limiting and '

                'brute-force protection. Set REDIS_URL=redis://... in your environment.'

            )

        app.logger.warning(

            'PR4: REDIS_URL not set � brute-force tracking is in-memory only. '

            'Set REDIS_URL for multi-worker safety.'

        )

except ImportError:

    _redis_client = None

    app.logger.warning(

        'PR4: redis package not installed � login backoff will be in-memory only. '

        'Run: pip install redis'

    )



@limiter.request_filter
def _rate_limit_exempt_for_tests():
    if app.config.get('TESTING', False):
        return True
    dev_rl_exempt_enabled = (
        bool(app.config.get('DEBUG'))
        or (app.config.get('DISABLE_RATE_LIMITS_IN_DEV', False) and app.config.get('APP_ENV') != 'production')
    )
    if dev_rl_exempt_enabled:
        req_path = (request.path or '').rstrip('/')
        if request.method == 'GET' and (
            req_path in {
                '/api/auth/me',
                '/api/exposure/latest',
                '/api/dashboard/stats',

                '/api/reports',
                '/api/credits',
                '/api/account/plan',
            }
            or re.fullmatch(r'/api/reports/\d+', req_path) is not None
            or re.fullmatch(r'/api/reports/\d+/actions', req_path) is not None
        ):
            return True
    # E2E escape hatch for local/dev smoke tests only.

    # Never active in production because DEBUG is false there.

    return bool(app.config.get('DEBUG')) and request.headers.get('X-E2E-Test') == '1'



# Initialize email service

init_mail(app)



if os.environ.get('FLASK_ENV') == 'production' and not LIMITER_AVAILABLE:

    raise RuntimeError('flask-limiter must be installed in production environments')



os.makedirs(app.config.get('LOG_DIR', 'logs'), exist_ok=True)

_file_handler = RotatingFileHandler(

    os.path.join(app.config.get('LOG_DIR', 'logs'), 'app.log'),

    maxBytes=5 * 1024 * 1024,

    backupCount=5,

)

_file_handler.setFormatter(logging.Formatter('%(asctime)s %(levelname)s %(name)s %(message)s'))

app.logger.setLevel(app.config.get('LOG_LEVEL', 'INFO'))

if not any(isinstance(h, RotatingFileHandler) for h in app.logger.handlers):

    app.logger.addHandler(_file_handler)



if sentry_sdk and app.config.get('SENTRY_DSN'):

    sentry_sdk.init(

        dsn=app.config.get('SENTRY_DSN'),

        integrations=[FlaskIntegration()],

        traces_sample_rate=app.config.get('SENTRY_TRACES_SAMPLE_RATE', 0.1),

    )



# Configure Stripe

stripe.api_key = app.config.get('STRIPE_SECRET_KEY')



MAX_CSV_ROWS = 5000
MAX_REVIEW_TEXT_LENGTH = 5000
MAX_CSV_FIELD_LENGTH = 5000
ALLOWED_CSV_MIME_TYPES = {
    "text/csv",
    "application/csv",
    "application/vnd.ms-excel",
}
MAX_FIRM_NAME_LENGTH = 120

EMAIL_REGEX = re.compile(r'^[^@\s]+@[^@\s]+\.[^@\s]+$')



FREE_PLAN_REPORT_LIMIT = 1
FREE_PLAN_MAX_REVIEWS_PER_REPORT = 50
ONETIME_MAX_REVIEWS_PER_REPORT = 500
# Canonical firm plans.
FIRM_PLAN_FREE = plan_service.FIRM_PLAN_FREE
FIRM_PLAN_TEAM = plan_service.FIRM_PLAN_TEAM
FIRM_PLAN_FIRM = plan_service.FIRM_PLAN_FIRM
# Legacy aliases retained for backward compatibility with existing rows.
FIRM_PLAN_TRIAL = "trial"
FIRM_PLAN_PROFESSIONAL = "professional"
FIRM_PLAN_LEADERSHIP = "leadership"
FIRM_PLAN_VALUES = {
    FIRM_PLAN_FREE,
    FIRM_PLAN_TEAM,
    FIRM_PLAN_FIRM,
    FIRM_PLAN_TRIAL,
    FIRM_PLAN_PROFESSIONAL,
    FIRM_PLAN_LEADERSHIP,
}
SECURITY_EVENT_META_MAX = 2048
MAX_BRANDING_LOGO_BYTES = 5 * 1024 * 1024
ALLOWED_LOGO_EXTENSIONS = {'png', 'jpg', 'jpeg'}  # SVG removed: stored XSS risk (F2)

BRANDING_THEME_DEFAULT = 'default'

BRANDING_THEME_PRESETS = {

    'default': {'label': 'Default', 'accent': '#d97706', 'primary': '#1e3a8a', 'surface': '#f8fafc'},

    'blue': {'label': 'Blue', 'accent': '#2563eb', 'primary': '#1d4ed8', 'surface': '#eff6ff'},

    'green': {'label': 'Green', 'accent': '#0f766e', 'primary': '#065f46', 'surface': '#ecfdf5'},

}

BRANDING_UPLOAD_DIR = os.path.join(app.root_path, 'static', 'uploads', 'branding')

os.makedirs(BRANDING_UPLOAD_DIR, exist_ok=True)



CSV_HEADER_ALIASES = {

    'date': (

        'date',

        'review_date',

        'created_at',

        'created',

        'submitted_at',

        'submitted',

        'timestamp',

        'time',

        'at',

        'published_at',

        'publish_time',

    ),

    'rating': (

        'rating (1-5)',

        'rating',

        'overall rating',

        'overall',

        'rate',

        'score',

        'star rating',

        'stars',

        'star_rating',

        'review_rating',

        'review_score',

    ),

    'review_text': (

        'client comment',

        'review_text',

        'review',

        'review text',

        'review_body',

        'comment',

        'comments',

        'feedback',

        'text',

        'response',

        'content',

        'message',

    ),

}



REQUEST_METRICS = {

    'requests_total': 0,

    'errors_total': 0,

    'latency_ms_total': 0.0,

}



FAILED_LOGIN_ATTEMPTS = {}   # F3/PR4: in-memory fallback only; replaced by Redis below

LOGIN_BACKOFF_WINDOW_SECONDS = 15 * 60

LOGIN_BACKOFF_THRESHOLD = 3

LOGIN_BACKOFF_MAX_SECONDS = 15

TWO_FACTOR_CODE_LENGTH = 6

TWO_FACTOR_MAX_ATTEMPTS = 5





def _is_dev_environment():

    return bool(app.config.get('DEBUG') or app.config.get('TESTING'))





def _is_local_host(hostname):

    host_value = (hostname or '').split(':', 1)[0].lower()

    return host_value in {'localhost', '127.0.0.1', '::1'}





def _request_is_secure():

    forwarded_proto = (request.headers.get('X-Forwarded-Proto', '') or '').split(',', 1)[0].strip().lower()

    if forwarded_proto:

        return forwarded_proto == 'https'

    return request.is_secure





def _security_headers_enabled():

    return app.config.get('ENABLE_SECURITY_HEADERS', True) and not _is_dev_environment()





def _is_allowed_cors_origin(origin):

    if not origin:

        return True

    configured = str(app.config.get('CORS_ALLOWED_ORIGINS', '') or '').strip()

    allowed = set()
    if configured:
        allowed.update({item.strip() for item in configured.split(',') if item.strip()})

    # Support comma-separated FRONTEND_ORIGIN values as well.
    frontend_origin = (os.environ.get('FRONTEND_ORIGIN') or '').strip()
    if frontend_origin:
        allowed.update({item.strip().rstrip('/') for item in frontend_origin.split(',') if item.strip()})

    parsed_origin = urlparse(origin)

    # Dev ergonomics: allow localhost/127.0.0.1 origins on any port and
    # temporary Cloudflare quick-tunnel origins. Production still requires
    # explicit allowlisting via CORS_ALLOWED_ORIGINS.
    if _is_dev_environment():
        origin_host = (parsed_origin.hostname or '').lower()
        if _is_local_host(origin_host):
            return parsed_origin.scheme in {'http', 'https'}
        if origin_host.endswith('.trycloudflare.com'):
            return parsed_origin.scheme == 'https'

    if allowed:
        return origin.rstrip('/') in {item.rstrip('/') for item in allowed}

    parsed_host = urlparse(request.host_url)

    # Dev ergonomics: temporary public previews often use Cloudflare quick tunnels.
    # Keep strict allowlisting in production via CORS_ALLOWED_ORIGINS.
    if _is_dev_environment():
        origin_host = (parsed_origin.hostname or '').lower()
        if origin_host.endswith('.trycloudflare.com'):
            return parsed_origin.scheme == 'https'

    return (

        parsed_origin.scheme in {'http', 'https'}

        and parsed_origin.scheme == parsed_host.scheme

        and parsed_origin.netloc == parsed_host.netloc

    )





def _safe_api_error(message, status_code=500, *, log_message=None):

    request_id = getattr(g, 'request_id', None)

    if log_message:

        app.logger.exception('%s request_id=%s', log_message, request_id)

    return jsonify({'success': False, 'error': message, 'request_id': request_id}), status_code





def _mask_identifier(identifier):

    value = (identifier or '').strip()

    if not value:

        return 'unknown'

    if '@' in value:

        local, domain = value.split('@', 1)

        local_masked = f"{local[:2]}***" if local else "***"

        return f"{local_masked}@{domain}"

    return f"{value[:2]}***"





def _prune_login_attempts(now_ts):

    """No-op when Redis is active (TTL handles expiry); kept for in-memory fallback."""

    expiry_cutoff = now_ts - LOGIN_BACKOFF_WINDOW_SECONDS

    stale_keys = [

        key for key, item in FAILED_LOGIN_ATTEMPTS.items()

        if item.get('last_failed_at', 0) < expiry_cutoff

    ]

    for key in stale_keys:

        FAILED_LOGIN_ATTEMPTS.pop(key, None)





def _record_failed_login(identifier, client_ip):

    """Atomically increment failure counters; uses Redis when available."""

    if _redis_client is not None:

        # F3/PR4: atomic INCR + EXPIRE � cross-worker, survives restarts.

        # Two keys: one per-IP (always) and one per-account (email hash, no PII in key).

        account_hash = hashlib.sha256(identifier.encode()).hexdigest()[:16]

        for rkey in (f'login_fail:ip:{client_ip}', f'login_fail:acct:{account_hash}'):

            try:

                pipe = _redis_client.pipeline(transaction=False)

                pipe.incr(rkey)

                pipe.expire(rkey, LOGIN_BACKOFF_WINDOW_SECONDS)

                pipe.execute()

            except Exception as _e:

                app.logger.warning('PR4: Redis record_failed_login error: %s', _e)

        return

    # Fallback: in-memory (single-worker dev only)

    now_ts = time_module.time()

    _prune_login_attempts(now_ts)

    for key in (f'account:{identifier}', f'ip:{client_ip}'):

        record = FAILED_LOGIN_ATTEMPTS.get(key, {'count': 0, 'last_failed_at': now_ts})

        record['count'] += 1

        record['last_failed_at'] = now_ts

        FAILED_LOGIN_ATTEMPTS[key] = record





def _clear_failed_login(identifier, client_ip):

    """Delete failure counters on successful authentication."""

    if _redis_client is not None:

        account_hash = hashlib.sha256(identifier.encode()).hexdigest()[:16]

        try:

            _redis_client.delete(

                f'login_fail:ip:{client_ip}',

                f'login_fail:acct:{account_hash}',

            )

        except Exception as _e:

            app.logger.warning('PR4: Redis clear_failed_login error: %s', _e)

        return

    FAILED_LOGIN_ATTEMPTS.pop(f'account:{identifier}', None)

    FAILED_LOGIN_ATTEMPTS.pop(f'ip:{client_ip}', None)





def _login_backoff_seconds(identifier, client_ip):

    """Return seconds to sleep before processing a login attempt."""

    if _redis_client is not None:

        account_hash = hashlib.sha256(identifier.encode()).hexdigest()[:16]

        max_delay = 0

        for rkey in (f'login_fail:ip:{client_ip}', f'login_fail:acct:{account_hash}'):

            try:

                val = _redis_client.get(rkey)

                failures = int(val) if val else 0

            except Exception as _e:

                app.logger.warning('PR4: Redis login_backoff error: %s', _e)

                failures = 0

            if failures >= LOGIN_BACKOFF_THRESHOLD:

                delay = min(LOGIN_BACKOFF_MAX_SECONDS, failures - LOGIN_BACKOFF_THRESHOLD + 1)

                max_delay = max(max_delay, delay)

        return max_delay

    # Fallback: in-memory

    now_ts = time_module.time()

    _prune_login_attempts(now_ts)

    max_delay = 0

    for key in (f'account:{identifier}', f'ip:{client_ip}'):

        record = FAILED_LOGIN_ATTEMPTS.get(key)

        if not record:

            continue

        failures = int(record.get('count', 0))

        if failures < LOGIN_BACKOFF_THRESHOLD:

            continue

        delay = min(LOGIN_BACKOFF_MAX_SECONDS, failures - LOGIN_BACKOFF_THRESHOLD + 1)

        max_delay = max(max_delay, delay)

    return max_delay





@app.before_request

def _security_and_metrics_before_request():

    request_id = (request.headers.get('X-Request-ID') or '').strip()

    if not request_id:

        request_id = str(uuid.uuid4())

    g.request_id = request_id

    if request.path.startswith('/api/'):

        origin = (request.headers.get('Origin') or '').strip()

        if origin and not _is_allowed_cors_origin(origin):

            app.logger.warning('cors_denied request_id=%s origin=%s path=%s', g.request_id, origin, request.path)

            return jsonify({'success': False, 'error': 'CORS origin denied.', 'request_id': g.request_id}), 403

        # Handle CORS preflight early for API routes.
        if request.method == 'OPTIONS':
            return ('', 204)

    request._start_ts = perf_counter()

    if _is_dev_environment() or not app.config.get('FORCE_HTTPS', True):

        return None

    if _is_local_host(request.host):

        return None

    forwarded_proto = (request.headers.get('X-Forwarded-Proto', '') or '').split(',', 1)[0].strip().lower()

    if not forwarded_proto:

        return None

    if forwarded_proto == 'https' or _request_is_secure():

        return None

    secure_url = request.url.replace('http://', 'https://', 1)

    return redirect(secure_url, code=307)





@app.after_request

def _metrics_and_security_after_request(response):

    request_id = getattr(g, 'request_id', None)

    if request_id:

        response.headers['X-Request-ID'] = request_id

    if request.path.startswith('/api/'):

        origin = (request.headers.get('Origin') or '').strip()

        if origin and _is_allowed_cors_origin(origin):

            response.headers['Access-Control-Allow-Origin'] = origin

            response.headers['Access-Control-Allow-Credentials'] = 'true'

            response.headers['Access-Control-Allow-Headers'] = 'Content-Type, X-CSRFToken, X-Requested-With, X-Request-ID'

            response.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, PATCH, DELETE, OPTIONS'

            vary = response.headers.get('Vary')

            response.headers['Vary'] = f'{vary}, Origin' if vary else 'Origin'

    started = getattr(request, '_start_ts', None)

    if started is not None:

        REQUEST_METRICS['requests_total'] += 1

        elapsed = (perf_counter() - started) * 1000.0

        REQUEST_METRICS['latency_ms_total'] += elapsed

        if response.status_code >= 400:

            REQUEST_METRICS['errors_total'] += 1



    if _security_headers_enabled():

        response.headers['X-Content-Type-Options'] = 'nosniff'

        response.headers['X-Frame-Options'] = 'SAMEORIGIN'

        response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'

        response.headers['Content-Security-Policy'] = app.config.get('SECURITY_CSP_POLICY')

        if _request_is_secure():

            response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'

    if started is not None:

        app.logger.info('request_complete request_id=%s method=%s path=%s status=%s latency_ms=%.2f',

            request_id, request.method, request.path, response.status_code, elapsed)

    else:

        app.logger.info('request_complete request_id=%s method=%s path=%s status=%s',

            request_id, request.method, request.path, response.status_code)

    return response





def db_connect():
    return _db_connector.connect()




def _log_security_event(user_id, event_type, metadata=None):

    """Best-effort append-only audit log writer. Never raises."""

    conn = None

    try:

        event_name = str(event_type or '').strip()

        if not event_name:

            return



        if isinstance(metadata, dict):

            safe = metadata

        elif metadata is not None:

            safe = {'value': metadata}

        else:

            safe = {}



        try:

            serialized_meta = json.dumps(safe, separators=(',', ':'), ensure_ascii=False)

        except Exception:  # noqa: BLE001

            serialized_meta = json.dumps({'_error': 'metadata_unserializable'}, separators=(',', ':'))

        if len(serialized_meta) > SECURITY_EVENT_META_MAX:

            serialized_meta = serialized_meta[:SECURITY_EVENT_META_MAX]



        conn = db_connect()

        c = conn.cursor()

        c.execute(

            '''

            INSERT INTO security_events (user_id, event_type, metadata)

            VALUES (?, ?, ?)

            ''',

            (user_id, event_name, serialized_meta),

        )

        conn.commit()

    except _DB_OPERATIONAL_ERRORS as exc:

        message = str(exc).lower()

        if 'locked' in message:

            app.logger.debug('security_events locked: %s', exc)

        else:

            app.logger.debug('security_events operational error: %s', exc)

    except Exception as exc:  # noqa: BLE001

        app.logger.debug('security_events failed: %s', exc)

    finally:

        if conn is not None:

            try:

                conn.close()

            except Exception:  # noqa: BLE001

                pass





def is_valid_email(email):

    if not email:

        return False

    _, parsed = parseaddr(email)

    return bool(parsed and EMAIL_REGEX.match(parsed) and len(parsed) <= 254)





def validate_password_strength(password):

    if not password or len(password) < 8:

        return False, 'Password must be at least 8 characters long.'

    if not re.search(r'[A-Z]', password):

        return False, 'Password must include at least one uppercase letter.'

    if not re.search(r'[a-z]', password):

        return False, 'Password must include at least one lowercase letter.'

    if not re.search(r'\d', password):

        return False, 'Password must include at least one number.'

    return True, ''



# Initialize Flask-Login

login_manager = LoginManager()

@login_manager.user_loader

def load_user(user_id):

    conn = db_connect()

    c = conn.cursor()

    c.execute(

        '''

        SELECT

            id,

            username,

            email,

            firm_name,

            is_admin,

            stripe_customer_id,

            stripe_subscription_id,

            subscription_status,

            trial_reviews_used,

            trial_limit,

            one_time_reports_purchased,

            one_time_reports_used,

            subscription_type,

            trial_month,

            trial_review_limit_per_report,
            two_factor_enabled,
            two_factor_method,
            email_verified,
            onboarding_complete
        FROM users
        WHERE id = ?
        ''',
        (user_id,),

    )

    user_data = c.fetchone()

    conn.close()



    if user_data:

        return User(

            id=user_data[0],

            username=user_data[1],

            email=user_data[2],

            firm_name=user_data[3],

            is_admin=user_data[4],

            stripe_customer_id=user_data[5],

            stripe_subscription_id=user_data[6],

            subscription_status=user_data[7],

            trial_reviews_used=user_data[8],

            trial_limit=user_data[9],

            one_time_reports_purchased=user_data[10],

            one_time_reports_used=user_data[11],

            subscription_type=user_data[12],

            trial_month=user_data[13],

            trial_review_limit_per_report=user_data[14],
            two_factor_enabled=user_data[15],
            two_factor_method=user_data[16],
            email_verified=user_data[17],
            onboarding_complete=user_data[18],
        )
    return None



login_manager.init_app(app)

login_manager.login_view = 'login'





@login_manager.unauthorized_handler

def _handle_unauthorized():

    if request.path.startswith('/api/'):

        return jsonify({'success': False, 'error': 'Not authenticated'}), 401

    return redirect(url_for('login'))



# ===== DATABASE INITIALIZATION =====



def init_db():

    """Initialize SQLite database with reviews and users tables."""

    conn = db_connect()

    c = conn.cursor()

    c.execute('PRAGMA journal_mode = WAL')

    

    def _add_column_if_missing(existing_columns, column_name, ddl):

        if column_name in existing_columns:

            return

        try:

            c.execute(ddl)

        except _DB_OPERATIONAL_ERRORS as exc:

            if 'duplicate column name' not in str(exc).lower() and 'already exists' not in str(exc).lower():

                raise

        if column_name not in existing_columns:

            existing_columns.append(column_name)



    # Create reviews table

    c.execute('''

        CREATE TABLE IF NOT EXISTS reviews (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            date TEXT NOT NULL,

            rating INTEGER NOT NULL,

            review_text TEXT NOT NULL,

            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP

        )

    ''')



    # Create users table for admin auth + pricing / usage tracking

    c.execute('''

        CREATE TABLE IF NOT EXISTS users (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            email TEXT UNIQUE NOT NULL,

            username TEXT UNIQUE NOT NULL,

            password_hash TEXT NOT NULL,
            is_verified INTEGER NOT NULL DEFAULT 0,
            email_verified INTEGER NOT NULL DEFAULT 0,
            onboarding_complete INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL,
            firm_name TEXT,

            is_admin INTEGER DEFAULT 1,

            trial_reports_used INTEGER DEFAULT 0,

            trial_month TEXT,

            trial_review_limit_per_report INTEGER DEFAULT 50,

            stripe_customer_id TEXT,

            stripe_subscription_id TEXT,

            subscription_status TEXT DEFAULT 'trial',

            trial_reviews_used INTEGER DEFAULT 0,

            trial_limit INTEGER DEFAULT 1,

            one_time_reports_purchased INTEGER DEFAULT 0,

            one_time_reports_used INTEGER DEFAULT 0,

            subscription_type TEXT DEFAULT 'trial',

            two_factor_enabled INTEGER DEFAULT 0,

            two_factor_method TEXT DEFAULT 'email'

        )

    ''')



    # Create report snapshots table

    c.execute(

        '''

        CREATE TABLE IF NOT EXISTS reports (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            user_id INTEGER NOT NULL,

            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

            total_reviews INTEGER NOT NULL,

            avg_rating REAL NOT NULL,

            themes TEXT,

            top_praise TEXT,

            top_complaints TEXT,

            subscription_type_at_creation TEXT,

            report_hash TEXT,

            FOREIGN KEY (user_id) REFERENCES users (id)

        )

        '''

    )



    c.execute(

        '''

        CREATE TABLE IF NOT EXISTS report_action_items (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            user_id INTEGER NOT NULL,

            report_id INTEGER NOT NULL,

            title TEXT NOT NULL,

            owner TEXT,

            status TEXT NOT NULL DEFAULT 'open',

            due_date TEXT,

            timeframe TEXT,

            kpi TEXT,

            notes TEXT,

            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,

            FOREIGN KEY (report_id) REFERENCES reports(id) ON DELETE CASCADE

        )

        '''

    )



    c.execute(

        '''

        CREATE TABLE IF NOT EXISTS report_pack_schedules (

            user_id INTEGER PRIMARY KEY,

            enabled INTEGER NOT NULL DEFAULT 0,

            cadence TEXT NOT NULL DEFAULT 'weekly',

            recipients_json TEXT NOT NULL DEFAULT '[]',

            last_sent_at TEXT,

            next_send_at TEXT,

            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE

        )

        '''

    )

    c.execute(

        '''

        CREATE TABLE IF NOT EXISTS support_tickets (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            ticket_ref TEXT UNIQUE NOT NULL,

            user_id INTEGER,

            requester_name TEXT,

            requester_email TEXT NOT NULL,

            firm_name TEXT,

            source TEXT NOT NULL DEFAULT 'contact',

            category TEXT NOT NULL,

            urgency TEXT NOT NULL DEFAULT 'normal',

            subject TEXT NOT NULL,

            message TEXT NOT NULL,

            status TEXT NOT NULL DEFAULT 'new',

            priority TEXT NOT NULL DEFAULT 'normal',

            escalation_level TEXT NOT NULL DEFAULT 'none',

            escalation_reason TEXT,

            auto_response_template TEXT,

            auto_response_sent INTEGER NOT NULL DEFAULT 0,

            handled_by_user_id INTEGER,

            created_at TEXT NOT NULL,

            updated_at TEXT NOT NULL,

            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL,

            FOREIGN KEY (handled_by_user_id) REFERENCES users(id) ON DELETE SET NULL

        )

        '''

    )

    c.execute('CREATE INDEX IF NOT EXISTS idx_support_tickets_user_id ON support_tickets(user_id)')
    c.execute('CREATE INDEX IF NOT EXISTS idx_support_tickets_requester_email ON support_tickets(requester_email)')
    c.execute('CREATE INDEX IF NOT EXISTS idx_support_tickets_status_priority ON support_tickets(status, priority, created_at)')



    # Ownership mapping for multi-tenant review isolation without changing reviews schema

    c.execute(

        '''

        CREATE TABLE IF NOT EXISTS review_ownership (

            review_id INTEGER PRIMARY KEY,

            user_id INTEGER NOT NULL,

            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

            FOREIGN KEY (review_id) REFERENCES reviews(id) ON DELETE CASCADE,

            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE

        )

        '''

    )



    # Password reset tokens

    c.execute(

        '''

        CREATE TABLE IF NOT EXISTS password_reset_tokens (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            user_id INTEGER NOT NULL,

            token TEXT UNIQUE NOT NULL,

            expires_at TEXT NOT NULL,

            used_at TEXT,

            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE

        )

        '''

    )



    c.execute(

        '''

        CREATE TABLE IF NOT EXISTS email_verification_tokens (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            user_id INTEGER NOT NULL,

            token TEXT UNIQUE NOT NULL,

            expires_at TEXT NOT NULL,

            used_at TEXT,

            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE

        )

        '''

    )



    c.execute(

        '''

        CREATE TABLE IF NOT EXISTS user_email_verification (

            user_id INTEGER PRIMARY KEY,

            verified_at TEXT,

            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE

        )

        '''

    )



    c.execute(

        '''

        CREATE TABLE IF NOT EXISTS account_branding (

            user_id INTEGER PRIMARY KEY,

            logo_filename TEXT,

            accent_theme TEXT NOT NULL DEFAULT 'default',

            updated_at TEXT,

            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE

        )

        '''

    )



    c.execute(

        '''

        CREATE TABLE IF NOT EXISTS two_factor_challenges (

            id TEXT PRIMARY KEY,

            user_id INTEGER NOT NULL,

            code_hash TEXT NOT NULL,

            expires_at TEXT NOT NULL,

            consumed_at TEXT,

            attempts INTEGER DEFAULT 0,

            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE

        )

        '''

    )



    # F4: Idempotency gate for Stripe checkout credit grants.

    # PRIMARY KEY on session_id guarantees uniqueness; INSERT OR IGNORE is

    # used as the atomic dedupe check before any credit increment.

    c.execute(

        '''

        CREATE TABLE IF NOT EXISTS processed_checkout_sessions (

            session_id  TEXT    PRIMARY KEY,

            user_id     INTEGER NOT NULL,

            plan        TEXT    NOT NULL,

            processed_at TEXT   NOT NULL

        )

        '''

    )

    # F15/PR6: public_feedback isolates anonymous client submissions from user review datasets.

    # The /feedback route writes here regardless of auth status; it NEVER touches `reviews`.

    c.execute(

        '''

        CREATE TABLE IF NOT EXISTS public_feedback (

            id          INTEGER PRIMARY KEY AUTOINCREMENT,

            date        TEXT    NOT NULL,

            rating      INTEGER NOT NULL,

            review_text TEXT    NOT NULL,

            submitted_at TEXT   NOT NULL DEFAULT (CURRENT_TIMESTAMP)

        )

        '''

    )

    c.execute(

        '''

        CREATE TABLE IF NOT EXISTS security_events (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            user_id INTEGER,

            event_type TEXT NOT NULL,

            metadata TEXT,

            created_at TEXT NOT NULL DEFAULT (CURRENT_TIMESTAMP)

        )

        '''

    )



    c.execute(

        '''

        CREATE TABLE IF NOT EXISTS report_pdf_artifacts (

            report_id INTEGER PRIMARY KEY,

            user_id INTEGER NOT NULL,

            pdf_blob BYTEA NOT NULL,

            generated_at TEXT NOT NULL,

            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

            FOREIGN KEY (report_id) REFERENCES reports(id) ON DELETE CASCADE,

            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE

        )

        '''

    )

    c.execute(
        '''
        CREATE TABLE IF NOT EXISTS firms (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            plan TEXT NOT NULL DEFAULT 'free' CHECK(plan IN ('free','team','firm','trial','professional','leadership')),
            created_at TEXT NOT NULL,
            created_by_user_id INTEGER,
            FOREIGN KEY (created_by_user_id) REFERENCES users(id) ON DELETE SET NULL
        )
        '''
    )

    c.execute(

        '''

        CREATE TABLE IF NOT EXISTS firm_users (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            firm_id INTEGER NOT NULL,

            user_id INTEGER NOT NULL,

            role TEXT NOT NULL CHECK(role IN ('owner','partner','member')),

            status TEXT NOT NULL CHECK(status IN ('active','invited','suspended')),

            invited_by_user_id INTEGER,

            invited_at TEXT,

            joined_at TEXT,

            invite_token_hash TEXT,

            UNIQUE(firm_id, user_id),

            FOREIGN KEY (firm_id) REFERENCES firms(id) ON DELETE CASCADE,

            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,

            FOREIGN KEY (invited_by_user_id) REFERENCES users(id) ON DELETE SET NULL

        )

        '''

    )

    c.execute(

        '''

        CREATE TABLE IF NOT EXISTS audit_log (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            firm_id INTEGER NOT NULL,

            actor_user_id INTEGER NOT NULL,

            entity_type TEXT NOT NULL CHECK(entity_type IN ('report','action','governance_brief','member')),

            entity_id INTEGER NOT NULL,

            event_type TEXT NOT NULL,

            before_json TEXT,

            after_json TEXT,

            created_at TEXT NOT NULL,

            FOREIGN KEY (firm_id) REFERENCES firms(id) ON DELETE CASCADE,

            FOREIGN KEY (actor_user_id) REFERENCES users(id) ON DELETE CASCADE

        )

        '''

    )

    c.execute(
        '''
        CREATE TABLE IF NOT EXISTS governance_briefs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            firm_id INTEGER NOT NULL,

            created_by_user_id INTEGER NOT NULL,

            exposure_snapshot_json TEXT NOT NULL,

            version_hash TEXT NOT NULL,

            created_at TEXT NOT NULL,

            pdf_path TEXT,

            FOREIGN KEY (firm_id) REFERENCES firms(id) ON DELETE CASCADE,

            FOREIGN KEY (created_by_user_id) REFERENCES users(id) ON DELETE CASCADE

        )
        '''
    )
    c.execute(
        '''
        CREATE TABLE IF NOT EXISTS governance_signals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            report_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            description TEXT,
            severity TEXT NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY (report_id) REFERENCES reports(id) ON DELETE CASCADE
        )
        '''
    )
    c.execute(
        '''
        CREATE TABLE IF NOT EXISTS governance_recommendations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            report_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            priority TEXT NOT NULL,
            suggested_owner TEXT,
            created_at TEXT NOT NULL,
            FOREIGN KEY (report_id) REFERENCES reports(id) ON DELETE CASCADE
        )
        '''
    )
    c.execute(

        '''

        CREATE TABLE IF NOT EXISTS interest_events (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            firm_id INTEGER NOT NULL,

            user_id INTEGER NOT NULL,

            type TEXT NOT NULL,

            source TEXT NOT NULL,

            created_at TEXT NOT NULL,

            FOREIGN KEY (firm_id) REFERENCES firms(id) ON DELETE CASCADE,

            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE

        )

        '''

    )

    c.execute(

        '''

        CREATE TABLE IF NOT EXISTS feature_interest (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            firm_id INTEGER NOT NULL,

            feature_key TEXT NOT NULL,

            choice TEXT NOT NULL CHECK(choice IN ('yes','no')),

            updated_at TEXT NOT NULL,

            UNIQUE(firm_id, feature_key),

            FOREIGN KEY (firm_id) REFERENCES firms(id) ON DELETE CASCADE

        )

        '''

    )

    c.execute('PRAGMA table_info(security_events)')

    security_event_columns = [col[1] for col in c.fetchall()]

    _add_column_if_missing(

        security_event_columns,

        'metadata',

        'ALTER TABLE security_events ADD COLUMN metadata TEXT',

    )



    # Migration: ensure new pricing / Stripe columns exist on older databases

    c.execute('PRAGMA table_info(users)')

    columns = [col[1] for col in c.fetchall()]



    # Core SaaS columns

    _add_column_if_missing(columns, 'email', 'ALTER TABLE users ADD COLUMN email TEXT')
    _add_column_if_missing(columns, 'firm_name', 'ALTER TABLE users ADD COLUMN firm_name TEXT')
    _add_column_if_missing(columns, 'email_verified', 'ALTER TABLE users ADD COLUMN email_verified INTEGER DEFAULT 0')
    had_onboarding_complete = 'onboarding_complete' in columns
    _add_column_if_missing(columns, 'onboarding_complete', 'ALTER TABLE users ADD COLUMN onboarding_complete INTEGER DEFAULT 0')
    if not had_onboarding_complete:
        c.execute(
            '''
            UPDATE users
            SET onboarding_complete = CASE
                WHEN COALESCE(is_admin, 0) = 1 THEN 1
                WHEN EXISTS(
                    SELECT 1
                    FROM firm_users fu
                    WHERE fu.user_id = users.id
                      AND fu.status = 'active'
                ) THEN 1
                ELSE 0
            END
            '''
        )


    # Stripe-related columns

    _add_column_if_missing(columns, 'stripe_customer_id', 'ALTER TABLE users ADD COLUMN stripe_customer_id TEXT')

    _add_column_if_missing(columns, 'stripe_subscription_id', 'ALTER TABLE users ADD COLUMN stripe_subscription_id TEXT')

    _add_column_if_missing(

        columns,

        'subscription_status',

        "ALTER TABLE users ADD COLUMN subscription_status TEXT DEFAULT 'trial'",

    )



    # Trial and one-time report tracking

    _add_column_if_missing(columns, 'trial_reviews_used', 'ALTER TABLE users ADD COLUMN trial_reviews_used INTEGER DEFAULT 0')

    _add_column_if_missing(columns, 'trial_limit', 'ALTER TABLE users ADD COLUMN trial_limit INTEGER DEFAULT 1')

    _add_column_if_missing(

        columns,

        'one_time_reports_purchased',

        'ALTER TABLE users ADD COLUMN one_time_reports_purchased INTEGER DEFAULT 0',

    )

    _add_column_if_missing(columns, 'one_time_reports_used', 'ALTER TABLE users ADD COLUMN one_time_reports_used INTEGER DEFAULT 0')

    _add_column_if_missing(columns, 'subscription_type', "ALTER TABLE users ADD COLUMN subscription_type TEXT DEFAULT 'trial'")

    _add_column_if_missing(columns, 'two_factor_enabled', 'ALTER TABLE users ADD COLUMN two_factor_enabled INTEGER DEFAULT 0')

    _add_column_if_missing(columns, 'two_factor_method', "ALTER TABLE users ADD COLUMN two_factor_method TEXT DEFAULT 'email'")



    c.execute('PRAGMA table_info(reports)')

    report_columns = [col[1] for col in c.fetchall()]

    _add_column_if_missing(report_columns, 'report_hash', 'ALTER TABLE reports ADD COLUMN report_hash TEXT')

    _add_column_if_missing(report_columns, 'custom_name', 'ALTER TABLE reports ADD COLUMN custom_name TEXT')

    _add_column_if_missing(report_columns, 'deleted_at', 'ALTER TABLE reports ADD COLUMN deleted_at TEXT')

    _add_column_if_missing(report_columns, 'purge_at', 'ALTER TABLE reports ADD COLUMN purge_at TEXT')

    _add_column_if_missing(report_columns, 'firm_id', 'ALTER TABLE reports ADD COLUMN firm_id INTEGER')

    _add_column_if_missing(report_columns, 'created_by_user_id', 'ALTER TABLE reports ADD COLUMN created_by_user_id INTEGER')



    c.execute('PRAGMA table_info(report_action_items)')
    action_columns = [col[1] for col in c.fetchall()]
    _add_column_if_missing(action_columns, 'firm_id', 'ALTER TABLE report_action_items ADD COLUMN firm_id INTEGER')

    _add_column_if_missing(action_columns, 'owner_user_id', 'ALTER TABLE report_action_items ADD COLUMN owner_user_id INTEGER')

    _add_column_if_missing(action_columns, 'timeframe', 'ALTER TABLE report_action_items ADD COLUMN timeframe TEXT')

    _add_column_if_missing(action_columns, 'created_by_user_id', 'ALTER TABLE report_action_items ADD COLUMN created_by_user_id INTEGER')
    _add_column_if_missing(action_columns, 'updated_by_user_id', 'ALTER TABLE report_action_items ADD COLUMN updated_by_user_id INTEGER')

    c.execute('PRAGMA table_info(firms)')
    firm_columns = [col[1] for col in c.fetchall()]
    firms_table_sql_row = None
    if not _db_connector.is_postgres:
        c.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='firms'")
        firms_table_sql_row = c.fetchone()
    firms_table_sql = str(firms_table_sql_row[0] or '').lower() if firms_table_sql_row else ''
    legacy_plan_check = "check(plan in ('trial','professional','leadership'))" in firms_table_sql
    if legacy_plan_check:
        # SQLite cannot alter CHECK constraints in place; rebuild firms table once.
        c.execute('PRAGMA foreign_keys=OFF')
        has_practice_area = 'practice_area' in firm_columns
        has_firm_size = 'firm_size' in firm_columns
        c.execute(
            '''
            CREATE TABLE IF NOT EXISTS firms_new (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                plan TEXT NOT NULL DEFAULT 'free' CHECK(plan IN ('free','team','firm','trial','professional','leadership')),
                created_at TEXT NOT NULL,
                created_by_user_id INTEGER,
                practice_area TEXT,
                firm_size TEXT,
                FOREIGN KEY (created_by_user_id) REFERENCES users(id) ON DELETE SET NULL
            )
            '''
        )
        practice_area_expr = 'practice_area' if has_practice_area else 'NULL AS practice_area'
        firm_size_expr = 'firm_size' if has_firm_size else 'NULL AS firm_size'
        c.execute(
            f'''
            INSERT INTO firms_new (id, name, plan, created_at, created_by_user_id, practice_area, firm_size)
            SELECT id, name, plan, created_at, created_by_user_id, {practice_area_expr}, {firm_size_expr}
            FROM firms
            '''
        )
        c.execute('DROP TABLE firms')
        c.execute('ALTER TABLE firms_new RENAME TO firms')
        c.execute('PRAGMA foreign_keys=ON')
        c.execute('PRAGMA table_info(firms)')
        firm_columns = [col[1] for col in c.fetchall()]
    _add_column_if_missing(
        firm_columns,
        'plan',
        "ALTER TABLE firms ADD COLUMN plan TEXT NOT NULL DEFAULT 'free'",
    )
    _add_column_if_missing(firm_columns, 'practice_area', 'ALTER TABLE firms ADD COLUMN practice_area TEXT')
    _add_column_if_missing(firm_columns, 'firm_size', 'ALTER TABLE firms ADD COLUMN firm_size TEXT')
    c.execute("UPDATE firms SET plan = 'team' WHERE LOWER(COALESCE(plan, '')) = 'professional'")
    c.execute("UPDATE firms SET plan = 'firm' WHERE LOWER(COALESCE(plan, '')) = 'leadership'")
    c.execute("UPDATE firms SET plan = 'free' WHERE LOWER(COALESCE(plan, '')) = 'trial'")
    c.execute(
        '''
        UPDATE firms
        SET plan = 'free'
        WHERE plan IS NULL OR LOWER(plan) NOT IN ('free', 'team', 'firm')
        '''
    )
    c.execute(
        '''
        CREATE TABLE IF NOT EXISTS alerts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            firm_id INTEGER NOT NULL,
            report_id INTEGER,
            signal_type TEXT NOT NULL,
            message TEXT NOT NULL,
            occurrences INTEGER NOT NULL DEFAULT 0,
            status TEXT NOT NULL DEFAULT 'active',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            UNIQUE(firm_id, report_id, signal_type),
            FOREIGN KEY (firm_id) REFERENCES firms(id) ON DELETE CASCADE,
            FOREIGN KEY (report_id) REFERENCES reports(id) ON DELETE SET NULL
        )
        '''
    )


    # Align all legacy trial limits to the current free plan allowance.

    c.execute(
        'UPDATE users SET trial_limit = ? WHERE trial_limit IS NULL OR trial_limit != ?',
        (FREE_PLAN_REPORT_LIMIT, FREE_PLAN_REPORT_LIMIT),
    )

    # Backfill email_verified from legacy verification markers.
    c.execute(
        '''
        UPDATE users
        SET email_verified = CASE
            WHEN COALESCE(email_verified, 0) = 1 THEN 1
            WHEN COALESCE(is_verified, 0) = 1 THEN 1
            WHEN EXISTS (
                SELECT 1
                FROM user_email_verification uev
                WHERE uev.user_id = users.id
                  AND uev.verified_at IS NOT NULL
            ) THEN 1
            ELSE 0
        END
        '''
    )


    # Trial usage should be monotonic: never drop below trial reports already generated.

    c.execute(

        '''

        UPDATE users

        SET trial_reviews_used = (

            CASE

                WHEN COALESCE(trial_reviews_used, 0) > COALESCE(

                    (

                        SELECT COUNT(*)

                        FROM reports r

                        WHERE r.user_id = users.id

                          AND r.subscription_type_at_creation = 'trial'

                    ),

                    0

                )

                THEN COALESCE(trial_reviews_used, 0)

                ELSE COALESCE(

                    (

                        SELECT COUNT(*)

                        FROM reports r

                        WHERE r.user_id = users.id

                          AND r.subscription_type_at_creation = 'trial'

                    ),

                    0

                )

            END

        )

        '''

    )



    # Firm workspace backfill: each existing user becomes owner of a firm-of-one.

    now_iso = datetime.now(timezone.utc).isoformat()

    c.execute('SELECT id, firm_name FROM users ORDER BY id')

    user_rows = c.fetchall()

    user_to_firm = {}

    for row in user_rows:

        user_id = int(row[0])

        firm_name = (str(row[1]).strip() if row[1] else '') or 'Firm'



        c.execute(

            '''

            SELECT firm_id

            FROM firm_users

            WHERE user_id = ? AND status = 'active'

            ORDER BY id ASC

            LIMIT 1

            ''',

            (user_id,),

        )

        membership = c.fetchone()

        if membership:

            firm_id = int(membership[0])

        else:

            c.execute(

                '''

                INSERT INTO firms (name, created_at, created_by_user_id)

                VALUES (?, ?, ?)

                ''',

                (firm_name, now_iso, user_id),

            )

            firm_id = int(c.lastrowid)

            c.execute(

                '''

                INSERT OR IGNORE INTO firm_users (

                    firm_id, user_id, role, status, invited_by_user_id, invited_at, joined_at

                )

                VALUES (?, ?, 'owner', 'active', ?, ?, ?)

                ''',

                (firm_id, user_id, user_id, now_iso, now_iso),

            )



        user_to_firm[user_id] = firm_id

        c.execute(

            '''

            UPDATE firms

            SET name = COALESCE(NULLIF(name, ''), ?)

            WHERE id = ?

            ''',

            (firm_name, firm_id),

        )

        c.execute(

            '''

            UPDATE firm_users

            SET role = CASE WHEN role NOT IN ('owner','partner','member') THEN 'owner' ELSE role END

            WHERE firm_id = ? AND user_id = ?

            ''',

            (firm_id, user_id),

        )



    # Backfill governance resource firm bindings.

    for user_id, firm_id in user_to_firm.items():

        c.execute(

            '''

            UPDATE reports

            SET firm_id = ?, created_by_user_id = COALESCE(created_by_user_id, user_id)

            WHERE user_id = ? AND firm_id IS NULL

            ''',

            (firm_id, user_id),

        )

        c.execute(

            '''

            UPDATE report_action_items

            SET firm_id = ?,

                created_by_user_id = COALESCE(created_by_user_id, user_id),

                updated_by_user_id = COALESCE(updated_by_user_id, user_id)

            WHERE user_id = ? AND firm_id IS NULL

            ''',

            (firm_id, user_id),

        )



    # Create default admin user if not exists

    c.execute('SELECT id FROM users WHERE username = ?', (app.config['ADMIN_USERNAME'],))

    admin_row = c.fetchone()

    if not admin_row:

        password_hash = generate_password_hash(app.config['ADMIN_PASSWORD'])

        c.execute(

            '''INSERT INTO users

               (email, username, password_hash, is_verified, created_at)

               VALUES (?, ?, ?, 1, ?)''',

            (

                app.config['ADMIN_EMAIL'],

                app.config['ADMIN_USERNAME'],

                password_hash,

                datetime.utcnow().isoformat(),

            ),

        )

        admin_user_id = c.lastrowid

    else:

        admin_user_id = admin_row[0]



    # Ensure default admin has reasonable SaaS fields populated

    c.execute(

        '''

        UPDATE users

        SET email = COALESCE(email, ?),

            firm_name = COALESCE(firm_name, ?),

            trial_limit = COALESCE(trial_limit, ?),

            subscription_status = COALESCE(subscription_status, 'trial'),

            subscription_type = COALESCE(subscription_type, 'trial')

        WHERE username = ?

        ''',

        (

            f"{app.config['ADMIN_USERNAME']}@example.com",

            app.config['FIRM_NAME'],

            FREE_PLAN_REPORT_LIMIT,

            app.config['ADMIN_USERNAME'],

        ),

    )



    # Performance indexes

    c.execute('CREATE INDEX IF NOT EXISTS idx_users_email ON users(email)')

    c.execute('CREATE INDEX IF NOT EXISTS idx_reports_user_id ON reports(user_id)')

    c.execute('CREATE INDEX IF NOT EXISTS idx_reports_firm_id ON reports(firm_id)')

    c.execute('CREATE INDEX IF NOT EXISTS idx_reports_user_hash ON reports(user_id, report_hash)')

    c.execute('CREATE INDEX IF NOT EXISTS idx_reports_user_deleted_at ON reports(user_id, deleted_at)')

    c.execute('CREATE INDEX IF NOT EXISTS idx_reports_firm_deleted_at ON reports(firm_id, deleted_at)')

    c.execute('CREATE INDEX IF NOT EXISTS idx_report_pdf_artifacts_user_id ON report_pdf_artifacts(user_id)')

    c.execute('CREATE INDEX IF NOT EXISTS idx_actions_user_report ON report_action_items(user_id, report_id)')
    c.execute('CREATE INDEX IF NOT EXISTS idx_actions_firm_report ON report_action_items(firm_id, report_id)')
    c.execute('CREATE INDEX IF NOT EXISTS idx_governance_signals_report ON governance_signals(report_id)')
    c.execute('CREATE INDEX IF NOT EXISTS idx_governance_recommendations_report ON governance_recommendations(report_id)')
    c.execute('CREATE INDEX IF NOT EXISTS idx_alerts_firm_status_created ON alerts(firm_id, status, created_at DESC)')
    c.execute('CREATE INDEX IF NOT EXISTS idx_actions_owner_user ON report_action_items(owner_user_id)')

    c.execute('CREATE INDEX IF NOT EXISTS idx_actions_status ON report_action_items(status)')

    c.execute('CREATE INDEX IF NOT EXISTS idx_reviews_created_at ON reviews(created_at)')

    c.execute('CREATE INDEX IF NOT EXISTS idx_ownership_user_id ON review_ownership(user_id)')

    c.execute('CREATE INDEX IF NOT EXISTS idx_firm_users_user_status ON firm_users(user_id, status)')

    c.execute('CREATE INDEX IF NOT EXISTS idx_firm_users_firm_status ON firm_users(firm_id, status)')

    c.execute('CREATE INDEX IF NOT EXISTS idx_governance_briefs_firm_created ON governance_briefs(firm_id, created_at DESC)')

    c.execute('CREATE INDEX IF NOT EXISTS idx_audit_log_firm_created ON audit_log(firm_id, created_at DESC)')

    c.execute('CREATE INDEX IF NOT EXISTS idx_interest_events_firm_created ON interest_events(firm_id, created_at DESC)')

    c.execute('CREATE INDEX IF NOT EXISTS idx_feature_interest_key_choice ON feature_interest(feature_key, choice)')

    c.execute('CREATE INDEX IF NOT EXISTS idx_2fa_challenges_user_id ON two_factor_challenges(user_id)')

    c.execute('CREATE INDEX IF NOT EXISTS idx_branding_user_id ON account_branding(user_id)')

    c.execute(

        'CREATE INDEX IF NOT EXISTS idx_security_events_user_created '

        'ON security_events(user_id, created_at DESC)'

    )

    c.execute(

        'CREATE INDEX IF NOT EXISTS idx_security_events_type_created '

        'ON security_events(event_type, created_at DESC)'

    )

    # PR7 / F9 / F13: indexes for the heaviest per-user queries.

    # (user_id, deleted_at, created_at) � dashboard stats + reports list ORDER BY created_at DESC

    c.execute(

        'CREATE INDEX IF NOT EXISTS idx_reports_user_active_created '

        'ON reports(user_id, deleted_at, created_at)'

    )

    # (user_id, report_id, created_at) � action-items list ORDER BY created_at DESC

    c.execute(

        'CREATE INDEX IF NOT EXISTS idx_actions_user_report_created '

        'ON report_action_items(user_id, report_id, created_at)'

    )

    # (user_id, status, due_date) � execution-summary aggregation on due_date ranges

    c.execute(

        'CREATE INDEX IF NOT EXISTS idx_actions_user_status_due '

        'ON report_action_items(user_id, status, due_date)'

    )

    # (user_id, review_id) covering index � review_ownership join in analyze_reviews()

    c.execute(

        'CREATE INDEX IF NOT EXISTS idx_ownership_user_review '

        'ON review_ownership(user_id, review_id)'

    )



    # Backfill ownership for legacy records to default admin owner

    c.execute(

        '''

        INSERT OR IGNORE INTO review_ownership (review_id, user_id)

        SELECT id, ? FROM reviews

        ''',

        (admin_user_id,),

    )



    conn.commit()

    conn.close()





# Initialize the database at module load time.

# This runs under Gunicorn (production) AND `python app.py` (local dev) because

# it executes whenever the module is imported G�� not just inside __main__.

# All CREATE TABLE statements use IF NOT EXISTS and all ALTER TABLE calls

# check for column existence first, so this is fully idempotent and safe to

# run on every startup against an already-populated database.

with app.app_context():

    try:

        init_db()

        app.logger.info('[clarion:startup] init_db() completed successfully')

    except Exception as _init_db_exc:

        import traceback as _tb

        app.logger.error('[clarion:startup] FATAL: init_db() failed: %s', _init_db_exc)

        app.logger.error('[clarion:startup] %s', _tb.format_exc())

        raise




_partner_brief_scheduler = None


def _brief_email_day():
    """Resolve BRIEF_EMAIL_DAY into a safe monthly day value (1-28)."""
    raw_value = str(os.environ.get('BRIEF_EMAIL_DAY', '1')).strip()
    try:
        day = int(raw_value)
    except Exception:  # noqa: BLE001
        day = 1
    if day < 1:
        day = 1
    if day > 28:
        app.logger.warning('BRIEF_EMAIL_DAY=%s is above 28; clamping to 28 for monthly scheduler safety.', raw_value)
        day = 28
    return day


def _build_monthly_partner_brief_payload(c, firm_id, firm_name):
    c.execute(
        '''
        SELECT id, created_at, avg_rating, themes, top_complaints, custom_name
        FROM reports
        WHERE firm_id = ?
          AND deleted_at IS NULL
        ORDER BY created_at DESC
        LIMIT 1
        ''',
        (firm_id,),
    )
    latest_report = c.fetchone()
    if not latest_report:
        return None

    report_id = int(latest_report[0])
    report_name = _effective_report_name(report_id, latest_report[1], latest_report[5])
    raw_themes = _deserialize_report_data(latest_report[3], {}) or {}
    ordered_themes = sorted(
        [{'name': str(name), 'mentions': int(mentions)} for name, mentions in raw_themes.items()],
        key=lambda item: item['mentions'],
        reverse=True,
    )
    top_issue = ordered_themes[0]['name'] if ordered_themes else 'No dominant issue identified yet'

    raw_top_complaints = _deserialize_report_data(latest_report[4], []) or []
    example_quote = ''
    for item in raw_top_complaints:
        if isinstance(item, str) and item.strip():
            example_quote = item.strip()
            break
        if isinstance(item, dict):
            candidate = str(item.get('review_text') or '').strip()
            if candidate:
                example_quote = candidate
                break

    recommended_discussion = (
        f'Review ownership and next-step actions for "{top_issue}" before the next partner meeting.'
        if top_issue != 'No dominant issue identified yet'
        else 'Review current client issues and confirm assigned action ownership.'
    )

    avg_rating = latest_report[2]
    avg_rating_display = 'Not available'
    if avg_rating is not None:
        avg_rating_display = f'{float(avg_rating):.2f} / 5'

    base_url = (os.environ.get('APP_BASE_URL') or '').rstrip('/')
    dashboard_url = f'{base_url}/dashboard/reports/{report_id}' if base_url else ''

    return {
        'firm_name': firm_name or app.config.get('FIRM_NAME'),
        'report_name': report_name,
        'average_rating': avg_rating_display,
        'top_issue': top_issue,
        'example_quote': example_quote or 'No client quote available yet.',
        'recommended_discussion': recommended_discussion,
        'generated_at': datetime.utcnow().strftime('%b %d, %Y %H:%M UTC'),
        'dashboard_url': dashboard_url,
    }


def _run_monthly_partner_brief_email_job():
    """Scheduled monthly fan-out of the latest governance brief via Resend."""
    with app.app_context():
        resend_api_key = (os.environ.get('RESEND_API_KEY') or '').strip()
        if not resend_api_key:
            app.logger.warning('Monthly partner brief email job skipped: RESEND_API_KEY missing.')
            return

        recipients = parse_partner_email_list(os.environ.get('PARTNER_EMAILS') or '')
        if not recipients:
            app.logger.warning('Monthly partner brief email job skipped: PARTNER_EMAILS missing/invalid.')
            return

        from_email = _resolve_from_email()
        conn = db_connect()
        c = conn.cursor()
        c.execute('SELECT id, name FROM firms ORDER BY id ASC')
        firm_rows = c.fetchall() or []

        total_emails_sent = 0
        firms_processed = 0
        for firm_row in firm_rows:
            firm_id = int(firm_row[0])
            firm_name = str(firm_row[1] or '').strip()
            payload = _build_monthly_partner_brief_payload(c, firm_id, firm_name)
            if not payload:
                continue

            subject = f'Clarion Partner Brief: {payload["report_name"]}'
            html = build_partner_brief_html(payload)
            try:
                emails_sent = send_partner_brief_via_resend(
                    api_key=resend_api_key,
                    recipients=recipients,
                    subject=subject,
                    html=html,
                    from_email=from_email,
                )
                total_emails_sent += int(emails_sent)
                firms_processed += 1
            except Exception:  # noqa: BLE001
                app.logger.exception('Monthly partner brief email failed for firm_id=%s.', firm_id)

        conn.close()
        app.logger.info(
            'Monthly partner brief job finished firms_processed=%s emails_sent=%s',
            firms_processed,
            total_emails_sent,
        )


def _start_monthly_partner_brief_scheduler():
    """Start APScheduler cron job for monthly partner brief delivery."""
    global _partner_brief_scheduler

    if _partner_brief_scheduler is not None:
        return

    enabled = str(os.environ.get('BRIEF_EMAIL_SCHEDULER_ENABLED', '1')).strip().lower() not in ('0', 'false', 'no')
    if not enabled:
        app.logger.info('Monthly partner brief scheduler disabled by BRIEF_EMAIL_SCHEDULER_ENABLED.')
        return

    if app.config.get('TESTING'):
        app.logger.info('Monthly partner brief scheduler disabled in testing mode.')
        return

    if app.config.get('DEBUG') and os.environ.get('WERKZEUG_RUN_MAIN') != 'true':
        # Prevent duplicate scheduler startup under Flask debug reloader.
        return

    if not APSCHEDULER_AVAILABLE:
        app.logger.warning('APScheduler unavailable; monthly partner brief email scheduler not started.')
        return

    tz_name = os.environ.get('FIRM_TIMEZONE', 'America/Chicago')
    scheduler = BackgroundScheduler(timezone=tz_name)
    day = _brief_email_day()
    scheduler.add_job(
        _run_monthly_partner_brief_email_job,
        trigger=CronTrigger(day=day, hour=9, minute=0),
        id='monthly_partner_brief_email',
        replace_existing=True,
        max_instances=1,
        coalesce=True,
        misfire_grace_time=60 * 60,
    )
    scheduler.start()
    _partner_brief_scheduler = scheduler
    app.logger.info('Monthly partner brief scheduler started day=%s timezone=%s', day, tz_name)


try:
    _start_monthly_partner_brief_scheduler()
    start_weekly_scheduler()
    app.logger.info('[clarion:startup] schedulers started successfully')
except Exception as _sched_exc:
    import traceback as _tb2
    app.logger.error('[clarion:startup] WARNING: scheduler startup failed (non-fatal): %s', _sched_exc)
    app.logger.error('[clarion:startup] %s', _tb2.format_exc())
# ===== USER CLASS FOR FLASK-LOGIN =====



class User(UserMixin):

    def __init__(

        self,

        id,

        username,

        is_admin=True,

        email=None,

        firm_name=None,

        stripe_customer_id=None,

        stripe_subscription_id=None,

        subscription_status='trial',

        trial_reviews_used=0,

        trial_limit=None,

        one_time_reports_purchased=0,

        one_time_reports_used=0,

        subscription_type='trial',

        trial_month=None,

        trial_review_limit_per_report=50,

        two_factor_enabled=0,
        two_factor_method='email',
        email_verified=0,
        onboarding_complete=0,
    ):
        self.id = id

        self.username = username

        self.is_admin = bool(is_admin)

        # SaaS identity fields

        self.email = email

        self.firm_name = firm_name or app.config['FIRM_NAME']



        # Stripe subscription + customer fields

        self.stripe_customer_id = stripe_customer_id

        self.stripe_subscription_id = stripe_subscription_id

        self.subscription_status = subscription_status or 'trial'

        self.subscription_type = subscription_type or 'trial'



        # Usage tracking

        self.trial_reviews_used = trial_reviews_used or 0

        self.trial_limit = trial_limit or FREE_PLAN_REPORT_LIMIT

        if self.trial_limit != FREE_PLAN_REPORT_LIMIT:

            self.trial_limit = FREE_PLAN_REPORT_LIMIT

        self.one_time_reports_purchased = one_time_reports_purchased or 0

        self.one_time_reports_used = one_time_reports_used or 0



        # Legacy fields (kept for compatibility, not used in new logic)

        self.trial_month = trial_month

        self.trial_review_limit_per_report = trial_review_limit_per_report or 50

        self.two_factor_enabled = bool(two_factor_enabled)
        self.two_factor_method = two_factor_method or 'email'
        self.email_verified = bool(email_verified)
        self.onboarding_complete = bool(onboarding_complete)


    # ===== PRICING / ACCOUNT HELPERS =====



    def has_active_subscription(self):

        """Return True if the user has an active Stripe subscription."""

        return self.subscription_status == 'active'



    def has_unused_one_time_reports(self):

        return self.one_time_reports_purchased > self.one_time_reports_used



    def get_remaining_one_time_reports(self):

        return max(0, self.one_time_reports_purchased - self.one_time_reports_used)



    def is_trial_expired(self):

        trial_usage, trial_limit = _get_trial_usage_count(self.id, self.trial_limit)

        return trial_usage >= trial_limit



    def can_generate_report(self):

        """

        Tiered logic:

        Priority: subscription G�� one-time G�� trial

        """

        return (

            self.has_active_subscription()

            or self.has_unused_one_time_reports()

            or not self.is_trial_expired()

        )



    def get_account_status(self):

        """Return a dict describing the current account status for UI."""

        if self.has_active_subscription():

            return {

                'type': self.subscription_type,

                'display': f'Unlimited ({self.subscription_type.title()} Subscription)',

                'remaining': None,

            }

        elif self.has_unused_one_time_reports():

            remaining = self.get_remaining_one_time_reports()

            return {

                'type': 'onetime',

                'display': f'Free: {remaining} reports remaining',

                'remaining': remaining,

            }

        else:

            trial_usage, trial_limit = _get_trial_usage_count(self.id, self.trial_limit)

            remaining = max(0, trial_limit - trial_usage)

            return {

                'type': 'trial',

                'display': f'Free: {remaining}/{trial_limit} remaining this month',

                'remaining': remaining,

                'trial_limit': trial_limit,

            }





def _resolve_user_active_firm_id(c, user_id):

    c.execute(

        '''

        SELECT firm_id

        FROM firm_users

        WHERE user_id = ?

          AND status = 'active'

        ORDER BY id ASC

        LIMIT 1

        ''',

        (user_id,),

    )

    row = c.fetchone()

    return int(row[0]) if row else None





def _resolve_current_firm_context():

    if not current_user.is_authenticated:

        raise PermissionError('Not authenticated')

    conn = db_connect()

    c = conn.cursor()

    c.execute(

        '''

        SELECT fu.firm_id, fu.role, fu.status, f.name

        FROM firm_users fu

        INNER JOIN firms f ON f.id = fu.firm_id

        WHERE fu.user_id = ?

          AND fu.status = 'active'

        ORDER BY fu.id ASC

        ''',

        (current_user.id,),

    )

    rows = c.fetchall()

    conn.close()

    if not rows:

        raise PermissionError('No active firm membership for current user.')

    if len(rows) > 1:

        raise RuntimeError('Multiple active firm memberships detected; explicit firm selection is required.')

    row = rows[0]

    return {

        'firm_id': int(row[0]),

        'role': str(row[1]),

        'status': str(row[2]),

        'firm_name': str(row[3] or ''),

    }





def _require_firm_context():
    try:
        return _resolve_current_firm_context(), None
    except PermissionError as exc:
        return None, (jsonify({'success': False, 'error': str(exc)}), 403)
    except RuntimeError as exc:
        return None, (jsonify({'success': False, 'error': str(exc)}), 409)


def get_firm_plan(firm_id):
    return plan_service.get_firm_plan(firm_id, db_connect)


def _set_firm_plan_for_user(c, user_id, plan):
    normalized = str(plan or FIRM_PLAN_FREE).strip().lower()
    plan_aliases = {
        FIRM_PLAN_TRIAL: FIRM_PLAN_FREE,
        FIRM_PLAN_PROFESSIONAL: FIRM_PLAN_TEAM,
        FIRM_PLAN_LEADERSHIP: FIRM_PLAN_FIRM,
        "monthly": FIRM_PLAN_TEAM,
        "annual": FIRM_PLAN_FIRM,
    }
    target_plan = plan_aliases.get(normalized, normalized)
    if target_plan not in {FIRM_PLAN_FREE, FIRM_PLAN_TEAM, FIRM_PLAN_FIRM}:
        target_plan = FIRM_PLAN_FREE
    c.execute(
        '''
        UPDATE firms
        SET plan = ?
        WHERE id IN (
            SELECT firm_id
            FROM firm_users
            WHERE user_id = ?
              AND status = 'active'
        )
        ''',
        (target_plan, user_id),
    )


def _get_plan_limits(plan):
    normalized = str(plan or FIRM_PLAN_FREE).strip().lower()
    limits = PLAN_LIMITS.get(normalized) or PLAN_LIMITS.get(FIRM_PLAN_FREE) or {}
    return {
        "max_reviews_per_upload": limits.get("max_reviews_per_upload"),
        "max_reports_per_month": limits.get("max_reports_per_month"),
        "max_users": limits.get("max_users"),
        "history_days": limits.get("history_days"),
        "pdf_watermark": bool(limits.get("pdf_watermark", False)),
    }


def _report_history_window_days_for_plan(plan):
    limits = _get_plan_limits(plan)
    return limits.get("history_days")


def _report_history_metadata(plan):
    window_days = _report_history_window_days_for_plan(plan)
    if window_days is None:
        return {
            "history_window_days": None,
            "history_truncated": False,
            "history_notice": None,
        }
    if window_days == 90:
        notice = (
            "Your current plan shows the last 90 days of governance history. "
            "Upgrade to unlock full historical intelligence."
        )
    else:
        notice = (
            "Your current plan shows the last 12 months of governance history. "
            "Upgrade to unlock full historical intelligence."
        )
    return {
        "history_window_days": window_days,
        "history_truncated": True,
        "history_notice": notice,
    }


def _report_history_cutoff_iso(plan):
    window_days = _report_history_window_days_for_plan(plan)
    if window_days is None:
        return None
    cutoff_dt = datetime.now(timezone.utc) - timedelta(days=window_days)
    return cutoff_dt.isoformat()


def _to_utc_datetime(value):
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _enforce_report_history_access(report_created_at, firm_id):
    """Enforce historical intelligence access window for a firm/report timestamp."""
    firm_plan = get_firm_plan(firm_id)
    history_meta = _report_history_metadata(firm_plan)
    result = plan_service.enforce_history_access(firm_id, report_created_at, db_connect)
    if result:
        return (
            jsonify(
                {
                    'success': False,
                    'error': 'Report outside plan history window',
                    **history_meta,
                }
            ),
            403,
        ), history_meta
    return None, history_meta


def _plan_limit_error(message):
    return jsonify({'error': 'plan_limit', 'message': message}), 403


def _monthly_report_count_for_firm(firm_id, now_utc=None):
    now_utc = now_utc or datetime.now(timezone.utc)
    month_start = datetime(now_utc.year, now_utc.month, 1, tzinfo=timezone.utc).isoformat()
    conn = db_connect()
    c = conn.cursor()
    c.execute(
        '''
        SELECT COUNT(*)
        FROM reports
        WHERE firm_id = ?
          AND deleted_at IS NULL
          AND created_at >= ?
        ''',
        (int(firm_id), month_start),
    )
    count = int(c.fetchone()[0] or 0)
    conn.close()
    return count


def _enforce_report_generation_limit(firm_id, plan):
    result = plan_service.enforce_monthly_report_limit(firm_id, db_connect)
    if result:
        return _plan_limit_error(result.get("message") or "Plan monthly report limit reached.")
    return None


def _enforce_upload_review_limit(valid_rows, plan):
    del plan  # Plan is derived server-side from firm_id in plan_service.
    firm_ctx, err = _require_firm_context()
    if err:
        return err
    result = plan_service.enforce_upload_limit(firm_ctx['firm_id'], len(valid_rows), db_connect)
    if result:
        return _plan_limit_error(result.get("message") or "Plan upload review limit reached.")
    return None


def _pdf_export_context_for_plan(plan):
    limits = _get_plan_limits(plan)
    watermark_required = bool(limits.get("pdf_watermark", False))
    if watermark_required:
        return {
            "is_paid_user": False,
            "access_level": "trial",
            "plan_type": "free",
        }
    if str(plan).lower() == FIRM_PLAN_FIRM:
        plan_type = "pro_annual"
    else:
        plan_type = "pro_monthly"
    return {
        "is_paid_user": True,
        "access_level": "paid",
        "plan_type": plan_type,
    }


def _is_owner(role):
    return role == 'owner'




def _is_partner_or_owner(role):

    return role in {'owner', 'partner'}





def _can_export_governance_brief(role):

    return role in {'owner', 'partner'}





def _can_assign_actions(role):

    return role in {'owner', 'partner'}





def _can_delete_reports(role):

    return role == 'owner'





def _can_mutate_action(role, actor_user_id, action_owner_user_id):

    if role in {'owner', 'partner'}:

        return True

    if role != 'member':

        return False

    if action_owner_user_id is None:

        return False

    return int(action_owner_user_id) == int(actor_user_id)





def _log_audit_event(conn, firm_id, actor_user_id, entity_type, entity_id, event_type, before_dict=None, after_dict=None):

    before_json = json.dumps(before_dict or {}, separators=(',', ':'), ensure_ascii=False)

    after_json = json.dumps(after_dict or {}, separators=(',', ':'), ensure_ascii=False)

    now_iso = datetime.now(timezone.utc).isoformat()

    c = conn.cursor()

    c.execute(

        '''

        INSERT INTO audit_log (

            firm_id, actor_user_id, entity_type, entity_id, event_type, before_json, after_json, created_at

        )

        VALUES (?, ?, ?, ?, ?, ?, ?, ?)

        ''',

        (int(firm_id), int(actor_user_id), str(entity_type), int(entity_id), str(event_type), before_json, after_json, now_iso),

    )





def _resolve_action_owner_assignment(c, firm_id, owner_user_id_raw, owner_text_raw):

    owner_user_id = None

    owner_text = bleach.clean((owner_text_raw or '').strip(), strip=True)

    if owner_user_id_raw is not None:

        try:

            candidate = int(owner_user_id_raw)

        except (TypeError, ValueError):

            raise ValueError('owner_user_id must be an integer.')

        c.execute(

            '''

            SELECT u.id, COALESCE(NULLIF(u.email, ''), u.username)

            FROM firm_users fu

            INNER JOIN users u ON u.id = fu.user_id

            WHERE fu.firm_id = ?

              AND fu.user_id = ?

              AND fu.status = 'active'

            ''',

            (int(firm_id), candidate),

        )

        member = c.fetchone()

        if not member:

            raise ValueError('owner_user_id must reference an active member in this firm.')

        owner_user_id = int(member[0])

        owner_text = str(member[1] or '').strip()

    if owner_user_id is None and not owner_text:

        owner_text = 'Unassigned (requires assignment)'

    return owner_user_id, owner_text



# ===== ANALYSIS FUNCTIONS =====



def analyze_reviews():

    """

    Analyze reviews owned by the current authenticated user.

    Returns empty result set if called without an authenticated user context.

    F16/PR6: anonymous branch removed � unscoped global reads are not permitted.

    """

    # F16/PR6: hard guard � never return cross-user data to an anonymous caller.

    if current_user.is_anonymous:

        return {

            'total_reviews': 0,

            'avg_rating': 0,

            'themes': {},

            'top_praise': [],

            'top_complaints': [],

            'all_reviews': [],

        }



    conn = db_connect()

    c = conn.cursor()

    c.execute(

        '''

        SELECT r.date, r.rating, r.review_text

        FROM reviews r

        INNER JOIN review_ownership ro ON ro.review_id = r.id

        WHERE ro.user_id = ?

        ORDER BY r.created_at DESC

        ''',

        (current_user.id,),

    )

    reviews = [

        {'date': row[0], 'rating': row[1], 'review_text': row[2]}

        for row in c.fetchall()

    ]

    conn.close()



    if not reviews:

        return {

            'total_reviews': 0,

            'avg_rating': 0,

            'themes': {},

            'top_praise': [],

            'top_complaints': [],

            'all_reviews': []

        }



    # Apply per-plan analysis cap: free plan = first 30 reviews only.

    analysis_reviews = reviews

    if not current_user.has_active_subscription() and not current_user.has_unused_one_time_reports():

        analysis_reviews = reviews[:FREE_PLAN_MAX_REVIEWS_PER_REPORT]



    total_reviews = len(analysis_reviews)

    avg_rating = sum(r['rating'] for r in analysis_reviews) / total_reviews



    theme_keywords = {

        'Communication': ['communication', 'responsive', 'returned calls', 'kept me informed', 'updates', 'contact'],

        'Professionalism': ['professional', 'courteous', 'respectful', 'polite', 'demeanor', 'ethical'],

        'Legal Expertise': ['knowledgeable', 'experienced', 'expert', 'skilled', 'competent', 'expertise'],

        'Case Outcome': ['won', 'successful', 'settlement', 'verdict', 'result', 'outcome', 'resolved'],

        'Cost/Value': ['expensive', 'affordable', 'fees', 'billing', 'cost', 'worth it', 'value', 'price'],

        'Responsiveness': ['quick', 'slow', 'delayed', 'waiting', 'timely', 'immediately', 'promptly'],

        'Compassion': ['caring', 'understanding', 'empathetic', 'compassionate', 'listened', 'supportive'],

        'Staff Support': ['staff', 'assistant', 'paralegal', 'secretary', 'team', 'office'],

    }



    theme_counts = Counter()

    for review in analysis_reviews:

        text_lower = review['review_text'].lower()

        for theme, keywords in theme_keywords.items():

            if any(keyword in text_lower for keyword in keywords):

                theme_counts[theme] += 1



    top_praise = [r for r in analysis_reviews if r['rating'] >= 4][:10]

    top_complaints = [r for r in analysis_reviews if r['rating'] <= 2][:10]



    return {

        'total_reviews': total_reviews,

        'avg_rating': round(avg_rating, 2),

        'themes': dict(theme_counts.most_common(8)),

        'top_praise': top_praise,

        'top_complaints': top_complaints,

        'all_reviews': reviews  # keep full set for reference

    }





def _serialize_report_data(data):

    return json.dumps(data, ensure_ascii=False)





def _deserialize_report_data(data, fallback):

    if not data:

        return fallback

    try:

        return json.loads(data)

    except (TypeError, json.JSONDecodeError):

        return fallback





def _purge_expired_deleted_reports(user_id=None):

    conn = db_connect()

    c = conn.cursor()

    if user_id is None:

        c.execute(

            '''

            DELETE FROM reports

            WHERE deleted_at IS NOT NULL

              AND purge_at IS NOT NULL

              AND datetime(purge_at) <= datetime('now')

            '''

        )

    else:

        c.execute(

            '''

            DELETE FROM reports

            WHERE user_id = ?

              AND deleted_at IS NOT NULL

              AND purge_at IS NOT NULL

              AND datetime(purge_at) <= datetime('now')

            ''',

            (user_id,),

        )

    conn.commit()

    conn.close()





def _get_active_report_count(user_id):

    _purge_expired_deleted_reports(user_id)

    conn = db_connect()

    c = conn.cursor()

    c.execute(

        '''

        SELECT COUNT(*)

        FROM reports

        WHERE user_id = ?

          AND deleted_at IS NULL

        ''',

        (user_id,),

    )

    row = c.fetchone()

    conn.close()

    return int(row[0] or 0) if row else 0





def _build_report_hash(valid_rows):

    canonical_rows = []

    for row in valid_rows:

        date_value = str(row[0]).strip()

        rating_value = str(row[1]).strip()

        review_text = str(row[2]).strip()

        canonical_rows.append(f'{date_value}|{rating_value}|{review_text}')

    canonical_rows.sort()

    digest_source = '\n'.join(canonical_rows).encode('utf-8')

    return hashlib.sha256(digest_source).hexdigest()





def _find_duplicate_report_id(user_id, report_hash):

    if not report_hash:

        return None

    _purge_expired_deleted_reports(user_id)

    conn = db_connect()

    c = conn.cursor()

    firm_id = _resolve_user_active_firm_id(c, user_id)

    if firm_id is None:

        conn.close()

        return None

    c.execute(

        '''

        SELECT id

        FROM reports

        WHERE firm_id = ?

          AND report_hash = ?

          AND deleted_at IS NULL

        ORDER BY created_at DESC

        LIMIT 1

        ''',

        (firm_id, report_hash),

    )

    row = c.fetchone()

    conn.close()

    return int(row[0]) if row else None





def save_report_snapshot(user_id, report_access_type=None, report_hash=None):

    """Capture the current analysis view and store as a downloadable report snapshot."""

    analysis = analyze_reviews()

    if analysis['total_reviews'] == 0:

        return None



    subscription_type = report_access_type

    if not subscription_type:

        conn = db_connect()

        c = conn.cursor()

        c.execute('SELECT subscription_type FROM users WHERE id = ?', (user_id,))

        row = c.fetchone()

        subscription_type = row[0] if row else 'trial'



    conn = db_connect()

    c = conn.cursor()

    firm_id = _resolve_user_active_firm_id(c, user_id)

    if firm_id is None:

        conn.close()

        return None

    c.execute(
        '''
        INSERT INTO reports (
            user_id,

            firm_id,

            created_by_user_id,

            total_reviews,

            avg_rating,

            themes,

            top_praise,

            top_complaints,

            subscription_type_at_creation,

            report_hash

        )

        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)

        ''',

        (

            user_id,

            firm_id,

            user_id,

            analysis['total_reviews'],

            analysis['avg_rating'],

            _serialize_report_data(analysis['themes']),

            _serialize_report_data(analysis['top_praise']),

            _serialize_report_data(analysis['top_complaints']),

            subscription_type,

            report_hash,

        ),

    )

    report_id = c.lastrowid

    conn.commit()

    conn.close()

    return report_id





def _plan_badge_label(plan_type):

    labels = {

        'trial': 'Free',

        'onetime': 'Free',

        'monthly': 'Team',

        'annual': 'Firm',

    }

    return labels.get(plan_type or 'trial', 'Free')





def _report_display_name(report_id, created_at):

    dt = created_at

    if isinstance(created_at, str):

        try:

            dt = datetime.fromisoformat(created_at)

        except ValueError:

            dt = None

    if isinstance(dt, datetime):

        stamp = dt.strftime('%b %d')

    else:

        stamp = str(created_at)[:10] if created_at else 'Unknown Date'

    return f'Pricing Model Report - {stamp} (#{report_id})'





def _effective_report_name(report_id, created_at, custom_name=None):

    custom = str(custom_name or '').strip()

    if custom:

        return custom

    return _report_display_name(report_id, created_at)





def _current_trial_cycle_bounds(now_dt=None):

    current = now_dt or datetime.now(timezone.utc)

    start = current.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    if start.month == 12:

        end = start.replace(year=start.year + 1, month=1)

    else:

        end = start.replace(month=start.month + 1)

    return start, end





def _trial_cycle_next_reset_iso():

    _, end = _current_trial_cycle_bounds()

    return end.isoformat()





def _build_user_credit_snapshot(user_id):

    state = _get_current_user_state(user_id)

    if not state:

        return {

            'free_reports_remaining': 0,

            'free_reports_used': 0,

            'free_reports_limit': FREE_PLAN_REPORT_LIMIT,

            'paid_reports_remaining': 0,

            'paid_reports_used': 0,

            'paid_reports_purchased': 0,

            'has_active_subscription': False,

            'subscription_type': 'trial',

            'next_reset': None,

        }



    trial_usage_count, trial_limit = _get_trial_usage_count(user_id, state.get('trial_limit') or FREE_PLAN_REPORT_LIMIT)

    free_remaining = max(0, trial_limit - trial_usage_count)

    paid_remaining = max(0, state['one_time_reports_purchased'] - state['one_time_reports_used'])

    has_active_subscription = state['subscription_status'] == 'active'



    next_reset = _trial_cycle_next_reset_iso() if not has_active_subscription else None



    return {

        'free_reports_remaining': free_remaining,

        'free_reports_used': trial_usage_count,

        'free_reports_limit': trial_limit,

        'paid_reports_remaining': paid_remaining,

        'paid_reports_used': state['one_time_reports_used'],

        'paid_reports_purchased': state['one_time_reports_purchased'],

        'has_active_subscription': has_active_subscription,

        'subscription_type': state['subscription_type'],

        'next_reset': next_reset,

    }





def _get_current_user_state(user_id):

    conn = db_connect()

    c = conn.cursor()

    c.execute(

        '''

        SELECT subscription_status, subscription_type, one_time_reports_purchased, one_time_reports_used,

               trial_reviews_used, trial_limit, stripe_customer_id

        FROM users

        WHERE id = ?

        ''',

        (user_id,),

    )

    row = c.fetchone()

    conn.close()

    if not row:

        return None

    trial_limit = row[5] or FREE_PLAN_REPORT_LIMIT

    if trial_limit != FREE_PLAN_REPORT_LIMIT:

        trial_limit = FREE_PLAN_REPORT_LIMIT

    return {

        'subscription_status': row[0],

        'subscription_type': row[1] or 'trial',

        'one_time_reports_purchased': row[2] or 0,

        'one_time_reports_used': row[3] or 0,

        'trial_reviews_used': row[4] or 0,

        'trial_limit': trial_limit,

        'stripe_customer_id': row[6],

    }





def _account_plan_payload(user_id):

    state = _get_current_user_state(user_id)

    if not state:

        return {

            'plan_type': 'free',

            'plan_label': 'Free',

            'is_trial': True,

        }



    subscription_status = state.get('subscription_status') or 'trial'

    subscription_type = state.get('subscription_type') or 'trial'

    one_time_remaining = max(

        0,

        int(state.get('one_time_reports_purchased') or 0) - int(state.get('one_time_reports_used') or 0),

    )



    if subscription_status == 'active':

        if subscription_type == 'annual':

            return {'plan_type': 'pro_annual', 'plan_label': 'Firm', 'is_trial': False}

        if subscription_type == 'monthly':

            return {'plan_type': 'pro_monthly', 'plan_label': 'Team', 'is_trial': False}

    if one_time_remaining > 0:

        return {'plan_type': 'one_time', 'plan_label': 'Free', 'is_trial': False}

    return {'plan_type': 'free', 'plan_label': 'Free', 'is_trial': True}





def _normalize_branding_theme(theme_id):

    theme = (theme_id or BRANDING_THEME_DEFAULT).strip().lower()

    return theme if theme in BRANDING_THEME_PRESETS else BRANDING_THEME_DEFAULT





def _branding_theme_options():

    options = []

    for key, data in BRANDING_THEME_PRESETS.items():

        options.append(

            {

                'id': key,

                'label': data['label'],

                'accent_hex': data['accent'],

                'primary_hex': data['primary'],

                'surface_hex': data.get('surface', '#f8fafc'),

            }

        )

    return options





def _branding_logo_path(logo_filename):

    if not logo_filename:

        return None

    safe_name = os.path.basename(logo_filename)

    full_path = os.path.join(BRANDING_UPLOAD_DIR, safe_name)

    if not os.path.isfile(full_path):

        return None

    return full_path





def _delete_branding_logo_file(logo_filename):

    full_path = _branding_logo_path(logo_filename)

    if full_path and os.path.isfile(full_path):

        try:

            os.remove(full_path)

        except OSError:

            pass





def _get_account_branding(user_id):

    conn = db_connect()

    c = conn.cursor()

    c.execute(

        '''

        SELECT logo_filename, accent_theme, updated_at

        FROM account_branding

        WHERE user_id = ?

        ''',

        (user_id,),

    )

    row = c.fetchone()

    conn.close()



    logo_filename = row[0] if row else None

    accent_theme = _normalize_branding_theme(row[1] if row else BRANDING_THEME_DEFAULT)

    updated_at = row[2] if row else None

    logo_path = _branding_logo_path(logo_filename)

    has_logo = bool(logo_path)



    return {

        'accent_theme': accent_theme,

        'theme_options': _branding_theme_options(),

        'logo_filename': logo_filename if has_logo else None,

        'logo_path': logo_path,

        'logo_url': '/api/account/branding/logo' if has_logo else None,

        'has_logo': has_logo,

        'logo_updated_at': updated_at,

    }





def _save_account_branding(user_id, accent_theme=None, logo_filename=None, remove_logo=False):

    current = _get_account_branding(user_id)

    old_logo = current.get('logo_filename')

    next_theme = (

        _normalize_branding_theme(accent_theme)

        if accent_theme is not None

        else _normalize_branding_theme(current.get('accent_theme'))

    )

    next_logo = None if remove_logo else (logo_filename or old_logo)

    now_iso = datetime.utcnow().isoformat()



    conn = db_connect()

    c = conn.cursor()

    c.execute(

        '''

        INSERT INTO account_branding (user_id, logo_filename, accent_theme, updated_at)

        VALUES (?, ?, ?, ?)

        ON CONFLICT(user_id) DO UPDATE SET

            logo_filename = excluded.logo_filename,

            accent_theme = excluded.accent_theme,

            updated_at = excluded.updated_at

        ''',

        (user_id, next_logo, next_theme, now_iso),

    )

    conn.commit()

    conn.close()



    if old_logo and old_logo != next_logo:

        _delete_branding_logo_file(old_logo)



    return _get_account_branding(user_id)





def _branding_public_payload(branding):

    return {

        'accent_theme': branding.get('accent_theme', BRANDING_THEME_DEFAULT),

        'theme_options': branding.get('theme_options', _branding_theme_options()),

        'logo_url': branding.get('logo_url'),

        'has_logo': bool(branding.get('has_logo')),

        'logo_updated_at': branding.get('logo_updated_at'),

    }





def _get_report_trend_points(scope_id, limit=12):

    conn = db_connect()

    c = conn.cursor()

    c.execute(

        '''

        SELECT id, created_at, total_reviews, avg_rating

        FROM reports

        WHERE (firm_id = ? OR (firm_id IS NULL AND user_id = ?))

          AND deleted_at IS NULL

        ORDER BY created_at DESC

        LIMIT ?

        ''',

        (scope_id, scope_id, int(limit)),

    )

    rows = c.fetchall()

    conn.close()

    rows = list(reversed(rows))

    trend_points = []

    for row in rows:

        created_at = row[1]

        label = f'Report {row[0]}'

        if created_at:

            try:

                parsed = datetime.fromisoformat(str(created_at).replace('Z', '+00:00'))

                label = parsed.strftime('%b %d')

            except ValueError:

                label = str(created_at)[:10]

        trend_points.append(

            {

                'report_id': row[0],

                'created_at': created_at,

                'label': label,

                'total_reviews': int(row[2] or 0),

                'avg_rating': float(row[3] or 0.0),

            }

        )

    return trend_points





def _get_report_action_rows(scope_id, report_id, limit=20):
    conn = db_connect()

    c = conn.cursor()

    c.execute(

        '''

        SELECT title, owner, status, due_date, timeframe, kpi, notes, updated_at, owner_user_id, created_by_user_id, updated_by_user_id

        FROM report_action_items

        WHERE report_id = ?

          AND (firm_id = ? OR (firm_id IS NULL AND user_id = ?))

        ORDER BY

            CASE WHEN due_date IS NULL THEN 1 ELSE 0 END ASC,

            due_date ASC,

            updated_at DESC

        LIMIT ?

        ''',

        (report_id, scope_id, scope_id, int(limit)),

    )

    rows = c.fetchall()

    conn.close()

    return [
        {
            'title': row[0],
            'owner': row[1],
            'status': row[2],

            'due_date': row[3],

            'timeframe': row[4],

            'kpi': row[5],

            'notes': row[6],

            'updated_at': row[7],

            'owner_user_id': row[8],

            'created_by_user_id': row[9],

            'updated_by_user_id': row[10],

        }

        for row in rows
    ]


def _get_report_governance_insights(report_id, limit=5):
    """Load persisted governance signals/recommendations for a report."""
    conn = db_connect()
    c = conn.cursor()
    c.execute(
        '''
        SELECT title, description, severity, created_at
        FROM governance_signals
        WHERE report_id = ?
        ORDER BY CASE LOWER(COALESCE(severity, 'low'))
            WHEN 'high' THEN 3
            WHEN 'medium' THEN 2
            WHEN 'low' THEN 1
            ELSE 0
        END DESC, id ASC
        LIMIT ?
        ''',
        (report_id, int(limit)),
    )
    signal_rows = c.fetchall()
    c.execute(
        '''
        SELECT title, priority, suggested_owner, created_at
        FROM governance_recommendations
        WHERE report_id = ?
        ORDER BY CASE LOWER(COALESCE(priority, 'low'))
            WHEN 'high' THEN 3
            WHEN 'medium' THEN 2
            WHEN 'low' THEN 1
            ELSE 0
        END DESC, id ASC
        LIMIT ?
        ''',
        (report_id, int(limit)),
    )
    recommendation_rows = c.fetchall()
    conn.close()
    return {
        'signals': [
            {
                'title': str(row[0] or ''),
                'description': str(row[1] or ''),
                'severity': str(row[2] or 'low').lower(),
                'created_at': row[3],
            }
            for row in signal_rows
        ],
        'recommendations': [
            {
                'title': str(row[0] or ''),
                'priority': str(row[1] or 'low').lower(),
                'suggested_owner': str(row[2] or ''),
                'created_at': row[3],
            }
            for row in recommendation_rows
        ],
    }


def _safe_float_number(value, default=0.0):
    try:

        return float(value)

    except (TypeError, ValueError):

        return float(default)





def _safe_int_number(value, default=0):

    try:

        return int(value)

    except (TypeError, ValueError):

        return int(default)





def _parse_iso_dt(value):
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value).replace('Z', '+00:00'))
    except ValueError:
        return None


def _validate_action_due_date_local(due_date_value):
    """Validate action due dates using local server date semantics.

    Reject dates before today (server local date).
    """
    if not due_date_value:
        return None
    try:
        parsed = datetime.fromisoformat(str(due_date_value)).date()
    except ValueError:
        return 'Due date must be a valid ISO date.'

    if parsed < datetime.now().date():
        return 'Due date cannot be in the past.'
    return None


def _allow_past_due_date_for_e2e() -> bool:
    """Allow past due dates only for explicit local E2E smoke harness traffic.

    Guard rails (all required):
    - Request includes `X-E2E: 1`
    - App is in debug, or explicit override flag is enabled
    - Authenticated user matches configured E2E smoke identity
    """
    if request.headers.get('X-E2E') != '1':
        return False

    in_dev_or_flagged = bool(app.config.get('DEBUG')) or bool(
        app.config.get('ALLOW_PAST_DUE_DATES_FOR_E2E', False)
    )
    if not in_dev_or_flagged:
        return False

    if not getattr(current_user, 'is_authenticated', False):
        return False

    e2e_email = (os.environ.get('E2E_SMOKE_EMAIL') or 'smoke.e2e@clarion.local').strip().lower()
    user_email = (getattr(current_user, 'email', None) or '').strip().lower()
    user_username = (getattr(current_user, 'username', None) or '').strip().lower()
    return user_email == e2e_email or user_username == e2e_email


def _trend_stability_from_points_canonical(points):
    points = list(points or [])

    if len(points) < 3:

        return 'Insufficient data'

    scores = [_safe_float_number(point.get('avg_rating'), 0.0) for point in points if isinstance(point, dict)]

    scores = [score for score in scores if score > 0]

    if len(scores) < 3:

        return 'Insufficient data'

    spread = max(scores) - min(scores)

    if spread <= 0.25:

        return 'Stable'

    if spread <= 0.7:

        return 'Moderately stable'

    return 'Volatile'





def _at_risk_count_from_trend_points_canonical(points):

    points = list(points or [])

    if not points:

        return 0

    risk = 0

    prev = None

    for point in points:

        if not isinstance(point, dict):

            continue

        score = _safe_float_number(point.get('avg_rating'), 0.0)

        if score and score < 4.0:

            risk += 1

        if prev is not None and score and score < prev:

            risk += 1

        if score:

            prev = score

    return max(0, risk)





def _normalize_theme_rows_for_exposure(raw_themes):

    if not isinstance(raw_themes, dict):

        return []

    total_mentions = sum(_safe_int_number(val, 0) for val in raw_themes.values()) or 1

    rows = []

    for name, mentions in raw_themes.items():

        mentions_int = _safe_int_number(mentions, 0)

        rows.append(

            {

                'name': str(name or '').strip() or 'Uncategorized',

                'mentions': mentions_int,

                'percentage': (mentions_int / total_mentions) * 100.0,

            }

        )

    return rows





def _reports_has_column(c, column_name):

    c.execute('PRAGMA table_info(reports)')

    columns = {str(row[1]) for row in c.fetchall()}

    return column_name in columns





def _resolve_latest_exposure_subject(c, firm_id):

    """

    Canonical "latest" resolver for exposure status.

    Preferred: if reports.snapshot_id and a snapshot table with generated_at exist, order by generated_at.

    Fallback: order by reports.created_at DESC. In this codebase, each reports row is the generated snapshot record,

    so created_at is the governance-state timestamp when dedicated snapshot linkage is unavailable.

    """

    snapshot_table = None

    has_snapshot_id = _reports_has_column(c, 'snapshot_id')

    if has_snapshot_id:

        for candidate in ('report_snapshots', 'snapshots'):

            c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name = ?", (candidate,))

            found = c.fetchone()

            if not found:

                continue

            c.execute(f'PRAGMA table_info({candidate})')

            snapshot_columns = {str(row[1]) for row in c.fetchall()}

            if 'id' in snapshot_columns and 'generated_at' in snapshot_columns:

                snapshot_table = candidate

                break



    if snapshot_table:

        c.execute(

            f'''

            SELECT

                r.id AS report_id,

                r.snapshot_id AS snapshot_id,

                COALESCE(s.generated_at, r.created_at) AS latest_ts

            FROM reports r

            LEFT JOIN {snapshot_table} s ON s.id = r.snapshot_id

            WHERE r.firm_id = ?

              AND r.deleted_at IS NULL

            ORDER BY datetime(COALESCE(s.generated_at, r.created_at)) DESC, r.id DESC

            LIMIT 1

            ''',

            (firm_id,),

        )

    else:

        c.execute(

            '''

            SELECT

                r.id AS report_id,

                NULL AS snapshot_id,

                r.created_at AS latest_ts

            FROM reports r

            WHERE r.firm_id = ?

              AND r.deleted_at IS NULL

            ORDER BY datetime(r.created_at) DESC, r.id DESC

            LIMIT 1

            ''',

            (firm_id,),

        )

    row = c.fetchone()

    if not row:

        return None

    return {

        'report_id': int(row[0]),

        'snapshot_id': int(row[1]) if row[1] is not None else None,

        'latest_ts': row[2],

        'uses_snapshot_generated_at': bool(snapshot_table),

    }





def _compute_exposure_snapshot(avg_rating, themes, trend_points, implementation_items):

    """

    Canonical exposure computation used by both Dashboard and Governance Brief PDF.

    Rule set intentionally mirrors the previous PDF exposure behavior.

    """

    trend_points_list = list(trend_points or [])

    action_rows = list(implementation_items or [])

    theme_rows = list(themes or [])



    current_score = _safe_float_number(avg_rating, 0.0)

    previous_score = current_score

    if len(trend_points_list) >= 2 and isinstance(trend_points_list[-2], dict):

        previous_score = _safe_float_number(trend_points_list[-2].get('avg_rating'), current_score)

    score_delta = current_score - previous_score if len(trend_points_list) >= 2 else None



    trend_stability = _trend_stability_from_points_canonical(trend_points_list)

    at_risk_reports = _at_risk_count_from_trend_points_canonical(trend_points_list)



    now = datetime.utcnow()

    open_actions = 0

    overdue_actions = 0

    for row in action_rows:

        if not isinstance(row, dict):

            continue

        status = str(row.get('status') or 'open').strip().lower()

        is_completed = status in {'done', 'completed'}

        due_dt = _parse_iso_dt(row.get('due_date'))

        if not is_completed:

            open_actions += 1

        if not is_completed and due_dt and due_dt < now:

            overdue_actions += 1



    exposure_label = 'Baseline'

    if overdue_actions > 0 or at_risk_reports > 0:

        exposure_label = 'High'

    elif trend_stability in {'Moderately stable', 'Volatile'} or (score_delta is not None and score_delta < 0):

        exposure_label = 'Watchlist'



    if exposure_label == 'Baseline':

        exposure_tier = 'Controlled'

    elif exposure_label == 'Watchlist':

        exposure_tier = 'Watch'

    elif exposure_label == 'Elevated':

        exposure_tier = 'Elevated'

    else:

        exposure_tier = 'Critical'



    top_theme = {'name': 'Uncategorized', 'percentage': 0.0}

    if theme_rows:

        friction_tokens = ('commun', 'respons', 'wait', 'bill', 'cost', 'fee', 'support', 'delay', 'friction', 'complaint')

        strength_tokens = ('outcome', 'result', 'expert', 'legal', 'professional')

        scored = []

        for row in theme_rows:

            if not isinstance(row, dict):

                continue

            name = str(row.get('name') or '').lower()

            share = _safe_float_number(row.get('percentage'), 0.0)

            score = share

            if any(token in name for token in friction_tokens):

                score += 25.0

            if any(token in name for token in strength_tokens):

                score -= 10.0

            scored.append((score, row))

        if scored:

            scored.sort(key=lambda pair: pair[0], reverse=True)

            top_theme = scored[0][1]



    top_theme_name = str(top_theme.get('name') or 'Uncategorized')

    top_theme_share = _safe_float_number(top_theme.get('percentage'), 0.0)

    primary_risk_driver = f"{top_theme_name} ({top_theme_share:.1f}%)"



    responsible_owner = 'Unassigned (requires assignment)'

    for row in action_rows:

        if not isinstance(row, dict):

            continue

        owner = str(row.get('owner') or '').strip()

        theme_name = str(row.get('theme') or '').strip().lower()

        if owner and owner.lower() != 'unassigned' and theme_name and theme_name == top_theme_name.lower():

            responsible_owner = owner

            break

    if responsible_owner == 'Unassigned (requires assignment)':

        for row in action_rows:

            if not isinstance(row, dict):

                continue

            owner = str(row.get('owner') or '').strip()

            if owner and owner.lower() != 'unassigned':

                responsible_owner = owner

                break



    exposure_score = round(max(0.0, min(100.0, (current_score / 5.0) * 100.0)), 1) if current_score > 0 else None



    return {

        'has_data': True,

        'exposure_score': exposure_score,

        'exposure_tier': exposure_tier,

        'exposure_label': exposure_label,

        'partner_escalation_required': exposure_label == 'High',

        'primary_risk_driver': primary_risk_driver,

        'responsible_owner': responsible_owner,

        'at_risk_count': int(at_risk_reports),

        'open_actions': int(open_actions),

        'overdue_actions': int(overdue_actions),

        'trend_stability': trend_stability,

        'score_delta': score_delta,

    }





def get_report_access_type(user_id):

    state = _get_current_user_state(user_id)

    if not state:

        return 'trial'

    if state['subscription_status'] == 'active':

        return state['subscription_type']

    if state['one_time_reports_purchased'] > state['one_time_reports_used']:

        return 'onetime'

    return 'trial'





def _has_report_recovery_access(user_id):

    state = _get_current_user_state(user_id)

    if not state:

        return False

    if state['subscription_status'] == 'active':

        return True

    one_time_remaining = max(

        0,

        int(state.get('one_time_reports_purchased') or 0) - int(state.get('one_time_reports_used') or 0),

    )

    return one_time_remaining > 0





def _get_trial_report_snapshot_count(user_id):

    cycle_start, cycle_end = _current_trial_cycle_bounds()

    conn = db_connect()

    c = conn.cursor()

    c.execute(

        '''

        SELECT COUNT(*)

        FROM reports

        WHERE user_id = ?

          AND subscription_type_at_creation = 'trial'

          AND datetime(created_at) >= datetime(?)

          AND datetime(created_at) < datetime(?)

        ''',

        (

            user_id,

            cycle_start.isoformat(),

            cycle_end.isoformat(),

        ),

    )

    row = c.fetchone()

    conn.close()

    return int(row[0] or 0) if row else 0





def _get_trial_usage_count(user_id, default_limit=FREE_PLAN_REPORT_LIMIT):

    state = _get_current_user_state(user_id)

    if not state:

        return 0, default_limit



    trial_limit = int(state.get('trial_limit') or default_limit)

    if trial_limit != FREE_PLAN_REPORT_LIMIT:

        trial_limit = FREE_PLAN_REPORT_LIMIT



    usage_count = _get_trial_report_snapshot_count(user_id)

    return usage_count, trial_limit





def _has_pro_subscription_access(user_id):

    state = _get_current_user_state(user_id)

    if not state:

        return False

    if state['subscription_status'] != 'active':

        return False

    return (state.get('subscription_type') or 'trial') in ('monthly', 'annual')





def _has_paid_customer_access(user_id):

    state = _get_current_user_state(user_id)

    if not state:

        return False

    if state['subscription_status'] == 'active':

        return True

    one_time_remaining = max(

        0,

        int(state.get('one_time_reports_purchased') or 0) - int(state.get('one_time_reports_used') or 0),

    )

    return one_time_remaining > 0





def _normalize_schedule_recipients(raw_recipients, fallback_email):

    if isinstance(raw_recipients, str):

        candidates = [part.strip() for part in raw_recipients.split(',')]

    elif isinstance(raw_recipients, list):

        candidates = [str(item).strip() for item in raw_recipients]

    else:

        candidates = []



    unique = []

    for candidate in candidates:

        email = candidate.lower()

        if not is_valid_email(email):

            continue

        if email in unique:

            continue

        unique.append(email)

        if len(unique) >= 8:

            break



    fallback = (fallback_email or '').strip().lower()

    if not unique and is_valid_email(fallback):

        unique.append(fallback)

    return unique





def _next_report_pack_run(cadence):

    now = datetime.now(timezone.utc)

    if cadence == 'monthly':

        return now + timedelta(days=30)

    return now + timedelta(days=7)





def _ensure_report_pack_schedule(user_id, fallback_email):

    conn = db_connect()

    c = conn.cursor()

    c.execute(

        '''

        INSERT OR IGNORE INTO report_pack_schedules (user_id, enabled, cadence, recipients_json, next_send_at)

        VALUES (?, 0, 'weekly', ?, ?)

        ''',

        (user_id, json.dumps(_normalize_schedule_recipients([], fallback_email)), _next_report_pack_run('weekly').isoformat()),

    )

    conn.commit()

    conn.close()





def _get_report_pack_schedule(user_id, fallback_email):

    _ensure_report_pack_schedule(user_id, fallback_email)

    conn = db_connect()

    c = conn.cursor()

    c.execute(

        '''

        SELECT enabled, cadence, recipients_json, last_sent_at, next_send_at

        FROM report_pack_schedules

        WHERE user_id = ?

        ''',

        (user_id,),

    )

    row = c.fetchone()

    conn.close()

    if not row:

        return {

            'enabled': False,

            'cadence': 'weekly',

            'recipients': _normalize_schedule_recipients([], fallback_email),

            'last_sent_at': None,

            'next_send_at': _next_report_pack_run('weekly').isoformat(),

        }



    try:

        recipients_raw = json.loads(row[2] or '[]')

    except (TypeError, json.JSONDecodeError):

        recipients_raw = []



    return {

        'enabled': bool(row[0]),

        'cadence': row[1] if row[1] in ('weekly', 'monthly') else 'weekly',

        'recipients': _normalize_schedule_recipients(recipients_raw, fallback_email),

        'last_sent_at': row[3],

        'next_send_at': row[4],

    }


SUPPORT_TICKET_CATEGORIES = {
    'product_bug',
    'data_upload',
    'partner_brief',
    'billing',
    'account_access',
    'security',
    'privacy',
    'other',
}
SUPPORT_TICKET_URGENCIES = {'low', 'normal', 'high', 'critical'}
SUPPORT_TICKET_STATUSES = {'new', 'auto_replied', 'escalated', 'in_review', 'resolved'}
SUPPORT_TICKET_PRIORITIES = {'low', 'normal', 'high', 'urgent'}


def _support_ticket_ref():

    return f"SUP-{datetime.now(timezone.utc).strftime('%Y%m%d')}-{secrets.token_hex(3).upper()}"


def _normalize_support_category(value):

    category = str(value or '').strip().lower().replace('-', '_').replace(' ', '_')

    return category if category in SUPPORT_TICKET_CATEGORIES else 'other'


def _normalize_support_urgency(value):

    urgency = str(value or '').strip().lower()

    return urgency if urgency in SUPPORT_TICKET_URGENCIES else 'normal'


def _support_auto_response_text(category, status, priority, escalation_level):

    if escalation_level == 'security':

        return (
            'Your request was flagged for manual security review. '
            f'If additional security details are needed, follow-up will come from {SECURITY_CONTACT_EMAIL}.'
        )

    if escalation_level == 'manual':

        return (
            'Your request was flagged for manual review by the support team. '
            'We will review the account context and follow up as soon as possible.'
        )

    if category == 'data_upload':

        return (
            'Upload issues usually resolve fastest when the ticket includes the CSV headers, the page where the upload failed, '
            'and the exact validation message shown in the app.'
        )

    if category == 'partner_brief':

        return (
            'Partner-brief delivery depends on configured email settings. '
            'Include whether RESEND_API_KEY, RESEND_FROM_EMAIL, and recipient configuration are present for this deployment.'
        )

    if category == 'billing':

        return (
            'Billing requests are reviewed against the account and payment state on file. '
            'Include the plan, invoice date, or checkout problem you hit.'
        )

    if status == 'auto_replied' and priority == 'low':

        return (
            'Your request was logged successfully. '
            'For faster handling, reply with the page, workflow, and any screenshots if this is a product issue.'
        )

    return (
        'Your request was logged successfully. '
        f'If more detail is needed, the support team will reply from {SUPPORT_EMAIL}.'
    )


def _triage_support_ticket(category, urgency, subject, message):

    text = f"{subject} {message}".lower()
    escalation_level = 'none'
    escalation_reason = ''
    status = 'new'
    priority = 'normal'

    security_tokens = ('security', 'breach', 'hacked', 'unauthorized', 'phishing', 'vulnerability', 'exposed')
    billing_tokens = ('billing', 'invoice', 'charged', 'charge', 'refund', 'payment', 'stripe')
    account_tokens = ('login', 'sign in', '2fa', 'two-factor', 'verification', 'locked out', 'account access')

    if category == 'security' or urgency == 'critical' or any(token in text for token in security_tokens):

        escalation_level = 'security'
        escalation_reason = 'Security-sensitive request requires manual review.'
        status = 'escalated'
        priority = 'urgent'

    elif category in ('billing', 'privacy', 'account_access') or urgency == 'high':

        escalation_level = 'manual'
        escalation_reason = 'Request requires account-aware manual review.'
        status = 'escalated'
        priority = 'high'

    elif any(token in text for token in billing_tokens) or any(token in text for token in account_tokens):

        escalation_level = 'manual'
        escalation_reason = 'Request likely needs billing or account review.'
        status = 'escalated'
        priority = 'high'

    elif category in ('data_upload', 'partner_brief', 'product_bug'):

        status = 'auto_replied'
        priority = 'normal' if urgency in ('low', 'normal') else 'high'

    else:

        status = 'auto_replied'
        priority = 'low' if urgency == 'low' else 'normal'

    auto_response = _support_auto_response_text(category, status, priority, escalation_level)

    return {
        'status': status,
        'priority': priority,
        'escalation_level': escalation_level,
        'escalation_reason': escalation_reason,
        'auto_response_template': auto_response,
    }


def _serialize_support_ticket_row(row):

    if not row:

        return None

    return {
        'id': int(row[0]),
        'ticket_ref': row[1],
        'user_id': row[2],
        'requester_name': row[3],
        'requester_email': row[4],
        'firm_name': row[5],
        'source': row[6],
        'category': row[7],
        'urgency': row[8],
        'subject': row[9],
        'message': row[10],
        'status': row[11],
        'priority': row[12],
        'escalation_level': row[13],
        'escalation_reason': row[14],
        'auto_response_template': row[15],
        'auto_response_sent': bool(row[16]),
        'handled_by_user_id': row[17],
        'created_at': row[18],
        'updated_at': row[19],
    }


def _send_support_ticket_autoresponse(ticket):

    requester_email = str(ticket.get('requester_email') or '').strip().lower()

    if not is_valid_email(requester_email):

        return False

    try:

        return send_templated_email(
            EmailPayload(
                to_email=requester_email,
                subject=f"Clarion support request received: {ticket.get('ticket_ref')}",
                template_name="support_ticket_ack",
                context={
                    'ticket_ref': ticket.get('ticket_ref'),
                    'status': ticket.get('status'),
                    'priority': ticket.get('priority'),
                    'category': ticket.get('category'),
                    'auto_response_template': ticket.get('auto_response_template'),
                    'support_email': SUPPORT_EMAIL,
                    'security_email': SECURITY_CONTACT_EMAIL,
                },
            )
        )

    except Exception:

        app.logger.exception('Support auto-response failed for ticket %s', ticket.get('ticket_ref'))
        return False


def _notify_support_ticket(ticket):

    if not is_valid_email(SUPPORT_EMAIL):

        return False

    try:

        if FROM_EMAIL and RESEND_API_KEY:

            html_lines = [
                '<h2>New Clarion support ticket</h2>',
                f"<p><strong>Ticket:</strong> {bleach.clean(ticket.get('ticket_ref') or '', strip=True)}</p>",
                f"<p><strong>Category:</strong> {bleach.clean(ticket.get('category') or '', strip=True)}</p>",
                f"<p><strong>Priority:</strong> {bleach.clean(ticket.get('priority') or '', strip=True)}</p>",
                f"<p><strong>Status:</strong> {bleach.clean(ticket.get('status') or '', strip=True)}</p>",
                f"<p><strong>Requester:</strong> {bleach.clean(ticket.get('requester_email') or '', strip=True)}</p>",
                f"<p><strong>Firm:</strong> {bleach.clean(ticket.get('firm_name') or '', strip=True)}</p>",
                f"<p><strong>Subject:</strong> {bleach.clean(ticket.get('subject') or '', strip=True)}</p>",
                f"<p><strong>Message:</strong><br>{bleach.clean(ticket.get('message') or '', strip=True).replace(chr(10), '<br>')}</p>",
            ]
            send_email(SUPPORT_EMAIL, f"Clarion support ticket {ticket.get('ticket_ref')}", ''.join(html_lines))
            return True

        return send_templated_email(
            EmailPayload(
                to_email=SUPPORT_EMAIL,
                subject=f"Clarion support ticket {ticket.get('ticket_ref')}",
                template_name="support_ticket_internal",
                context={'ticket': ticket, 'support_email': SUPPORT_EMAIL},
            )
        )

    except Exception:

        app.logger.exception('Support notification failed for ticket %s', ticket.get('ticket_ref'))
        return False


def _load_support_tickets_for_user(user_id, requester_email=None, include_all=False, limit=20):

    conn = db_connect()
    c = conn.cursor()

    if include_all:

        c.execute(
            '''
            SELECT id, ticket_ref, user_id, requester_name, requester_email, firm_name, source, category, urgency,
                   subject, message, status, priority, escalation_level, escalation_reason, auto_response_template,
                   auto_response_sent, handled_by_user_id, created_at, updated_at
            FROM support_tickets
            ORDER BY datetime(created_at) DESC
            LIMIT ?
            ''',
            (int(limit),),
        )

    elif user_id:

        c.execute(
            '''
            SELECT id, ticket_ref, user_id, requester_name, requester_email, firm_name, source, category, urgency,
                   subject, message, status, priority, escalation_level, escalation_reason, auto_response_template,
                   auto_response_sent, handled_by_user_id, created_at, updated_at
            FROM support_tickets
            WHERE user_id = ?
            ORDER BY datetime(created_at) DESC
            LIMIT ?
            ''',
            (int(user_id), int(limit)),
        )

    else:

        c.execute(
            '''
            SELECT id, ticket_ref, user_id, requester_name, requester_email, firm_name, source, category, urgency,
                   subject, message, status, priority, escalation_level, escalation_reason, auto_response_template,
                   auto_response_sent, handled_by_user_id, created_at, updated_at
            FROM support_tickets
            WHERE requester_email = ?
            ORDER BY datetime(created_at) DESC
            LIMIT ?
            ''',
            (str(requester_email or '').strip().lower(), int(limit)),
        )

    rows = c.fetchall()
    conn.close()
    return [_serialize_support_ticket_row(row) for row in rows]





def _api_plan_type(access_type):

    mapping = {

        'trial': 'free',

        'onetime': 'one_time',

        'monthly': 'pro_monthly',

        'annual': 'pro_annual',

    }

    return mapping.get(access_type or 'trial', 'free')





def _access_level(access_type):

    return 'paid' if access_type in ('onetime', 'monthly', 'annual') else 'trial'





def _report_access_context(access_type):

    normalized = access_type or 'trial'

    annual_plan = normalized == 'annual'

    return {

        'raw_access_type': normalized,

        'access_level': _access_level(normalized),

        'plan_type': _api_plan_type(normalized),

        'implementation_theme_limit': None if annual_plan else 3,

        'strategic_theme_limit': 8 if annual_plan else 3,

    }





def _max_reviews_for_access_type(access_type):

    if access_type == 'trial':

        return FREE_PLAN_MAX_REVIEWS_PER_REPORT

    if access_type == 'onetime':

        return ONETIME_MAX_REVIEWS_PER_REPORT

    return MAX_CSV_ROWS





def _normalize_csv_header(value):

    normalized = (value or '').lstrip('\ufeff').strip().lower()

    normalized = re.sub(r'[\(\)\[\]\{\}\-_/]+', ' ', normalized)

    normalized = re.sub(r'[^a-z0-9\s]+', ' ', normalized)

    normalized = re.sub(r'\s+', ' ', normalized).strip()

    return normalized





def _resolve_csv_column_mapping(fieldnames):

    headers = []

    for index, name in enumerate(fieldnames or []):

        normalized = _normalize_csv_header(name)

        if normalized:

            headers.append({'index': index, 'original': name, 'normalized': normalized})



    mapping = {}

    ambiguous = {}

    attempted_synonyms = {

        canonical: sorted({_normalize_csv_header(alias) for alias in aliases if _normalize_csv_header(alias)})

        for canonical, aliases in CSV_HEADER_ALIASES.items()

    }



    loose_tokens = {

        'rating': ('rating', 'rate', 'star', 'stars', 'overall'),

        'review_text': ('comment', 'comments', 'review', 'feedback', 'text', 'response'),

        'date': ('date', 'time', 'timestamp', 'created', 'submitted', 'published'),

    }



    def _contains_score(normalized_header, canonical):

        tokens = loose_tokens.get(canonical, ())

        if not tokens:

            return 0

        matched = [token for token in tokens if token in normalized_header]

        if not matched:

            return 0

        # Prefer headers with more canonical tokens.

        return len(set(matched))



    for canonical, aliases in CSV_HEADER_ALIASES.items():

        alias_set = {_normalize_csv_header(alias) for alias in aliases if _normalize_csv_header(alias)}



        exact_candidates = [header for header in headers if header['normalized'] in alias_set]

        if len(exact_candidates) == 1:

            mapping[canonical] = exact_candidates[0]['original']

            continue

        if len(exact_candidates) > 1:

            # If one exact candidate is literally the canonical field name, prefer it.

            canonical_norm = _normalize_csv_header(canonical)

            canonical_exact = [header for header in exact_candidates if header['normalized'] == canonical_norm]

            if len(canonical_exact) == 1:

                mapping[canonical] = canonical_exact[0]['original']

                continue

            ambiguous[canonical] = [header['original'] for header in exact_candidates]

            continue



        scored_contains = []

        for header in headers:

            score = _contains_score(header['normalized'], canonical)

            if score > 0:

                scored_contains.append((score, header))

        if not scored_contains:

            continue

        scored_contains.sort(key=lambda row: (-row[0], row[1]['index']))

        best_score = scored_contains[0][0]

        best = [header for score, header in scored_contains if score == best_score]

        if len(best) == 1:

            mapping[canonical] = best[0]['original']

        else:

            ambiguous[canonical] = [header['original'] for header in best]



    missing_required = [key for key in ('rating', 'review_text') if key not in mapping]

    diagnostics = {

        'normalized_headers': [header['normalized'] for header in headers],

        'attempted_synonyms': attempted_synonyms,

        'ambiguous': ambiguous,

    }

    return mapping, missing_required, diagnostics





def _normalize_review_date(date_raw):

    value = str(date_raw or '').strip()

    if not value:

        return datetime.now(timezone.utc).date().isoformat()



    value = value.replace('Z', '+00:00')

    try:

        parsed = datetime.fromisoformat(value)

        return parsed.date().isoformat()

    except ValueError:

        pass



    for fmt in (

        '%Y-%m-%d',

        '%m/%d/%Y',

        '%d/%m/%Y',

        '%Y/%m/%d',

        '%m-%d-%Y',

        '%d-%m-%Y',

        '%m/%d/%y',

        '%d/%m/%y',

    ):

        try:

            parsed = datetime.strptime(value, fmt)

            return parsed.date().isoformat()

        except ValueError:

            continue



    iso_match = re.search(r'(\d{4}-\d{2}-\d{2})', value)

    if iso_match:

        return iso_match.group(1)



    return datetime.now(timezone.utc).date().isoformat()





def _parse_rating_value(raw_rating):

    value = str(raw_rating or '').strip()

    if not value:

        return None



    match = re.search(r'(\d+(?:\.\d+)?)', value)

    if not match:

        return None



    try:

        numeric = float(match.group(1))

    except ValueError:

        return None



    lower_value = value.lower()

    if numeric > 5 and numeric <= 10 and ('/10' in lower_value or 'out of 10' in lower_value):

        numeric = numeric / 2.0

    if numeric > 5 and numeric <= 100 and '%' in lower_value:

        numeric = (numeric / 100.0) * 5.0



    rating = int(round(numeric))

    if not 1 <= rating <= 5:

        return None

    return rating





def _parse_csv_upload_rows(upload_file, access_type):

    raw_bytes = upload_file.read()

    csv_content = None

    for encoding in ('utf-8-sig', 'utf-8', 'cp1252', 'latin-1'):

        try:

            csv_content = raw_bytes.decode(encoding)

            break

        except UnicodeDecodeError:

            continue

    if csv_content is None:

        return None, 'CSV decoding failed. Use UTF-8 encoded text and try again.', None



    csv_file = StringIO(csv_content)

    reader = csv.DictReader(csv_file)

    if not reader.fieldnames:

        return None, 'Your CSV appears empty or missing headers. Add a header row and try again.', None



    column_mapping, missing_required, diagnostics = _resolve_csv_column_mapping(reader.fieldnames)

    if missing_required or diagnostics.get('ambiguous'):

        visible_columns = ', '.join([name.strip() for name in reader.fieldnames if name and name.strip()][:12]) or 'none detected'

        normalized_columns = ', '.join(diagnostics.get('normalized_headers', [])[:16]) or 'none detected'

        rating_synonyms = ', '.join(diagnostics.get('attempted_synonyms', {}).get('rating', [])[:20]) or 'none'

        review_synonyms = ', '.join(diagnostics.get('attempted_synonyms', {}).get('review_text', [])[:20]) or 'none'

        ambiguity_details = diagnostics.get('ambiguous', {})

        ambiguity_line = ''

        if ambiguity_details:

            parts = []

            for key, candidates in ambiguity_details.items():

                parts.append(f"{key}: {', '.join(candidates)}")

            ambiguity_line = f" Ambiguous matches - {'; '.join(parts)}."

        return (

            None,

            "We couldn't find the required columns for rating and review text. "

            "Tried synonyms for rating and review text using exact + loose token matching. "

            f"Detected columns: {visible_columns}. "

            f"Normalized headers: {normalized_columns}. "

            f"Rating synonyms tried: {rating_synonyms}. "

            f"Review text synonyms tried: {review_synonyms}.{ambiguity_line}",

            None,

        )



    max_reviews_allowed = _max_reviews_for_access_type(access_type)

    valid_rows = []

    row_count = 0

    skipped_due_to_plan_limit = 0

    dropped_rows = 0



    for row in reader:

        row_count += 1

        if row_count > MAX_CSV_ROWS:

            return None, f'CSV has too many rows. Maximum allowed is {MAX_CSV_ROWS}.', None



        for column_name, raw_value in row.items():

            value_text = str(raw_value or '').strip()

            if len(value_text) > MAX_CSV_FIELD_LENGTH:

                label = str(column_name or 'unknown')

                return None, (

                    f'CSV field too long at row {row_count}, column "{label}". '

                    f'Maximum allowed is {MAX_CSV_FIELD_LENGTH} characters.'

                ), None



        rating_source = row.get(column_mapping.get('rating', ''), '')

        review_source = row.get(column_mapping.get('review_text', ''), '')

        date_source = row.get(column_mapping.get('date', ''), '') if column_mapping.get('date') else ''



        rating = _parse_rating_value(rating_source)

        review_text = str(review_source or '').strip()

        if rating is None or not review_text:

            dropped_rows += 1

            continue



        date_value = _normalize_review_date(date_source)



        cleaned_text = bleach.clean(review_text, strip=True)

        if len(cleaned_text) > MAX_REVIEW_TEXT_LENGTH:

            dropped_rows += 1

            continue



        if len(valid_rows) < max_reviews_allowed:

            valid_rows.append((date_value, rating, cleaned_text))

        else:

            if access_type == 'trial':

                skipped_due_to_plan_limit += 1

                continue

            if access_type == 'onetime':

                return None, (

                    f'Free supports up to {ONETIME_MAX_REVIEWS_PER_REPORT} reviews per report. '

                    'Upgrade to Team or Firm for larger uploads.'

                ), None

            return None, f'Upload exceeds the per-report limit of {max_reviews_allowed} reviews.', None



    if not valid_rows:

        return (

            None,

            'No valid review rows were found after automatic column mapping. '

            'Make sure each row has a rating (1-5) and review text.',

            None,

        )



    return valid_rows, None, {

        'applied_review_limit': max_reviews_allowed,

        'truncated_for_plan': skipped_due_to_plan_limit > 0,

        'skipped_due_to_plan_limit': skipped_due_to_plan_limit,

        'dropped_rows': dropped_rows,

        'column_mapping': column_mapping,

    }





def _insert_user_reviews(user_id, valid_rows):

    conn = db_connect()

    c = conn.cursor()

    for date_value, rating, cleaned_text in valid_rows:

        c.execute(

            'INSERT INTO reviews (date, rating, review_text) VALUES (?, ?, ?)',

            (date_value, rating, cleaned_text)

        )

        review_id = c.lastrowid

        c.execute(

            'INSERT OR IGNORE INTO review_ownership (review_id, user_id) VALUES (?, ?)',

            (review_id, user_id),

        )

    conn.commit()

    conn.close()





# -- PR5 atomic-upload helpers (F8/F10/F11) -----------------------------------

# These *_tx variants accept an existing (conn, cursor) so the caller can wrap

# reviews + report + credit update in a single BEGIN IMMEDIATE / COMMIT block.

# The originals above are left untouched; they are used outside the upload path.



def _analyze_reviews_tx(c, user_id):

    """

    Read-through variant of analyze_reviews() that uses the caller's cursor.

    Because it shares the open transaction, it sees uncommitted inserts made

    earlier in the same connection � essential for correctness here.

    Analytics logic is identical to analyze_reviews(); only the DB fetch differs.

    F16/PR6: anonymous branch removed � caller must always supply a real user_id.

    """

    # user_id is always a real authenticated user's id when called from the upload path.

    c.execute(

        '''

        SELECT r.date, r.rating, r.review_text

        FROM reviews r

        INNER JOIN review_ownership ro ON ro.review_id = r.id

        WHERE ro.user_id = ?

        ORDER BY r.created_at DESC

        ''',

        (user_id,),

    )

    reviews = [

        {'date': row[0], 'rating': row[1], 'review_text': row[2]}

        for row in c.fetchall()

    ]



    if not reviews:

        return {

            'total_reviews': 0,

            'avg_rating': 0,

            'themes': {},

            'top_praise': [],

            'top_complaints': [],

            'all_reviews': [],

        }



    analysis_reviews = reviews

    if not current_user.is_anonymous:

        if not current_user.has_active_subscription() and not current_user.has_unused_one_time_reports():

            analysis_reviews = reviews[:FREE_PLAN_MAX_REVIEWS_PER_REPORT]



    total_reviews = len(analysis_reviews)

    avg_rating = sum(r['rating'] for r in analysis_reviews) / total_reviews



    theme_keywords = {

        'Communication': ['communication', 'responsive', 'returned calls', 'kept me informed', 'updates', 'contact'],

        'Professionalism': ['professional', 'courteous', 'respectful', 'polite', 'demeanor', 'ethical'],

        'Legal Expertise': ['knowledgeable', 'experienced', 'expert', 'skilled', 'competent', 'expertise'],

        'Case Outcome': ['won', 'successful', 'settlement', 'verdict', 'result', 'outcome', 'resolved'],

        'Cost/Value': ['expensive', 'affordable', 'fees', 'billing', 'cost', 'worth it', 'value', 'price'],

        'Responsiveness': ['quick', 'slow', 'delayed', 'waiting', 'timely', 'immediately', 'promptly'],

        'Compassion': ['caring', 'understanding', 'empathetic', 'compassionate', 'listened', 'supportive'],

        'Staff Support': ['staff', 'assistant', 'paralegal', 'secretary', 'team', 'office'],

    }



    theme_counts = Counter()

    for review in analysis_reviews:

        text_lower = review['review_text'].lower()

        for theme, keywords in theme_keywords.items():

            if any(keyword in text_lower for keyword in keywords):

                theme_counts[theme] += 1



    top_praise = [r for r in analysis_reviews if r['rating'] >= 4][:10]

    top_complaints = [r for r in analysis_reviews if r['rating'] <= 2][:10]



    return {

        'total_reviews': total_reviews,

        'avg_rating': round(avg_rating, 2),

        'themes': dict(theme_counts.most_common(8)),

        'top_praise': top_praise,

        'top_complaints': top_complaints,

        'all_reviews': reviews,

    }





def _insert_user_reviews_tx(c, user_id, valid_rows):
    """Insert reviews + ownership rows using the caller's cursor (no commit)."""
    for date_value, rating, cleaned_text in valid_rows:
        c.execute(

            'INSERT INTO reviews (date, rating, review_text) VALUES (?, ?, ?)',

            (date_value, rating, cleaned_text),

        )

        review_id = c.lastrowid

        c.execute(
            'INSERT OR IGNORE INTO review_ownership (review_id, user_id) VALUES (?, ?)',
            (review_id, user_id),
        )


def _build_top_complaint_signal_candidates(analysis):
    total_reviews = max(1, int(analysis.get('total_reviews') or 0))
    themes = analysis.get('themes') or {}
    rows = []
    for name, mentions in themes.items():
        try:
            mention_count = int(mentions)
        except Exception:
            continue
        if mention_count <= 0:
            continue
        metric_slug = str(name).strip().lower().replace(' ', '_')
        rows.append(
            {
                'title': str(name),
                'frequency': mention_count / total_reviews,
                'source_metric': f'{metric_slug}_mentions',
            }
        )
    rows.sort(key=lambda row: row['frequency'], reverse=True)
    return rows


def _persist_governance_insights_tx(c, report_id, insights):
    """Persist generated governance insights for a report (same transaction)."""
    now_iso = datetime.now(timezone.utc).isoformat()
    c.execute('DELETE FROM governance_signals WHERE report_id = ?', (report_id,))
    c.execute('DELETE FROM governance_recommendations WHERE report_id = ?', (report_id,))

    for signal in insights.get('exposure_signals', []) or []:
        signal_title = str(signal.get('title') or '').strip() or 'Governance Signal'
        signal_description = str(signal.get('description') or '').strip()
        signal_severity = str(signal.get('severity') or 'low').strip().lower() or 'low'
        c.execute(
            '''
            INSERT INTO governance_signals (report_id, title, description, severity, created_at)
            VALUES (?, ?, ?, ?, ?)
            ''',
            (
                report_id,
                signal_title,
                signal_description,
                signal_severity,
                now_iso,
            ),
        )
        if signal_severity == 'high':
            normalized_title = signal_title.lower()
            tracked_categories = {
                'communication': 'Communication',
                'professionalism': 'Professionalism',
                'case outcome': 'Case outcome',
            }
            matched_category = next(
                (label for key, label in tracked_categories.items() if key in normalized_title),
                None,
            )
            if matched_category:
                percent_match = re.search(r'(\d+)%', signal_description or '')
                percent = int(percent_match.group(1)) if percent_match else None
                if percent is not None and percent >= 20:
                    try:
                        send_slack_alert(
                            (
                                f'Clarion Client Experience Alert\n'
                                f'{matched_category} complaints increasing.\n'
                                f'{percent}% of reviews mention {matched_category.lower()} issues.\n'
                                f'Review recommended before next partner meeting.'
                            )
                        )
                    except Exception:
                        app.logger.exception(
                            'Slack alert dispatch failed for report_id=%s signal=%s',
                            report_id,
                            signal_title,
                        )

    for recommendation in insights.get('recommended_actions', []) or []:
        c.execute(
            '''
            INSERT INTO governance_recommendations (report_id, title, priority, suggested_owner, created_at)
            VALUES (?, ?, ?, ?, ?)
            ''',
            (
                report_id,
                str(recommendation.get('title') or '').strip() or 'Recommended Action',
                str(recommendation.get('priority') or 'low').strip().lower() or 'low',
                str(recommendation.get('suggested_owner') or '').strip(),
                now_iso,
            ),
        )




def _save_report_snapshot_tx(c, user_id, subscription_type, report_hash):

    """

    Insert the report snapshot using the caller's cursor (no commit).

    Calls _analyze_reviews_tx so analysis reads the uncommitted reviews

    inserted earlier in the same transaction.

    Returns report_id, or None if there are no analyzable reviews.

    """

    analysis = _analyze_reviews_tx(c, user_id)

    if analysis['total_reviews'] == 0:

        return None



    firm_id = _resolve_user_active_firm_id(c, user_id)

    if firm_id is None:

        return None



    c.execute(

        '''

        INSERT INTO reports (

            user_id,

            firm_id,

            created_by_user_id,

            total_reviews,

            avg_rating,

            themes,

            top_praise,

            top_complaints,

            subscription_type_at_creation,

            report_hash

        )

        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)

        ''',

        (

            user_id,

            firm_id,

            user_id,

            analysis['total_reviews'],

            analysis['avg_rating'],

            _serialize_report_data(analysis['themes']),

            _serialize_report_data(analysis['top_praise']),

            _serialize_report_data(analysis['top_complaints']),

            subscription_type,

            report_hash,
        ),
    )
    report_id = c.lastrowid

    ordered_themes = sorted(
        [{'name': name, 'mentions': int(mentions)} for name, mentions in (analysis.get('themes') or {}).items()],
        key=lambda item: item['mentions'],
        reverse=True,
    )
    access_context = _report_access_context(subscription_type or 'trial')
    implementation_roadmap = _build_implementation_roadmap(
        ordered_themes,
        access_context['implementation_theme_limit'],
    )
    all_reviews = analysis.get('all_reviews') or []
    total_reviews = max(1, int(analysis.get('total_reviews') or 0))
    negative_count = sum(1 for review in all_reviews if int(review.get('rating') or 0) <= 2)
    report_for_insights = {
        'top_complaints': _build_top_complaint_signal_candidates(analysis),
        'sentiment_summary': {
            'negative_share': negative_count / total_reviews,
        },
        'implementation_roadmap': implementation_roadmap,
    }
    insights = generate_governance_insights(report_for_insights)
    _persist_governance_insights_tx(c, report_id, insights)

    return report_id




# -- end PR5 helpers -----------------------------------------------------------





def _build_root_cause_themes(themes, max_items):

    selected = themes if max_items is None else themes[:max_items]

    root_causes = []

    for theme in selected:

        root_causes.append(

            {

                'theme': theme['name'],

                'mentions': theme['mentions'],

                'root_cause': (

                    f"{theme['name']} signal appears in {theme['mentions']} comments. "

                    "Primary drivers suggest expectation mismatch and inconsistent workflow execution."

                ),

                'impact': 'Client confidence and referral risk',

            }

        )

    return root_causes





def _build_recommended_changes(themes, max_items):

    selected = themes if max_items is None else themes[:max_items]

    actions = []

    for theme in selected:

        actions.append(

            {

                'theme': theme['name'],

                'recommendation': (

                    f"Create a standard operating playbook for {theme['name'].lower()} with weekly owner reviews."

                ),

            }

        )

    return actions





def _build_implementation_roadmap(themes, max_items):

    selected = themes if max_items is None else themes[:max_items]

    roadmap = []

    for idx, theme in enumerate(selected):

        roadmap.append(

            {

                'theme': theme['name'],

                'timeline': 'Days 1-30' if idx % 3 == 0 else ('Days 31-60' if idx % 3 == 1 else 'Days 61-90'),

                'owner': 'Operations Lead' if idx % 2 == 0 else 'Managing Attorney',

                'kpi': f"Reduce negative {theme['name'].lower()} mentions by 20%",

            }

        )

    return roadmap





def _build_strategic_plans(themes, max_items):

    selected = themes[:max_items]

    plans = []

    for theme in selected:

        plans.append(

            {

                'theme': theme['name'],

                'objective': f"Improve {theme['name'].lower()} outcomes in active matters.",

                'ninety_day_steps': [

                    'Week 1-2: baseline current process and assign owner.',

                    'Week 3-6: launch standard workflow and client communication touchpoints.',

                    'Week 7-12: monitor KPI trend and adjust staffing/process controls.',

                ],

                'owner': 'Client Experience Manager',

                'kpi': f"{theme['name']} satisfaction +15%",

            }

        )

    return plans





def is_email_verified(user_id):
    conn = db_connect()
    c = conn.cursor()
    c.execute('SELECT email_verified FROM users WHERE id = ?', (user_id,))
    row = c.fetchone()
    conn.close()
    return bool(row and int(row[0] or 0) == 1)


def _email_verification_serializer():
    return URLSafeTimedSerializer(app.config['SECRET_KEY'])


def create_email_verification_token(user_id, email):
    payload = {
        'user_id': int(user_id),
        'email': str(email or '').strip().lower(),
    }
    return _email_verification_serializer().dumps(payload, salt=EMAIL_VERIFICATION_SALT)


def decode_email_verification_token(token):
    try:
        payload = _email_verification_serializer().loads(
            token,
            salt=EMAIL_VERIFICATION_SALT,
            max_age=EMAIL_VERIFICATION_MAX_AGE_SECONDS,
        )
        user_id = int(payload.get('user_id'))
        email = str(payload.get('email') or '').strip().lower()
        if not email:
            return None, 'Invalid verification token.'
        return {'user_id': user_id, 'email': email}, None
    except SignatureExpired:
        return None, 'Verification link has expired. Request a new verification email.'
    except (BadSignature, ValueError, TypeError):
        return None, 'Invalid verification token.'


def _send_verification_email_smtp(to_email, verification_link, firm_name):
    smtp_server = os.environ.get('SMTP_SERVER')
    smtp_port = int(os.environ.get('SMTP_PORT', '587'))
    smtp_username = os.environ.get('SMTP_USERNAME')
    smtp_password = os.environ.get('SMTP_PASSWORD')
    from_email = os.environ.get('FROM_EMAIL') or smtp_username

    if not smtp_server or not from_email:
        return False

    subject = 'Verify your Clarion account'
    body = (
        'Welcome to Clarion.\n\n'
        'Please verify your email to activate your account.\n\n'
        f'Verify Email:\n{verification_link}\n'
    )

    message = EmailMessage()
    message['Subject'] = subject
    message['From'] = from_email
    message['To'] = to_email
    message.set_content(body)

    try:
        with smtplib.SMTP(smtp_server, smtp_port, timeout=15) as smtp:
            smtp.ehlo()
            if smtp_port in (587, 2525):
                smtp.starttls()
                smtp.ehlo()
            if smtp_username and smtp_password:
                smtp.login(smtp_username, smtp_password)
            smtp.send_message(message)
        return True
    except Exception:
        app.logger.exception('SMTP verification email send failed for %s', to_email)
        return False


def _verification_delivery_status():
    resend_api_key = (os.environ.get('RESEND_API_KEY') or '').strip()
    resend_from_email = _resolve_from_email()
    resend_sender = parseaddr(resend_from_email)[1] if resend_from_email else ''
    if resend_api_key and resend_from_email and resend_sender:
        return {
            'available': True,
            'method': 'resend',
            'error': None,
        }
    configured_resend_sender = (os.environ.get('RESEND_FROM_EMAIL') or os.environ.get('FROM_EMAIL') or '').strip()
    if resend_api_key and not resend_from_email:
        return {
            'available': False,
            'method': 'resend',
            'error': 'Verification email delivery is configured for Resend, but no sender address is set. Add RESEND_FROM_EMAIL or FROM_EMAIL before sending verification emails.',
        }
    if resend_api_key and configured_resend_sender and not parseaddr(configured_resend_sender)[1]:
        return {
            'available': False,
            'method': 'resend',
            'error': f'Verification email delivery is configured for Resend, but the sender address is invalid: {configured_resend_sender}',
        }

    if app.config.get('MAIL_ENABLED'):
        return {
            'available': True,
            'method': 'mail',
            'error': None,
        }

    smtp_server = (os.environ.get('SMTP_SERVER') or '').strip()
    smtp_from_email = (os.environ.get('FROM_EMAIL') or os.environ.get('SMTP_USERNAME') or '').strip()
    smtp_sender = parseaddr(smtp_from_email)[1] if smtp_from_email else ''
    if smtp_server and smtp_from_email and smtp_sender:
        return {
            'available': True,
            'method': 'smtp',
            'error': None,
        }
    if smtp_server and not smtp_from_email:
        return {
            'available': False,
            'method': 'smtp',
            'error': 'Verification email delivery is configured for SMTP, but no sender address is set. Add FROM_EMAIL or SMTP_USERNAME before sending verification emails.',
        }
    if smtp_server and smtp_from_email and not smtp_sender:
        return {
            'available': False,
            'method': 'smtp',
            'error': f'Verification email delivery is configured for SMTP, but the sender address is invalid: {smtp_from_email}',
        }

    return {
        'available': False,
        'method': None,
        'error': 'Verification email delivery is not configured in this deployment yet. Contact support to finish account setup.',
    }


def _verification_delivery_response_payload(delivery_status, delivery_result=None):
    if not delivery_result:
        return {
            'verification_delivery_available': bool(delivery_status['available']),
            'verification_delivery_method': delivery_status['method'],
            'verification_delivery_error': delivery_status['error'],
            'verification_delivery_error_type': None,
            'verification_delivery_from_email': None,
        }
    if delivery_result.success:
        return {
            'verification_delivery_available': True,
            'verification_delivery_method': delivery_result.provider or delivery_status['method'],
            'verification_delivery_error': None,
            'verification_delivery_error_type': None,
            'verification_delivery_from_email': delivery_result.from_email,
        }
    return {
        'verification_delivery_available': False,
        'verification_delivery_method': delivery_result.provider or delivery_status['method'],
        'verification_delivery_error': delivery_result.error_message or delivery_status['error'] or 'We could not send the verification email right now.',
        'verification_delivery_error_type': delivery_result.error_type,
        'verification_delivery_from_email': delivery_result.from_email,
    }


def send_email_verification_link_with_result(to_email, verification_link, firm_name):
    delivery_status = _verification_delivery_status()
    sender_choice = resolve_from_email_choice()
    resolved_sender = sender_choice.from_email
    known_working_sender = _known_working_resend_sender()
    try:
        if _allow_dev_auth_shortcuts_for_email(to_email):
            print("\n==============================")
            print("DEV VERIFICATION LINK")
            print(verification_link)
            print("==============================\n")
            return EmailDeliveryResult(success=True, provider='dev')

        if delivery_status['method'] in {'resend', 'mail'} and delivery_status['available']:
            result = send_verification_email_with_result(to_email, verification_link, firm_name)
        elif delivery_status['method'] == 'smtp' and delivery_status['available']:
            smtp_success = _send_verification_email_smtp(to_email, verification_link, firm_name)
            result = EmailDeliveryResult(
                success=bool(smtp_success),
                provider='smtp',
                from_email=(os.environ.get('FROM_EMAIL') or os.environ.get('SMTP_USERNAME') or '').strip() or None,
                error_type=None if smtp_success else 'smtp_runtime_error',
                error_message=None if smtp_success else 'SMTP delivery failed for the verification email. Check SMTP connectivity, credentials, and sender configuration.',
            )
        else:
            app.logger.warning('Verification email delivery unavailable for %s: %s', to_email, delivery_status['error'])
            result = EmailDeliveryResult(
                success=False,
                provider=delivery_status['method'],
                error_type='provider_not_configured',
                error_message=delivery_status['error'],
            )

        if result.success:
            app.logger.info(
                'Verification email delivery succeeded for %s via %s from=%s sender_source=%s known_working_sender=%s sender_matches_known_working=%s',
                to_email,
                result.provider,
                result.from_email or '-',
                sender_choice.source,
                known_working_sender,
                uses_known_working_resend_sender(result.from_email or resolved_sender),
            )
        else:
            app.logger.warning(
                'Verification email delivery failed for %s via %s from=%s sender_source=%s known_working_sender=%s sender_matches_known_working=%s error_type=%s detail=%s',
                to_email,
                result.provider or delivery_status['method'] or 'none',
                result.from_email or resolved_sender or '-',
                sender_choice.source,
                known_working_sender,
                uses_known_working_resend_sender(result.from_email or resolved_sender),
                result.error_type or 'unknown',
                result.error_message or delivery_status['error'] or 'unknown',
            )
        return result
    except Exception as exc:
        app.logger.exception('Verification email send failed unexpectedly for %s', to_email)
        return EmailDeliveryResult(
            success=False,
            provider=delivery_status['method'],
            error_type='delivery_runtime_error',
            error_message=f'Verification email delivery failed unexpectedly in the application runtime: {exc}',
        )


def send_email_verification_link(to_email, verification_link, firm_name):
    return send_email_verification_link_with_result(to_email, verification_link, firm_name).success


def _is_resend_verification_rate_limited(ip_address):
    """Basic in-memory limiter: 3 resend requests per 10 minutes per IP."""
    now_ts = time_module.time()
    window_start = now_ts - RESEND_VERIFICATION_WINDOW_SECONDS
    recent_attempts = [
        ts
        for ts in _resend_verification_attempts_by_ip.get(ip_address, [])
        if ts >= window_start
    ]
    if len(recent_attempts) >= RESEND_VERIFICATION_MAX_REQUESTS:
        _resend_verification_attempts_by_ip[ip_address] = recent_attempts
        return True
    recent_attempts.append(now_ts)
    _resend_verification_attempts_by_ip[ip_address] = recent_attempts
    return False


def _public_verify_email_link(token):
    return f'{_resolve_public_app_base_url()}/verify-email/{token}'


def _allow_dev_auth_shortcuts_for_email(email):
    if not DEV_MODE:
        return False
    normalized_email = str(email or '').strip().lower()
    admin_email = str(app.config.get('ADMIN_EMAIL') or '').strip().lower()
    return bool(normalized_email and admin_email and normalized_email == admin_email)




def _user_response_payload(user):
    firm_membership = _get_user_active_firm_membership(user.id)
    firm_membership_disabled = _has_suspended_membership_without_active(user.id)
    firm_name = (
        (firm_membership.get('firm_name') if firm_membership else None)
        or user.firm_name
        or app.config['FIRM_NAME']
    )
    trial_reports_used, trial_limit = _get_trial_usage_count(user.id, user.trial_limit)
    return {
        'id': user.id,
        'email': user.email,
        'firm_name': firm_name,
        'firm_id': int(firm_membership['firm_id']) if firm_membership else None,
        'firm_role': firm_membership['role'] if firm_membership else None,
        'has_firm_context': bool(firm_membership),
        'firm_membership_disabled': bool(firm_membership_disabled),
        'subscription_type': user.subscription_type,
        'is_admin': user.is_admin,
        'onboarding_complete': bool(getattr(user, 'onboarding_complete', False)),
        'trial_reviews_used': trial_reports_used,
        'trial_limit': trial_limit,
        'email_verified': bool(getattr(user, 'email_verified', False) or is_email_verified(user.id)),
        'two_factor_enabled': user.two_factor_enabled,
        'two_factor_available': bool(app.config.get('ENABLE_2FA')),
    }


def _get_user_active_firm_membership(user_id):
    conn = db_connect()
    c = conn.cursor()
    c.execute(
        '''
        SELECT fu.firm_id, fu.role, f.name
        FROM firm_users fu
        INNER JOIN firms f ON f.id = fu.firm_id
        WHERE fu.user_id = ?
          AND fu.status = 'active'
        ORDER BY fu.id ASC
        LIMIT 1
        ''',
        (user_id,),
    )
    row = c.fetchone()
    conn.close()
    if not row:
        return None
    return {
        'firm_id': int(row[0]),
        'role': str(row[1]),
        'firm_name': str(row[2] or ''),
    }


def _has_suspended_membership_without_active(user_id):
    """True when a user has only suspended memberships and no active one."""
    conn = db_connect()
    c = conn.cursor()
    c.execute(
        '''
        SELECT
            SUM(CASE WHEN status = 'active' THEN 1 ELSE 0 END),
            SUM(CASE WHEN status = 'suspended' THEN 1 ELSE 0 END)
        FROM firm_users
        WHERE user_id = ?
        ''',
        (user_id,),
    )
    row = c.fetchone()
    conn.close()
    active_count = int((row[0] if row and row[0] is not None else 0) or 0)
    suspended_count = int((row[1] if row and row[1] is not None else 0) or 0)
    return active_count == 0 and suspended_count > 0




def _get_client_ip():

    # F7/PR4: ProxyFix (applied at startup) has already resolved the real client

    # IP into request.remote_addr from exactly 1 trusted X-Forwarded-For hop.

    # Never read X-Forwarded-For directly here � that would allow client spoofing.

    return request.remote_addr or 'unknown'





def _is_two_factor_required(user):

    return bool(app.config.get('ENABLE_2FA') and user and user.two_factor_enabled)





def _create_two_factor_challenge(user):

    challenge_id = secrets.token_urlsafe(24)

    code = ''.join(secrets.choice('0123456789') for _ in range(TWO_FACTOR_CODE_LENGTH))

    code_hash = generate_password_hash(code)

    expires_at = (datetime.now(timezone.utc) + timedelta(seconds=app.config.get('TWO_FACTOR_OTP_TTL_SECONDS', 600))).isoformat()



    conn = db_connect()

    c = conn.cursor()

    c.execute(

        'DELETE FROM two_factor_challenges WHERE consumed_at IS NOT NULL OR expires_at < ?',

        (datetime.now(timezone.utc).isoformat(),),

    )

    c.execute(

        '''

        INSERT INTO two_factor_challenges (id, user_id, code_hash, expires_at, attempts)

        VALUES (?, ?, ?, ?, 0)

        ''',

        (challenge_id, user.id, code_hash, expires_at),

    )

    conn.commit()

    conn.close()



    if app.config.get('MAIL_ENABLED'):

        sent = send_two_factor_code_email(

            to_email=user.email,

            code=code,

            firm_name=user.firm_name or app.config.get('FIRM_NAME', 'Your Firm'),

        )

        if not sent:

            raise RuntimeError('Unable to deliver two-factor code email.')

    else:

        app.logger.info('2FA OTP generated for user_id=%s code=%s (mail disabled)', user.id, code)



    return challenge_id





def _check_password_for_user(user_id, password):

    conn = db_connect()

    c = conn.cursor()

    c.execute('SELECT password_hash FROM users WHERE id = ?', (user_id,))

    row = c.fetchone()

    conn.close()

    return bool(row and check_password_hash(row[0], password))





def _verify_two_factor_challenge_code(challenge_id, code, expected_user_id=None):

    conn = db_connect()

    c = conn.cursor()

    c.execute(

        '''

        SELECT id, user_id, code_hash, expires_at, consumed_at, attempts

        FROM two_factor_challenges

        WHERE id = ?

        ''',

        (challenge_id,),

    )

    row = c.fetchone()

    if not row:

        conn.close()

        return {'ok': False, 'error': 'Invalid verification challenge.', 'status': 400}



    if expected_user_id and int(row[1]) != int(expected_user_id):

        conn.close()

        return {'ok': False, 'error': 'Challenge does not match this account.', 'status': 403}



    expires_at = datetime.fromisoformat(row[3])

    if row[4] or expires_at < datetime.now(timezone.utc):

        conn.close()

        return {'ok': False, 'error': 'This verification code has expired. Please sign in again.', 'status': 400}



    if int(row[5] or 0) >= TWO_FACTOR_MAX_ATTEMPTS:

        c.execute(

            'UPDATE two_factor_challenges SET consumed_at = ? WHERE id = ?',

            (datetime.now(timezone.utc).isoformat(), challenge_id),

        )

        conn.commit()

        conn.close()

        return {'ok': False, 'error': 'Too many verification attempts. Please sign in again.', 'status': 429}



    if not check_password_hash(row[2], code):

        c.execute(

            'UPDATE two_factor_challenges SET attempts = attempts + 1 WHERE id = ?',

            (challenge_id,),

        )

        conn.commit()

        conn.close()

        return {'ok': False, 'error': 'Invalid verification code.', 'status': 401}



    c.execute(

        'UPDATE two_factor_challenges SET consumed_at = ? WHERE id = ?',

        (datetime.now(timezone.utc).isoformat(), challenge_id),

    )

    conn.commit()

    conn.close()

    return {'ok': True, 'user_id': row[1], 'status': 200}



# ===== PUBLIC / MARKETING ROUTES =====



@app.route("/")
def marketing_home():
    """Serve React SPA if built, otherwise fall back to Flask marketing template."""
    if _react_dist_exists:
        return send_from_directory(_REACT_DIST, 'index.html')
    return render_template("marketing_home.html")








@app.route("/how-it-works")

def how_it_works():

    return render_template("how_it_works.html")



@app.route("/features")

def features():

    return render_template("features.html")



@app.route("/case-studies")

def case_studies():

    return render_template("case_studies.html")



@app.route("/pricing")

def pricing():

    return render_template(

        "pricing.html",

        trial_limit=FREE_PLAN_REPORT_LIMIT,

        onetime_price=app.config['ONETIME_REPORT_PRICE'],

        monthly_price=app.config['MONTHLY_SUBSCRIPTION_PRICE'],

        annual_price=app.config['ANNUAL_SUBSCRIPTION_PRICE'],

    )



@app.route("/privacy")

def privacy():

    """Privacy policy page"""

    return render_template("privacy.html")



@app.route("/terms")

def terms():

    """Terms of service page"""

    return render_template("terms.html")



@app.route("/security")

def security():

    """Security page"""

    return render_template("security.html")



@app.route("/app")

def index():

    """App landing page."""

    return render_template(

        "index.html",

        trial_limit=FREE_PLAN_REPORT_LIMIT,

        onetime_price=app.config['ONETIME_REPORT_PRICE'],

        monthly_price=app.config['MONTHLY_SUBSCRIPTION_PRICE'],

        annual_price=app.config['ANNUAL_SUBSCRIPTION_PRICE'],

    )



# ===== CLIENT FEEDBACK ROUTES =====



@app.route('/feedback', methods=['GET', 'POST'])

@limiter.limit('10 per minute')

@limiter.limit('20 per hour')

def feedback_form():

    """

    Public client feedback submission form.

    F15/PR6: submissions write to `public_feedback`, never to `reviews` or

    `review_ownership`. This prevents any public user from poisoning a firm's

    dataset regardless of authentication status.

    PR6b: rate-limited to 10/min + 20/hr per IP; review_text hard-capped at MAX_REVIEW_TEXT_LENGTH.

    """

    if request.method == 'POST':

        date = request.form.get('date') or datetime.now().strftime('%Y-%m-%d')

        rating = request.form.get('rating')

        review_text = request.form.get('review_text') or ''



        if not rating or not review_text:

            flash('Please provide a rating and review text.', 'danger')

            return redirect(url_for('feedback_form'))



        try:

            rating = int(rating)

            if rating < 1 or rating > 5:

                raise ValueError

        except ValueError:

            flash('Rating must be between 1 and 5.', 'danger')

            return redirect(url_for('feedback_form'))



        # PR6b: hard cap � do NOT silently truncate; reject oversized input.

        if len(review_text) > MAX_REVIEW_TEXT_LENGTH:

            flash(f'Review text is too long. Please keep it under {MAX_REVIEW_TEXT_LENGTH} characters.', 'danger')

            return redirect(url_for('feedback_form'))



        sanitized_review_text = bleach.clean(review_text, strip=True)



        # F15/PR6: write ONLY to public_feedback � never touches reviews or review_ownership.

        conn = db_connect()

        c = conn.cursor()

        c.execute(

            'INSERT INTO public_feedback (date, rating, review_text) VALUES (?, ?, ?)',

            (date, rating, sanitized_review_text),

        )

        conn.commit()

        conn.close()



        flash('Thank you for your feedback!', 'success')

        return redirect(url_for('thank_you'))



    return render_template('feedback_form.html')



@app.route('/thank-you')

def thank_you():

    """Thank you page after feedback submission"""

    return render_template('thank_you.html')



# ===== ADMIN AUTH ROUTES =====





@app.route('/register', methods=['GET', 'POST'])

@limiter.limit('5 per hour')

def register():

    """Self-service registration for new firms (free trial)."""

    if current_user.is_authenticated:

        return redirect(url_for('upload'))



    if request.method == 'POST':

        errors = {}

        full_name = (request.form.get('full_name') or '').strip()

        firm_name = (request.form.get('firm_name') or app.config['FIRM_NAME']).strip()

        email = (request.form.get('email') or '').strip().lower()

        password = request.form.get('password') or ''

        confirm_password = request.form.get('confirm_password') or ''



        if not is_valid_email(email):

            errors['email'] = 'Enter a valid business email address.'

        if len(firm_name) < 2 or len(firm_name) > MAX_FIRM_NAME_LENGTH:

            errors['firm_name'] = f'Firm name must be 2-{MAX_FIRM_NAME_LENGTH} characters.'

        if len(full_name) < 2 or len(full_name) > 120:

            errors['full_name'] = 'Enter your full name (2-120 characters).'

        ok_password, password_msg = validate_password_strength(password)

        if not ok_password:

            errors['password'] = password_msg

        if password != confirm_password:

            errors['confirm_password'] = 'Passwords do not match.'



        if errors:

            flash('Please correct the highlighted fields and submit again.', 'danger')

            return render_template('register.html', errors=errors)



        sanitized_firm_name = bleach.clean(firm_name, strip=True)

        if not sanitized_firm_name:

            email_local_part = (email.split('@', 1)[0] or '').strip()

            sanitized_firm_name = f'{email_local_part} firm' if email_local_part else 'New Firm'



        conn = db_connect()

        c = conn.cursor()



        # Use email as username for SaaS users

        c.execute(

            'SELECT id FROM users WHERE email = ? OR username = ?',

            (email, email),

        )

        existing = c.fetchone()

        if existing:

            conn.close()

            flash('An account with that email already exists. Please log in.', 'warning')

            return redirect(url_for('login'))



        password_hash = generate_password_hash(password)



        # NEW: include created_at (and keep everything else)

        from datetime import datetime

        created_at = datetime.utcnow().isoformat()



        c.execute(
            '''
            INSERT INTO users (
                username,
                email,
                firm_name,

                password_hash,

                is_admin,

                trial_reviews_used,

                trial_limit,
                subscription_status,
                subscription_type,
                created_at,
                email_verified
            )
            VALUES (?, ?, ?, ?, 0, 0, ?, 'trial', 'trial', ?, ?)
            ''',
            (
                email,
                email,
                sanitized_firm_name,
                password_hash,
                FREE_PLAN_REPORT_LIMIT,
                created_at,
                1 if _allow_dev_auth_shortcuts_for_email(email) else 0,
            ),
        )
        user_id = c.lastrowid

        conn.commit()

        conn.close()



        user = User(

            id=user_id,

            username=email,

            email=email,

            firm_name=sanitized_firm_name,

            is_admin=False,

            subscription_status='trial',

            trial_reviews_used=0,

            trial_limit=FREE_PLAN_REPORT_LIMIT,

            one_time_reports_purchased=0,

            one_time_reports_used=0,

            subscription_type='trial',

        )
        verify_token = create_email_verification_token(user_id, email)
        verification_link = url_for('verify_email', token=verify_token, _external=True)
        if _allow_dev_auth_shortcuts_for_email(email):
            login_user(user)
            flash('Internal tester account created. Verification was skipped for this admin-only dev shortcut.', 'success')
            return redirect(url_for('upload'))
        flash('Account created successfully. Please verify your email before signing in.', 'success')
        if send_email_verification_link(email, verification_link, sanitized_firm_name):
            flash('Verification email sent. Check your inbox to activate your account.', 'info')
        else:
            flash(f'We could not send the verification email automatically. Use this verification link: {verification_link}', 'warning')
        return redirect(url_for('login'))



    # Legacy GET /register -> SPA handoff
    return redirect(_resolve_public_app_base_url() + '/signup', code=302)



@app.route('/verify-email/<token>')
@limiter.limit('20 per hour')
def verify_email(token):
    app.logger.info(
        'Legacy verification route hit for token handoff; redirecting to SPA verify flow base_url=%s',
        _resolve_public_app_base_url(),
    )
    return redirect(f'{_resolve_public_app_base_url()}/verify-email/{token}')


@app.route('/login', methods=['GET', 'POST'])
@limiter.limit('5 per minute')
def login():
    """Login page for firm administrators and trial accounts."""

    if current_user.is_authenticated:

        return redirect(url_for('dashboard'))



    if request.method == 'POST':

        # Identifier may be email address or legacy username

        identifier = (request.form.get('username') or '').strip()

        password = request.form.get('password') or ''

        client_ip = _get_client_ip()

        # PR4b: log resolved IP + raw header so ops can verify PROXY_HOPS is correct.

        # Safe: no credentials logged; remote_addr is already resolved by ProxyFix.

        app.logger.debug(

            'login attempt web remote_addr=%s xff_raw=%s xfp=%s',

            client_ip,

            request.headers.get('X-Forwarded-For', '-'),

            request.headers.get('X-Forwarded-Proto', '-'),

        )



        if not identifier or not password:

            flash('Email and password are required to sign in.', 'danger')

            return redirect(url_for('login'))



        backoff_seconds = _login_backoff_seconds(identifier, client_ip)

        if backoff_seconds > 0:

            time_module.sleep(backoff_seconds)



        conn = db_connect()

        c = conn.cursor()

        c.execute(

            'SELECT id, password_hash FROM users WHERE email = ? OR username = ?',

            (identifier, identifier),

        )

        user_data = c.fetchone()

        conn.close()



        if user_data and check_password_hash(user_data[1], password):
            # Load full user record via the user loader for consistency
            user = load_user(user_data[0])
            if user:
                if not is_email_verified(user.id) and not _allow_dev_auth_shortcuts_for_email(user.email):
                    _record_failed_login(identifier, client_ip)
                    _log_security_event(user.id, 'auth_login_blocked_unverified', metadata={'channel': 'web'})
                    flash('Please verify your email before logging in.', 'warning')
                    return redirect(url_for('login'))
                _clear_failed_login(identifier, client_ip)
                if _is_two_factor_required(user):
                    session['pending_2fa_user_id'] = user.id

                    try:

                        session['pending_2fa_challenge_id'] = _create_two_factor_challenge(user)

                    except Exception:

                        _log_security_event(user.id, 'auth_2fa_failed', metadata={'channel': 'web', 'reason': 'challenge_create_failed'},

                        )

                        app.logger.exception('Failed to deliver 2FA code for web login user_id=%s', user.id)

                        flash('Unable to send verification code right now. Please try again.', 'danger')

                        return redirect(url_for('login'))

                    _log_security_event(user.id, 'auth_2fa_required', metadata={'channel': 'web'})

                    flash('Enter the 6-digit security code sent to your email.', 'info')

                    return redirect(url_for('login_two_factor'))

                login_user(user)

                _log_security_event(user.id, 'auth_login_success', metadata={'channel': 'web'})

                flash('You are now signed in. Next step: upload a CSV or visit your dashboard for recent reports.', 'success')

                return redirect(url_for('dashboard'))



        _record_failed_login(identifier, client_ip)

        _log_security_event(None, 'auth_login_failed', metadata={

                'channel': 'web',

                'identifier_type': 'email' if '@' in identifier else 'username',

                'has_identifier': 1 if bool(identifier) else 0,

            },

        )

        app.logger.warning(

            'Failed web login attempt ip=%s account=%s',

            client_ip,

            _mask_identifier(identifier),

        )

        flash('Sign-in failed. Check your email/password and try again. If you forgot your password, contact support.', 'danger')

        return redirect(url_for('login'))



    # Legacy GET /login -> SPA handoff
    return redirect(_resolve_public_app_base_url() + '/login', code=302)





@app.route('/login-2fa', methods=['GET', 'POST'])

@limiter.limit('10 per 15 minutes')

def login_two_factor():

    """Second-step web login challenge for accounts with optional 2FA enabled."""

    pending_user_id = session.get('pending_2fa_user_id')

    challenge_id = session.get('pending_2fa_challenge_id')



    if not pending_user_id or not challenge_id:

        flash('Your verification session expired. Please sign in again.', 'warning')

        return redirect(url_for('login'))



    if request.method == 'POST':

        code = (request.form.get('code') or '').strip()

        if not code:

            flash('Enter the verification code from your email.', 'danger')

            return render_template('login_2fa.html')



        verification = _verify_two_factor_challenge_code(challenge_id, code, expected_user_id=pending_user_id)

        if not verification['ok']:

            _log_security_event(pending_user_id, 'auth_2fa_failed', metadata={'channel': 'web', 'status': int(verification.get('status') or 0)},

            )

            flash(verification['error'], 'danger')

            if verification['status'] in (400, 429):

                session.pop('pending_2fa_user_id', None)

                session.pop('pending_2fa_challenge_id', None)

                return redirect(url_for('login'))

            return render_template('login_2fa.html')



        user = load_user(verification['user_id'])

        if not user:

            session.pop('pending_2fa_user_id', None)

            session.pop('pending_2fa_challenge_id', None)

            flash('Account not found. Please sign in again.', 'danger')

            return redirect(url_for('login'))



        login_user(user)

        _log_security_event(user.id, 'auth_2fa_success', metadata={'channel': 'web'})

        session.pop('pending_2fa_user_id', None)

        session.pop('pending_2fa_challenge_id', None)

        flash('Security check complete. You are now signed in.', 'success')

        return redirect(url_for('dashboard'))



    return render_template('login_2fa.html')





# --- SPA handoff: legacy GET /forgot-password -> SPA ---
@app.route('/forgot-password', methods=['GET'])
@limiter.limit('20 per hour')
def forgot_password():
    """Legacy GET: redirect to SPA /forgot-password."""
    return redirect(f'{_resolve_public_app_base_url()}/forgot-password', code=302)


# --- JSON API for SPA password reset ---
@app.route('/api/auth/forgot-password', methods=['POST'])
@limiter.limit('5 per hour')
def api_auth_forgot_password():
    """Request a password reset. Never reveals account existence."""
    try:
        payload = request.get_json(silent=True) or {}
        email = (payload.get('email') or '').strip().lower()
        if not is_valid_email(email):
            return jsonify({'success': False, 'error': 'A valid email address is required.'}), 400
        conn = db_connect()
        c = conn.cursor()
        c.execute('SELECT id FROM users WHERE email = ? OR username = ?', (email, email))
        row = c.fetchone()
        if row:
            token = secrets.token_urlsafe(32)
            expires_at = (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()
            c.execute('INSERT INTO password_reset_tokens (user_id, token, expires_at) VALUES (?, ?, ?)',
                      (row[0], token, expires_at))
            conn.commit()
            reset_link = f'{_resolve_public_app_base_url()}/reset-password/{token}'
            if app.config.get('MAIL_ENABLED'):
                send_password_reset_email(email, reset_link, app.config.get('FIRM_NAME', 'Clarion'))
        conn.close()
        return jsonify({'success': True, 'message': 'If that address is registered, a reset link has been sent.'}), 200
    except Exception as exc:
        app.logger.exception('api_auth_forgot_password error: %s', exc)
        return jsonify({'success': False, 'error': 'Unable to process request. Please try again.'}), 500


@app.route('/api/auth/reset-password/<token>', methods=['GET'])
@limiter.limit('20 per hour')
def api_auth_reset_password_validate(token):
    """Validate a password reset token; returns JSON validity state."""
    try:
        conn = db_connect()
        c = conn.cursor()
        c.execute('SELECT id, expires_at, used_at FROM password_reset_tokens WHERE token = ?', (token,))
        row = c.fetchone()
        conn.close()
        if not row:
            return jsonify({'valid': False, 'reason': 'invalid'}), 200
        expires_at = datetime.fromisoformat(row[1])
        if row[2]:
            return jsonify({'valid': False, 'reason': 'used'}), 200
        if expires_at < datetime.now(timezone.utc):
            return jsonify({'valid': False, 'reason': 'expired'}), 200
        return jsonify({'valid': True}), 200
    except Exception as exc:
        app.logger.exception('api_auth_reset_password_validate error: %s', exc)
        return jsonify({'valid': False, 'reason': 'error'}), 500


@app.route('/api/auth/reset-password/<token>', methods=['POST'])
@limiter.limit('10 per hour')
def api_auth_reset_password_submit(token):
    """Submit a new password for a valid reset token."""
    try:
        payload = request.get_json(silent=True) or {}
        password = payload.get('password') or ''
        confirm_password = payload.get('confirm_password') or ''
        ok_password, password_msg = validate_password_strength(password)
        if not ok_password:
            return jsonify({'success': False, 'error': password_msg}), 400
        if password != confirm_password:
            return jsonify({'success': False, 'error': 'Passwords do not match.'}), 400
        conn = db_connect()
        c = conn.cursor()
        c.execute('SELECT id, user_id, expires_at, used_at FROM password_reset_tokens WHERE token = ?', (token,))
        row = c.fetchone()
        if not row:
            conn.close()
            return jsonify({'success': False, 'error': 'Invalid or expired reset token.'}), 400
        expires_at = datetime.fromisoformat(row[2])
        if row[3] or expires_at < datetime.now(timezone.utc):
            conn.close()
            return jsonify({'success': False, 'error': 'This reset link has expired. Please request a new one.'}), 400
        password_hash = generate_password_hash(password)
        c.execute('UPDATE users SET password_hash = ? WHERE id = ?', (password_hash, row[1]))
        c.execute('UPDATE password_reset_tokens SET used_at = ? WHERE id = ?',
                  (datetime.now(timezone.utc).isoformat(), row[0]))
        conn.commit()
        conn.close()
        return jsonify({'success': True, 'message': 'Password reset successful. You can now sign in.'}), 200
    except Exception as exc:
        app.logger.exception('api_auth_reset_password_submit error: %s', exc)
        return jsonify({'success': False, 'error': 'Unable to reset password. Please try again.'}), 500


# --- Legacy form-based forgot password (not linked from SPA) ---
@app.route('/forgot-password-form', methods=['GET', 'POST'])
@limiter.limit('5 per hour')
def forgot_password_form():

    if request.method == 'POST':

        email = (request.form.get('email') or '').strip().lower()

        generic_msg = 'If that email exists, a reset link has been generated. Contact support to deliver it securely.'

        if not is_valid_email(email):

            flash('Enter a valid email address to request a password reset.', 'danger')

            return render_template('forgot_password.html')



        conn = db_connect()

        c = conn.cursor()

        c.execute('SELECT id FROM users WHERE email = ? OR username = ?', (email, email))

        row = c.fetchone()

        if row:

            token = secrets.token_urlsafe(32)

            expires_at = (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()

            c.execute(

                'INSERT INTO password_reset_tokens (user_id, token, expires_at) VALUES (?, ?, ?)',

                (row[0], token, expires_at),

            )

            conn.commit()

            reset_link = url_for('reset_password', token=token, _external=True)

            if app.config.get('MAIL_ENABLED'):

                send_password_reset_email(email, reset_link, app.config.get('FIRM_NAME', 'Your Firm'))

                flash('If that email exists, a password reset link has been sent.', 'info')

            else:

                flash(f'{generic_msg} Reset link: {reset_link}', 'info')

        else:

            flash(generic_msg, 'info')

        conn.close()

        return redirect(url_for('login'))



    return render_template('forgot_password.html')





# Legacy GET /reset-password/<token> -> SPA handoff
@app.route('/reset-password/<token>', methods=['GET'])
@limiter.limit('20 per hour')
def reset_password_legacy_get(token):
    """Hand off legacy reset link to SPA /reset-password/:token."""
    return redirect(f'{_resolve_public_app_base_url()}/reset-password/{token}', code=302)


@app.route('/reset-password-form/<token>', methods=['GET', 'POST'])
@limiter.limit('10 per hour')
def reset_password(token):

    conn = db_connect()

    c = conn.cursor()

    c.execute(

        '''

        SELECT id, user_id, expires_at, used_at

        FROM password_reset_tokens

        WHERE token = ?

        ''',

        (token,),

    )

    token_row = c.fetchone()



    if not token_row:

        conn.close()

        flash('Invalid password reset token. Request a new one.', 'danger')

        return redirect(url_for('forgot_password'))



    expires_at = datetime.fromisoformat(token_row[2])

    if token_row[3] or expires_at < datetime.now(timezone.utc):

        conn.close()

        flash('This reset token has expired. Please request a new reset link.', 'danger')

        return redirect(url_for('forgot_password'))



    if request.method == 'POST':

        password = request.form.get('password') or ''

        confirm_password = request.form.get('confirm_password') or ''

        ok_password, password_msg = validate_password_strength(password)

        if not ok_password:

            conn.close()

            flash(password_msg, 'danger')

            return render_template('reset_password.html', token=token)

        if password != confirm_password:

            conn.close()

            flash('Passwords do not match. Please re-enter both fields.', 'danger')

            return render_template('reset_password.html', token=token)



        password_hash = generate_password_hash(password)

        c.execute('UPDATE users SET password_hash = ? WHERE id = ?', (password_hash, token_row[1]))

        c.execute('UPDATE password_reset_tokens SET used_at = ? WHERE id = ?', (datetime.now(timezone.utc).isoformat(), token_row[0]))

        conn.commit()

        conn.close()

        flash('Password reset successful. You can now sign in with your new password.', 'success')

        return redirect(url_for('login'))



    conn.close()

    return render_template('reset_password.html', token=token)



@app.route('/logout', methods=['POST'])

@login_required

def logout():

    """Admin logout"""

    logout_user()

    flash('You have been signed out.', 'info')

    return redirect(url_for('marketing_home'))





@app.route('/stripe-webhook', methods=['POST'])

@csrf.exempt

def stripe_webhook():

    payload = request.data

    sig_header = request.headers.get('Stripe-Signature')

    webhook_secret = app.config.get('STRIPE_WEBHOOK_SECRET')



    if not webhook_secret:

        return '', 204



    try:

        event = stripe.Webhook.construct_event(payload, sig_header, webhook_secret)

    except Exception:

        return '', 400



    event_type = event.get('type', '')

    obj = event.get('data', {}).get('object', {})



    if event_type in ('customer.subscription.deleted', 'customer.subscription.updated'):

        subscription_id = obj.get('id')
        status = obj.get('status')

        if subscription_id:
            conn = db_connect()
            c = conn.cursor()
            c.execute('SELECT id FROM users WHERE stripe_subscription_id = ?', (subscription_id,))
            user_rows = c.fetchall()

            if status in ('canceled', 'unpaid', 'incomplete_expired', 'past_due'):
                c.execute(
                    '''
                    UPDATE users
                    SET subscription_status = 'canceled',
                        subscription_type = 'trial'
                    WHERE stripe_subscription_id = ?
                    ''',
                    (subscription_id,),
                )
                for user_row in user_rows:
                    _set_firm_plan_for_user(c, int(user_row[0]), FIRM_PLAN_FREE)
            elif status == 'active':
                recurring_interval = (
                    ((obj.get('items') or {}).get('data') or [{}])[0]
                    .get('price', {})
                    .get('recurring', {})
                    .get('interval')
                )
                stripe_price_id = (
                    ((obj.get('items') or {}).get('data') or [{}])[0]
                    .get('price', {})
                    .get('id')
                )
                if stripe_price_id == app.config.get('STRIPE_PRICE_ID_ANNUAL') or recurring_interval == 'year':
                    subscription_type = 'annual'
                elif stripe_price_id == app.config.get('STRIPE_PRICE_ID_MONTHLY') or recurring_interval == 'month':
                    subscription_type = 'monthly'
                else:
                    subscription_type = None

                if subscription_type:
                    c.execute(
                        '''
                        UPDATE users
                        SET subscription_status = 'active',
                            subscription_type = ?
                        WHERE stripe_subscription_id = ?
                        ''',
                        (subscription_type, subscription_id),
                    )
                    firm_plan = FIRM_PLAN_FIRM if subscription_type == 'annual' else FIRM_PLAN_TEAM
                    for user_row in user_rows:
                        _set_firm_plan_for_user(c, int(user_row[0]), firm_plan)
                else:
                    c.execute(
                        '''
                        UPDATE users
                        SET subscription_status = 'active'
                        WHERE stripe_subscription_id = ?
                        ''',
                        (subscription_id,),
                    )

            conn.commit()
            conn.close()



    return '', 200



# ===== ADMIN ROUTES =====



@app.route('/dashboard')

@login_required

def dashboard():

    """Admin dashboard with overview and account status."""

    analysis = analyze_reviews()

    account_status = current_user.get_account_status()

    _purge_expired_deleted_reports(current_user.id)



    # For backward-compatible UI hints on the dashboard template

    reports_remaining = (

        account_status.get('remaining')

        if account_status.get('type') == 'trial'

        else None

    )

    upgrade_needed = account_status.get('type') == 'trial' and account_status.get('remaining') == 0

    limited = account_status.get('type') == 'trial'



    # Convert themes dict to list of dicts for UI (name, mentions, percentage)

    themes_dict = analysis['themes']

    total_mentions = sum(themes_dict.values()) or 1

    dashboard_themes = [

        {

            'name': name,

            'mentions': int(mentions),

            'percentage': (int(mentions) / total_mentions) * 100.0,

        }

        for name, mentions in themes_dict.items()

    ]



    conn = db_connect()

    c = conn.cursor()

    c.execute(

        '''

        SELECT id, created_at, total_reviews, subscription_type_at_creation

        FROM reports

        WHERE user_id = ?

          AND deleted_at IS NULL

        ORDER BY created_at DESC

        ''',

        (current_user.id,),

    )

    report_rows = c.fetchall()

    conn.close()



    reports_history = []

    for row in report_rows:

        try:

            dt = datetime.strptime(row[1], '%Y-%m-%d %H:%M:%S')

            formatted_date = dt.strftime('%b %d, %Y at %I:%M %p')

        except Exception:

            formatted_date = row[1]



        reports_history.append(

            {

                'id': row[0],

                'created_at': formatted_date,

                'total_reviews': row[2],

                'subscription_type_at_creation': row[3],

                'plan_label': _plan_badge_label(row[3]),

            }

        )



    # Legacy GET /dashboard -> SPA handoff
    return redirect(_resolve_public_app_base_url() + '/dashboard', code=302)





@app.route('/clear-reviews', methods=['POST'])

@login_required

@limiter.limit('10 per hour')

def clear_reviews():

    """

    PR7 / F12: Remove reviews owned by the current user in small batches to

    avoid holding the SQLite write-lock for long stretches.



    Each call deletes at most CHUNK rows in a single BEGIN IMMEDIATE transaction

    and returns JSON describing progress so the caller can loop until done=True.



    For the legacy HTML form path (no Accept: application/json), one chunk is

    deleted per POST and the page is redirected as before; the UI can re-POST

    until the flash message says no rows remain.

    """

    _CHUNK = 500  # rows per transaction � keep WAL pause < ~50 ms at scale



    conn = db_connect()

    c = conn.cursor()

    try:

        conn.execute('BEGIN IMMEDIATE')

        # Collect the next CHUNK review_ids owned by this user.

        c.execute(

            '''

            SELECT review_id FROM review_ownership

            WHERE user_id = ?

            LIMIT ?

            ''',

            (current_user.id, _CHUNK),

        )

        ids = [row[0] for row in c.fetchall()]

        deleted = 0

        if ids:

            placeholders = ','.join('?' * len(ids))

            c.execute(

                f'DELETE FROM reviews WHERE id IN ({placeholders})',

                ids,

            )

            deleted = c.rowcount

        conn.commit()

    except Exception:

        conn.rollback()

        conn.close()

        raise

    conn.close()



    # Check whether more rows remain (outside the write transaction � read-only).

    conn2 = db_connect()

    c2 = conn2.cursor()

    c2.execute(

        'SELECT COUNT(*) FROM review_ownership WHERE user_id = ?',

        (current_user.id,),

    )

    remaining = c2.fetchone()[0]

    conn2.close()



    wants_json = (

        request.accept_mimetypes.best_match(['application/json', 'text/html']) == 'application/json'

        or request.headers.get('X-Requested-With') == 'XMLHttpRequest'

    )

    done = remaining == 0

    _log_security_event(current_user.id, 'purge_batch', metadata={'deleted_this_batch': deleted, 'remaining': remaining, 'done': 1 if done else 0},

    )

    if wants_json:

        return jsonify({

            'success': True,

            'deleted_this_batch': deleted,

            'remaining': remaining,

            'done': done,

            'message': (

                'All reviews cleared.' if done

                else f'Deleted {deleted} reviews this batch; {remaining} remaining.'

            ),

        }), 200



    # HTML form path: redirect with flash; UI must re-POST if remaining > 0.

    if done:

        flash('All reviews were cleared successfully. Next step: upload a new CSV to generate fresh insights.', 'success')

    else:

        flash(

            f'Deleted {deleted} reviews this batch; {remaining} still remaining. '

            'Re-submit to continue clearing.',

            'info',

        )

    return redirect(url_for('dashboard'))


@app.route('/upload', methods=['GET', 'POST'])

@login_required

@limiter.limit('15 per hour')

def upload():

    """CSV upload page for bulk review import with tiered limits."""

    account_status = current_user.get_account_status()

    can_upload = current_user.can_generate_report()



    if request.method == 'POST':

        # TODO: Re-enable email verification gate when email confirmation flow exists.

        access_type = get_report_access_type(current_user.id)

        trial_usage_count, trial_limit = _get_trial_usage_count(current_user.id, current_user.trial_limit)

        can_upload = (

            current_user.has_active_subscription()

            or current_user.has_unused_one_time_reports()

            or (access_type == 'trial' and trial_usage_count < trial_limit)

        )



        if not can_upload:

            flash('You have no remaining report credits. Upgrade or purchase a one-time report to generate new snapshots.', 'warning')

            return redirect(url_for('pricing'))



        if 'file' not in request.files:

            flash('No CSV file was detected in the upload request. Please choose a file and try again.', 'danger')

            return redirect(url_for('upload'))



        file = request.files['file']
        if file.filename == '':
            flash('No file selected. Choose a CSV file with review text and rating columns.', 'danger')
            return redirect(url_for('upload'))

        if (file.mimetype or '').lower() not in ALLOWED_CSV_MIME_TYPES:
            flash('Invalid file type. Please upload a CSV file.', 'danger')
            return redirect(url_for('upload'))

        if not file.filename.lower().endswith('.csv'):
            flash('Unsupported file type. Please upload a .csv file and try again.', 'danger')
            return redirect(url_for('upload'))


        if access_type == 'trial' and trial_usage_count >= trial_limit:

            flash(

                f'Free plan includes {trial_limit} reports per month. Upgrade to continue generating reports.',

                'warning',

            )

            return redirect(url_for('pricing'))



        try:

            valid_rows, csv_error, parse_meta = _parse_csv_upload_rows(file, access_type)

            if csv_error:

                flash(csv_error, 'danger')

                return redirect(url_for('upload'))



            report_hash = _build_report_hash(valid_rows)

            duplicate_report_id = _find_duplicate_report_id(current_user.id, report_hash)

            if duplicate_report_id:

                flash(

                    'This upload appears identical to an existing report. '

                    "To keep your trends accurate, we don't allow uploading the same reviews twice for the same account.",

                    'warning',

                )

                return redirect(url_for('upload'))



            # PR5 (F8/F10/F11): single connection, single BEGIN IMMEDIATE transaction.

            # reviews + report snapshot + credit update all commit together or not at all.

            conn = db_connect()

            c = conn.cursor()

            snapshot_report_id = None  # guard: defined before tx so rollback paths don't raise UnboundLocalError

            count = 0

            try:

                conn.execute('BEGIN IMMEDIATE')



                _insert_user_reviews_tx(c, current_user.id, valid_rows)

                count = len(valid_rows)



                # F8 test hook: set UPLOAD_FAIL_AFTER_REVIEWS=1 to prove rollback.

                # PR5b: only active in dev/test � ignored in production.

                if (

                    os.environ.get('UPLOAD_FAIL_AFTER_REVIEWS') == '1'

                    and (app.config.get('DEBUG') or app.config.get('TESTING'))

                ):

                    raise RuntimeError('PR5 test: forced failure after review inserts')



                snapshot_report_id = _save_report_snapshot_tx(

                    c,

                    current_user.id,

                    subscription_type=access_type,

                    report_hash=report_hash,

                )



                # Credit update AFTER snapshot exists � same transaction.

                if access_type == 'onetime':

                    c.execute(

                        '''

                        UPDATE users

                        SET one_time_reports_used = one_time_reports_used + 1

                        WHERE id = ?

                        ''',

                        (current_user.id,),

                    )

                elif access_type == 'trial':

                    updated_free_usage = max(

                        trial_usage_count + 1,

                        _get_trial_report_snapshot_count(current_user.id),

                    )

                    c.execute(

                        '''

                        UPDATE users

                        SET trial_reviews_used = ?

                        WHERE id = ?

                        ''',

                        (updated_free_usage, current_user.id),

                    )



                conn.commit()

            except Exception:

                conn.rollback()

                raise

            finally:

                conn.close()



            if not snapshot_report_id:

                flash('Upload succeeded, but no snapshot was created because no analyzable reviews were found.', 'warning')

                _log_security_event(current_user.id, 'upload_success', metadata={'report_id': None, 'count': count, 'access_type': access_type, 'channel': 'web'},

                )

                return redirect(url_for('dashboard'))



            if access_type == 'trial' and parse_meta and parse_meta.get('truncated_for_plan'):

                skipped = parse_meta.get('skipped_due_to_plan_limit', 0)

                flash(

                    f'Success! We analyzed the first {FREE_PLAN_MAX_REVIEWS_PER_REPORT} valid reviews for the Free plan '

                    f'and skipped {skipped} additional reviews. Upgrade to analyze all uploaded reviews.',

                    'warning',

                )

            else:

                flash(

                    f'Success! Imported {count} reviews and saved report snapshot #{snapshot_report_id}. '

                    'Next step: open your dashboard to download this report anytime.',

                    'success',

                )

            _log_security_event(current_user.id, 'upload_success', metadata={'report_id': snapshot_report_id, 'count': count, 'access_type': access_type, 'channel': 'web'},

            )

            return redirect(url_for('dashboard'))



        except Exception as exc:

            _log_security_event(current_user.id, 'upload_failed', metadata={'error_class': type(exc).__name__, 'channel': 'web'},

            )

            flash('We could not process that CSV upload. Please verify the file format and try again.', 'danger')

            return redirect(url_for('upload'))



    # Legacy GET /upload -> SPA handoff
    return redirect(_resolve_public_app_base_url() + '/upload', code=302)



PDF_TEMPLATE_VERSION = 'GovBrief Template v2026-03-03-1'





def _truthy_query_param(name: str) -> bool:

    value = (request.args.get(name) or '').strip().lower()

    return value in {'1', 'true', 'yes', 'y', 'on'}





def _store_report_pdf_artifact(user_id: int, report_id: int, pdf_bytes: bytes, generated_at: Optional[str] = None) -> None:

    timestamp = generated_at or datetime.utcnow().isoformat()

    conn = db_connect()

    c = conn.cursor()

    c.execute(

        '''

        INSERT INTO report_pdf_artifacts (report_id, user_id, pdf_blob, generated_at, updated_at)

        VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)

        ON CONFLICT(report_id) DO UPDATE SET

            user_id = excluded.user_id,

            pdf_blob = excluded.pdf_blob,

            generated_at = excluded.generated_at,

            updated_at = CURRENT_TIMESTAMP

        ''',

        (report_id, user_id, pdf_bytes, timestamp),

    )

    conn.commit()

    conn.close()





def _load_report_pdf_artifact(report_id: int) -> Optional[bytes]:

    conn = db_connect()

    c = conn.cursor()

    c.execute(

        '''

        SELECT pdf_blob

        FROM report_pdf_artifacts

        WHERE report_id = ?

        ''',

        (report_id,),

    )

    row = c.fetchone()

    conn.close()

    if not row or row[0] is None:

        return None

    return bytes(row[0])





def _pdf_inline_response(pdf_data: bytes | BytesIO, brief_date: str):

    stream = pdf_data if isinstance(pdf_data, BytesIO) else BytesIO(pdf_data)

    if isinstance(stream, BytesIO):

        stream.seek(0)

    response = send_file(

        stream,

        as_attachment=False,

        mimetype='application/pdf',

    )

    response.headers['Content-Disposition'] = f'inline; filename=\"clarion-governance-brief-{brief_date}.pdf\"'
    response.headers['Content-Type'] = 'application/pdf'

    response.headers['Cache-Control'] = 'no-store, max-age=0'

    response.headers['Pragma'] = 'no-cache'

    response.headers['Expires'] = '0'

    response.headers['X-GovBrief-Template-Version'] = PDF_TEMPLATE_VERSION

    return response



@app.route('/download-pdf')

@login_required

@limiter.limit('25 per hour')

def download_pdf():
    """Generate and download PDF report based on user's plan."""

    analysis = analyze_reviews()



    if analysis['total_reviews'] == 0:

        flash('No reviews found. Upload a CSV to get started, then try generating a PDF again.', 'warning')

        return redirect(url_for('dashboard'))



    # Enrich themes with percentage values for the PDF

    themes_dict = analysis['themes']

    total_mentions = sum(themes_dict.values()) or 1



    enriched_themes = []

    for name, mentions in themes_dict.items():

        enriched_themes.append({

            'name': name,

            'mentions': int(mentions),

            'percentage': (int(mentions) / total_mentions) * 100.0,

        })



    # Determine paid status and subscription type for implementation plans

    access_type = get_report_access_type(current_user.id)

    access_context = _report_access_context(access_type)

    is_paid_user = access_context['access_level'] == 'paid'

    subscription_type = access_type

    branding = _get_account_branding(current_user.id)

    trend_points = _get_report_trend_points(current_user.id, limit=12)

    exposure_snapshot = _compute_exposure_snapshot(

        analysis['avg_rating'],

        enriched_themes,

        trend_points,

        [],

    )

    current_firm_name = app.config['FIRM_NAME']

    try:

        resolved_ctx = _resolve_current_firm_context()

        current_firm_name = (resolved_ctx.get('firm_name') or '').strip() or current_firm_name

    except Exception:

        current_firm_name = (current_user.firm_name or current_firm_name)



    pdf_buffer = generate_pdf_report(
        firm_name=current_firm_name,

        total_reviews=analysis['total_reviews'],

        avg_rating=analysis['avg_rating'],

        themes=enriched_themes,

        top_praise=analysis['top_praise'],

        top_complaints=analysis['top_complaints'],

        is_paid_user=is_paid_user,

        subscription_type=subscription_type,

        access_level=access_context['access_level'],

        plan_type=access_context['plan_type'],

        analysis_period=None,

        report_title='Client Feedback Report',

        report_created_at=datetime.utcnow().isoformat(),

        trend_points=trend_points,

        implementation_items=[],

        branding=branding,
        exposure_snapshot=exposure_snapshot,
        governance_signals=[],
        governance_recommendations=[],
    )


    brief_date = datetime.now().strftime("%Y%m%d")

    return _pdf_inline_response(pdf_buffer, brief_date)





@app.route('/download-report/<int:report_id>')

@login_required

@limiter.limit('25 per hour')

def download_report(report_id):
    _purge_expired_deleted_reports(current_user.id)

    conn = db_connect()

    c = conn.cursor()

    c.execute(

        '''

        SELECT id, user_id, created_at, total_reviews, avg_rating, themes, top_praise, top_complaints, subscription_type_at_creation

        FROM reports

        WHERE id = ?

          AND user_id = ?

          AND deleted_at IS NULL

        ''',

        (report_id, current_user.id),

    )

    report = c.fetchone()

    conn.close()



    if not report:

        flash('That report was not found for your account. Please choose a report from your history list.', 'danger')

        return redirect(url_for('dashboard'))



    raw_themes = _deserialize_report_data(report[5], {})

    themes = []

    total_mentions = sum(raw_themes.values()) or 1

    for name, mentions in raw_themes.items():

        themes.append(

            {

                'name': name,

                'mentions': int(mentions),

                'percentage': (int(mentions) / total_mentions) * 100.0,

            }

        )



    top_praise = _deserialize_report_data(report[6], [])

    top_complaints = _deserialize_report_data(report[7], [])

    report_access = report[8] or 'trial'

    access_context = _report_access_context(report_access)

    is_paid_user = access_context['access_level'] == 'paid'

    subscription_type = report_access

    branding = _get_account_branding(current_user.id)

    conn_scope = db_connect()

    c_scope = conn_scope.cursor()

    scope_firm_id = _resolve_user_active_firm_id(c_scope, current_user.id) or current_user.id

    conn_scope.close()

    trend_points = _get_report_trend_points(scope_firm_id, limit=12)

    implementation_items = _get_report_action_rows(scope_firm_id, report_id, limit=20)
    governance_insights = _get_report_governance_insights(report_id, limit=5)
    exposure_snapshot = _compute_exposure_snapshot(
        report[4],
        themes,
        trend_points,
        implementation_items,
    )

    current_firm_name = app.config['FIRM_NAME']

    try:

        resolved_ctx = _resolve_current_firm_context()

        current_firm_name = (resolved_ctx.get('firm_name') or '').strip() or current_firm_name

    except Exception:

        current_firm_name = (current_user.firm_name or current_firm_name)



    pdf_buffer = generate_pdf_report(

        firm_name=current_firm_name,

        total_reviews=report[3],

        avg_rating=report[4],

        themes=themes,

        top_praise=top_praise,

        top_complaints=top_complaints,

        is_paid_user=is_paid_user,

        subscription_type=subscription_type,

        access_level=access_context['access_level'],

        plan_type=access_context['plan_type'],

        analysis_period=None,

        report_title=_report_display_name(report_id, report[2]),

        report_created_at=report[2],

        trend_points=trend_points,

        implementation_items=implementation_items,
        branding=branding,
        exposure_snapshot=exposure_snapshot,
        governance_signals=governance_insights.get('signals', []),
        governance_recommendations=governance_insights.get('recommendations', []),
    )


    brief_date = datetime.utcnow().strftime("%Y%m%d")

    return _pdf_inline_response(pdf_buffer, brief_date)





@app.route('/account')

@login_required

def account():

    account_status = current_user.get_account_status()

    portal_url = None

    if current_user.stripe_customer_id and current_user.has_active_subscription():

        try:

            session = stripe.billing_portal.Session.create(

                customer=current_user.stripe_customer_id,

                return_url=url_for('account', _external=True),

            )

            portal_url = session.url

        except Exception:

            portal_url = None



    usage = {

        'trial_used': trial_usage_count,

        'trial_limit': trial_limit,

        'trial_remaining': max(0, trial_limit - trial_usage_count),

        'one_time_purchased': current_user.one_time_reports_purchased,

        'one_time_used': current_user.one_time_reports_used,

        'one_time_remaining': current_user.get_remaining_one_time_reports(),

    }



    # Legacy GET /account -> SPA handoff
    return redirect(_resolve_public_app_base_url() + '/account', code=302)





@app.route('/export-data')
@login_required
@limiter.limit('5 per hour')
def export_data():
    def _csv_safe_cell(value):
        text = '' if value is None else str(value)
        if text and text[0] in ('=', '+', '-', '@'):
            return f"'{text}"
        return text

    conn = db_connect()
    c = conn.cursor()
    c.execute(

        '''

        SELECT r.date, r.rating, r.review_text

        FROM reviews r

        INNER JOIN review_ownership ro ON ro.review_id = r.id

        WHERE ro.user_id = ?

        ORDER BY r.created_at DESC

        ''',

        (current_user.id,),

    )

    rows = c.fetchall()

    conn.close()



    csv_buffer = StringIO()
    writer = csv.writer(csv_buffer)
    writer.writerow(['date', 'rating', 'review_text'])
    for row in rows:
        writer.writerow([_csv_safe_cell(cell) for cell in row])


    mem = StringIO(csv_buffer.getvalue())

    from io import BytesIO

    out = BytesIO(mem.getvalue().encode('utf-8'))

    out.seek(0)

    return send_file(

        out,

        as_attachment=True,

        download_name=f'user_data_export_{current_user.id}.csv',

        mimetype='text/csv',

    )



@app.route('/health')

def health():

    return jsonify({'status': 'ok', 'service': 'law-firm-feedback-saas'}), 200





@app.route('/metrics')

@login_required

def metrics():

    if not current_user.is_admin:

        _log_security_event(current_user.id, 'admin_authz_denied', metadata={'path': '/metrics', 'reason': 'not_admin'},

        )

        return jsonify({'success': False, 'error': 'Forbidden'}), 403

    total = REQUEST_METRICS['requests_total']

    avg_latency = (REQUEST_METRICS['latency_ms_total'] / total) if total else 0.0

    return jsonify({

        'requests_total': total,

        'errors_total': REQUEST_METRICS['errors_total'],

        'avg_latency_ms': round(avg_latency, 2),

    }), 200





# ===== JSON API ENDPOINTS (for React frontend) =====



@app.route('/api/version', methods=['GET'])
def api_version():
    """Backend fingerprint endpoint for frontend wiring diagnostics."""

    return jsonify({

        'success': True,

        'service': 'law-firm-feedback-saas',

        'api_version': '2026-02-23',

        'routes': {

            'auth_login': '/api/auth/login',

            'auth_register': '/api/auth/register',

            'auth_me': '/api/auth/me',

            'account_plan': '/api/account/plan',

            'account_branding': '/api/account/branding',

            'account_branding_logo': '/api/account/branding/logo',

            'account_branding_theme': '/api/account/branding/theme',

            'auth_logout': '/api/auth/logout',

            'dashboard_stats': '/api/dashboard/stats',

            'dashboard_reports': '/api/reports',

            'dashboard_report_detail': '/api/reports/<id>',

            'dashboard_report_actions': '/api/reports/<id>/actions',

            'dashboard_report_executive_summary': '/api/reports/<id>/executive-summary',

            'dashboard_reports_deleted': '/api/reports/deleted',

            'dashboard_report_restore': '/api/reports/<id>/restore',

            'dashboard_credits': '/api/credits',

            'report_packs_schedule': '/api/report-packs/schedule',

            'report_packs_send_now': '/api/report-packs/send-now',

            'upload': '/api/upload',

            'billing_checkout': '/api/billing/checkout',

            'billing_checkout_finalize': '/api/billing/checkout/finalize',

        },

    }), 200


@app.route('/api/system/status', methods=['GET'])
def api_system_status():
    """Expose non-sensitive runtime flags for frontend environment UX."""
    can_view_internal_flags = bool(getattr(current_user, 'is_authenticated', False) and getattr(current_user, 'is_admin', False))
    return jsonify(
        {
            'success': True,
            'dev_mode': bool(app.config.get('DEV_MODE', False)) if can_view_internal_flags else False,
            'internal_testing_available': bool(app.config.get('DEV_MODE', False)) if can_view_internal_flags else False,
        }
    ), 200


@app.route('/api/csrf-token', methods=['GET'])
def api_csrf_token():
    """Return a CSRF token for SPA mutating requests."""
    return jsonify({'success': True, 'csrf_token': generate_csrf()}), 200


def _resolve_frontend_origin():
    """Infer the SPA origin for Stripe return URLs."""

    origin = request.headers.get('Origin')

    if origin:

        return origin.rstrip('/')



    referer = request.headers.get('Referer')

    if referer:

        parsed = urlparse(referer)

        if parsed.scheme and parsed.netloc:

            return f'{parsed.scheme}://{parsed.netloc}'



    return os.environ.get('FRONTEND_ORIGIN', 'http://localhost:8081').rstrip('/')


def _resolve_public_app_base_url():
    """Resolve the public SPA base URL for email links and redirects."""
    explicit_base = (
        os.environ.get('FRONTEND_BASE_URL')
        or os.environ.get('APP_BASE_URL')
        or ''
    ).strip().rstrip('/')
    if explicit_base:
        return explicit_base

    frontend_origin = _resolve_frontend_origin()
    if frontend_origin:
        return frontend_origin.rstrip('/')

    return request.host_url.rstrip('/')


def _ensure_stripe_customer_id():

    """Return existing Stripe customer ID or create one for the current user."""

    if current_user.stripe_customer_id:

        return current_user.stripe_customer_id



    customer = stripe.Customer.create(

        email=current_user.email or current_user.username,

        metadata={'user_id': str(current_user.id)},

    )

    conn = db_connect()

    c = conn.cursor()

    c.execute(

        'UPDATE users SET stripe_customer_id = ? WHERE id = ?',

        (customer.id, current_user.id),

    )

    conn.commit()

    conn.close()

    return customer.id


def _normalize_checkout_plan(raw_plan):
    requested_plan = str(raw_plan or '').strip().lower()
    plan_aliases = {
        'team': 'monthly',
        'firm': 'annual',
        'professional': 'monthly',
        'leadership': 'annual',
        'pro_monthly': 'monthly',
        'pro_annual': 'annual',
        'onetime': 'onetime',
        'one_time': 'onetime',
        'monthly': 'monthly',
        'annual': 'annual',
    }
    return requested_plan, plan_aliases.get(requested_plan)



@app.route('/api/billing/checkout', methods=['POST'])
@limiter.limit('20 per hour')
@login_required
def api_billing_checkout():
    """Create Stripe checkout session for one-time or subscription plans."""

    payload = request.get_json(silent=True) or {}

    requested_plan, plan = _normalize_checkout_plan(payload.get('plan'))

    if plan not in ('onetime', 'monthly', 'annual'):
        return jsonify({'success': False, 'error': 'Invalid plan. Choose team or firm.'}), 400



    if not app.config.get('STRIPE_SECRET_KEY'):

        return jsonify({'success': False, 'error': 'Billing is not configured on this server.'}), 503



    if plan == 'onetime':

        price_id = app.config.get('STRIPE_PRICE_ID_ONETIME')

    elif plan == 'annual':

        price_id = app.config.get('STRIPE_PRICE_ID_ANNUAL')

    else:

        price_id = app.config.get('STRIPE_PRICE_ID_MONTHLY')



    if not price_id:

        return jsonify({'success': False, 'error': 'Price configuration is missing for this plan.'}), 503



    try:

        customer_id = _ensure_stripe_customer_id()

        frontend_origin = _resolve_frontend_origin()

        success_url = (

            f'{frontend_origin}/pricing?checkout=success&plan={requested_plan or plan}'

            '&session_id={CHECKOUT_SESSION_ID}'

        )

        cancel_url = f'{frontend_origin}/pricing?checkout=canceled&plan={requested_plan or plan}'



        checkout_session = stripe.checkout.Session.create(

            customer=customer_id,

            payment_method_types=['card'],

            line_items=[{'price': price_id, 'quantity': 1}],

            mode='payment' if plan == 'onetime' else 'subscription',

            success_url=success_url,

            cancel_url=cancel_url,

            # PR3b: bind session to user so finalize can verify ownership

            client_reference_id=str(current_user.id),

            metadata={'user_id': str(current_user.id), 'plan': plan},

        )

        _log_security_event(current_user.id, 'billing_checkout_created', metadata={'plan': plan, 'channel': 'api'},

        )

        return jsonify({'success': True, 'checkout_url': checkout_session.url}), 200

    except Exception:

        app.logger.exception('Failed to create checkout session for user %s plan %s', current_user.id, plan)

        return jsonify({'success': False, 'error': 'Unable to start checkout right now.'}), 500



@app.route('/api/billing/checkout/finalize', methods=['POST'])
@limiter.limit('30 per hour')
@login_required
def api_billing_checkout_finalize():
    """Finalize checkout after Stripe redirects back to the SPA."""

    payload = request.get_json(silent=True) or {}

    session_id = payload.get('session_id')

    requested_plan, plan = _normalize_checkout_plan(payload.get('plan'))


    if not session_id or plan not in ('onetime', 'monthly', 'annual'):
        return jsonify({'success': False, 'error': 'Missing session_id or invalid plan.'}), 400



    if not app.config.get('STRIPE_SECRET_KEY'):

        return jsonify({'success': False, 'error': 'Billing is not configured on this server.'}), 503



    if not current_user.stripe_customer_id:

        return jsonify({'success': False, 'error': 'No Stripe customer found for this account.'}), 400



    try:

        checkout_session = stripe.checkout.Session.retrieve(session_id)

    except Exception:

        app.logger.exception('Failed to retrieve checkout session %s for user %s', session_id, current_user.id)

        return jsonify({'success': False, 'error': 'Unable to verify checkout session.'}), 500



    if str(checkout_session.customer) != str(current_user.stripe_customer_id):

        _log_security_event(current_user.id, 'billing_checkout_mismatch', metadata={'route': 'api_billing_checkout_finalize', 'session_id': session_id, 'reason': 'customer_mismatch'},

        )

        return jsonify({'success': False, 'error': 'Checkout session does not match this account.'}), 403



    # PR3b: verify user-binding embedded at session creation time

    # PR3c: use attribute access � Stripe objects may not behave like dicts.

    ref_id = getattr(checkout_session, 'client_reference_id', '') or ''

    meta = getattr(checkout_session, 'metadata', {}) or {}

    meta_uid = meta.get('user_id', '') if isinstance(meta, dict) else ''

    if ref_id and ref_id != str(current_user.id):

        _log_security_event(current_user.id, 'billing_checkout_mismatch', metadata={'route': 'api_billing_checkout_finalize', 'session_id': session_id, 'reason': 'client_reference_mismatch'},

        )

        return jsonify({'success': False, 'error': 'Checkout session does not belong to this account.'}), 403

    if not ref_id and meta_uid and meta_uid != str(current_user.id):

        _log_security_event(current_user.id, 'billing_checkout_mismatch', metadata={'route': 'api_billing_checkout_finalize', 'session_id': session_id, 'reason': 'metadata_user_mismatch'},

        )

        return jsonify({'success': False, 'error': 'Checkout session does not belong to this account.'}), 403



    conn = db_connect()

    c = conn.cursor()



    try:

        # PR3b: explicit BEGIN IMMEDIATE so INSERT + UPDATE are one atomic transaction

        conn.execute('BEGIN IMMEDIATE')

        if plan == 'onetime':

            if checkout_session.payment_status != 'paid':

                conn.rollback()

                conn.close()

                return jsonify({'success': False, 'error': 'Payment has not completed yet.'}), 400



            # F4: dedupe gate

            c.execute(

                '''

                INSERT OR IGNORE INTO processed_checkout_sessions

                    (session_id, user_id, plan, processed_at)

                VALUES (?, ?, 'onetime', ?)

                ''',

                (session_id, current_user.id, datetime.now(timezone.utc).isoformat()),

            )

            if c.rowcount == 0:

                conn.rollback()

                conn.close()

                _log_security_event(current_user.id, 'billing_checkout_finalized', metadata={'plan': plan, 'session_id': session_id, 'channel': 'api'},

                )

                return jsonify({'success': True, 'plan': plan, 'already_processed': True}), 200



            c.execute(

                '''

                UPDATE users

                SET one_time_reports_purchased = one_time_reports_purchased + 1

                WHERE id = ?

                ''',

                (current_user.id,),

            )

        else:

            # PR3c: attribute access for subscription field.

            subscription_id = getattr(checkout_session, 'subscription', None)

            if not subscription_id:

                conn.rollback()

                conn.close()

                return jsonify({'success': False, 'error': 'Subscription checkout is not complete yet.'}), 400



            c.execute(

                '''

                UPDATE users

                SET stripe_subscription_id = ?,

                    subscription_status = 'active',

                    subscription_type = ?

                WHERE id = ?

                ''',

                (subscription_id, plan, current_user.id),

            )
            # Keep firm-level plan in sync immediately after checkout finalize.
            target_firm_plan = FIRM_PLAN_FIRM if plan == 'annual' else FIRM_PLAN_TEAM
            _set_firm_plan_for_user(c, current_user.id, target_firm_plan)



        conn.commit()

        conn.close()

        _log_security_event(current_user.id, 'billing_checkout_finalized', metadata={'plan': plan, 'session_id': session_id, 'channel': 'api'},

        )

        response_plan = 'team' if plan == 'monthly' else 'firm' if plan == 'annual' else 'onetime'
        return jsonify({'success': True, 'plan': response_plan}), 200

    except Exception:

        conn.rollback()

        conn.close()

        app.logger.exception('Failed to finalize checkout for user %s session %s', current_user.id, session_id)

        return jsonify({'success': False, 'error': 'Unable to finalize checkout.'}), 500



@app.route('/api/auth/login', methods=['POST'])
@csrf.exempt
@limiter.limit('5 per minute')
def api_login():
    """JSON login endpoint for React frontend"""

    try:

        data = request.get_json(silent=True) or {}

        email = (data.get('email') or '').strip().lower()

        password = data.get('password') or ''

        client_ip = _get_client_ip()

        # PR4b: same diagnostic log as web login � verify PROXY_HOPS in ops logs.

        app.logger.debug(

            'login attempt api remote_addr=%s xff_raw=%s xfp=%s',

            client_ip,

            request.headers.get('X-Forwarded-For', '-'),

            request.headers.get('X-Forwarded-Proto', '-'),

        )



        if not email or not password:

            return jsonify({'success': False, 'error': 'Email and password are required'}), 400



        backoff_seconds = _login_backoff_seconds(email, client_ip)

        if backoff_seconds > 0:

            time_module.sleep(backoff_seconds)



        conn = db_connect()

        c = conn.cursor()

        c.execute(

            'SELECT id, password_hash FROM users WHERE email = ? OR username = ?',

            (email, email),

        )

        user_data = c.fetchone()

        conn.close()



        if user_data and check_password_hash(user_data[1], password):
            user = load_user(user_data[0])
            if user:
                if not is_email_verified(user.id) and not _allow_dev_auth_shortcuts_for_email(user.email):
                    _record_failed_login(email, client_ip)
                    _log_security_event(user.id, 'auth_login_blocked_unverified', metadata={'channel': 'api'})
                    return jsonify({'success': False, 'error': 'Please verify your email before logging in.'}), 403
                _clear_failed_login(email, client_ip)
                if _is_two_factor_required(user):
                    challenge_id = _create_two_factor_challenge(user)
                    _log_security_event(user.id, 'auth_2fa_required', metadata={'channel': 'api'})

                    return jsonify(

                        {

                            'success': True,

                            'requires_2fa': True,

                            'challenge_id': challenge_id,

                            'message': 'Enter the 6-digit code sent to your email to complete sign-in.',

                        }

                    ), 202



                login_user(user, remember=True)

                _log_security_event(user.id, 'auth_login_success', metadata={'channel': 'api'})

                return jsonify({

                    'success': True,

                    'user': _user_response_payload(user),

                }), 200



        _record_failed_login(email, client_ip)

        _log_security_event(None, 'auth_login_failed', metadata={

                'channel': 'api',

                'identifier_type': 'email' if '@' in email else 'username',

                'has_identifier': 1 if bool(email) else 0,

            },

        )

        app.logger.warning(

            'Failed login attempt ip=%s account=%s',

            client_ip,

            _mask_identifier(email),

        )

        return jsonify({'success': False, 'error': 'Invalid email or password'}), 401

    except Exception:

        return _safe_api_error(

            'Login failed due to a server error. Please try again.',

            log_message='api_login failed',

        )





@app.route('/api/auth/2fa/verify', methods=['POST'])

@csrf.exempt

@limiter.limit('10 per 15 minutes')

def api_verify_two_factor():

    """Finalize login challenge for users with optional email OTP enabled."""

    if not app.config.get('ENABLE_2FA'):

        return jsonify({'success': False, 'error': 'Two-factor authentication is not enabled.'}), 404



    payload = request.get_json(silent=True) or {}

    challenge_id = (payload.get('challenge_id') or '').strip()

    code = (payload.get('code') or '').strip()



    if not challenge_id or not code:

        return jsonify({'success': False, 'error': 'Challenge ID and code are required.'}), 400



    try:

        verification = _verify_two_factor_challenge_code(challenge_id, code)

        if not verification['ok']:

            _log_security_event(None, 'auth_2fa_failed', metadata={'channel': 'api', 'status': int(verification.get('status') or 0)},

            )

            return jsonify({'success': False, 'error': verification['error']}), verification['status']



        user = load_user(verification['user_id'])

        if not user:

            return jsonify({'success': False, 'error': 'Account not found.'}), 404



        login_user(user, remember=True)

        _log_security_event(user.id, 'auth_2fa_success', metadata={'channel': 'api'})

        return jsonify({'success': True, 'user': _user_response_payload(user)}), 200

    except Exception:

        return _safe_api_error(

            'Unable to verify your security code right now.',

            log_message='api_verify_two_factor failed',

        )





@app.route('/api/auth/2fa/enable', methods=['POST'])
@login_required
def api_enable_two_factor():
    """Enable optional email OTP with password re-verification."""

    if not app.config.get('ENABLE_2FA'):

        return jsonify({'success': False, 'error': 'Two-factor authentication is not enabled.'}), 404



    payload = request.get_json(silent=True) or {}

    password = payload.get('password') or ''

    if not password:

        return jsonify({'success': False, 'error': 'Password is required.'}), 400



    try:

        if not _check_password_for_user(current_user.id, password):

            return jsonify({'success': False, 'error': 'Invalid password.'}), 401



        conn = db_connect()

        c = conn.cursor()

        c.execute(

            '''

            UPDATE users

            SET two_factor_enabled = 1, two_factor_method = 'email'

            WHERE id = ?

            ''',

            (current_user.id,),

        )

        conn.commit()

        conn.close()

        return jsonify({'success': True, 'two_factor_enabled': True}), 200

    except Exception:

        return _safe_api_error(

            'Unable to enable two-factor authentication.',

            log_message='api_enable_two_factor failed',

        )





@app.route('/api/auth/2fa/disable', methods=['POST'])
@login_required
def api_disable_two_factor():
    """Disable optional email OTP with password re-verification."""

    if not app.config.get('ENABLE_2FA'):

        return jsonify({'success': False, 'error': 'Two-factor authentication is not enabled.'}), 404



    payload = request.get_json(silent=True) or {}

    password = payload.get('password') or ''

    if not password:

        return jsonify({'success': False, 'error': 'Password is required.'}), 400



    try:

        if not _check_password_for_user(current_user.id, password):

            return jsonify({'success': False, 'error': 'Invalid password.'}), 401



        conn = db_connect()

        c = conn.cursor()

        c.execute(

            '''

            UPDATE users

            SET two_factor_enabled = 0

            WHERE id = ?

            ''',

            (current_user.id,),

        )

        conn.commit()

        conn.close()

        return jsonify({'success': True, 'two_factor_enabled': False}), 200

    except Exception:

        return _safe_api_error(

            'Unable to disable two-factor authentication.',

            log_message='api_disable_two_factor failed',

        )





@app.route('/api/auth/register', methods=['POST'])
@csrf.exempt
@limiter.limit('5 per minute')
def api_register():
    """JSON registration endpoint for React frontend"""

    try:
        data = request.get_json() or {}
        email = (data.get('email') or '').strip().lower()
        password = data.get('password') or ''
        full_name = (data.get('full_name') or '').strip()
        firm_name = (data.get('firm_name') or '').strip()


        errors = {}



        # Validation
        if not is_valid_email(email):
            errors['email'] = 'Enter a valid business email address.'
        if firm_name and (len(firm_name) < 2 or len(firm_name) > MAX_FIRM_NAME_LENGTH):
            errors['firm_name'] = f'Firm name must be 2-{MAX_FIRM_NAME_LENGTH} characters.'
        if len(full_name) < 2 or len(full_name) > 120:

            errors['full_name'] = 'Enter your full name (2-120 characters).'

        ok_password, password_msg = validate_password_strength(password)

        if not ok_password:

            errors['password'] = password_msg



        if errors:

            return jsonify({'success': False, 'error': 'Validation failed', 'errors': errors}), 400



        sanitized_firm_name = bleach.clean(firm_name, strip=True)
        stored_firm_name = sanitized_firm_name or app.config.get('FIRM_NAME', 'Your Firm')

        password_hash = generate_password_hash(password)
        created_at = datetime.now(timezone.utc).isoformat()

        user_id = None
        for attempt in range(2):
            conn = None
            try:
                conn = db_connect()
                c = conn.cursor()

                # Check if account exists
                c.execute(
                    'SELECT id FROM users WHERE email = ? OR username = ?',
                    (email, email),
                )
                existing = c.fetchone()
                if existing:
                    conn.close()
                    return jsonify({'success': False, 'error': 'An account with that email already exists'}), 409

                # Create user
                c.execute(
                    '''
                    INSERT INTO users (
                        username,
                        email,
                        firm_name,
                        password_hash,
                        subscription_type,
                        created_at,
                        email_verified
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                    ''',
                    (
                        email,
                        email,
                        stored_firm_name,
                        password_hash,
                        'trial',
                        created_at,
                        1 if _allow_dev_auth_shortcuts_for_email(email) else 0,
                    ),
                )
                user_id = c.lastrowid

                # Set trial limit
                c.execute(
                    'UPDATE users SET trial_limit = ? WHERE id = ?',
                    (3, user_id),
                )

                conn.commit()
                conn.close()
                break
            except _DB_OPERATIONAL_ERRORS as exc:
                if conn is not None:
                    try:
                        conn.close()
                    except Exception:
                        pass
                missing_schema = 'no such table' in str(exc).lower()
                if attempt == 0 and missing_schema:
                    app.logger.warning('api_register detected missing schema; running init_db() before retry.')
                    init_db()
                    continue
                raise



        delivery_status = _verification_delivery_status()
        email_sent = False
        delivery_result = None
        if _allow_dev_auth_shortcuts_for_email(email):
            # DEV_MODE ONLY � remove before production
            app.logger.info("DEV_MODE internal auth shortcut: email verification skipped for %s", email)
        else:
            verification_token = create_email_verification_token(user_id, email)
            verify_link = _public_verify_email_link(verification_token)
            delivery_result = send_email_verification_link_with_result(email, verify_link, stored_firm_name)
            email_sent = delivery_result.success

        delivery_payload = _verification_delivery_response_payload(delivery_status, delivery_result)

        return jsonify({
            'success': True,
            'verified': bool(_allow_dev_auth_shortcuts_for_email(email)),
            'requires_verification': not _allow_dev_auth_shortcuts_for_email(email),
            'verification_sent': bool(email_sent),
            **delivery_payload,
            'support_email': SUPPORT_EMAIL,
            'email': email,
        }), 201
    except Exception as _reg_exc:

        import traceback as _reg_tb

        app.logger.error('[api_register] EXCEPTION: %s', _reg_exc)

        app.logger.error('[api_register] %s', _reg_tb.format_exc())

        return _safe_api_error(

            'Registration failed due to a server error.',

            log_message='api_register failed',

        )





@app.route('/api/auth/me', methods=['GET'])
def api_get_me():
    """Get current user info"""
    if not current_user.is_authenticated:
        session.clear()
        return jsonify({'success': False, 'error': 'Not authenticated'}), 401

    try:
        if _has_suspended_membership_without_active(current_user.id):
            logout_user()
            session.clear()
            return jsonify({'success': False, 'error': 'Session is no longer valid for this account.'}), 403
        return jsonify({
            'success': True,
            'user': _user_response_payload(current_user),
        }), 200
    except Exception:

        return _safe_api_error(
            'Unable to load session details.',
            log_message='api_get_me failed',
        )


@app.route('/api/auth/verify-email/<token>', methods=['GET'])
@csrf.exempt
@limiter.limit('30 per hour')
def api_verify_email(token):
    """Verify email token and activate account for login."""
    token_data, token_error = decode_email_verification_token(token)
    if token_error:
        return jsonify({'verified': False, 'error': token_error}), 400

    try:
        conn = db_connect()
        c = conn.cursor()
        c.execute('SELECT id, email FROM users WHERE id = ?', (token_data['user_id'],))
        user_row = c.fetchone()
        if not user_row:
            conn.close()
            return jsonify({'verified': False, 'error': 'Verification token is not valid for an active account.'}), 400

        user_email = str(user_row[1] or '').strip().lower()
        if user_email != token_data['email']:
            conn.close()
            return jsonify({'verified': False, 'error': 'Verification token does not match this account.'}), 400

        now_iso = datetime.now(timezone.utc).isoformat()
        c.execute('UPDATE users SET email_verified = 1, is_verified = 1 WHERE id = ?', (token_data['user_id'],))
        c.execute(
            '''
            INSERT INTO user_email_verification (user_id, verified_at)
            VALUES (?, ?)
            ON CONFLICT(user_id) DO UPDATE SET verified_at = excluded.verified_at
            ''',
            (token_data['user_id'], now_iso),
        )
        conn.commit()
        conn.close()
        verified_user = load_user(str(token_data['user_id']))
        if verified_user:
            login_user(verified_user, remember=False)
        return jsonify({
            'verified': True,
            'user': _user_response_payload(verified_user) if verified_user else None,
        }), 200
    except Exception:
        return _safe_api_error(
            'Unable to verify email right now.',
            log_message='api_verify_email failed',
        )


@app.route('/api/onboarding/complete', methods=['POST'])
@login_required
def api_onboarding_complete():
    try:
        conn = db_connect()
        c = conn.cursor()
        c.execute('UPDATE users SET onboarding_complete = 1 WHERE id = ?', (current_user.id,))
        conn.commit()
        conn.close()
        refreshed_user = load_user(str(current_user.id))
        if refreshed_user:
            login_user(refreshed_user, remember=False)
        return jsonify({
            'success': True,
            'user': _user_response_payload(refreshed_user) if refreshed_user else None,
        }), 200
    except Exception:
        return _safe_api_error(
            'Unable to finish onboarding right now.',
            log_message='api_onboarding_complete failed',
        )


@app.route('/api/auth/resend-verification', methods=['POST'])
@csrf.exempt
@limiter.limit('5 per minute')
def api_resend_verification():
    """Resend email verification link for pending accounts."""
    generic_response = {
        'message': 'If the email exists, a verification link has been sent.'
    }
    try:
        caller_ip = get_remote_address() or request.remote_addr or 'unknown'
        if _is_resend_verification_rate_limited(caller_ip):
            return jsonify({
                'error': 'Too many verification requests. Please wait before trying again.'
            }), 429

        payload = request.get_json(silent=True) or {}
        email = (payload.get('email') or '').strip().lower()
        delivery_status = _verification_delivery_status()
        response_payload = {
            **generic_response,
            **_verification_delivery_response_payload(delivery_status),
            'support_email': SUPPORT_EMAIL,
        }
        if not is_valid_email(email):
            return jsonify(response_payload), 200

        conn = db_connect()
        c = conn.cursor()
        c.execute('SELECT id, firm_name, email_verified FROM users WHERE email = ? OR username = ?', (email, email))
        row = c.fetchone()
        conn.close()

        if not row:
            return jsonify(response_payload), 200

        user_id = int(row[0])
        if int(row[2] or 0) == 1:
            return jsonify(response_payload), 200

        token = create_email_verification_token(user_id, email)
        verify_link = _public_verify_email_link(token)
        delivery_result = send_email_verification_link_with_result(
            email,
            verify_link,
            str(row[1] or app.config.get('FIRM_NAME', 'Your Firm')),
        )
        return jsonify({
            **response_payload,
            'verification_sent': bool(delivery_result.success),
            **_verification_delivery_response_payload(delivery_status, delivery_result),
        }), 200
    except Exception:
        return _safe_api_error(
            'Unable to resend verification email right now.',
            log_message='api_resend_verification failed',
        )


@app.route('/api/firms/create', methods=['POST'])
@login_required
def api_create_firm():
    """Create a firm for first-run onboarding and attach current user as owner."""
    try:
        existing_ctx, _ = _require_firm_context()
        if existing_ctx:
            return jsonify({
                'success': True,
                'firm_id': existing_ctx['firm_id'],
                'firm_name': existing_ctx.get('firm_name') or app.config['FIRM_NAME'],
            }), 200

        payload = request.get_json(silent=True) or {}
        requested_name = bleach.clean((payload.get('name') or '').strip(), strip=True)
        practice_area = bleach.clean((payload.get('practice_area') or '').strip(), strip=True)
        firm_size = bleach.clean((payload.get('firm_size') or '').strip(), strip=True)

        if not requested_name:
            return jsonify({'success': False, 'error': 'Firm name is required.'}), 400
        if len(requested_name) < 2 or len(requested_name) > MAX_FIRM_NAME_LENGTH:
            return jsonify({'success': False, 'error': f'Firm name must be 2-{MAX_FIRM_NAME_LENGTH} characters.'}), 400
        if len(practice_area) > 120:
            return jsonify({'success': False, 'error': 'Practice area must be 120 characters or fewer.'}), 400
        allowed_sizes = {'1-2', '3-5', '6-10', '10+'}
        if firm_size and firm_size not in allowed_sizes:
            return jsonify({'success': False, 'error': 'Firm size must be one of 1-2, 3-5, 6-10, or 10+.'}), 400

        now_iso = datetime.now(timezone.utc).isoformat()
        conn = db_connect()
        c = conn.cursor()
        c.execute(
            '''
            INSERT INTO firms (name, created_at, created_by_user_id, practice_area, firm_size)
            VALUES (?, ?, ?, ?, ?)
            ''',
            (
                requested_name,
                now_iso,
                current_user.id,
                practice_area or None,
                firm_size or None,
            ),
        )
        firm_id = int(c.lastrowid)
        c.execute(
            '''
            INSERT INTO firm_users (
                firm_id, user_id, role, status, invited_by_user_id, invited_at, joined_at
            )
            VALUES (?, ?, 'owner', 'active', ?, ?, ?)
            ''',
            (firm_id, current_user.id, current_user.id, now_iso, now_iso),
        )
        c.execute('UPDATE users SET firm_name = ? WHERE id = ?', (requested_name, current_user.id))
        _log_audit_event(
            conn,
            firm_id,
            current_user.id,
            'member',
            current_user.id,
            'MEMBER_ROLE_CHANGED',
            before_dict={'firm_name': current_user.firm_name or ''},
            after_dict={'firm_name': requested_name, 'role': 'owner'},
        )
        conn.commit()
        conn.close()

        refreshed_user = load_user(current_user.id)
        if refreshed_user:
            login_user(refreshed_user, remember=True)

        return jsonify({'success': True, 'firm_id': firm_id, 'user': _user_response_payload(refreshed_user or current_user)}), 201
    except Exception:
        return _safe_api_error(
            'Unable to create firm right now.',
            log_message=f'Failed onboarding firm create for user {current_user.id}',
        )


@app.route('/api/account/plan', methods=['GET'])
@login_required
def api_account_plan():
    """Return account-level plan information for SPA UI indicators."""
    try:
        plan = _account_plan_payload(current_user.id)
        firm_ctx, err = _require_firm_context()
        if err:
            return err
        firm_plan = get_firm_plan(firm_ctx['firm_id'])
        return jsonify({
            'success': True,
            **plan,
            'firm_plan': firm_plan,
            'plan_limits': plan_service.get_plan_limits(firm_ctx['firm_id'], db_connect),
        }), 200
    except Exception:
        return _safe_api_error(
            'Unable to load account plan right now.',
            log_message=f'Failed to load account plan for user {current_user.id}',
        )




@app.route('/api/account/profile', methods=['PUT'])
@login_required
def api_account_profile_put():
    """Update account profile fields supported by the current workspace model."""

    try:

        payload = request.get_json(silent=True) or {}

        requested_firm_name = bleach.clean((payload.get('firm_name') or '').strip(), strip=True)

        if not requested_firm_name:

            return jsonify({'success': False, 'error': 'firm_name is required.'}), 400

        if len(requested_firm_name) < 2 or len(requested_firm_name) > MAX_FIRM_NAME_LENGTH:

            return jsonify({'success': False, 'error': f'Firm name must be 2-{MAX_FIRM_NAME_LENGTH} characters.'}), 400



        firm_ctx, err = _require_firm_context()

        if err:

            return err

        if not _is_owner(firm_ctx['role']):

            return jsonify({'success': False, 'error': 'Only firm owners can update firm profile settings.'}), 403



        conn = db_connect()

        c = conn.cursor()

        c.execute('UPDATE firms SET name = ? WHERE id = ?', (requested_firm_name, firm_ctx['firm_id']))

        c.execute('UPDATE users SET firm_name = ? WHERE id = ?', (requested_firm_name, current_user.id))

        _log_audit_event(

            conn,

            firm_ctx['firm_id'],

            current_user.id,

            'member',

            current_user.id,

            'MEMBER_ROLE_CHANGED',

            before_dict={'firm_name': firm_ctx.get('firm_name') or ''},

            after_dict={'firm_name': requested_firm_name},

        )

        conn.commit()

        conn.close()



        user = load_user(current_user.id)

        return jsonify({'success': True, 'user': _user_response_payload(user) if user else _user_response_payload(current_user)}), 200

    except Exception:

        return _safe_api_error(

            'Unable to update account profile right now.',

            log_message=f'Failed account profile update for user {current_user.id}',

        )





@app.route('/api/account/branding', methods=['GET'])

@login_required

def api_account_branding_get():

    """Return account-level branding settings for report PDFs.

    All plans receive their current branding data. The response includes
    a `branding_editor_enabled` flag so the frontend knows whether to
    show the upload UI or an upgrade prompt.
    """

    try:

        firm_ctx, err = _require_firm_context()

        if err:

            return err

        firm_plan = get_firm_plan(firm_ctx['firm_id'])

        branding = _get_account_branding(current_user.id)

        payload = _branding_public_payload(branding)

        payload['branding_editor_enabled'] = (firm_plan == FIRM_PLAN_FIRM)

        return jsonify({'success': True, 'branding': payload}), 200

    except Exception:

        return _safe_api_error(

            'Unable to load branding settings right now.',

            log_message=f'Failed to load branding for user {current_user.id}',

        )





@app.route('/api/account/branding/logo', methods=['GET'])

@login_required

def api_account_branding_logo_get():

    """Return the current account logo file."""

    branding = _get_account_branding(current_user.id)

    logo_filename = branding.get('logo_filename')

    logo_path = branding.get('logo_path')

    if not logo_filename or not logo_path:

        return jsonify({'success': False, 'error': 'No logo configured.'}), 404

    return send_from_directory(

        BRANDING_UPLOAD_DIR,

        os.path.basename(logo_filename),

        as_attachment=False,

        max_age=300,

    )





@app.route('/api/account/branding/logo', methods=['POST'])
@login_required
def api_account_branding_logo_put():
    """Upload or replace the account-level logo used in report PDFs.

    Requires Firm plan. Free and Team plans receive a 403 with an upgrade message.
    """

    try:

        firm_ctx, err = _require_firm_context()

        if err:

            return err

        firm_plan = get_firm_plan(firm_ctx['firm_id'])

        if firm_plan != FIRM_PLAN_FIRM:

            return jsonify({

                'success': False,

                'error': 'Custom branding is available on the Firm plan.',

                'upgrade_required': True,

            }), 403

        logo_file = request.files.get('logo')

        if not logo_file or not logo_file.filename:

            return jsonify({'success': False, 'error': 'No logo file uploaded.'}), 400



        original_name = secure_filename(logo_file.filename)

        if '.' not in original_name:

            return jsonify({'success': False, 'error': 'Unsupported file format. Use PNG or JPG.'}), 400

        extension = original_name.rsplit('.', 1)[1].lower()

        if extension not in ALLOWED_LOGO_EXTENSIONS:

            return jsonify({'success': False, 'error': 'Unsupported file format. Use PNG or JPG. SVG is not accepted.'}), 400



        logo_file.stream.seek(0, os.SEEK_END)

        file_size = logo_file.stream.tell()

        logo_file.stream.seek(0)

        if file_size > MAX_BRANDING_LOGO_BYTES:

            return jsonify({'success': False, 'error': 'Logo file is too large. Limit is 5MB.'}), 400



        stored_name = f'user_{current_user.id}_{int(time_module.time())}_{secrets.token_hex(4)}.{extension}'

        save_path = os.path.join(BRANDING_UPLOAD_DIR, stored_name)

        logo_file.save(save_path)



        branding = _save_account_branding(current_user.id, logo_filename=stored_name)

        return jsonify({'success': True, 'branding': _branding_public_payload(branding)}), 200

    except Exception:

        return _safe_api_error(

            'Unable to upload logo right now.',

            log_message=f'Failed branding logo upload for user {current_user.id}',

        )





@app.route('/api/account/branding/logo', methods=['DELETE'])
@login_required
def api_account_branding_logo_delete():
    """Remove account logo and fall back to firm name text branding.

    Requires Firm plan. Only Firm users can have logos to remove.
    """

    try:

        firm_ctx, err = _require_firm_context()

        if err:

            return err

        firm_plan = get_firm_plan(firm_ctx['firm_id'])

        if firm_plan != FIRM_PLAN_FIRM:

            return jsonify({

                'success': False,

                'error': 'Custom branding is available on the Firm plan.',

                'upgrade_required': True,

            }), 403

        branding = _save_account_branding(current_user.id, remove_logo=True)

        return jsonify({'success': True, 'branding': _branding_public_payload(branding)}), 200

    except Exception:

        return _safe_api_error(

            'Unable to remove logo right now.',

            log_message=f'Failed branding logo delete for user {current_user.id}',

        )





@app.route('/api/account/branding/theme', methods=['PUT'])
@login_required
def api_account_branding_theme_put():
    """Update the account-level accent theme used by report PDFs.

    Requires Firm plan. Free and Team plans receive a 403 with an upgrade message.
    """

    try:

        firm_ctx, err = _require_firm_context()

        if err:

            return err

        firm_plan = get_firm_plan(firm_ctx['firm_id'])

        if firm_plan != FIRM_PLAN_FIRM:

            return jsonify({

                'success': False,

                'error': 'Custom branding is available on the Firm plan.',

                'upgrade_required': True,

            }), 403

        payload = request.get_json(silent=True) or {}

        requested_theme = (payload.get('accent_theme') or '').strip().lower()

        if requested_theme not in BRANDING_THEME_PRESETS:

            return jsonify(

                {

                    'success': False,

                    'error': 'Unsupported accent theme.',

                    'theme_options': _branding_theme_options(),

                }

            ), 400



        branding = _save_account_branding(current_user.id, accent_theme=requested_theme)

        return jsonify({'success': True, 'branding': _branding_public_payload(branding)}), 200

    except Exception:

        return _safe_api_error(

            'Unable to update branding theme right now.',

            log_message=f'Failed branding theme update for user {current_user.id}',

        )





@app.route('/api/team/invite', methods=['POST'])
@login_required
def api_team_invite():
    """Invite a new team member to the firm."""
    try:

        firm_ctx, err = _require_firm_context()

        if err:

            return err

        if not _is_owner(firm_ctx['role']):

            return jsonify({'success': False, 'error': 'Only firm owners can invite members.'}), 403

        seat_limit_result = plan_service.enforce_seat_limit(firm_ctx['firm_id'], db_connect)
        if seat_limit_result:
            return _plan_limit_error(seat_limit_result.get('message') or 'Plan seat limit reached.')



        payload = request.get_json(silent=True) or {}

        email = (payload.get('email') or '').strip().lower()

        role = (payload.get('role') or 'member').strip().lower()

        if role not in {'partner', 'member'}:

            return jsonify({'success': False, 'error': 'Role must be partner or member.'}), 400

        if not is_valid_email(email):

            return jsonify({'success': False, 'error': 'A valid email is required.'}), 400



        invite_token = secrets.token_urlsafe(32)

        invite_hash = hashlib.sha256(invite_token.encode('utf-8')).hexdigest()

        now_iso = datetime.now(timezone.utc).isoformat()

        conn = db_connect()

        c = conn.cursor()

        c.execute('SELECT id FROM users WHERE email = ? OR username = ? LIMIT 1', (email, email))

        user_row = c.fetchone()

        if user_row:

            invited_user_id = int(user_row[0])

            c.execute(

                '''

                SELECT 1

                FROM firm_users

                WHERE user_id = ? AND status = 'active' AND firm_id != ?

                LIMIT 1

                ''',

                (invited_user_id, firm_ctx['firm_id']),

            )

            if c.fetchone():

                conn.close()

                return jsonify({'success': False, 'error': 'User already belongs to another active firm workspace.'}), 409

        else:

            c.execute(

                '''

                INSERT INTO users (email, username, password_hash, is_verified, created_at, firm_name, is_admin, subscription_type, subscription_status)

                VALUES (?, ?, ?, 0, ?, ?, 0, 'trial', 'trial')

                ''',

                (email, email, generate_password_hash(secrets.token_urlsafe(24)), now_iso, firm_ctx.get('firm_name') or app.config['FIRM_NAME']),

            )

            invited_user_id = int(c.lastrowid)



        c.execute(

            '''

            INSERT INTO firm_users (

                firm_id, user_id, role, status, invited_by_user_id, invited_at, invite_token_hash

            )

            VALUES (?, ?, ?, 'invited', ?, ?, ?)

            ON CONFLICT(firm_id, user_id) DO UPDATE SET

                role = excluded.role,

                status = 'invited',

                invited_by_user_id = excluded.invited_by_user_id,

                invited_at = excluded.invited_at,

                invite_token_hash = excluded.invite_token_hash

            ''',

            (firm_ctx['firm_id'], invited_user_id, role, current_user.id, now_iso, invite_hash),

        )

        _log_audit_event(

            conn,

            firm_ctx['firm_id'],

            current_user.id,

            'member',

            invited_user_id,

            'MEMBER_INVITED',

            before_dict={},

            after_dict={'email': email, 'role': role, 'status': 'invited'},

        )

        conn.commit()

        conn.close()



        resp = {'success': True, 'message': 'Invitation created.'}

        if app.config.get('DEBUG') or app.config.get('TESTING'):

            resp['invite_token'] = invite_token

            resp['invite_url'] = f'/invite/accept?token={invite_token}'

        return jsonify(resp), 200

    except Exception:

        return _safe_api_error(

            'Unable to invite team member right now.',

            log_message=f'Failed team invite for user {current_user.id}',

        )


def _api_team_invite_disabled_legacy():
    """Original stub kept for reference — no longer active."""
    return jsonify({'success': False, 'error': 'Team invitations are not available yet. This feature is coming soon.', 'code': 'feature_unavailable'}), 503
    """Original invite logic kept here but disabled for 1.0."""
    try:

        firm_ctx, err = _require_firm_context()

        if err:

            return err

        if not _is_owner(firm_ctx['role']):

            return jsonify({'success': False, 'error': 'Only firm owners can invite members.'}), 403

        seat_limit_result = plan_service.enforce_seat_limit(firm_ctx['firm_id'], db_connect)
        if seat_limit_result:
            return _plan_limit_error(seat_limit_result.get('message') or 'Plan seat limit reached.')



        payload = request.get_json(silent=True) or {}

        email = (payload.get('email') or '').strip().lower()

        role = (payload.get('role') or 'member').strip().lower()

        if role not in {'partner', 'member'}:

            return jsonify({'success': False, 'error': 'Role must be partner or member.'}), 400

        if not is_valid_email(email):

            return jsonify({'success': False, 'error': 'A valid email is required.'}), 400



        invite_token = secrets.token_urlsafe(32)

        invite_hash = hashlib.sha256(invite_token.encode('utf-8')).hexdigest()

        now_iso = datetime.now(timezone.utc).isoformat()

        conn = db_connect()

        c = conn.cursor()

        c.execute('SELECT id FROM users WHERE email = ? OR username = ? LIMIT 1', (email, email))

        user_row = c.fetchone()

        if user_row:

            invited_user_id = int(user_row[0])

            c.execute(

                '''

                SELECT 1

                FROM firm_users

                WHERE user_id = ? AND status = 'active' AND firm_id != ?

                LIMIT 1

                ''',

                (invited_user_id, firm_ctx['firm_id']),

            )

            if c.fetchone():

                conn.close()

                return jsonify({'success': False, 'error': 'User already belongs to another active firm workspace.'}), 409

        else:

            c.execute(

                '''

                INSERT INTO users (email, username, password_hash, is_verified, created_at, firm_name, is_admin, subscription_type, subscription_status)

                VALUES (?, ?, ?, 0, ?, ?, 0, 'trial', 'trial')

                ''',

                (email, email, generate_password_hash(secrets.token_urlsafe(24)), now_iso, firm_ctx.get('firm_name') or app.config['FIRM_NAME']),

            )

            invited_user_id = int(c.lastrowid)



        c.execute(

            '''

            INSERT INTO firm_users (

                firm_id, user_id, role, status, invited_by_user_id, invited_at, invite_token_hash

            )

            VALUES (?, ?, ?, 'invited', ?, ?, ?)

            ON CONFLICT(firm_id, user_id) DO UPDATE SET

                role = excluded.role,

                status = 'invited',

                invited_by_user_id = excluded.invited_by_user_id,

                invited_at = excluded.invited_at,

                invite_token_hash = excluded.invite_token_hash

            ''',

            (firm_ctx['firm_id'], invited_user_id, role, current_user.id, now_iso, invite_hash),

        )

        _log_audit_event(

            conn,

            firm_ctx['firm_id'],

            current_user.id,

            'member',

            invited_user_id,

            'MEMBER_INVITED',

            before_dict={},

            after_dict={'email': email, 'role': role, 'status': 'invited'},

        )

        conn.commit()

        conn.close()



        resp = {'success': True, 'message': 'Invitation created.'}

        if app.config.get('DEBUG') or app.config.get('TESTING'):

            resp['invite_token'] = invite_token

            resp['invite_url'] = f'/accept-invite?token={invite_token}'

        return jsonify(resp), 200

    except Exception:

        return _safe_api_error(

            'Unable to invite team member right now.',

            log_message=f'Failed team invite for user {current_user.id}',

        )





@app.route('/api/team/accept', methods=['POST'])
def api_team_accept():
    try:

        payload = request.get_json(silent=True) or {}

        token = (payload.get('token') or '').strip()

        password = payload.get('password') or ''

        if not token:

            return jsonify({'success': False, 'error': 'Invite token is required.'}), 400

        invite_hash = hashlib.sha256(token.encode('utf-8')).hexdigest()

        now_iso = datetime.now(timezone.utc).isoformat()



        conn = db_connect()

        c = conn.cursor()

        c.execute(

            '''

            SELECT fu.id, fu.firm_id, fu.user_id, fu.role, u.password_hash

            FROM firm_users fu

            INNER JOIN users u ON u.id = fu.user_id

            WHERE fu.invite_token_hash = ?

              AND fu.status = 'invited'

            LIMIT 1

            ''',

            (invite_hash,),

        )

        row = c.fetchone()

        if not row:

            conn.close()

            return jsonify({'success': False, 'error': 'Invite token is invalid or expired.'}), 404



        membership_id = int(row[0])

        firm_id = int(row[1])

        invited_user_id = int(row[2])

        role = str(row[3])



        c.execute(

            '''

            SELECT 1

            FROM firm_users

            WHERE user_id = ? AND status = 'active' AND firm_id != ?

            LIMIT 1

            ''',

            (invited_user_id, firm_id),

        )

        if c.fetchone():

            conn.close()

            return jsonify({'success': False, 'error': 'User already belongs to another active firm workspace.'}), 409



        if password:

            ok_password, password_msg = validate_password_strength(password)

            if not ok_password:

                conn.close()

                return jsonify({'success': False, 'error': password_msg}), 400

            c.execute(

                '''

                UPDATE users

                SET password_hash = ?, is_verified = 1, email_verified = 1
                WHERE id = ?

                ''',

                (generate_password_hash(password), invited_user_id),

            )



        c.execute(

            '''

            UPDATE firm_users

            SET status = 'active',

                joined_at = ?,

                invite_token_hash = NULL

            WHERE id = ?

            ''',

            (now_iso, membership_id),

        )

        _log_audit_event(

            conn,

            firm_id,

            invited_user_id,

            'member',

            invited_user_id,

            'MEMBER_ACTIVATED',

            before_dict={'status': 'invited'},

            after_dict={'status': 'active', 'role': role},

        )

        conn.commit()

        conn.close()

        return jsonify({'success': True, 'message': 'Invitation accepted.'}), 200

    except Exception:

        return _safe_api_error(

            'Unable to accept invitation right now.',

            log_message='api_team_accept failed',

        )





@app.route('/api/team/members', methods=['GET'])

@login_required

def api_team_members():

    try:

        firm_ctx, err = _require_firm_context()

        if err:

            return err

        conn = db_connect()

        c = conn.cursor()

        c.execute(

            '''

            SELECT fu.user_id, u.email, fu.role, fu.status, fu.joined_at, fu.invited_at

            FROM firm_users fu

            INNER JOIN users u ON u.id = fu.user_id

            WHERE fu.firm_id = ?

            ORDER BY fu.status DESC, fu.joined_at DESC, fu.id DESC

            ''',

            (firm_ctx['firm_id'],),

        )

        rows = c.fetchall()

        conn.close()

        members = [

            {

                'user_id': int(r[0]),

                'email': r[1],

                'role': r[2],

                'status': r[3],

                'joined_at': r[4],

                'invited_at': r[5],

            }

            for r in rows

        ]

        return jsonify({'success': True, 'firm_id': firm_ctx['firm_id'], 'members': members}), 200

    except Exception:

        return _safe_api_error(

            'Unable to load team members right now.',

            log_message=f'Failed team members list for user {current_user.id}',

        )





@app.route('/api/team/member/<int:user_id>/role', methods=['POST'])
@login_required
def api_team_member_role(user_id):
    try:

        firm_ctx, err = _require_firm_context()

        if err:

            return err

        if not _is_owner(firm_ctx['role']):

            return jsonify({'success': False, 'error': 'Only firm owners can manage member roles.'}), 403

        payload = request.get_json(silent=True) or {}

        next_role = (payload.get('role') or '').strip().lower()

        if next_role not in {'owner', 'partner', 'member'}:

            return jsonify({'success': False, 'error': 'Role must be owner, partner, or member.'}), 400

        conn = db_connect()

        c = conn.cursor()

        c.execute('SELECT role, status FROM firm_users WHERE firm_id = ? AND user_id = ?', (firm_ctx['firm_id'], user_id))

        row = c.fetchone()

        if not row:

            conn.close()

            return jsonify({'success': False, 'error': 'Member not found in this firm.'}), 404

        before_role = str(row[0])

        c.execute('UPDATE firm_users SET role = ? WHERE firm_id = ? AND user_id = ?', (next_role, firm_ctx['firm_id'], user_id))

        _log_audit_event(

            conn,

            firm_ctx['firm_id'],

            current_user.id,

            'member',

            user_id,

            'MEMBER_ROLE_CHANGED',

            before_dict={'role': before_role},

            after_dict={'role': next_role},

        )

        conn.commit()

        conn.close()

        return jsonify({'success': True}), 200

    except Exception:

        return _safe_api_error(

            'Unable to update member role right now.',

            log_message=f'Failed role update for member {user_id} by user {current_user.id}',

        )





@app.route('/api/team/member/<int:user_id>/status', methods=['POST'])
@login_required
def api_team_member_status(user_id):
    try:

        firm_ctx, err = _require_firm_context()

        if err:

            return err

        if not _is_owner(firm_ctx['role']):

            return jsonify({'success': False, 'error': 'Only firm owners can manage member status.'}), 403

        payload = request.get_json(silent=True) or {}

        next_status = (payload.get('status') or '').strip().lower()

        if next_status not in {'active', 'suspended'}:

            return jsonify({'success': False, 'error': 'Status must be active or suspended.'}), 400

        conn = db_connect()

        c = conn.cursor()

        c.execute('SELECT status FROM firm_users WHERE firm_id = ? AND user_id = ?', (firm_ctx['firm_id'], user_id))

        row = c.fetchone()

        if not row:

            conn.close()

            return jsonify({'success': False, 'error': 'Member not found in this firm.'}), 404

        before_status = str(row[0])

        c.execute('UPDATE firm_users SET status = ? WHERE firm_id = ? AND user_id = ?', (next_status, firm_ctx['firm_id'], user_id))

        event_type = 'MEMBER_ACTIVATED' if next_status == 'active' else 'MEMBER_SUSPENDED'

        _log_audit_event(

            conn,

            firm_ctx['firm_id'],

            current_user.id,

            'member',

            user_id,

            event_type,

            before_dict={'status': before_status},

            after_dict={'status': next_status},

        )

        conn.commit()

        conn.close()

        return jsonify({'success': True}), 200

    except Exception:

        return _safe_api_error(

            'Unable to update member status right now.',

            log_message=f'Failed status update for member {user_id} by user {current_user.id}',

        )





@app.route('/api/auth/logout', methods=['POST'])

@csrf.exempt

def api_logout():

    """JSON logout endpoint"""

    try:

        logout_user()

        return jsonify({'success': True}), 200

    except Exception:

        return _safe_api_error(

            'Logout failed due to a server error.',

            log_message='api_logout failed',

        )





@app.route('/api/dashboard/stats', methods=['GET'])

@app.route('/api/dashboard/metrics', methods=['GET'])

# Heavy aggregation read used by dashboard widgets; guard against scraping bursts.

@limiter.limit('60 per minute')

@limiter.limit('600 per hour')

def api_dashboard_stats():

    """JSON dashboard stats endpoint for the React frontend."""

    if not current_user.is_authenticated:

        return jsonify({'success': False, 'error': 'Not authenticated'}), 401



    try:

        firm_ctx, err = _require_firm_context()

        if err:

            return err

        account_status = current_user.get_account_status()

        _purge_expired_deleted_reports(current_user.id)



        conn = db_connect()

        c = conn.cursor()

        c.execute(

            '''

            SELECT id, created_at, total_reviews, subscription_type_at_creation, avg_rating

            FROM reports

            WHERE firm_id = ?

              AND deleted_at IS NULL

            ORDER BY created_at DESC

            LIMIT 500

            ''',

            (firm_ctx['firm_id'],),

        )

        report_rows = c.fetchall()



        c.execute(

            '''

            SELECT trial_limit

            FROM users

            WHERE id = ?

            ''',

            (current_user.id,),

        )

        usage_row = c.fetchone()

        conn.close()



        recent_reports = []

        total_reviews_processed = 0

        last_report_at = None

        sentiment_points = []



        for idx, row in enumerate(report_rows):

            if idx == 0:

                last_report_at = row[1]



            reviews_count = row[2] or 0

            total_reviews_processed += reviews_count

            avg_rating = float(row[4] or 0.0)

            sentiment_points.append(max(0.0, min(100.0, (avg_rating / 5.0) * 100.0)))



            recent_reports.append(

                {

                    'id': row[0],

                    'created_at': row[1],

                    'total_reviews': reviews_count,

                    'subscription_type_at_creation': row[3],

                    'plan_label': _plan_badge_label(row[3]),

                    'avg_rating': avg_rating,

                }

            )



        trial_reviews_used, trial_limit = _get_trial_usage_count(

            current_user.id,

            usage_row[0] if usage_row else FREE_PLAN_REPORT_LIMIT,

        )



        unique_active_reports = len({row[0] for row in report_rows})

        total_reviews_for_stability = sum(int(row[2] or 0) for row in report_rows)

        trend_stability = 'Insufficient data'

        trend_stability_explanation = (

            "We'll calculate trend stability once you have at least 3 unique reports and 100+ reviews."

        )



        if unique_active_reports >= 3 and total_reviews_for_stability >= 100:

            stability_rows = report_rows[:5]

            stability_values = [max(0.0, min(100.0, (float(row[4] or 0.0) / 5.0) * 100.0)) for row in stability_rows]

            if stability_values:

                mean = sum(stability_values) / len(stability_values)

                variance = sum((value - mean) ** 2 for value in stability_values) / len(stability_values)

                std_dev = variance ** 0.5

                if std_dev < 4.0:

                    trend_stability = 'Stable'

                    trend_stability_explanation = (

                        'Your sentiment scores have been fairly consistent across recent reports.'

                    )

                elif std_dev < 9.0:

                    trend_stability = 'Moderately stable'

                    trend_stability_explanation = (

                        'Sentiment is shifting, but not dramatically between reports.'

                    )

                else:

                    trend_stability = 'Volatile'

                    trend_stability_explanation = (

                        'Sentiment is fluctuating significantly between reports. '

                        'Check recent operational or staffing changes.'

                    )



        confidence_window = report_rows[:10]

        confidence_reviews = sum(int(row[2] or 0) for row in confidence_window)

        if confidence_reviews < 50:

            confidence_level = 'Low'

            confidence_explanation = (

                "We've analyzed a small number of reviews. Add more client feedback to increase confidence in these insights."

            )

        elif confidence_reviews <= 200:

            confidence_level = 'Medium'

            confidence_explanation = (

                "We have a decent sample of reviews. More recent feedback will make trends clearer."

            )

        else:

            confidence_level = 'High'

            confidence_explanation = (

                "We've analyzed a strong sample of reviews. These trends are likely representative of your clients' experience."

            )



        avg_sentiment_score = round((sum(sentiment_points) / len(sentiment_points)), 1) if sentiment_points else None



        return jsonify(

            {

                'success': True,

                'stats': {

                    'processed_files': len(report_rows),

                    'total_reviews_processed': total_reviews_processed,

                    'last_report_at': last_report_at,

                    'recent_reports': recent_reports,

                    'account_status': {

                        'type': account_status.get('type'),

                        'display': account_status.get('display'),

                        'remaining': account_status.get('remaining'),

                    },

                    'trial_reviews_used': trial_reviews_used,

                    'trial_limit': trial_limit,

                    'email_verified': is_email_verified(current_user.id),

                    'trend_stability': trend_stability,

                    'trend_stability_explanation': trend_stability_explanation,

                    'confidence_level': confidence_level,

                    'confidence_explanation': confidence_explanation,

                    'avg_sentiment_score': avg_sentiment_score,

                },

            }

        ), 200

    except Exception:

        return _safe_api_error(

            'Unable to load dashboard stats right now.',

            log_message=f'Failed to load dashboard stats for user {current_user.id}',

        )


@app.route('/api/alerts', methods=['GET'])
@login_required
@limiter.limit('60 per minute')
def api_alerts_list():
    """Return active governance alerts for the current firm."""
    try:
        firm_ctx, err = _require_firm_context()
        if err:
            return err
        # Run monitor scan opportunistically to surface fresh alerts without external scheduler wiring.
        scan_recent_reviews_for_signals(db_connect, firm_id=firm_ctx['firm_id'])
        alerts = get_active_alerts(db_connect, firm_ctx['firm_id'], limit=request.args.get('limit', 20, type=int) or 20)
        return jsonify({'success': True, 'alerts': alerts}), 200
    except Exception:
        return _safe_api_error(
            'Unable to load governance alerts right now.',
            log_message=f'Failed to load alerts for user {current_user.id}',
        )


@app.route('/api/actions/recent', methods=['GET'])
@login_required
@limiter.limit('60 per minute')
def api_recent_actions():
    """Return recent governance actions (firm-scoped) for dashboard visibility."""
    try:
        firm_ctx, err = _require_firm_context()
        if err:
            return err

        firm_plan = get_firm_plan(firm_ctx['firm_id'])
        history_cutoff = _report_history_cutoff_iso(firm_plan)
        conn = db_connect()
        c = conn.cursor()
        query = (
            '''
            SELECT
                a.id,
                a.title,
                a.owner,
                a.status,
                a.due_date,
                a.updated_at,
                r.id,
                r.themes
            FROM report_action_items a
            JOIN reports r ON r.id = a.report_id
            WHERE a.firm_id = ?
              AND r.deleted_at IS NULL
            '''
        )
        params = [firm_ctx['firm_id']]
        if history_cutoff:
            query += " AND datetime(r.created_at) >= datetime(?)"
            params.append(history_cutoff)
        query += " ORDER BY datetime(COALESCE(a.updated_at, a.created_at)) DESC LIMIT 5"
        c.execute(query, tuple(params))
        rows = c.fetchall()
        conn.close()

        items = []
        for row in rows:
            themes = _deserialize_report_data(row[7], {})
            issue = 'Governance issue'
            if isinstance(themes, dict) and themes:
                top_theme = sorted(themes.items(), key=lambda kv: int(kv[1] or 0), reverse=True)[0][0]
                issue = str(top_theme)
            items.append(
                {
                    'id': int(row[0]),
                    'issue': issue,
                    'action': str(row[1] or ''),
                    'owner': str(row[2] or 'Unassigned'),
                    'status': str(row[3] or 'open'),
                    'due_date': row[4],
                    'updated_at': row[5],
                    'report_id': int(row[6]),
                }
            )

        return jsonify({'success': True, 'actions': items}), 200
    except Exception:
        return _safe_api_error(
            'Unable to load recent governance actions right now.',
            log_message=f'Failed to load recent actions for user {current_user.id}',
        )





@app.route('/api/exposure/latest', methods=['GET'])

@login_required

# Exposure snapshot is aggregation-heavy over latest report context.

@limiter.limit('60 per minute')

@limiter.limit('600 per hour')

def api_exposure_latest():

    """Return canonical exposure snapshot for the latest firm report."""

    try:

        firm_ctx, err = _require_firm_context()

        if err:

            return err



        conn = db_connect()

        c = conn.cursor()

        latest_subject = _resolve_latest_exposure_subject(c, firm_ctx['firm_id'])

        if not latest_subject:

            conn.close()

            return jsonify(

                {

                    'success': True,

                    'has_data': False,

                    'report_id': None,

                    'snapshot_id': None,

                    'exposure_score': None,

                    'exposure_tier': None,

                    'exposure_label': None,

                    'partner_escalation_required': None,

                    'primary_risk_driver': None,

                    'responsible_owner': None,

                }

            ), 200



        report_id = int(latest_subject['report_id'])

        snapshot_id = latest_subject['snapshot_id']

        c.execute(

            '''

            SELECT avg_rating, themes

            FROM reports

            WHERE id = ?

              AND firm_id = ?

              AND deleted_at IS NULL

            LIMIT 1

            ''',

            (report_id, firm_ctx['firm_id']),

        )

        report_row = c.fetchone()

        conn.close()

        if not report_row:

            return jsonify({'success': False, 'error': 'Latest report not found.'}), 404



        avg_rating = report_row[0]

        raw_themes = _deserialize_report_data(report_row[1], {}) or {}

        theme_rows = _normalize_theme_rows_for_exposure(raw_themes)

        trend_points = _get_report_trend_points(firm_ctx['firm_id'], limit=12)

        implementation_items = _get_report_action_rows(firm_ctx['firm_id'], report_id, limit=20)

        snapshot = _compute_exposure_snapshot(avg_rating, theme_rows, trend_points, implementation_items)

        snapshot['report_id'] = report_id

        snapshot['snapshot_id'] = snapshot_id

        snapshot['latest_timestamp'] = latest_subject['latest_ts']

        snapshot['latest_basis'] = 'snapshot_generated_at' if latest_subject['uses_snapshot_generated_at'] else 'reports_created_at'

        snapshot['success'] = True

        return jsonify(snapshot), 200

    except Exception:

        return _safe_api_error(

            'Unable to load exposure status right now.',

            log_message=f'Failed to load exposure snapshot for user {current_user.id}',

        )





@app.route('/api/credits', methods=['GET'])

@login_required

def api_credits():

    """Return entitlement/credit counts for dashboard truthfulness."""

    try:

        credits = _build_user_credit_snapshot(current_user.id)

        return jsonify({'success': True, 'credits': credits}), 200

    except Exception:

        return _safe_api_error(

            'Unable to load credits right now.',

            log_message=f'Failed to load credits for user {current_user.id}',

        )





@app.route('/api/interest/google_reviews', methods=['POST'])
@login_required
def api_interest_google_reviews():
    """Capture lightweight demand signal for future Google Reviews sync."""

    try:

        firm_ctx, err = _require_firm_context()

        if err:

            return err



        payload = request.get_json(silent=True) or {}

        source = bleach.clean(str(payload.get('source') or '').strip(), strip=True)

        note = bleach.clean(str(payload.get('note') or '').strip(), strip=True)

        if not source:

            return jsonify({'success': False, 'error': 'source is required.'}), 400

        if len(source) > 120:

            return jsonify({'success': False, 'error': 'source is too long.'}), 400

        if len(note) > 240:

            return jsonify({'success': False, 'error': 'note is too long.'}), 400



        now_iso = datetime.now(timezone.utc).isoformat()

        conn = db_connect()

        c = conn.cursor()

        c.execute(

            '''

            INSERT INTO interest_events (firm_id, user_id, type, source, created_at)

            VALUES (?, ?, 'google_reviews', ?, ?)

            ''',

            (firm_ctx['firm_id'], current_user.id, source, now_iso),

        )

        interest_id = int(c.lastrowid)

        _log_audit_event(

            conn,

            firm_ctx['firm_id'],

            current_user.id,

            'member',

            interest_id,

            'INTEREST_GOOGLE_REVIEWS',

            before_dict={},

            after_dict={'type': 'google_reviews', 'source': source, 'note': note or None},

        )

        conn.commit()

        conn.close()

        return jsonify({'success': True, 'recorded': True}), 200

    except Exception:

        return _safe_api_error(

            'Unable to record interest right now.',

            log_message=f'Failed to record Google Reviews sync interest for user {current_user.id}',

        )





@app.route('/api/feature-interest', methods=['POST'])
@app.route('/api/interest', methods=['POST'])
@login_required
def api_feature_interest_upsert():
    """Persist latest per-firm feature interest selection."""

    try:

        firm_ctx, err = _require_firm_context()

        if err:

            return err



        payload = request.get_json(silent=True) or {}

        feature_key = bleach.clean(str(payload.get('feature_key') or payload.get('feature') or '').strip(), strip=True).lower()

        choice = bleach.clean(str(payload.get('choice') or '').strip(), strip=True).lower()



        if not feature_key:

            return jsonify({'success': False, 'error': 'feature_key is required.'}), 400

        if len(feature_key) > 120:

            return jsonify({'success': False, 'error': 'feature_key is too long.'}), 400

        if choice not in ('yes', 'no'):

            return jsonify({'success': False, 'error': 'choice must be yes or no.'}), 400



        now_iso = datetime.now(timezone.utc).isoformat()

        conn = db_connect()

        c = conn.cursor()

        c.execute(

            '''

            INSERT INTO feature_interest (firm_id, feature_key, choice, updated_at)

            VALUES (?, ?, ?, ?)

            ON CONFLICT(firm_id, feature_key)

            DO UPDATE SET

                choice = excluded.choice,

                updated_at = excluded.updated_at

            ''',

            (firm_ctx['firm_id'], feature_key, choice, now_iso),

        )

        conn.commit()

        conn.close()

        return jsonify({'success': True, 'feature_key': feature_key, 'choice': choice}), 200

    except Exception:

        return _safe_api_error(

            'Unable to save feature preference right now.',

            log_message=f'Failed to upsert feature interest for user {current_user.id}',

        )





@app.route('/api/feature-interest/summary', methods=['GET'])

@app.route('/api/interest/summary', methods=['GET'])

@login_required

def api_feature_interest_summary():

    """Return aggregate feature-interest counts plus current firm's selection."""

    try:

        firm_ctx, err = _require_firm_context()

        if err:

            return err



        feature_key = bleach.clean(str(request.args.get('feature_key') or request.args.get('feature') or '').strip(), strip=True).lower()

        if not feature_key:

            return jsonify({'success': False, 'error': 'feature_key is required.'}), 400

        if len(feature_key) > 120:

            return jsonify({'success': False, 'error': 'feature_key is too long.'}), 400



        conn = db_connect()

        c = conn.cursor()

        c.execute(

            '''

            SELECT

                COALESCE(SUM(CASE WHEN choice = 'yes' THEN 1 ELSE 0 END), 0) AS yes_count,

                COALESCE(SUM(CASE WHEN choice = 'no' THEN 1 ELSE 0 END), 0) AS no_count,

                COUNT(*) AS total_firms

            FROM feature_interest

            WHERE feature_key = ?

            ''',

            (feature_key,),

        )

        aggregate_row = c.fetchone() or {}

        c.execute(

            '''

            SELECT choice

            FROM feature_interest

            WHERE firm_id = ? AND feature_key = ?

            LIMIT 1

            ''',

            (firm_ctx['firm_id'], feature_key),

        )

        current_row = c.fetchone()

        conn.close()



        return jsonify(

            {

                'success': True,

                'feature_key': feature_key,

                'yes_count': int((aggregate_row['yes_count'] if aggregate_row else 0) or 0),

                'no_count': int((aggregate_row['no_count'] if aggregate_row else 0) or 0),

                'total_firms': int((aggregate_row['total_firms'] if aggregate_row else 0) or 0),

                'current_firm_choice': (current_row['choice'] if current_row else None),

            }

        ), 200

    except Exception:

        return _safe_api_error(

            'Unable to load feature interest summary right now.',

            log_message=f'Failed to load feature interest summary for user {current_user.id}',

        )





@app.route('/api/report-packs/schedule', methods=['GET'])

@login_required

def api_report_pack_schedule_get():

    """Return executive report pack scheduling settings."""

    try:

        schedule = _get_report_pack_schedule(current_user.id, current_user.email or current_user.username)

        can_manage = _has_pro_subscription_access(current_user.id)

        return jsonify(

            {

                'success': True,

                'schedule': schedule,

                'can_manage': can_manage,

                'upgrade_required': not can_manage,

                'upgrade_message': (

                    None

                    if can_manage

                    else 'Scheduled executive report packs are available on Team and Firm plans.'

                ),

            }

        ), 200

    except Exception:

        return _safe_api_error(

            'Unable to load report pack schedule right now.',

            log_message=f'Failed to load report pack schedule for user {current_user.id}',

        )





@app.route('/api/report-packs/schedule', methods=['PUT'])
@login_required
def api_report_pack_schedule_put():
    """Update executive report pack scheduling settings."""

    try:

        if not _has_pro_subscription_access(current_user.id):

            return jsonify(

                {

                    'success': False,

                    'error': 'Scheduled executive report packs require a Team or Firm plan.',

                    'upgrade_required': True,

                }

            ), 403



        payload = request.get_json(silent=True) or {}

        enabled = bool(payload.get('enabled', False))

        cadence = (payload.get('cadence') or 'weekly').strip().lower()

        if cadence not in ('weekly', 'monthly'):

            cadence = 'weekly'

        recipients = _normalize_schedule_recipients(payload.get('recipients', []), current_user.email or current_user.username)

        if not recipients:

            return jsonify({'success': False, 'error': 'Add at least one valid recipient email.'}), 400



        now_iso = datetime.now(timezone.utc).isoformat()

        next_send_at = _next_report_pack_run(cadence).isoformat() if enabled else None

        _ensure_report_pack_schedule(current_user.id, current_user.email or current_user.username)



        conn = db_connect()

        c = conn.cursor()

        c.execute(

            '''

            UPDATE report_pack_schedules

            SET enabled = ?, cadence = ?, recipients_json = ?, next_send_at = ?, updated_at = ?

            WHERE user_id = ?

            ''',

            (1 if enabled else 0, cadence, json.dumps(recipients), next_send_at, now_iso, current_user.id),

        )

        conn.commit()

        conn.close()



        schedule = _get_report_pack_schedule(current_user.id, current_user.email or current_user.username)

        return jsonify({'success': True, 'schedule': schedule}), 200

    except Exception:

        return _safe_api_error(

            'Unable to update report pack schedule right now.',

            log_message=f'Failed to update report pack schedule for user {current_user.id}',

        )





@app.route('/api/report-packs/send-now', methods=['POST'])
@login_required
# Immediate digest generation/email fan-out is expensive and abusable.
@limiter.limit('10 per hour')
def api_report_pack_send_now():
    """Send an executive summary digest to scheduled recipients immediately."""

    try:

        if not _has_pro_subscription_access(current_user.id):

            return jsonify(

                {

                    'success': False,

                    'error': 'Executive report pack delivery requires a Team or Firm plan.',

                    'upgrade_required': True,

                }

            ), 403



        schedule = _get_report_pack_schedule(current_user.id, current_user.email or current_user.username)

        recipients = schedule.get('recipients') or []

        if not recipients:

            return jsonify({'success': False, 'error': 'No recipients configured for report packs.'}), 400



        _purge_expired_deleted_reports(current_user.id)

        conn = db_connect()

        c = conn.cursor()

        c.execute(

            '''

            SELECT id, created_at, total_reviews, avg_rating

            FROM reports

            WHERE user_id = ?

              AND deleted_at IS NULL

            ORDER BY created_at DESC

            LIMIT 5

            ''',

            (current_user.id,),

        )

        rows = c.fetchall()

        conn.close()

        if not rows:

            return jsonify({'success': False, 'error': 'Generate at least one report before sending an executive pack.'}), 400



        total_reviews = sum(int(row[2] or 0) for row in rows)

        avg_rating = 0.0

        if rows:

            avg_rating = round(sum(float(row[3] or 0.0) for row in rows) / len(rows), 2)

        latest_report_date = rows[0][1]

        report_count = _get_active_report_count(current_user.id)



        delivery_count = 0

        for recipient in recipients:

            sent = send_templated_email(

                EmailPayload(

                    to_email=recipient,

                    subject=f'Executive Report Pack - {current_user.firm_name or app.config["FIRM_NAME"]}',

                    template_name='report_pack_digest',

                    context={

                        'firm_name': current_user.firm_name or app.config['FIRM_NAME'],

                        'report_count': report_count,

                        'total_reviews': total_reviews,

                        'avg_rating': avg_rating,

                        'latest_report_date': latest_report_date,

                        'dashboard_url': f'{request.host_url.rstrip("/")}/dashboard/reports',

                    },

                )

            )

            if sent:

                delivery_count += 1



        now_iso = datetime.now(timezone.utc).isoformat()

        next_send_at = _next_report_pack_run(schedule.get('cadence') or 'weekly').isoformat() if schedule.get('enabled') else None

        conn = db_connect()

        c = conn.cursor()

        c.execute(

            '''

            UPDATE report_pack_schedules

            SET last_sent_at = ?, next_send_at = ?, updated_at = ?

            WHERE user_id = ?

            ''',

            (now_iso, next_send_at, now_iso, current_user.id),

        )

        conn.commit()

        conn.close()



        return jsonify(

            {

                'success': True,

                'delivery_count': delivery_count,

                'recipient_count': len(recipients),

                'message': (

                    f'Executive pack sent to {delivery_count} of {len(recipients)} recipient(s).'

                ),

            }

        ), 200

    except Exception:

        return _safe_api_error(

            'Unable to send executive pack right now.',

            log_message=f'Failed to send report pack for user {current_user.id}',

        )





@app.route('/api/support/tickets', methods=['POST'])
@limiter.limit('3 per 10 minutes', key_func=lambda: f'user:{current_user.id}' if getattr(current_user, 'is_authenticated', False) else get_remote_address())
@limiter.limit('10 per hour', key_func=lambda: f'user:{current_user.id}' if getattr(current_user, 'is_authenticated', False) else get_remote_address())
def api_support_ticket_create():

    """Create a support ticket from public or authenticated product surfaces."""

    try:

        payload = request.get_json(silent=True) or {}
        is_authenticated_user = bool(getattr(current_user, 'is_authenticated', False))

        category = _normalize_support_category(payload.get('category'))
        urgency = _normalize_support_urgency(payload.get('urgency'))
        source = str(payload.get('source') or 'contact').strip().lower()
        if source not in ('contact', 'dashboard'):
            source = 'contact'

        subject = bleach.clean(str(payload.get('subject') or '').strip(), strip=True)
        message = bleach.clean(str(payload.get('message') or '').strip(), strip=True)
        requester_name = bleach.clean(str(payload.get('name') or '').strip(), strip=True)
        firm_name = bleach.clean(str(payload.get('firm_name') or '').strip(), strip=True)

        if is_authenticated_user:
            requester_email = (getattr(current_user, 'email', None) or getattr(current_user, 'username', '') or '').strip().lower()
            if not firm_name:
                firm_name = bleach.clean(str(getattr(current_user, 'firm_name', '') or '').strip(), strip=True)
        else:
            requester_email = bleach.clean(str(payload.get('email') or '').strip().lower(), strip=True)

        if not is_valid_email(requester_email):
            return jsonify({'success': False, 'error': 'Enter a valid email address.'}), 400

        if len(subject) < 6:
            return jsonify({'success': False, 'error': 'Add a short subject so support can triage the request.'}), 400

        if len(subject) > 180:
            return jsonify({'success': False, 'error': 'Subject is too long.'}), 400

        if len(message) < 20:
            return jsonify({'success': False, 'error': 'Add enough detail for support to reproduce or understand the issue.'}), 400

        if len(message) > 5000:
            return jsonify({'success': False, 'error': 'Message is too long.'}), 400

        triage = _triage_support_ticket(category, urgency, subject, message)
        now_iso = datetime.now(timezone.utc).isoformat()
        ticket_ref = _support_ticket_ref()

        conn = db_connect()
        c = conn.cursor()
        c.execute(
            '''
            INSERT INTO support_tickets (
                ticket_ref, user_id, requester_name, requester_email, firm_name, source, category, urgency,
                subject, message, status, priority, escalation_level, escalation_reason, auto_response_template,
                auto_response_sent, handled_by_user_id, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, NULL, ?, ?)
            ''',
            (
                ticket_ref,
                current_user.id if is_authenticated_user else None,
                requester_name or None,
                requester_email,
                firm_name or None,
                source,
                category,
                urgency,
                subject,
                message,
                triage['status'],
                triage['priority'],
                triage['escalation_level'],
                triage['escalation_reason'] or None,
                triage['auto_response_template'],
                now_iso,
                now_iso,
            ),
        )
        ticket_id = c.lastrowid
        conn.commit()
        conn.close()

        ticket = _load_support_tickets_for_user(
            current_user.id if is_authenticated_user else None,
            requester_email=requester_email,
            include_all=False,
            limit=1,
        )[0]

        auto_response_sent = _send_support_ticket_autoresponse(ticket)
        support_notification_sent = _notify_support_ticket(ticket)

        if auto_response_sent:
            conn = db_connect()
            c = conn.cursor()
            c.execute(
                'UPDATE support_tickets SET auto_response_sent = 1, updated_at = ? WHERE id = ?',
                (datetime.now(timezone.utc).isoformat(), ticket_id),
            )
            conn.commit()
            conn.close()
            ticket['auto_response_sent'] = True

        return jsonify(
            {
                'success': True,
                'ticket': ticket,
                'support_email': SUPPORT_EMAIL,
                'security_email': SECURITY_CONTACT_EMAIL,
                'auto_response_email_sent': bool(auto_response_sent),
                'support_notification_sent': bool(support_notification_sent),
            }
        ), 201

    except Exception:

        return _safe_api_error(
            'Unable to create support request right now.',
            log_message='Failed to create support ticket',
        )


@app.route('/api/support/tickets', methods=['GET'])
@login_required
def api_support_tickets_list():

    """List support tickets for the current user or the admin queue."""

    try:

        scope = str(request.args.get('scope') or '').strip().lower()
        include_all = bool(current_user.is_admin and scope == 'queue')
        tickets = _load_support_tickets_for_user(
            current_user.id,
            requester_email=current_user.email or current_user.username,
            include_all=include_all,
            limit=50 if include_all else 20,
        )
        escalated_count = sum(1 for ticket in tickets if ticket and ticket.get('escalation_level') not in (None, '', 'none'))
        open_count = sum(1 for ticket in tickets if ticket and ticket.get('status') != 'resolved')

        return jsonify(
            {
                'success': True,
                'scope': 'queue' if include_all else 'self',
                'tickets': tickets,
                'summary': {
                    'open_count': open_count,
                    'escalated_count': escalated_count,
                },
                'support_email': SUPPORT_EMAIL,
                'security_email': SECURITY_CONTACT_EMAIL,
            }
        ), 200

    except Exception:

        return _safe_api_error(
            'Unable to load support tickets right now.',
            log_message=f'Failed to load support tickets for user {current_user.id}',
        )


@app.route('/api/support/tickets/<int:ticket_id>', methods=['PATCH'])
@login_required
def api_support_ticket_update(ticket_id):

    """Allow admins to move a support ticket through review states."""

    if not current_user.is_admin:
        return jsonify({'success': False, 'error': 'Forbidden'}), 403

    try:

        payload = request.get_json(silent=True) or {}
        next_status = str(payload.get('status') or '').strip().lower()
        next_priority = str(payload.get('priority') or '').strip().lower()

        updates = []
        params = []

        if next_status:
            if next_status not in SUPPORT_TICKET_STATUSES:
                return jsonify({'success': False, 'error': 'Invalid support ticket status.'}), 400
            updates.append('status = ?')
            params.append(next_status)

        if next_priority:
            if next_priority not in SUPPORT_TICKET_PRIORITIES:
                return jsonify({'success': False, 'error': 'Invalid support ticket priority.'}), 400
            updates.append('priority = ?')
            params.append(next_priority)

        if not updates:
            return jsonify({'success': False, 'error': 'No supported updates were provided.'}), 400

        updates.append('handled_by_user_id = ?')
        params.append(current_user.id)
        updates.append('updated_at = ?')
        params.append(datetime.now(timezone.utc).isoformat())
        params.append(ticket_id)

        conn = db_connect()
        c = conn.cursor()
        c.execute(f"UPDATE support_tickets SET {', '.join(updates)} WHERE id = ?", params)
        if c.rowcount <= 0:
            conn.close()
            return jsonify({'success': False, 'error': 'Support ticket not found.'}), 404
        conn.commit()
        conn.close()

        updated_ticket = next(
            (row for row in _load_support_tickets_for_user(current_user.id, include_all=True, limit=100) if int(row['id']) == int(ticket_id)),
            None,
        )
        return jsonify({'success': True, 'ticket': updated_ticket}), 200

    except Exception:

        return _safe_api_error(
            'Unable to update support ticket right now.',
            log_message=f'Failed to update support ticket {ticket_id} by admin {current_user.id}',
        )


@app.route('/api/reports', methods=['GET'])

@login_required

# Report list powers table/search views and can drive expensive repeated reads.

@limiter.limit('30 per minute')

def api_reports_list():

    """List user reports with UX-oriented metadata for dashboard tables."""

    limit = request.args.get('limit', 50, type=int) or 50

    limit = max(1, min(limit, 200))

    try:

        firm_ctx, err = _require_firm_context()

        if err:

            return err

        firm_plan = get_firm_plan(firm_ctx['firm_id'])
        history_meta = _report_history_metadata(firm_plan)
        history_cutoff = _report_history_cutoff_iso(firm_plan)
        _purge_expired_deleted_reports(current_user.id)

        conn = db_connect()

        c = conn.cursor()

        query = (
            '''
            SELECT id, created_at, total_reviews, subscription_type_at_creation, custom_name
            FROM reports
            WHERE firm_id = ?
              AND deleted_at IS NULL
            '''
        )
        params = [firm_ctx['firm_id']]
        if history_cutoff:
            query += ' AND datetime(created_at) >= datetime(?)'
            params.append(history_cutoff)
        query += ' ORDER BY created_at DESC LIMIT ?'
        params.append(limit)
        c.execute(query, tuple(params))

        rows = c.fetchall()

        conn.close()



        reports = []

        for row in rows:

            report_id = row[0]

            created_at = row[1]

            raw_access_type = row[3] or 'trial'

            access_context = _report_access_context(raw_access_type)

            reports.append(

                {

                    'id': report_id,

                    'name': _effective_report_name(report_id, created_at, row[4]),

                    'status': 'ready',

                    'created_at': created_at,

                    'total_reviews': row[2] or 0,

                    'access_level': access_context['access_level'],

                    'plan_label': _plan_badge_label(raw_access_type),

                    'plan_type': access_context['plan_type'],

                    'view_url': f'/dashboard/reports/{report_id}',

                    'download_pdf_url': f'/api/reports/{report_id}/pdf',

                }

            )



        return jsonify({'success': True, 'reports': reports, **history_meta}), 200

    except Exception:

        return _safe_api_error(

            'Unable to load reports right now.',

            log_message=f'Failed to load report list for user {current_user.id}',

        )


@app.route('/api/plan/limits', methods=['GET'])
@login_required
def api_plan_limits():
    """Return normalized firm plan + limits for frontend enforcement UX."""
    try:
        firm_ctx, err = _require_firm_context()
        if err:
            return err
        plan_payload = plan_service.get_plan_limits(firm_ctx['firm_id'], db_connect)
        return jsonify(
            {
                'success': True,
                'plan': plan_payload.get('plan'),
                'limits': {
                    'max_users': plan_payload.get('max_users'),
                    'max_reviews_per_upload': plan_payload.get('max_reviews_per_upload'),
                    'max_reports_per_month': plan_payload.get('max_reports_per_month'),
                    'history_days': plan_payload.get('history_days'),
                    'pdf_watermark': bool(plan_payload.get('pdf_watermark', False)),
                },
            }
        ), 200
    except Exception:
        return _safe_api_error(
            'Unable to load plan limits right now.',
            log_message=f'Failed to load plan limits for user {current_user.id}',
        )





@app.route('/api/reports/<int:report_id>', methods=['GET'])

@login_required

# Report detail joins multiple payload fragments; limit read-amplification.

@limiter.limit('30 per minute')

def api_report_detail(report_id):

    """Return report detail payload for in-app report viewing/snippets."""

    try:

        firm_ctx, err = _require_firm_context()

        if err:

            return err

        _purge_expired_deleted_reports(current_user.id)

        conn = db_connect()

        c = conn.cursor()

        c.execute(
            '''
            SELECT id, created_at, total_reviews, avg_rating, themes, top_praise, top_complaints, subscription_type_at_creation, custom_name
            FROM reports
            WHERE id = ?
              AND firm_id = ?
              AND deleted_at IS NULL
            ''',
            (report_id, firm_ctx['firm_id']),
        )

        row = c.fetchone()



        if not row:
            conn.close()
            return jsonify({'success': False, 'error': 'Report not found'}), 404

        history_error, history_meta = _enforce_report_history_access(row[1], firm_ctx['firm_id'])
        if history_error:
            conn.close()
            return history_error



        themes_raw = _deserialize_report_data(row[4], {})

        raw_top_praise = _deserialize_report_data(row[5], [])

        raw_top_complaints = _deserialize_report_data(row[6], [])

        raw_access_type = row[7] or 'trial'

        custom_name = str(row[8] or '').strip() or None

        access_context = _report_access_context(raw_access_type)



        def _normalize_signal_rows(signal_rows):

            output = []

            for item in signal_rows or []:

                if isinstance(item, str):

                    text = item.strip()

                    if text:

                        output.append(text)

                    continue

                if isinstance(item, dict):

                    text = str(item.get('review_text') or '').strip()

                    if text:

                        output.append(text)

            return output



        top_praise = _normalize_signal_rows(raw_top_praise)

        top_complaints = _normalize_signal_rows(raw_top_complaints)



        ordered_themes = sorted(

            [{'name': name, 'mentions': int(mentions)} for name, mentions in (themes_raw or {}).items()],

            key=lambda item: item['mentions'],

            reverse=True,

        )
        c.execute(
            '''
            SELECT id, created_at, themes
            FROM reports
            WHERE firm_id = ?
              AND deleted_at IS NULL
              AND id <> ?
            ORDER BY created_at DESC
            LIMIT 1
            ''',
            (firm_ctx['firm_id'], report_id),
        )
        previous_row = c.fetchone()
        theme_trends = {}
        if previous_row:
            previous_themes = _deserialize_report_data(previous_row[2], {})
            theme_trends = compute_theme_trends(
                {"themes": themes_raw},
                {"themes": previous_themes},
            )



        top_theme = ordered_themes[0] if ordered_themes else {'name': 'No dominant theme', 'mentions': 0}

        total_reviews = int(row[2] or 0)

        avg_rating = float(row[3] or 0.0)

        confidence_score = min(96, 55 + max(0, min(total_reviews, 400)) // 6)

        recommended_tier = 'Team' if total_reviews >= 200 else 'Free'

        if access_context['plan_type'] == 'pro_annual':

            recommended_tier = 'Firm'

        expected_margin_impact = f"{min(22, 6 + (top_theme['mentions'] // 3))}%"



        executive_summary = [

            f"{_report_display_name(report_id, row[1])} is ready for partner review.",

            f"Top focus area: {top_theme['name']} ({top_theme['mentions']} mentions).",

            f"{total_reviews} reviews analyzed with an average rating of {avg_rating:.2f}.",

            f"Plan used for this run: {_plan_badge_label(raw_access_type)}.",

            f"Estimated margin impact after remediation: {expected_margin_impact}.",

            f"Model confidence score: {confidence_score} / 100.",

        ]

        if top_praise:

            executive_summary.append(f"Strongest praise signal: {top_praise[0]}")

        if top_complaints:

            executive_summary.append(f"Most common complaint signal: {top_complaints[0]}")



        paid_access = access_context['access_level'] == 'paid'

        root_cause_themes = _build_root_cause_themes(

            ordered_themes,

            access_context['implementation_theme_limit'],

        ) if paid_access else []

        recommended_changes = _build_recommended_changes(

            ordered_themes,

            access_context['implementation_theme_limit'],

        ) if paid_access else []

        implementation_roadmap = _build_implementation_roadmap(

            ordered_themes,

            access_context['implementation_theme_limit'],

        ) if paid_access else []

        strategic_plans = _build_strategic_plans(

            ordered_themes,

            access_context['strategic_theme_limit'],

        ) if paid_access else []



        conn.close()
        return jsonify(

            {

                'success': True,

                'report': {

                    'id': report_id,

                    'title': _effective_report_name(report_id, row[1], custom_name),

                    'name': _effective_report_name(report_id, row[1], custom_name),

                    'status': 'ready',

                    'created_at': row[1],

                    'custom_name': custom_name,

                    'total_reviews': total_reviews,

                    'avg_rating': avg_rating,

                    'access_level': access_context['access_level'],

                    'plan_type': access_context['plan_type'],

                    'plan_label': _plan_badge_label(raw_access_type),

                    'themes': ordered_themes,
                    'theme_trends': theme_trends,

                    'top_praise': top_praise,

                    'top_complaints': top_complaints,

                    'opportunities_for_enhancement': top_complaints[:5],

                    'executive_summary': executive_summary[:10],

                    'root_cause_themes': root_cause_themes,

                    'recommended_changes': recommended_changes,

                    'implementation_roadmap': implementation_roadmap,

                    'strategic_plans': strategic_plans,

                    'strategy_limits': {

                        'implementation_themes': access_context['implementation_theme_limit'],

                        'strategic_plan_themes': access_context['strategic_theme_limit'],

                    },

                    'key_numbers': {

                        'recommended_tier': recommended_tier,

                        'expected_margin_impact': expected_margin_impact,

                        'confidence_score': confidence_score,

                    },

                    'download_pdf_url': f'/api/reports/{report_id}/pdf',
                    'history_window_days': history_meta['history_window_days'],
                    'history_notice': history_meta['history_notice'],
                    'history_truncated': history_meta['history_truncated'],

                },

            }

        ), 200

    except Exception:

        return _safe_api_error(

            'Unable to load report detail right now.',

            log_message=f'Failed to load report detail {report_id} for user {current_user.id}',

        )





@app.route('/api/reports/<int:report_id>', methods=['PATCH'])
@login_required
def api_report_rename(report_id):
    """Update persisted custom report name for the current firm."""

    try:

        firm_ctx, err = _require_firm_context()

        if err:

            return err



        payload = request.get_json(silent=True) or {}

        requested_name = bleach.clean(str(payload.get('name') or '').strip(), strip=True)

        if len(requested_name) < 3:

            return jsonify({'success': False, 'error': 'Report name must be at least 3 characters.'}), 400

        if len(requested_name) > 120:

            return jsonify({'success': False, 'error': 'Report name must be 120 characters or fewer.'}), 400



        conn = db_connect()

        c = conn.cursor()

        c.execute(

            '''

            SELECT id, created_at, custom_name

            FROM reports

            WHERE id = ?

              AND firm_id = ?

              AND deleted_at IS NULL

            ''',

            (report_id, firm_ctx['firm_id']),

        )

        row = c.fetchone()

        if not row:

            conn.close()

            return jsonify({'success': False, 'error': 'Report not found.'}), 404



        previous_name = str(row[2] or '').strip() or _report_display_name(report_id, row[1])

        c.execute(

            '''

            UPDATE reports

            SET custom_name = ?

            WHERE id = ? AND firm_id = ?

            ''',

            (requested_name, report_id, firm_ctx['firm_id']),

        )

        _log_audit_event(

            conn,

            firm_ctx['firm_id'],

            current_user.id,

            'report',

            report_id,

            'REPORT_RENAMED',

            before_dict={'name': previous_name},

            after_dict={'name': requested_name},

        )

        conn.commit()

        conn.close()

        return jsonify(

            {

                'success': True,

                'report': {

                    'id': report_id,

                    'name': requested_name,

                    'title': requested_name,

                    'custom_name': requested_name,

                },

            }

        ), 200

    except Exception:

        return _safe_api_error(

            'Unable to update report name right now.',

            log_message=f'Failed to rename report {report_id} for user {current_user.id}',

        )





@app.route('/api/reports/<int:report_id>/executive-summary', methods=['GET'])

@login_required

# Export endpoint performs formatted report generation work.

@limiter.limit('20 per hour')

def api_report_executive_summary(report_id):

    """Download an executive-summary text export for leadership circulation."""

    try:

        firm_ctx, err = _require_firm_context()

        if err:

            return err

        if not _has_paid_customer_access(current_user.id):

            return jsonify(

                {

                    'success': False,

                    'error': 'Executive summary export is available on paid plans. Upgrade to unlock this export.',

                    'upgrade_required': True,

                }

            ), 403



        _purge_expired_deleted_reports(current_user.id)

        conn = db_connect()

        c = conn.cursor()

        c.execute(

            '''

            SELECT id, created_at, total_reviews, avg_rating, themes, top_praise, top_complaints, subscription_type_at_creation

            FROM reports

            WHERE id = ?

              AND firm_id = ?

              AND deleted_at IS NULL

            ''',

            (report_id, firm_ctx['firm_id']),

        )

        row = c.fetchone()

        if not row:
            conn.close()
            return jsonify({'success': False, 'error': 'Report not found.'}), 404

        history_error, _ = _enforce_report_history_access(row[1], firm_ctx['firm_id'])
        if history_error:
            conn.close()
            return history_error

        conn.close()



        themes_raw = _deserialize_report_data(row[4], {})

        top_praise = _deserialize_report_data(row[5], [])

        top_complaints = _deserialize_report_data(row[6], [])

        ordered_themes = sorted(

            [{'name': name, 'mentions': int(mentions)} for name, mentions in (themes_raw or {}).items()],

            key=lambda item: item['mentions'],

            reverse=True,

        )

        top_theme = ordered_themes[0] if ordered_themes else {'name': 'No dominant theme', 'mentions': 0}



        def _normalize_signal_rows(signal_rows):

            output = []

            for item in signal_rows or []:

                if isinstance(item, str):

                    text = item.strip()

                    if text:

                        output.append(text)

                    continue

                if isinstance(item, dict):

                    text = str(item.get('review_text') or '').strip()

                    if text:

                        output.append(text)

            return output



        praise_rows = _normalize_signal_rows(top_praise)

        complaint_rows = _normalize_signal_rows(top_complaints)

        created_at = row[1]

        avg_rating = float(row[3] or 0.0)

        total_reviews = int(row[2] or 0)

        plan_label = _plan_badge_label(row[7] or 'trial')



        lines = [

            f'Executive Summary - {_report_display_name(report_id, created_at)}',

            f'Firm: {current_user.firm_name or app.config["FIRM_NAME"]}',

            f'Generated: {datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")}',

            '',

            f'Plan context: {plan_label}',

            f'Total reviews analyzed: {total_reviews}',

            f'Average rating: {avg_rating:.2f}/5',

            f'Top theme: {top_theme["name"]} ({top_theme["mentions"]} mentions)',

            '',

            'Top opportunities:',

        ]

        for item in complaint_rows[:5]:

            lines.append(f'- {item}')

        if not complaint_rows:

            lines.append('- No major complaint signals detected.')

        lines.append('')

        lines.append('Top strengths:')

        for item in praise_rows[:5]:

            lines.append(f'- {item}')

        if not praise_rows:

            lines.append('- No praise highlights recorded in this snapshot.')

        lines.append('')

        lines.append('Next recommended action:')

        lines.append(f'- Assign an owner to address {top_theme["name"]} and track KPI progress in the Action Tracker.')



        from io import BytesIO

        payload = '\n'.join(lines).encode('utf-8')

        out = BytesIO(payload)

        out.seek(0)

        return send_file(

            out,

            as_attachment=True,

            download_name=f'executive_summary_report_{report_id}.txt',

            mimetype='text/plain',

        )

    except Exception:

        return _safe_api_error(

            'Unable to export executive summary right now.',

            log_message=f'Failed executive summary export for report {report_id} user {current_user.id}',

        )





@app.route('/api/reports/<int:report_id>/actions', methods=['GET'])
@login_required
# Action list can be polled heavily from execution UI; keep reads bounded.
@limiter.limit('30 per minute')
def api_report_actions_list(report_id):
    try:

        firm_ctx, err = _require_firm_context()

        if err:

            return err

        firm_plan = get_firm_plan(firm_ctx['firm_id'])
        history_meta = _report_history_metadata(firm_plan)
        history_cutoff = _report_history_cutoff_iso(firm_plan)
        _purge_expired_deleted_reports(current_user.id)

        conn = db_connect()

        c = conn.cursor()

        c.execute(

            '''

            SELECT id, created_at

            FROM reports

            WHERE id = ?

              AND firm_id = ?

              AND deleted_at IS NULL

            ''',

            (report_id, firm_ctx['firm_id']),

        )

        report_row = c.fetchone()

        if not report_row:

            conn.close()

            return jsonify({'success': False, 'error': 'Report not found.'}), 404

        history_error, _ = _enforce_report_history_access(report_row[1], firm_ctx['firm_id'])
        if history_error:
            conn.close()
            return history_error



        _actions_limit = min(max(1, request.args.get('limit', 200, type=int)), 200)

        c.execute(

            '''

            SELECT id, title, owner, owner_user_id, status, due_date, timeframe, kpi, notes, created_at, updated_at, created_by_user_id, updated_by_user_id

            FROM report_action_items

            WHERE firm_id = ? AND report_id = ?

            ORDER BY created_at DESC

            LIMIT ?

            ''',

            (firm_ctx['firm_id'], report_id, _actions_limit),

        )

        rows = c.fetchall()

        conn.close()

        actions = []

        for row in rows:

            actions.append(

                {

                    'id': row[0],

                    'title': row[1],

                    'owner': row[2] or '',

                    'owner_user_id': row[3],

                    'status': row[4] or 'open',

                    'due_date': row[5],

                    'timeframe': row[6] or None,

                    'kpi': row[7] or '',

                    'notes': row[8] or '',

                    'created_at': row[9],

                    'updated_at': row[10],

                    'created_by_user_id': row[11],

                    'updated_by_user_id': row[12],

                }

            )

        has_paid_access = _has_paid_customer_access(current_user.id)

        return jsonify({'success': True, 'actions': actions, 'upsell': {'limit': None if has_paid_access else 1, 'can_add_unlimited': has_paid_access, 'upgrade_message': ('Upgrade to unlock unlimited action items, owners, and KPI tracking.' if not has_paid_access else None)}}), 200

    except Exception:
        return _safe_api_error('Unable to load report actions right now.', log_message=f'Failed to load action items for report {report_id} user {current_user.id}')


@app.route('/api/reports/<int:report_id>/governance-signals', methods=['GET'])
@login_required
# Signals/recommendations query can be expensive for large reports.
@limiter.limit('30 per minute')
def api_report_governance_signals(report_id):
    """Return persisted governance signals + recommendations for a report."""
    try:
        firm_ctx, err = _require_firm_context()
        if err:
            return err

        conn = db_connect()
        c = conn.cursor()
        c.execute(
            '''
            SELECT id, created_at
            FROM reports
            WHERE id = ?
              AND firm_id = ?
              AND deleted_at IS NULL
            ''',
            (report_id, firm_ctx['firm_id']),
        )
        report_row = c.fetchone()
        if not report_row:
            conn.close()
            return jsonify({'error': 'Report not found'}), 404

        history_error, _ = _enforce_report_history_access(report_row[1], firm_ctx['firm_id'])
        if history_error:
            conn.close()
            return history_error

        c.execute(
            '''
            SELECT id, title, description, severity, created_at
            FROM governance_signals
            WHERE report_id = ?
            ORDER BY CASE LOWER(COALESCE(severity, 'low'))
                WHEN 'high' THEN 3
                WHEN 'medium' THEN 2
                WHEN 'low' THEN 1
                ELSE 0
            END DESC, id ASC
            ''',
            (report_id,),
        )
        signal_rows = c.fetchall()

        c.execute(
            '''
            SELECT id, title, priority, suggested_owner, created_at
            FROM governance_recommendations
            WHERE report_id = ?
            ORDER BY CASE LOWER(COALESCE(priority, 'low'))
                WHEN 'high' THEN 3
                WHEN 'medium' THEN 2
                WHEN 'low' THEN 1
                ELSE 0
            END DESC, id ASC
            ''',
            (report_id,),
        )
        recommendation_rows = c.fetchall()
        conn.close()

        signals = [
            {
                'id': int(row[0]),
                'title': str(row[1] or ''),
                'description': str(row[2] or ''),
                'severity': str(row[3] or 'low').lower(),
                'created_at': row[4],
            }
            for row in signal_rows
        ]
        recommendations = [
            {
                'id': int(row[0]),
                'title': str(row[1] or ''),
                'priority': str(row[2] or 'low').lower(),
                'suggested_owner': str(row[3] or ''),
                'created_at': row[4],
            }
            for row in recommendation_rows
        ]
        return jsonify({'signals': signals, 'recommendations': recommendations}), 200
    except Exception:
        return _safe_api_error(
            'Unable to load governance signals right now.',
            log_message=f'Failed to load governance signals for report {report_id} user {current_user.id}',
        )


@app.route('/api/actions', methods=['GET'])
@login_required
# Firm-wide action list is a broad read across reports.
@limiter.limit('30 per minute')
def api_firm_actions_list():
    """Return action items across active reports in the current firm."""
    try:
        firm_ctx, err = _require_firm_context()
        if err:
            return err
        _purge_expired_deleted_reports(current_user.id)
        conn = db_connect()
        c = conn.cursor()
        actions_limit = min(max(1, request.args.get('limit', 500, type=int)), 1000)
        c.execute(
            '''
            SELECT
                rai.id,
                rai.report_id,
                rai.title,
                rai.owner,
                rai.owner_user_id,
                rai.status,
                rai.due_date,
                rai.timeframe,
                rai.kpi,
                rai.notes,
                rai.created_at,
                rai.updated_at,
                rai.created_by_user_id,
                rai.updated_by_user_id,
                r.created_at,
                r.custom_name
            FROM report_action_items rai
            JOIN reports r
              ON r.id = rai.report_id
             AND r.firm_id = rai.firm_id
            WHERE rai.firm_id = ?
              AND r.deleted_at IS NULL
            ORDER BY rai.created_at DESC
            LIMIT ?
            ''',
            (firm_ctx['firm_id'], actions_limit),
        )
        rows = c.fetchall()
        conn.close()
        actions = []
        for row in rows:
            actions.append(
                {
                    'id': row[0],
                    'report_id': row[1],
                    'title': row[2],
                    'owner': row[3] or '',
                    'owner_user_id': row[4],
                    'status': row[5] or 'open',
                    'due_date': row[6],
                    'timeframe': row[7] or None,
                    'kpi': row[8] or '',
                    'notes': row[9] or '',
                    'created_at': row[10],
                    'updated_at': row[11],
                    'created_by_user_id': row[12],
                    'updated_by_user_id': row[13],
                    'report_name': _effective_report_name(row[1], row[14], row[15]),
                    'report_created_at': row[14],
                    'report_status': 'ready',
                }
            )
        return jsonify({'success': True, 'actions': actions}), 200
    except Exception:
        return _safe_api_error(
            'Unable to load actions right now.',
            log_message=f'Failed to load firm actions for user {current_user.id}',
        )


@app.route('/api/reports/<int:report_id>/actions', methods=['POST'])
@login_required
def api_report_actions_create(report_id):
    try:

        firm_ctx, err = _require_firm_context()

        if err:

            return err

        if not _can_assign_actions(firm_ctx['role']):

            return jsonify({'success': False, 'error': 'Insufficient role to assign governance actions.'}), 403

        _purge_expired_deleted_reports(current_user.id)

        payload = request.get_json(silent=True) or {}

        title = bleach.clean((payload.get('title') or '').strip(), strip=True)

        status = (payload.get('status') or 'open').strip().lower()

        due_date = (payload.get('due_date') or '').strip() or None

        timeframe_raw = bleach.clean(str(payload.get('timeframe') or '').strip(), strip=True)

        timeframe = timeframe_raw or None

        kpi = bleach.clean((payload.get('kpi') or '').strip(), strip=True)

        notes = bleach.clean((payload.get('notes') or '').strip(), strip=True)

        if not title:

            return jsonify({'success': False, 'error': 'Action title is required.'}), 400

        if len(title) > 160:

            return jsonify({'success': False, 'error': 'Action title must be 160 characters or fewer.'}), 400

        if status not in ('open', 'in_progress', 'done'):
            status = 'open'
        if due_date and not _allow_past_due_date_for_e2e():
            due_date_error = _validate_action_due_date_local(due_date)
            if due_date_error:
                return jsonify({'success': False, 'error': due_date_error}), 400
        if timeframe and timeframe not in ('Days 1-30', 'Days 31-60', 'Days 61-90'):

            return jsonify({'success': False, 'error': 'Timeframe must be Days 1-30, Days 31-60, or Days 61-90.'}), 400

        conn = db_connect()

        c = conn.cursor()

        c.execute('SELECT id FROM reports WHERE id = ? AND firm_id = ? AND deleted_at IS NULL', (report_id, firm_ctx['firm_id']))

        if not c.fetchone():

            conn.close()

            return jsonify({'success': False, 'error': 'Report not found.'}), 404

        has_paid_access = _has_paid_customer_access(current_user.id)

        if not has_paid_access:

            c.execute('SELECT COUNT(*) FROM report_action_items WHERE firm_id = ? AND report_id = ?', (firm_ctx['firm_id'], report_id))

            action_count_row = c.fetchone()

            action_count = int(action_count_row[0] or 0) if action_count_row else 0

            if action_count >= 1:

                conn.close()

                return jsonify({'success': False, 'error': 'Free plan includes 1 action item per report. Upgrade for unlimited action tracking.', 'upgrade_required': True}), 403

        owner_user_id, owner_text = _resolve_action_owner_assignment(c, firm_ctx['firm_id'], payload.get('owner_user_id'), payload.get('owner'))

        now_iso = datetime.now(timezone.utc).isoformat()

        c.execute(

            '''

            INSERT INTO report_action_items (

                user_id, firm_id, report_id, title, owner, owner_user_id, status, due_date, timeframe, kpi, notes, created_by_user_id, updated_by_user_id, updated_at

            )

            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)

            ''',

            (current_user.id, firm_ctx['firm_id'], report_id, title, owner_text, owner_user_id, status, due_date, timeframe, kpi, notes, current_user.id, current_user.id, now_iso),

        )

        action_id = int(c.lastrowid)

        _log_audit_event(conn, firm_ctx['firm_id'], current_user.id, 'action', action_id, 'ACTION_CREATED', before_dict={}, after_dict={'title': title, 'owner_user_id': owner_user_id, 'owner': owner_text, 'status': status, 'timeframe': timeframe})

        conn.commit()

        c.execute('SELECT id, title, owner, owner_user_id, status, due_date, timeframe, kpi, notes, created_at, updated_at, created_by_user_id, updated_by_user_id FROM report_action_items WHERE id = ?', (action_id,))

        row = c.fetchone()

        conn.close()

        return jsonify({'success': True, 'action': {'id': row[0], 'title': row[1], 'owner': row[2] or '', 'owner_user_id': row[3], 'status': row[4] or 'open', 'due_date': row[5], 'timeframe': row[6] or None, 'kpi': row[7] or '', 'notes': row[8] or '', 'created_at': row[9], 'updated_at': row[10], 'created_by_user_id': row[11], 'updated_by_user_id': row[12]}}), 201

    except ValueError as exc:

        return jsonify({'success': False, 'error': str(exc)}), 400

    except Exception:

        return _safe_api_error('Unable to create action item right now.', log_message=f'Failed to create action item for report {report_id} user {current_user.id}')





@app.route('/api/reports/<int:report_id>/actions/<int:action_id>', methods=['PATCH'])
@login_required
def api_report_actions_update(report_id, action_id):
    """Update a report action item.



    Ownership gate: item must belong to current_user AND live on a non-deleted

    report owned by current_user.  Returns 404 for both not-found and

    unauthorised cases to avoid leaking existence (IDOR-safe).



    Optimistic locking (warning phase): if the client supplies an

    ``If-Match`` header its value is compared against the row's

    ``updated_at`` string; a mismatch returns 409.  Missing ``If-Match``

    is logged as a warning and the update proceeds � flip

    ``ENFORCE_ETAG = True`` (or set env var ENFORCE_ETAG=true) once the

    frontend sends the header on every edit.



    ``updated_at`` is written with sub-second precision so that rapid

    back-to-back edits always produce a distinct ETag.



    The full updated row is returned so the client can store the new

    ``updated_at`` as its next ``If-Match`` value.

    """

    enforce_etag = os.environ.get('ENFORCE_ETAG', 'false').lower() == 'true'

    try:

        firm_ctx, err = _require_firm_context()

        if err:

            return err

        uid = current_user.id

        etag = request.headers.get('If-Match')

        if not etag and enforce_etag:

            return jsonify({'success': False, 'error': 'If-Match header required.'}), 428



        payload = request.get_json(silent=True) or {}

        allowed_fields = {'title', 'owner', 'owner_user_id', 'status', 'due_date', 'timeframe', 'kpi', 'notes'}

        incoming_fields = {key: payload[key] for key in payload.keys() if key in allowed_fields}

        if not incoming_fields:

            return jsonify({'success': False, 'error': 'No valid fields provided for update.'}), 400



        conn = db_connect()

        c = conn.cursor()

        c.execute(

            '''

            SELECT rai.id, rai.title, rai.owner, rai.owner_user_id, rai.status, rai.due_date, rai.timeframe, rai.kpi, rai.notes, rai.updated_at

            FROM report_action_items rai

            WHERE rai.id = ?

              AND rai.report_id = ?

              AND rai.firm_id = ?

              AND EXISTS (

                    SELECT 1 FROM reports r

                    WHERE r.id = rai.report_id

                      AND r.firm_id = ?

                      AND r.deleted_at IS NULL

              )

            ''',

            (action_id, report_id, firm_ctx['firm_id'], firm_ctx['firm_id']),

        )

        owner_row = c.fetchone()

        if not owner_row:

            conn.close()

            return jsonify({'success': False, 'error': 'Action item not found.'}), 404

        current_owner_user_id = owner_row[3]

        if not _can_mutate_action(firm_ctx['role'], uid, current_owner_user_id):

            conn.close()

            return jsonify({'success': False, 'error': 'Insufficient permission to update this action.'}), 403

        if firm_ctx['role'] == 'member' and ({'owner', 'owner_user_id'} & set(incoming_fields.keys())):

            conn.close()

            return jsonify({'success': False, 'error': 'Members cannot reassign ownership.'}), 403

        if etag and owner_row[9] != etag:

            conn.close()

            return jsonify({'success': False, 'error': 'Conflict � item was modified by another request. Reload and retry.'}), 409



        set_parts = []

        values = []

        before_state = {'title': owner_row[1], 'owner': owner_row[2], 'owner_user_id': owner_row[3], 'status': owner_row[4], 'due_date': owner_row[5], 'timeframe': owner_row[6], 'kpi': owner_row[7], 'notes': owner_row[8]}



        if 'title' in incoming_fields:

            title = bleach.clean(str(incoming_fields['title']).strip(), strip=True)

            if not title:

                conn.close()

                return jsonify({'success': False, 'error': 'Action title is required.'}), 400

            if len(title) > 160:

                conn.close()

                return jsonify({'success': False, 'error': 'Action title must be 160 characters or fewer.'}), 400

            set_parts.append('title = ?')

            values.append(title)

        owner_changed = False

        if 'owner' in incoming_fields or 'owner_user_id' in incoming_fields:

            owner_user_id, owner_text = _resolve_action_owner_assignment(c, firm_ctx['firm_id'], incoming_fields.get('owner_user_id'), incoming_fields.get('owner'))

            set_parts.extend(['owner_user_id = ?', 'owner = ?'])

            values.extend([owner_user_id, owner_text])

            owner_changed = True

        if 'status' in incoming_fields:

            status = str(incoming_fields['status']).strip().lower()

            if status not in ('open', 'in_progress', 'done'):

                conn.close()

                return jsonify({'success': False, 'error': 'Status must be open, in_progress, or done.'}), 400

            set_parts.append('status = ?')

            values.append(status)

        if 'due_date' in incoming_fields:
            due_date_raw = str(incoming_fields['due_date']).strip()
            due_date = due_date_raw or None
            if due_date and not _allow_past_due_date_for_e2e():
                due_date_error = _validate_action_due_date_local(due_date)
                if due_date_error:
                    conn.close()
                    return jsonify({'success': False, 'error': due_date_error}), 400
            set_parts.append('due_date = ?')
            values.append(due_date)
        if 'timeframe' in incoming_fields:

            timeframe_raw = str(incoming_fields['timeframe']).strip()

            timeframe = timeframe_raw or None

            if timeframe and timeframe not in ('Days 1-30', 'Days 31-60', 'Days 61-90'):

                conn.close()

                return jsonify({'success': False, 'error': 'Timeframe must be Days 1-30, Days 31-60, or Days 61-90.'}), 400

            set_parts.append('timeframe = ?')

            values.append(timeframe)

        if 'kpi' in incoming_fields:

            set_parts.append('kpi = ?')

            values.append(bleach.clean(str(incoming_fields['kpi']).strip(), strip=True))

        if 'notes' in incoming_fields:

            set_parts.append('notes = ?')

            values.append(bleach.clean(str(incoming_fields['notes']).strip(), strip=True))



        now_precise = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%S.') + f'{datetime.now(timezone.utc).microsecond // 1000:03d}Z'

        set_parts.extend(['updated_at = ?', 'updated_by_user_id = ?'])

        values.extend([now_precise, uid])



        if etag:

            c.execute(f'''UPDATE report_action_items SET {", ".join(set_parts)} WHERE id = ? AND report_id = ? AND firm_id = ? AND updated_at = ?''', (*values, action_id, report_id, firm_ctx['firm_id'], etag))

            if c.rowcount == 0:

                conn.close()

                return jsonify({'success': False, 'error': 'Conflict � item was modified by another request. Reload and retry.'}), 409

        else:

            c.execute(f'''UPDATE report_action_items SET {", ".join(set_parts)} WHERE id = ? AND report_id = ? AND firm_id = ?''', (*values, action_id, report_id, firm_ctx['firm_id']))



        c.execute('SELECT id, title, owner, owner_user_id, status, due_date, timeframe, kpi, notes, created_at, updated_at, created_by_user_id, updated_by_user_id FROM report_action_items WHERE id = ?', (action_id,))

        updated = c.fetchone()

        after_state = {'title': updated[1], 'owner': updated[2], 'owner_user_id': updated[3], 'status': updated[4], 'due_date': updated[5], 'timeframe': updated[6], 'kpi': updated[7], 'notes': updated[8]}

        _log_audit_event(conn, firm_ctx['firm_id'], uid, 'action', action_id, 'ACTION_UPDATED', before_state, after_state)

        if before_state.get('status') != after_state.get('status'):

            _log_audit_event(conn, firm_ctx['firm_id'], uid, 'action', action_id, 'ACTION_STATUS_CHANGED', {'status': before_state.get('status')}, {'status': after_state.get('status')})

        if owner_changed and (before_state.get('owner_user_id') != after_state.get('owner_user_id') or before_state.get('owner') != after_state.get('owner')):

            _log_audit_event(conn, firm_ctx['firm_id'], uid, 'action', action_id, 'ACTION_REASSIGNED', {'owner_user_id': before_state.get('owner_user_id'), 'owner': before_state.get('owner')}, {'owner_user_id': after_state.get('owner_user_id'), 'owner': after_state.get('owner')})

        conn.commit()

        conn.close()

        return jsonify({'success': True, 'action': {'id': updated[0], 'title': updated[1], 'owner': updated[2] or '', 'owner_user_id': updated[3], 'status': updated[4] or 'open', 'due_date': updated[5], 'timeframe': updated[6] or None, 'kpi': updated[7] or '', 'notes': updated[8] or '', 'created_at': updated[9], 'updated_at': updated[10], 'created_by_user_id': updated[11], 'updated_by_user_id': updated[12]}}), 200

    except ValueError as exc:

        return jsonify({'success': False, 'error': str(exc)}), 400

    except Exception:

        return _safe_api_error('Unable to update action item right now.', log_message=f'Failed to update action item {action_id} report {report_id} user {current_user.id}')





@app.route('/api/reports/<int:report_id>/actions/<int:action_id>', methods=['DELETE'])
@login_required
def api_report_actions_delete(report_id, action_id):
    """Delete a report action item."""

    try:

        firm_ctx, err = _require_firm_context()

        if err:

            return err

        if not _can_assign_actions(firm_ctx['role']):

            return jsonify({'success': False, 'error': 'Insufficient permission to delete actions.'}), 403

        conn = db_connect()

        c = conn.cursor()

        c.execute('SELECT id, title, owner, owner_user_id, status FROM report_action_items WHERE id = ? AND report_id = ? AND firm_id = ?', (action_id, report_id, firm_ctx['firm_id']))

        before_row = c.fetchone()

        if not before_row:

            conn.close()

            return jsonify({'success': False, 'error': 'Action item not found.'}), 404

        c.execute(

            '''

            DELETE FROM report_action_items

            WHERE id = ? AND report_id = ? AND firm_id = ?

            ''',

            (action_id, report_id, firm_ctx['firm_id']),

        )

        deleted = c.rowcount

        if deleted > 0:

            _log_audit_event(conn, firm_ctx['firm_id'], current_user.id, 'action', action_id, 'ACTION_DELETED', before_dict={'title': before_row[1], 'owner': before_row[2], 'owner_user_id': before_row[3], 'status': before_row[4]}, after_dict={})

        conn.commit()

        conn.close()

        if deleted <= 0:

            return jsonify({'success': False, 'error': 'Action item not found.'}), 404

        return '', 204

    except Exception:

        return _safe_api_error(

            'Unable to delete action item right now.',

            log_message=f'Failed to delete action item {action_id} report {report_id} user {current_user.id}',

        )





@app.route('/api/execution-summary')

@login_required

# Execution summary computes aggregate counts for workspace scan cards.

@limiter.limit('60 per minute')

@limiter.limit('600 per hour')

def api_execution_summary():

    """Return server-authoritative action-item counts for the current user.



    Scope:

    - Only items whose ``user_id`` matches the authenticated user.

    - Only items whose parent report is non-deleted and owned by the same user

      (mirrors the gating applied by the action-list and report-list endpoints).



    Overdue / due-soon logic is evaluated in the firm's configured timezone

    (``FIRM_TIMEZONE`` env var, defaults to UTC) so counts are deterministic

    and independent of the browser's local time.



    Overdue  : due_date < today AND status != 'done' AND due_date IS NOT NULL

    Due-soon : today <= due_date <= today+7 AND status != 'done' AND due_date IS NOT NULL

    """

    try:

        firm_ctx, err = _require_firm_context()

        if err:

            return err



        # Firm-local "today" � deterministic regardless of browser timezone.

        import zoneinfo as _zi

        _tz      = _zi.ZoneInfo(os.environ.get('FIRM_TIMEZONE', 'UTC'))

        _now     = datetime.now(_tz)

        today    = _now.strftime('%Y-%m-%d')

        due_soon = (_now + timedelta(days=7)).strftime('%Y-%m-%d')



        conn = db_connect()

        c    = conn.cursor()

        c.execute(

            '''

            SELECT

                SUM(CASE WHEN status = 'open'        THEN 1 ELSE 0 END) AS open,

                SUM(CASE WHEN status = 'in_progress' THEN 1 ELSE 0 END) AS in_progress,

                SUM(CASE WHEN status = 'done'        THEN 1 ELSE 0 END) AS done,



                SUM(CASE WHEN status   != 'done'

                          AND due_date IS NOT NULL

                          AND due_date  < ?

                         THEN 1 ELSE 0 END)          AS overdue,



                SUM(CASE WHEN status   != 'done'

                          AND due_date IS NOT NULL

                          AND due_date >= ?

                          AND due_date <= ?

                         THEN 1 ELSE 0 END)          AS due_soon



            FROM report_action_items

            WHERE firm_id = ?

              AND EXISTS (

                      SELECT 1 FROM reports

                      WHERE  id         = report_id

                        AND  firm_id    = ?

                        AND  deleted_at IS NULL

                  )

            ''',

            (today, today, due_soon, firm_ctx['firm_id'], firm_ctx['firm_id']),

        )

        row = c.fetchone()

        conn.close()



        return jsonify({

            'success':      True,

            'open':         row['open']        or 0,

            'in_progress':  row['in_progress'] or 0,

            'done':         row['done']        or 0,

            'overdue':      row['overdue']     or 0,

            'due_soon':     row['due_soon']    or 0,

            'as_of':        today,

            'timezone':     os.environ.get('FIRM_TIMEZONE', 'UTC'),

        }), 200



    except Exception:

        return _safe_api_error(

            'Unable to load execution summary right now.',

            log_message=f'Failed to load execution summary for user {current_user.id}',

        )





@app.route('/api/reports/<int:report_id>', methods=['DELETE'])
@login_required
def api_report_delete(report_id):
    """Soft-delete a report for 30 days. Restoring is gated to paid access."""

    try:

        firm_ctx, err = _require_firm_context()

        if err:

            return err

        if not _can_delete_reports(firm_ctx['role']):

            return jsonify({'success': False, 'error': 'Only firm owners can delete reports.'}), 403

        _purge_expired_deleted_reports(current_user.id)

        conn = db_connect()

        c = conn.cursor()

        c.execute(

            '''

            SELECT id, created_at, subscription_type_at_creation

            FROM reports

            WHERE id = ?

              AND firm_id = ?

              AND deleted_at IS NULL

            ''',

            (report_id, firm_ctx['firm_id']),

        )

        report_row = c.fetchone()

        if not report_row:

            conn.close()

            return jsonify({'success': False, 'error': 'Report not found.'}), 404



        deleted_at = datetime.now(timezone.utc)

        purge_at = deleted_at + timedelta(days=30)

        c.execute(

            '''

            UPDATE reports

            SET deleted_at = ?, purge_at = ?

            WHERE id = ? AND firm_id = ?

            ''',

            (deleted_at.isoformat(), purge_at.isoformat(), report_id, firm_ctx['firm_id']),

        )

        _log_audit_event(

            conn,

            firm_ctx['firm_id'],

            current_user.id,

            'report',

            report_id,

            'REPORT_DELETED',

            before_dict={'deleted_at': None},

            after_dict={'deleted_at': deleted_at.isoformat(), 'purge_at': purge_at.isoformat()},

        )

        conn.commit()

        conn.close()

        return '', 204

    except Exception:

        return _safe_api_error(

            'Unable to delete report right now.',

            log_message=f'Failed to delete report {report_id} for user {current_user.id}',

        )





@app.route('/api/reports/deleted', methods=['GET'])

@login_required

# Deleted report inventory can be enumerated; apply read guardrails.

@limiter.limit('30 per minute')

def api_deleted_reports():

    """List recently deleted reports retained for up to 30 days."""

    limit = request.args.get('limit', 50, type=int) or 50

    limit = max(1, min(limit, 200))

    try:

        firm_ctx, err = _require_firm_context()

        if err:

            return err

        firm_plan = get_firm_plan(firm_ctx['firm_id'])
        history_meta = _report_history_metadata(firm_plan)
        history_cutoff = _report_history_cutoff_iso(firm_plan)
        _purge_expired_deleted_reports(current_user.id)

        can_restore = _has_report_recovery_access(current_user.id) and _can_delete_reports(firm_ctx['role'])



        conn = db_connect()

        c = conn.cursor()

        deleted_query = (
            '''
            SELECT id, created_at, total_reviews, subscription_type_at_creation, deleted_at, purge_at
            FROM reports
            WHERE firm_id = ?
              AND deleted_at IS NOT NULL
              AND (purge_at IS NULL OR datetime(purge_at) > datetime('now'))
            '''
        )
        deleted_params = [firm_ctx['firm_id']]
        if history_cutoff:
            deleted_query += ' AND datetime(created_at) >= datetime(?)'
            deleted_params.append(history_cutoff)
        deleted_query += ' ORDER BY deleted_at DESC LIMIT ?'
        deleted_params.append(limit)
        c.execute(deleted_query, tuple(deleted_params))

        rows = c.fetchall()

        conn.close()



        reports = []

        for row in rows:

            report_id = row[0]

            created_at = row[1]

            raw_access_type = row[3] or 'trial'

            access_context = _report_access_context(raw_access_type)

            reports.append(

                {

                    'id': report_id,

                    'name': _report_display_name(report_id, created_at),

                    'created_at': created_at,

                    'total_reviews': row[2] or 0,

                    'plan_label': _plan_badge_label(raw_access_type),

                    'plan_type': access_context['plan_type'],

                    'deleted_at': row[4],

                    'purge_at': row[5],

                    'can_restore': can_restore,

                }

            )



        return jsonify(

            {

                'success': True,

                'reports': reports,
                **history_meta,

                'can_restore': can_restore,

                'retention_days': 30,

                'upgrade_required': not can_restore,

            }

        ), 200

    except Exception:

        return _safe_api_error(

            'Unable to load recently deleted reports right now.',

            log_message=f'Failed to load deleted reports for user {current_user.id}',

        )





@app.route('/api/reports/<int:report_id>/restore', methods=['POST'])
@login_required
def api_restore_report(report_id):
    """Restore a soft-deleted report if the account has paid recovery access."""

    try:

        firm_ctx, err = _require_firm_context()

        if err:

            return err

        if not _can_delete_reports(firm_ctx['role']):

            return jsonify({'success': False, 'error': 'Only firm owners can restore deleted reports.'}), 403

        _purge_expired_deleted_reports(current_user.id)

        if not _has_report_recovery_access(current_user.id):

            return jsonify(

                {

                    'success': False,

                    'error': 'Upgrade to a paid plan within 30 days to restore deleted reports.',

                    'upgrade_required': True,

                }

            ), 403



        conn = db_connect()

        c = conn.cursor()

        c.execute(

            '''

            SELECT id, created_at, report_hash

            FROM reports

            WHERE id = ?

              AND firm_id = ?

              AND deleted_at IS NOT NULL

              AND (purge_at IS NULL OR datetime(purge_at) > datetime('now'))

            ''',

            (report_id, firm_ctx['firm_id']),

        )

        row = c.fetchone()

        if not row:

            conn.close()

            return jsonify({'success': False, 'error': 'Report not found in recently deleted.'}), 404



        report_hash = row[2]

        if report_hash:

            c.execute(

                '''

                SELECT id

                FROM reports

                WHERE firm_id = ?

                  AND report_hash = ?

                  AND deleted_at IS NULL

                  AND id != ?

                LIMIT 1

                ''',

                (firm_ctx['firm_id'], report_hash, report_id),

            )

            duplicate_row = c.fetchone()

            if duplicate_row:

                conn.close()

                return jsonify(

                    {

                        'success': False,

                        'error': (

                            'A matching active report already exists for this dataset. '

                            'Delete the active duplicate before restoring this report.'

                        ),

                    }

                ), 409



        c.execute(

            '''

            UPDATE reports

            SET deleted_at = NULL, purge_at = NULL

            WHERE id = ? AND firm_id = ?

            ''',

            (report_id, firm_ctx['firm_id']),

        )

        _log_audit_event(

            conn,

            firm_ctx['firm_id'],

            current_user.id,

            'report',

            report_id,

            'REPORT_RESTORED',

            before_dict={'deleted_at': 'set'},

            after_dict={'deleted_at': None, 'purge_at': None},

        )

        conn.commit()

        conn.close()



        return jsonify(

            {

                'success': True,

                'report': {

                    'id': row[0],

                    'name': _report_display_name(row[0], row[1]),

                },

            }

        ), 200

    except Exception:

        return _safe_api_error(

            'Unable to restore this report right now.',

            log_message=f'Failed to restore report {report_id} for user {current_user.id}',

        )





@app.route('/api/reports/<int:report_id>/pdf', methods=['GET'])

@login_required

# PDF generation is CPU/IO heavy; limit per authenticated user.

@limiter.limit('10 per hour', key_func=lambda: f"user:{current_user.id}" if current_user.is_authenticated else get_remote_address())

def api_report_pdf(report_id):
    """Canonical report PDF endpoint for SPA usage."""
    firm_ctx, err = _require_firm_context()
    if err:
        return err
    _purge_expired_deleted_reports(current_user.id)
    conn = db_connect()

    c = conn.cursor()

    reports_has_snapshot_id = _reports_has_column(c, 'snapshot_id')

    report_select = (

        '''

        SELECT id, user_id, created_at, total_reviews, avg_rating, themes, top_praise, top_complaints, subscription_type_at_creation, snapshot_id

        FROM reports

        WHERE id = ?

          AND firm_id = ?

          AND deleted_at IS NULL

        '''

        if reports_has_snapshot_id

        else '''

        SELECT id, user_id, created_at, total_reviews, avg_rating, themes, top_praise, top_complaints, subscription_type_at_creation, NULL AS snapshot_id

        FROM reports

        WHERE id = ?

          AND firm_id = ?

          AND deleted_at IS NULL

        '''

    )

    c.execute(report_select, (report_id, firm_ctx['firm_id']))

    report = c.fetchone()

    latest_subject = _resolve_latest_exposure_subject(c, firm_ctx['firm_id'])



    if not report:
        conn.close()

        return jsonify({'success': False, 'error': 'Report not found'}), 404

    history_error, _ = _enforce_report_history_access(report[2], firm_ctx['firm_id'])
    if history_error:
        conn.close()
        return history_error

    conn.close()



    raw_themes = _deserialize_report_data(report[5], {})

    themes = []

    total_mentions = sum(raw_themes.values()) or 1

    for name, mentions in raw_themes.items():

        themes.append(

            {

                'name': name,

                'mentions': int(mentions),

                'percentage': (int(mentions) / total_mentions) * 100.0,

            }

        )



    top_praise = _deserialize_report_data(report[6], [])

    top_complaints = _deserialize_report_data(report[7], [])

    report_access = report[8] or 'trial'

    access_context = _report_access_context(report_access)

    is_paid_user = access_context['access_level'] == 'paid'

    subscription_type = report_access

    branding = _get_account_branding(current_user.id)

    trend_points = _get_report_trend_points(firm_ctx['firm_id'], limit=12)

    implementation_items = _get_report_action_rows(firm_ctx['firm_id'], report_id, limit=20)
    governance_insights = _get_report_governance_insights(report_id, limit=5)
    canonical_exposure = _compute_exposure_snapshot(
        report[4],
        themes,
        trend_points,
        implementation_items,
    )

    report_snapshot_id = int(report[9]) if report[9] is not None else None



    force_refresh = _truthy_query_param('refresh') or _truthy_query_param('regenerate')
    export_mode = _truthy_query_param('export')
    if export_mode and not _can_export_governance_brief(firm_ctx['role']):
        return jsonify({'success': False, 'error': 'Only owners and partners can export governance briefs.'}), 403
    firm_plan = get_firm_plan(firm_ctx['firm_id'])
    pdf_plan_context = _pdf_export_context_for_plan(firm_plan)
    artifact_bytes = None if force_refresh else _load_report_pdf_artifact(report_id)
    if artifact_bytes is not None and not force_refresh:

        brief_date = datetime.utcnow().strftime("%Y%m%d")

        return _pdf_inline_response(artifact_bytes, brief_date)



    snapshot_payload = {

        'report_id': report_id,

        'snapshot_id': report_snapshot_id,

        'at_risk_count': int(canonical_exposure.get('at_risk_count') or 0),

        'open_actions': int(canonical_exposure.get('open_actions') or 0),

        'overdue_actions': int(canonical_exposure.get('overdue_actions') or 0),

        'avg_rating': float(report[4] or 0.0),

        'exposure_tier': canonical_exposure.get('exposure_tier'),

        'exposure_label': canonical_exposure.get('exposure_label'),

        'partner_escalation_required': canonical_exposure.get('partner_escalation_required'),

        'primary_risk_driver': canonical_exposure.get('primary_risk_driver'),

        'responsible_owner': canonical_exposure.get('responsible_owner'),

    }

    export_ts_utc = datetime.now(timezone.utc).isoformat()

    export_local_iso = datetime.now(zoneinfo.ZoneInfo(os.environ.get('FIRM_TIMEZONE', 'America/Chicago'))).isoformat()

    version_hash = hashlib.sha256(

        json.dumps(

            {'firm_id': firm_ctx['firm_id'], 'report_id': report_id, 'snapshot': snapshot_payload, 'exported_at': export_ts_utc},

            separators=(',', ':'),

            ensure_ascii=False,

        ).encode('utf-8')

    ).hexdigest()[:16]



    firm_display_name = (firm_ctx.get('firm_name') or '').strip() or current_user.firm_name or app.config['FIRM_NAME']

    pdf_buffer = generate_pdf_report(

        firm_name=firm_display_name,

        total_reviews=report[3],

        avg_rating=report[4],

        themes=themes,

        top_praise=top_praise,

        top_complaints=top_complaints,

        is_paid_user=pdf_plan_context["is_paid_user"],
        subscription_type=subscription_type,
        access_level=pdf_plan_context["access_level"],
        plan_type=pdf_plan_context["plan_type"],
        analysis_period=None,

        report_title=_report_display_name(report_id, report[2]),

        report_created_at=report[2],

        trend_points=trend_points,

        implementation_items=implementation_items,

        branding=branding,

        exported_by=(current_user.email or current_user.username or 'Unknown'),

        exported_role=firm_ctx['role'],

        exported_at=export_local_iso,
        version_hash=version_hash,
        exposure_snapshot=canonical_exposure,
        governance_signals=governance_insights.get('signals', []),
        governance_recommendations=governance_insights.get('recommendations', []),
    )
    pdf_bytes = pdf_buffer.getvalue()

    _store_report_pdf_artifact(current_user.id, report_id, pdf_bytes, generated_at=datetime.utcnow().isoformat())

    # Send partner brief email after fresh governance brief generation.
    # Never block report delivery if email provider fails.
    try:
        if PARTNER_EMAILS:
            ordered_themes = sorted(
                themes,
                key=lambda item: int(item.get('mentions') or 0),
                reverse=True,
            )
            top_issue = ordered_themes[0]['name'] if ordered_themes else 'No dominant issue identified yet'

            example_quote = ''
            for item in top_complaints:
                if isinstance(item, str) and item.strip():
                    example_quote = item.strip()
                    break
                if isinstance(item, dict):
                    candidate = str(item.get('review_text') or '').strip()
                    if candidate:
                        example_quote = candidate
                        break

            recommended_discussion = (
                f'Review ownership and next-step actions for "{top_issue}" before the next partner meeting.'
                if top_issue != 'No dominant issue identified yet'
                else 'Review current client issues and confirm assigned action ownership.'
            )

            avg_rating_display = 'Not available'
            if report[4] is not None:
                avg_rating_display = f'{float(report[4]):.2f} / 5'

            dashboard_url = f'{request.host_url.rstrip("/")}/dashboard/reports/{report_id}'
            brief_html = build_partner_brief_html(
                {
                    'firm_name': firm_display_name,
                    'report_name': _report_display_name(report_id, report[2]),
                    'average_rating': avg_rating_display,
                    'top_issue': top_issue,
                    'example_quote': example_quote or 'No client quote available yet.',
                    'recommended_discussion': recommended_discussion,
                    'generated_at': datetime.utcnow().strftime('%b %d, %Y %H:%M UTC'),
                    'dashboard_url': dashboard_url,
                }
            )

            for recipient in PARTNER_EMAILS:
                send_email_with_pdf(
                    recipient,
                    "Clarion Client Experience Brief",
                    brief_html,
                    pdf_bytes,
                    filename=f"governance_brief_{int(report_id)}.pdf",
                )
    except Exception:
        app.logger.exception(
            "Partner brief auto-email failed after governance brief generation. firm_id=%s report_id=%s",
            firm_ctx.get('firm_id'),
            report_id,
        )



    if export_mode:

        # Parity trace for release-day verification: exported PDF values must match canonical latest when this report is latest.

        app.logger.info(

            'Exposure export parity log firm_id=%s report_id=%s snapshot_id=%s exposure_label=%s escalation=%s',

            firm_ctx['firm_id'],

            report_id,

            report_snapshot_id,

            canonical_exposure.get('exposure_label'),

            canonical_exposure.get('partner_escalation_required'),

        )

        if latest_subject and int(latest_subject.get('report_id') or 0) == int(report_id):

            latest_snapshot = _compute_exposure_snapshot(report[4], themes, trend_points, implementation_items)

            if (

                latest_snapshot.get('exposure_label') != canonical_exposure.get('exposure_label')

                or latest_snapshot.get('partner_escalation_required') != canonical_exposure.get('partner_escalation_required')

            ):

                app.logger.warning(

                    'Exposure parity mismatch on latest export firm_id=%s report_id=%s snapshot_id=%s latest_label=%s export_label=%s latest_escalation=%s export_escalation=%s',

                    firm_ctx['firm_id'],

                    report_id,

                    report_snapshot_id,

                    latest_snapshot.get('exposure_label'),

                    canonical_exposure.get('exposure_label'),

                    latest_snapshot.get('partner_escalation_required'),

                    canonical_exposure.get('partner_escalation_required'),

                )



        conn2 = db_connect()

        c2 = conn2.cursor()

        c2.execute(

            '''

            INSERT INTO governance_briefs (firm_id, created_by_user_id, exposure_snapshot_json, version_hash, created_at, pdf_path)

            VALUES (?, ?, ?, ?, ?, ?)

            ''',

            (

                firm_ctx['firm_id'],

                current_user.id,

                json.dumps(snapshot_payload, separators=(',', ':'), ensure_ascii=False),

                version_hash,

                export_ts_utc,

                f'/api/reports/{report_id}/pdf',

            ),

        )

        brief_id = int(c2.lastrowid)

        _log_audit_event(

            conn2,

            firm_ctx['firm_id'],

            current_user.id,

            'governance_brief',

            brief_id,

            'GOVERNANCE_BRIEF_EXPORTED',

            before_dict={},

            after_dict={'version_hash': version_hash, 'created_at': export_ts_utc, 'report_id': report_id},

        )

        conn2.commit()
        send_slack_alert(
            (
                f'[Clarion] Governance brief generated\n'
                f'Firm ID: {firm_ctx["firm_id"]}\n'
                f'Report ID: {int(report_id)}\n'
                f'Brief ID: {brief_id}\n'
                f'Exported by: {current_user.email or current_user.username or current_user.id}'
            )
        )

        conn2.close()



    brief_date = datetime.utcnow().strftime("%Y%m%d")

    return _pdf_inline_response(pdf_bytes, brief_date)





def _send_partner_brief_email_response():
    """Send the latest governance brief summary to configured partner emails via Resend."""
    firm_ctx, err = _require_firm_context()
    if err:
        return err

    resend_api_key = (os.environ.get('RESEND_API_KEY') or '').strip()
    if not resend_api_key:
        return jsonify({'success': False, 'error': 'RESEND_API_KEY is not configured.'}), 500

    recipient_raw = os.environ.get('PARTNER_EMAILS') or ''
    recipients = parse_partner_email_list(recipient_raw)
    if not recipients:
        return jsonify({'success': False, 'error': 'PARTNER_EMAILS is empty or invalid.'}), 400

    conn = db_connect()
    c = conn.cursor()
    c.execute(
        '''
        SELECT id, created_at, avg_rating, themes, top_complaints, custom_name
        FROM reports
        WHERE firm_id = ?
          AND deleted_at IS NULL
        ORDER BY created_at DESC
        LIMIT 1
        ''',
        (firm_ctx['firm_id'],),
    )
    latest_report = c.fetchone()
    conn.close()

    if not latest_report:
        return jsonify({'success': False, 'error': 'No governance brief is available yet.'}), 404

    history_error, _ = _enforce_report_history_access(latest_report[1], firm_ctx['firm_id'])
    if history_error:
        return history_error

    report_id = int(latest_report[0])
    report_name = _effective_report_name(report_id, latest_report[1], latest_report[5])
    raw_themes = _deserialize_report_data(latest_report[3], {}) or {}
    ordered_themes = sorted(
        [{'name': str(name), 'mentions': int(mentions)} for name, mentions in raw_themes.items()],
        key=lambda item: item['mentions'],
        reverse=True,
    )
    top_issue = ordered_themes[0]['name'] if ordered_themes else 'No dominant issue identified yet'

    raw_top_complaints = _deserialize_report_data(latest_report[4], []) or []
    example_quote = ''
    for item in raw_top_complaints:
        if isinstance(item, str) and item.strip():
            example_quote = item.strip()
            break
        if isinstance(item, dict):
            candidate = str(item.get('review_text') or '').strip()
            if candidate:
                example_quote = candidate
                break

    recommended_discussion = (
        f'Review ownership and next-step actions for "{top_issue}" before the next partner meeting.'
        if top_issue != 'No dominant issue identified yet'
        else 'Review current client issues and confirm assigned action ownership.'
    )

    avg_rating = latest_report[2]
    avg_rating_display = 'Not available'
    if avg_rating is not None:
        avg_rating_display = f'{float(avg_rating):.2f} / 5'

    base_url = (os.environ.get('APP_BASE_URL') or request.host_url or '').rstrip('/')
    dashboard_url = f'{base_url}/dashboard/reports/{report_id}' if base_url else ''

    brief_payload = {
        'firm_name': firm_ctx.get('firm_name') or current_user.firm_name or app.config.get('FIRM_NAME'),
        'report_name': report_name,
        'average_rating': avg_rating_display,
        'top_issue': top_issue,
        'example_quote': example_quote or 'No client quote available yet.',
        'recommended_discussion': recommended_discussion,
        'generated_at': datetime.utcnow().strftime('%b %d, %Y %H:%M UTC'),
        'dashboard_url': dashboard_url,
    }
    html = build_partner_brief_html(brief_payload)
    request_payload = request.get_json(silent=True) or {}
    if bool(request_payload.get('append_summary')):
        summary_text = generate_partner_summary(
            {
                'average_rating': avg_rating_display,
                'top_issue': top_issue,
                'example_quote': example_quote or 'No client quote available yet.',
                'recommended_action': recommended_discussion,
            }
        )
        html = f"{html}<pre style='white-space:pre-wrap;font-family:inherit'>{summary_text}</pre>"

    supplied_html = str(request_payload.get('html') or '').strip()
    if supplied_html:
        html = supplied_html

    pdf_artifact = _load_report_pdf_artifact(report_id)
    if not pdf_artifact:
        return jsonify(
            {
                'success': False,
                'error': 'No governance brief PDF is available yet. Open the brief preview once before emailing it.',
            }
        ), 409

    pdf_bytes = pdf_artifact.getvalue() if isinstance(pdf_artifact, BytesIO) else bytes(pdf_artifact)
    from_email = _resolve_from_email()
    subject = f'Clarion Partner Brief: {report_name}'

    try:
        emails_sent = 0
        for recipient in recipients:
            send_email_with_pdf(
                recipient,
                subject,
                html,
                pdf_bytes,
                filename=f'governance_brief_{report_id}.pdf',
            )
            emails_sent += 1
    except Exception:
        return _safe_api_error(
            'Unable to send partner brief email right now.',
            log_message=f'Partner brief email send failed for firm_id={firm_ctx["firm_id"]}',
        )

    return jsonify(
        {
            'success': True,
            'emails_sent': int(emails_sent),
            'recipient_count': len(recipients),
            'recipients': recipients,
            'from_email': from_email,
            'timestamp': datetime.utcnow().isoformat() + 'Z',
        }
    ), 200


@app.route('/api/email-brief/status', methods=['GET'])
@login_required
def api_email_brief_status():
    firm_ctx, err = _require_firm_context()
    if err:
        return err

    resend_api_key = (os.environ.get('RESEND_API_KEY') or '').strip()
    from_email = _resolve_from_email()
    recipients = parse_partner_email_list(os.environ.get('PARTNER_EMAILS') or '')
    missing_requirements = []
    if not resend_api_key:
        missing_requirements.append('email_provider')
    if not recipients:
        missing_requirements.append('recipient_list')

    return jsonify(
        {
            'success': True,
            'delivery_available': len(missing_requirements) == 0,
            'recipient_count': len(recipients),
            'recipients': recipients,
            'from_email': from_email,
            'missing_requirements': missing_requirements,
            'firm_name': firm_ctx.get('firm_name') or current_user.firm_name or app.config.get('FIRM_NAME'),
        }
    ), 200


@app.route("/api/email-governance-brief", methods=["POST"])
@login_required
@limiter.limit('10 per hour', key_func=lambda: f"user:{current_user.id}" if current_user.is_authenticated else get_remote_address())
def email_governance_brief():
    return _send_partner_brief_email_response()


@app.route("/api/test-email")
def test_email():
    html = """
    <h2>Clarion Email Test</h2>
    <p>Your Clarion email system is working.</p>
    """

    send_governance_email(
        "YOUR_EMAIL_HERE",
        "Clarion Email Test",
        html,
    )

    return {"status": "sent"}


@app.route('/api/email-brief', methods=['POST'])
@login_required
# Partner brief delivery can be abused for outbound spam; keep strict per-user limits.
@limiter.limit('10 per hour', key_func=lambda: f"user:{current_user.id}" if current_user.is_authenticated else get_remote_address())
def api_email_brief():
    return _send_partner_brief_email_response()


@app.route('/api/partner-summary', methods=['GET'])
@login_required
def api_partner_summary():
    """Return partner meeting summary text for the latest governance brief."""
    firm_ctx, err = _require_firm_context()
    if err:
        return err

    conn = db_connect()
    c = conn.cursor()
    c.execute(
        '''
        SELECT avg_rating, themes, top_complaints
        FROM reports
        WHERE firm_id = ?
          AND deleted_at IS NULL
        ORDER BY created_at DESC
        LIMIT 1
        ''',
        (firm_ctx['firm_id'],),
    )
    latest_report = c.fetchone()
    conn.close()

    if not latest_report:
        return jsonify({'summary': 'No governance brief is available yet.'}), 200

    avg_rating = latest_report[0]
    avg_rating_display = 'Not available'
    if avg_rating is not None:
        avg_rating_display = f'{float(avg_rating):.2f} / 5'

    raw_themes = _deserialize_report_data(latest_report[1], {}) or {}
    ordered_themes = sorted(
        [{'name': str(name), 'mentions': int(mentions)} for name, mentions in raw_themes.items()],
        key=lambda item: item['mentions'],
        reverse=True,
    )
    top_issue = ordered_themes[0]['name'] if ordered_themes else 'No dominant issue identified yet'

    raw_top_complaints = _deserialize_report_data(latest_report[2], []) or []
    example_quote = ''
    for item in raw_top_complaints:
        if isinstance(item, str) and item.strip():
            example_quote = item.strip()
            break
        if isinstance(item, dict):
            candidate = str(item.get('review_text') or '').strip()
            if candidate:
                example_quote = candidate
                break

    recommended_discussion = (
        f'Review ownership and next-step actions for "{top_issue}" before the next partner meeting.'
        if top_issue != 'No dominant issue identified yet'
        else 'Review current client issues and confirm assigned action ownership.'
    )

    summary = generate_partner_summary(
        {
            'average_rating': avg_rating_display,
            'top_issue': top_issue,
            'example_quote': example_quote or 'No client quote available yet.',
            'recommended_action': recommended_discussion,
        }
    )
    return jsonify({'summary': summary}), 200


@app.route('/api/upload', methods=['POST'])
@limiter.limit('15 per hour')
@login_required
def api_upload():
    """JSON CSV upload endpoint for the React frontend."""
    # TODO: Re-enable email verification gate when email confirmation flow exists.
    firm_ctx, err = _require_firm_context()
    if err:
        return err
    firm_plan = get_firm_plan(firm_ctx['firm_id'])

    access_type = get_report_access_type(current_user.id)





    file = request.files.get('file')
    if not file:
        return jsonify({'error': 'No file provided'}), 400

    if file.filename == '':
        return jsonify({'success': False, 'error': 'No file selected.'}), 400

    if (file.mimetype or '').lower() not in ALLOWED_CSV_MIME_TYPES:
        return jsonify({'error': 'Invalid file type. Please upload a CSV file.'}), 400

    if not file.filename.lower().endswith('.csv'):
        return jsonify({'success': False, 'error': 'Unsupported file type. Please upload a .csv file.'}), 400


    try:
        valid_rows, csv_error, parse_meta = _parse_csv_upload_rows(file, access_type)
        if csv_error:
            return jsonify({'success': False, 'error': csv_error}), 400
        review_limit_error = _enforce_upload_review_limit(valid_rows, firm_plan)
        if review_limit_error:
            return review_limit_error
        report_limit_error = _enforce_report_generation_limit(firm_ctx['firm_id'], firm_plan)
        if report_limit_error:
            return report_limit_error
        return _ingest_rows_into_report(valid_rows, access_type, parse_meta=parse_meta, channel='api')
    except Exception as exc:
        _log_security_event(current_user.id, 'upload_failed', metadata={'error_class': type(exc).__name__, 'channel': 'api'},
        )
        return _safe_api_error(
            'Upload failed due to a server error.',
            log_message=f'CSV upload failed for user {current_user.id}',
        )


def _ingest_rows_into_report(valid_rows, access_type, parse_meta=None, channel='api'):
    trial_usage_count, _ = _get_trial_usage_count(current_user.id, current_user.trial_limit)
    report_hash = _build_report_hash(valid_rows)
    duplicate_report_id = _find_duplicate_report_id(current_user.id, report_hash)
    if duplicate_report_id:
        return jsonify(
            {
                'success': False,
                'error': (
                    "This upload appears identical to an existing report. "
                    "To keep your trends accurate, we don't allow uploading the same reviews twice for the same account."
                ),
            }
        ), 409

    firm_ctx, firm_err = _require_firm_context()
    if firm_err:
        return firm_err
    firm_plan = get_firm_plan(firm_ctx['firm_id'])
    report_limit_error = _enforce_report_generation_limit(firm_ctx['firm_id'], firm_plan)
    if report_limit_error:
        return report_limit_error

    conn = db_connect()
    c = conn.cursor()
    snapshot_report_id = None
    count = 0
    try:
        conn.execute('BEGIN IMMEDIATE')
        _insert_user_reviews_tx(c, current_user.id, valid_rows)
        count = len(valid_rows)

        if (
            os.environ.get('UPLOAD_FAIL_AFTER_REVIEWS') == '1'
            and (app.config.get('DEBUG') or app.config.get('TESTING'))
        ):
            raise RuntimeError('PR5 test: forced failure after review inserts')

        snapshot_report_id = _save_report_snapshot_tx(
            c,
            current_user.id,
            subscription_type=access_type,
            report_hash=report_hash,
        )

        if access_type == 'onetime':
            c.execute(
                '''
                UPDATE users
                SET one_time_reports_used = one_time_reports_used + 1
                WHERE id = ?
                ''',
                (current_user.id,),
            )
        elif access_type == 'trial':
            updated_free_usage = max(
                trial_usage_count + 1,
                _get_trial_report_snapshot_count(current_user.id),
            )
            c.execute(
                '''
                UPDATE users
                SET trial_reviews_used = ?
                WHERE id = ?
                ''',
                (updated_free_usage, current_user.id),
            )

        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

    if snapshot_report_id:
        try:
            scan_recent_reviews_for_signals(db_connect, firm_id=firm_ctx['firm_id'])
        except Exception:
            app.logger.exception('Failed signal monitor scan for firm %s after upload', firm_ctx['firm_id'])

    conn = db_connect()
    c = conn.cursor()
    c.execute(
        '''
        SELECT trial_reviews_used, trial_limit, one_time_reports_purchased, one_time_reports_used, subscription_type
        FROM users
        WHERE id = ?
        ''',
        (current_user.id,),
    )
    usage_row = c.fetchone()
    conn.close()

    usage = {
        'trial_reviews_used': max(
            int(usage_row[0] or 0) if usage_row else 0,
            _get_trial_report_snapshot_count(current_user.id),
        ),
        'trial_limit': usage_row[1] if usage_row else FREE_PLAN_REPORT_LIMIT,
        'one_time_reports_used': usage_row[3] if usage_row else 0,
        'one_time_reports_remaining': max(0, (usage_row[2] if usage_row else 0) - (usage_row[3] if usage_row else 0)),
        'subscription_type': usage_row[4] if usage_row else 'trial',
    }

    if not snapshot_report_id:
        _log_security_event(current_user.id, 'upload_success', metadata={'report_id': None, 'count': count, 'access_type': access_type, 'channel': channel})
        return jsonify(
            {
                'success': True,
                'summary': {
                    'imported_count': count,
                    'report_id': None,
                    'message': 'Upload succeeded, but no snapshot was created.',
                    'truncated_for_plan': bool(parse_meta and parse_meta.get('truncated_for_plan')),
                    'skipped_due_to_plan_limit': int(parse_meta.get('skipped_due_to_plan_limit', 0)) if parse_meta else 0,
                },
                'usage': usage,
            }
        ), 200

    summary_message = f'Success! Imported {count} reviews and saved report snapshot #{snapshot_report_id}.'
    if access_type == 'trial' and parse_meta and parse_meta.get('truncated_for_plan'):
        skipped = int(parse_meta.get('skipped_due_to_plan_limit', 0))
        summary_message = (
            f'Success! We analyzed the first {FREE_PLAN_MAX_REVIEWS_PER_REPORT} valid reviews for the Free plan '
            f'and skipped {skipped} additional reviews. Upgrade to analyze all uploaded reviews.'
        )

    _log_security_event(current_user.id, 'upload_success', metadata={'report_id': snapshot_report_id, 'count': count, 'access_type': access_type, 'channel': channel})
    return jsonify(
        {
            'success': True,
            'summary': {
                'imported_count': count,
                'report_id': snapshot_report_id,
                'message': summary_message,
                'truncated_for_plan': bool(parse_meta and parse_meta.get('truncated_for_plan')),
                'skipped_due_to_plan_limit': int(parse_meta.get('skipped_due_to_plan_limit', 0)) if parse_meta else 0,
            },
            'usage': usage,
        }
    ), 200


@app.route('/api/onboarding/load-demo', methods=['POST'])
@login_required
def api_onboarding_load_demo():
    """Seed a demo dataset for the current firm using the normal ingestion pipeline."""
    try:
        firm_ctx, err = _require_firm_context()
        if err:
            return err

        access_type = get_report_access_type(current_user.id)

        demo_path = os.path.join(app.root_path, 'data', 'demo_reviews.csv')
        if not os.path.exists(demo_path):
            return jsonify({'success': False, 'error': 'Demo dataset is not configured.'}), 500

        with open(demo_path, 'rb') as demo_file:
            demo_bytes = demo_file.read()
        stream = BytesIO(demo_bytes)
        valid_rows, csv_error, parse_meta = _parse_csv_upload_rows(stream, access_type)
        if csv_error:
            return jsonify({'success': False, 'error': csv_error}), 400
        firm_plan = get_firm_plan(firm_ctx['firm_id'])
        review_limit_error = _enforce_upload_review_limit(valid_rows, firm_plan)
        if review_limit_error:
            return review_limit_error
        report_limit_error = _enforce_report_generation_limit(firm_ctx['firm_id'], firm_plan)
        if report_limit_error:
            return report_limit_error

        return _ingest_rows_into_report(valid_rows, access_type, parse_meta=parse_meta, channel='onboarding_demo')
    except Exception:
        return _safe_api_error(
            'Unable to load demo dataset right now.',
            log_message=f'Failed onboarding demo dataset load for user {current_user.id}',
        )




# ===== ERROR HANDLERS =====





@app.errorhandler(429)

def rate_limited(error):

    if request.path.startswith('/api/'):

        reset_ts = int((datetime.now(timezone.utc) + timedelta(minutes=15)).timestamp())

        now_ts = int(datetime.now(timezone.utc).timestamp())

        retry_after = max(reset_ts - now_ts, 1)

        _log_security_event(current_user.id if current_user.is_authenticated else None, 'rate_limit_hit', metadata={'path': request.path, 'reset_timestamp': reset_ts, 'scope': 'api'},

        )

        resp = jsonify(

            {

                'success': False,

                'error': 'Rate limit exceeded. Please try again shortly.',

                'reset_timestamp': reset_ts,

                'request_id': getattr(g, 'request_id', None),

            }

        )

        resp.status_code = 429

        resp.headers['X-RateLimit-Reset'] = str(reset_ts)

        resp.headers['Retry-After'] = str(retry_after)

        return resp



    reset_ts = int((datetime.now(timezone.utc) + timedelta(minutes=15)).timestamp())

    response = render_template('errors/rate_limit.html', reset_timestamp=reset_ts, wait_minutes=15)

    resp = app.make_response((response, 429))

    resp.headers['X-RateLimit-Reset'] = str(reset_ts)

    return resp





@app.errorhandler(404)

def not_found(error):

    if request.path.startswith('/api/'):

        return jsonify({'success': False, 'error': f'API endpoint not found: {request.path}', 'request_id': getattr(g, 'request_id', None)}), 404

    # For all non-API 404s, serve React SPA so React Router handles the path
    if _react_dist_exists:
        return send_from_directory(_REACT_DIST, 'index.html'), 200

    return render_template('marketing_home.html'), 404



@app.errorhandler(500)

def internal_error(error):

    app.logger.exception('Unhandled server error request_id=%s: %s', getattr(g, 'request_id', None), error)

    if request.path.startswith('/api/'):

        return jsonify({'success': False, 'error': 'Internal server error', 'request_id': getattr(g, 'request_id', None)}), 500

    flash('An unexpected server error occurred. Please retry in a moment. If it persists, contact support.', 'danger')

    return render_template('marketing_home.html'), 500



@app.errorhandler(RequestEntityTooLarge)

def file_too_large(error):

    if request.path.startswith('/api/'):

        return jsonify({'success': False, 'error': 'Upload failed: file exceeds the 10 MB limit.', 'request_id': getattr(g, 'request_id', None)}), 413

    flash('Upload failed: file exceeds the 10 MB limit. Compress or split the CSV and try again.', 'danger')

    return redirect(request.referrer or url_for('upload')), 413


@app.errorhandler(CSRFError)
def handle_csrf_error(error):
    app.logger.warning(
        'csrf_error request_id=%s path=%s reason=%s',
        getattr(g, 'request_id', None),
        request.path,
        getattr(error, 'description', str(error)),
    )
    if request.path.startswith('/api/'):
        return (
            jsonify(
                {
                    'success': False,
                    'error': 'Security validation failed. Refresh and try again.',
                    'code': 'csrf_failed',
                    'request_id': getattr(g, 'request_id', None),
                }
            ),
            400,
        )
    flash('Your session token expired. Please refresh and try again.', 'warning')
    return redirect(request.referrer or url_for('marketing_home'))



# ===== APPLICATION ENTRY POINT =====



if __name__ == '__main__':

    port = int(os.environ.get('PORT', 5000))

    app.run(host='0.0.0.0', port=port, debug=app.config['DEBUG'])







