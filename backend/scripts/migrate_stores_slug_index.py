#!/usr/bin/env python3
"""
migrate_stores_slug_index.py
============================
Phase 3 of the Store consolidation plan — clean up the
`stores_collection.slug_1` GLOBAL slug uniqueness index.

Background
----------
Two distinct slug indexes coexist on `stores_collection` by design:

  · composite (organization_id, slug) UNIQUE partial
        defense-in-depth + fast org-scoped lookups
  · global  slug                       UNIQUE partial   ← THIS SCRIPT
        REQUIRED for deterministic public routing
        (`/co/<slug>` URL → `_resolve_org()` in routers/public.py)

The global index used to be `unique=True, sparse=True`. MongoDB 7's
sparse indexes ALSO index explicit `null` values (only missing fields
are excluded), so once a store was created without a slug, every
subsequent slug-less insert hit DuplicateKey on `{slug: null}`.

The runtime helper `database._ensure_stores_indexes()` self-heals on
startup, but this CLI is the explicit, observable migration path:
inspect → diff → drop → recreate → verify with canary inserts.

What this script does
---------------------
  1. Inspect current `slug_1` index spec.
  2. If already on partialFilterExpression → exit 0.
  3. If legacy sparse=True → drop + create new spec.
  4. Verify with 3 canary inserts (string / null / missing); all
     three must succeed.
  5. Cleanup canaries, print before/after diff.

Idempotent. Safe to re-run.

Usage:
    cd backend
    python -m scripts.migrate_stores_slug_index            # apply
    python -m scripts.migrate_stores_slug_index --rollback # restore legacy
    python -m scripts.migrate_stores_slug_index --check    # read-only
"""

import argparse
import asyncio
import sys
from pathlib import Path

_BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_BACKEND_DIR))


_INDEX_NAME = "slug_1"
_NEW_SPEC = {
    "unique": True,
    "partialFilterExpression": {"slug": {"$type": "string"}},
}
_LEGACY_SPEC = {"unique": True, "sparse": True}


async def _current_spec():
    from database import stores_collection
    async for idx in stores_collection.list_indexes():
        if idx.get("name") == _INDEX_NAME:
            return idx
    return None


def _classify(idx: dict) -> str:
    if not idx:
        return "missing"
    if "partialFilterExpression" in idx and not idx.get("sparse"):
        return "partial"  # already migrated
    if idx.get("sparse"):
        return "sparse"   # legacy, needs migration
    return "unknown"


async def _drop_and_create(new_spec: dict):
    from database import stores_collection
    try:
        await stores_collection.drop_index(_INDEX_NAME)
    except Exception as e:
        # NamespaceNotFound = no such index, ignore
        msg = str(e).lower()
        if "not found" not in msg and "ns not found" not in msg:
            raise
    create_kwargs = {"name": _INDEX_NAME, **new_spec}
    await stores_collection.create_index("slug", **create_kwargs)


async def _verify_post_migration():
    """Run 3 canary inserts on stores_collection to validate the new
    index's behaviour.

    All three must succeed. After verification the canary docs are
    removed so the DB returns to its pre-test state.

    Uses an idempotent canary org_id namespace that's guaranteed not
    to clash with any real org (8-char prefix `canary-p3` is reserved).
    """
    from database import stores_collection
    canaries = [
        {"id": "canary-p3-string", "organization_id": "canary-p3-org-a",
         "name": "C1", "slug": "canary-p3-real-slug"},
        {"id": "canary-p3-null",   "organization_id": "canary-p3-org-b",
         "name": "C2", "slug": None},
        {"id": "canary-p3-miss",   "organization_id": "canary-p3-org-c",
         "name": "C3"},  # slug missing entirely
    ]
    inserted_ids = []
    failures = []
    for doc in canaries:
        try:
            await stores_collection.insert_one(doc)
            inserted_ids.append(doc["id"])
        except Exception as e:
            failures.append((doc.get("id"), type(e).__name__, str(e)[:200]))
    # Cleanup — always run, even on failure
    for cid in inserted_ids:
        try:
            await stores_collection.delete_one({"id": cid})
        except Exception:
            pass
    return failures


async def _check():
    idx = await _current_spec()
    klass = _classify(idx)
    print("=" * 70)
    print(f"stores.{_INDEX_NAME} — current state")
    print("=" * 70)
    if idx is None:
        print("Index does not exist.")
    else:
        for k, v in idx.items():
            if k != "v":
                print(f"  {k}: {v}")
    print()
    print(f"Classification: {klass.upper()}")
    if klass == "partial":
        print("OK — Already migrated. No action needed.")
    elif klass == "sparse":
        print("LEGACY — sparse=True. Run without --check to migrate.")
    elif klass == "missing":
        print("MISSING — index absent. Run without --check to create.")
    else:
        print("UNKNOWN — manual review needed.")
    return klass


async def _migrate():
    klass = await _check()
    print()
    if klass == "partial":
        print("Nothing to do. Exit.")
        return 0
    print(f"Applying migration: drop + create {_INDEX_NAME} with partialFilterExpression")
    await _drop_and_create(_NEW_SPEC)
    print("Migration applied.")
    print()
    print("Verifying with 3 canary inserts (string / null / missing)...")
    failures = await _verify_post_migration()
    if failures:
        print("Verification FAILED:")
        for cid, exc_name, msg in failures:
            print(f"   - {cid}: {exc_name}: {msg}")
        print()
        print("Migration applied but post-check FAILED. Investigate.")
        return 2
    print("All 3 canary inserts succeeded. Migration verified.")
    print()
    final = await _current_spec()
    print("Final index spec:")
    for k, v in final.items():
        if k != "v":
            print(f"  {k}: {v}")
    return 0


async def _rollback():
    klass = await _check()
    print()
    if klass == "sparse":
        print("Already on legacy sparse spec. Nothing to roll back.")
        return 0
    print("Rolling back: drop + create with sparse=True (LEGACY, BUGGED)")
    print("WARNING: This will re-introduce the duplicate-key bug on null slugs.")
    print("   (continuing in 5 seconds — Ctrl+C to abort)")
    await asyncio.sleep(5)
    await _drop_and_create(_LEGACY_SPEC)
    print("Rollback applied. Index is back to legacy sparse=True.")
    return 0


async def _run(args):
    if args.check:
        await _check()
        return 0
    if args.rollback:
        return await _rollback()
    return await _migrate()


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--check", action="store_true",
                        help="Only inspect, no changes")
    parser.add_argument("--rollback", action="store_true",
                        help="Restore the legacy sparse=True spec")
    args = parser.parse_args()
    rc = asyncio.run(_run(args))
    sys.exit(rc)


if __name__ == "__main__":
    main()
