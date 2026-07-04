"""
migrate_isolate_tiers.py
========================
Onda 19 Step 2 + Step 3 — split shared tiers into dedicated 1:1 copies
per commercial plan, then re-provision active orgs to pick up the new
mapping.

Convention going forward (post-migration):
  · Tier slug = "{module_key}_{commercial_plan_slug}"
  · Each commercial plan has dedicated tier per module
  · Editing one plan never silently impacts another

Algorithm (idempotent — safe to re-run):
  1. Build inverse index tier_slug → [plan_slugs] from commercial_plans.module_plans
  2. For each shared tier (used by ≥2 plans):
     a. Pick "semantic owner" — the plan whose slug matches the tier suffix
        (e.g. tier `cashflow_monitor_pro` semantic owner = plan "pro")
     b. For each non-owner plan in the shared list:
        - Compute new_slug = "{module_key}_{plan_slug}"
        - If new_slug already exists in pricing_plans → skip create (idempotent)
        - Otherwise: create a fresh PricingPlan doc as exact copy of the
          shared tier, only the slug/name change
        - Update commercial_plans[plan].module_plans[module_key] = new_slug
        - Write CatalogAuditEntry per change
  3. Collect set of plan_slugs that were re-mapped.
  4. Find every active org with commercial_plan_slug ∈ that set, call
     provision_commercial_plan() to recompute their module_subscriptions.
     Effective entitlements unchanged (new tiers are exact copies).

Safety:
  · Stripe is NOT touched — only DB-side AFianco state.
  · Old shared tier docs are LEFT IN PLACE as orphans (rollback safety net).
  · Re-running on a fully-migrated DB → zero writes, zero errors.

Usage:
  cd backend && set -a; source .env; set +a
  ./venv/bin/python -m scripts.migrate_isolate_tiers --dry-run    # preview
  ./venv/bin/python -m scripts.migrate_isolate_tiers              # execute
"""

import argparse
import asyncio
import sys
import uuid
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

_BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_BACKEND_DIR))

from database import (  # noqa: E402
    commercial_plans_collection,
    pricing_plans_collection,
    organizations_collection,
    catalog_audit_log_collection,
)


def _semantic_owner(tier_slug: str, plan_slugs: list[str]) -> str:
    """Pick which plan keeps the original tier slug.

    Priority:
      1. Plan whose slug matches the tier's suffix exactly
         (tier `cashflow_monitor_pro` → owner `pro`)
      2. Plan whose slug is the tier's last underscore-separated segment
         even if multi-token (rare)
      3. Alphabetically first plan in the list (deterministic fallback)
    """
    # Direct suffix match
    for p in plan_slugs:
        if tier_slug.endswith(f"_{p}"):
            return p
    # Fallback
    return sorted(plan_slugs)[0]


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


async def _audit(action: str, entity_id: str, changes: dict, notes: str) -> None:
    """Append a catalog_audit_log entry for the migration."""
    await catalog_audit_log_collection.insert_one({
        "id": uuid.uuid4().hex,
        "entity_type": "pricing_plan" if action.startswith("tier_") else "commercial_plan",
        "entity_id": entity_id,
        "action": action,
        "changes": changes,
        "performed_by": "onda_19_migration",
        "performed_at": _now_iso(),
        "notes": notes,
    })


async def main(dry_run: bool) -> int:
    print(f"{'DRY-RUN' if dry_run else 'EXECUTE'} — Onda 19 tier isolation migration")
    print("=" * 78)

    # ── 1. Load state ─────────────────────────────────────────────────────
    plans: dict[str, dict] = {}
    cursor = commercial_plans_collection.find(
        {"is_addon": {"$ne": True}, "is_archived": {"$ne": True}},
        {"_id": 0},
    )
    async for plan in cursor:
        plans[plan["slug"]] = plan

    tier_to_plans: dict[str, list[str]] = defaultdict(list)
    for plan_slug, plan in plans.items():
        for module_key, tier_slug in (plan.get("module_plans") or {}).items():
            tier_to_plans[tier_slug].append((plan_slug, module_key))

    existing_tiers: dict[str, dict] = {}
    cursor = pricing_plans_collection.find({}, {"_id": 0})
    async for tier in cursor:
        existing_tiers[tier["slug"]] = tier

    shared = {t: refs for t, refs in tier_to_plans.items() if len(refs) >= 2}

    if not shared:
        print("\n✓ No shared tiers — already fully isolated. Nothing to do.")
        return 0

    # ── 2. Plan + execute splits ─────────────────────────────────────────
    new_tiers_to_create: list[dict] = []  # PricingPlan docs to insert
    plan_remap_updates: dict[str, dict] = {}  # plan_slug → {module_key: new_tier_slug, ...}
    created_count = 0
    remapped_count = 0
    skipped_count = 0

    for shared_slug, refs in shared.items():
        plan_slugs = sorted({p for p, _ in refs})
        # Module key — derived from the tier slug's source plan refs
        # All refs to the same shared tier come from the same module_key
        module_keys = sorted({m for _, m in refs})
        if len(module_keys) != 1:
            print(f"  ⚠ {shared_slug!r} cross-module (modules={module_keys}). Skipping — anomalous data.")
            continue
        module_key = module_keys[0]

        owner = _semantic_owner(shared_slug, plan_slugs)
        non_owners = [p for p in plan_slugs if p != owner]

        print(f"\n  {shared_slug} (module={module_key}):")
        print(f"    semantic owner: {owner!r} → keeps {shared_slug!r}")

        for plan_slug in non_owners:
            new_slug = f"{module_key}_{plan_slug}"

            # Idempotency check 1: new tier already exists?
            if new_slug in existing_tiers:
                print(f"    {plan_slug!r}: {new_slug!r} already exists in pricing_plans (skip create)")
                # Still need to ensure the mapping points to it. Check current.
                current_mapping = (
                    plans.get(plan_slug, {}).get("module_plans") or {}
                ).get(module_key)
                if current_mapping == new_slug:
                    print(f"      mapping already correct (skip remap)")
                    skipped_count += 1
                else:
                    plan_remap_updates.setdefault(plan_slug, {})[module_key] = new_slug
                    remapped_count += 1
                    print(f"      → will remap module_plans[{module_key}] → {new_slug!r}")
                continue

            # Need to create new dedicated tier as copy of shared
            shared_doc = existing_tiers.get(shared_slug)
            if not shared_doc:
                print(f"    ⚠ shared tier doc {shared_slug!r} missing in pricing_plans — skip")
                continue

            # Copy with new slug + new id + name update
            new_tier = {
                "id": uuid.uuid4().hex,
                "module_key": shared_doc["module_key"],
                "slug": new_slug,
                "name": _name_for(shared_doc.get("name", ""), plan_slug),
                "price_monthly": shared_doc.get("price_monthly", 0.0),
                "price_yearly": shared_doc.get("price_yearly"),
                "currency": shared_doc.get("currency", "EUR"),
                "limits": dict(shared_doc.get("limits") or {}),
                "is_active": True,
                "sort_order": shared_doc.get("sort_order", 0),
                "created_at": _now_iso(),
                "updated_at": _now_iso(),
            }
            new_tiers_to_create.append(new_tier)
            plan_remap_updates.setdefault(plan_slug, {})[module_key] = new_slug
            created_count += 1
            remapped_count += 1
            print(f"    {plan_slug!r}: create {new_slug!r} (copy of {shared_slug!r})")
            print(f"      → will remap module_plans[{module_key}] → {new_slug!r}")

    # ── 3. Plan summary before write ──────────────────────────────────────
    print()
    print("─" * 78)
    print(f"  Will create: {created_count} new dedicated tiers")
    print(f"  Will remap : {remapped_count} module_plans entries (across "
          f"{len(plan_remap_updates)} commercial plans)")
    print(f"  Skipped (already migrated): {skipped_count}")
    print("─" * 78)

    if dry_run:
        print("\nDRY-RUN — no writes performed.")
        return 0

    # ── 4. Execute writes ──────────────────────────────────────────────────
    if new_tiers_to_create:
        await pricing_plans_collection.insert_many(new_tiers_to_create)
        print(f"\n✓ Inserted {len(new_tiers_to_create)} new tier docs")
        for t in new_tiers_to_create:
            await _audit(
                action="tier_isolation_create",
                entity_id=t["slug"],
                changes={"created_from": "shared_tier_split", "limits": t["limits"]},
                notes=f"Onda 19: dedicated tier for plan inferred via slug suffix",
            )

    for plan_slug, module_updates in plan_remap_updates.items():
        # Build $set for module_plans subkeys atomically
        set_doc = {f"module_plans.{mk}": ts for mk, ts in module_updates.items()}
        set_doc["updated_at"] = _now_iso()
        result = await commercial_plans_collection.update_one(
            {"slug": plan_slug},
            {"$set": set_doc},
        )
        if result.matched_count:
            print(f"✓ Remapped {plan_slug}: {module_updates}")
            await _audit(
                action="commercial_plan_remap_to_dedicated_tiers",
                entity_id=plan_slug,
                changes={"module_plans_updated": module_updates},
                notes="Onda 19: switched from shared tier to dedicated 1:1 mapping",
            )

    # ── 5. Re-provision active orgs (Step 3) ──────────────────────────────
    affected_plan_slugs = set(plan_remap_updates.keys())
    if not affected_plan_slugs:
        print("\nNo plans were remapped → no orgs to re-provision.")
        return 0

    print(f"\nRe-provisioning active orgs on plans: {sorted(affected_plan_slugs)}")
    cursor = organizations_collection.find(
        {"is_active": True, "commercial_plan_slug": {"$in": list(affected_plan_slugs)}},
        {"_id": 0, "id": 1, "name": 1, "commercial_plan_slug": 1, "stripe_subscription_id": 1, "billing_status": 1},
    )
    orgs = await cursor.to_list(10000)

    if not orgs:
        print("  (no active orgs on these plans — nothing to re-provision)")
        return 0

    from services import plan_provisioning
    reprovisioned = 0
    failed = 0
    for org in orgs:
        try:
            await plan_provisioning.provision_commercial_plan(
                org_id=org["id"],
                plan_slug=org["commercial_plan_slug"],
                assigned_by="onda_19_migration",
                stripe_subscription_id=org.get("stripe_subscription_id"),
                billing_status=org.get("billing_status", "active"),
            )
            reprovisioned += 1
            print(f"  ✓ {org['name']:30s} ({org['commercial_plan_slug']})")
        except Exception as e:
            failed += 1
            print(f"  ✗ {org['name']:30s} FAILED: {e}")

    print(f"\nRe-provisioning summary: {reprovisioned} OK, {failed} failed")
    return 0 if failed == 0 else 1


def _name_for(base_name: str, plan_slug: str) -> str:
    """Derive a display name for the new dedicated tier.

    Strategy: if the base_name contained a plan-tier label (e.g. "Cashflow
    Pro"), substitute the plan-specific label. Otherwise just append the
    plan slug in parentheses for clarity.
    """
    label_map = {
        "free": "Free",
        "starter": "Solo",
        "core": "Core",
        "pro": "Pro",
        "enterprise": "Enterprise",
    }
    plan_label = label_map.get(plan_slug, plan_slug.title())
    # Try a safe replace if base name contains a known label
    for old_label in ("Pro", "Free", "Starter", "Core", "Enterprise"):
        if old_label in base_name and old_label != plan_label:
            return base_name.replace(old_label, plan_label)
    # Fallback: append
    return f"{base_name} ({plan_label})" if base_name else plan_label


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="Preview only, no writes")
    args = parser.parse_args()
    sys.exit(asyncio.run(main(dry_run=args.dry_run)))
