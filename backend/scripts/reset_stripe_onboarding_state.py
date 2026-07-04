#!/usr/bin/env python3
"""
Cleanly remove the afianco-side payment_connection for an org so the
onboarding flow can be retried from scratch.

What this does
--------------
* Deletes the ``payment_connections`` document for the given org.

What it does NOT do
-------------------
* Does NOT delete the Stripe Account itself. Stripe deliberately
  forbids deleting Connect Express accounts via API (data retention,
  KYC audit). Test-mode accounts stay parked in the dashboard but
  are inert once afianco no longer references them.
* Does NOT touch any other collection (orders, audit_logs, etc.).
  Past orders that referenced the old ``payment_checkout.reference``
  remain valid as historical snapshots.

Confirmation prompt
-------------------
Always asks for explicit ``yes`` before deleting unless ``--force``
is passed. Lets you script the cleanup in CI without a TTY by
bypassing the prompt.

Usage
-----
    cd backend
    python -m scripts.reset_stripe_onboarding_state
    python -m scripts.reset_stripe_onboarding_state --org-id <uuid>
    python -m scripts.reset_stripe_onboarding_state --force   # no prompt
"""

import argparse
import asyncio
import sys
from pathlib import Path

_BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_BACKEND_DIR))


_DEFAULT_ORG_ID = "16d64b96-b90f-4705-b6aa-03d279014909"  # org "tet"


async def _reset(org_id: str, force: bool):
    from database import payment_connections_collection

    existing = await payment_connections_collection.find_one(
        {"organization_id": org_id, "provider": "stripe"},
        {"_id": 0, "external_account_id": 1, "status": 1, "runtime_status": 1},
    )

    print("=" * 72)
    print(f"Stripe onboarding reset — org {org_id}")
    print("=" * 72)
    print()
    if not existing:
        print("Nothing to reset — no payment_connection found for this org.")
        print()
        return 0

    print("Found existing connection:")
    print(f"  external_account_id : {existing.get('external_account_id')}")
    print(f"  status              : {existing.get('status')}")
    print(f"  runtime_status      : {existing.get('runtime_status')}")
    print()
    print("Reset will:")
    print("  • Delete the payment_connection from MongoDB.")
    print("  • Leave the Stripe Account itself parked (Stripe forbids")
    print("    deletion of Connect Express accounts via API).")
    print("  • Leave historical orders untouched (their snapshot of")
    print("    payment_checkout.reference remains valid).")
    print()

    if not force:
        try:
            answer = input("Proceed? Type 'yes' to confirm: ").strip().lower()
        except EOFError:
            answer = ""
        if answer != "yes":
            print("Cancelled — nothing was deleted.")
            return 1

    result = await payment_connections_collection.delete_many(
        {"organization_id": org_id, "provider": "stripe"},
    )
    print(f"✓ Deleted {result.deleted_count} payment_connection(s).")
    print()
    print("Next steps:")
    print("  • Hard-refresh frontend; Settings → Payment Connections")
    print("    will now show the org as not connected.")
    print("  • Re-run scripts/create_stripe_test_ch_account.py if you")
    print("    want a fresh API-created Express account, or use the")
    print("    UI 'Connect Stripe' button to onboard manually.")
    return 0


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--org-id", default=_DEFAULT_ORG_ID,
                        help=f"Organisation id (default: {_DEFAULT_ORG_ID})")
    parser.add_argument("--force", action="store_true",
                        help="Skip the 'yes' confirmation prompt (CI-safe)")
    args = parser.parse_args()
    rc = asyncio.run(_reset(args.org_id, force=args.force))
    sys.exit(rc)


if __name__ == "__main__":
    main()
