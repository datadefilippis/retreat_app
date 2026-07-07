"""SA1 — backfill one-shot: fee ledger storico + sales_channel.

Ricostruisce il libro mastro delle fee per gli incassi ONLINE avvenuti
prima di SA1 e assegna il canale di vendita agli ordini pre-GT1.

Regole (le stesse del runtime):
  1. Righe schedule con status 'paid' e stripe_payment_intent →
     una riga ledger kind='schedule_row' (amount = row.amount_minor).
     'paid_manual' NON entra: il manuale non genera fee.
  2. Ordini payment_intent='collected' SENZA schedule → una riga
     kind='checkout' con il totale ordine.
  3. Righe con refund.stripe_refund_id → riga negativa kind='refund'.
  4. Percentuale: dall'audit log payment.checkout.created dell'ordine
     (il valore VERO della creazione), fallback org corrente.
  5. sales_channel mancante → dal campo source:
     manual→manual, pos→pos, storefront*→store.

Idempotente: le righe ledger sono upsert su entry_key; il backfill
canali tocca solo ordini senza sales_channel. Rilanciabile.

Uso:  venv/bin/python scripts/backfill_fee_ledger.py [--dry-run]
"""

import asyncio
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
os.environ.setdefault("JWT_SECRET_KEY", "backfill")

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

DRY = "--dry-run" in sys.argv


async def main() -> None:
    from database import db, orders_collection, organizations_collection
    from services.platform_fee_ledger import record_platform_fee

    # percentuale storica per ordine dall'audit trail del checkout
    fee_pct_by_order: dict = {}
    async for log in db.audit_logs.find(
            {"action": "payment.checkout.created"},
            {"_id": 0, "resource_id": 1, "details.application_fee_percent": 1}):
        pct = (log.get("details") or {}).get("application_fee_percent")
        if pct is not None:
            fee_pct_by_order[log["resource_id"]] = float(pct)

    org_pct: dict = {}
    async for o in organizations_collection.find(
            {}, {"_id": 0, "id": 1, "application_fee_percent": 1}):
        org_pct[o["id"]] = float(o.get("application_fee_percent") or 0)

    def pct_for(order_id: str, org_id: str) -> float:
        return fee_pct_by_order.get(order_id, org_pct.get(org_id, 0.0))

    written = {"schedule_row": 0, "checkout": 0, "refund": 0}
    scheduled_order_ids = set()

    # ── 1+3. Righe schedule pagate online / rimborsate ──────────────
    async for sched in db.payment_schedules.find(
            {}, {"_id": 0, "order_id": 1, "organization_id": 1,
                 "currency": 1, "rows": 1}):
        order_id = sched.get("order_id")
        org_id = sched.get("organization_id")
        scheduled_order_ids.add(order_id)
        for row in sched.get("rows") or []:
            seq = row.get("seq")
            amount = int(row.get("amount_minor") or 0)
            if amount <= 0:
                continue
            pct = pct_for(order_id, org_id)
            if row.get("status") in ("paid", "refunded") \
                    and row.get("stripe_payment_intent"):
                key = row.get("stripe_session_id") \
                    or f"backfill:{order_id}:row:{seq}"
                if not DRY:
                    await record_platform_fee(
                        entry_key=key, organization_id=org_id,
                        order_id=order_id, kind="schedule_row",
                        amount_minor=amount, fee_percent=pct,
                        currency=sched.get("currency"), row_seq=seq,
                        collected_at=row.get("paid_at"))
                written["schedule_row"] += 1
            refund = row.get("refund") or {}
            if refund.get("stripe_refund_id"):
                if not DRY:
                    await record_platform_fee(
                        entry_key=f"refund:{order_id}:{seq}",
                        organization_id=org_id, order_id=order_id,
                        kind="refund",
                        amount_minor=-int(refund.get("amount_minor")
                                          or amount),
                        fee_percent=pct,
                        currency=sched.get("currency"), row_seq=seq,
                        collected_at=refund.get("at"))
                written["refund"] += 1

    # ── 2. Ordini collected senza schedule ───────────────────────────
    async for o in orders_collection.find(
            {"payment_intent": "collected",
             "id": {"$nin": list(scheduled_order_ids)}},
            {"_id": 0, "id": 1, "organization_id": 1, "total": 1,
             "currency": 1, "payment_checkout.completed_at": 1}):
        amount = int(round(float(o.get("total") or 0) * 100))
        if amount <= 0:
            continue
        if not DRY:
            await record_platform_fee(
                entry_key=f"backfill:{o['id']}:checkout",
                organization_id=o["organization_id"], order_id=o["id"],
                kind="checkout", amount_minor=amount,
                fee_percent=pct_for(o["id"], o["organization_id"]),
                currency=o.get("currency"),
                collected_at=(o.get("payment_checkout") or {}).get("completed_at"))
        written["checkout"] += 1

    # ── 5. sales_channel dagli ordini pre-GT1 ────────────────────────
    channels = 0
    for source, channel in (("manual", "manual"), ("pos", "pos"),
                            ("storefront", "store"),
                            ("storefront_direct", "store")):
        q = {"source": source,
             "$or": [{"sales_channel": {"$exists": False}},
                     {"sales_channel": None}, {"sales_channel": ""}]}
        if DRY:
            channels += await orders_collection.count_documents(q)
        else:
            r = await orders_collection.update_many(
                q, {"$set": {"sales_channel": channel}})
            channels += r.modified_count

    # indice per gli aggregati SA2/SA4 (idempotente)
    if not DRY:
        await db.platform_fee_ledger.create_index(
            [("organization_id", 1), ("collected_at", -1)])
        await db.platform_fee_ledger.create_index("entry_key", unique=True)

    mode = "DRY-RUN" if DRY else "APPLICATO"
    print(f"[{mode}] ledger: {written} | sales_channel backfill: {channels}")


if __name__ == "__main__":
    asyncio.run(main())
