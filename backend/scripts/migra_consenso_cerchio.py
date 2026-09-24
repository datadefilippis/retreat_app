"""Lotto B2/B3 (24/9/2026) — il registro del consenso agli iscritti di
prima, con onesta' sulla prova che abbiamo:

  confermati (confirmed_at)        → modalita «doppio» (hanno cliccato)
  source prelaunch_lead            → «prelancio», testo lancio-v1
  altri pending / disiscritti      → «singolo-senza-prova»

Il testo e la versione vengono da services/testi_consenso.py
(versione_storica: quale casella mostrava la fonte da cui si e'
iscritto). ip/user_agent restano None: non li avevamo.

Backfill B3: chi ha confirmed_at e non verificato_at → verificato_at =
confirmed_at, verificato_da {tipo: conferma, dettaglio: backfill}.

Idempotente: chi ha gia' `consenso` non viene toccato; il backfill
scrive solo dove manca.

Uso (da backend/, con l'env caricato):
  venv/bin/python scripts/migra_consenso_cerchio.py --prova
  venv/bin/python scripts/migra_consenso_cerchio.py
"""
import argparse
import asyncio
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


def _modalita(sub: dict) -> str:
    if (sub.get("source") or "").lower().startswith("prelaunch"):
        return "prelancio"
    if sub.get("confirmed_at") or sub.get("status") == "confirmed":
        return "doppio"
    return "singolo-senza-prova"


async def main(prova: bool) -> None:
    from database import db
    from services.testi_consenso import TESTI, versione_storica

    consensi = gia = backfill = 0
    per_modalita: Counter = Counter()
    per_versione: Counter = Counter()
    async for sub in db.aurya_subscribers.find(
            {}, {"_id": 0, "email": 1, "source": 1, "status": 1, "consent": 1,
                 "consent_at": 1, "created_at": 1, "confirmed_at": 1,
                 "consenso": 1, "verificato_at": 1}):
        set_: dict = {}
        if not (sub.get("consenso") or {}).get("versione"):
            modalita = _modalita(sub)
            versione = versione_storica(sub.get("source"))
            set_["consenso"] = {
                "at": sub.get("consent_at") or sub.get("created_at"),
                "testo": TESTI[versione], "versione": versione,
                "ip": None, "user_agent": None,
                "pagina": sub.get("source"),
                "modalita": modalita, "da_migrazione": True,
            }
            per_modalita[modalita] += 1
            per_versione[versione] += 1
            consensi += 1
        else:
            gia += 1
        if sub.get("confirmed_at") and not sub.get("verificato_at"):
            set_["verificato_at"] = sub["confirmed_at"]
            set_["verificato_da"] = {"tipo": "conferma", "dettaglio": "backfill 24/9", "at": sub["confirmed_at"]}
            backfill += 1
        if set_ and not prova:
            await db.aurya_subscribers.update_one({"email": sub["email"]}, {"$set": set_})

    pre = "PROVA — " if prova else ""
    print(f"{pre}consenso: da scrivere {consensi}, gia' col registro {gia}; "
          f"verificato_at da backfill {backfill}")
    for m, n in per_modalita.most_common():
        print(f"  modalita {m:22s} {n:3d}")
    for v, n in per_versione.most_common():
        print(f"  versione {v:22s} {n:3d}")


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--prova", action="store_true", help="conta e mostra, non scrive")
    asyncio.run(main(p.parse_args().prova))
