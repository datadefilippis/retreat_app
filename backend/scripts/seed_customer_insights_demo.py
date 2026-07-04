"""Seed Customer Insights demo dataset.

Creates ~20 customers with **deliberately diverse** histories so the
new /modules/customer-insights page exercises every code path:

  • Multiple segments visible (top, active, occasional, inactive, new)
  • Multiple statuses visible (healthy, watch, at_risk, lost)
  • Period filter has data in 30d, 90d, 12m, all-time windows
  • Concentration math has top performers (top 5/top 10 share > 0)
  • Drill-downs from KPI cards yield non-empty tables
  • Some customers have email, some phone, some neither (filter test)
  • Trend direction split: growing / declining / stable / new

Idempotent: re-running wipes the demo customers + their sales by
``demo_seed`` metadata flag and re-inserts them. Real customers and
sales for the org are untouched.

USAGE
-----
    cd backend
    set -a; source .env; set +a
    ./venv/bin/python -m scripts.seed_customer_insights_demo

    # Then refresh the materialized customer_metrics:
    curl -X POST -H "Authorization: Bearer <admin_token>" \\
        http://localhost:8000/api/modules/customers_light/refresh

    # Or the script does it for you (requires the legacy refresh
    # function which is async-safe to call directly).

OUTPUT
------
    Creates ~20 customers + ~150 sales_records + 5-8 orders, then runs
    the legacy refresh_customer_metrics so the new Insights page sees
    populated data immediately. Prints a summary of what's seeded.
"""

import asyncio
import random
import sys
import uuid
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

# Make backend/ importable
_BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_BACKEND_DIR))


# ── Org targets ────────────────────────────────────────────────────────
# Default to the dev "tet" org. Override via CLI arg (--org-id <uuid>).

DEFAULT_ORG_ID = "16d64b96-b90f-4705-b6aa-03d279014909"


# ── Customer personas ──────────────────────────────────────────────────
#
# Each persona spec produces customer + N sales_records with a specific
# history shape. We control segment / status / risk by tuning:
#   purchases_count, days_ago_first, days_ago_last, avg_amount.
#
# Targeted segment distribution (after refresh):
#   ~3 top      (high revenue, recent + frequent)
#   ~4 active   (recent, moderate revenue)
#   ~3 occasional (purchase 90-180d ago)
#   ~4 inactive (last purchase > 200d ago)
#   ~3 new      (first purchase ≤ 30d ago)
#   ~3 at-risk  (single purchase OR large gap → high churn score)


PERSONAS = [
    # ── TOP customers (rank ≤ top 10 %, recent, frequent) ────────────
    {
        "name": "Anna Bianchi",
        "email": "anna.bianchi@example.test",
        "phone": "+41 79 123 45 01",
        "purchases": 18,        # high frequency
        "days_first": 540,      # 18 months ago
        "days_last": 5,         # last week
        "avg_amount": 280,
        "spread_pct": 0.30,
        "tag": "vip",
    },
    {
        "name": "Marco Rossi",
        "email": "marco.rossi@example.test",
        "phone": "+41 79 123 45 02",
        "purchases": 14,
        "days_first": 420,
        "days_last": 12,
        "avg_amount": 350,
        "spread_pct": 0.25,
        "tag": "vip",
    },
    {
        "name": "Studio Luca SA",
        "email": "info@studioluca.test",
        "phone": "+41 91 555 12 34",
        "purchases": 12,
        "days_first": 380,
        "days_last": 18,
        "avg_amount": 420,
        "spread_pct": 0.20,
        "tag": "b2b",
    },

    # ── ACTIVE customers (recent, moderate frequency) ────────────────
    {
        "name": "Sara Müller",
        "email": "sara.mueller@example.test",
        "phone": "+41 79 234 56 78",
        "purchases": 8,
        "days_first": 200,
        "days_last": 14,
        "avg_amount": 95,
        "spread_pct": 0.40,
        "tag": "regular",
    },
    {
        "name": "Giulia Pellegrini",
        "email": "giulia.p@example.test",
        "phone": None,  # no phone → tests has_phone filter
        "purchases": 6,
        "days_first": 160,
        "days_last": 22,
        "avg_amount": 110,
        "spread_pct": 0.30,
        "tag": "regular",
    },
    {
        "name": "Davide Conti",
        "email": None,  # no email → tests has_email filter
        "phone": "+41 79 345 67 89",
        "purchases": 7,
        "days_first": 220,
        "days_last": 30,
        "avg_amount": 75,
        "spread_pct": 0.50,
        "tag": "regular",
    },
    {
        "name": "Café Lugano Centro",
        "email": "amministrazione@cafelugano.test",
        "phone": "+41 91 922 33 44",
        "purchases": 9,
        "days_first": 250,
        "days_last": 45,
        "avg_amount": 130,
        "spread_pct": 0.20,
        "tag": "b2b",
    },

    # ── OCCASIONAL customers (last purchase 60-180d ago) ─────────────
    {
        "name": "Roberto Gilardi",
        "email": "r.gilardi@example.test",
        "phone": "+41 79 456 78 90",
        "purchases": 4,
        "days_first": 320,
        "days_last": 95,
        "avg_amount": 60,
        "spread_pct": 0.40,
        "tag": "regular",
    },
    {
        "name": "Elena Schmid",
        "email": "elena.schmid@example.test",
        "phone": None,
        "purchases": 3,
        "days_first": 280,
        "days_last": 130,
        "avg_amount": 85,
        "spread_pct": 0.30,
        "tag": "regular",
    },
    {
        "name": "Lorenzo Ferri",
        "email": "lorenzo.ferri@example.test",
        "phone": "+41 79 567 89 01",
        "purchases": 5,
        "days_first": 360,
        "days_last": 150,
        "avg_amount": 70,
        "spread_pct": 0.30,
        "tag": "regular",
    },

    # ── INACTIVE customers (no purchases for 200+ days) ──────────────
    {
        "name": "Francesca Vitali",
        "email": "f.vitali@example.test",
        "phone": "+41 79 678 90 12",
        "purchases": 4,
        "days_first": 540,
        "days_last": 250,
        "avg_amount": 90,
        "spread_pct": 0.40,
        "tag": "regular",
    },
    {
        "name": "Hans Bühler",
        "email": "hans.buehler@example.test",
        "phone": None,
        "purchases": 3,
        "days_first": 400,
        "days_last": 280,
        "avg_amount": 65,
        "spread_pct": 0.30,
        "tag": "regular",
    },
    {
        "name": "Paola Mazzoni",
        "email": "paola.mazzoni@example.test",
        "phone": "+41 79 789 01 23",
        "purchases": 5,
        "days_first": 450,
        "days_last": 320,
        "avg_amount": 70,
        "spread_pct": 0.30,
        "tag": "regular",
    },
    {
        "name": "Fabio Donati",
        "email": None,
        "phone": "+41 79 890 12 34",
        "purchases": 2,
        "days_first": 380,
        "days_last": 220,
        "avg_amount": 55,
        "spread_pct": 0.40,
        "tag": "regular",
    },

    # ── NEW customers (first purchase ≤ 30 days ago) ─────────────────
    {
        "name": "Sofia Lombardi",
        "email": "sofia.lombardi@example.test",
        "phone": "+41 79 901 23 45",
        "purchases": 1,           # single purchase → high churn risk
        "days_first": 8,
        "days_last": 8,
        "avg_amount": 120,
        "spread_pct": 0.0,
        "tag": "new",
    },
    {
        "name": "Tommaso Greco",
        "email": "tommaso.greco@example.test",
        "phone": None,
        "purchases": 2,
        "days_first": 25,
        "days_last": 10,
        "avg_amount": 80,
        "spread_pct": 0.20,
        "tag": "new",
    },
    {
        "name": "Chiara Rinaldi",
        "email": "chiara.rinaldi@example.test",
        "phone": "+41 79 012 34 56",
        "purchases": 3,
        "days_first": 28,
        "days_last": 3,
        "avg_amount": 95,
        "spread_pct": 0.30,
        "tag": "new",
    },

    # ── AT-RISK / LOST one-shot customers ────────────────────────────
    {
        "name": "Stefano Marchi",
        "email": "stefano.m@example.test",
        "phone": "+41 79 111 22 33",
        "purchases": 1,           # single purchase 60d ago → at-risk
        "days_first": 65,
        "days_last": 65,
        "avg_amount": 200,
        "spread_pct": 0.0,
        "tag": "at_risk",
    },
    {
        "name": "Valentina Bruno",
        "email": "v.bruno@example.test",
        "phone": "+41 79 222 33 44",
        "purchases": 2,           # 2 purchases 70-110d ago → watch
        "days_first": 110,
        "days_last": 70,
        "avg_amount": 75,
        "spread_pct": 0.30,
        "tag": "regular",
    },
    {
        "name": "Antonio Rizzo",
        "email": None,
        "phone": None,
        "purchases": 1,
        "days_first": 200,
        "days_last": 200,
        "avg_amount": 150,
        "spread_pct": 0.0,
        "tag": "at_risk",
    },
]


SALES_CATEGORIES = [
    "Vendite prodotti", "Servizi", "Consulenze", "Eventi", "Corsi",
]
SALES_DESCRIPTIONS = [
    "Sessione coaching",
    "Consulenza personalizzata",
    "Workshop tematico",
    "Ordine prodotti",
    "Pacchetto trattamenti",
    "Consulenza online",
    "Corso intensivo",
]
SALES_CHANNELS = ["Online", "POS", "Negozio", "Storefront"]


# ── Helpers ────────────────────────────────────────────────────────────


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _generate_id() -> str:
    return str(uuid.uuid4())


def _random_amount(avg: float, spread: float) -> float:
    """Return a value in [avg×(1-spread), avg×(1+spread)] rounded to 2dp."""
    if spread <= 0:
        return round(avg, 2)
    delta = avg * spread
    return round(avg + random.uniform(-delta, delta), 2)


def _date_n_days_ago(n: int) -> str:
    return (datetime.now(timezone.utc) - timedelta(days=n)).date().isoformat()


# ── Wipe + seed ────────────────────────────────────────────────────────


async def wipe_demo_seed(org_id: str):
    """Remove the previous demo seed (idempotent)."""
    from database import (
        customers_collection,
        sales_records_collection,
        orders_collection,
    )

    res_c = await customers_collection.delete_many({
        "organization_id": org_id,
        "metadata.demo_seed": "customer_insights_v1",
    })
    res_s = await sales_records_collection.delete_many({
        "organization_id": org_id,
        "source_label": "demo_seed_customer_insights_v1",
    })
    res_o = await orders_collection.delete_many({
        "organization_id": org_id,
        "metadata.demo_seed": "customer_insights_v1",
    })
    return {
        "customers": res_c.deleted_count,
        "sales": res_s.deleted_count,
        "orders": res_o.deleted_count,
    }


async def seed_customers(org_id: str) -> list[dict]:
    """Insert the 20 personas. Returns the list of customer dicts so the
    sales-seeder can reference their ids."""
    from database import customers_collection

    now_iso = _now_iso()
    docs = []
    for p in PERSONAS:
        cid = _generate_id()
        docs.append({
            "id": cid,
            "organization_id": org_id,
            "name": p["name"],
            "email": p["email"],
            "phone": p["phone"],
            "tags": [p["tag"]],
            "is_active": True,
            "metadata": {"demo_seed": "customer_insights_v1"},
            "created_at": now_iso,
            "updated_at": now_iso,
        })
    if docs:
        await customers_collection.insert_many(docs)
    return docs


async def seed_sales(org_id: str, customers: list[dict]) -> int:
    """For each persona, generate `purchases` sales spread between
    days_first and days_last."""
    from database import sales_records_collection

    now_iso = _now_iso()
    docs = []

    persona_by_name = {p["name"]: p for p in PERSONAS}

    for c in customers:
        p = persona_by_name[c["name"]]
        n = p["purchases"]
        if n <= 0:
            continue

        if n == 1:
            # Single purchase exactly at days_last
            day_offsets = [p["days_last"]]
        else:
            # Evenly spread between days_first and days_last with some jitter
            step = (p["days_first"] - p["days_last"]) / max(n - 1, 1)
            day_offsets = [
                int(p["days_first"] - i * step + random.randint(-3, 3))
                for i in range(n)
            ]
            # Ensure all stay in [days_last, days_first]
            day_offsets = [
                max(p["days_last"], min(p["days_first"], d)) for d in day_offsets
            ]

        for offset in day_offsets:
            amount = _random_amount(p["avg_amount"], p["spread_pct"])
            biz_date = _date_n_days_ago(offset)
            docs.append({
                "id": _generate_id(),
                "organization_id": org_id,
                "dataset_id": None,
                "customer_id": c["id"],
                "date": biz_date,
                "amount": amount,
                "currency": "EUR",
                "category": random.choice(SALES_CATEGORIES),
                "description": random.choice(SALES_DESCRIPTIONS),
                "channel": random.choice(SALES_CHANNELS),
                "payment_status": random.choice(["paid", "paid", "paid", "pending"]),
                "source_label": "demo_seed_customer_insights_v1",
                "created_at": now_iso,
                "updated_at": now_iso,
            })

    if docs:
        await sales_records_collection.insert_many(docs)
    return len(docs)


async def seed_a_few_orders(org_id: str, customers: list[dict]) -> int:
    """Insert a handful of orders for the order-derived metrics
    (booking_count / event_attendance / cancellation_rate_pct)."""
    from database import orders_collection

    now = datetime.now(timezone.utc)
    now_iso = now.isoformat()
    docs = []

    # Pick 5 customers with the most purchases (top + active)
    top = sorted(
        customers,
        key=lambda c: -next(
            (p["purchases"] for p in PERSONAS if p["name"] == c["name"]), 0
        ),
    )[:5]

    for i, c in enumerate(top):
        # 2 orders each, one of which has a "cancelled" mixed in for #4
        for j, status in enumerate(["confirmed", "confirmed"]):
            ord_status = "cancelled" if (i == 3 and j == 1) else status
            order_total = round(random.uniform(80, 250), 2)
            order_date = now - timedelta(days=random.randint(5, 60))
            docs.append({
                "id": _generate_id(),
                "organization_id": org_id,
                "customer_id": c["id"],
                "order_number": f"ORD-DEMO-{i*2+j+1:04d}",
                "status": ord_status,
                "total": order_total,
                "currency": "EUR",
                "items": [
                    {
                        "product_id": _generate_id(),
                        "product_name": "Demo product",
                        "quantity": random.randint(1, 3),
                        "unit_price": order_total,
                        "item_type": random.choice(["product", "booking", "event_ticket"]),
                    },
                ],
                "fulfillment": {"status": "fulfilled" if ord_status == "confirmed" else "cancelled"},
                "created_at": order_date.isoformat(),
                "updated_at": now_iso,
                "metadata": {"demo_seed": "customer_insights_v1"},
            })

    if docs:
        await orders_collection.insert_many(docs)
    return len(docs)


async def trigger_refresh(org_id: str):
    """Re-compute customer_metrics (single source of truth for both
    the new /api/customer-insights/* surface and the platform module
    dispatcher mounted at /api/modules/customers_light/*)."""
    from modules.customer_insights.refresh import refresh_customer_metrics

    return await refresh_customer_metrics(org_id)


# ── Reporting ──────────────────────────────────────────────────────────


async def report(org_id: str):
    """Print a quick after-state summary so the user knows what's live."""
    from database import customer_metrics_collection

    cur = customer_metrics_collection.find(
        {"organization_id": org_id}, {"_id": 0, "segment": 1, "customer_status": 1},
    )
    rows = await cur.to_list(length=10000)

    seg_count: dict[str, int] = {}
    sta_count: dict[str, int] = {}
    for r in rows:
        s = r.get("segment", "unknown")
        st = r.get("customer_status", "unknown")
        seg_count[s] = seg_count.get(s, 0) + 1
        sta_count[st] = sta_count.get(st, 0) + 1

    print(f"\nMaterialised customer_metrics for org={org_id}:")
    print(f"  Total customers: {len(rows)}")
    print("  Segments:")
    for k, v in sorted(seg_count.items()):
        print(f"    {k:12s} {v}")
    print("  Statuses:")
    for k, v in sorted(sta_count.items()):
        print(f"    {k:12s} {v}")


# ── Entrypoint ─────────────────────────────────────────────────────────


async def run(org_id: str):
    print("=" * 70)
    print(f"Customer Insights demo seed — org {org_id}")
    print("=" * 70)

    print("\n[1/4] Wiping previous demo data…")
    wiped = await wipe_demo_seed(org_id)
    print(
        f"      removed: customers={wiped['customers']}  "
        f"sales={wiped['sales']}  orders={wiped['orders']}"
    )

    print("\n[2/4] Inserting customers + sales + orders…")
    customers = await seed_customers(org_id)
    sales_n = await seed_sales(org_id, customers)
    orders_n = await seed_a_few_orders(org_id, customers)
    print(
        f"      created: customers={len(customers)}  "
        f"sales={sales_n}  orders={orders_n}"
    )

    print("\n[3/4] Refreshing customer_metrics (materialised view)…")
    refreshed = await trigger_refresh(org_id)
    print(f"      {refreshed.get('message')}")

    print("\n[4/4] Verifying segment / status distribution…")
    await report(org_id)

    print("\n" + "=" * 70)
    print("✓ Demo seed complete. Now visit:")
    print("  http://localhost:3000/modules/customer-insights")
    print("=" * 70)


def main():
    import argparse
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument(
        "--org-id", default=DEFAULT_ORG_ID,
        help=f"Target organisation id (default: {DEFAULT_ORG_ID})",
    )
    parser.add_argument(
        "--seed", type=int, default=42,
        help="Random seed for reproducibility (default: 42)",
    )
    args = parser.parse_args()

    random.seed(args.seed)
    asyncio.run(run(args.org_id))


if __name__ == "__main__":
    main()
