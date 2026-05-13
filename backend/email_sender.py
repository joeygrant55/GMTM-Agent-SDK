"""
SendGrid v3 sender for outreach_draft artifacts.

Reads SENDGRID_API_KEY and SPARQ_FROM_EMAIL from env. If either is missing, send_outreach_email
returns ok=False with reason="send_infra_unconfigured" — the caller transitions the artifact to
'queued' and logs for manual send. This is the trust-ladder default: nothing goes out without
explicit athlete approval AND configured infrastructure.
"""

import os
import re
from typing import Optional
import requests


EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def is_valid_email(addr: Optional[str]) -> bool:
    if not addr or not isinstance(addr, str):
        return False
    return bool(EMAIL_RE.match(addr.strip()))


def send_outreach_email(
    to_email: str,
    to_name: Optional[str],
    subject: str,
    body: str,
    reply_to_email: Optional[str] = None,
    reply_to_name: Optional[str] = None,
) -> dict:
    api_key = os.environ.get("SENDGRID_API_KEY")
    from_email = os.environ.get("SPARQ_FROM_EMAIL")
    from_name = os.environ.get("SPARQ_FROM_NAME", "SPARQ Recruiting")

    if not api_key or not from_email:
        return {"ok": False, "reason": "send_infra_unconfigured"}

    if not is_valid_email(to_email):
        return {"ok": False, "reason": "invalid_to_email"}

    payload = {
        "personalizations": [
            {
                "to": [{"email": to_email, **({"name": to_name} if to_name else {})}],
                "subject": subject or "(no subject)",
            }
        ],
        "from": {"email": from_email, "name": from_name},
        "content": [{"type": "text/plain", "value": body or ""}],
    }
    if reply_to_email and is_valid_email(reply_to_email):
        payload["reply_to"] = {
            "email": reply_to_email,
            **({"name": reply_to_name} if reply_to_name else {}),
        }

    try:
        res = requests.post(
            "https://api.sendgrid.com/v3/mail/send",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=15,
        )
        if 200 <= res.status_code < 300:
            return {
                "ok": True,
                "message_id": res.headers.get("X-Message-Id"),
                "status_code": res.status_code,
            }
        return {
            "ok": False,
            "reason": "sendgrid_error",
            "status_code": res.status_code,
            "body": res.text[:500],
        }
    except requests.RequestException as e:
        return {"ok": False, "reason": "network_error", "error": str(e)[:200]}
