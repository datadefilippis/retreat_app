"""E2E caparra su Stripe test (Fase 2 S2, task 2.8 — driver).

Percorre il flusso REALE a livello servizio (stessi code path del runtime):
  1. cliente di test (upsert)
  2. create_order sul ritiro col piano caparra 30% → lo schedule nasce
     con righe deposit+balance (verifica)
  3. create_checkout_session → deve addebitare SOLO la caparra: verifica
     contro Stripe (session.amount_total == caparra; application fee 5%)
  4. stampa l'URL della session per il pagamento in browser (test card)
  5. --verify: dopo il pagamento, verify_commerce_order_payment (pull
     reconcile: stesso path del webhook) → assert riga paid, ordine
     confirmed, payment_state=deposit_paid, biglietti emessi

Uso:
  venv/bin/python scripts/e2e_deposit_checkout.py            # step 1-4
  venv/bin/python scripts/e2e_deposit_checkout.py --verify ORD_ID
"""

import asyncio
import os
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))

from dotenv import load_dotenv
load_dotenv(BACKEND_DIR / ".env", override=False)

DEMO_ORG_ID = "2393033b-80a8-47c9-8529-b7810c0b2123"
PRODUCT_NAME = "Ritiro Yoga Test S1"


async def create_flow() -> int:
    import stripe
    stripe.api_key = os.environ["STRIPE_SECRET_KEY"]
    from database import db
    from models.order import OrderCreate, OrderLineCreate
    from services.order_service import create_order
    from services.payment_checkout_service import create_checkout_session

    product = await db.products.find_one(
        {"organization_id": DEMO_ORG_ID, "name": PRODUCT_NAME}, {"_id": 0})
    if not product:
        print(f"prodotto '{PRODUCT_NAME}' non trovato — creare col wizard prima")
        return 1
    occ = await db.event_occurrences.find_one(
        {"organization_id": DEMO_ORG_ID, "product_id": product["id"]}, {"_id": 0})
    print(f"ritiro: {product['id']} | occurrence: {occ['id']} | start: {occ['start_at']}")

    # cliente di test (upsert per nome)
    customer = await db.customers.find_one(
        {"organization_id": DEMO_ORG_ID, "name": "Marco Partecipante"}, {"_id": 0})
    if not customer:
        from models.customer import Customer
        c = Customer(name="Marco Partecipante", email="marco.test@example.com",
                     organization_id=DEMO_ORG_ID)
        doc = c.model_dump()
        for k in ("created_at", "updated_at"):
            if hasattr(doc.get(k), "isoformat"):
                doc[k] = doc[k].isoformat()
        await db.customers.insert_one(doc)
        customer = doc
    print(f"cliente: {customer['id']}")

    order = await create_order(
        DEMO_ORG_ID,
        OrderCreate(
            customer_id=customer["id"],
            items=[OrderLineCreate(
                product_id=product["id"],
                quantity=1,
                occurrence_id=occ["id"],
            )],
        ),
        source="storefront",
        payment_intent="required",   # come fa il router storefront per i direct
    )
    print(f"ordine: {order['id']} | totale: {order['total']}€")

    schedule = await db.payment_schedules.find_one(
        {"order_id": order["id"]}, {"_id": 0})
    assert schedule, "schedule non creato!"
    kinds = [r["kind"] for r in schedule["rows"]]
    amounts = [r["amount_minor"] for r in schedule["rows"]]
    print(f"schedule: {kinds} {amounts} (somma={sum(amounts)})")
    assert kinds == ["deposit", "balance"], f"attese righe deposit+balance, trovate {kinds}"

    session = await create_checkout_session(DEMO_ORG_ID, order)
    assert session, "checkout session non creata (readiness?)"

    # Verifica su Stripe: la session addebita SOLO la caparra
    s = stripe.checkout.Session.retrieve(
        session["session_id"], stripe_account=session["connected_account"])
    deposit_minor = schedule["rows"][0]["amount_minor"]
    print(f"Stripe session amount_total: {s['amount_total']} (attesa caparra {deposit_minor})")
    assert s["amount_total"] == deposit_minor, "LA SESSION NON ADDEBITA LA CAPARRA"
    pi_data = (s.get("payment_intent") or "")
    print(f"metadata row_seq: {s['metadata'].get('schedule_row_seq')}")

    # riga → processing?
    schedule = await db.payment_schedules.find_one({"order_id": order["id"]}, {"_id": 0})
    print(f"riga 0 status: {schedule['rows'][0]['status']}")

    print("\nPAGA QUI (test card 4242 4242 4242 4242, qualsiasi data/CVC):")
    print(session["url"])
    print(f"\npoi:  venv/bin/python scripts/e2e_deposit_checkout.py --verify {order['id']}")
    return 0


async def verify_flow(order_id: str) -> int:
    from database import db
    from services.payment_checkout_service import verify_commerce_order_payment

    result = await verify_commerce_order_payment(order_id, DEMO_ORG_ID)
    print(f"verify: {result}")

    order = await db.orders.find_one({"id": order_id}, {"_id": 0})
    schedule = await db.payment_schedules.find_one({"order_id": order_id}, {"_id": 0})
    events = await db.payment_events.find({"order_id": order_id}, {"_id": 0}).to_list(50)
    tickets = await db.issued_tickets.find({"order_id": order_id}, {"_id": 0, "code": 1, "status": 1}).to_list(20)

    print(f"ordine: status={order.get('status')} payment_intent={order.get('payment_intent')} "
          f"payment_state={order.get('payment_state')}")
    print(f"schedule: state={schedule['payment_state']} "
          f"rows={[(r['seq'], r['status']) for r in schedule['rows']]} "
          f"totals={schedule['totals']}")
    print(f"eventi ({len(events)}): {[(e['action'], e['actor']) for e in events]}")
    print(f"biglietti: {[(t['code'], t['status']) for t in tickets]}")

    ok = (
        order.get("status") == "confirmed"
        and order.get("payment_state") == "deposit_paid"
        and schedule["rows"][0]["status"] == "paid"
        and schedule["rows"][1]["status"] == "pending"
        and len(tickets) >= 1
    )
    print("\nE2E CAPARRA:", "OK — tutto sincronizzato e tracciato" if ok else "FALLITO")
    return 0 if ok else 1


if __name__ == "__main__":
    if len(sys.argv) > 2 and sys.argv[1] == "--verify":
        raise SystemExit(asyncio.run(verify_flow(sys.argv[2])))
    raise SystemExit(asyncio.run(create_flow()))
