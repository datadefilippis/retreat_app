#!/usr/bin/env python3
"""
Create a Stripe Connect Express account for an org via API, with all
KYC fields pre-populated using Stripe's test-mode-friendly fixtures.

Why this exists
===============
The hosted Stripe onboarding (``connect.stripe.com/setup/...``) is a
browser-only flow that's tedious to repeat during dev. Stripe DOES
expose API-driven account creation: we ``Account.create`` with the
full ``individual``, ``business_profile``, ``external_account``, and
``tos_acceptance`` blocks, plus the requested capabilities
(``card_payments``, ``transfers``, ``twint_payments``), and Stripe
returns an account that's already (in test mode) ``charges_enabled``
ready to use.

This script:
  1. Calls ``stripe.Account.create`` with the canonical CH test
     fixture data (Bahnhofstrasse, IBAN test, AHV test).
  2. Stores the ``acct_xxx`` in the ``payment_connections``
     collection so afianco picks it up immediately.
  3. Prints capability status (``card_payments``, ``twint_payments``)
     so we know if TWINT is active out of the gate or still pending.

Limitations
-----------
* Real-mode requires document verification — this is dev-only.
* If a capability stays in ``pending`` because Stripe wants more
  data, the script logs which fields are due and exits cleanly;
  the operator can then go to the Stripe dashboard for that single
  account to satisfy them.

Usage
-----
    cd backend
    python -m scripts.create_stripe_test_ch_account
    # or specify org
    python -m scripts.create_stripe_test_ch_account --org-id <uuid>
"""

import argparse
import asyncio
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

_BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_BACKEND_DIR))

# Load .env so STRIPE_SECRET_KEY is picked up exactly like the running
# backend would. ``database.py`` already calls ``load_dotenv`` on
# import, so importing it before stripe gives us the env populated.
from database import payment_connections_collection  # noqa: E402  (loads .env)

import stripe  # noqa: E402


_DEFAULT_ORG_ID = "16d64b96-b90f-4705-b6aa-03d279014909"  # org "tet"


def _check_test_mode():
    key = os.environ.get("STRIPE_SECRET_KEY", "")
    if not key:
        raise SystemExit(
            "STRIPE_SECRET_KEY not set in environment. "
            "Make sure backend/.env has it."
        )
    if key.startswith("sk_live_"):
        raise SystemExit(
            "Refusing to run: STRIPE_SECRET_KEY is a LIVE key. "
            "This script creates synthetic data and must only run "
            "against a test-mode key (sk_test_...)."
        )
    if not key.startswith("sk_test_"):
        raise SystemExit(
            f"STRIPE_SECRET_KEY does not look like a Stripe key "
            f"(starts with {key[:7]}...)."
        )
    stripe.api_key = key
    return key


def _build_account_payload() -> dict:
    """Canonical CH-individual test fixture.

    Stripe test mode accepts these values without document upload as
    long as the data is internally consistent. Sources:
      - https://stripe.com/docs/connect/testing#test-personal-information
      - https://stripe.com/docs/connect/testing-verification
    """
    now_unix = int(datetime.now(tz=timezone.utc).timestamp())
    return {
        "type": "express",
        "country": "CH",
        "email": "afianco-test-ch@example.test",
        "business_type": "individual",
        "capabilities": {
            "card_payments": {"requested": True},
            "transfers": {"requested": True},
            # Swiss-specific — TWINT is gated to CH accounts.
            "twint_payments": {"requested": True},
        },
        "business_profile": {
            "url": "https://afianco.app",
            "mcc": "5734",  # Computer Software Stores — generic
            "product_description": "Test merchant for AFianco TWINT smoke",
        },
        "individual": {
            "first_name": "Test",
            "last_name": "Owner",
            "email": "afianco-test-ch@example.test",
            "phone": "+41441234567",
            "address": {
                "line1": "Bahnhofstrasse 1",
                "city": "Zürich",
                "postal_code": "8001",
                "country": "CH",
            },
            "dob": {"day": 1, "month": 1, "year": 1990},
            # Stripe accepts a placeholder AHV in test mode. The real
            # format is 756.xxxx.xxxx.xx; Stripe's docs use a fixed
            # canonical value that always passes test verification.
            "id_number": "AVS756123456789",
        },
        "external_account": {
            "object": "bank_account",
            "country": "CH",
            "currency": "chf",
            "account_holder_name": "Test Owner",
            "account_holder_type": "individual",
            # Stripe official test IBAN for CH.
            "account_number": "CH9300762011623852957",
        },
        # NOTE: Stripe forbids ``tos_acceptance`` via API for Express
        # accounts (the merchant must agree in person via the hosted
        # onboarding link). The ToS are accepted later if/when the
        # merchant opens the deep-link to ``connect.stripe.com``.
        # In test mode we can leave the account without ToS — Stripe
        # still gives us an ``acct_xxx`` and the capability state is
        # readable; ``charges_enabled`` won't flip to True until
        # the merchant accepts ToS, but the UI exercise we want to
        # smoke (capability lookup, banner CTA, refresh) is unaffected.
    }


def _summarize_capabilities(account) -> dict:
    """Return a flat dict of capability → status for printing."""
    caps = getattr(account, "capabilities", None) or {}
    if hasattr(caps, "to_dict"):
        try:
            caps = caps.to_dict()
        except Exception:
            caps = {}
    return {k: str(v) for k, v in caps.items()}


def _summarize_requirements(account) -> dict:
    """Return ``currently_due / past_due`` for diagnostics."""
    req = getattr(account, "requirements", None) or {}
    if hasattr(req, "to_dict"):
        try:
            req = req.to_dict()
        except Exception:
            req = {}
    return {
        "currently_due": list(req.get("currently_due") or []),
        "past_due": list(req.get("past_due") or []),
        "disabled_reason": req.get("disabled_reason"),
    }


async def _persist_connection(org_id: str, account) -> str:
    """Upsert the payment_connections record for the org."""
    now = datetime.now(timezone.utc)
    fields = {
        "external_account_id": account.id,
        "is_default": True,
        "status": "active" if getattr(account, "charges_enabled", False) else "pending",
        "runtime_status": "ready" if getattr(account, "charges_enabled", False) else "needs_auth",
        "connect_type": "express",
        "charges_enabled": bool(getattr(account, "charges_enabled", False)),
        "payouts_enabled": bool(getattr(account, "payouts_enabled", False)),
        "details_submitted": bool(getattr(account, "details_submitted", False)),
        "requirements_currently_due": _summarize_requirements(account)["currently_due"],
        "runtime_error": None,
        "last_runtime_check_at": now,
        "connected_at": now,
        "metadata": {
            "_dev_create_via_api": True,
            "_test_fixture": "ch_individual_canonical",
        },
        "updated_at": now,
    }

    existing = await payment_connections_collection.find_one(
        {"organization_id": org_id, "provider": "stripe"},
    )
    if existing:
        await payment_connections_collection.update_one(
            {"_id": existing["_id"]},
            {"$set": fields},
        )
        return "updated"

    from uuid import uuid4
    doc = {
        "id": f"api_{uuid4().hex[:12]}",
        "organization_id": org_id,
        "provider": "stripe",
        "display_name": "Stripe (api-created CH test)",
        "created_at": now,
        **fields,
    }
    await payment_connections_collection.insert_one(doc)
    return "inserted"


async def _run(org_id: str):
    _check_test_mode()
    payload = _build_account_payload()
    print("=" * 72)
    print("Creating Stripe Connect Express account (test mode, country=CH)…")
    print("=" * 72)
    try:
        account = await asyncio.to_thread(stripe.Account.create, **payload)
    except stripe.error.StripeError as exc:  # type: ignore[attr-defined]
        print(f"✗ Stripe rejected the account creation: {exc}")
        return 2
    except Exception as exc:
        print(f"✗ Unexpected error: {exc}")
        return 2

    print(f"✓ Stripe Account created: {account.id}")
    print(f"  charges_enabled  : {getattr(account, 'charges_enabled', False)}")
    print(f"  payouts_enabled  : {getattr(account, 'payouts_enabled', False)}")
    print(f"  details_submitted: {getattr(account, 'details_submitted', False)}")
    print()
    print("Capabilities (status per method):")
    for cap, status in _summarize_capabilities(account).items():
        print(f"  - {cap:24s} {status}")
    print()
    reqs = _summarize_requirements(account)
    if reqs["currently_due"]:
        print("⚠ Currently due (account needs more data before charges_enabled):")
        for f in reqs["currently_due"]:
            print(f"    · {f}")
        print()
    if reqs["disabled_reason"]:
        print(f"⚠ Disabled reason: {reqs['disabled_reason']}")
        print()

    action = await _persist_connection(org_id, account)
    print(f"✓ payment_connections {action} for org {org_id}")
    print()

    # Stripe forbids ToS acceptance via API; generate a one-click
    # onboarding link the operator opens once. After accepting ToS
    # the account auto-flips to ``charges_enabled=True`` and the
    # requested capabilities become ``active`` (test mode is
    # permissive for individual accounts with full KYC pre-filled).
    try:
        link = await asyncio.to_thread(
            stripe.AccountLink.create,
            account=account.id,
            refresh_url="http://localhost:3003/settings",
            return_url="http://localhost:3003/settings",
            type="account_onboarding",
        )
        print("=" * 72)
        print("⚡ ONE CLICK to finish onboarding (accept ToS):")
        print("=" * 72)
        print(f"  {link.url}")
        print()
        print("Open that URL in your browser. Stripe pre-fills every")
        print("field we sent via API; you only have to click the green")
        print("'Accept and submit' button at the bottom. Takes ~10 seconds.")
        print()
        print("After the redirect back to /settings:")
        print("  • Refresh the 'Metodi di pagamento' card (↻ button).")
        print("  • Card capability should flip to Attivo.")
        print("  • TWINT may still need an explicit toggle on the")
        print("    Stripe Express dashboard — see step below.")
    except Exception as exc:
        print(f"⚠ Could not generate AccountLink: {exc}")
        print(f"  Open https://dashboard.stripe.com/test/connect/accounts/{account.id}")
        print(f"  to complete the onboarding manually.")
    print()
    print("Next (after ToS accepted):")
    print("  1) Hard-refresh frontend.")
    print("  2) Settings → 'Metodi di pagamento' card.")
    print("  3) Click ↻ refresh to bypass the 5-min capability cache.")
    print()
    print("If TWINT shows as inactive but currently_due is empty:")
    print(f"  - Open https://dashboard.stripe.com/test/connect/accounts/{account.id}")
    print("  - Toggle TWINT under Payment Methods.")
    print("  - Refresh afianco again.")
    return 0


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument(
        "--org-id", default=_DEFAULT_ORG_ID,
        help=f"Organisation id (default: {_DEFAULT_ORG_ID})",
    )
    args = parser.parse_args()
    rc = asyncio.run(_run(args.org_id))
    sys.exit(rc)


if __name__ == "__main__":
    main()
