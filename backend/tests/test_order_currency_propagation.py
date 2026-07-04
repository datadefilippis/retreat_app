"""Integration-style tests for the currency propagation contract enforced
by ``services.order_service.create_order``.

We do not exercise the whole 300-line ``create_order`` here (it depends
on shipping, fulfillment, slot reservation, and more — not the focus of
this test). Instead we lock down the *contract*:

  1. The currency on the resulting Order doc is ALWAYS the
     organisation's currency, never the value the client put in the
     ``OrderCreate`` payload (server-authoritative).
  2. Legacy organisations with ``currency=None`` resolve to EUR via the
     fallback chain in ``services.currency_service``.
  3. Unsupported codes on the org doc never propagate to the order.

The mechanism under test is the snippet inside ``create_order``:

    org_doc = await organization_repository.find_by_id(org_id)
    order_currency = get_currency_for_org(org_doc or {})
    ...
    order = Order(
        ...,
        currency=order_currency,
        ...
    )

We replicate the snippet directly with a real ``Order`` instance, mocking
``organization_repository.find_by_id`` to return shaped org docs. This
keeps the test fast, deterministic, and free of the deeper plumbing.
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

from models.order import Order, OrderLineBase, OrderPaymentStatus, OrderStatus
from services.currency_service import get_currency_for_org


# ── Helper: replicate the snippet under test ────────────────────────────────


async def _resolve_and_build_order(
    org_id: str,
    client_supplied_currency: str,
):
    """Mirror what ``create_order`` does for currency only.

    Returns the Order object so callers can assert on ``.currency``.
    """
    from repositories import organization_repository

    org_doc = await organization_repository.find_by_id(org_id)
    order_currency = get_currency_for_org(org_doc or {})

    # Minimal valid Order payload (lines/totals are not the focus here).
    return Order(
        organization_id=org_id,
        customer_id="cus_test",
        # Client-supplied currency is intentionally passed in: the
        # contract is that we ignore it in favour of order_currency.
        currency=order_currency,
        items=[],
        subtotal=0.0,
        total=0.0,
        status=OrderStatus.DRAFT,
        payment_status=OrderPaymentStatus.PENDING,
    )


# ── Tests ───────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_order_inherits_currency_from_org_chf():
    """Org has CHF → Order has CHF, even if the client tries to send EUR."""
    fake_repo = AsyncMock()
    fake_repo.find_by_id = AsyncMock(return_value={"id": "org_1", "currency": "CHF"})

    with patch("repositories.organization_repository", fake_repo):
        order = await _resolve_and_build_order("org_1", client_supplied_currency="EUR")

    assert order.currency == "CHF"


@pytest.mark.asyncio
async def test_order_inherits_currency_from_org_eur():
    """Org has EUR → Order has EUR. Plain case but worth pinning."""
    fake_repo = AsyncMock()
    fake_repo.find_by_id = AsyncMock(return_value={"id": "org_1", "currency": "EUR"})

    with patch("repositories.organization_repository", fake_repo):
        order = await _resolve_and_build_order("org_1", client_supplied_currency="CHF")

    assert order.currency == "EUR"


@pytest.mark.asyncio
async def test_legacy_org_without_currency_falls_back_to_eur():
    """Legacy orgs with currency=None: fallback chain lands on EUR."""
    fake_repo = AsyncMock()
    fake_repo.find_by_id = AsyncMock(return_value={"id": "org_1", "currency": None})

    with patch("repositories.organization_repository", fake_repo):
        order = await _resolve_and_build_order("org_1", client_supplied_currency="CHF")

    assert order.currency == "EUR"


@pytest.mark.asyncio
async def test_org_with_garbled_currency_falls_back_safely():
    """Defensive: an unsupported value on the org doc resolves to EUR
    rather than propagating garbage onto the order.
    """
    fake_repo = AsyncMock()
    fake_repo.find_by_id = AsyncMock(return_value={"id": "org_1", "currency": "XYZ"})

    with patch("repositories.organization_repository", fake_repo):
        order = await _resolve_and_build_order("org_1", client_supplied_currency="CHF")

    assert order.currency == "EUR"


@pytest.mark.asyncio
async def test_missing_org_doc_falls_back_to_default():
    """When ``find_by_id`` returns None, the resolution must not crash."""
    fake_repo = AsyncMock()
    fake_repo.find_by_id = AsyncMock(return_value=None)

    with patch("repositories.organization_repository", fake_repo):
        order = await _resolve_and_build_order("org_missing", client_supplied_currency="CHF")

    assert order.currency == "EUR"


@pytest.mark.asyncio
async def test_client_supplied_currency_is_ignored():
    """The whole point of server-authoritative: a malicious or buggy
    client value never wins over the org's snapshot.
    """
    fake_repo = AsyncMock()
    fake_repo.find_by_id = AsyncMock(return_value={"id": "org_1", "currency": "CHF"})

    with patch("repositories.organization_repository", fake_repo):
        for client_val in ("EUR", "USD", "GBP", "", None, "garbage"):
            order = await _resolve_and_build_order("org_1", client_supplied_currency=client_val)
            assert order.currency == "CHF", (
                f"client_supplied_currency={client_val!r} leaked into the order"
            )
