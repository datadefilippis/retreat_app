"""
PII scrubbing for Sentry events.

Strategy (3-layer defense):
    - Sensitive field NAMES → values redacted recursively in event tree
    - Sensitive HTTP HEADERS → redacted in request.headers section
    - Free-text strings (exc messages) → emails/JWT/Bearer tokens masked

This module is internal (underscore prefix) — only used by sentry.py.
Extension: add patterns to PII_FIELDS / PII_HEADERS as needed.
"""
import re
from typing import Any, Optional

# Field names whose VALUES must be redacted (case-insensitive substring match)
PII_FIELDS = frozenset({
    "password", "passwd", "pwd",
    "token", "api_key", "apikey", "secret",
    "authorization", "auth",
    "card_number", "cardnumber", "cvc", "cvv",
    "iban", "ssn", "tax_id", "fiscal_code", "codice_fiscale",
    "session_id", "session", "cookie",
    "private_key", "client_secret",
})

# HTTP header names to redact (case-insensitive, exact match)
PII_HEADERS = frozenset({
    "authorization", "cookie", "set-cookie",
    "x-api-key", "x-auth-token", "x-csrf-token",
})

# Regex patterns to mask in free-text strings
_EMAIL_PATTERN = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
_BEARER_PATTERN = re.compile(r"Bearer\s+[A-Za-z0-9._\-]+", re.IGNORECASE)
_JWT_PATTERN = re.compile(r"eyJ[A-Za-z0-9_=-]+\.[A-Za-z0-9_=-]+\.[A-Za-z0-9_.+/=-]+")

# Inline keyword-value masking for free-text strings.
# Catches patterns like:
#   "Password was X"  /  "password=X"  /  "password: X"
#   "secret is X"     /  "token = X"   /  "api_key was X"
# This is a 4th-layer defense: developers should never embed PII in exception
# messages, but if they do, this pattern catches the most common "keyword + value"
# inline format. Does NOT match free prose like "I forgot my password" (no value).
_KEYWORD_VALUE_PATTERN = re.compile(
    r"(?i)\b(password|passwd|pwd|secret|token|api[\s_-]?key|auth)\b"
    r"\s*(?:was|is|=|:)\s*([^\s.,;]+)",
)

_REDACTED = "[Filtered]"


def _is_pii_key(key: Any) -> bool:
    if not isinstance(key, str):
        return False
    lower = key.lower()
    return any(pii in lower for pii in PII_FIELDS)


def _is_pii_header(key: Any) -> bool:
    return isinstance(key, str) and key.lower() in PII_HEADERS


def _mask_text(text: str) -> str:
    if not isinstance(text, str):
        return text
    text = _EMAIL_PATTERN.sub(_REDACTED, text)
    text = _BEARER_PATTERN.sub(f"Bearer {_REDACTED}", text)
    text = _JWT_PATTERN.sub(_REDACTED, text)
    # 4th layer: keyword-value pairs (e.g. "Password was X", "token=Y")
    text = _KEYWORD_VALUE_PATTERN.sub(rf"\1 {_REDACTED}", text)
    return text


def _scrub_recursive(obj: Any, in_headers: bool = False) -> Any:
    """
    Recursively walk an event/breadcrumb dict and redact sensitive values.

    in_headers: True when traversing an HTTP headers dict (different rules).
    """
    if isinstance(obj, dict):
        result = {}
        for k, v in obj.items():
            recurse_in_headers = in_headers or (
                isinstance(k, str) and k.lower() in ("headers", "request_headers")
            )
            if (in_headers and _is_pii_header(k)) or (not in_headers and _is_pii_key(k)):
                result[k] = _REDACTED
            else:
                result[k] = _scrub_recursive(v, in_headers=recurse_in_headers)
        return result
    if isinstance(obj, list):
        return [_scrub_recursive(item, in_headers=in_headers) for item in obj]
    if isinstance(obj, str):
        return _mask_text(obj)
    return obj


def scrub_event(event: dict, hint: Optional[dict] = None) -> Optional[dict]:
    """
    Sentry before_send hook.

    Returns the scrubbed event, or None to drop the event entirely.
    Errors during scrubbing fall through to dropping (better than send PII unmasked).
    """
    try:
        return _scrub_recursive(event)
    except Exception:
        return None


def scrub_breadcrumb(crumb: dict, hint: Optional[dict] = None) -> Optional[dict]:
    """Sentry before_breadcrumb hook. Same scrubbing logic as events."""
    try:
        return _scrub_recursive(crumb)
    except Exception:
        return None
