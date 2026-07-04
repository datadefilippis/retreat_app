#!/usr/bin/env python3
"""
Read-only diagnostic that compares the afianco DB state with Stripe's
own view of the connected account. Run between manual onboarding
steps to confirm what changed and detect drift.

Reads ONLY. Never writes to Mongo or Stripe. Safe to run any time
during the live-validation flow described in the Sub-stream 2 manual
TWINT checklist.

Usage
-----
    cd backend
    python -m scripts.verify_stripe_onboarding_state            # default org "tet"
    python -m scripts.verify_stripe_onboarding_state --org-id <uuid>
    python -m scripts.verify_stripe_onboarding_state --org-id <uuid> --json
"""

import argparse
import asyncio
import json
import os
import sys
from pathlib import Path

_BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_BACKEND_DIR))

# Loads .env via database.py side effect.
from database import payment_connections_collection  # noqa: E402

import stripe  # noqa: E402


_DEFAULT_ORG_ID = "16d64b96-b90f-4705-b6aa-03d279014909"  # org "tet"


def _check_test_mode():
    key = os.environ.get("STRIPE_SECRET_KEY", "")
    if not key:
        raise SystemExit("STRIPE_SECRET_KEY not set in backend/.env")
    if key.startswith("sk_live_"):
        raise SystemExit(
            "Refusing to run: STRIPE_SECRET_KEY is a LIVE key. "
            "Diagnostic must only run against a test-mode key.",
        )
    stripe.api_key = key


def _to_dict(obj):
    """Coerce Stripe SDK objects to a plain dict."""
    if obj is None:
        return None
    if isinstance(obj, dict):
        return obj
    if hasattr(obj, "to_dict"):
        try:
            return obj.to_dict()
        except Exception:
            pass
    return obj


def _short_caps(account) -> dict:
    caps = _to_dict(getattr(account, "capabilities", None)) or {}
    return {k: str(v) for k, v in caps.items()}


def _short_reqs(account) -> dict:
    req = _to_dict(getattr(account, "requirements", None)) or {}
    return {
        "currently_due": list(req.get("currently_due") or []),
        "past_due": list(req.get("past_due") or []),
        "eventually_due": list(req.get("eventually_due") or []),
        "disabled_reason": req.get("disabled_reason"),
    }


async def _diagnose(org_id: str, as_json: bool):
    _check_test_mode()

    # 1. afianco DB view of the connection
    conn = await payment_connections_collection.find_one(
        {"organization_id": org_id, "provider": "stripe"},
        {"_id": 0},
    )
    db_view = {
        "found_in_db": bool(conn),
        "external_account_id": (conn or {}).get("external_account_id"),
        "status": (conn or {}).get("status"),
        "runtime_status": (conn or {}).get("runtime_status"),
        "is_default": (conn or {}).get("is_default"),
        "charges_enabled_db": (conn or {}).get("charges_enabled"),
        "details_submitted_db": (conn or {}).get("details_submitted"),
        "requirements_currently_due_db": (conn or {}).get("requirements_currently_due"),
        "metadata": (conn or {}).get("metadata"),
    }

    # 2. Stripe's authoritative view (read-only Account.retrieve)
    stripe_view = None
    if db_view["external_account_id"]:
        try:
            account = await asyncio.to_thread(
                stripe.Account.retrieve, db_view["external_account_id"],
            )
            stripe_view = {
                "id": account.id,
                "country": getattr(account, "country", None),
                "type": getattr(account, "type", None),
                "charges_enabled": bool(getattr(account, "charges_enabled", False)),
                "payouts_enabled": bool(getattr(account, "payouts_enabled", False)),
                "details_submitted": bool(getattr(account, "details_submitted", False)),
                "capabilities": _short_caps(account),
                "requirements": _short_reqs(account),
            }
        except Exception as exc:
            stripe_view = {"error": str(exc)}

    # 3. Drift check
    drift = []
    if stripe_view and "error" not in stripe_view:
        if db_view.get("charges_enabled_db") != stripe_view["charges_enabled"]:
            drift.append(
                f"charges_enabled: DB={db_view.get('charges_enabled_db')} vs Stripe={stripe_view['charges_enabled']}"
            )
        if db_view.get("details_submitted_db") != stripe_view["details_submitted"]:
            drift.append(
                f"details_submitted: DB={db_view.get('details_submitted_db')} vs Stripe={stripe_view['details_submitted']}"
            )

    payload = {
        "org_id": org_id,
        "db": db_view,
        "stripe": stripe_view,
        "drift": drift,
        "ready_for_checkout": bool(
            stripe_view
            and "error" not in (stripe_view or {})
            and stripe_view.get("charges_enabled")
            and stripe_view.get("capabilities", {}).get("card_payments") == "active"
        ),
        "twint_active_on_stripe": bool(
            stripe_view
            and "error" not in (stripe_view or {})
            and stripe_view.get("capabilities", {}).get("twint_payments") == "active"
        ),
    }

    if as_json:
        print(json.dumps(payload, indent=2, default=str))
        return 0

    # Pretty print
    print("=" * 72)
    print(f"Stripe onboarding diagnostic — org {org_id}")
    print("=" * 72)
    print()
    print("─ afianco DB view ─" + "─" * 53)
    if not db_view["found_in_db"]:
        print("  No payment_connection record. Run create_stripe_test_ch_account.")
    else:
        for k, v in db_view.items():
            print(f"  {k:34s} {v}")
    print()
    print("─ Stripe API view (authoritative) ─" + "─" * 36)
    if stripe_view is None:
        print("  Skipped (no external_account_id in DB).")
    elif "error" in stripe_view:
        print(f"  ✗ Stripe API error: {stripe_view['error']}")
    else:
        for k, v in stripe_view.items():
            if isinstance(v, dict):
                print(f"  {k}:")
                for kk, vv in v.items():
                    print(f"    {kk:30s} {vv}")
            else:
                print(f"  {k:34s} {v}")
    print()
    print("─ Drift check ─" + "─" * 56)
    if drift:
        for d in drift:
            print(f"  ⚠ {d}")
    else:
        print("  ✓ DB and Stripe agree.")
    print()
    print("─ Verdict ─" + "─" * 60)
    print(f"  ready_for_checkout      : {payload['ready_for_checkout']}")
    print(f"  twint_active_on_stripe  : {payload['twint_active_on_stripe']}")
    print()
    if not payload["ready_for_checkout"] and stripe_view and "error" not in stripe_view:
        cur = stripe_view.get("requirements", {}).get("currently_due") or []
        if cur:
            print("  Stripe still wants:")
            for f in cur:
                print(f"    · {f}")
    return 0


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--org-id", default=_DEFAULT_ORG_ID,
                        help=f"Organisation id (default: {_DEFAULT_ORG_ID})")
    parser.add_argument("--json", action="store_true",
                        help="Emit machine-readable JSON instead of text")
    args = parser.parse_args()
    rc = asyncio.run(_diagnose(args.org_id, as_json=args.json))
    sys.exit(rc)


if __name__ == "__main__":
    main()
