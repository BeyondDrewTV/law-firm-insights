# Operations Playbook

## Stripe subscription disputes
1. Retrieve customer timeline from Stripe dashboard.
2. Compare against internal `reports` and usage counters.
3. If dispute valid, refund and disable subscription access.
4. If fraud suspected, lock account and preserve logs for evidence.

## Failed/declined payments
1. Check latest invoice/payment intent status in Stripe.
2. Ask customer to update payment method in billing portal.
3. Grant short grace period (24-72h) by policy, then downgrade access.
4. Send follow-up email with next steps and support contact.

## Manual account adjustments (admin CLI)

> **Interpreter note:** Always run admin scripts with the venv312 interpreter on Windows.
> Using system Python (`python` or `py`) will fail with import errors.

**Windows:**
```bat
cd backend
venv312\Scripts\python.exe scripts\admin_cli.py --help
```

**Linux/cloud (platform venv active):**
```bash
python scripts/admin_cli.py --help
```

Examples:
- Add one-time credits:
  ```bat
  venv312\Scripts\python.exe scripts\admin_cli.py grant-credits --email user@firm.com --count 2
  ```
- Set subscription status:
  ```bat
  venv312\Scripts\python.exe scripts\admin_cli.py set-subscription --email user@firm.com --type monthly --status active
  ```
- Force email verification:
  ```bat
  venv312\Scripts\python.exe scripts\admin_cli.py verify-email --email user@firm.com
  ```

## Bug investigation workflow
1. Correlate support ticket ID with request timestamp.
2. Check startup log for `[clarion:startup]` line — confirms interpreter and env var status.
3. Pull Sentry issue + application logs.
4. Reproduce in staging with anonymized data.
5. Ship patch + regression test.

## Downtime response
1. Confirm outage via `/health` and host provider status page.
2. Roll back to last stable release if deployment-triggered.
3. Restore DB from latest backup if data corruption involved.
4. Publish customer status update every 30 minutes.
5. Run postmortem within 24 hours.

## Scaling procedure
- Short term: increase Gunicorn workers/threads via `GUNICORN_WORKERS` env var.
- Mid term: migrate from SQLite to Postgres + Redis cache/queue.
- Long term: move CSV ingest and PDF generation to background workers (Celery/RQ).

## Stripe webhook failure recovery
1. Identify failed webhook deliveries in Stripe dashboard.
2. Re-send failed events after validating endpoint health.
3. If prolonged outage, run reconciliation script against Stripe subscriptions and local users.
4. Log reconciliation actions in incident notes.
