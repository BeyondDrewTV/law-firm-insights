"""Weekly governance brief email scheduler."""

from __future__ import annotations

import os
from typing import Iterable

from apscheduler.schedulers.background import BackgroundScheduler

from governance import generate_governance_brief
from services.email_service import send_email_batch


scheduler = BackgroundScheduler(timezone=os.getenv("FIRM_TIMEZONE", "America/Chicago"))


def _normalize_recipients(recipients: Iterable[str]) -> list[str]:
    normalized: list[str] = []
    for value in recipients:
        email = str(value or "").strip()
        if email:
            normalized.append(email)
    return normalized


def weekly_brief():
    try:
        html = generate_governance_brief()
        recipients = _normalize_recipients(os.getenv("PARTNER_EMAILS", "").split(","))
        if not recipients:
            return

        send_email_batch(
            recipients,
            "Weekly Clarion Client Experience Brief",
            html
        )
    except Exception:
        # Keep scheduler resilient; failures should not stop future runs.
        return


def start_scheduler():
    if scheduler.running:
        return

    # Prevent duplicate scheduler startup under Flask debug reloader.
    if os.environ.get("FLASK_ENV") == "development" and os.environ.get("WERKZEUG_RUN_MAIN") != "true":
        return

    scheduler.add_job(
        weekly_brief,
        trigger="cron",
        day_of_week="mon",
        hour=8,
        id="weekly_governance_brief_email",
        replace_existing=True,
    )

    scheduler.start()
