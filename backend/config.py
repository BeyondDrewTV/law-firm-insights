"""

Configuration classes for Clarion application
Loads settings from environment variables

"""



import os

import sys

from dotenv import load_dotenv



load_dotenv()





class Config:

    """Application configuration"""



    # Flask

    APP_ENV = (os.environ.get('APP_ENV') or os.environ.get('FLASK_ENV') or 'development').strip().lower()

    DEBUG = os.environ.get('FLASK_ENV') == 'development' or os.environ.get('FLASK_DEBUG') == '1'



    _secret_key_raw = os.environ.get('SECRET_KEY')

    SECRET_KEY = _secret_key_raw.strip() if _secret_key_raw else ''

    _known_dev_secret_keys = {

        '',

        'dev-local-insecure-secret-key',

        'changeme',

        'change-me',

        'replace-me',

        'insecure-secret',

        'default-secret-key',

    }

    if APP_ENV == 'production' and (not SECRET_KEY or SECRET_KEY.lower() in _known_dev_secret_keys):

        raise RuntimeError('Invalid SECRET_KEY for production. Set SECRET_KEY to a strong random value in environment variables before startup.')

    if not SECRET_KEY:

        SECRET_KEY = 'dev-local-insecure-secret-key'

    FORCE_HTTPS = os.environ.get('FORCE_HTTPS', '1') == '1'

    ENABLE_SECURITY_HEADERS = os.environ.get('ENABLE_SECURITY_HEADERS', '1') == '1'

    CORS_ALLOWED_ORIGINS = os.environ.get('CORS_ALLOWED_ORIGINS', '').strip()

    SECURITY_CSP_POLICY = os.environ.get(

        'SECURITY_CSP_POLICY',

        "default-src 'self'; "

        "base-uri 'self'; frame-ancestors 'self'; object-src 'none'; "

        "script-src 'self' 'unsafe-inline' https:; "

        "style-src 'self' 'unsafe-inline' https:; "

        "img-src 'self' data: https:; "

        "connect-src 'self' https:;",

    )



    SESSION_COOKIE_HTTPONLY = True

    SESSION_COOKIE_SAMESITE = os.environ.get('SESSION_COOKIE_SAMESITE', 'Lax')

    _session_secure_env = os.environ.get('SESSION_COOKIE_SECURE')

    SESSION_COOKIE_SECURE = (_session_secure_env == '1') if _session_secure_env is not None else not DEBUG

    PERMANENT_SESSION_LIFETIME_SECONDS = int(os.environ.get('PERMANENT_SESSION_LIFETIME_SECONDS', str(60 * 60 * 12)))



    # Database URL (PostgreSQL target). Development falls back to local SQLite when unset.
    _database_url_env = (os.environ.get('DATABASE_URL') or '').strip()
    if _database_url_env:
        DATABASE_URL = _database_url_env
        DATABASE_PATH = ''
        print(f'[DB] Using DATABASE_URL: {DATABASE_URL}', file=sys.stderr, flush=True)
    else:
        _db_env = (os.environ.get('DATABASE_PATH') or '').strip()
        if _db_env:
            DATABASE_PATH = os.path.abspath(_db_env)
        else:
            DATABASE_PATH = os.path.abspath(
                os.path.join(os.path.dirname(os.path.abspath(__file__)), 'feedback.db')
            )
        DATABASE_URL = f"sqlite:///{DATABASE_PATH.replace(os.sep, '/')}"
        print(f'[DB] DATABASE_URL not set. Falling back to SQLite file: {DATABASE_PATH}', file=sys.stderr, flush=True)


    # For managed DB services, encryption at rest is provided by the infrastructure layer.

    DATABASE_ENCRYPTION_AT_REST = os.environ.get('DATABASE_ENCRYPTION_AT_REST', 'provider-managed')



    # Admin credentials

    ADMIN_EMAIL = os.environ.get('ADMIN_EMAIL') or 'founder@clarionhq.co'

    ADMIN_USERNAME = os.environ.get('ADMIN_USERNAME') or 'admin'

    _admin_password_raw = (os.environ.get('ADMIN_PASSWORD') or '').strip()
    _known_weak_admin_passwords = {
        '',
        'changeme',
        'changeme123',
        'change-me',
        'password',
        'admin',
        'admin123',
        'letmein',
        'secret',
    }
    if APP_ENV == 'production' and (
        not _admin_password_raw
        or _admin_password_raw.lower() in _known_weak_admin_passwords
    ):
        raise RuntimeError(
            'Unsafe ADMIN_PASSWORD for production. '
            'Set ADMIN_PASSWORD to a strong unique value in environment variables before startup.'
        )
    ADMIN_PASSWORD = _admin_password_raw if _admin_password_raw else 'changeme123'



    # Firm information

    FIRM_NAME = os.environ.get('FIRM_NAME') or 'Law Firm'



    # File upload

    MAX_CONTENT_LENGTH = int(os.environ.get('MAX_CONTENT_LENGTH', str(10 * 1024 * 1024)))



    # Stripe configuration

    STRIPE_PUBLISHABLE_KEY = os.environ.get('STRIPE_PUBLISHABLE_KEY')

    STRIPE_SECRET_KEY = os.environ.get('STRIPE_SECRET_KEY')

    STRIPE_WEBHOOK_SECRET = os.environ.get('STRIPE_WEBHOOK_SECRET')



    # Stripe Price IDs
    STRIPE_PRICE_ID_TEAM_MONTHLY = os.environ.get('STRIPE_PRICE_ID_TEAM_MONTHLY')
    STRIPE_PRICE_ID_TEAM_ANNUAL = os.environ.get('STRIPE_PRICE_ID_TEAM_ANNUAL')
    STRIPE_PRICE_ID_FIRM_MONTHLY = os.environ.get('STRIPE_PRICE_ID_FIRM_MONTHLY')
    STRIPE_PRICE_ID_FIRM_ANNUAL = os.environ.get('STRIPE_PRICE_ID_FIRM_ANNUAL')

    # Pricing
    FREE_TRIAL_LIMIT = int(os.environ.get('FREE_TRIAL_LIMIT', 1))
    TEAM_MONTHLY_PRICE = int(os.environ.get('TEAM_MONTHLY_PRICE', 179))
    TEAM_ANNUAL_PRICE = int(os.environ.get('TEAM_ANNUAL_PRICE', 1790))
    FIRM_MONTHLY_PRICE = int(os.environ.get('FIRM_MONTHLY_PRICE', 449))
    FIRM_ANNUAL_PRICE = int(os.environ.get('FIRM_ANNUAL_PRICE', 4490))

    # Mail configuration

    MAIL_ENABLED = os.environ.get('MAIL_ENABLED', '0') == '1'

    MAIL_SERVER = os.environ.get('MAIL_SERVER', 'smtp.sendgrid.net')

    MAIL_PORT = int(os.environ.get('MAIL_PORT', '587'))

    MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS', '1') == '1'

    MAIL_USE_SSL = os.environ.get('MAIL_USE_SSL', '0') == '1'

    MAIL_USERNAME = os.environ.get('MAIL_USERNAME')

    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')

    MAIL_DEFAULT_SENDER = os.environ.get('MAIL_DEFAULT_SENDER', 'no-reply@example.com')

    MAIL_MAX_RETRIES = int(os.environ.get('MAIL_MAX_RETRIES', '3'))

    TWO_FACTOR_OTP_TTL_SECONDS = int(os.environ.get('TWO_FACTOR_OTP_TTL_SECONDS', '600'))

    ENABLE_2FA = os.environ.get('ENABLE_2FA', '0') == '1'



    # â”€â”€ Reverse-proxy hop count (PR4b) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

    # Controls ProxyFix(x_for=N): must equal the number of trusted proxies

    # between the internet and Gunicorn.  Set in your .env or system environment.

    #

    #   Nginx only               â†’ PROXY_HOPS=1  (default)

    #   Cloudflare + Nginx       â†’ PROXY_HOPS=2

    #   ALB/ELB + Nginx          â†’ PROXY_HOPS=2

    #   Cloudflare + ALB + Nginx â†’ PROXY_HOPS=3

    #

    # Wrong value = either IP spoofing (too low) or wrong IP resolved (too high).

    PROXY_HOPS = int(os.environ.get('PROXY_HOPS', '1'))



    # â”€â”€ Redis (F3/F7 PR4) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

    # Required in production for shared rate-limiting and brute-force tracking.

    # In development, fall back to in-memory if absent (app.py emits a warning).

    REDIS_URL = os.environ.get('REDIS_URL', '')

    # Flask-Limiter reads RATELIMIT_STORAGE_URI directly from app.config.

    # Use Redis when available; memory:// only in dev/test.

    RATELIMIT_STORAGE_URI = REDIS_URL if REDIS_URL else 'memory://'

    _disable_rl_env = os.environ.get('DISABLE_RATE_LIMITS_IN_DEV')

    if _disable_rl_env is None:

        DISABLE_RATE_LIMITS_IN_DEV = APP_ENV != 'production'

    else:

        DISABLE_RATE_LIMITS_IN_DEV = _disable_rl_env.strip().lower() in {'1', 'true', 'yes', 'on'}



    # â”€â”€ Monitoring / logging â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

    SENTRY_DSN = os.environ.get('SENTRY_DSN')

    SENTRY_TRACES_SAMPLE_RATE = float(os.environ.get('SENTRY_TRACES_SAMPLE_RATE', '0.1'))

    LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO')

    LOG_DIR = os.environ.get('LOG_DIR', 'logs')






