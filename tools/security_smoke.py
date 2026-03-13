#!/usr/bin/env python3
"""
5-minute security smoke checks for backend hardening.

Checks:
1) /api/csrf-token returns token
2) login works and session cookie is set
3) CORS allowlist behavior
4) /api/reports/<id>/pdf works and (optional) rate limits to 429 on abuse
5) request_id appears in API errors
"""

from __future__ import annotations

import argparse
import json
import os
import random
import string
import sys
from dataclasses import dataclass
from typing import Any

import requests


@dataclass
class CheckResult:
    name: str
    ok: bool
    details: str


def _ok(name: str, details: str) -> CheckResult:
    return CheckResult(name=name, ok=True, details=details)


def _fail(name: str, details: str) -> CheckResult:
    return CheckResult(name=name, ok=False, details=details)


def _print_result(r: CheckResult) -> None:
    mark = "PASS" if r.ok else "FAIL"
    print(f"[{mark}] {r.name}: {r.details}")


def _as_json(resp: requests.Response) -> dict[str, Any]:
    try:
        data = resp.json()
        if isinstance(data, dict):
            return data
        return {"_non_object_json": data}
    except Exception:
        return {}


def _ensure_demo_data(base_url: str, session: requests.Session, csrf_token: str) -> None:
    headers = {"X-CSRFToken": csrf_token}
    resp = session.post(f"{base_url}/api/onboarding/load-demo", headers=headers, timeout=60)
    if resp.status_code not in (200, 403):
        raise RuntimeError(f"load-demo failed: {resp.status_code} {resp.text[:200]}")


def _first_report_id(base_url: str, session: requests.Session) -> int | None:
    resp = session.get(f"{base_url}/api/reports", timeout=30)
    if resp.status_code != 200:
        return None
    data = _as_json(resp)
    reports = data.get("reports") or []
    if not reports:
        return None
    try:
        return int(reports[0]["id"])
    except Exception:
        return None


def run() -> int:
    parser = argparse.ArgumentParser(description="Security smoke checks")
    parser.add_argument("--base-url", default=os.getenv("SECURITY_SMOKE_BASE_URL", "http://127.0.0.1:5000"))
    parser.add_argument("--allowed-origin", default=os.getenv("SECURITY_SMOKE_ALLOWED_ORIGIN", "https://yourdomain.com"))
    parser.add_argument("--email", default=os.getenv("SECURITY_SMOKE_EMAIL"))
    parser.add_argument("--password", default=os.getenv("SECURITY_SMOKE_PASSWORD"))
    parser.add_argument("--report-id", type=int, default=(int(os.getenv("SECURITY_SMOKE_REPORT_ID")) if os.getenv("SECURITY_SMOKE_REPORT_ID") else None))
    parser.add_argument("--abuse-pdf", action="store_true", help="Send 11 PDF requests and assert 429 on the 11th")
    parser.add_argument("--seed-demo-if-empty", action="store_true", help="Attempt /api/onboarding/load-demo if no report id is found")
    parser.add_argument("--create-dev-user-if-missing", action="store_true", help="Create an account if login fails (for DEV_MODE envs)")
    args = parser.parse_args()

    base_url = args.base_url.rstrip("/")
    s = requests.Session()
    results: list[CheckResult] = []

    # 1) CSRF token
    try:
        r = s.get(f"{base_url}/api/csrf-token", timeout=20)
        body = _as_json(r)
        token = body.get("csrf_token")
        if r.status_code == 200 and isinstance(token, str) and len(token) > 20:
            results.append(_ok("csrf-token", "token returned"))
        else:
            results.append(_fail("csrf-token", f"status={r.status_code} body={body}"))
    except Exception as exc:
        results.append(_fail("csrf-token", f"request error: {exc}"))
        token = None

    # 2) Login + cookie set
    email = args.email
    password = args.password
    if not email or not password:
        results.append(_fail("login-cookie", "missing --email/--password (or SECURITY_SMOKE_EMAIL/PASSWORD env vars)"))
    else:
        r = s.post(f"{base_url}/api/auth/login", json={"email": email, "password": password}, timeout=20)
        if r.status_code != 200 and args.create_dev_user_if_missing:
            suffix = "".join(random.choice(string.ascii_lowercase + string.digits) for _ in range(6))
            email = f"smoke_{suffix}@example.com"
            reg = s.post(
                f"{base_url}/api/auth/register",
                json={"full_name": "Smoke User", "firm_name": "Smoke Firm", "email": email, "password": password},
                timeout=20,
            )
            if reg.status_code in (200, 201):
                r = s.post(f"{base_url}/api/auth/login", json={"email": email, "password": password}, timeout=20)
        body = _as_json(r)
        cookie_names = [c.name.lower() for c in s.cookies]
        has_session_cookie = any("session" in c for c in cookie_names)
        if r.status_code == 200 and has_session_cookie:
            results.append(_ok("login-cookie", f"login ok; cookies={cookie_names}"))
        else:
            results.append(_fail("login-cookie", f"status={r.status_code} cookies={cookie_names} body={body}"))

    # 3) CORS allowlist behavior
    try:
        r_allowed = s.get(f"{base_url}/api/reports", headers={"Origin": args.allowed_origin}, timeout=20)
        allowed_header = r_allowed.headers.get("Access-Control-Allow-Origin")
        if allowed_header == args.allowed_origin:
            results.append(_ok("cors-allowed-origin", f"Access-Control-Allow-Origin={allowed_header}"))
        else:
            results.append(_fail("cors-allowed-origin", f"expected {args.allowed_origin}, got {allowed_header!r}"))
    except Exception as exc:
        results.append(_fail("cors-allowed-origin", f"request error: {exc}"))

    try:
        r_denied = s.get(f"{base_url}/api/reports", headers={"Origin": "https://evil.com"}, timeout=20)
        body = _as_json(r_denied)
        if r_denied.status_code == 403 and isinstance(body.get("request_id"), str):
            results.append(_ok("cors-denied-origin", "403 with request_id"))
        else:
            results.append(_fail("cors-denied-origin", f"status={r_denied.status_code} body={body}"))
    except Exception as exc:
        results.append(_fail("cors-denied-origin", f"request error: {exc}"))

    # 4) request_id in API errors (header + body match)
    rid = "smoke-request-id-123"
    try:
        r = s.get(f"{base_url}/api/not-a-route", headers={"X-Request-ID": rid}, timeout=20)
        body = _as_json(r)
        h_rid = r.headers.get("X-Request-ID")
        b_rid = body.get("request_id")
        if h_rid == rid and b_rid == rid:
            results.append(_ok("request-id-propagation", f"header/body both {rid}"))
        else:
            results.append(_fail("request-id-propagation", f"header={h_rid!r} body={b_rid!r}"))
    except Exception as exc:
        results.append(_fail("request-id-propagation", f"request error: {exc}"))

    # 5) PDF endpoint works + optional abuse check
    report_id = args.report_id
    if report_id is None and args.seed_demo_if_empty and token:
        try:
            _ensure_demo_data(base_url, s, token)
        except Exception as exc:
            results.append(_fail("seed-demo", str(exc)))
    if report_id is None:
        report_id = _first_report_id(base_url, s)

    if report_id is None:
        results.append(_fail("pdf-route", "no report id available; pass --report-id or use --seed-demo-if-empty"))
    else:
        first_pdf = s.get(f"{base_url}/api/reports/{report_id}/pdf", timeout=60)
        if first_pdf.status_code == 200:
            results.append(_ok("pdf-route", f"/api/reports/{report_id}/pdf returned 200"))
        else:
            results.append(_fail("pdf-route", f"status={first_pdf.status_code} body={first_pdf.text[:200]}"))

        if args.abuse_pdf:
            statuses: list[int] = []
            last_json: dict[str, Any] = {}
            last_headers: dict[str, str] = {}
            for _ in range(11):
                rr = s.get(f"{base_url}/api/reports/{report_id}/pdf", timeout=60)
                statuses.append(rr.status_code)
                last_json = _as_json(rr)
                last_headers = dict(rr.headers)
            if 429 in statuses and isinstance(last_json.get("request_id"), str) and last_json.get("reset_timestamp"):
                results.append(
                    _ok(
                        "pdf-rate-limit",
                        f"statuses={statuses}; retry_after={last_headers.get('Retry-After')} reset={last_headers.get('X-RateLimit-Reset')}",
                    )
                )
            else:
                results.append(_fail("pdf-rate-limit", f"statuses={statuses}; last_json={json.dumps(last_json)}"))

    # Print + exit code
    for result in results:
        _print_result(result)
    failed = [r for r in results if not r.ok]
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(run())

