#!/usr/bin/env python3
"""
migrate_currency_default.py
============================
CH compliance v1 — Sub-stream 1 — backfill ``currency`` on legacy
organizations so the new validator and immutability check have a
consistent baseline value.

Why:
  Until v1, ``Organization.currency`` was an ``Optional[str]`` defaulting
  to ``None``. Plenty of existing organisations therefore have no
  currency set at all. The new currency policy keeps tolerating ``None``
  on read (it falls back to EUR via ``services.currency_service``), but
  to make the immutability guardrail meaningful we want a concrete value
  on each org doc — otherwise the first PUT after deploy could legally
  switch them to anything because the "existing currency" check sees
  ``None``.

What this script does:
  1. Count organisations with ``currency`` missing or ``None``
  2. In ``--check`` mode (default): just print the counts, no writes
  3. In ``--apply`` mode: set ``currency = "EUR"`` on those organisations
  4. Print a before/after summary

Idempotent. Safe to re-run. Reversible by ``--rollback``, which clears
``currency`` back to ``None`` for organisations that were touched by
this script (identified by a small marker stored in
``settings.ch_compliance.currency_backfilled_at``).

Usage:
    cd backend
    python -m scripts.migrate_currency_default            # dry-run / check (default)
    python -m scripts.migrate_currency_default --apply    # perform writes
    python -m scripts.migrate_currency_default --rollback # undo writes done by this script
"""

import argparse
import asyncio
import sys
from datetime import datetime, timezone
from pathlib import Path

_BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_BACKEND_DIR))


_DEFAULT_CURRENCY = "EUR"
_BACKFILL_MARKER_KEY = "ch_compliance.currency_backfilled_at"


def _missing_currency_filter() -> dict:
    """Match docs where ``currency`` is missing OR null OR empty string."""
    return {
        "$or": [
            {"currency": {"$exists": False}},
            {"currency": None},
            {"currency": ""},
        ]
    }


def _backfilled_filter() -> dict:
    """Match docs that this script has previously written to."""
    return {f"settings.{_BACKFILL_MARKER_KEY}": {"$exists": True}}


async def _counts():
    from database import organizations_collection
    total = await organizations_collection.count_documents({})
    missing = await organizations_collection.count_documents(_missing_currency_filter())
    backfilled = await organizations_collection.count_documents(_backfilled_filter())
    return total, missing, backfilled


async def _check():
    total, missing, backfilled = await _counts()
    print("=" * 70)
    print("organizations.currency — current state")
    print("=" * 70)
    print(f"  total organizations              : {total}")
    print(f"  with missing/null/empty currency : {missing}")
    print(f"  previously backfilled by script  : {backfilled}")
    print()
    if missing == 0:
        print("✅ Nothing to do — every organisation has a currency value.")
    else:
        print(f"⚠ {missing} organisation(s) need backfilling. Run with --apply.")
    return missing


async def _apply():
    from database import organizations_collection

    print("=" * 70)
    print("Applying currency backfill")
    print("=" * 70)
    missing_before = await organizations_collection.count_documents(_missing_currency_filter())
    if missing_before == 0:
        print("✅ Nothing to do — every organisation already has a currency.")
        return 0

    now_iso = datetime.now(timezone.utc).isoformat()
    result = await organizations_collection.update_many(
        _missing_currency_filter(),
        {
            "$set": {
                "currency": _DEFAULT_CURRENCY,
                f"settings.{_BACKFILL_MARKER_KEY}": now_iso,
                "updated_at": now_iso,
            }
        },
    )
    print(f"  matched  : {result.matched_count}")
    print(f"  modified : {result.modified_count}")
    print()
    missing_after = await organizations_collection.count_documents(_missing_currency_filter())
    print(f"  remaining without currency: {missing_after}")
    if missing_after == 0:
        print("✅ Backfill complete.")
        return 0
    print("⚠ Some organisations still without currency. Inspect manually.")
    return 1


async def _rollback():
    from database import organizations_collection

    print("=" * 70)
    print("Rolling back currency backfill (only for docs touched by this script)")
    print("=" * 70)
    target = await organizations_collection.count_documents(_backfilled_filter())
    if target == 0:
        print("✅ Nothing to roll back — no organisation was previously backfilled by this script.")
        return 0

    result = await organizations_collection.update_many(
        _backfilled_filter(),
        {
            "$set": {
                "currency": None,
                "updated_at": datetime.now(timezone.utc).isoformat(),
            },
            "$unset": {
                f"settings.{_BACKFILL_MARKER_KEY}": "",
            },
        },
    )
    print(f"  matched  : {result.matched_count}")
    print(f"  modified : {result.modified_count}")
    print("✅ Rollback complete.")
    return 0


async def _run(args):
    if args.rollback:
        return await _rollback()
    if args.apply:
        return await _apply()
    await _check()
    return 0


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Perform the backfill. Default mode is read-only (--check).",
    )
    parser.add_argument(
        "--rollback",
        action="store_true",
        help="Undo writes performed by a prior --apply run.",
    )
    args = parser.parse_args()
    if args.apply and args.rollback:
        parser.error("--apply and --rollback are mutually exclusive")
    rc = asyncio.run(_run(args))
    sys.exit(rc)


if __name__ == "__main__":
    main()
