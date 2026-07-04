"""Tests for services.pii_redactor.

Wave 5.1 (2026-05). Pure functions, no DB / no I/O — fast.
"""
import pytest
from services.pii_redactor import (
    redact_pii,
    is_likely_pii_field,
    _mask_email,
    _mask_phone,
    _mask_iban,
)


# ── Email ───────────────────────────────────────────────────────────────────


def test_mask_email_basic():
    assert _mask_email("ordini@caffe-centrale.test") == "ord***@caf***.test"


def test_mask_email_short_local():
    masked = _mask_email("a@b.it")
    # No fully visible local part
    assert "@" in masked
    assert "a" not in masked.split("@")[0] or masked.startswith("***")


def test_mask_email_in_string():
    out = redact_pii("Contattare il cliente a marco.rossi@example.com")
    assert "marco.rossi" not in out
    # TLD preserved (last token after final dot), domain root masked
    assert out.endswith(".com")
    assert "@" in out


# ── Phone ───────────────────────────────────────────────────────────────────


def test_mask_phone_international():
    masked = _mask_phone("+41 79 123 4501")
    # Last 2 digits visible
    assert masked.endswith("01")
    # Not the original digits in the middle
    assert "79123" not in masked


def test_mask_phone_in_string():
    out = redact_pii("Telefono: +39 333 1234567")
    assert "1234567" not in out
    assert "67" in out  # last 2 visible


# ── IBAN ────────────────────────────────────────────────────────────────────


def test_mask_iban_swiss():
    masked = _mask_iban("CH9300762011623852957")
    assert masked.startswith("CH")
    assert masked.endswith("2957")
    assert "0076" not in masked


def test_mask_iban_in_string():
    out = redact_pii("Bonifico IBAN: IT60X0542811101000000123456")
    assert "0542811101" not in out
    assert "IT" in out  # prefix kept
    assert "3456" in out  # last 4 kept


# ── Field-level detection ──────────────────────────────────────────────────


def test_field_name_email_flagged():
    assert is_likely_pii_field("email")
    assert is_likely_pii_field("customer_email")
    assert is_likely_pii_field("EMAIL")  # case insensitive


def test_field_name_normal_not_flagged():
    assert not is_likely_pii_field("name")
    assert not is_likely_pii_field("customer_name")
    assert not is_likely_pii_field("total_revenue")


# ── Recursive redaction ─────────────────────────────────────────────────────


def test_redact_pii_in_dict():
    raw = {
        "customer_name": "Caffè Centrale Snc",       # KEEP (business id)
        "customer_email": "ordini@centrale.test",     # MASK
        "phone": "+41 79 123 4501",                   # MASK
        "iban": "CH9300762011623852957",              # MASK
        "total_revenue": 12345.67,                    # KEEP
        "currency": "CHF",                            # KEEP
    }
    out = redact_pii(raw)

    # Business name preserved
    assert out["customer_name"] == "Caffè Centrale Snc"
    # Personal email masked
    assert "ordini" not in out["customer_email"]
    # Phone masked
    assert "1234501" not in out["phone"]
    # IBAN masked
    assert "0762011623852957" not in out["iban"]
    # Numeric fields preserved
    assert out["total_revenue"] == 12345.67
    assert out["currency"] == "CHF"


def test_redact_pii_in_nested_list():
    raw = {
        "top_customers": [
            {"name": "Caffè Centrale", "email": "a@b.com"},
            {"name": "Hotel Splendid", "email": "info@hotel.test"},
        ],
    }
    out = redact_pii(raw)
    assert out["top_customers"][0]["name"] == "Caffè Centrale"
    assert "a@b.com" not in out["top_customers"][0]["email"]
    assert out["top_customers"][1]["name"] == "Hotel Splendid"


def test_redact_does_not_mutate_input():
    raw = {"email": "user@example.com"}
    out = redact_pii(raw)
    # Input unchanged
    assert raw["email"] == "user@example.com"
    # Output redacted
    assert out["email"] != "user@example.com"


def test_redact_none_safe():
    assert redact_pii(None) is None
    assert redact_pii({"x": None}) == {"x": None}


def test_redact_numeric_passthrough():
    assert redact_pii(42) == 42
    assert redact_pii(3.14) == 3.14
    assert redact_pii(True) is True


def test_redact_handles_string_within_text():
    """Realistic case: tool result has prose with embedded PII."""
    raw = {
        "description": "Inviare conferma a marco@rossi.it (tel: +39 333 1234567)",
    }
    out = redact_pii(raw)
    assert "marco" not in out["description"]
    # Phone last 2 digits visible
    assert "67" in out["description"]
