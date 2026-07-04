#!/usr/bin/env python3
"""
backfill_grandfather_email_verified.py
=======================================
Onda 28 Step 3 — grandfather existing users so they aren't locked out
when the new email-verification gate (Onda 28 Step 1+2) goes live.

Why
---
Before Onda 28, `email_verified` was set on users but never enforced
anywhere except at login (which itself only blocks non-system_admin).
Users who somehow obtained a valid JWT without verifying email could
still use the app via existing tokens. After Onda 28 Step 2, the new
`get_verified_user` dependency rejects ALL non-whitelist requests
from users with email_verified != true.

Without this script, every user_doc currently in prod with
`email_verified: false` (or missing) would be locked out of the app at
the next deploy. We grandfather them by flipping the flag to true,
under the assumption that they were active before mandatory
verification became policy and we don't want to disrupt them.

Filter — who gets grandfathered
-------------------------------
Users matching ALL of:
  · is_active == true
  · email_verified != true (i.e. false OR missing)
  · created_at < CUTOFF (default: 2026-05-07T00:00:00Z — the day
    Onda 28 went live; configurable via --before-date)

Users created on or after CUTOFF are NEW signups (post-Onda 28 era)
and MUST verify the normal way — they are NOT grandfathered.

What this script does
---------------------
For each matching user, it sets:
  · email_verified = true
  · _grandfathered_at = now()  (ISO UTC)
  · _grandfather_reason = "pre-onda28-existing-user"

The two underscore-prefixed fields are audit metadata — they let
operators (and future scripts) tell which `email_verified=true`
values came from a real verification flow vs from this backfill.

A row in the `audit_logs` collection is also written per user.

Idempotent: re-running is safe — already-grandfathered users are
filtered out (they have email_verified=true).

Reversible: `--rollback` flag walks the same set (matched by
_grandfather_reason) and reverts. Lets us undo the backfill if
something goes wrong.

Usage
-----
    cd backend
    # Dry-run (default)
    python -m scripts.backfill_grandfather_email_verified

    # Apply
    python -m scripts.backfill_grandfather_email_verified --apply

    # Custom cutoff (rare)
    python -m scripts.backfill_grandfather_email_verified --before-date 2026-05-01T00:00:00Z --apply

    # Rollback (undo a previous --apply)
    python -m scripts.backfill_grandfather_email_verified --rollback --apply
"""

import argparse
import asyncio
import sys
from datetime import datetime, timezone
from pathlib import Path

_BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_BACKEND_DIR))


_DEFAULT_CUTOFF_ISO = "2026-05-07T00:00:00+00:00"
_GRANDFATHER_REASON = "pre-onda28-existing-user"


def _now_iso():
    return datetime.now(timezone.utc).isoformat()


async def _count_targets(cutoff_iso: str) -> int:
    """Count users that are eligible for grandfathering."""
    from database import users_collection
    return await users_collection.count_documents({
        "is_active": True,
        "$or": [
            {"email_verified": {"$ne": True}},
            {"email_verified": {"$exists": False}},
        ],
        "created_at": {"$lt": cutoff_iso},
    })


async def _list_targets(cutoff_iso: str, limit: int = 50) -> list[dict]:
    """Return a sample of target user docs (for the dry-run report)."""
    from database import users_collection
    cursor = users_collection.find(
        {
            "is_active": True,
            "$or": [
                {"email_verified": {"$ne": True}},
                {"email_verified": {"$exists": False}},
            ],
            "created_at": {"$lt": cutoff_iso},
        },
        {"_id": 0, "id": 1, "email": 1, "role": 1, "created_at": 1,
         "email_verified": 1, "organization_id": 1},
    ).limit(limit)
    return [doc async for doc in cursor]


async def _apply_grandfather(cutoff_iso: str) -> dict:
    """Apply the grandfather flag and return counters."""
    from database import users_collection, audit_logs_collection
    from models.common import generate_id

    now = _now_iso()
    targets = await _list_targets(cutoff_iso, limit=10_000)

    if not targets:
        return {"matched": 0, "modified": 0}

    # Bulk update
    target_ids = [t["id"] for t in targets]
    res = await users_collection.update_many(
        {"id": {"$in": target_ids}},
        {"$set": {
            "email_verified": True,
            "_grandfathered_at": now,
            "_grandfather_reason": _GRANDFATHER_REASON,
        }},
    )

    # Audit log per user (best-effort)
    audit_docs = []
    for t in targets:
        audit_docs.append({
            "id": generate_id(),
            "actor_user_id": "system",
            "actor_role": "system",
            "organization_id": t.get("organization_id"),
            "action": "USER_GRANDFATHERED_EMAIL_VERIFIED",
            "target_type": "user",
            "target_id": t["id"],
            "metadata": {
                "email": t.get("email"),
                "previous_email_verified": t.get("email_verified", None),
                "reason": _GRANDFATHER_REASON,
                "cutoff_iso": cutoff_iso,
            },
            "created_at": now,
        })
    if audit_docs:
        try:
            await audit_logs_collection.insert_many(audit_docs)
        except Exception as e:
            print(f"  ⚠ audit log insert failed (non-fatal): {e}")

    return {
        "matched": res.matched_count,
        "modified": res.modified_count,
        "audited": len(audit_docs),
    }


async def _rollback() -> dict:
    """Reverse a previous grandfather pass.

    Walks all users with `_grandfather_reason == _GRANDFATHER_REASON`
    and:
      · sets email_verified = false (back to the unverified state)
      · $unset _grandfathered_at + _grandfather_reason
      · audit log entry of the rollback

    Returns counters.
    """
    from database import users_collection, audit_logs_collection
    from models.common import generate_id

    now = _now_iso()

    # Snapshot for audit before mutating
    cursor = users_collection.find(
        {"_grandfather_reason": _GRANDFATHER_REASON},
        {"_id": 0, "id": 1, "email": 1, "organization_id": 1,
         "_grandfathered_at": 1},
    )
    targets = [doc async for doc in cursor]

    if not targets:
        return {"matched": 0, "modified": 0}

    target_ids = [t["id"] for t in targets]
    res = await users_collection.update_many(
        {"id": {"$in": target_ids}},
        {
            "$set": {"email_verified": False},
            "$unset": {"_grandfathered_at": "", "_grandfather_reason": ""},
        },
    )

    audit_docs = []
    for t in targets:
        audit_docs.append({
            "id": generate_id(),
            "actor_user_id": "system",
            "actor_role": "system",
            "organization_id": t.get("organization_id"),
            "action": "USER_GRANDFATHER_ROLLED_BACK",
            "target_type": "user",
            "target_id": t["id"],
            "metadata": {
                "email": t.get("email"),
                "rolled_back_grandfathered_at": t.get("_grandfathered_at"),
            },
            "created_at": now,
        })
    if audit_docs:
        try:
            await audit_logs_collection.insert_many(audit_docs)
        except Exception:
            pass

    return {
        "matched": res.matched_count,
        "modified": res.modified_count,
        "audited": len(audit_docs),
    }


async def main(args):
    print("=" * 70)
    print(f"BACKFILL — grandfather email_verified for pre-Onda 28 users")
    print(f"  cutoff: {args.before_date}")
    print(f"  mode:   {'ROLLBACK' if args.rollback else 'APPLY' if args.apply else 'DRY-RUN'}")
    print("=" * 70)
    print()

    if args.rollback:
        # Rollback flow
        from database import users_collection
        affected_count = await users_collection.count_documents(
            {"_grandfather_reason": _GRANDFATHER_REASON},
        )
        print(f"  Rollback would affect {affected_count} user(s) "
              f"(those previously grandfathered).")
        if not args.apply:
            print("\n  DRY-RUN: re-run with --rollback --apply to execute.")
            return 0
        print("\n  Applying rollback...")
        counters = await _rollback()
        print(f"    matched={counters['matched']}  "
              f"modified={counters['modified']}  "
              f"audited={counters.get('audited', 0)}")
        print("\n✅ Rollback complete.")
        return 0

    # Forward flow (apply or dry-run)
    cutoff_iso = args.before_date
    target_count = await _count_targets(cutoff_iso)
    sample = await _list_targets(cutoff_iso, limit=20)

    print(f"  Found {target_count} user(s) eligible for grandfathering.")
    print()
    if sample:
        print("  Sample (up to 20):")
        for t in sample:
            print(f"    · {t.get('email', '?'):40s} "
                  f"role={t.get('role', '?'):14s} "
                  f"created={t.get('created_at', '?')[:10]:10s} "
                  f"email_verified={t.get('email_verified', 'MISSING')}")
        print()

    if target_count == 0:
        print("✅ Nothing to do — no eligible users found.")
        return 0

    if not args.apply:
        print("DRY-RUN: re-run with --apply to grandfather these users.")
        return 0

    print("Applying grandfather flag...")
    counters = await _apply_grandfather(cutoff_iso)
    print(f"  matched={counters['matched']}  "
          f"modified={counters['modified']}  "
          f"audited={counters.get('audited', 0)}")
    print()

    # Verify post-condition
    remaining = await _count_targets(cutoff_iso)
    if remaining == 0:
        print("✅ Backfill complete. All eligible users now have email_verified=true.")
        return 0
    else:
        print(f"⚠ {remaining} user(s) still match the filter — investigate.")
        return 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Execute changes (default: dry-run)",
    )
    parser.add_argument(
        "--rollback",
        action="store_true",
        help="Reverse a previous grandfather pass "
             "(walks _grandfather_reason marker)",
    )
    parser.add_argument(
        "--before-date",
        default=_DEFAULT_CUTOFF_ISO,
        help=f"ISO UTC cutoff date — only users created BEFORE this "
             f"are eligible. Default: {_DEFAULT_CUTOFF_ISO}",
    )
    args = parser.parse_args()

    if args.rollback and args.apply is False:
        print("(Rollback dry-run mode — nothing will change. Add --apply to execute.)")
        print()

    sys.exit(asyncio.run(main(args)))
