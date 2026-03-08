"""Partner brief email rendering + delivery via Resend."""

from __future__ import annotations

from datetime import datetime, timezone
from html import escape
from typing import Any

import resend

from services.email_service import _resolve_from_email


def _safe_text(value: Any, fallback: str = "Not available") -> str:
    text = str(value or "").strip()
    return text or fallback


def parse_partner_email_list(raw: str) -> list[str]:
    """Parse PARTNER_EMAILS env var into a normalized recipient list."""
    if not raw:
        return []
    unique: list[str] = []
    seen = set()
    for item in raw.split(","):
        email = item.strip().lower()
        if not email or "@" not in email:
            continue
        if email in seen:
            continue
        seen.add(email)
        unique.append(email)
    return unique


def build_partner_brief_html(brief_data: dict[str, Any]) -> str:
    """Generate a clean HTML summary for partner monthly brief delivery."""
    firm_name = escape(_safe_text(brief_data.get("firm_name"), "Your Firm"))
    report_name = escape(_safe_text(brief_data.get("report_name"), "Governance Brief"))
    average_rating = escape(_safe_text(brief_data.get("average_rating"), "Not available"))
    top_issue = escape(_safe_text(brief_data.get("top_issue"), "No top issue identified yet"))
    example_quote = escape(_safe_text(brief_data.get("example_quote"), "No client quote available yet"))
    recommended_discussion = escape(
        _safe_text(
            brief_data.get("recommended_discussion"),
            "Review current client issues and confirm assigned action ownership.",
        )
    )
    generated_at = escape(
        _safe_text(
            brief_data.get("generated_at"),
            datetime.now(timezone.utc).strftime("%b %d, %Y %H:%M UTC"),
        )
    )
    dashboard_url = escape(_safe_text(brief_data.get("dashboard_url"), ""))

    dashboard_link_html = (
        f'<p style="margin-top:16px;font-size:13px;color:#475569;">Open workspace: '
        f'<a href="{dashboard_url}" style="color:#1D4ED8;text-decoration:none;">{dashboard_url}</a></p>'
        if dashboard_url and dashboard_url != "Not available"
        else ""
    )

    return f"""<!doctype html>
<html>
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width,initial-scale=1" />
    <title>Partner Brief Summary</title>
  </head>
  <body style="margin:0;padding:24px;background:#F3F5F9;font-family:Segoe UI,Arial,sans-serif;color:#0D1B2A;">
    <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="max-width:680px;margin:0 auto;background:#FFFFFF;border:1px solid #E2E8F0;border-radius:10px;overflow:hidden;">
      <tr>
        <td style="padding:18px 20px;background:#0F2D57;color:#FFFFFF;">
          <div style="font-size:12px;letter-spacing:.08em;text-transform:uppercase;opacity:.9;">Clarion Partner Brief</div>
          <div style="margin-top:8px;font-size:20px;font-weight:700;">{report_name}</div>
          <div style="margin-top:6px;font-size:12px;opacity:.9;">{firm_name} &bull; {generated_at}</div>
        </td>
      </tr>
      <tr>
        <td style="padding:18px 20px 4px 20px;">
          <div style="font-size:12px;text-transform:uppercase;letter-spacing:.08em;color:#64748B;">Average Rating</div>
          <div style="margin-top:4px;font-size:16px;font-weight:600;color:#0F172A;">{average_rating}</div>
        </td>
      </tr>
      <tr>
        <td style="padding:8px 20px;">
          <div style="font-size:12px;text-transform:uppercase;letter-spacing:.08em;color:#64748B;">Top Client Issue</div>
          <div style="margin-top:4px;font-size:16px;font-weight:600;color:#0F172A;">{top_issue}</div>
        </td>
      </tr>
      <tr>
        <td style="padding:8px 20px;">
          <div style="font-size:12px;text-transform:uppercase;letter-spacing:.08em;color:#64748B;">Example Client Quote</div>
          <div style="margin-top:6px;padding:12px;border-left:3px solid #EF4444;background:#F8FAFC;color:#0F172A;font-size:14px;line-height:1.5;">"{example_quote}"</div>
        </td>
      </tr>
      <tr>
        <td style="padding:8px 20px 20px 20px;">
          <div style="font-size:12px;text-transform:uppercase;letter-spacing:.08em;color:#64748B;">Recommended Partner Discussion</div>
          <div style="margin-top:6px;padding:12px;border-left:3px solid #0EA5C2;background:#F8FAFC;color:#0F172A;font-size:14px;line-height:1.5;">{recommended_discussion}</div>
          {dashboard_link_html}
        </td>
      </tr>
    </table>
  </body>
</html>"""


def send_partner_brief_via_resend(
    *,
    api_key: str,
    recipients: list[str],
    subject: str,
    html: str,
    from_email: str | None = None,
) -> int:
    """Send partner brief email to recipient list, return successful send count."""
    resend.api_key = api_key
    resolved_from_email = from_email or _resolve_from_email()
    sent = 0
    for recipient in recipients:
        resend.Emails.send(
            {
                "from": resolved_from_email,
                "to": [recipient],
                "subject": subject,
                "html": html,
            }
        )
        sent += 1
    return sent
