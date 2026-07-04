#!/usr/bin/env python3
"""
migrate_public_slug_index.py
============================
Onda 9.Z Step A — migrate `organizations.public_slug_1` index from
`unique=True, sparse=True` to
`unique=True, partialFilterExpression={"public_slug": {"$type": "string"}}`.

Why:
  MongoDB 7's sparse indexes only exclude documents where the indexed
  field is MISSING; documents where the field is explicitly `null` ARE
  indexed. `Organization.public_slug = None` Pydantic default produces
  exactly that, so after the first signup every subsequent `insert_one`
  hits a DuplicateKey error on `{public_slug: null}` and the router
  reports HTTP 500. Bug confirmed by live reproduction on 2026-04-30.

What this script does:
  1. Inspect current index state
  2. If already migrated (partialFilterExpression present) → exit 0
  3. If sparse=True legacy index → drop + create new spec
  4. Verify behaviour with 3 synthetic inserts (string / null / missing)
     all of which must succeed
  5. Cleanup the synthetic docs
  6. Print before/after diff

Idempotent. Safe to re-run.

Usage:
    cd backend
    python -m scripts.migrate_public_slug_index            # apply migration
    python -m scripts.migrate_public_slug_index --rollback # restore sparse
    python -m scripts.migrate_public_slug_index --check    # read-only
"""

import argparse
import asyncio
import sys
from pathlib import Path

_BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_BACKEND_DIR))


_INDEX_NAME = "public_slug_1"
_NEW_SPEC = {
    "unique": True,
    "partialFilterExpression": {"public_slug": {"$type": "string"}},
}
_LEGACY_SPEC = {"unique": True, "sparse": True}


async def _current_spec():
    from database import organizations_collection
    async for idx in organizations_collection.list_indexes():
        if idx.get("name") == _INDEX_NAME:
            return idx
    return None


def _classify(idx: dict) -> str:
    if not idx:
        return "missing"
    if "partialFilterExpression" in idx:
        return "partial"  # already migrated
    if idx.get("sparse"):
        return "sparse"   # legacy, needs migration
    return "unknown"


async def _drop_and_create(new_spec: dict):
    from database import organizations_collection
    try:
        await organizations_collection.drop_index(_INDEX_NAME)
    except Exception as e:
        # NamespaceNotFound = no such index, ignore
        msg = str(e).lower()
        if "not found" not in msg and "ns not found" not in msg:
            raise
    create_kwargs = {"name": _INDEX_NAME, **new_spec}
    await organizations_collection.create_index("public_slug", **create_kwargs)


async def _verify_post_migration():
    """Run 3 canary inserts to validate the new index's behaviour.

    All three must succeed. After verification the canary docs are
    removed so the DB returns to its pre-test state.
    """
    from database import organizations_collection
    canaries = [
        {"id": "canary-9z-string", "name": "C1", "public_slug": "canary-9z-real-slug"},
        {"id": "canary-9z-null",   "name": "C2", "public_slug": None},
        {"id": "canary-9z-miss",   "name": "C3"},  # public_slug missing
    ]
    inserted_ids = []
    failures = []
    for doc in canaries:
        try:
            await organizations_collection.insert_one(doc)
            inserted_ids.append(doc["id"])
        except Exception as e:
            failures.append((doc.get("id"), type(e).__name__, str(e)[:200]))
    # Cleanup
    for cid in inserted_ids:
        try:
            await organizations_collection.delete_one({"id": cid})
        except Exception:
            pass
    return failures


async def _check():
    idx = await _current_spec()
    klass = _classify(idx)
    print("=" * 70)
    print("public_slug_1 — current state")
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
        print("✅ Already migrated. No action needed.")
    elif klass == "sparse":
        print("❌ Legacy sparse=True. Run without --check to migrate.")
    elif klass == "missing":
        print("⚠ Index missing. Run without --check to create with new spec.")
    else:
        print("⚠ Unknown spec. Manual review needed.")
    return klass


async def _migrate():
    klass = await _check()
    print()
    if klass == "partial":
        print("Nothing to do. Exit.")
        return 0
    print("Applying migration: drop + create with partialFilterExpression")
    await _drop_and_create(_NEW_SPEC)
    print("✅ Migration applied.")
    print()
    print("Verifying with 3 canary inserts (string / null / missing)...")
    failures = await _verify_post_migration()
    if failures:
        print("❌ Verification FAILED:")
        for cid, exc_name, msg in failures:
            print(f"   · {cid}: {exc_name}: {msg}")
        print()
        print("Migration applied but post-check FAILED. Investigate.")
        return 2
    print("✅ All 3 canary inserts succeeded. Migration verified.")
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
    print("⚠ This will re-introduce the duplicate-key bug. Are you sure?")
    print("   (continuing in 5 seconds — Ctrl+C to abort)")
    await asyncio.sleep(5)
    await _drop_and_create(_LEGACY_SPEC)
    print("✅ Rollback applied. Index is back to legacy sparse=True.")
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
