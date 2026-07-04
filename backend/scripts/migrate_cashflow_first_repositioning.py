#!/usr/bin/env python3
"""
migrate_cashflow_first_repositioning.py — Onda 9.N migration

Applies the strategic repositioning of Free + Solo plans to a CASHFLOW-FIRST
identity. Background:

  · Production data: all current users use cashflow-only.
  · Original Free had a tiny commerce demo (30 contact requests, 1 store, 50
    products). This created an INCOHERENT value ladder: Solo (€19) actually
    LOST commerce features versus Free.
  · Strategic decision (Onda 9.N): Free becomes pure cashflow demo. Solo
    becomes pure cashflow real plan. Commerce starts at Commerce Starter
    (€39). No regressions in the ladder.

WHAT THIS SCRIPT DOES:

  1. Ensures the new `product_catalog_disabled` PricingPlan exists in DB
     (idempotent insert from seed_pricing.py).
  2. Force-updates `module_plans.commerce` and `module_plans.product_catalog`
     on the Free and Solo CommercialPlan rows in DB, bypassing the seed
     additive-merge protection (which would otherwise leave the old
     assignments untouched on every startup).
  3. Force-updates `features_display` on Free and Solo to match the new
     seed file (removes commerce_30_contact_requests, products_50, no_shop).
  4. Force-updates `tagline` and `description` on Free and Solo.
  5. For every existing organization currently on `free` or `starter` plan:
     re-runs `provision_commercial_plan` to create new ModuleSubscriptions
     pointing at `commerce_disabled` + `product_catalog_disabled`. This
     also triggers reconcile_stores_to_plan_limit (Onda 9.K) which would
     deactivate any orphan store — but production has no commerce users so
     this should be a no-op.

USAGE:

    # Dry-run (default — shows what would change, no writes):
    python backend/scripts/migrate_cashflow_first_repositioning.py

    # Apply:
    python backend/scripts/migrate_cashflow_first_repositioning.py --execute

    # Apply but SKIP per-org re-provisioning (only update catalog rows):
    python backend/scripts/migrate_cashflow_first_repositioning.py --execute --skip-reprovision

WHAT IT DOES NOT DO:

  · Does not touch Stripe (no API calls).
  · Does not delete old `commerce_free` or `product_catalog_free` PricingPlans
    (kept for retrocompatibility / rollback).
  · Does not change prices (€0 / €19 / €39 / €79 / €199 unchanged).
  · Does not impact Commerce Starter / Pro / Custom plans.

ROLLBACK:

  Reverse by editing seed files back and running this script again — or
  manually update commercial_plans collection back to the old slugs:
    db.commercial_plans.updateOne({slug: 'free'},
      {$set: {'module_plans.commerce': 'commerce_free',
              'module_plans.product_catalog': 'product_catalog_free'}})
"""

from __future__ import annotations

import argparse
import asyncio
import os
import sys
from pathlib import Path

_BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_BACKEND_DIR))


def _ok(msg: str) -> None: print(f"  \u2713 {msg}")
def _info(msg: str) -> None: print(f"  \u2192 {msg}")
def _warn(msg: str) -> None: print(f"  \u26A0 {msg}")
def _fail(msg: str) -> None: print(f"  \u2717 {msg}")


# Patches to apply to commercial_plans rows (forced — bypass seed protection).
# These mirror exactly what seed_commercial_plans.py now declares.

PATCHES = {
    "free": {
        "tagline": "Cashflow demo, gratis per sempre",
        "description": "Prova gratis il monitoraggio cashflow.",
        "module_plans.commerce": "commerce_disabled",
        "module_plans.product_catalog": "product_catalog_disabled",
        "features_display": [
            "billing.features.cashflow_basic",
            "billing.features.data_rows_200",
            "billing.features.basic_analytics",
            "billing.features.ai_chat_3",
        ],
    },
    "starter": {
        "tagline": "Cashflow completo per la tua attivita",
        "description": "Cashflow completo + analytics avanzate per la tua attivita.",
        "module_plans.product_catalog": "product_catalog_disabled",
        # commerce already commerce_disabled, no change needed
        "features_display": [
            "billing.features.cashflow_full",
            "billing.features.data_rows_1000",
            "billing.features.ai_chat_20",
            "billing.features.email_alerts",
            "billing.features.email_digest_kpi",
            "billing.features.alert_config",
            "billing.features.export",
            "billing.features.team_2",
        ],
    },
}


async def _ensure_pricing_plans_exist(dry_run: bool) -> None:
    """Make sure product_catalog_disabled PricingPlan exists in DB."""
    from database import pricing_plans_collection

    existing = await pricing_plans_collection.find_one(
        {"module_key": "product_catalog", "slug": "product_catalog_disabled"},
        {"_id": 0, "slug": 1},
    )
    if existing:
        _ok("product_catalog_disabled tier already in DB")
        return

    if dry_run:
        _info("WOULD insert product_catalog_disabled tier")
        return

    # Re-run the seed_pricing function to insert it (idempotent)
    from services.seed_pricing import ensure_pricing_plans_exist
    await ensure_pricing_plans_exist()
    _ok("Inserted product_catalog_disabled tier via ensure_pricing_plans_exist()")


async def _patch_commercial_plans(dry_run: bool) -> dict:
    """Apply PATCHES to commercial_plans rows, bypassing seed protection."""
    from database import commercial_plans_collection
    counters = {"patched": 0, "unchanged": 0, "missing": 0}

    for slug, patch in PATCHES.items():
        existing = await commercial_plans_collection.find_one({"slug": slug}, {"_id": 0})
        if not existing:
            _warn(f"{slug}: row not in DB (run seed_commercial_plans first)")
            counters["missing"] += 1
            continue

        # Compute diffs to print
        diffs = []
        for k, v in patch.items():
            if "." in k:
                # Dot-notation field
                parent, child = k.split(".", 1)
                current = (existing.get(parent) or {}).get(child)
            else:
                current = existing.get(k)
            if current != v:
                diffs.append((k, current, v))

        if not diffs:
            _ok(f"{slug}: already at target state (no change)")
            counters["unchanged"] += 1
            continue

        print(f"  \u2192 {slug} ({existing.get('name')}):")
        for k, cur, new in diffs:
            cur_repr = repr(cur)[:60]
            new_repr = repr(new)[:60]
            print(f"      {k}:")
            print(f"        from: {cur_repr}")
            print(f"        to:   {new_repr}")

        if dry_run:
            counters["patched"] += 1
            continue

        await commercial_plans_collection.update_one(
            {"slug": slug},
            {"$set": patch},
        )
        counters["patched"] += 1

    return counters


async def _reprovision_orgs(dry_run: bool) -> dict:
    """Re-run provision_commercial_plan for every org on Free or Solo so their
    ModuleSubscriptions point at the new commerce_disabled + product_catalog_disabled
    tiers."""
    from database import organizations_collection
    from services.plan_provisioning import provision_commercial_plan

    counters = {"reprovisioned": 0, "skipped_no_plan": 0, "errors": 0}

    cursor = organizations_collection.find(
        {"commercial_plan_slug": {"$in": ["free", "starter"]}},
        {"_id": 0, "id": 1, "name": 1, "commercial_plan_slug": 1, "billing_status": 1,
         "stripe_subscription_id": 1, "trial_ends_at": 1, "current_period_end": 1},
    )
    orgs = []
    async for o in cursor:
        orgs.append(o)

    if not orgs:
        _info("No orgs on free/starter — nothing to re-provision")
        return counters

    for org in orgs:
        org_id = org["id"]
        plan = org.get("commercial_plan_slug")
        name = org.get("name", org_id)[:30]
        billing_status = org.get("billing_status", "manual")

        if dry_run:
            _info(f"WOULD reprovision: {name:30} plan={plan} billing={billing_status}")
            counters["reprovisioned"] += 1
            continue

        try:
            from datetime import datetime
            trial_ends = None
            if org.get("trial_ends_at"):
                try:
                    trial_ends = datetime.fromisoformat(
                        org["trial_ends_at"].replace("Z", "+00:00"),
                    )
                except (ValueError, TypeError):
                    pass
            current_end = None
            if org.get("current_period_end"):
                try:
                    current_end = datetime.fromisoformat(
                        org["current_period_end"].replace("Z", "+00:00"),
                    )
                except (ValueError, TypeError):
                    pass

            await provision_commercial_plan(
                org_id=org_id,
                plan_slug=plan,
                assigned_by="migration:9.N",
                stripe_subscription_id=org.get("stripe_subscription_id"),
                billing_status=billing_status,
                trial_ends_at=trial_ends,
                current_period_end=current_end,
                notes="Onda 9.N cashflow-first repositioning",
            )
            _ok(f"Reprovisioned: {name} ({plan})")
            counters["reprovisioned"] += 1
        except Exception as e:
            _fail(f"Failed to reprovision {name}: {e}")
            counters["errors"] += 1

    return counters


async def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--execute", action="store_true", help="Apply changes (default: dry-run).")
    parser.add_argument("--skip-reprovision", action="store_true",
                        help="Only patch commercial_plans rows; do not re-run provision_commercial_plan per org.")
    args = parser.parse_args()
    dry_run = not args.execute

    print("=" * 70)
    print("migrate_cashflow_first_repositioning.py (Onda 9.N)")
    print(f"MODE: {'DRY-RUN' if dry_run else 'EXECUTE'}")
    print(f"DB:   {os.environ.get('DB_NAME', 'test_database')}")
    print("=" * 70)

    print("\n[1/3] Ensure new PricingPlan tiers exist in DB...")
    await _ensure_pricing_plans_exist(dry_run)

    print("\n[2/3] Patch commercial_plans rows (force-bypass seed protection)...")
    p_counters = await _patch_commercial_plans(dry_run)
    print(f"\n  Summary: patched={p_counters['patched']} unchanged={p_counters['unchanged']} missing={p_counters['missing']}")

    if args.skip_reprovision:
        print("\n[3/3] SKIPPED per-org reprovisioning (--skip-reprovision flag)")
    else:
        print("\n[3/3] Re-provision existing orgs on free/starter to new module assignments...")
        r_counters = await _reprovision_orgs(dry_run)
        print(f"\n  Summary: reprovisioned={r_counters['reprovisioned']} skipped={r_counters['skipped_no_plan']} errors={r_counters['errors']}")

    if dry_run:
        print("\nNOTE: dry-run only. Re-run with --execute to apply.\n")
    else:
        if p_counters.get("missing", 0) > 0:
            _fail("Some commercial_plans rows missing — restart backend and retry.")
            return 1
        print("\nDone. Free + Solo now positioned as cashflow-only. Commerce starts at Commerce Starter.\n")
        print("VERIFY:")
        print("  - /plans page: Free + Solo cards should show '—' on commerce/products rows")
        print("  - Solo card should NOT show 'Niente shop' badge anymore")
        print("  - Sidebar nav for Solo orgs: no 'Stores' / 'Orders' / 'Calendar' entries")

    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
