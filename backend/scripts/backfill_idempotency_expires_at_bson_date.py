"""Backfill idempotency_keys.expires_at: ISO string → BSON Date.

Track O Step 1.1 fix — pre-O1.1 il middleware/idempotency.py scriveva
expires_at come ISO string (`.isoformat()`). MongoDB TTL index su `expires_at`
con expireAfterSeconds=0 IGNORA silenziosamente i record string → collection
cresceva unbounded.

Post-O1.1 il middleware scrive BSON Date direttamente, ma i record LEGACY
in prod sono ancora string. Questo script converte i record esistenti
(safe, idempotent, dry-run friendly).

Usage:
    # Dry-run (no DB write, mostra cosa farebbe)
    python -m scripts.backfill_idempotency_expires_at_bson_date --dry-run

    # Apply (production)
    python -m scripts.backfill_idempotency_expires_at_bson_date --apply

    # Apply con limit batch (default 1000, safe per collection grandi)
    python -m scripts.backfill_idempotency_expires_at_bson_date --apply --batch-size 500

Behavior:
    1. Find docs where expires_at is type "string" (legacy)
    2. Parse ISO string → datetime UTC
    3. Update document with $set: {expires_at: <datetime>}
    4. Idempotent: re-running e' safe (skip docs gia' convertiti)
    5. Post-run: stampa stats (converted, skipped, errors)

After successful run, TTL index inizia ad auto-cleanup gli expired records
(MongoDB background thread, ~60s polling).
"""

import asyncio
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

# Make backend root importable
BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from database import idempotency_keys_collection  # noqa: E402


async def backfill(dry_run: bool = True, batch_size: int = 1000) -> dict:
    """Convert legacy ISO-string expires_at to BSON Date.

    Returns stats dict: {converted, skipped, errors}.
    """
    stats = {"converted": 0, "skipped": 0, "errors": 0, "parse_failures": 0}

    # MongoDB $type query: 2 = string. Records with BSON Date (type 9) are skipped.
    cursor = idempotency_keys_collection.find(
        {"expires_at": {"$type": 2}},  # 2 = string
        {"_id": 1, "expires_at": 1, "digest": 1},
    ).limit(batch_size)

    async for doc in cursor:
        raw = doc.get("expires_at")
        if not isinstance(raw, str):
            # Should not happen given $type filter, defensive skip
            stats["skipped"] += 1
            continue

        # Parse ISO 8601 string → datetime (UTC-aware)
        try:
            parsed = datetime.fromisoformat(raw)
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=timezone.utc)
        except (ValueError, TypeError) as exc:
            print(
                f"  parse failure for digest={doc.get('digest', '?')[:16]} "
                f"raw={raw!r}: {exc}"
            )
            stats["parse_failures"] += 1
            continue

        if dry_run:
            stats["converted"] += 1
            continue

        try:
            await idempotency_keys_collection.update_one(
                {"_id": doc["_id"]},
                {"$set": {"expires_at": parsed}},
            )
            stats["converted"] += 1
        except Exception as exc:
            print(f"  update failure for _id={doc['_id']}: {exc}")
            stats["errors"] += 1

    return stats


async def main():
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Report cosa farebbe, no DB write (default).",
    )
    parser.add_argument(
        "--apply", action="store_true",
        help="Esegui le update (overrides --dry-run).",
    )
    parser.add_argument(
        "--batch-size", type=int, default=1000,
        help="Max documenti per esecuzione (default 1000).",
    )
    args = parser.parse_args()

    dry_run = not args.apply  # default dry_run unless --apply

    mode = "DRY-RUN" if dry_run else "APPLY (production)"
    print(f"=== idempotency_keys.expires_at backfill ({mode}) ===")
    print(f"Batch size: {args.batch_size}")
    print("")

    stats = await backfill(dry_run=dry_run, batch_size=args.batch_size)

    print("")
    print("=== Stats ===")
    print(f"  converted:      {stats['converted']}")
    print(f"  skipped:        {stats['skipped']}")
    print(f"  errors:         {stats['errors']}")
    print(f"  parse_failures: {stats['parse_failures']}")
    print("")
    if dry_run:
        print("Dry-run only. Re-run with --apply to commit changes.")
    else:
        print("Done. TTL index will auto-cleanup expired records within ~60s.")


if __name__ == "__main__":
    asyncio.run(main())
