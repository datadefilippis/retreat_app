#!/usr/bin/env python3
"""
setup_stripe_retreat.py — Crea Product + Prices Stripe per retreat_pro
e scrive gli ID sul CommercialPlan. Gemello snello di setup_stripe.py
per il fork ritiri (Blocco B.2, 4/7/2026).

Solo retreat_pro ha bisogno di Stripe Billing:
  · retreat_free     → 0€, nessun checkout (baseline al signup)
  · retreat_founding → 0€, assegnazione admin, nessun checkout

Idempotente: cerca il product via metadata plan_slug=retreat_pro prima
di crearlo; i price esistenti con lo stesso importo/intervallo vengono
riusati. Nessuna cancellazione, mai.

Usage (da backend/):
    venv/bin/python scripts/setup_stripe_retreat.py            # dry-run
    venv/bin/python scripts/setup_stripe_retreat.py --execute
"""

import argparse
import asyncio
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))

from dotenv import load_dotenv
load_dotenv(BACKEND_DIR / ".env", override=False)

import os
import stripe

PLAN_SLUG = "retreat_pro"
PRODUCT_NAME = "Retreat Pro"
PRODUCT_DESC = "Piano Pro piattaforma ritiri — fee 2%, evidenza nel calendario pubblico."
PRICE_MONTHLY_MINOR = 2900   # 29 €
PRICE_YEARLY_MINOR = 29000   # 290 €


def find_or_create_product(dry_run: bool) -> str:
    for p in stripe.Product.list(active=True, limit=100).auto_paging_iter():
        if (p.get("metadata") or {}).get("plan_slug") == PLAN_SLUG:
            print(f"product esistente: {p['id']}")
            return p["id"]
    if dry_run:
        print(f"[dry-run] creerei product '{PRODUCT_NAME}' (metadata plan_slug={PLAN_SLUG})")
        return "prod_DRYRUN"
    p = stripe.Product.create(
        name=PRODUCT_NAME, description=PRODUCT_DESC,
        metadata={"plan_slug": PLAN_SLUG, "app": "retreat"},
    )
    print(f"product creato: {p['id']}")
    return p["id"]


def find_or_create_price(product_id: str, amount_minor: int,
                         interval: str, dry_run: bool) -> str:
    if product_id != "prod_DRYRUN":
        for pr in stripe.Price.list(product=product_id, active=True,
                                    limit=100).auto_paging_iter():
            rec = pr.get("recurring") or {}
            if (pr["unit_amount"] == amount_minor
                    and pr["currency"] == "eur"
                    and rec.get("interval") == interval):
                print(f"price esistente {interval}: {pr['id']}")
                return pr["id"]
    if dry_run:
        print(f"[dry-run] creerei price {amount_minor/100:.0f}€/{interval}")
        return f"price_DRYRUN_{interval}"
    pr = stripe.Price.create(
        product=product_id, unit_amount=amount_minor, currency="eur",
        recurring={"interval": interval},
        metadata={"plan_slug": PLAN_SLUG},
    )
    print(f"price creato {interval}: {pr['id']}")
    return pr["id"]


async def write_ids(product_id: str, monthly_id: str, yearly_id: str,
                    dry_run: bool) -> None:
    from database import commercial_plans_collection
    if dry_run:
        print(f"[dry-run] scriverei su {PLAN_SLUG}: product={product_id} "
              f"monthly={monthly_id} yearly={yearly_id}")
        return
    r = await commercial_plans_collection.update_one(
        {"slug": PLAN_SLUG},
        {"$set": {"stripe_product_id": product_id,
                  "stripe_price_id_monthly": monthly_id,
                  "stripe_price_id_yearly": yearly_id}},
    )
    print(f"DB aggiornato ({PLAN_SLUG}): matched={r.matched_count}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--execute", action="store_true",
                    help="applica (default: dry-run)")
    args = ap.parse_args()
    dry = not args.execute

    key = os.environ.get("STRIPE_SECRET_KEY", "")
    if not key:
        sys.exit("STRIPE_SECRET_KEY mancante in backend/.env")
    if key.startswith("sk_live") :
        print("⚠ CHIAVE LIVE — procedo solo perché esplicitamente eseguito")
    stripe.api_key = key

    product_id = find_or_create_product(dry)
    monthly_id = find_or_create_price(product_id, PRICE_MONTHLY_MINOR, "month", dry)
    yearly_id = find_or_create_price(product_id, PRICE_YEARLY_MINOR, "year", dry)
    asyncio.run(write_ids(product_id, monthly_id, yearly_id, dry))
    print("fatto" + (" (dry-run)" if dry else ""))


if __name__ == "__main__":
    main()
