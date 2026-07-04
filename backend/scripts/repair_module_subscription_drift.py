#!/usr/bin/env python3
"""
repair_module_subscription_drift.py
====================================
Detect and (optionally) repair the "orphaned Pro module_subscription" drift
class identified in Onda 9.Y.0.2.

Drift definition:
  An organization where:
    - commercial_plan_slug ∈ {free, starter}
    - billing_status ∈ {canceled, none, manual} (NOT active/trialing)
  AND
    - has an *active* module_subscription with `commercial_plan_slug` of
      a higher tier (core, pro, enterprise) — granting entitlements
      (e.g. cashflow_monitor.data_rows = -1) that the org's actual
      commercial plan does NOT include.

Root cause (audit 2026-04-30):
  Stripe sometimes delivers `customer.subscription.updated` with
  status=canceled WITHOUT the matching `customer.subscription.deleted`.
  Pre-9.Y.0.2, `_handle_subscription_updated` metadata-only branch
  updated org fields but did NOT cancel module_subscriptions, leaving
  the higher-tier rows active. The 9.Y.0.2 patch closes the path going
  forward; this script repairs orgs already in drift.

Usage:
  cd backend

  # Dry-run (default) — list every drifted org, no mutations
  python -m scripts.repair_module_subscription_drift

  # Apply fix to ALL drifted orgs
  python -m scripts.repair_module_subscription_drift --apply

  # Fix a single org by id / email / slug
  python -m scripts.repair_module_subscription_drift --apply --org-id <ID>
  python -m scripts.repair_module_subscription_drift --apply --email a@b.com
  python -m scripts.repair_module_subscription_drift --apply --slug myorg

Fix action:
  Calls `deprovision_stripe_subscription(org_id, stripe_subscription_id)`
  if a stripe_subscription_id is present (clean codepath shared with
  customer.subscription.deleted webhook). Otherwise calls
  `provision_commercial_plan(org_id, commercial_plan_slug)` to cancel
  active subs and create fresh ones from the catalog.

Idempotent. Safe to re-run.
"""

import argparse
import asyncio
import sys
from pathlib import Path

# ── Add backend/ to sys.path so we can import project modules ────────────────
_BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_BACKEND_DIR))


_LOWER_TIER_SLUGS = frozenset({"free", "starter"})
_HIGHER_TIER_SLUGS = frozenset({"core", "pro", "enterprise"})
# Statuses where the org is NOT in active billing — drift is recoverable.
# (active/trialing/past_due are managed live by Stripe; we don't touch them.)
_RECOVERABLE_BILLING_STATUSES = frozenset({"canceled", "none", "manual"})


async def _resolve_target_orgs(args) -> list:
    """Return list of {id, name, ...} dicts to scan."""
    from database import organizations_collection, users_collection

    if args.org_id:
        cursor = organizations_collection.find({"id": args.org_id})
        orgs = await cursor.to_list(1)
        if not orgs:
            print(f"ERROR: org_id={args.org_id} not found", file=sys.stderr)
            sys.exit(2)
        return orgs

    if args.slug:
        cursor = organizations_collection.find({"public_slug": args.slug})
        orgs = await cursor.to_list(1)
        if not orgs:
            print(f"ERROR: slug={args.slug} not found", file=sys.stderr)
            sys.exit(2)
        return orgs

    if args.email:
        user = await users_collection.find_one({"email": args.email.lower().strip()})
        if not user or not user.get("organization_id"):
            print(f"ERROR: user email={args.email} has no organization", file=sys.stderr)
            sys.exit(2)
        org = await organizations_collection.find_one({"id": user["organization_id"]})
        return [org] if org else []

    # All orgs
    cursor = organizations_collection.find({})
    return await cursor.to_list(10000)


async def _detect_drift(org: dict) -> dict | None:
    """Return drift info for org if drifted, else None.

    Drift shape:
      {
        "org_id": str,
        "org_name": str,
        "commercial_plan_slug": str,
        "billing_status": str,
        "stripe_subscription_id": Optional[str],
        "drifted_subs": [
          {"id", "module_key", "pricing_plan_id",
           "sub_commercial_plan_slug"}, ...
        ],
      }
    """
    from database import module_subscriptions_collection

    org_id = org["id"]
    cps = (org.get("commercial_plan_slug") or "free").lower()
    bs = (org.get("billing_status") or "none").lower()

    # We only examine orgs whose org-level state should be lower-tier.
    if cps not in _LOWER_TIER_SLUGS:
        return None
    # Skip orgs in active billing — Stripe owns their state, we don't touch.
    if bs not in _RECOVERABLE_BILLING_STATUSES:
        return None

    # Find any *active* module_subscription whose own commercial_plan_slug
    # is a higher tier — that's drift.
    cursor = module_subscriptions_collection.find({
        "organization_id": org_id,
        "status": "active",
    })
    subs = await cursor.to_list(50)
    drifted = [
        {
            "id": s.get("id"),
            "module_key": s.get("module_key"),
            "pricing_plan_id": s.get("pricing_plan_id"),
            "sub_commercial_plan_slug": s.get("commercial_plan_slug"),
        }
        for s in subs
        if (s.get("commercial_plan_slug") or "").lower() in _HIGHER_TIER_SLUGS
    ]
    if not drifted:
        return None

    return {
        "org_id": org_id,
        "org_name": org.get("name"),
        "commercial_plan_slug": cps,
        "billing_status": bs,
        "stripe_subscription_id": org.get("stripe_subscription_id"),
        "drifted_subs": drifted,
    }


async def _repair_org(drift: dict) -> dict:
    """Apply the canonical fix to a drifted org.

    Strategy:
      - If stripe_subscription_id present → use deprovision_stripe_subscription
        (same path as customer.subscription.deleted webhook)
      - Else → provision_commercial_plan(commercial_plan_slug) which cancels
        active module_subscriptions and creates lower-tier ones
    """
    from services.plan_provisioning import (
        deprovision_stripe_subscription,
        provision_commercial_plan,
    )

    org_id = drift["org_id"]
    stripe_sub_id = drift.get("stripe_subscription_id")

    if stripe_sub_id:
        cancelled = await deprovision_stripe_subscription(org_id, stripe_sub_id)
        return {
            "method": "deprovision_stripe_subscription",
            "stripe_sub_id": stripe_sub_id,
            "module_subs_cancelled": cancelled,
        }

    # No stripe_subscription_id — direct re-provision to the org's lower tier
    target_slug = drift["commercial_plan_slug"]
    result = await provision_commercial_plan(
        org_id=org_id,
        plan_slug=target_slug,
        assigned_by="repair:9y02",
        billing_status="none" if target_slug == "free" else "manual",
    )
    return {"method": "provision_commercial_plan", **result}


async def _run(args) -> int:
    orgs = await _resolve_target_orgs(args)

    drifts = []
    for org in orgs:
        drift = await _detect_drift(org)
        if drift:
            drifts.append(drift)

    print("=" * 78)
    print(
        f"MODULE_SUBSCRIPTION DRIFT REPAIR — scanned {len(orgs)} orgs, "
        f"found {len(drifts)} in drift"
    )
    print("=" * 78)

    if not drifts:
        print("\n✅ No drift detected.")
        return 0

    for d in drifts:
        print(f"\n● Org: {d['org_name']!r} (id={d['org_id']})")
        print(f"  commercial_plan_slug = {d['commercial_plan_slug']!r}")
        print(f"  billing_status       = {d['billing_status']!r}")
        print(f"  stripe_subscription  = {d.get('stripe_subscription_id') or '(none)'}")
        print(f"  drifted active subs:")
        for s in d["drifted_subs"]:
            print(
                f"    · {s['module_key']:>18}  "
                f"sub_id={(s['id'] or '')[:12]}...  "
                f"sub.commercial_plan_slug={s['sub_commercial_plan_slug']!r}"
            )

        if args.apply:
            print("  → APPLYING FIX...")
            try:
                result = await _repair_org(d)
                print(f"  ✅ Fixed via {result['method']}")
                for k, v in result.items():
                    if k != "method":
                        print(f"     {k} = {v}")
            except Exception as e:
                print(f"  ❌ FIX FAILED: {e}")
                # Don't bail — try the next org
        else:
            print("  (dry-run; pass --apply to fix)")

    print()
    if args.apply:
        print(f"Done. Repaired {len(drifts)} orgs.")
    else:
        print(f"Dry-run complete. Re-run with --apply to fix {len(drifts)} orgs.")
    return 0 if not drifts or args.apply else 1


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument(
        "--apply", action="store_true",
        help="Apply the fix. Default is dry-run.",
    )
    parser.add_argument("--org-id", help="Limit to a single org by id")
    parser.add_argument("--slug", help="Limit to a single org by public_slug")
    parser.add_argument("--email", help="Limit to a single org via user email")
    args = parser.parse_args()

    rc = asyncio.run(_run(args))
    sys.exit(rc)


if __name__ == "__main__":
    main()
