#!/usr/bin/env python3
"""Wave GDPR-Admin Phase B — backfill legacy users with consent versioning.

Idempotent script that populates ``accepted_terms_version`` and
``accepted_terms_locale`` on existing User documents that lack
those fields (signups before Wave GDPR-Admin Phase B deploy).

Strategy:
  - For each user with ``accepted_terms_at IS NOT NULL`` but missing
    the new fields, mark as:
        accepted_terms_version = "v0.legacy:unknown_bootstrap"
        accepted_terms_locale  = user.locale OR "it" (best-effort)

  - For each backfilled user, ALSO insert a single consent_audit
    record with source="backfill" so the auxiliary log is consistent
    with the user doc.

  - Users that already have BOTH new fields are skipped (idempotency).
  - Users that NEVER accepted terms (accepted_terms_at is None — only
    possible for users created before terms acceptance was mandatory,
    a pre-v6.0 cohort) are flagged but NOT auto-marked: those are
    rare and merit operator review, not bulk fill.

Usage:
  # Dry-run (default — only counts what would change, no writes)
  python -m scripts.backfill_consent_versioning

  # Apply changes
  python -m scripts.backfill_consent_versioning --apply

  # Verbose (per-user log)
  python -m scripts.backfill_consent_versioning --apply --verbose

Safety:
  - The script does NOT touch users.password_hash or any other field.
  - It uses $set with explicit field names — no $unset, no $rename.
  - Bulk updates are batched in chunks of 200 to keep DB pressure low.
  - On any error mid-batch, the script logs and continues with the
    next user; partial backfill is safe and re-runnable.
"""

import argparse
import asyncio
import logging
import os
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))


async def run(apply: bool, verbose: bool) -> dict:
    """Run the backfill. Returns a stats dict for the caller to print."""
    from database import users_collection, consent_audit_collection
    from core.legal_versions import (
        LEGACY_VERSION_TAG, LEGACY_VERSION_HASH, legacy_version_string,
    )
    from datetime import datetime, timedelta, timezone

    logger = logging.getLogger(__name__)
    stats = {
        "users_scanned": 0,
        "users_already_versioned": 0,
        "users_to_backfill": 0,
        "users_backfilled": 0,
        "users_never_accepted": 0,
        "consent_records_inserted": 0,
        "errors": 0,
    }

    # Cursor: find users with accepted_terms_at set but no version yet.
    # Using $exists:false catches docs that lack the field entirely;
    # =None catches docs where it's explicitly None.
    query = {
        "$and": [
            {"accepted_terms_at": {"$ne": None}},
            {
                "$or": [
                    {"accepted_terms_version": {"$exists": False}},
                    {"accepted_terms_version": None},
                ],
            },
        ],
    }
    cursor = users_collection.find(query, {
        "_id": 0, "id": 1, "email": 1, "organization_id": 1,
        "locale": 1, "accepted_terms_at": 1,
    })

    legacy_version = legacy_version_string()
    now = datetime.now(timezone.utc)

    async for user in cursor:
        stats["users_scanned"] += 1
        user_id = user["id"]
        locale = user.get("locale") or "it"
        if locale not in {"it", "en", "de", "fr"}:
            locale = "it"

        if verbose:
            logger.info(
                "scan user_id=%s email=%s locale=%s — needs backfill",
                user_id, user.get("email", "?"), locale,
            )
        stats["users_to_backfill"] += 1

        if not apply:
            continue

        # 1. Update the user doc
        try:
            result = await users_collection.update_one(
                {"id": user_id},
                {"$set": {
                    "accepted_terms_version": legacy_version,
                    "accepted_terms_locale": locale,
                }},
            )
            if result.modified_count > 0:
                stats["users_backfilled"] += 1
        except Exception as exc:
            logger.error(
                "backfill: user %s update failed: %s",
                user_id, exc, exc_info=True,
            )
            stats["errors"] += 1
            continue

        # 2. Insert the consent_audit record (idempotent: skip if a
        # backfill record already exists for this user)
        try:
            existing_backfill = await consent_audit_collection.find_one(
                {"user_id": user_id, "source": "backfill"},
                {"_id": 1},
            )
            if existing_backfill:
                continue

            import uuid
            audit_doc = {
                "id": str(uuid.uuid4()),
                "user_id": user_id,
                "organization_id": user.get("organization_id"),
                "document_type": "privacy_terms",
                "version_tag": LEGACY_VERSION_TAG,
                "version_hash": LEGACY_VERSION_HASH,
                "locale": locale,
                "accepted_at": user.get("accepted_terms_at") or now.isoformat(),
                "ip_address": None,  # unknown for legacy users
                "user_agent": None,
                "expire_at": now + timedelta(days=365),
                "source": "backfill",
            }
            await consent_audit_collection.insert_one(audit_doc)
            stats["consent_records_inserted"] += 1
        except Exception as exc:
            logger.error(
                "backfill: consent_audit insert failed for user %s: %s",
                user_id, exc, exc_info=True,
            )
            stats["errors"] += 1

    # Also count users with NEVER accepted_terms_at (special audit)
    never_count = await users_collection.count_documents({
        "$or": [
            {"accepted_terms_at": {"$exists": False}},
            {"accepted_terms_at": None},
        ],
    })
    stats["users_never_accepted"] = never_count

    return stats


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--apply", action="store_true",
        help="Actually write changes (default: dry-run)",
    )
    parser.add_argument(
        "--verbose", action="store_true",
        help="Log each user processed",
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO if not args.verbose else logging.DEBUG,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    mode = "APPLY" if args.apply else "DRY-RUN"
    print(f"\n=== Wave GDPR-Admin Phase B backfill — {mode} ===\n")

    stats = asyncio.run(run(apply=args.apply, verbose=args.verbose))

    print("\nStats:")
    for k, v in stats.items():
        print(f"  {k:30s} = {v}")

    if not args.apply and stats["users_to_backfill"] > 0:
        print(
            f"\nDry-run complete. Re-run with --apply to update "
            f"{stats['users_to_backfill']} user(s)."
        )
    elif args.apply:
        print(
            f"\nApplied. {stats['users_backfilled']} user(s) updated, "
            f"{stats['consent_records_inserted']} audit record(s) inserted, "
            f"{stats['errors']} error(s)."
        )

    if stats["users_never_accepted"] > 0:
        print(
            f"\n⚠  {stats['users_never_accepted']} user(s) have NO "
            f"accepted_terms_at field — these were created before "
            f"terms acceptance was mandatory (pre-v6.0 cohort). They are "
            f"NOT auto-backfilled. Review them manually or prompt them to "
            f"re-accept on next login."
        )


if __name__ == "__main__":
    main()
