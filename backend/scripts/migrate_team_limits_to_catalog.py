#!/usr/bin/env python3
"""
migrate_team_limits_to_catalog.py
==================================
Onda 10 Step B.1 — migrate `_TEAM_LIMITS` hardcoded dict into
`commercial_plans.platform_limits.team_members`.

Why:
  Pre-Onda 10, the team-members invitation gate consulted a frozen dict
  `_TEAM_LIMITS = {"free":1, "starter":2, "core":5, "pro":15,
  "enterprise":-1}` duplicated in TWO files (routers/organizations.py
  and routers/billing.py). Drift trap and zero admin self-serve: a
  system_admin who wanted to bump Solo from 2 to 5 had to deploy code.

  Migrating to `commercial_plans.platform_limits.team_members` brings
  team_members under the same admin-editable umbrella as everything
  else, queryable via the existing /admin/catalog endpoints, and
  audit-logged automatically when modified.

What this script does:
  1. Inspects every commercial_plan (by slug) and reports current
     platform_limits state
  2. With --apply: sets platform_limits.team_members on each known
     plan slug to the legacy _TEAM_LIMITS value
  3. Idempotent: re-running with --apply is a no-op if the value
     already matches

Usage:
    cd backend
    python -m scripts.migrate_team_limits_to_catalog            # dry-run
    python -m scripts.migrate_team_limits_to_catalog --apply    # execute

Idempotent. Safe to re-run.
"""

import argparse
import sys
from pathlib import Path

_BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_BACKEND_DIR))


# Source-of-truth: the legacy hardcoded dicts (still kept in their
# respective files as defence-in-depth fallback for plan slugs that
# aren't yet in the catalog).
_LEGACY_TEAM_LIMITS = {
    "free":       1,
    "starter":    2,
    "core":       5,
    "pro":       15,
    "enterprise": -1,
}

# Onda 10 Step B.2 — chat session retention TTL (days). Was hardcoded
# in services/chat_service.py:_PLAN_TTL_DAYS.
_LEGACY_CHAT_TTL_DAYS = {
    "free":         7,
    "starter":     30,
    "core":        90,
    "pro":        180,
    "enterprise": 365,
}

# Onda 10 Step B.5 — stores abuse cap (defence-in-depth above stores_max).
# Was hardcoded as HARD_ABUSE_CAP=10 in routers/stores.py:238 — same value
# for every plan. Migrating allows admin to grant special customers a
# higher abuse cap (or lower it for non-trusted plans).
_LEGACY_STORES_ABUSE_CAP = {
    "free":       10,
    "starter":    10,
    "core":       10,
    "pro":        10,
    "enterprise": 50,   # bump for enterprise-tier strategic customers
}

# Map of platform_limit key → legacy dict, for the migration loop.
# Adding a new key in the future = add a row here, the loop handles it.
_MIGRATIONS = [
    ("team_members",            _LEGACY_TEAM_LIMITS),
    ("chat_session_ttl_days",   _LEGACY_CHAT_TTL_DAYS),
    ("stores_max_abuse_cap",    _LEGACY_STORES_ABUSE_CAP),
]


def _sync_mongo():
    import os
    import pymongo
    return pymongo.MongoClient(
        os.environ.get("MONGO_URL", "mongodb://localhost:27017"),
        serverSelectionTimeoutMS=5000,
    )[os.environ.get("DB_NAME", "test_database")]


def _build_target_dict() -> dict:
    """For each plan slug, compute the desired platform_limits dict that
    consolidates all the legacy dicts into a single document write."""
    target: dict = {}
    for plat_key, legacy_dict in _MIGRATIONS:
        for slug, value in legacy_dict.items():
            target.setdefault(slug, {})[plat_key] = value
    return target


def _run(args) -> int:
    db = _sync_mongo()
    coll = db.commercial_plans

    print("=" * 78)
    print("MIGRATION — hardcoded dicts → commercial_plans.platform_limits")
    print(f"Mode: {'APPLY' if args.apply else 'DRY-RUN'}")
    print(f"Migrating keys: {[k for k, _ in _MIGRATIONS]}")
    print("=" * 78)
    print()

    target_by_slug = _build_target_dict()
    affected = []  # list of (slug, key, old, new)
    skipped_slugs = []
    missing = set()

    for slug, target_dict in target_by_slug.items():
        plan = coll.find_one({"slug": slug, "is_addon": {"$ne": True}})
        if not plan:
            missing.add(slug)
            print(f"  [{slug:12}] ⚠  plan not found in commercial_plans (skipped)")
            continue

        # Merge with any existing keys so we don't drop unrelated entries
        # admin may have added in the future (e.g. hard_abuse_caps in B.5).
        current_pl = plan.get("platform_limits") or {}
        if not isinstance(current_pl, dict):
            current_pl = {}
        merged = {**current_pl, **target_dict}

        if merged == current_pl:
            skipped_slugs.append(slug)
            print(f"  [{slug:12}] ✅ already on target")
            continue

        # Track per-key changes for the audit log
        for k, v in target_dict.items():
            if current_pl.get(k) != v:
                affected.append((slug, k, current_pl.get(k), v))

        if args.apply:
            # Single $set on the whole platform_limits dict atomically:
            # works whether the existing value is null/missing/dict.
            res = coll.update_one(
                {"slug": slug},
                {"$set": {"platform_limits": merged}},
            )
            ok = res.modified_count == 1
            for k, v in target_dict.items():
                old = current_pl.get(k)
                if old != v:
                    print(f"  [{slug:12}] {'✅ MIGRATED' if ok else '❌ NOT MODIFIED'} "
                          f"{k}: {old!r} → {v}")
        else:
            for k, v in target_dict.items():
                old = current_pl.get(k)
                if old != v:
                    print(f"  [{slug:12}] would set {k}: {old!r} → {v}")

    print()
    print("─" * 78)
    total = sum(len(d) for _, d in _MIGRATIONS)
    print(f"  total key×slug considered: {total}")
    print(f"  individual changes:        {len(affected)}")
    print(f"  slugs already aligned:     {len(skipped_slugs)}")
    print(f"  plans missing:             {len(missing)} {sorted(missing) if missing else ''}")

    # Audit log entry on apply
    if args.apply and affected:
        from datetime import datetime, timezone
        # Group changes by slug for a cleaner audit shape
        changes_by_slug: dict = {}
        for slug, key, old, new in affected:
            changes_by_slug.setdefault(slug, {})[key] = {"old": old, "new": new}
        db.catalog_audit_log.insert_one({
            "entity_type": "commercial_plan",
            "entity_id": "multiple",
            "action": "migrate_platform_limits",
            "changes": changes_by_slug,
            "performed_by": "migration_script",
            "performed_at": datetime.now(timezone.utc).isoformat(),
            "notes": (
                "Onda 10 Step B.1+B.2 — hardcoded dicts "
                f"({', '.join(k for k, _ in _MIGRATIONS)}) → "
                "platform_limits"
            ),
        })
        print("  audit log entry inserted")

    if not args.apply and affected:
        print()
        print("Re-run with --apply to execute.")
        return 1
    return 0


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--apply", action="store_true",
                        help="Execute the migration (default: dry-run)")
    args = parser.parse_args()
    rc = _run(args)
    sys.exit(rc)


if __name__ == "__main__":
    main()
