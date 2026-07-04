#!/usr/bin/env python3
"""
dump_pricing_state.py — Snapshot the complete billing state for diff/rollback.

Captures everything that the new-plans rollout (Ondes 1–9) might change:
    1. All `pricing_plans` (per-module, with their `limits` dict)
    2. All `commercial_plans` (the user-facing bundles + their module_plans
       mapping + Stripe Product/Price IDs)
    3. All organizations' billing-relevant fields (`commercial_plan_slug`,
       `billing_status`, `stripe_subscription_id`, `legacy_pricing_lock`,
       `legacy_price_ids`, etc.)
    4. All active `module_subscriptions`
    5. (Post Onda 3) all active `addon_subscriptions`
    6. Stripe-side: a snapshot of every Stripe Product + Price referenced by
       commercial_plans, fetched live (only if `--include-stripe` is passed
       and STRIPE_SECRET_KEY is set).

USAGE:
    # Snapshot before applying Onda N — write to /tmp:
    ./venv/bin/python scripts/dump_pricing_state.py --output /tmp/pricing_pre_onda1.json

    # Snapshot including live Stripe state (slow, requires API key):
    ./venv/bin/python scripts/dump_pricing_state.py --output /tmp/pricing_full.json --include-stripe

    # Diff two snapshots after applying an onda:
    ./venv/bin/python scripts/dump_pricing_state.py --output /tmp/pricing_post_onda1.json
    diff <(jq -S . /tmp/pricing_pre_onda1.json) <(jq -S . /tmp/pricing_post_onda1.json)

WHY THIS EXISTS:
    Each onda in the new-plans rollout touches `pricing_plans` and/or
    `commercial_plans`. If something goes sideways, we need to know exactly
    what state we left behind. Generic Mongo backups are too coarse and
    don't include the live Stripe Product/Price state.

    This script is the canonical "billing photograph" — run it before AND
    after every onda, store the snapshots, and diff them to verify only the
    intended changes happened.

INVARIANTS:
    * Read-only: never modifies any data.
    * Stable JSON output: keys sorted, deterministic for diffing.
    * Sensitive data (Stripe secret key, internal Mongo URI) NEVER written
      to the snapshot.
    * Output file is plain JSON (UTF-8) — no proprietary format.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

# Resolve backend root.
_BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_BACKEND_DIR))


# ── Helpers ──────────────────────────────────────────────────────────────────

def _serialize(value: Any) -> Any:
    """Make a Mongo document JSON-safe (datetimes → ISO strings, ObjectId → str).

    Keeps the structure deterministic so two snapshots can be diffed line by
    line without false positives from datetime equality differences.
    """
    if isinstance(value, datetime):
        # Always ISO-format with explicit UTC marker for stability.
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return value.isoformat()
    if isinstance(value, dict):
        return {k: _serialize(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_serialize(v) for v in value]
    if hasattr(value, "isoformat"):  # date or other datetime-like
        return value.isoformat()
    return value


async def _dump_pricing_plans() -> List[dict]:
    """Snapshot all pricing_plans (per-module entitlement definitions)."""
    from database import db
    plans = []
    async for doc in db["pricing_plans"].find({}, {"_id": 0}).sort([("module_key", 1), ("sort_order", 1)]):
        plans.append(_serialize(doc))
    return plans


async def _dump_commercial_plans() -> List[dict]:
    """Snapshot all commercial_plans (user-facing bundles + add-ons)."""
    from database import db
    plans = []
    async for doc in db["commercial_plans"].find({}, {"_id": 0}).sort([("sort_order", 1)]):
        plans.append(_serialize(doc))
    return plans


async def _dump_organizations_billing_state() -> List[dict]:
    """Snapshot only the billing-relevant fields per org. Excludes PII like
    `name` and full settings to keep the snapshot focused and shareable."""
    from database import db
    orgs = []
    projection = {
        "_id": 0,
        "id": 1,
        "commercial_plan_slug": 1,
        "billing_status": 1,
        "billing_interval": 1,
        "stripe_customer_id": 1,
        "stripe_subscription_id": 1,
        "trial_ends_at": 1,
        "current_period_end": 1,
        "cancel_at_period_end": 1,
        "plan": 1,                       # legacy
        "plan_assigned_by": 1,
        "legacy_pricing_lock": 1,
        "legacy_pricing_locked_at": 1,
        "legacy_price_ids": 1,
        "is_active": 1,
    }
    async for doc in db["organizations"].find({}, projection).sort([("id", 1)]):
        orgs.append(_serialize(doc))
    return orgs


async def _dump_module_subscriptions() -> List[dict]:
    """Snapshot all module subscriptions (regardless of status — useful for
    audit when an onda removes/cancels some)."""
    from database import db
    subs = []
    async for doc in db["module_subscriptions"].find({}, {"_id": 0}).sort([("organization_id", 1), ("module_key", 1)]):
        subs.append(_serialize(doc))
    return subs


async def _dump_addon_subscriptions() -> List[dict]:
    """Snapshot all add-on subscriptions. Only exists post Onda 3 — empty
    array before that."""
    from database import db
    if "addon_subscriptions" not in await db.list_collection_names():
        return []
    subs = []
    async for doc in db["addon_subscriptions"].find({}, {"_id": 0}).sort([("organization_id", 1), ("addon_slug", 1)]):
        subs.append(_serialize(doc))
    return subs


async def _dump_stripe_products() -> List[dict]:
    """Optionally snapshot live Stripe state for every Product+Price referenced
    by commercial_plans. Requires STRIPE_SECRET_KEY in env."""
    api_key = os.environ.get("STRIPE_SECRET_KEY")
    if not api_key:
        return [{"error": "STRIPE_SECRET_KEY not set — Stripe snapshot skipped"}]

    try:
        import stripe
    except ImportError:
        return [{"error": "stripe package not installed"}]

    stripe.api_key = api_key

    # Collect all Stripe Product/Price IDs referenced in commercial_plans
    from database import db
    product_ids: set[str] = set()
    price_ids: set[str] = set()
    async for plan in db["commercial_plans"].find({}, {"_id": 0, "stripe_product_id": 1, "stripe_price_id_monthly": 1, "stripe_price_id_yearly": 1}):
        if plan.get("stripe_product_id"):
            product_ids.add(plan["stripe_product_id"])
        if plan.get("stripe_price_id_monthly"):
            price_ids.add(plan["stripe_price_id_monthly"])
        if plan.get("stripe_price_id_yearly"):
            price_ids.add(plan["stripe_price_id_yearly"])

    products: List[dict] = []
    for pid in sorted(product_ids):
        try:
            p = await asyncio.to_thread(stripe.Product.retrieve, pid)
            products.append({
                "id": p.get("id"),
                "name": p.get("name"),
                "active": p.get("active"),
                "metadata": dict(p.get("metadata") or {}),
            })
        except Exception as exc:
            products.append({"id": pid, "error": str(exc)})

    prices: List[dict] = []
    for pid in sorted(price_ids):
        try:
            p = await asyncio.to_thread(stripe.Price.retrieve, pid)
            prices.append({
                "id": p.get("id"),
                "active": p.get("active"),
                "currency": p.get("currency"),
                "unit_amount": p.get("unit_amount"),
                "recurring": dict(p.get("recurring") or {}),
                "product": p.get("product"),
            })
        except Exception as exc:
            prices.append({"id": pid, "error": str(exc)})

    return [{"products": products, "prices": prices}]


async def main() -> int:
    parser = argparse.ArgumentParser(
        description="Snapshot complete billing state for diff/rollback.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--output", "-o", required=True, help="Output JSON file path.")
    parser.add_argument(
        "--include-stripe",
        action="store_true",
        help="Also fetch live Stripe Products/Prices (slow, requires STRIPE_SECRET_KEY).",
    )
    args = parser.parse_args()

    output_path = Path(args.output).resolve()
    if output_path.exists():
        print(f"⚠ Output file exists: {output_path}")
        print("  (will be overwritten)")

    print(f"Snapshotting billing state to {output_path}…")
    snapshot: Dict[str, Any] = {
        "schema_version": "v58.0",
        "snapshot_at": datetime.now(timezone.utc).isoformat(),
        "include_stripe": args.include_stripe,
    }

    print("  · pricing_plans…", end=" ", flush=True)
    snapshot["pricing_plans"] = await _dump_pricing_plans()
    print(f"{len(snapshot['pricing_plans'])} docs")

    print("  · commercial_plans…", end=" ", flush=True)
    snapshot["commercial_plans"] = await _dump_commercial_plans()
    print(f"{len(snapshot['commercial_plans'])} docs")

    print("  · organizations (billing fields)…", end=" ", flush=True)
    snapshot["organizations"] = await _dump_organizations_billing_state()
    print(f"{len(snapshot['organizations'])} docs")

    print("  · module_subscriptions…", end=" ", flush=True)
    snapshot["module_subscriptions"] = await _dump_module_subscriptions()
    print(f"{len(snapshot['module_subscriptions'])} docs")

    print("  · addon_subscriptions…", end=" ", flush=True)
    snapshot["addon_subscriptions"] = await _dump_addon_subscriptions()
    print(f"{len(snapshot['addon_subscriptions'])} docs")

    if args.include_stripe:
        print("  · Stripe Products/Prices (LIVE)…", end=" ", flush=True)
        snapshot["stripe"] = await _dump_stripe_products()
        if snapshot["stripe"] and isinstance(snapshot["stripe"][0], dict) and "error" in snapshot["stripe"][0]:
            print(f"{snapshot['stripe'][0]['error']}")
        else:
            stripe_data = snapshot["stripe"][0] if snapshot["stripe"] else {}
            print(f"{len(stripe_data.get('products', []))} products, {len(stripe_data.get('prices', []))} prices")

    # Write deterministic JSON: sorted keys, indented for git-friendly diffs.
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as f:
        json.dump(snapshot, f, indent=2, sort_keys=True, ensure_ascii=False)

    size_kb = output_path.stat().st_size / 1024
    print(f"\nDone. Wrote {size_kb:.1f} KB to {output_path}")
    print(f"Diff against another snapshot with:")
    print(f"  diff <(jq -S . {output_path}) <(jq -S . OTHER_SNAPSHOT.json)")

    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
