#!/usr/bin/env python3
"""
migrate_cost_price_to_components.py
====================================
Wave 1 — W1.S1 — one-shot migration that converts the legacy
``Product.cost_price`` scalar into a single ``manual`` component on the
new ``Product.cost_source`` container.

Why:
  Wave 1 introduces additive cost composition (``cost_source.components``)
  as the authoritative source for margin calculation. Existing products
  carry their unit cost in the legacy ``cost_price`` field. Before the
  new resolver, the new admin UI, and the cost_at_sale snapshot
  (W1.S6) go live, we need every existing non-zero ``cost_price`` to be
  materialised as a ``manual`` component so the new pipeline finds the
  user's intent intact on day one.

What this script does:
  1. Count products in three buckets:
       - have a non-zero ``cost_price`` AND no ``cost_source.components``
         → these MUST be migrated
       - already have ``cost_source.components`` populated
         → leave them alone (idempotent re-run)
       - have ``cost_price`` null/zero AND no ``cost_source``
         → nothing to migrate; the merchant simply never set a cost
  2. In ``--check`` mode (default): print the counts, no writes.
  3. In ``--apply`` mode: for each product in bucket 1, write
       cost_source = {
           method: "wac_90d",                # safe default; admin can change
           components: [
               {
                   type: "manual",
                   label: "Costo prodotto",   # i18n-friendly placeholder
                   manual_value: <cost_price>
               }
           ]
       }
     The ``cost_price`` field itself is preserved (NOT cleared) — the
     deprecation is announced in code, the field stays in the schema
     during Wave 1 to avoid breaking any reader we haven't audited yet.
     The cleanup commit at the end of Wave 1 (after all UIs migrate to
     ``cost_source``) will drop the field.

Marker:
  Each migrated product gets ``cost_source._migration_marker.from_cost_price_at``
  set to the ISO timestamp so ``--rollback`` can identify exactly the
  products this script touched and revert them — never products an
  admin has since edited via the new UI.

Idempotent. Safe to re-run.

Usage:
    cd backend
    python -m scripts.migrate_cost_price_to_components             # dry-run / check
    python -m scripts.migrate_cost_price_to_components --apply     # perform writes
    python -m scripts.migrate_cost_price_to_components --rollback  # undo prior --apply
"""

import argparse
import asyncio
import sys
from datetime import datetime, timezone
from pathlib import Path

_BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_BACKEND_DIR))


# ── Constants ────────────────────────────────────────────────────────────────
# These literals must stay in sync with:
#   - models/cost_source.py    (CostSource / CostComponent)
#   - the rollback marker on each migrated doc
# Lifted out here so the migration intent is documented in one place.

_DEFAULT_METHOD = "wac_90d"
_MIGRATED_LABEL = "Costo prodotto"      # English: "Product cost"
_MARKER_KEY = "_migration_marker.from_cost_price_at"


def _needs_migration_filter() -> dict:
    """Products that carry a usable legacy ``cost_price`` and have not yet
    been moved over.

    "Usable" means:
      - field exists AND is a number AND is greater than zero
      (a stored 0 is indistinguishable from "I never set this", we don't
      manufacture a €0 component just because the field has been touched).

    "Not yet moved over" means EITHER:
      - ``cost_source`` is missing entirely, OR
      - ``cost_source.components`` is missing or empty
      (someone may have a ``cost_source`` with method set but zero
      components — still effectively unconfigured)
    """
    return {
        "$and": [
            {"cost_price": {"$exists": True, "$ne": None, "$gt": 0}},
            {
                "$or": [
                    {"cost_source": {"$exists": False}},
                    {"cost_source": None},
                    {"cost_source.components": {"$exists": False}},
                    {"cost_source.components": []},
                ]
            },
        ]
    }


def _already_migrated_filter() -> dict:
    """Products this script has written to (carry the rollback marker)."""
    return {f"cost_source.{_MARKER_KEY}": {"$exists": True}}


def _has_cost_source_filter() -> dict:
    """Products with any non-empty cost_source.components (regardless of
    whether they came from this script or from the admin UI)."""
    return {
        "cost_source.components.0": {"$exists": True},
    }


async def _counts():
    from database import products_collection

    total = await products_collection.count_documents({})
    needs = await products_collection.count_documents(_needs_migration_filter())
    migrated_by_script = await products_collection.count_documents(
        _already_migrated_filter()
    )
    have_cost_source = await products_collection.count_documents(
        _has_cost_source_filter()
    )
    have_cost_price = await products_collection.count_documents(
        {"cost_price": {"$exists": True, "$ne": None, "$gt": 0}}
    )
    return {
        "total": total,
        "needs_migration": needs,
        "migrated_by_script": migrated_by_script,
        "have_cost_source": have_cost_source,
        "have_cost_price": have_cost_price,
    }


def _print_counts(c: dict) -> None:
    print("=" * 70)
    print("products — cost_price → cost_source migration state")
    print("=" * 70)
    print(f"  total products                            : {c['total']}")
    print(f"  with non-zero cost_price                  : {c['have_cost_price']}")
    print(f"  with any cost_source.components populated : {c['have_cost_source']}")
    print(f"  previously migrated by this script        : {c['migrated_by_script']}")
    print(f"  NEED MIGRATION (cost_price set, no source): {c['needs_migration']}")
    print()


async def _check() -> int:
    c = await _counts()
    _print_counts(c)
    if c["needs_migration"] == 0:
        print("✅ Nothing to do.")
        return 0
    print(f"⚠ {c['needs_migration']} product(s) ready to migrate. Run with --apply.")
    return 0


async def _apply() -> int:
    from database import products_collection

    print("=" * 70)
    print("Applying cost_price → cost_source migration")
    print("=" * 70)

    c_before = await _counts()
    _print_counts(c_before)

    if c_before["needs_migration"] == 0:
        print("✅ Nothing to do — every product is already migrated or has no cost_price.")
        return 0

    now_iso = datetime.now(timezone.utc).isoformat()

    # Stream the matching docs and write per-doc because each product
    # needs a different ``manual_value`` (its own cost_price). A bulk
    # ``update_many`` cannot express "use the doc's existing field as the
    # new component value", so a cursor + individual updates is the
    # honest approach. With merchant orgs in the low thousands of products
    # this is well under a second of work.
    cursor = products_collection.find(
        _needs_migration_filter(),
        {"_id": 0, "id": 1, "cost_price": 1, "cost_source": 1},
    )

    matched = 0
    modified = 0
    async for prod in cursor:
        matched += 1
        cost_price = prod.get("cost_price")
        # Defensive: filter guaranteed > 0, but during a long-running
        # migration the doc could have been edited in flight.
        if not isinstance(cost_price, (int, float)) or cost_price <= 0:
            continue

        # Preserve any existing cost_source.method the admin may have set
        # via API before this migration ran. Default to wac_90d otherwise.
        existing_source = prod.get("cost_source") or {}
        method = existing_source.get("method") or _DEFAULT_METHOD

        new_source = {
            "method": method,
            "components": [
                {
                    "type": "manual",
                    "label": _MIGRATED_LABEL,
                    "manual_value": float(cost_price),
                }
            ],
            # Marker enables a precise --rollback later without touching
            # products the admin has since edited via the new UI.
            "_migration_marker": {
                "from_cost_price_at": now_iso,
                "from_cost_price_value": float(cost_price),
            },
        }

        result = await products_collection.update_one(
            {"id": prod["id"]},
            {
                "$set": {
                    "cost_source": new_source,
                    "updated_at": now_iso,
                }
            },
        )
        modified += result.modified_count

    print(f"  matched products : {matched}")
    print(f"  modified products: {modified}")
    print()

    c_after = await _counts()
    _print_counts(c_after)

    if c_after["needs_migration"] == 0:
        print("✅ Migration complete.")
        return 0
    print(f"⚠ {c_after['needs_migration']} product(s) still pending. Inspect manually.")
    return 1


async def _rollback() -> int:
    from database import products_collection

    print("=" * 70)
    print("Rolling back cost_price → cost_source migration")
    print("(only for products touched by this script — admin edits preserved)")
    print("=" * 70)

    target = await products_collection.count_documents(_already_migrated_filter())
    if target == 0:
        print("✅ Nothing to roll back — no product was previously migrated by this script.")
        return 0

    print(f"  rolling back {target} product(s)...")
    now_iso = datetime.now(timezone.utc).isoformat()

    # Restore: drop the entire cost_source we wrote (the admin can
    # re-edit; the original cost_price is still intact on the doc).
    result = await products_collection.update_many(
        _already_migrated_filter(),
        {
            "$unset": {"cost_source": ""},
            "$set": {"updated_at": now_iso},
        },
    )
    print(f"  matched  : {result.matched_count}")
    print(f"  modified : {result.modified_count}")
    print("✅ Rollback complete.")
    return 0


async def _run(args) -> int:
    if args.rollback:
        return await _rollback()
    if args.apply:
        return await _apply()
    return await _check()


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Perform the migration. Default mode is read-only (--check).",
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
