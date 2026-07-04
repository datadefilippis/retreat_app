"""Tests for TWINT capability handling in stripe_connect_express.py.

Scope (CH compliance v1 — Sub-stream 2.x close-out):

1. ``_create_express_account`` requests ``twint_payments`` alongside
   ``card_payments``/``transfers``. This is the merge-blocking fix —
   without it, every CH merchant onboarding through the production UI
   would silently get a Stripe account that cannot ever offer TWINT.

2. ``ensure_twint_capability_for_org`` covers the post-onboarding path
   (org switches currency to CHF after Stripe was already connected,
   or a legacy account predates the capability fix). Behaviour matrix:
     - no Stripe account                  → noop / no_account
     - account country != CH              → country_mismatch (no Stripe call)
     - account already has the capability → noop / already_requested
     - account is CH and unrequested      → calls Account.modify
     - Stripe API fails                   → status=error, never raises

The Stripe SDK is fully mocked — these tests must stay deterministic
and runnable without network/keys.
"""

import os
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-not-for-production")
os.environ.setdefault("MONGO_URL", "mongodb://localhost:27017")
os.environ.setdefault("DB_NAME", "test_db")
# is_express_configured() requires this. The string is never used —
# the SDK is mocked end-to-end.
os.environ.setdefault("STRIPE_SECRET_KEY", "sk_test_dummy_for_tests")

import pytest

from services import stripe_connect_express


# ── _create_express_account: TWINT must be requested at creation ──────────


@pytest.mark.asyncio
async def test_create_express_account_requests_twint_capability():
    """Regression guard for the Sub-stream 2.x merge-blocker fix.

    Before the fix, _create_express_account requested only card_payments
    and transfers. Every CH merchant going through the UI flow ended up
    with a Stripe account that couldn't offer TWINT — Stripe Connect
    Express has no merchant-facing toggle for capabilities, so once the
    account exists without the request, the only way to add it later is
    via Account.modify (which is what ensure_twint_capability_for_org
    does for the migration case).

    This test pins the capabilities dict to make sure a future refactor
    can't accidentally drop the twint_payments line.
    """
    fake_account = SimpleNamespace(id="acct_test_123")
    fake_stripe = MagicMock()
    fake_stripe.Account.create = MagicMock(return_value=fake_account)

    with patch.object(stripe_connect_express, "_get_stripe", return_value=fake_stripe):
        account_id = await stripe_connect_express._create_express_account(
            org_id="org_xyz", email="merchant@example.test",
        )

    assert account_id == "acct_test_123"
    fake_stripe.Account.create.assert_called_once()
    kwargs = fake_stripe.Account.create.call_args.kwargs
    caps = kwargs["capabilities"]
    assert caps == {
        "card_payments": {"requested": True},
        "transfers": {"requested": True},
        "twint_payments": {"requested": True},
    }, (
        "twint_payments must be requested at creation time. "
        "Removing it ships every CH merchant without TWINT."
    )
    # Also: type=express, metadata propagated, email passed through.
    assert kwargs["type"] == "express"
    assert kwargs["metadata"] == {"afianco_org_id": "org_xyz"}
    assert kwargs["email"] == "merchant@example.test"


@pytest.mark.asyncio
async def test_create_express_account_email_optional():
    """email is optional — kwarg must be omitted, not None, when absent."""
    fake_account = SimpleNamespace(id="acct_no_email")
    fake_stripe = MagicMock()
    fake_stripe.Account.create = MagicMock(return_value=fake_account)

    with patch.object(stripe_connect_express, "_get_stripe", return_value=fake_stripe):
        await stripe_connect_express._create_express_account(
            org_id="org_xyz", email=None,
        )

    kwargs = fake_stripe.Account.create.call_args.kwargs
    assert "email" not in kwargs, (
        "Stripe rejects email=None — caller must omit when absent."
    )


# ── ensure_twint_capability_for_org: the four paths ───────────────────────


@pytest.mark.asyncio
async def test_ensure_twint_noop_when_no_account():
    """No Stripe connection yet → noop, no Stripe call."""
    fake_collection = MagicMock()
    fake_collection.find_one = AsyncMock(return_value=None)

    with patch.object(stripe_connect_express, "_get_stripe") as get_stripe, \
         patch("database.payment_connections_collection", fake_collection):
        result = await stripe_connect_express.ensure_twint_capability_for_org("org_no_acct")

    assert result == {"status": "noop", "reason": "no_account"}
    get_stripe.assert_not_called()


@pytest.mark.asyncio
async def test_ensure_twint_country_mismatch_skips_stripe_modify():
    """Non-CH account → return country_mismatch, never call modify.

    A country change is impossible after Stripe account creation, so
    requesting the capability would be a no-op anyway. We surface the
    mismatch so the caller can render an actionable hint to the
    merchant ("your Stripe account is registered in IT — TWINT
    requires a Swiss account").
    """
    fake_collection = MagicMock()
    fake_collection.find_one = AsyncMock(return_value={
        "external_account_id": "acct_it_account",
    })
    italian_account = SimpleNamespace(
        country="IT",
        capabilities={"card_payments": "active"},
    )
    fake_stripe = MagicMock()
    fake_stripe.Account.retrieve = MagicMock(return_value=italian_account)
    fake_stripe.Account.modify = MagicMock()

    with patch.object(stripe_connect_express, "_get_stripe", return_value=fake_stripe), \
         patch("database.payment_connections_collection", fake_collection):
        result = await stripe_connect_express.ensure_twint_capability_for_org("org_it")

    assert result["status"] == "country_mismatch"
    assert result["country"] == "IT"
    assert result["account_id"] == "acct_it_account"
    fake_stripe.Account.modify.assert_not_called()


@pytest.mark.asyncio
async def test_ensure_twint_noop_when_already_requested():
    """If twint_payments is already in any state ≠ unrequested, skip the
    round-trip to Stripe (Account.modify would also be idempotent, but
    we save the call)."""
    fake_collection = MagicMock()
    fake_collection.find_one = AsyncMock(return_value={
        "external_account_id": "acct_ch_active",
    })
    ch_account = SimpleNamespace(
        country="CH",
        capabilities={
            "card_payments": "active",
            "transfers": "active",
            "twint_payments": "active",
        },
    )
    fake_stripe = MagicMock()
    fake_stripe.Account.retrieve = MagicMock(return_value=ch_account)
    fake_stripe.Account.modify = MagicMock()

    with patch.object(stripe_connect_express, "_get_stripe", return_value=fake_stripe), \
         patch("database.payment_connections_collection", fake_collection):
        result = await stripe_connect_express.ensure_twint_capability_for_org("org_ch_done")

    assert result["status"] == "noop"
    assert result["reason"] == "already_requested"
    assert result["capability"] == "active"
    fake_stripe.Account.modify.assert_not_called()


@pytest.mark.asyncio
async def test_ensure_twint_calls_modify_when_ch_and_unrequested():
    """Happy-path migration: CH account, capability missing → request it."""
    fake_collection = MagicMock()
    fake_collection.find_one = AsyncMock(return_value={
        "external_account_id": "acct_ch_legacy",
    })
    legacy_ch_account = SimpleNamespace(
        country="CH",
        capabilities={
            "card_payments": "active",
            "transfers": "active",
            # twint_payments key absent → treated as unrequested
        },
    )
    after_modify = SimpleNamespace(
        country="CH",
        capabilities={
            "card_payments": "active",
            "transfers": "active",
            "twint_payments": "pending",
        },
    )
    fake_stripe = MagicMock()
    fake_stripe.Account.retrieve = MagicMock(return_value=legacy_ch_account)
    fake_stripe.Account.modify = MagicMock(return_value=after_modify)

    with patch.object(stripe_connect_express, "_get_stripe", return_value=fake_stripe), \
         patch("database.payment_connections_collection", fake_collection):
        result = await stripe_connect_express.ensure_twint_capability_for_org("org_ch_legacy")

    assert result["status"] == "ok"
    assert result["capability"] == "pending"
    assert result["account_id"] == "acct_ch_legacy"
    fake_stripe.Account.modify.assert_called_once_with(
        "acct_ch_legacy",
        capabilities={"twint_payments": {"requested": True}},
    )


@pytest.mark.asyncio
async def test_ensure_twint_returns_error_on_stripe_retrieve_failure():
    """A Stripe API exception must be caught and returned as
    {status: error}. The caller (org-update endpoint) MUST NOT bubble
    this up — currency change should succeed even when this side-effect
    fails."""
    fake_collection = MagicMock()
    fake_collection.find_one = AsyncMock(return_value={
        "external_account_id": "acct_broken",
    })
    fake_stripe = MagicMock()
    fake_stripe.Account.retrieve = MagicMock(side_effect=RuntimeError("Stripe down"))

    with patch.object(stripe_connect_express, "_get_stripe", return_value=fake_stripe), \
         patch("database.payment_connections_collection", fake_collection):
        result = await stripe_connect_express.ensure_twint_capability_for_org("org_broken")

    assert result["status"] == "error"
    assert "Stripe down" in result["error"]
    assert result["account_id"] == "acct_broken"


@pytest.mark.asyncio
async def test_ensure_twint_returns_error_on_modify_failure_without_breaking():
    """retrieve succeeds but modify raises → graceful error.

    Important contract: this function NEVER raises. The caller (router)
    swallows even the dict-with-error case to keep currency save
    user-facing successful.
    """
    fake_collection = MagicMock()
    fake_collection.find_one = AsyncMock(return_value={
        "external_account_id": "acct_modify_breaks",
    })
    ch_account = SimpleNamespace(
        country="CH",
        capabilities={"card_payments": "active"},
    )
    fake_stripe = MagicMock()
    fake_stripe.Account.retrieve = MagicMock(return_value=ch_account)
    fake_stripe.Account.modify = MagicMock(
        side_effect=RuntimeError("rate_limit"),
    )

    with patch.object(stripe_connect_express, "_get_stripe", return_value=fake_stripe), \
         patch("database.payment_connections_collection", fake_collection):
        result = await stripe_connect_express.ensure_twint_capability_for_org("org_x")

    assert result["status"] == "error"
    assert "rate_limit" in result["error"]


@pytest.mark.asyncio
async def test_ensure_twint_handles_to_dict_capabilities():
    """stripe-python returns a typed StripeObject for capabilities;
    our helper calls .to_dict() when present. Cover that branch."""

    class FakeCaps:
        def to_dict(self):
            return {
                "card_payments": "active",
                "twint_payments": "active",
            }

    fake_collection = MagicMock()
    fake_collection.find_one = AsyncMock(return_value={
        "external_account_id": "acct_typed_caps",
    })
    typed_account = SimpleNamespace(
        country="CH",
        capabilities=FakeCaps(),
    )
    fake_stripe = MagicMock()
    fake_stripe.Account.retrieve = MagicMock(return_value=typed_account)
    fake_stripe.Account.modify = MagicMock()

    with patch.object(stripe_connect_express, "_get_stripe", return_value=fake_stripe), \
         patch("database.payment_connections_collection", fake_collection):
        result = await stripe_connect_express.ensure_twint_capability_for_org("org_typed")

    # twint already active → noop, modify never called.
    assert result["status"] == "noop"
    assert result["reason"] == "already_requested"
    assert result["capability"] == "active"
    fake_stripe.Account.modify.assert_not_called()
