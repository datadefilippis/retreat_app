"""
rename_tiers_by_plan.py
=======================
Onda 19.1 — standardize the display `name` of every PricingPlan tier
so it always matches the CommercialPlan that uses it.

Before
======
Tier names were inherited from the original tier's role/limits, leading
to inconsistent labels:
  · `commerce_disabled` showed as "Commerce Disabled" — actually the
    Solo plan tier (Solo has no commerce features)
  · `ai_assistant_starter_lite` showed as "AI Starter Lite" — actually
    the Solo plan tier
  · `ai_assistant_starter` showed as "AI Starter" — actually the
    Commerce Starter (core) plan tier ← especially confusing
  · `commerce_unlimited` showed as "Commerce Unlimited" — actually the
    Custom plan tier

After
=====
For every tier `T` referenced by exactly one CommercialPlan `P` (post-
Onda-19 migration this is the steady state):
    T.name = P.name
e.g. all 6 module-tiers used by Solo become "Solo" in the Tiers UI.
The slug stays unchanged (immutable identifier).

Orphan tiers (no commercial plan uses them) are prefixed "(orphan)" so
the admin can spot them.

Run
===
  cd backend && set -a; source .env; set +a
  ./venv/bin/python -m scripts.rename_tiers_by_plan --dry-run
  ./venv/bin/python -m scripts.rename_tiers_by_plan
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
    catalog_audit_log_collection,
)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


async def main(dry_run: bool) -> int:
    print(f"{'DRY-RUN' if dry_run else 'EXECUTE'} — Onda 19.1 tier name standardization")
    print("=" * 78)

    # ── Build inverse index tier_slug → list of CommercialPlan docs ───────
    tier_to_plans: dict[str, list[dict]] = defaultdict(list)
    cursor = commercial_plans_collection.find(
        {"is_addon": {"$ne": True}, "is_archived": {"$ne": True}},
        {"_id": 0, "slug": 1, "name": 1, "module_plans": 1},
    )
    async for plan in cursor:
        for tier_slug in (plan.get("module_plans") or {}).values():
            tier_to_plans[tier_slug].append(plan)

    # ── Walk all tiers, plan the renames ─────────────────────────────────
    cursor = pricing_plans_collection.find({}, {"_id": 0, "slug": 1, "name": 1, "module_key": 1})
    rename_plan: list[tuple[str, str, str]] = []  # (slug, old_name, new_name)
    async for tier in cursor:
        slug = tier["slug"]
        old_name = tier.get("name", "")
        plans = tier_to_plans.get(slug, [])

        if len(plans) == 0:
            new_name = f"(orphan) {old_name}" if not old_name.startswith("(orphan)") else old_name
        elif len(plans) == 1:
            new_name = plans[0]["name"]
        else:
            # Multi-plan (shouldn't happen post-Onda-19 but handle gracefully)
            joined = " · ".join(sorted({p["name"] for p in plans}))
            new_name = f"(shared) {joined}"

        if new_name != old_name:
            rename_plan.append((slug, old_name, new_name))

    # ── Output planning ────────────────────────────────────────────────
    print(f"\n  {len(rename_plan)} tier(s) will be renamed:\n")
    if not rename_plan:
        print("  ✓ All tier names already match their plan. Nothing to do.")
        return 0

    # Group output by module for readability
    by_module: dict[str, list] = defaultdict(list)
    cursor = pricing_plans_collection.find({}, {"_id": 0, "slug": 1, "module_key": 1})
    slug_to_module: dict[str, str] = {}
    async for t in cursor:
        slug_to_module[t["slug"]] = t["module_key"]

    for slug, old_name, new_name in rename_plan:
        mk = slug_to_module.get(slug, "?")
        by_module[mk].append((slug, old_name, new_name))

    for mk in sorted(by_module.keys()):
        print(f"  {mk}:")
        for slug, old_name, new_name in sorted(by_module[mk]):
            print(f"    {slug:42s}  {old_name!r:30s}  →  {new_name!r}")
        print()

    if dry_run:
        print("DRY-RUN — no writes performed.")
        return 0

    # ── Execute ──────────────────────────────────────────────────────────
    now = _now_iso()
    bulk_updates = 0
    audit_inserts = []
    for slug, old_name, new_name in rename_plan:
        result = await pricing_plans_collection.update_one(
            {"slug": slug},
            {"$set": {"name": new_name, "updated_at": now}},
        )
        if result.modified_count:
            bulk_updates += 1
            audit_inserts.append({
                "id": uuid.uuid4().hex,
                "entity_type": "pricing_plan",
                "entity_id": slug,
                "action": "tier_rename_to_plan_name",
                "changes": {"name": {"old": old_name, "new": new_name}},
                "performed_by": "onda_19_1_rename_script",
                "performed_at": now,
                "notes": "Onda 19.1: standardize tier display name to match the CommercialPlan that uses it",
            })

    if audit_inserts:
        await catalog_audit_log_collection.insert_many(audit_inserts)

    print(f"\n✓ Renamed {bulk_updates} tier(s) + {len(audit_inserts)} audit entries written.")
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="Preview only, no writes")
    args = parser.parse_args()
    sys.exit(asyncio.run(main(dry_run=args.dry_run)))
