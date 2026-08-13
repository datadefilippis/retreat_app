"""Riallinea i Price Stripe di un piano al prezzo nel DB (AB1b, 13/8/2026).

PERCHE' ESISTE: il checkout abbonamento usa stripe_price_id_monthly/yearly
salvati sul CommercialPlan (stripe_service.create_checkout_session), NON
price_monthly dal DB. I Price di Stripe sono immutabili: quando il prezzo
cambia (es. Pro 29 -> 19, migrazione pro_price_19_v1) il checkout continua
a mostrare quello vecchio finche' qualcuno non crea un Price nuovo e lo
aggancia al piano. Questo script fa esattamente quel giro:

  1. legge il piano dal DB (price_monthly/price_yearly = verita')
  2. se il Price Stripe corrente ha gia' quell'importo -> no-op
  3. crea Price nuovi sullo STESSO Product (lo storico abbonamenti resta
     coerente), con idempotency key che include l'importo
  4. disattiva i Price vecchi (active=false: niente acquisti per sbaglio,
     gli abbonamenti esistenti che li usano NON vengono toccati)
  5. aggiorna stripe_price_id_monthly/yearly sul piano

Uso (dalla cartella backend, stessa venv del server):
    python scripts/stripe_reprice_plan.py retreat_pro           # dry-run
    python scripts/stripe_reprice_plan.py retreat_pro --apply   # esegue

In prod: server-side col pattern nohup, la chiave Stripe arriva
dall'ambiente come per il server. Riusabile per ogni futuro cambio prezzo.
"""
import asyncio
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))


def _cents(amount: float) -> int:
    return int(round(float(amount) * 100))


async def main(slug: str, apply: bool) -> int:
    from database import commercial_plans_collection
    from services.stripe_catalog_service import _get_stripe

    stripe = _get_stripe()
    if stripe is None:
        print("ERRORE: Stripe non configurato (STRIPE_SECRET_KEY assente).")
        return 1

    plan = await commercial_plans_collection.find_one({"slug": slug})
    if not plan:
        print(f"ERRORE: piano '{slug}' non trovato.")
        return 1

    product_id = plan.get("stripe_product_id")
    if not product_id:
        print(f"ERRORE: '{slug}' non ha stripe_product_id — usa "
              "ensure_stripe_for_plan per la prima creazione, non questo script.")
        return 1

    currency = (plan.get("currency") or "eur").lower()
    updates: dict = {}

    for campo, interval, db_amount in [
        ("stripe_price_id_monthly", "month", plan.get("price_monthly")),
        ("stripe_price_id_yearly", "year", plan.get("price_yearly")),
    ]:
        if not db_amount or db_amount <= 0:
            print(f"[{interval}] prezzo DB assente/zero — salto.")
            continue
        want = _cents(db_amount)
        old_id = plan.get(campo)
        old_amount = None
        if old_id:
            try:
                old = stripe.Price.retrieve(old_id)
                old_amount = old.get("unit_amount")
            except Exception as e:
                print(f"[{interval}] avviso: Price attuale {old_id} "
                      f"non leggibile da Stripe: {e}")
        if old_amount == want:
            print(f"[{interval}] gia' allineato: {old_id} = {want/100:.2f} "
                  f"{currency.upper()} — no-op.")
            continue

        print(f"[{interval}] DB {want/100:.2f} {currency.upper()} vs Stripe "
              f"{(old_amount or 0)/100:.2f} ({old_id or 'nessun price'}) "
              "-> serve un Price nuovo")
        if not apply:
            continue

        nuovo = stripe.Price.create(
            product=product_id,
            unit_amount=want,
            currency=currency,
            recurring={"interval": interval},
            metadata={"afianco_slug": slug, "reprice": "ab1b-2026-08"},
            # l'importo nella chiave: un futuro cambio prezzo genera
            # una chiave nuova invece di rigiocare questa
            idempotency_key=f"reprice:{slug}:{interval}:{want}",
        )
        nuovo_id = nuovo["id"]
        updates[campo] = nuovo_id
        print(f"[{interval}] creato {nuovo_id} = {want/100:.2f} {currency.upper()}")

        if old_id:
            try:
                stripe.Price.modify(old_id, active=False)
                print(f"[{interval}] disattivato il vecchio {old_id}")
            except Exception as e:
                print(f"[{interval}] avviso: non ho potuto disattivare "
                      f"{old_id}: {e} (non blocca: il piano ora punta al nuovo)")

    if apply and updates:
        await commercial_plans_collection.update_one(
            {"slug": slug}, {"$set": updates})
        print(f"Piano '{slug}' aggiornato: {updates}")
    elif not apply:
        print("\nDRY-RUN: nessuna modifica. Rilancia con --apply per eseguire.")
    else:
        print("Niente da fare: tutto gia' allineato.")
    return 0


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if len(args) != 1:
        print(__doc__)
        sys.exit(2)
    sys.exit(asyncio.run(main(args[0], apply="--apply" in sys.argv)))
