"""
services/leads.py

Forwards "Talk to an Expert" form submissions to mf-engine-v2's own
lead_capture endpoint (see src/modules/lead_capture in that repo). GiftCityFunds
does not store leads itself -- this is a thin proxy, same relationship this
app already has with mf-engine for fund data (services/mf_engine.py).

The endpoint is public (no partner token required), so this is a plain HTTP
call rather than the authenticated flow mf_engine.py uses for fund data.
"""

from __future__ import annotations

import re
from typing import Any, Dict, Optional, Tuple

import requests

from services.mf_engine import BASE_URL, MfEngineError

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

# Identifies submissions from this site in mf-engine's shared lead_capture
# table, which is also fed by other properties (e.g. Zinni).
LEAD_SOURCE = "giftcityfunds_web"


def validate_lead(data: dict) -> Tuple[dict, Optional[str]]:
    """Returns (cleaned_fields, error). error is None when the submission is
    valid. Mirrors mf-engine's own createLeadCaptureSchema validation
    (src/modules/lead_capture/lead_capture.validation.ts) so a bad
    submission is rejected here rather than round-tripping to that API."""
    name = (data.get("name") or "").strip()
    phone = (data.get("phone") or "").strip()
    email = (data.get("email") or "").strip()
    message = (data.get("message") or "").strip()
    page_path = (data.get("page_path") or "").strip() or None
    fields = {"name": name, "phone": phone, "email": email, "message": message, "page_path": page_path}

    if not name or not phone or not email or not message:
        return fields, "Name, phone, email and message are all required."
    if not _EMAIL_RE.match(email):
        return fields, "Enter a valid email address."
    if len(phone) < 7:
        return fields, "Enter a valid phone number."
    if len(message) < 10:
        return fields, "Message must be at least 10 characters."
    return fields, None


def submit_lead(name: str, phone: str, email: str, message: str, page_path: Optional[str]) -> Dict[str, Any]:
    """POSTs to mf-engine-v2's lead_capture endpoint. Raises MfEngineError on
    any connection failure or non-2xx response."""
    try:
        resp = requests.post(
            f"{BASE_URL}/api/v2/lead_capture",
            json={
                "name": name,
                "phone": phone,
                "email": email,
                "message": message,
                "source": LEAD_SOURCE,
                "pagePath": page_path,
            },
            timeout=15,
        )
    except requests.RequestException as exc:
        raise MfEngineError(f"Could not reach mf-engine lead_capture: {exc}") from exc

    if resp.status_code not in (200, 201):
        detail = None
        try:
            detail = resp.json().get("message")
        except ValueError:
            pass
        raise MfEngineError(detail or f"mf-engine lead_capture returned HTTP {resp.status_code}")

    return resp.json()
