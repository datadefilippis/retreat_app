"""
audit_shared_tiers.py
=====================
Onda 19 Step 1 — read-only diagnostic.

Lists every PricingPlan (entitlement tier) that is referenced by ≥2
CommercialPlans via their `module_plans` mapping. Shared tiers are
the architectural problem we want to eliminate in Onda 19: editing
one tier silently impacts every commercial plan that points to it.

The migration script (Step 2) will create dedicated copies of each
shared tier — one per consuming plan — so each plan owns its own
tier 1:1 per module.

Run:
  cd backend && set -a; source .env; set +a
  ./venv/bin/python -m scripts.audit_shared_tiers

Zero writes. Safe to run anytime in any env.
"""

import asyncio
import sys
from collections import defaultdict
from pathlib import Path

_BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_BACKEND_DIR))

from database import (  # noqa: E402
    commercial_plans_collection,
    pricing_plans_collection,
)


async def main() -> int:
    # 1. Build inverse index: tier_slug → [plan_slug, ...]
    tier_to_plans: dict[str, list[str]] = defaultdict(list)
    plan_count = 0
    cursor = commercial_plans_collection.find(
        {"is_addon": {"$ne": True}},
        {"_id": 0, "slug": 1, "name": 1, "module_plans": 1, "is_archived": 1},
    )
    plans_by_slug: dict[str, dict] = {}
    async for plan in cursor:
        if plan.get("is_archived"):
            continue
        plan_count += 1
        plans_by_slug[plan["slug"]] = plan
        for module_key, tier_slug in (plan.get("module_plans") or {}).items():
            tier_to_plans[tier_slug].append(f"{plan['slug']}.{module_key}")

    # 2. Group by module key for readable output
    shared = {t: refs for t, refs in tier_to_plans.items() if len(refs) >= 2}
    dedicated = {t: refs for t, refs in tier_to_plans.items() if len(refs) == 1}

    # 3. Existing tier docs by slug (so we can flag references to non-existent tiers)
    existing_tier_slugs = set()
    cursor = pricing_plans_collection.find({}, {"_id": 0, "slug": 1})
    async for tier in cursor:
        existing_tier_slugs.add(tier["slug"])

    # ── Output ────────────────────────────────────────────────────────────
    print("=" * 78)
    print(f"SHARED TIERS — used by ≥2 commercial plans  (will migrate to dedicated)")
    print("=" * 78)

    if not shared:
        print("\n  ✓ No shared tiers detected. Nothing to migrate.\n")
    else:
        # Group displayed by module for clarity
        by_module: dict[str, list[tuple[str, list[str]]]] = defaultdict(list)
        for tier_slug, refs in shared.items():
            # refs are "plan.module" — extract module from first ref
            module_key = refs[0].split(".", 1)[1]
            plan_slugs = sorted({r.split(".", 1)[0] for r in refs})
            by_module[module_key].append((tier_slug, plan_slugs))

        total_shared_tiers = 0
        total_new_tiers_to_create = 0
        for module_key in sorted(by_module.keys()):
            print(f"\n  {module_key}:")
            for tier_slug, plan_slugs in by_module[module_key]:
                total_shared_tiers += 1
                exists_marker = "" if tier_slug in existing_tier_slugs else "  ⚠ tier doc MISSING"
                print(f"    {tier_slug:40s} → used by {len(plan_slugs)} plans:")
                for ps in plan_slugs:
                    plan_name = plans_by_slug.get(ps, {}).get("name", ps)
                    print(f"      · {ps:18s} ({plan_name})")
                # Plan that "keeps" the original slug = best semantic match
                # (e.g. plan_slug=='pro' keeps tier_slug ending in '_pro')
                semantic_owner = next(
                    (p for p in plan_slugs if tier_slug.endswith(f"_{p}")),
                    plan_slugs[0],  # fallback: alphabetical first
                )
                # New dedicated tiers needed = (n_plans - 1) since one plan
                # keeps the original tier
                new_count = len(plan_slugs) - 1
                total_new_tiers_to_create += new_count
                print(f"      → After migration: {tier_slug!r} stays for {semantic_owner!r}")
                for p in plan_slugs:
                    if p == semantic_owner:
                        continue
                    new_slug = f"{module_key}_{p}"
                    will_create = "(create new)" if new_slug not in existing_tier_slugs else "(already exists)"
                    print(f"      → New dedicated for {p!r}: {new_slug!r} {will_create}")
                print(f"  {exists_marker}")

        print()
        print("─" * 78)
        print(f"  Total shared tier slugs: {total_shared_tiers}")
        print(f"  New dedicated tiers to create: {total_new_tiers_to_create}")
        print("─" * 78)

    print()
    print("=" * 78)
    print(f"DEDICATED TIERS (already 1:1)")
    print("=" * 78)
    if not dedicated:
        print("\n  (none)\n")
    else:
        by_module2: dict[str, list[tuple[str, str]]] = defaultdict(list)
        for tier_slug, refs in dedicated.items():
            module_key = refs[0].split(".", 1)[1]
            plan_slug = refs[0].split(".", 1)[0]
            by_module2[module_key].append((tier_slug, plan_slug))
        for module_key in sorted(by_module2.keys()):
            print(f"\n  {module_key}:")
            for tier_slug, plan_slug in sorted(by_module2[module_key]):
                plan_name = plans_by_slug.get(plan_slug, {}).get("name", plan_slug)
                print(f"    {tier_slug:40s} ← {plan_slug:18s} ({plan_name}) ✓")

    # Orphan tiers — exist as PricingPlan but no commercial plan refs them
    referenced_slugs = set(tier_to_plans.keys())
    orphan_slugs = existing_tier_slugs - referenced_slugs
    print()
    print("=" * 78)
    print(f"ORPHAN TIERS (in pricing_plans collection but NO commercial plan uses them)")
    print("=" * 78)
    if not orphan_slugs:
        print("\n  (none)\n")
    else:
        for slug in sorted(orphan_slugs):
            print(f"  {slug}")
        print(f"\n  (Orphans are safe — they don't impact provisioning. Will not be touched by Onda 19.)")

    print()
    print(f"Audit complete. Inspected {plan_count} active commercial plans.")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
