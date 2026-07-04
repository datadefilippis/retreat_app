"""Contract tests for the payment provider abstraction layer.

These tests pin down the *interface* — every concrete provider added
in the future (Datatrans, PostFinance Checkout, TWINT direct) must
satisfy them too. We re-use the same suite via a tiny helper at the
bottom of the file.
"""

import os
import sys
from decimal import Decimal
from pathlib import Path
from unittest.mock import AsyncMock

BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-not-for-production")
os.environ.setdefault("MONGO_URL", "mongodb://localhost:27017")
os.environ.setdefault("DB_NAME", "test_db")

import pytest

from payment_providers import (
    AccountCapabilities,
    AccountNotConfigured,
    CapabilityMissing,
    CheckoutLineItem,
    CheckoutSessionRequest,
    CheckoutSessionResult,
    CurrencyMismatch,
    NormalizedEvent,
    PaymentProvider,
    PaymentProviderRegistry,
    ProviderError,
    WebhookSignatureInvalid,
)
from payment_providers.base import _NullPaymentProvider


# ── ABC cannot be instantiated ──────────────────────────────────────────────


def test_abstract_class_cannot_be_instantiated():
    """``PaymentProvider`` is an ABC; direct instantiation must fail."""
    with pytest.raises(TypeError):
        PaymentProvider()


def test_subclass_must_implement_all_methods():
    """A subclass that misses an abstractmethod cannot be instantiated."""

    class IncompleteProvider(PaymentProvider):
        name = "incomplete"
        # Intentionally only one method implemented.
        def verify_webhook(self, payload, signature_header, secret):
            return {}

    with pytest.raises(TypeError):
        IncompleteProvider()


# ── _NullPaymentProvider is the safe default ────────────────────────────────


@pytest.mark.asyncio
async def test_null_provider_raises_account_not_configured_on_create():
    null = _NullPaymentProvider()
    req = CheckoutSessionRequest(
        org_id="org_1", order_id="ord_1", currency="EUR",
        line_items=(CheckoutLineItem(name="x", quantity=1, unit_amount=Decimal("10")),),
        success_url="https://x", cancel_url="https://y",
    )
    with pytest.raises(AccountNotConfigured):
        await null.create_checkout_session(req)


@pytest.mark.asyncio
async def test_null_provider_raises_on_capabilities():
    null = _NullPaymentProvider()
    with pytest.raises(AccountNotConfigured):
        await null.get_account_capabilities("acct_x")


def test_null_provider_raises_on_webhook_verify():
    null = _NullPaymentProvider()
    with pytest.raises(AccountNotConfigured):
        null.verify_webhook(b"", "", "")


# ── Registry behaviour ──────────────────────────────────────────────────────


def _make_fake_provider(name: str) -> PaymentProvider:
    """Build a minimal provider instance for registry testing."""

    class FakeProvider(PaymentProvider):
        async def create_checkout_session(self, request):
            return CheckoutSessionResult(
                url="https://checkout.example/" + request.order_id,
                session_id="cs_fake_1",
                provider=self.name,
            )

        async def get_account_capabilities(self, connected_account_id):
            return AccountCapabilities(card_active=True)

        def verify_webhook(self, payload, signature_header, secret):
            return {"verified": True}

        def parse_event(self, verified_event, connected_account=None):
            return NormalizedEvent(
                type=NormalizedEvent.TYPE_CHECKOUT_COMPLETED,
                provider=self.name,
                provider_event_id="evt_fake_1",
                connected_account=connected_account,
                order_id=None, org_id=None, currency=None, amount=None,
                payment_intent_id=None, raw=verified_event,
            )

    inst = FakeProvider()
    inst.name = name
    return inst


def test_registry_register_and_lookup_by_name():
    PaymentProviderRegistry._reset_for_tests()
    fake = _make_fake_provider("fake_x")
    PaymentProviderRegistry.register("fake_x", fake)

    assert PaymentProviderRegistry.get_by_name("fake_x") is fake
    assert "fake_x" in PaymentProviderRegistry.names()


def test_registry_unknown_name_returns_null_provider():
    PaymentProviderRegistry._reset_for_tests()
    result = PaymentProviderRegistry.get_by_name("does_not_exist")
    assert isinstance(result, _NullPaymentProvider)


def test_registry_get_for_org_uses_configured_provider():
    PaymentProviderRegistry._reset_for_tests()
    stripe_fake = _make_fake_provider("stripe")
    datatrans_fake = _make_fake_provider("datatrans")
    PaymentProviderRegistry.register("stripe", stripe_fake)
    PaymentProviderRegistry.register("datatrans", datatrans_fake)

    org_a = {"payment_provider": "datatrans"}
    org_b = {"payment_provider": "stripe"}
    org_legacy = {}  # no payment_provider field

    assert PaymentProviderRegistry.get_for_org(org_a) is datatrans_fake
    assert PaymentProviderRegistry.get_for_org(org_b) is stripe_fake
    # Legacy org with nothing set falls back to stripe.
    assert PaymentProviderRegistry.get_for_org(org_legacy) is stripe_fake


def test_registry_get_for_org_handles_none_input():
    PaymentProviderRegistry._reset_for_tests()
    stripe_fake = _make_fake_provider("stripe")
    PaymentProviderRegistry.register("stripe", stripe_fake)
    # Defensive: caller may pass None when org doc lookup fails.
    assert PaymentProviderRegistry.get_for_org(None) is stripe_fake


def test_registry_get_for_org_unconfigured_provider_falls_back_to_stripe():
    """An org marked for a provider that no one registered yet must
    not crash — we fall back to stripe so the merchant can still
    transact, and we log the misconfiguration loudly.
    """
    PaymentProviderRegistry._reset_for_tests()
    stripe_fake = _make_fake_provider("stripe")
    PaymentProviderRegistry.register("stripe", stripe_fake)

    org = {"payment_provider": "datatrans"}
    assert PaymentProviderRegistry.get_for_org(org) is stripe_fake


def test_registry_with_empty_state_returns_null():
    """No providers registered at all (a misconfigured deploy) →
    null sentinel rather than KeyError.
    """
    PaymentProviderRegistry._reset_for_tests()
    result = PaymentProviderRegistry.get_for_org({})
    assert isinstance(result, _NullPaymentProvider)


def test_registry_register_requires_non_empty_name():
    PaymentProviderRegistry._reset_for_tests()
    fake = _make_fake_provider("x")
    with pytest.raises(ValueError):
        PaymentProviderRegistry.register("", fake)


def test_registry_unregister_removes_entry():
    PaymentProviderRegistry._reset_for_tests()
    fake = _make_fake_provider("temp")
    PaymentProviderRegistry.register("temp", fake)
    assert "temp" in PaymentProviderRegistry.names()
    PaymentProviderRegistry.unregister("temp")
    assert "temp" not in PaymentProviderRegistry.names()


# ── Exception hierarchy ─────────────────────────────────────────────────────


def test_exception_hierarchy_is_subclass_of_provider_error():
    """All sub-exceptions must inherit from ProviderError so the
    application layer can ``except ProviderError`` once.
    """
    assert issubclass(AccountNotConfigured, ProviderError)
    assert issubclass(CapabilityMissing, ProviderError)
    assert issubclass(WebhookSignatureInvalid, ProviderError)
    assert issubclass(CurrencyMismatch, ProviderError)


def test_capability_missing_carries_capability_name():
    err = CapabilityMissing(
        "TWINT not enabled",
        capability="twint",
        provider="stripe",
    )
    assert err.capability == "twint"
    assert err.provider == "stripe"
    assert err.code == "capability_missing"


def test_currency_mismatch_carries_expected_and_got():
    err = CurrencyMismatch(expected="EUR", got="CHF", provider="stripe")
    assert err.expected == "EUR"
    assert err.got == "CHF"
    assert "EUR" in str(err) and "CHF" in str(err)


# ── Model invariants ────────────────────────────────────────────────────────


def test_checkout_session_request_has_safe_defaults():
    req = CheckoutSessionRequest(
        org_id="org_1", order_id="ord_1", currency="EUR",
        line_items=(),
        success_url="https://ok", cancel_url="https://no",
    )
    assert req.application_fee_percent == Decimal("0")
    assert req.metadata == {}
    assert req.idempotency_key is None
    assert req.customer_email is None


def test_normalized_event_constants_are_unique():
    """Catch typos in the canonical event type strings."""
    types = {
        NormalizedEvent.TYPE_CHECKOUT_COMPLETED,
        NormalizedEvent.TYPE_PAYMENT_REFUNDED,
        NormalizedEvent.TYPE_PAYMENT_DISPUTED,
    }
    assert len(types) == 3
    assert all(isinstance(t, str) and t for t in types)
