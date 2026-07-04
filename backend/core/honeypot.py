"""
Track O Step 4.1 — Honeypot field anti-bot for signup endpoints.

The honeypot pattern: render a form field that is HIDDEN to humans via
CSS (display:none / position:absolute off-screen) but VISIBLE to bots
that scrape rendered HTML / Shadow DOM and fill every text input.

The chosen field name (`website`) is intentionally innocuous + common:
many bots heuristically fill any field named "website", "url",
"company" with URL/text to maximize their chances.

Threat model
============

CATCHES: naive-to-medium bots that scrape rendered HTML and fill all
        text inputs (estimated ~50% of automated signup attacks).
DOES NOT CATCH: sophisticated bots that call the API directly via
        curl/requests without ever rendering the frontend. For those
        we need CAPTCHA (O4.4 — hCaptcha integration).

Anti-enumeration response
=========================

When honeypot fires we return the SAME uniform 202 success response as
a legitimate signup. The bot has no way to distinguish "I was caught"
from "I succeeded" — so it can't:
  - Adapt its filling strategy
  - Skip the honeypot field on retry
  - Discover the field name via differential responses

Without uniform response, a bot could probe with hp filled vs empty,
notice different response codes/bodies, and learn to skip the trap.

Recording
=========

Honeypot hits are logged WARNING + recorded as audit event + counted
as Prometheus metric `signups_total{flow, status="honeypot_triggered"}`
so operator can see attack volume in dashboard without spurious
signups polluting real conversion rate.

Public API
==========

    is_honeypot_triggered(honeypot_value: str | None) -> bool
        True if honeypot field is non-empty (= bot caught).

    HONEYPOT_FIELD_NAME: str
        The canonical field name to use in Pydantic models.
        Pinned by sentinel so renaming requires updating all 3 signup
        forms (merchant, customer-portal, embed-SDK widget).
"""

from typing import Optional


# Pin del nome del campo — sentinel test verifica match in tutti i request model.
# Cambio del nome richiede update sincronizzato in:
#   - backend/routers/customer_auth.py SignupRequest
#   - backend/models/user.py UserCreate
#   - frontend signup forms (V2)
#   - embed-SDK signup component (V2)
HONEYPOT_FIELD_NAME = "website"


def is_honeypot_triggered(honeypot_value: Optional[str]) -> bool:
    """Return True if honeypot field is non-empty (= bot detected).

    Args:
        honeypot_value: value of the honeypot field from the request body.
                        None or empty string = legitimate human (hidden
                        field not filled). Any non-empty value = bot
                        caught.

    Returns:
        True if the value is set + non-empty (after strip). False
        otherwise.

    Notes:
        - Whitespace-only values count as triggered (some bots send " "
          to "tick the box" without exposing actual content).
        - Length not checked: even 1-character fill is enough signal.
    """
    if honeypot_value is None:
        return False
    if not isinstance(honeypot_value, str):
        # Defensive: if frontend sends int/bool/list, treat as triggered
        # (legitimate frontend always sends string-or-null).
        return True
    return bool(honeypot_value.strip())


__all__ = ["HONEYPOT_FIELD_NAME", "is_honeypot_triggered"]
