"""Bootstrap Stripe Connect DEV (Fase 2 S2 — e2e caparra).

SOLO TEST MODE (rifiuta chiavi live). Idempotente. Per l'org demo:
  1. Crea un connected account Stripe **custom** completamente abilitato
     con dati di test (tos_acceptance via API è permessa sui custom: per
     gli Express serve l'onboarding hosted — in dev il tipo non cambia la
     meccanica di Checkout diretto + application_fee che dobbiamo provare).
  2. Attende charges_enabled=True.
  3. Upserta il documento payment_connections (status=active,
     runtime_status=ready, is_default=True) che la readiness richiede.
  4. Imposta application_fee_percent=5 sull'org (il modello Free retreat).

Uso:  venv/bin/python scripts/bootstrap_dev_stripe.py
"""

import asyncio
import os
import sys
import time
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))

from dotenv import load_dotenv
load_dotenv(BACKEND_DIR / ".env", override=False)

DEMO_ORG_ID = "2393033b-80a8-47c9-8529-b7810c0b2123"


async def main() -> int:
    import stripe
    key = os.environ.get("STRIPE_SECRET_KEY", "")
    if not key.startswith("sk_test_"):
        print("RIFIUTO: serve una chiave sk_test_ (mai live per il bootstrap dev)")
        return 1
    stripe.api_key = key

    from database import db
    conn = await db.payment_connections.find_one(
        {"organization_id": DEMO_ORG_ID, "provider": "stripe"}, {"_id": 0})
    if conn and conn.get("external_account_id"):
        acct_id = conn["external_account_id"]
        print(f"connessione esistente: {acct_id}")
    else:
        acct = stripe.Account.create(
            type="custom",
            country="IT",
            email="operatore.demo@example.com",
            business_type="individual",
            capabilities={
                "card_payments": {"requested": True},
                "transfers": {"requested": True},
            },
            individual={
                "first_name": "Giulia",
                "last_name": "Demo",
                "email": "operatore.demo@example.com",
                "phone": "+390000000000",
                "dob": {"day": 1, "month": 1, "year": 1990},
                "address": {
                    "line1": "Via Test 1",
                    "city": "Ostuni",
                    "postal_code": "72017",
                    "state": "BR",
                    "country": "IT",
                },
            },
            business_profile={
                "mcc": "7991",   # health & fitness / wellness
                "product_description": "Ritiri olistici (account di test)",
            },
            tos_acceptance={"date": int(time.time()), "ip": "127.0.0.1"},
        )
        acct_id = acct.id
        stripe.Account.create_external_account(
            acct_id,
            external_account={
                "object": "bank_account",
                "country": "IT",
                "currency": "eur",
                "account_number": "IT60X0542811101000000123456",  # IBAN test
                "account_holder_name": "Giulia Demo",
            },
        )
        print(f"account custom creato: {acct_id}")

    # Attendi charges_enabled (in test di solito immediato)
    for attempt in range(10):
        acct = stripe.Account.retrieve(acct_id)
        if acct.get("charges_enabled"):
            break
        missing = (acct.get("requirements") or {}).get("currently_due", [])
        print(f"  attesa charges_enabled… (due: {missing[:4]})")
        await asyncio.sleep(2)
    print(f"charges_enabled: {acct.get('charges_enabled')} | payouts: {acct.get('payouts_enabled')}")
    if not acct.get("charges_enabled"):
        print("ATTENZIONE: account non abilitato — controllare requirements sopra")
        return 1

    from models.payment_connection import PaymentConnection
    from models.common import utc_now
    if not conn:
        doc = PaymentConnection(
            organization_id=DEMO_ORG_ID,
            provider="stripe",
            display_name="Stripe test (bootstrap dev)",
            external_account_id=acct_id,
            is_default=True,
            status="active",
            runtime_status="ready",
            connect_type="express",   # compat con le query dell'app
            connected_at=utc_now(),
        ).model_dump()
        doc["connected_at"] = doc["connected_at"].isoformat()
        lrc = doc.get("last_runtime_check_at")
        if lrc is not None:
            doc["last_runtime_check_at"] = lrc.isoformat()
        await db.payment_connections.insert_one(doc)
        print("payment_connection creata (active/ready/default)")
    else:
        await db.payment_connections.update_one(
            {"organization_id": DEMO_ORG_ID, "provider": "stripe"},
            {"$set": {"status": "active", "runtime_status": "ready",
                      "is_default": True,
                      "external_account_id": acct_id}},
        )
        print("payment_connection aggiornata (active/ready/default)")

    await db.organizations.update_one(
        {"id": DEMO_ORG_ID},
        {"$set": {"application_fee_percent": 5}},
    )
    print("application_fee_percent=5 impostata sull'org demo")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
