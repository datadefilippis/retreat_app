#!/usr/bin/env python3
"""
migrate_unique_sparse_indices.py
================================
Onda 9.Z Step D — preventive hardening: migrate every legacy
`unique=True, sparse=True` index in the database to
`unique=True, partialFilterExpression={<field>: {"$type": "string"}}`.

Why:
  Step A fixed the live bug on `organizations.public_slug_1`. The same
  trap exists on 7 other indices that today are dormant (0 explicit
  null values), but a single insert with `null` would activate them.
  Pre-emptive fix keeps the codebase safe for the next 6+ months.

What this script does:
  For each (collection, field) tuple in the registry below:
    1. Inspect the current index spec
    2. If already on partialFilterExpression → skip
    3. If on sparse=True legacy → drop + create with partial spec
    4. Verify with 3 canary inserts (string, null, missing) — all must
       succeed. Cleanup canaries.
    5. Print before/after diff

Idempotent. Safe to re-run. Each (collection, field) is independent —
a failure on one does not abort the others.

Usage:
    cd backend
    python -m scripts.migrate_unique_sparse_indices            # apply
    python -m scripts.migrate_unique_sparse_indices --check    # read-only
    python -m scripts.migrate_unique_sparse_indices --rollback # restore sparse
"""

import argparse
import asyncio
import sys
from pathlib import Path

_BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_BACKEND_DIR))


# Registry of (collection_attribute, field, expected_type, index_name).
# All fields here are strings in practice. The expected_type is what the
# partialFilterExpression filters on. Adjust if a future field is BSON type
# different.
_REGISTRY = [
    ("addon_subscriptions_collection",  "stripe_subscription_item_id", "string", "stripe_subscription_item_id_1"),
    ("issued_tickets_collection",        "access_token",                "string", "access_token_1"),
    ("issued_bookings_collection",       "access_token",                "string", "access_token_1"),
    ("issued_reservations_collection",   "access_token",                "string", "access_token_1"),
    ("issued_downloads_collection",      "access_token",                "string", "access_token_1"),
    ("issued_course_accesses_collection","access_token",                "string", "access_token_1"),
    ("stores_collection",                "slug",                        "string", "slug_1"),
]


async def _get_collection(coll_attr: str):
    import database
    return getattr(database, coll_attr)


async def _spec(coll, idx_name):
    async for idx in coll.list_indexes():
        if idx.get("name") == idx_name:
            return idx
    return None


def _classify(idx):
    if not idx:
        return "missing"
    if "partialFilterExpression" in idx:
        return "partial"
    if idx.get("sparse"):
        return "sparse"
    return "unknown"


async def _drop_and_create(coll, idx_name, field, expected_type, partial: bool):
    try:
        await coll.drop_index(idx_name)
    except Exception as e:
        msg = str(e).lower()
        if "not found" not in msg and "ns not found" not in msg:
            raise
    if partial:
        await coll.create_index(
            field,
            unique=True,
            partialFilterExpression={field: {"$type": expected_type}},
            name=idx_name,
        )
    else:
        await coll.create_index(field, unique=True, sparse=True, name=idx_name)


async def _verify(coll, field, expected_type):
    """3 canary inserts: with string / null / missing. All must succeed.

    Note: the canary uses synthetic IDs so they don't conflict with real data.
    Always cleaned up post-test.
    """
    import secrets, time
    nonce = secrets.token_hex(4)
    base_id = f"canary-9z-{nonce}-{int(time.time())}"
    canaries = [
        {"id": f"{base_id}-string",  "name": "C1", field: f"{base_id}-real-value"},
        {"id": f"{base_id}-null",    "name": "C2", field: None},
        {"id": f"{base_id}-missing", "name": "C3"},
    ]
    inserted = []
    failures = []
    for doc in canaries:
        try:
            await coll.insert_one(doc)
            inserted.append(doc["id"])
        except Exception as e:
            failures.append((doc["id"], type(e).__name__, str(e)[:200]))
    for cid in inserted:
        try:
            await coll.delete_one({"id": cid})
        except Exception:
            pass
    return failures


async def _process(coll_attr, field, expected_type, idx_name, *, mode="apply") -> dict:
    coll = await _get_collection(coll_attr)
    coll_name = getattr(coll, "name", coll_attr)
    pre = await _spec(coll, idx_name)
    klass = _classify(pre)

    out = {"collection": coll_name, "field": field, "index": idx_name, "before": klass}

    if mode == "check":
        return out

    if mode == "rollback":
        if klass == "sparse":
            out["action"] = "noop"
            return out
        await _drop_and_create(coll, idx_name, field, expected_type, partial=False)
        out["action"] = "restored_sparse"
        return out

    # apply
    if klass == "partial":
        out["action"] = "noop"
        return out

    await _drop_and_create(coll, idx_name, field, expected_type, partial=True)
    failures = await _verify(coll, field, expected_type)
    if failures:
        out["action"] = "applied_with_verify_failure"
        out["failures"] = failures
    else:
        out["action"] = "applied"
    return out


async def _run(args) -> int:
    print("=" * 78)
    print(f"UNIQUE+SPARSE INDEX MIGRATION ({len(_REGISTRY)} indices)")
    print(f"Mode: {'CHECK' if args.check else 'ROLLBACK' if args.rollback else 'APPLY'}")
    print("=" * 78)
    print()

    mode = "check" if args.check else "rollback" if args.rollback else "apply"

    if args.rollback:
        print("⚠ Rollback will re-introduce the sparse=True legacy spec on all")
        print("  indices. The known-broken behaviour will be back. Continuing in 5s.")
        print("  Ctrl+C to abort.")
        await asyncio.sleep(5)
        print()

    rc = 0
    for coll_attr, field, expected_type, idx_name in _REGISTRY:
        try:
            res = await _process(coll_attr, field, expected_type, idx_name, mode=mode)
        except Exception as e:
            print(f"  ❌ {coll_attr}.{field}: {type(e).__name__}: {e}")
            rc = 2
            continue

        marker = {
            "noop": "✅ already on target spec",
            "applied": "✅ migrated + verified",
            "applied_with_verify_failure": "⚠ migrated but verify FAILED",
            "restored_sparse": "↩ restored sparse=True",
        }.get(res.get("action"), f"({res.get('action')})")
        before = res.get("before", "?")

        line = f"  {coll_attr.replace('_collection',''):28} {field:32} [before={before:<7}] {marker}"
        print(line)
        if "failures" in res:
            for cid, exc, msg in res["failures"]:
                print(f"     · {cid}: {exc}: {msg}")
            rc = 1

    print()
    if rc == 0:
        print("✅ Done. All indices on target spec.")
    else:
        print(f"⚠ Completed with rc={rc}. Investigate.")
    return rc


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--check",    action="store_true", help="Inspect only, no changes")
    parser.add_argument("--rollback", action="store_true", help="Restore sparse=True spec")
    args = parser.parse_args()
    rc = asyncio.run(_run(args))
    sys.exit(rc)


if __name__ == "__main__":
    main()
