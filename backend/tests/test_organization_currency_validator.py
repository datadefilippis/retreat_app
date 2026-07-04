"""Tests for the ``Organization.currency`` validator and its mirror on
``OrganizationUpdate``.

We only test the validator behaviour here. The runtime immutability
guardrail (which depends on a DB lookup) is exercised separately via
the integration test for the PUT endpoint.
"""

import os
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-not-for-production")
os.environ.setdefault("MONGO_URL", "mongodb://localhost:27017")
os.environ.setdefault("DB_NAME", "test_db")

import pytest
from pydantic import ValidationError

from models.organization import Organization
from routers.organizations import OrganizationUpdate


# ── Organization model validator ────────────────────────────────────────────


def _build_org(currency=...):
    """Helper: build an Organization with a minimum valid payload."""
    payload = {"name": "Test Org"}
    if currency is not ...:
        payload["currency"] = currency
    return Organization(**payload)


def test_organization_accepts_eur():
    org = _build_org(currency="EUR")
    assert org.currency == "EUR"


def test_organization_accepts_chf():
    org = _build_org(currency="CHF")
    assert org.currency == "CHF"


def test_organization_normalises_lowercase():
    """Validator should uppercase the input."""
    assert _build_org(currency="eur").currency == "EUR"
    assert _build_org(currency="chf").currency == "CHF"


def test_organization_strips_whitespace():
    assert _build_org(currency=" eur ").currency == "EUR"


def test_organization_accepts_none_for_legacy_docs():
    """Legacy organisations had ``currency=None``; must keep loading."""
    assert _build_org(currency=None).currency is None


def test_organization_accepts_missing_currency():
    """Field is optional; absent is fine."""
    assert _build_org().currency is None


def test_organization_accepts_empty_string_as_none():
    """Empty string is a common legacy value; treat as None."""
    assert _build_org(currency="").currency is None


@pytest.mark.parametrize("bad", ["USD", "GBP", "XYZ", "1234"])
def test_organization_rejects_unsupported_codes(bad):
    with pytest.raises(ValidationError):
        _build_org(currency=bad)


# ── OrganizationUpdate (router DTO) validator ───────────────────────────────


def test_update_dto_accepts_supported():
    dto = OrganizationUpdate(currency="CHF")
    assert dto.currency == "CHF"


def test_update_dto_normalises_case():
    dto = OrganizationUpdate(currency="chf")
    assert dto.currency == "CHF"


def test_update_dto_treats_empty_as_none():
    """Sending currency='' from a form should not be a validation error;
    it just means 'no change' (downstream excludes None on dump)."""
    dto = OrganizationUpdate(currency="")
    assert dto.currency is None


def test_update_dto_rejects_unsupported():
    with pytest.raises(ValidationError):
        OrganizationUpdate(currency="USD")


def test_update_dto_currency_optional():
    """All fields are optional; empty payload is valid."""
    dto = OrganizationUpdate()
    assert dto.currency is None


def test_update_dto_other_fields_unaffected():
    """Smoke check: validator addition didn't break sibling fields."""
    dto = OrganizationUpdate(name="New Name", timezone="Europe/Zurich")
    assert dto.name == "New Name"
    assert dto.timezone == "Europe/Zurich"
    assert dto.currency is None
