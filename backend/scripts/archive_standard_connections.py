#!/usr/bin/env python3
"""
archive_standard_connections.py
===============================
Block 6 Fase 10a — archive legacy Standard Connect payment_connections
before the code that manages them is removed.

Safety properties:
  - Dry-run by default. Use --apply to actually write.
  - SELECTORS ARE EXPLICITLY SCOPED. Filter is
      {"connect_type": "standard"}
    so the query cannot accidentally sweep Express connections.
  - Hard cap: aborts if the candidate count exceeds --max-expected
    (default 100). Catches misconfigured environments where an unrelated
    collection / tenant might be mistakenly loaded.
  - Double-safety: copies to a NEW collection `payment_connections_archive`
    AND marks the original doc with `archived: true` + `archived_at`. The
    original is NEVER deleted — we prefer a flagged row to a lost row.
  - Idempotent: re-running with --apply is safe; already-archived docs are
    not re-copied (archive collection uses doc.id as unique key).

What this DOES NOT do:
  - It does not run block6_preflight. Call that separately first.
  - It does not touch billing data (organizations, billing_events,
    commercial_plans, subscriptions). Only payment_connections.

Usage:
  Dry-run  : docker compose exec backend python scripts/archive_standard_connections.py
  Apply    : docker compose exec backend python scripts/archive_standard_connections.py --apply

  Override threshold (rare):
      --max-expected N
"""

import argparse
import asyncio
import sys
from pathlib import Path

_BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_BACKEND_DIR))


async def main(apply: bool, max_expected: int) -> int:
    from database import payment_connections_collection, db
    from datetime import datetime, timezone
    from pymongo.errors import DuplicateKeyError

    archive_coll = db.payment_connections_archive

    # Ensure the archive collection has a unique index on `id` so the
    # re-run safety works. Idempotent index creation.
    await archive_coll.create_index("id", unique=True)

    selector = {"connect_type": "standard"}
    projection = {"_id": 0}  # keep full doc for archival

    # Enumerate candidates
    candidates = []
    async for doc in payment_connections_collection.find(selector, projection):
        candidates.append(doc)

    print(f"Candidates (connect_type='standard'): {len(candidates)}")
    for c in candidates:
        print(f"  - id={c.get('id')} org={c.get('organization_id')} "
              f"status={c.get('status')} account={c.get('external_account_id')}")

    if len(candidates) > max_expected:
        print()
        print(f"❌ ABORT: {len(candidates)} candidates exceeds --max-expected={max_expected}.")
        print("   This is unexpected scale. Investigate before proceeding.")
        return 2

    if not apply:
        print()
        print("ℹ️  Dry-run. No writes. Pass --apply to archive the above.")
        return 0

    now = datetime.now(timezone.utc)
    archived_count = 0
    flagged_count = 0
    skipped_count = 0

    for doc in candidates:
        doc_id = doc.get("id")
        if not doc_id:
            print(f"⚠️  skipping doc without id: {doc}")
            skipped_count += 1
            continue

        # Step 1: copy to archive (idempotent via unique index on id)
        archive_doc = dict(doc)
        archive_doc["archived_at"] = now
        try:
            await archive_coll.insert_one(archive_doc)
            archived_count += 1
        except DuplicateKeyError:
            # Already archived from a prior run — that's fine, keep going
            # so we still flag the original row below.
            pass

        # Step 2: flag the original with archived=true (idempotent set)
        update_res = await payment_connections_collection.update_one(
            {"id": doc_id},
            {"$set": {"archived": True, "archived_at": now}},
        )
        if update_res.modified_count == 1:
            flagged_count += 1

    print()
    print(f"Archived   : {archived_count} new copies into payment_connections_archive")
    print(f"Flagged    : {flagged_count} original docs marked archived=true")
    print(f"Skipped    : {skipped_count}")

    # Final integrity check: for each candidate, both the archive copy
    # and the original flag must exist.
    print()
    print("Verifying archive integrity...")
    integrity_issues = 0
    for doc in candidates:
        doc_id = doc.get("id")
        if not doc_id:
            continue
        in_archive = await archive_coll.count_documents({"id": doc_id}, limit=1)
        original = await payment_connections_collection.find_one(
            {"id": doc_id},
            {"_id": 0, "archived": 1},
        )
        if in_archive != 1 or not (original and original.get("archived") is True):
            print(f"  ✗ integrity issue on id={doc_id}: archive={in_archive}, "
                  f"archived_flag={original.get('archived') if original else '?'}")
            integrity_issues += 1
    if integrity_issues:
        print(f"⚠️  {integrity_issues} integrity issue(s) above — investigate.")
        return 3

    print("✅ all candidates have both an archive copy AND an archived=true flag")
    return 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true", help="Actually write. Default is dry-run.")
    ap.add_argument("--max-expected", type=int, default=100,
                    help="Abort if candidate count exceeds this. Default 100.")
    args = ap.parse_args()
    sys.exit(asyncio.run(main(args.apply, args.max_expected)))
