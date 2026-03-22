"""Centralized transactional email delivery with retry logic.

NOTE — Inbound email classification (agent office integration)
--------------------------------------------------------------
This module currently handles outbound transactional email only.
Inbound classification and routing for the Clarion Agent Office
is documented in the policy layer and not yet wired to runtime code.

When an inbound email integration is built (e.g. Zoho webhook, polling
script, or forwarding rule into admin@clarionhq.co), the classification
logic should be added here as a dedicated function:

    # TODO: inbound_classify(raw_email: dict) -> str
    # Returns one of: SALES/INTEREST | CUSTOMER FEEDBACK | SUPPORT |
    #   PARTNERSHIPS | PRESS/MEDIA | INVESTOR | SECURITY | GENERAL/UNCLEAR
    # See: Clarion-Agency/memory/email_routing_policy.md for rules.
    # Classifies by: sender domain, mailbox alias, keywords, intent,
    #   security sensitivity, business importance (in that priority order).
    # Output feeds agent routing and email_log.md append logic.
"""

from __future__ import annotations

import logging
import os
import time
from dataclasses import dataclass
from email.utils import parseaddr
from io import BytesIO
from typing import Optional

import resend
from flask import current_app, has_app_context, render_template

try:
    from flask_mail import Mail, Message
except Exception:  # noqa: BLE001
    class Message:  # simple fallback for local tests without Flask-Mail installed
        def __init__(self, subject=None, recipients=None, html=None, body=None):
            self.subject = subject
            self.recipients = recipients or []
            self.html = html
            self.body = body

    class Mail:
        def init_app(self, app):
            return None

        def send(self, msg):
            logger.info("MAIL_FALLBACK: subject=%s recipients=%s", msg.subject, msg.recipients)


mail = Mail()
logger = logging.getLogger(__name__)
resend.api_key = os.getenv("RESEND_API_KEY")
KNOWN_WORKING_RESEND_EMAIL = "onboarding@resend.dev"


@dataclass
class EmailPayload:
    to_email: str
    subject: str
    template_name: str
    context: dict


@dataclass
class EmailDeliveryResult:
    success: bool
    provider: str | None
    from_email: str | None = None
    error_type: str | None = None
    error_message: str | None = None


@dataclass
class SenderResolution:
    from_email: str
    source: str


def init_mail(app):
    mail.init_app(app)


def is_valid_recipient(email: str) -> bool:
    _, parsed = parseaddr(email or "")
    return bool(parsed and "@" in parsed)


def _format_sender(address: str, display_name: str) -> str:
    normalized_address = str(address or "").strip()
    if not normalized_address:
        return ""
    _, parsed = parseaddr(normalized_address)
    if not parsed or "@" not in parsed:
        return ""
    if "<" in normalized_address and ">" in normalized_address:
        return normalized_address
    return f"{display_name} <{parsed}>"


def _known_working_resend_sender(display_name: str = "Clarion") -> str:
    return _format_sender(KNOWN_WORKING_RESEND_EMAIL, display_name)


def resolve_from_email_choice(display_name: str = "Clarion") -> SenderResolution:
    raw = (os.getenv("RESEND_FROM_EMAIL") or os.getenv("FROM_EMAIL") or "").strip()
    resolved = _format_sender(raw, display_name)
    if resolved:
        return SenderResolution(from_email=resolved, source="configured_sender")
    if (os.getenv("RESEND_API_KEY") or "").strip():
        fallback = _known_working_resend_sender(display_name)
        logger.warning(
            "Falling back to known working Resend sender for %s: configured_sender=%s fallback_sender=%s",
            display_name,
            raw or "<empty>",
            fallback,
        )
        return SenderResolution(from_email=fallback, source="resend_dev_fallback")
    return SenderResolution(from_email="", source="none")


def _resolve_from_email(display_name: str = "Clarion") -> str:
    return resolve_from_email_choice(display_name).from_email


def uses_known_working_resend_sender(from_email: str | None) -> bool:
    _, parsed = parseaddr(from_email or "")
    return parsed.strip().lower() == KNOWN_WORKING_RESEND_EMAIL


def _has_resend_delivery_config() -> bool:
    return bool((os.getenv("RESEND_API_KEY") or "").strip() and _resolve_from_email())


def _classify_delivery_exception(provider: str, exc: Exception) -> tuple[str, str]:
    message = str(exc).strip() or exc.__class__.__name__
    normalized = message.lower()
    if provider == "resend":
        if any(token in normalized for token in ["timed out", "failed to establish a new connection", "connectionpool", "forbidden by its access permissions", "name or service not known", "getaddrinfo", "max retries exceeded"]):
            return "provider_network_error", f"Resend could not be reached from this runtime: {message}"
        if any(token in normalized for token in ["401", "403", "unauthorized", "forbidden", "api key"]):
            return "provider_auth_error", f"Resend rejected the request credentials: {message}"
        if any(token in normalized for token in ["from", "sender", "domain", "invalid", "validation"]):
            return "provider_request_error", f"Resend rejected the sender or request payload: {message}"
        return "provider_runtime_error", f"Resend failed while processing the request: {message}"
    if provider == "mail":
        return "mail_runtime_error", f"Configured mail delivery failed: {message}"
    return "delivery_runtime_error", message


def _send_via_resend(payload: EmailPayload, html_body: str, text_body: str) -> bool:
    resend.api_key = os.getenv("RESEND_API_KEY")
    sender = resolve_from_email_choice()
    from_email = sender.from_email
    logger.info(
        "Sending Resend email: subject=%s to=%s from=%s sender_source=%s sender_match_known_working=%s",
        payload.subject,
        payload.to_email,
        from_email or "-",
        sender.source,
        uses_known_working_resend_sender(from_email),
    )
    resend.Emails.send(
        {
            "from": from_email,
            "to": [payload.to_email],
            "subject": payload.subject,
            "html": html_body,
            "text": text_body,
        }
    )
    logger.info("Email sent via Resend: subject=%s to=%s", payload.subject, payload.to_email)
    return True


def _send_via_flask_mail(msg: Message, payload: EmailPayload) -> bool:
    mail.send(msg)
    logger.info("Email sent via Flask-Mail: subject=%s to=%s", payload.subject, payload.to_email)
    return True


def send_templated_email_result(payload: EmailPayload, *, retries: int = 3, backoff_s: float = 1.5) -> EmailDeliveryResult:
    if not is_valid_recipient(payload.to_email):
        logger.warning("Skipping email; invalid recipient: %s", payload.to_email)
        return EmailDeliveryResult(
            success=False,
            provider=None,
            error_type="invalid_recipient",
            error_message=f"Recipient address is invalid: {payload.to_email}",
        )

    html_body = render_template(f"emails/{payload.template_name}.html", **payload.context)
    text_body = render_template(f"emails/{payload.template_name}.txt", **payload.context)
    msg = Message(
        subject=payload.subject,
        recipients=[payload.to_email],
        html=html_body,
        body=text_body,
    )

    mail_enabled = bool(current_app.config.get("MAIL_ENABLED")) if has_app_context() else False
    provider = "resend" if _has_resend_delivery_config() else "mail" if mail_enabled else None
    from_email = _resolve_from_email()
    if not provider:
        logger.warning("Skipping email; no delivery provider is configured for %s", payload.subject)
        return EmailDeliveryResult(
            success=False,
            provider=None,
            error_type="provider_not_configured",
            error_message=f"No email delivery provider is configured for {payload.subject}.",
        )

    for attempt in range(1, max(1, retries) + 1):
        try:
            if _has_resend_delivery_config():
                _send_via_resend(payload, html_body, text_body)
            else:
                _send_via_flask_mail(msg, payload)
            return EmailDeliveryResult(success=True, provider=provider, from_email=from_email or None)
        except Exception as exc:  # noqa: BLE001
            logger.exception("Email send failed on attempt %s: %s", attempt, exc)
            if attempt < retries:
                time.sleep(backoff_s * attempt)
            else:
                error_type, error_message = _classify_delivery_exception(provider, exc)
                return EmailDeliveryResult(
                    success=False,
                    provider=provider,
                    from_email=from_email or None,
                    error_type=error_type,
                    error_message=error_message,
                )

    return EmailDeliveryResult(
        success=False,
        provider=provider,
        from_email=from_email or None,
        error_type="delivery_runtime_error",
        error_message="Email delivery failed for an unknown reason.",
    )


def send_templated_email(payload: EmailPayload, *, retries: int = 3, backoff_s: float = 1.5) -> bool:
    return send_templated_email_result(payload, retries=retries, backoff_s=backoff_s).success


def send_verification_email(to_email: str, verification_link: str, firm_name: str) -> bool:
    return send_verification_email_with_result(to_email, verification_link, firm_name).success


def send_verification_email_with_result(to_email: str, verification_link: str, firm_name: str) -> EmailDeliveryResult:
    return send_templated_email_result(
        EmailPayload(
            to_email=to_email,
            subject="Verify your Clarion account",
            template_name="verify",
            context={"verification_link": verification_link, "firm_name": firm_name},
        ),
        retries=1,
        backoff_s=0.0,
    )


def send_password_reset_email(to_email: str, reset_link: str, firm_name: str) -> bool:
    return send_templated_email(
        EmailPayload(
            to_email=to_email,
            subject="Reset your Clarion password",
            template_name="password_reset",
            context={"reset_link": reset_link, "firm_name": firm_name},
        )
    )


def send_payment_confirmation_email(
    to_email: str,
    plan_name: str,
    amount: str,
    receipt_url: Optional[str],
    firm_name: str,
) -> bool:
    return send_templated_email(
        EmailPayload(
            to_email=to_email,
            subject="Payment confirmation - Clarion",
            template_name="payment_confirmation",
            context={
                "plan_name": plan_name,
                "amount": amount,
                "receipt_url": receipt_url,
                "firm_name": firm_name,
            },
        )
    )


def send_two_factor_code_email(to_email: str, code: str, firm_name: str) -> bool:
    return send_templated_email(
        EmailPayload(
            to_email=to_email,
            subject="Your Clarion verification code",
            template_name="two_factor_code",
            context={"code": code, "firm_name": firm_name},
        )
    )


def send_governance_email(to_email: str, subject: str, html_content: str):
    params = {
        "from": _resolve_from_email("Clarion Governance"),
        "to": [to_email],
        "subject": subject,
        "html": html_content,
    }
    response = resend.Emails.send(params)
    return response


def send_email(to_email: str, subject: str, html: str):
    params = {
        "from": _resolve_from_email(),
        "to": [to_email],
        "subject": subject,
        "html": html,
    }
    response = resend.Emails.send(params)
    return response


def send_email_batch(recipients: list, subject: str, html: str):
    emails = []
    for recipient in recipients:
        emails.append(
            {
                "from": _resolve_from_email(),
                "to": [recipient],
                "subject": subject,
                "html": html,
            }
        )

    results = []
    for email in emails:
        results.append(resend.Emails.send(email))

    return results


def send_email_with_pdf(
    to_email: str,
    subject: str,
    html: str,
    pdf_bytes: bytes,
    filename: str = "governance_brief.pdf",
):
    if isinstance(pdf_bytes, BytesIO):
        pdf_bytes = pdf_bytes.getvalue()
    elif isinstance(pdf_bytes, memoryview):
        pdf_bytes = pdf_bytes.tobytes()
    elif isinstance(pdf_bytes, bytearray):
        pdf_bytes = bytes(pdf_bytes)

    params = {
        "from": _resolve_from_email(),
        "to": [to_email],
        "subject": subject,
        "html": html,
        "attachments": [{"filename": filename, "content": list(pdf_bytes)}],
    }

    return resend.Emails.send(params)
