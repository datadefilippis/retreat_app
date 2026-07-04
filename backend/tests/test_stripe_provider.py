"""Tests for ``payment_providers/stripe/`` — the concrete Stripe
implementation of :class:`PaymentProvider`.

We mock the Stripe SDK throughout so the suite stays fast and
deterministic. The pure helpers in ``method_types.py`` and
``webhook.py`` are tested directly; the higher-level provider is
tested via the registry path with the SDK injected.
"""

import os
import sys
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-not-for-production")
os.environ.setdefault("MONGO_URL", "mongodb://localhost:27017")
os.environ.setdefault("DB_NAME", "test_db")

import pytest

from payment_providers import (
    AccountCapabilities,
    CheckoutLineItem,
    CheckoutSessionRequest,
    NormalizedEvent,
    PaymentProviderRegistry,
    WebhookSignatureInvalid,
)
from payment_providers.stripe.capabilities import (
    _stripe_caps_to_model,
    fetch_account_capabilities,
)
from payment_providers.stripe.method_types import (
    is_swiss_method,
    resolve_payment_method_types,
)
from payment_providers.stripe.webhook import (
    parse_stripe_event,
    verify_stripe_webhook,
)


# ── method_types.py ─────────────────────────────────────────────────────────


def test_resolve_methods_eur_is_card_only():
    caps = AccountCapabilities(card_active=True, twint_active=True)
    assert resolve_payment_method_types("EUR", caps) == ("card",)


def test_resolve_methods_chf_with_twint_capability():
    caps = AccountCapabilities(card_active=True, twint_active=True)
    assert resolve_payment_method_types("CHF", caps) == ("card", "twint")


def test_resolve_methods_chf_without_twint_capability_falls_back_to_card():
    """The merchant has not enabled TWINT on Stripe yet — checkout must
    still work with cards. The UI is responsible for prompting the merchant
    to activate TWINT; the provider does NOT raise.
    """
    caps = AccountCapabilities(card_active=True, twint_active=False)
    assert resolve_payment_method_types("CHF", caps) == ("card",)


def test_resolve_methods_unknown_currency_defaults_to_card():
    caps = AccountCapabilities(card_active=True)
    assert resolve_payment_method_types("USD", caps) == ("card",)


def test_resolve_methods_case_insensitive_currency():
    caps = AccountCapabilities(twint_active=True)
    assert resolve_payment_method_types("chf", caps) == ("card", "twint")


def test_is_swiss_method_recognises_twint():
    assert is_swiss_method("twint") is True
    assert is_swiss_method("card") is False


# ── capabilities.py ─────────────────────────────────────────────────────────


def test_caps_to_model_translates_active_strings():
    raw = {
        "card_payments": "active",
        "twint_payments": "active",
        "sepa_debit_payments": "inactive",
        "transfers": "active",
    }
    caps = _stripe_caps_to_model(raw)
    assert caps.card_active is True
    assert caps.twint_active is True
    assert caps.sepa_debit_active is False
    assert caps.other == {"transfers": "active"}


def test_caps_to_model_handles_missing_dict():
    caps = _stripe_caps_to_model(None)
    assert caps.card_active is False
    assert caps.twint_active is False


def test_caps_to_model_treats_non_active_as_disabled():
    """``pending`` and ``inactive`` both count as not-enabled."""
    raw = {"card_payments": "pending", "twint_payments": "inactive"}
    caps = _stripe_caps_to_model(raw)
    assert caps.card_active is False
    assert caps.twint_active is False


@pytest.mark.asyncio
async def test_fetch_account_capabilities_calls_stripe():
    fake_stripe = MagicMock()
    fake_stripe.Account.retrieve = MagicMock(return_value={
        "capabilities": {"card_payments": "active", "twint_payments": "active"},
    })
    caps = await fetch_account_capabilities("acct_test", stripe_module=fake_stripe)
    assert caps.card_active is True
    assert caps.twint_active is True
    fake_stripe.Account.retrieve.assert_called_once_with("acct_test")


@pytest.mark.asyncio
async def test_fetch_account_capabilities_missing_account_raises():
    from payment_providers.exceptions import AccountNotConfigured
    fake_stripe = MagicMock()
    with pytest.raises(AccountNotConfigured):
        await fetch_account_capabilities("", stripe_module=fake_stripe)


@pytest.mark.asyncio
async def test_fetch_account_capabilities_wraps_sdk_errors():
    from payment_providers.exceptions import ProviderError
    fake_stripe = MagicMock()
    fake_stripe.Account.retrieve = MagicMock(side_effect=RuntimeError("api down"))
    with pytest.raises(ProviderError):
        await fetch_account_capabilities("acct_test", stripe_module=fake_stripe)


# ── webhook.py ──────────────────────────────────────────────────────────────


def test_verify_webhook_empty_secret_raises():
    fake_stripe = MagicMock()
    with pytest.raises(WebhookSignatureInvalid):
        verify_stripe_webhook(b"{}", "sig=x", "", stripe_module=fake_stripe)


def test_verify_webhook_passes_payload_to_sdk():
    fake_stripe = MagicMock()
    fake_stripe.Webhook.construct_event = MagicMock(return_value={"id": "evt_1"})
    out = verify_stripe_webhook(
        b'{"k":1}', "sig=ok", "whsec_test", stripe_module=fake_stripe,
    )
    assert out == {"id": "evt_1"}
    fake_stripe.Webhook.construct_event.assert_called_once_with(
        b'{"k":1}', "sig=ok", "whsec_test",
    )


def test_verify_webhook_wraps_sdk_errors():
    fake_stripe = MagicMock()
    fake_stripe.Webhook.construct_event = MagicMock(
        side_effect=RuntimeError("bad sig"),
    )
    with pytest.raises(WebhookSignatureInvalid):
        verify_stripe_webhook(b"{}", "sig=x", "whsec", stripe_module=fake_stripe)


def test_parse_event_checkout_completed():
    event = {
        "id": "evt_1",
        "type": "checkout.session.completed",
        "account": "acct_test",
        "data": {"object": {
            "id": "cs_1",
            "currency": "chf",
            "amount_total": 4950,
            "payment_intent": "pi_1",
            "metadata": {"order_id": "ord_1", "org_id": "org_1"},
        }},
    }
    n = parse_stripe_event(event)
    assert n.type == NormalizedEvent.TYPE_CHECKOUT_COMPLETED
    assert n.provider == "stripe"
    assert n.provider_event_id == "evt_1"
    assert n.connected_account == "acct_test"
    assert n.order_id == "ord_1"
    assert n.org_id == "org_1"
    assert n.currency == "CHF"
    assert n.amount == Decimal("49.50")
    assert n.payment_intent_id == "pi_1"


def test_parse_event_charge_refunded():
    event = {
        "id": "evt_2",
        "type": "charge.refunded",
        "data": {"object": {
            "currency": "eur",
            "amount_refunded": 1000,
            "payment_intent": "pi_2",
        }},
    }
    n = parse_stripe_event(event)
    assert n.type == NormalizedEvent.TYPE_PAYMENT_REFUNDED
    assert n.currency == "EUR"
    assert n.amount == Decimal("10.00")


def test_parse_event_charge_disputed():
    event = {
        "id": "evt_3",
        "type": "charge.dispute.created",
        "data": {"object": {
            "currency": "chf",
            "amount": 2000,
            "payment_intent": "pi_3",
        }},
    }
    n = parse_stripe_event(event)
    assert n.type == NormalizedEvent.TYPE_PAYMENT_DISPUTED
    assert n.currency == "CHF"
    assert n.amount == Decimal("20.00")


def test_parse_event_unknown_type_returns_empty_canonical_type():
    event = {"id": "evt_x", "type": "customer.created", "data": {"object": {}}}
    n = parse_stripe_event(event)
    assert n.type == ""
    assert n.provider == "stripe"
    assert n.provider_event_id == "evt_x"


def test_parse_event_handles_malformed_payload_defensively():
    n = parse_stripe_event(None)
    assert n.type == ""
    assert n.provider == "stripe"


# ── Provider via registry ───────────────────────────────────────────────────


def _ensure_stripe_registered():
    """Restore the auto-registration if a previous test wiped the registry.

    Some contract tests in ``test_payment_provider_interface.py`` call
    ``PaymentProviderRegistry._reset_for_tests()`` to start from a
    blank slate. That's correct for those tests, but it also clears
    the side-effect of importing ``payment_providers.stripe``. Pytest
    test ordering is not guaranteed, so this helper makes the stripe
    tests robust regardless of who ran first.
    """
    if "stripe" not in PaymentProviderRegistry.names():
        import importlib
        import payment_providers.stripe as _stripe_pkg
        importlib.reload(_stripe_pkg)


def test_stripe_provider_auto_registered():
    """Importing ``payment_providers`` triggers stripe sub-package
    import which self-registers ``StripeProvider`` under "stripe".
    """
    _ensure_stripe_registered()
    assert "stripe" in PaymentProviderRegistry.names()


def test_get_for_org_returns_stripe_by_default():
    _ensure_stripe_registered()
    provider = PaymentProviderRegistry.get_for_org({})
    assert provider.name == "stripe"


# ── End-to-end checkout creation (mocked SDK) ───────────────────────────────


@pytest.mark.asyncio
async def test_create_checkout_session_eur_card_only():
    """An EUR order must produce ``payment_method_types=["card"]`` and
    skip the capability lookup entirely.
    """
    from payment_providers.stripe.provider import StripeProvider

    fake_session = SimpleNamespace(
        id="cs_test_1",
        url="https://checkout.example/cs_test_1",
    )
    fake_stripe = MagicMock()
    fake_stripe.checkout.Session.create = MagicMock(return_value=fake_session)

    with patch(
        "payment_providers.stripe.provider._get_stripe",
        return_value=fake_stripe,
    ):
        provider = StripeProvider()
        req = CheckoutSessionRequest(
            org_id="org_1",
            order_id="ord_1",
            currency="EUR",
            line_items=(
                CheckoutLineItem(name="Test", quantity=1, unit_amount=Decimal("10.00")),
            ),
            success_url="https://x/ok",
            cancel_url="https://x/ko",
            metadata={"connected_account_id": "acct_test"},
        )
        result = await provider.create_checkout_session(req)

    assert result.url == "https://checkout.example/cs_test_1"
    assert result.session_id == "cs_test_1"
    assert result.provider == "stripe"
    assert result.payment_method_types == ("card",)

    call_kwargs = fake_stripe.checkout.Session.create.call_args.kwargs
    assert call_kwargs["payment_method_types"] == ["card"]
    assert call_kwargs["stripe_account"] == "acct_test"
    # connected_account_id stripped from outgoing metadata
    assert "connected_account_id" not in call_kwargs["metadata"]


@pytest.mark.asyncio
async def test_create_checkout_session_chf_with_twint_active():
    """A CHF order on an account with TWINT capability ON must emit
    ``payment_method_types=["card", "twint"]``.
    """
    from payment_providers.stripe.provider import StripeProvider

    fake_session = SimpleNamespace(id="cs_2", url="https://x/cs_2")
    fake_stripe = MagicMock()
    fake_stripe.checkout.Session.create = MagicMock(return_value=fake_session)
    fake_stripe.Account.retrieve = MagicMock(return_value={
        "capabilities": {"card_payments": "active", "twint_payments": "active"},
    })

    with patch(
        "payment_providers.stripe.provider._get_stripe",
        return_value=fake_stripe,
    ):
        provider = StripeProvider()
        req = CheckoutSessionRequest(
            org_id="org_ch", order_id="ord_ch", currency="CHF",
            line_items=(CheckoutLineItem(name="x", quantity=1, unit_amount=Decimal("50")),),
            success_url="https://x", cancel_url="https://y",
            metadata={"connected_account_id": "acct_ch"},
        )
        result = await provider.create_checkout_session(req)

    assert result.payment_method_types == ("card", "twint")
    call_kwargs = fake_stripe.checkout.Session.create.call_args.kwargs
    assert call_kwargs["payment_method_types"] == ["card", "twint"]


@pytest.mark.asyncio
async def test_create_checkout_session_chf_no_twint_falls_back_to_card():
    """Merchant hasn't enabled TWINT yet — checkout must still succeed
    with cards (UI then prompts them to enable TWINT).
    """
    from payment_providers.stripe.provider import StripeProvider

    fake_session = SimpleNamespace(id="cs_3", url="https://x/cs_3")
    fake_stripe = MagicMock()
    fake_stripe.checkout.Session.create = MagicMock(return_value=fake_session)
    fake_stripe.Account.retrieve = MagicMock(return_value={
        "capabilities": {"card_payments": "active", "twint_payments": "inactive"},
    })

    with patch(
        "payment_providers.stripe.provider._get_stripe",
        return_value=fake_stripe,
    ):
        provider = StripeProvider()
        req = CheckoutSessionRequest(
            org_id="org_ch2", order_id="ord_ch2", currency="CHF",
            line_items=(CheckoutLineItem(name="x", quantity=1, unit_amount=Decimal("50")),),
            success_url="https://x", cancel_url="https://y",
            metadata={"connected_account_id": "acct_ch2"},
        )
        result = await provider.create_checkout_session(req)

    assert result.payment_method_types == ("card",)


@pytest.mark.asyncio
async def test_create_checkout_session_idempotency_key_forwarded():
    from payment_providers.stripe.provider import StripeProvider

    fake_stripe = MagicMock()
    fake_stripe.checkout.Session.create = MagicMock(
        return_value=SimpleNamespace(id="cs_4", url="https://x/cs_4"),
    )

    with patch(
        "payment_providers.stripe.provider._get_stripe",
        return_value=fake_stripe,
    ):
        provider = StripeProvider()
        req = CheckoutSessionRequest(
            org_id="org_1", order_id="ord_idem", currency="EUR",
            line_items=(CheckoutLineItem(name="x", quantity=1, unit_amount=Decimal("5")),),
            success_url="https://x", cancel_url="https://y",
            metadata={"connected_account_id": "acct_test"},
            idempotency_key="ord_idem:1",
        )
        await provider.create_checkout_session(req)

    call_kwargs = fake_stripe.checkout.Session.create.call_args.kwargs
    assert call_kwargs.get("idempotency_key") == "ord_idem:1"


@pytest.mark.asyncio
async def test_create_checkout_session_application_fee_zero_omits_field():
    """fee_percent=0 must NOT pass ``application_fee_amount`` to Stripe."""
    from payment_providers.stripe.provider import StripeProvider

    fake_stripe = MagicMock()
    fake_stripe.checkout.Session.create = MagicMock(
        return_value=SimpleNamespace(id="cs_5", url="https://x/cs_5"),
    )

    with patch(
        "payment_providers.stripe.provider._get_stripe",
        return_value=fake_stripe,
    ):
        provider = StripeProvider()
        req = CheckoutSessionRequest(
            org_id="org_1", order_id="ord_1", currency="EUR",
            line_items=(CheckoutLineItem(name="x", quantity=1, unit_amount=Decimal("100")),),
            success_url="https://x", cancel_url="https://y",
            metadata={"connected_account_id": "acct_test"},
            application_fee_percent=Decimal("0"),
        )
        await provider.create_checkout_session(req)

    call_kwargs = fake_stripe.checkout.Session.create.call_args.kwargs
    assert "application_fee_amount" not in call_kwargs
    assert "application_fee_amount" not in (call_kwargs.get("payment_intent_data") or {})


@pytest.mark.asyncio
async def test_create_checkout_session_application_fee_calculated():
    from payment_providers.stripe.provider import StripeProvider

    fake_stripe = MagicMock()
    fake_stripe.checkout.Session.create = MagicMock(
        return_value=SimpleNamespace(id="cs_6", url="https://x/cs_6"),
    )

    with patch(
        "payment_providers.stripe.provider._get_stripe",
        return_value=fake_stripe,
    ):
        provider = StripeProvider()
        req = CheckoutSessionRequest(
            org_id="org_1", order_id="ord_1", currency="EUR",
            line_items=(CheckoutLineItem(name="x", quantity=1, unit_amount=Decimal("100")),),
            success_url="https://x", cancel_url="https://y",
            metadata={"connected_account_id": "acct_test"},
            application_fee_percent=Decimal("2.5"),
        )
        await provider.create_checkout_session(req)

    call_kwargs = fake_stripe.checkout.Session.create.call_args.kwargs
    # 100 EUR → 10000 cents. 2.5% fee → 250 cents.
    # Fix retreat 4/7/2026: per le Checkout Session la fee vive in
    # payment_intent_data (top-level Stripe la rifiuta: "unknown parameter",
    # verificato live in test mode — il vecchio assert codificava il bug).
    assert "application_fee_amount" not in call_kwargs
    assert call_kwargs.get("payment_intent_data", {}).get("application_fee_amount") == 250


@pytest.mark.asyncio
async def test_create_checkout_session_missing_connected_account_raises():
    from payment_providers.exceptions import AccountNotConfigured
    from payment_providers.stripe.provider import StripeProvider

    fake_stripe = MagicMock()
    with patch(
        "payment_providers.stripe.provider._get_stripe",
        return_value=fake_stripe,
    ):
        provider = StripeProvider()
        req = CheckoutSessionRequest(
            org_id="org_1", order_id="ord_1", currency="EUR",
            line_items=(CheckoutLineItem(name="x", quantity=1, unit_amount=Decimal("5")),),
            success_url="https://x", cancel_url="https://y",
            metadata={},  # no connected_account_id
        )
        with pytest.raises(AccountNotConfigured):
            await provider.create_checkout_session(req)
