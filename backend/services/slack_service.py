import logging
import os

import requests

SLACK_WEBHOOK = os.getenv("SLACK_WEBHOOK_URL")
logger = logging.getLogger(__name__)


def send_slack_alert(message: str):
    if not SLACK_WEBHOOK or not str(message or "").strip():
        return

    payload = {
        "text": message
    }

    try:
        requests.post(SLACK_WEBHOOK, json=payload, timeout=5)
    except Exception:
        logger.exception("Failed to send Slack alert.")
