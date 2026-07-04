"""
audit_addon_consistency.py
==========================
Onda 24 Phase G — drift detection between AddonSubscription rows in
the AFianco DB and the actual addon items inside the org's Stripe
subscription.

Mirrors the spirit of audit_billing_consistency.py but scoped to
addons. Read-only by default; --fix uses
billing_repository.reconcile_addons_with_stripe_items to converge
state to Stripe truth.

Detects:
  · DB-only orphans   (AddonSubscription active, no Stripe item)
  · Stripe-only       (Stripe item with metadata.is_addon=true, no DB row)
  · Quantity mismatch (DB.quantity ≠ Stripe item.quantity)
  · Price mismatch    (DB.stripe_price_id ≠ Stripe item.price.id)

Usage:
  cd backend && set -a; source .env; set +a
  ./venv/bin/python -m scripts.audit_addon_consistency --dry-run
  ./venv/bin/python -m scripts.audit_addon_consistency --fix
"""

import argparse
import asyncio
import os
import sys
from pathlib import Path

_BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_BACKEND_DIR))


def _setup_stripe():
    import stripe
    stripe.api_key = os.environ.get("STRIPE_SECRET_KEY", "").strip()
    return stripe


async def _fetch_stripe_addon_items(stripe, sub_id: str) -> list[dict]:
    """Return [{slug, item_id, price_id, quantity}, ...] from Stripe."""
    try:
        sub = stripe.Subscription.retrieve(sub_id, expand=["items"])
    except Exception:
        return []
    out = []
    for it in (sub.get("items") or {}).get("data", []) or []:
        md = it.get("metadata") if hasattr(it, "get") else getattr(it, "metadata", None) or {}
        if not isinstance(md, dict):
            try:
                md = dict(md)
            except Exception:
                md = {}
        if md.get("is_addon") != "true":
            continue
        slug = md.get("addon_slug")
        if not slug:
            continue
        item_id = it.get("id") if hasattr(it, "get") else getattr(it, "id", None)
        price = it.get("price") if hasattr(it, "get") else getattr(it, "price", None)
        price_id = (price.get("id") if hasattr(price, "get") else getattr(price, "id", None)) if price else None
        qty = it.get("quantity") if hasattr(it, "get") else getattr(it, "quantity", 1)
        out.append({
            "slug": slug,
            "item_id": item_id,
            "price_id": price_id,
            "quantity": int(qty or 1),
        })
    return out


async def main(dry_run: bool, fix: bool) -> int:
    print(f"{'FIX' if fix else 'DRY-RUN'} — Onda 24 Phase G addon consistency audit")
    print("=" * 78)

    from database import organizations_collection, addon_subscriptions_collection
    stripe = _setup_stripe()

    cursor = organizations_collection.find(
        {
            "stripe_subscription_id": {"$nin": [None, ""]},
            "is_active": {"$ne": False},
        },
        {"_id": 0, "id": 1, "name": 1, "stripe_subscription_id": 1},
    )
    orgs = await cursor.to_list(10000)

    total_drift = 0
    fixed_orgs = 0
    for org in orgs:
        org_id = org["id"]
        sub_id = org["stripe_subscription_id"]

        # DB side
        db_cursor = addon_subscriptions_collection.find(
            {"organization_id": org_id, "status": "active"},
            {"_id": 0, "addon_slug": 1, "stripe_subscription_item_id": 1,
             "stripe_price_id": 1, "quantity": 1},
        )
        db_addons = {a["addon_slug"]: a async for a in db_cursor}

        # Stripe side
        stripe_addons_list = await _fetch_stripe_addon_items(stripe, sub_id)
        stripe_addons = {a["slug"]: a for a in stripe_addons_list}

        issues = []

        # DB-only orphans
        for slug in db_addons.keys() - stripe_addons.keys():
            issues.append(("db_only", slug))

        # Stripe-only items not in DB
        for slug in stripe_addons.keys() - db_addons.keys():
            issues.append(("stripe_only", slug))

        # Both: check quantity / price_id match
        for slug in db_addons.keys() & stripe_addons.keys():
            db_a = db_addons[slug]
            st_a = stripe_addons[slug]
            if db_a.get("quantity") != st_a.get("quantity"):
                issues.append(("quantity_mismatch", slug, db_a.get("quantity"), st_a.get("quantity")))
            if db_a.get("stripe_price_id") and db_a["stripe_price_id"] != st_a["price_id"]:
                issues.append(("price_mismatch", slug, db_a["stripe_price_id"], st_a["price_id"]))

        if not issues:
            continue

        total_drift += len(issues)
        print(f"\n  ⚠ {org['name']} (org={org_id[:8]}…) sub={sub_id}")
        for issue in issues:
            print(f"      {issue}")

        if fix and not dry_run:
            from repositories import billing_repository
            counters = await billing_repository.reconcile_addons_with_stripe_items(
                organization_id=org_id,
                stripe_subscription_id=sub_id,
                addon_items_from_stripe=[
                    {
                        "slug": s["slug"],
                        "stripe_subscription_item_id": s["item_id"],
                        "stripe_price_id": s["price_id"],
                        "quantity": s["quantity"],
                    }
                    for s in stripe_addons_list
                ],
            )
            fixed_orgs += 1
            print(f"      → reconciled: upserted={counters.get('upserted', 0)} cancelled={counters.get('cancelled', 0)}")

    print()
    print("─" * 78)
    if total_drift == 0:
        print("  ✓ No addon drift detected. Invariant holds across all orgs.")
    else:
        print(f"  Total drift issues: {total_drift}")
        if fix:
            print(f"  Reconciled orgs:    {fixed_orgs}")
        else:
            print("  Run with --fix to reconcile via reconcile_addons_with_stripe_items")
    print("─" * 78)
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", default=True)
    parser.add_argument("--fix", action="store_true",
                        help="Reconcile DB to Stripe (writes to addon_subscriptions)")
    args = parser.parse_args()
    sys.exit(asyncio.run(main(
        dry_run=not args.fix,
        fix=args.fix,
    )))
