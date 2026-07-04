#!/usr/bin/env python3
"""
unarchive_standard_connections.py
=================================
Block 6 emergency rollback — restore Standard connections that were archived
by archive_standard_connections.py.

Use this if:
  - A later Block 6 phase (10b/c/d) exposed an issue and a merchant needs
    their Standard connection back urgently.
  - You realize the original archive was run against the wrong DB / env.

Semantics:
  - Dry-run by default, --apply to write.
  - Sets archived=false on the original doc and removes archived_at.
  - Does NOT re-copy from payment_connections_archive — the original row
    still exists, we just un-flag it. If the original row is ALSO missing
    (hard-deleted somehow), an optional --restore-from-archive path
    re-inserts it from the archive copy.
  - Idempotent: running twice is safe.

This script does NOT restore the old Standard code paths — only the DB
flags. If you also need the code back, revert the relevant Fase 10b/c/d
commits.

Usage:
  Dry-run  : docker compose exec backend python scripts/unarchive_standard_connections.py
  Apply    : docker compose exec backend python scripts/unarchive_standard_connections.py --apply
  Restore missing rows too:
      --restore-from-archive
"""

import argparse
import asyncio
import sys
from pathlib import Path

_BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_BACKEND_DIR))


async def main(apply: bool, restore_from_archive: bool) -> int:
    from database import payment_connections_collection, db

    archive_coll = db.payment_connections_archive

    # Find everything currently archived. Scoped strictly to Standard.
    archived_ids = set()
    async for doc in archive_coll.find({"connect_type": "standard"}, {"_id": 0, "id": 1}):
        if doc.get("id"):
            archived_ids.add(doc["id"])
    print(f"Archive contains {len(archived_ids)} Standard connection id(s)")

    if not archived_ids:
        print("Nothing to restore.")
        return 0

    # For each archived id, check if the original row still exists
    originals_present = 0
    originals_missing = []
    async for doc in payment_connections_collection.find(
        {"id": {"$in": list(archived_ids)}}, {"_id": 0, "id": 1},
    ):
        originals_present += 1
        archived_ids.discard(doc["id"])
    originals_missing = list(archived_ids)  # remaining are not in original collection
    print(f"  originals still present: {originals_present}")
    print(f"  originals missing      : {len(originals_missing)}")

    if not apply:
        print()
        print("ℹ️  Dry-run. Would un-flag present rows.")
        if originals_missing and restore_from_archive:
            print(f"   Would also re-insert {len(originals_missing)} missing rows from archive.")
        elif originals_missing:
            print(f"   {len(originals_missing)} are missing; pass --restore-from-archive to recreate.")
        return 0

    # Un-flag present originals
    update_res = await payment_connections_collection.update_many(
        {"archived": True, "connect_type": "standard"},
        {"$set": {"archived": False}, "$unset": {"archived_at": ""}},
    )
    print(f"  Un-flagged {update_res.modified_count} original rows")

    # Optionally restore missing ones from archive
    if originals_missing and restore_from_archive:
        restored = 0
        for missing_id in originals_missing:
            archive_doc = await archive_coll.find_one({"id": missing_id}, {"_id": 0})
            if not archive_doc:
                continue
            archive_doc.pop("archived_at", None)
            archive_doc["archived"] = False
            try:
                await payment_connections_collection.insert_one(archive_doc)
                restored += 1
            except Exception as exc:
                print(f"  failed to restore id={missing_id}: {exc}")
        print(f"  Restored {restored} missing rows from archive")

    print("✅ un-archive complete")
    return 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true", help="Actually write.")
    ap.add_argument("--restore-from-archive", action="store_true",
                    help="Also re-insert rows whose originals are missing.")
    args = ap.parse_args()
    sys.exit(asyncio.run(main(args.apply, args.restore_from_archive)))
