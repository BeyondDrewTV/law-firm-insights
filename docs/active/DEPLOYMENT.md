# Production Deployment Guide (Render / Railway / Heroku)

## 1) Prerequisites
- Domain + TLS enabled.
- Stripe live keys + `STRIPE_WEBHOOK_SECRET`.
- Resend account with `RESEND_API_KEY` + `RESEND_FROM_EMAIL` (or SMTP fallback).
- `SECRET_KEY` generated (64+ chars).

## 2) Environment variables
Use `config.example.py` as baseline and set at minimum:
- `SECRET_KEY`
- `DATABASE_PATH`
- `STRIPE_SECRET_KEY`, `STRIPE_PUBLISHABLE_KEY`, `STRIPE_WEBHOOK_SECRET`
- `RESEND_API_KEY`, `RESEND_FROM_EMAIL` — **required for email delivery**
- `SENTRY_DSN` (recommended)

## 3) Start command

> **Local Windows dev:** Always use the venv312 interpreter explicitly.
> `gunicorn` and `python` resolve to system binaries without activation,
> which lack project dependencies and will silently skip `.env` loading.

**Local dev (Windows):**
```bat
cd backend
start.bat
```
Or explicitly:
```bat
cd backend
venv312\Scripts\python.exe app.py
```

**Production (Gunicorn — cloud platform or Linux server):**
```bash
# Platform manages its own venv from requirements.txt; use relative gunicorn:
gunicorn -c gunicorn.conf.py app:app

# Linux local server with explicit venv312:
backend/venv312/bin/gunicorn -c gunicorn.conf.py app:app
```

## 4) Platform notes
### Render
- Build: `pip install -r requirements.txt`
- Start: `gunicorn -c gunicorn.conf.py app:app`
- Add persistent disk for SQLite (or migrate to Postgres).

#### Render staging environment (recommended)
Create a separate staging service to protect production security settings during UI iteration.
- Service name: `clarion-backend-staging`
- Branch: staging branch (not `main`)
- Start command: `gunicorn -c gunicorn.conf.py app:app`
- Set explicit env values for staging:
  - `FLASK_ENV=production`
  - `DEV_MODE=false`
  - `SECRET_KEY=<staging-secret>`
  - `REDIS_URL=<staging-redis-url>`
  - `CORS_ALLOWED_ORIGINS=https://staging.<your-domain>`
- Keep staging and production origin allowlists separate.
- Run security smoke checks against staging after frontend changes.

### Railway
- Same build/start commands.
- Ensure volume mount for SQLite persistence.

### Heroku
- Use `web: gunicorn -c gunicorn.conf.py app:app` in Procfile.
- Prefer Postgres for production; SQLite ephemeral FS is risky.

## 5) HTTPS and security
- Force HTTPS redirects at platform edge.
- `SESSION_COOKIE_SECURE=1`
- `SESSION_COOKIE_SAMESITE=Lax`
- Keep `FLASK_ENV` off development in production.

## 6) Health & metrics
- `GET /health` for uptime checks.
- `GET /metrics` for basic request/error/latency telemetry.

## 7) Stripe webhook
- Endpoint: `https://<your-domain>/stripe-webhook`
- Configure events:
  - `checkout.session.completed`
  - `customer.subscription.updated`
  - `customer.subscription.deleted`

## 8) Email end-to-end verification checklist
1. Confirm startup log shows `RESEND_API_KEY=SET` and `from_email` set.
2. Register a new account in staging.
3. Confirm verification email arrives and link works.
4. Trigger forgot-password, confirm reset email arrives.
5. Verify sender domain SPF/DKIM/DMARC configured in Resend dashboard.

## 9) Backup/restore

**Windows (venv312):**
```bat
cd backend
venv312\Scripts\python.exe scripts\backup_db.py
```

**Linux/cloud:**
```bash
python scripts/backup_db.py
```
Restore with `scripts/restore_db.sh <backup.gz>`.

## 10) Post-change security smoke test
After any UI deploy (staging first, then prod), run:
```bash
# Linux/cloud (platform Python):
python scripts/security_smoke.py \
  --base-url https://staging.<your-domain> \
  --email "$SECURITY_SMOKE_EMAIL" \
  --password "$SECURITY_SMOKE_PASSWORD" \
  --allowed-origin "https://staging.<your-domain>" \
  --abuse-pdf

# Windows (venv312):
venv312\Scripts\python.exe scripts\security_smoke.py ^
  --base-url http://localhost:5000 ^
  --email %SECURITY_SMOKE_EMAIL% ^
  --password %SECURITY_SMOKE_PASSWORD%
```
Checklist details: `docs/security-smoke-checklist.md`.
