# Launch Day Runbook

Use this checklist for a controlled production launch.

## 0) Interpreter pre-check (Windows local dev only)

Before doing anything, confirm you are using the correct Python:
```bat
cd backend
venv312\Scripts\python.exe -c "import dotenv, resend; print('OK')"
```
Expected output: `OK`. If you see `ModuleNotFoundError`, you are on the wrong Python.
Use `start.bat` or always invoke `venv312\Scripts\python.exe` explicitly.

## 1) Environment and secrets

- [ ] `SECRET_KEY` is set to a long random value.
- [ ] Stripe live keys are configured (`STRIPE_PUBLISHABLE_KEY`, `STRIPE_SECRET_KEY`).
- [ ] `STRIPE_WEBHOOK_SECRET` is set from Stripe Dashboard.
- [ ] `RESEND_API_KEY` and `RESEND_FROM_EMAIL` are set and verified in Resend dashboard.
- [ ] `SENTRY_DSN` is configured for production error tracking.
- [ ] `SESSION_COOKIE_SECURE=true` and `SESSION_COOKIE_HTTPONLY=true` in production.

## 2) Startup and health

- [ ] Deploy latest commit.
- [ ] Confirm startup log shows correct interpreter and env vars:
  ```
  [clarion:startup] interpreter='.../python...' env_vars_loaded=True RESEND_API_KEY=SET from_email='...'
  ```
  If `env_vars_loaded=False` or `RESEND_API_KEY=MISSING`, stop and fix environment before continuing.
- [ ] Verify app health endpoint returns 200:
  ```bash
  curl -fsS https://<your-domain>/health
  ```
- [ ] Verify metrics endpoint is reachable (internal/authorized as applicable):
  ```bash
  curl -fsS https://<your-domain>/metrics | head
  ```

## 3) Functional smoke test

- [ ] Submit one feedback entry through `/feedback`.
- [ ] Log in to `/login` and confirm dashboard updates.
- [ ] Upload a small valid CSV and verify records import.
- [ ] Generate a PDF report from admin dashboard.

## 4) Billing and email verification

- [ ] Complete one Stripe checkout in live-safe mode.
- [ ] Confirm webhook delivery to `/stripe-webhook` in Stripe events log.
- [ ] Trigger password reset and verify email delivery.
- [ ] Trigger account verification flow and verify email delivery.

## 5) Operations checks

- [ ] Confirm backup job is scheduled.
  - Windows: `venv312\Scripts\python.exe scripts\backup_db.py`
  - Linux/cloud: `python scripts/backup_db.py`
- [ ] Perform one restore drill in non-production (`scripts/restore_db.sh`).
- [ ] Confirm on-call contact and rollback owner are assigned.

## 6) Post-launch (first 24 hours)

- [ ] Watch error rate and logs every 1-2 hours.
- [ ] Review payment failures and webhook retries.
- [ ] Review email bounce/deferral reports.
- [ ] Capture customer-reported issues in a launch bug list.

## Suggested go/no-go gate

Proceed when all sections 0-4 are complete and section 5 has backup + restore validated.
