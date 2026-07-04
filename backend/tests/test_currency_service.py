"""Unit tests for ``backend/services/currency_service.py``.

Covers pure validators / resolvers and the async ``is_change_allowed_for_org``
helper using an in-memory mock for ``orders_collection``.
"""

import os
import sys
from pathlib import Path
from unittest.mock import AsyncMock, patch

BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-not-for-production")
os.environ.setdefault("MONGO_URL", "mongodb://localhost:27017")
os.environ.setdefault("DB_NAME", "test_db")

import pytest

from services.currency_service import (
    DEFAULT_CURRENCY,
    SUPPORTED_CURRENCIES,
    UnsupportedCurrencyError,
    get_currency_for_extra,
    get_currency_for_order,
    get_currency_for_org,
    get_currency_for_product,
    is_change_allowed_for_org,
    validate_currency_code,
)


# ── validate_currency_code ──────────────────────────────────────────────────


@pytest.mark.parametrize("code", ["EUR", "CHF", "eur", "chf", " EUR ", " chf "])
def test_validate_accepts_supported_codes(code):
    assert validate_currency_code(code) in SUPPORTED_CURRENCIES


@pytest.mark.parametrize("bad", [None, "", "USD", "GBP", "xx", "123"])
def test_validate_rejects_unsupported(bad):
    with pytest.raises(UnsupportedCurrencyError):
        validate_currency_code(bad)


def test_validate_returns_uppercase_normalised():
    assert validate_currency_code("chf") == "CHF"
    assert validate_currency_code(" eur ") == "EUR"


# ── get_currency_for_org ────────────────────────────────────────────────────


def test_get_currency_returns_default_when_missing():
    assert get_currency_for_org({}) == DEFAULT_CURRENCY


def test_get_currency_returns_default_when_none():
    assert get_currency_for_org({"currency": None}) == DEFAULT_CURRENCY


def test_get_currency_returns_default_when_empty_string():
    assert get_currency_for_org({"currency": ""}) == DEFAULT_CURRENCY


def test_get_currency_normalises_case_and_whitespace():
    assert get_currency_for_org({"currency": "chf"}) == "CHF"
    assert get_currency_for_org({"currency": " eur "}) == "EUR"


def test_get_currency_falls_back_on_unknown_value():
    """Read path must never crash; unknown codes resolve to default."""
    assert get_currency_for_org({"currency": "USD"}) == DEFAULT_CURRENCY


def test_get_currency_handles_non_mapping_input_gracefully():
    """Defensive: never crash if a caller passes the wrong type."""
    assert get_currency_for_org(None) == DEFAULT_CURRENCY  # type: ignore[arg-type]


# ── get_currency_for_order (priority chain) ─────────────────────────────────


def test_order_uses_order_currency_when_present():
    """Snapshot wins: order.currency is authoritative."""
    order = {"currency": "CHF"}
    org = {"currency": "EUR"}
    assert get_currency_for_order(order, org) == "CHF"


def test_order_falls_back_to_org_when_order_currency_missing():
    """Legacy order docs without currency: pull from org."""
    order = {"id": "ord_1"}  # no currency field
    org = {"currency": "CHF"}
    assert get_currency_for_order(order, org) == "CHF"


def test_order_falls_back_to_org_when_order_currency_unsupported():
    """Garbled snapshot value: ignore, fall through to org."""
    order = {"currency": "XYZ"}
    org = {"currency": "CHF"}
    assert get_currency_for_order(order, org) == "CHF"


def test_order_falls_back_to_default_when_no_org():
    order = {"id": "ord_1"}
    assert get_currency_for_order(order, None) == DEFAULT_CURRENCY


def test_order_handles_missing_order_doc_gracefully():
    """Defensive: never crash if a caller passes None for order."""
    assert get_currency_for_order(None, {"currency": "CHF"}) == "CHF"
    assert get_currency_for_order(None, None) == DEFAULT_CURRENCY


# ── get_currency_for_product (priority chain) ───────────────────────────────


def test_product_uses_product_currency_when_present():
    product = {"currency": "CHF"}
    org = {"currency": "EUR"}
    assert get_currency_for_product(product, org) == "CHF"


def test_product_falls_back_to_org():
    product = {"id": "prod_1"}
    org = {"currency": "CHF"}
    assert get_currency_for_product(product, org) == "CHF"


def test_product_falls_back_to_default_when_no_org():
    assert get_currency_for_product({}, None) == DEFAULT_CURRENCY


def test_product_handles_none_input():
    assert get_currency_for_product(None, {"currency": "CHF"}) == "CHF"
    assert get_currency_for_product(None, None) == DEFAULT_CURRENCY


# ── get_currency_for_extra (4-level priority) ───────────────────────────────


def test_extra_uses_extra_currency_first():
    extra = {"currency": "CHF"}
    product = {"currency": "EUR"}
    org = {"currency": "EUR"}
    assert get_currency_for_extra(extra, product, org) == "CHF"


def test_extra_falls_back_to_product():
    extra = {"id": "ext_1"}
    product = {"currency": "CHF"}
    org = {"currency": "EUR"}
    assert get_currency_for_extra(extra, product, org) == "CHF"


def test_extra_falls_back_to_org():
    extra = {}
    product = {}
    org = {"currency": "CHF"}
    assert get_currency_for_extra(extra, product, org) == "CHF"


def test_extra_falls_back_to_default():
    assert get_currency_for_extra({}, {}, {}) == DEFAULT_CURRENCY


def test_extra_handles_none_inputs():
    assert get_currency_for_extra(None, None, None) == DEFAULT_CURRENCY
    assert get_currency_for_extra(None, None, {"currency": "CHF"}) == "CHF"


# ── is_change_allowed_for_org (async) ───────────────────────────────────────


@pytest.mark.asyncio
async def test_change_allowed_when_no_orders_exist():
    fake_collection = AsyncMock()
    fake_collection.find_one = AsyncMock(return_value=None)
    # The function imports orders_collection lazily from `database` inside its
    # body, so we patch it at the source module.
    with patch("database.orders_collection", fake_collection):
        assert await is_change_allowed_for_org("org_no_orders") is True


@pytest.mark.asyncio
async def test_change_blocked_when_order_exists():
    fake_collection = AsyncMock()
    fake_collection.find_one = AsyncMock(return_value={"_id": "ord_1"})
    with patch("database.orders_collection", fake_collection):
        assert await is_change_allowed_for_org("org_with_orders") is False


@pytest.mark.asyncio
async def test_query_filters_by_organization_id():
    """Ensure we scope the existence check to the right org."""
    fake_collection = AsyncMock()
    fake_collection.find_one = AsyncMock(return_value=None)
    with patch("database.orders_collection", fake_collection):
        await is_change_allowed_for_org("org_xyz")
    fake_collection.find_one.assert_awaited_once()
    args, _ = fake_collection.find_one.call_args
    assert args[0] == {"organization_id": "org_xyz"}
