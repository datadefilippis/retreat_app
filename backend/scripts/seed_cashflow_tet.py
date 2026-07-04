"""
seed_cashflow_tet.py
====================
Seed cashflow data for the `tet` org so the user can test:
  · Cashflow dashboards (analytics, charts)
  · The data_rows monthly quota (free plan limit = 300)
  · The QuotaProgressBanner (Onda 10 Step F.2)

Counts:
  · 100 sales_records   (entrate)
  · 100 expense_records (uscite)
  ·  40 purchase_records (acquisti)
  Total: 240 rows → under the 300/mese free limit, so the user can
  still add ~60 more before paywall fires.

`created_at` is always now(): the system insert time is what the
data_rows quota counter uses (`_count_data_rows_authoritative` reads
`created_at >= start_of_month`). Business `date` field can be
backdated for visual realism on dashboards.

Run from backend/ with the venv:
  set -a; source .env; set +a
  ./venv/bin/python -m scripts.seed_cashflow_tet
"""

import asyncio
import random
import sys
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

# Make backend/ importable
_BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_BACKEND_DIR))

from database import (  # noqa: E402
    sales_records_collection,
    expense_records_collection,
    purchase_records_collection,
)

ORG_ID = "16d64b96-b90f-4705-b6aa-03d279014909"

SALES_CATEGORIES = [
    "Vendite prodotti", "Servizi", "Consulenze",
    "Eventi", "Corsi", "Abbonamenti",
]
SALES_CHANNELS = ["Online", "POS", "Negozio", "Storefront", "B2B"]
SALES_DESCRIPTIONS = [
    "Vendita tisane assortite", "Consulenza personalizzata",
    "Workshop erbe officinali", "Vendita oli essenziali",
    "Pacchetto cosmetici naturali", "Sessione formativa",
    "Abbonamento mensile", "Saponi artigianali",
]

EXPENSE_CATEGORIES = [
    "Marketing", "Affitto", "Materie prime", "Utenze",
    "Software", "Trasporti", "Manutenzione", "Formazione",
]
EXPENSE_SUPPLIERS = [
    "ENEL Energia", "TIM Business", "Aruba SpA", "Google Ads",
    "Studio Commercialista Rossi", "Fornitore Erbe Toscane",
    "Imballaggi Verdi srl", "Hostinger",
]
EXPENSE_DESCRIPTIONS = [
    "Bolletta luce", "Bolletta gas", "Internet/telefono",
    "Campagna social", "Acquisto packaging", "Software gestionale",
    "Affitto locale", "Manutenzione attrezzature",
]

PURCHASE_CATEGORIES = [
    "Materie prime", "Imballaggi", "Logistica",
    "Attrezzature", "Etichette",
]
PURCHASE_SUPPLIERS = [
    "Erboristeria Bianchi", "Cosmetics Wholesale srl",
    "Imballaggi Verdi srl", "Fornitore Bio Toscana",
    "Etichette Express", "Spedizioni Rapide",
]
PURCHASE_PRODUCTS = [
    "Camomilla essiccata", "Olio essenziale lavanda",
    "Bottiglie 100ml", "Cera d'api naturale",
    "Etichette adesive", "Burro di karité",
    "Estratto di calendula", "Sapone base",
]
PURCHASE_UNITS = ["kg", "litri", "pezzi", "scatole"]


def _generate_id() -> str:
    return uuid.uuid4().hex


async def seed_sales(count: int, now_iso: str) -> int:
    docs = []
    for _ in range(count):
        # Business date can be 0-60 days in the past — looks realistic
        days_ago = random.randint(0, 60)
        biz_date = (datetime.now(timezone.utc) - timedelta(days=days_ago)).date().isoformat()
        amount = round(random.uniform(20, 800), 2)
        docs.append({
            "id": _generate_id(),
            "organization_id": ORG_ID,
            "dataset_id": "manual",
            "date": biz_date,
            "amount": amount,
            "category": random.choice(SALES_CATEGORIES),
            "description": random.choice(SALES_DESCRIPTIONS),
            "channel": random.choice(SALES_CHANNELS),
            "source_label": "Manuale",
            "payment_status": random.choices(
                ["paid", "pending", "overdue"],
                weights=[8, 1, 1],
            )[0],
            # Onda 18 — created_at = system insert time. This is what
            # cashflow_monitor.data_rows quota counter uses.
            "created_at": now_iso,
            "updated_at": now_iso,
        })
    if docs:
        await sales_records_collection.insert_many(docs)
    return len(docs)


async def seed_expenses(count: int, now_iso: str) -> int:
    docs = []
    for _ in range(count):
        days_ago = random.randint(0, 60)
        biz_date = (datetime.now(timezone.utc) - timedelta(days=days_ago)).date().isoformat()
        amount = round(random.uniform(15, 1500), 2)
        docs.append({
            "id": _generate_id(),
            "organization_id": ORG_ID,
            "dataset_id": "manual",
            "date": biz_date,
            "amount": amount,
            "category": random.choice(EXPENSE_CATEGORIES),
            "description": random.choice(EXPENSE_DESCRIPTIONS),
            "supplier": random.choice(EXPENSE_SUPPLIERS),
            "is_paid": random.choice([True, True, True, False]),  # mostly paid
            "is_fixed": random.random() < 0.2,  # 20% fixed
            "source_label": "Manuale",
            "created_at": now_iso,
            "updated_at": now_iso,
        })
    if docs:
        await expense_records_collection.insert_many(docs)
    return len(docs)


async def seed_purchases(count: int, now_iso: str) -> int:
    docs = []
    for _ in range(count):
        days_ago = random.randint(0, 60)
        biz_date = (datetime.now(timezone.utc) - timedelta(days=days_ago)).date().isoformat()
        quantity = round(random.uniform(1, 50), 2)
        unit_price = round(random.uniform(2, 80), 2)
        total = round(quantity * unit_price, 2)
        iva_rate = random.choice([22, 22, 22, 10, 4, None])
        total_with_iva = round(total * (1 + iva_rate / 100), 2) if iva_rate else None
        docs.append({
            "id": _generate_id(),
            "organization_id": ORG_ID,
            "dataset_id": None,
            "date": biz_date,
            "supplier_name": random.choice(PURCHASE_SUPPLIERS),
            "quantity": quantity,
            "unit": random.choice(PURCHASE_UNITS),
            "unit_price": unit_price,
            "total_price": total,
            "category": random.choice(PURCHASE_CATEGORIES),
            "description": random.choice(PURCHASE_PRODUCTS),
            "iva": iva_rate,
            "total_with_iva": total_with_iva,
            "source_label": "Manuale",
            "created_at": now_iso,
            "updated_at": now_iso,
        })
    if docs:
        await purchase_records_collection.insert_many(docs)
    return len(docs)


async def main():
    now_dt = datetime.now(timezone.utc)
    now_iso = now_dt.isoformat()

    print(f"Seeding cashflow for tet @ {now_iso}")
    s = await seed_sales(100, now_iso)
    print(f"  ✓ {s} sales_records (entrate)")
    e = await seed_expenses(100, now_iso)
    print(f"  ✓ {e} expense_records (uscite)")
    p = await seed_purchases(40, now_iso)
    print(f"  ✓ {p} purchase_records (acquisti)")

    total = s + e + p
    print(f"\nTotal cashflow rows inserted: {total}")
    print("Free plan data_rows quota: 300/mese")
    print(f"Quota usage: {total}/300 ({(total/300)*100:.0f}%)")
    print(f"Remaining capacity before paywall: {300 - total} rows")


if __name__ == "__main__":
    asyncio.run(main())
