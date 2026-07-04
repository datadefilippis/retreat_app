"""
PII redaction for outbound LLM requests.

Wave 5.1 (2026-05) — GDPR compliance + defence in depth.

Why this exists
---------------
The chat AI's tool results carry merchant business data that often
includes personal-data fields of the merchant's CLIENTS: email
addresses, phone numbers, IBAN-like codes. Anthropic is a sub-
processor under GDPR Art. 28; sending raw PII out by default doesn't
break the rules (we have a DPA in place — see Wave 5 docs follow-up)
but minimising PII exposure is best practice and lowers blast radius
if a key ever leaks.

What gets redacted
------------------
This redactor focuses on FIELD-LEVEL PII that's mostly NOISE for the
AI's reasoning — the model rarely needs the exact email of a customer
to answer "qual è il mio cliente top?", it just needs the name + the
revenue. So we mask:

  - Email addresses        ord***@cafe-***.test
  - Phone numbers          +41 79 *** *** 01
  - IBAN-like codes        CH** **** **** **** **** *01
  - Tax IDs / VAT numbers  ITxxxxxxxxxxx (last 4 digits visible)

What is NOT redacted
--------------------
  - Customer / supplier NAMES ("Caffè Centrale Snc") — these are
    business identities visible on shop signs and invoices, not
    personal data in the strict GDPR sense. The AI needs them to
    cite the correct customer in its answer ("il tuo top cliente
    è Caffè Centrale Snc").
  - Monetary amounts.
  - Dates, internal IDs (UUIDs), counts.

The intent is: enough redaction to satisfy data-minimisation, not
enough to break the AI's reasoning.

Public API
----------
    redact_pii(obj: Any) -> Any
        Recursively walks dicts/lists, masking detected PII fields.
        Returns a NEW object — never mutates the input. Safe to call
        on any tool result before serialising for the LLM.

    is_likely_pii_field(field_name: str) -> bool
        Heuristic: True for keys whose names suggest PII (email,
        phone, iban, tax_id, vat_number, codice_fiscale). Used to
        catch values that might not match the regex (e.g. an oddly-
        formatted phone) just because the field name flags them.
"""
from __future__ import annotations

import re
from typing import Any, Set


# ── Regex patterns ──────────────────────────────────────────────────────────

_EMAIL_RE = re.compile(
    r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}",
)
# Phones: international + or 0 prefix, 7-15 digits with optional spaces / -.
# Defensive — catches +41 79 123 4567, 0039 333 1234567, +1-555-123-4567, etc.
_PHONE_RE = re.compile(
    r"(?:\+|00)?\d[\d\s\-\.\(\)]{6,15}\d",
)
# IBAN: 2 letters + 2 check digits + up to 30 alphanumerics. Strict enough
# not to false-positive on random text.
_IBAN_RE = re.compile(
    r"\b[A-Z]{2}\d{2}[A-Z0-9]{10,30}\b",
)
# Italian Codice Fiscale: 16 alphanumeric, mixed case OR uppercase
_CODICE_FISCALE_RE = re.compile(
    r"\b[A-Z]{6}\d{2}[A-Z]\d{2}[A-Z]\d{3}[A-Z]\b",
    re.IGNORECASE,
)
# Generic European VAT (ITxxxxxxxxxxx, DExxxxxxxxx, etc.) — 11-13 chars after 2-letter prefix
_VAT_RE = re.compile(
    r"\b[A-Z]{2}\d{9,13}\b",
)


# Field names commonly carrying PII. Lower-cased for case-insensitive compare.
_PII_FIELD_NAMES: Set[str] = {
    "email",
    "customer_email",
    "supplier_email",
    "phone",
    "phone_number",
    "tel",
    "telefono",
    "iban",
    "codice_fiscale",
    "tax_id",
    "vat_number",
    "p_iva",
    "partita_iva",
}


# ── Masking helpers ─────────────────────────────────────────────────────────


def _mask_email(value: str) -> str:
    """Keep first 3 chars of local part + domain root + TLD, hide the rest.

    ordini@caffe-centrale.test  ->  ord***@caf***.test
    """
    if "@" not in value:
        return _mask_generic(value)
    local, _, domain = value.partition("@")
    domain_parts = domain.split(".")
    if len(domain_parts) >= 2:
        root_part = domain_parts[0]
        tld = domain_parts[-1]
        masked_local = local[:3] + "***" if len(local) > 3 else "***"
        masked_root = root_part[:3] + "***" if len(root_part) > 3 else "***"
        return f"{masked_local}@{masked_root}.{tld}"
    return _mask_generic(value)


def _mask_phone(value: str) -> str:
    """Show only last 2 digits, mask the rest. Keep separators-ish.

    +41 79 123 4501  ->  +** ** *** **01
    """
    # Keep last 2 visible digits if value has at least 4 digits
    digits = re.sub(r"\D", "", value)
    if len(digits) < 4:
        return _mask_generic(value)
    last2 = digits[-2:]
    # Roughly mimic original shape with stars
    masked = re.sub(r"\d", "*", value)
    # Replace last 2 stars back with the actual digits
    return masked[:-2] + last2 if masked.endswith("**") else masked + last2


def _mask_iban(value: str) -> str:
    """Keep country code + last 4. CH9300762011623852957 -> CH**...2957."""
    if len(value) < 8:
        return _mask_generic(value)
    return f"{value[:2]}{'*' * (len(value) - 6)}{value[-4:]}"


def _mask_generic(value: str) -> str:
    """Last-resort: show first char + length + last char."""
    if len(value) <= 4:
        return "***"
    return f"{value[0]}{'*' * (len(value) - 2)}{value[-1]}"


# ── Field-level redaction ───────────────────────────────────────────────────


def is_likely_pii_field(field_name: str) -> bool:
    """True when the field NAME suggests PII content.

    Defensive: catches values that don't match a regex (e.g. a phone
    written as "079.123.4567" missing the international prefix) just
    because the field is labelled "phone".
    """
    return field_name.lower() in _PII_FIELD_NAMES


def _redact_string(value: str) -> str:
    """Apply all redaction patterns to a string, in order of specificity.

    Order matters: IBAN regex must run before VAT regex (overlap).
    """
    if not isinstance(value, str) or not value:
        return value
    out = value
    # IBAN before VAT (overlap risk)
    out = _IBAN_RE.sub(lambda m: _mask_iban(m.group(0)), out)
    out = _VAT_RE.sub(lambda m: _mask_iban(m.group(0)), out)
    out = _CODICE_FISCALE_RE.sub(lambda m: _mask_iban(m.group(0)), out)
    out = _EMAIL_RE.sub(lambda m: _mask_email(m.group(0)), out)
    out = _PHONE_RE.sub(lambda m: _mask_phone(m.group(0)), out)
    return out


def redact_pii(obj: Any) -> Any:
    """Recursively redact PII from a dict / list / scalar.

    Returns a NEW object. Originals are never mutated.

    Strategy per node type:
        - dict:  redact values; PII-named fields use _mask_generic
                 on the whole value (last-resort), other fields run
                 _redact_string on string values.
        - list:  redact each element recursively.
        - str:   apply regex-based redaction (email/phone/IBAN/VAT/CF).
        - other: untouched.
    """
    if isinstance(obj, dict):
        out: dict = {}
        for k, v in obj.items():
            if is_likely_pii_field(str(k)) and isinstance(v, str):
                # PII field: aggressive mask regardless of value shape
                out[k] = _mask_generic(v)
            elif isinstance(v, str):
                out[k] = _redact_string(v)
            else:
                out[k] = redact_pii(v)
        return out
    if isinstance(obj, list):
        return [redact_pii(item) for item in obj]
    if isinstance(obj, str):
        return _redact_string(obj)
    return obj
