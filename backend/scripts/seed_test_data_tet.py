"""
seed_test_data_tet.py
=====================
One-shot seeder to fill the `tet` org with synthetic data up to the
free-plan limits, so the user can test the paywall on the next +1
attempt.

Free plan limits (from PricingPlan tiers):
  · commerce.orders_monthly = 30
  · product_catalog.products = 50

Creates:
  · 5  customers
  · 50 products (varied categories, prices, item_types)
  · 30 orders (each 1-3 line items, mix of statuses)

Uses direct Mongo inserts (bypasses API quota gating). The Pydantic
models validate field types so the docs are well-formed.

Run from backend/ with the venv:
  set -a; source .env; set +a
  ./venv/bin/python -m scripts.seed_test_data_tet
"""

import asyncio
import random
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

# Make backend/ importable when run as script
_BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_BACKEND_DIR))

from database import (  # noqa: E402
    db,
    customers_collection,
    products_collection,
    orders_collection,
    organizations_collection,
    stores_collection,
)

# ── Tet org config ─────────────────────────────────────────────────────────
ORG_ID = "16d64b96-b90f-4705-b6aa-03d279014909"

# ── Realistic seed data (Italian small business themes) ────────────────────
CATEGORIES = [
    "Erbe officinali", "Cosmetici naturali", "Tisane",
    "Oli essenziali", "Saponi artigianali", "Integratori",
]
PRODUCT_NAME_PREFIXES = [
    "Tisana", "Olio", "Crema", "Balsamo", "Sapone",
    "Estratto", "Tintura", "Decotto", "Infuso", "Unguento",
]
PRODUCT_NAME_SUFFIXES = [
    "alla camomilla", "alla lavanda", "al rosmarino", "al timo",
    "alla calendula", "alla salvia", "alla menta", "all'eucalipto",
    "alla malva", "all'arnica", "al ginseng", "alla curcuma",
    "alla valeriana", "alla melissa", "all'echinacea", "al mirtillo",
]
ITEM_TYPES = ["physical", "service"]
ORDER_STATUSES = ["draft", "confirmed", "completed", "cancelled"]
PAYMENT_STATUSES = ["pending", "paid", "refunded"]

# ── Customer fixtures ──────────────────────────────────────────────────────
CUSTOMER_NAMES = [
    ("Maria Rossi",  "maria.rossi@example.it",  "+39 333 1112233"),
    ("Luca Bianchi", "luca.bianchi@example.it", "+39 334 4445566"),
    ("Sara Verdi",   "sara.verdi@example.it",   "+39 335 7778899"),
    ("Paolo Neri",   "paolo.neri@example.it",   "+39 336 1010202"),
    ("Anna Conti",   "anna.conti@example.it",   "+39 337 3030404"),
]


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _generate_id(prefix: str = "") -> str:
    """Match the project's generate_id() pattern (uuid4 hex 32 chars)."""
    import uuid
    suffix = uuid.uuid4().hex
    return f"{prefix}{suffix}" if prefix else suffix


async def seed_customers() -> list[str]:
    """Insert 5 customers, return their IDs."""
    customer_ids = []
    now_iso = _utc_now_iso()
    for name, email, phone in CUSTOMER_NAMES:
        cid = _generate_id()
        await customers_collection.insert_one({
            "id": cid,
            "organization_id": ORG_ID,
            "name": name,
            "email": email,
            "phone": phone,
            "address": None,
            "tags": [],
            "metadata": {},
            "is_active": True,
            "created_at": now_iso,
            "updated_at": now_iso,
        })
        customer_ids.append(cid)
    print(f"  ✓ {len(customer_ids)} customers created")
    return customer_ids


async def seed_products(store_id: str | None) -> list[dict]:
    """Insert 50 products. Returns list of {id, name, unit_price, item_type, sku, category}."""
    products = []
    now_iso = _utc_now_iso()
    for i in range(50):
        prefix = random.choice(PRODUCT_NAME_PREFIXES)
        suffix = random.choice(PRODUCT_NAME_SUFFIXES)
        name = f"{prefix} {suffix}"
        category = random.choice(CATEGORIES)
        item_type = random.choice(ITEM_TYPES)
        unit_price = round(random.uniform(8, 95), 2)
        cost_price = round(unit_price * random.uniform(0.3, 0.6), 2)
        sku = f"SKU-{i+1:04d}"
        pid = _generate_id()

        await products_collection.insert_one({
            "id": pid,
            "organization_id": ORG_ID,
            "name": name,
            "sku": sku,
            "category": category,
            "unit_price": unit_price,
            "cost_price": cost_price,
            "unit": "pz" if item_type == "physical" else "servizio",
            "description": f"{name} — prodotto demo per test",
            "image_url": None,
            "slug": None,
            "is_published": True,
            "item_type": item_type,
            "unit_label": "pz" if item_type == "physical" else "servizio",
            "price_mode": "fixed",
            "transaction_mode": "request",
            "stock_quantity": random.randint(5, 100) if item_type == "physical" else None,
            "tags": [],
            "metadata": {},
            "store_ids": [store_id] if store_id else [],
            "is_active": True,
            "created_at": now_iso,
            "updated_at": now_iso,
        })
        products.append({
            "id": pid,
            "name": name,
            "unit_price": unit_price,
            "item_type": item_type,
            "sku": sku,
            "category": category,
        })
    print(f"  ✓ {len(products)} products created")
    return products


async def seed_orders(customer_ids: list[str], products: list[dict]) -> int:
    """Insert 30 orders, each with 1-3 line items."""
    if not customer_ids or not products:
        print("  ✗ Need customers AND products before seeding orders")
        return 0

    # Build a customer_id → name lookup for the orders
    customer_lookup = {}
    cursor = customers_collection.find({"organization_id": ORG_ID}, {"_id": 0, "id": 1, "name": 1, "email": 1, "phone": 1})
    async for c in cursor:
        customer_lookup[c["id"]] = c

    # Onda 18 — `created_at` MUST always reflect the actual system insert
    # time (i.e. now), because the orders_monthly quota gate counts by
    # `created_at >= start_of_current_month`. If we backdated created_at
    # to last month, those orders would not count toward the quota — the
    # opposite of what a realistic seed should do.
    #
    # `order_date` (business date) CAN be in the past — that mirrors the
    # real product behaviour where an admin can record a back-dated
    # invoice/order with today's insert timestamp. The two timestamps
    # are intentionally decoupled.
    now_dt = datetime.now(timezone.utc)
    now_iso_orders = now_dt.isoformat()
    created = 0
    for i in range(30):
        # Business order_date can be up to 30 days in the past (varied
        # for visual realism — e.g. dashboards showing last month's data).
        days_ago = random.randint(0, 30)
        order_dt = now_dt - timedelta(days=days_ago)
        # NOTE: order_iso is used ONLY for `order_date`, NOT created_at.

        cid = random.choice(customer_ids)
        cust = customer_lookup.get(cid, {})
        # 1-3 line items
        n_lines = random.randint(1, 3)
        chosen_products = random.sample(products, n_lines)
        items = []
        subtotal = 0.0
        for p in chosen_products:
            qty = random.randint(1, 4)
            unit_price = p["unit_price"]
            line_total = round(qty * unit_price, 2)
            subtotal += line_total
            items.append({
                "product_id": p["id"],
                "product_name": p["name"],
                "sku": p["sku"],
                "category": p["category"],
                "item_type": p["item_type"],
                "transaction_mode": "request",
                "quantity": qty,
                "unit_price": unit_price,
                "discount_pct": 0,
                "line_total": line_total,
                "extras": [],
                "extras_total": 0.0,
            })

        status = random.choices(
            ORDER_STATUSES,
            weights=[2, 3, 4, 1],  # mostly confirmed/completed
        )[0]
        payment_status = "paid" if status == "completed" else random.choice(PAYMENT_STATUSES)

        oid = _generate_id()
        order_number = f"ORD-{i+1:04d}"
        await orders_collection.insert_one({
            "id": oid,
            "organization_id": ORG_ID,
            "order_number": order_number,
            "customer_id": cid,
            "customer_name": cust.get("name"),
            "customer_email": cust.get("email"),
            "currency": "EUR",
            "notes": None,
            "due_date": None,
            "order_date": order_dt.date().isoformat(),
            "status": status,
            "payment_status": payment_status,
            "payment_intent": "none",
            "payment_checkout": None,
            "items": items,
            "subtotal": round(subtotal, 2),
            "total": round(subtotal, 2),
            "source": "manual",
            "customer_account_id": None,
            "fulfillment": None,
            "contact_phone": cust.get("phone"),
            "coupon_code": None,
            "discount_total": 0,
            "order_fields_data": {},
            "terms_accepted_at": None,
            # Onda 18 — created_at is now (system insert), NOT order_dt
            "created_at": now_iso_orders,
            "updated_at": now_iso_orders,
        })
        created += 1
    print(f"  ✓ {created} orders created")
    return created


async def main():
    org = await organizations_collection.find_one({"id": ORG_ID})
    if not org:
        print(f"✗ Org {ORG_ID} not found")
        return
    print(f"Seeding org: name={org['name']} plan={org['commercial_plan_slug']}")

    # Use the existing default store if present (products optionally tagged with it)
    store = await stores_collection.find_one(
        {"organization_id": ORG_ID, "is_default": True},
        {"_id": 0, "id": 1, "name": 1},
    )
    store_id = store["id"] if store else None
    if store:
        print(f"  Using default store: {store['name']} ({store_id[:8]}...)")
    else:
        print("  No default store — products created with empty store_ids")

    customer_ids = await seed_customers()
    products = await seed_products(store_id)
    await seed_orders(customer_ids, products)

    # Final counts
    print("\n=== FINAL COUNTS ===")
    for c in ("customers", "products", "orders"):
        n = await db[c].count_documents({"organization_id": ORG_ID})
        print(f"  {c}: {n}")

    print("\nFREE PLAN LIMITS REACHED — next attempt to:")
    print("  • Create a 51st product → 429 QUOTA_EXCEEDED (product_catalog.products=50)")
    print("  • Create a 31st order   → 429 QUOTA_EXCEEDED (commerce.orders_monthly=30)")


if __name__ == "__main__":
    asyncio.run(main())
