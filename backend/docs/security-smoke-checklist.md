# Security Smoke Checklist (5 Minutes)

Run this after UI changes to confirm security hardening is still intact.

## Prerequisites
- Backend running.
- A valid test account (`SECURITY_SMOKE_EMAIL`, `SECURITY_SMOKE_PASSWORD`).
- Optional: report id (`SECURITY_SMOKE_REPORT_ID`) or use `--seed-demo-if-empty`.
- Optional: explicit allowed origin (`SECURITY_SMOKE_ALLOWED_ORIGIN`).

## One-command smoke run
From repo root:

```bash
python scripts/security_smoke.py \
  --base-url http://127.0.0.1:5000 \
  --email "$SECURITY_SMOKE_EMAIL" \
  --password "$SECURITY_SMOKE_PASSWORD" \
  --allowed-origin "https://yourdomain.com" \
  --seed-demo-if-empty \
  --abuse-pdf
```

Expected PASS checks:
1. `/api/csrf-token` returns a token.
2. Login succeeds and session cookie is present.
3. CORS allowlist works for allowed origin; denied origin returns `403` with `request_id`.
4. `/api/reports/<id>/pdf` returns `200` and rate-limits to `429` on abuse.
5. `request_id` appears in API error body and matches `X-Request-ID` header.

## Manual curl spot checks

### Allowed origin
```bash
curl -i http://127.0.0.1:5000/api/reports -H "Origin: https://yourdomain.com"
```
Expect:
- `Access-Control-Allow-Origin: https://yourdomain.com`

### Denied origin
```bash
curl -i http://127.0.0.1:5000/api/reports -H "Origin: https://evil.com"
```
Expect:
- `403`
- JSON includes `request_id`

### Request ID propagation
```bash
curl -i http://127.0.0.1:5000/api/not-a-route -H "X-Request-ID: req-check-001"
```
Expect:
- response header `X-Request-ID: req-check-001`
- body includes `"request_id":"req-check-001"`
