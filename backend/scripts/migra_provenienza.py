"""Lotto B1 (24/9/2026) — scrive `provenienza` agli iscritti che non
ce l'hanno, traducendo la fonte grezza con services/provenienza.py.

`source` NON si tocca. Idempotente: chi ha una provenienza scritta
all'iscrizione (dal form) non viene mai riscritto; chi l'ha avuta da
questo script (`da_migrazione: True`) viene ricalcolato, cosi' se la
tabella migliora basta rilanciarlo.

Uso (da backend/, con l'env caricato):
  venv/bin/python scripts/migra_provenienza.py --prova   # solo il conto
  venv/bin/python scripts/migra_provenienza.py           # scrive
"""
import argparse
import asyncio
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


async def main(prova: bool) -> None:
    from database import db
    from services.provenienza import classifica

    scritti = invariati = saltati = 0
    per_canale: Counter = Counter()
    esempi: dict = {}
    async for sub in db.aurya_subscribers.find(
            {}, {"_id": 0, "email": 1, "source": 1, "provenienza": 1}):
        prov = sub.get("provenienza") or {}
        if prov.get("canale") and not prov.get("da_migrazione"):
            saltati += 1                 # scritta dal form: e' la verita'
            continue
        nuova = {**classifica(sub.get("source")), "url": None, "referrer": None,
                 "utm": None, "dispositivo": None, "da_migrazione": True}
        chiave = f"{nuova['canale']} › {nuova['superficie']}"
        per_canale[chiave] += 1
        esempi.setdefault(chiave, sub.get("source"))
        if prov and all(prov.get(k) == nuova.get(k) for k in ("canale", "superficie", "dettaglio", "porta")):
            invariati += 1
            continue
        if not prova:
            await db.aurya_subscribers.update_one(
                {"email": sub["email"]}, {"$set": {"provenienza": nuova}})
        scritti += 1

    print(f"{'PROVA — ' if prova else ''}provenienza: da scrivere {scritti}, gia' uguali {invariati}, "
          f"scritte dal form (intoccabili) {saltati}")
    for chiave, n in per_canale.most_common():
        print(f"  {n:3d}  {chiave:40s} es. source={esempi[chiave]!r}")


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--prova", action="store_true", help="conta e mostra, non scrive")
    asyncio.run(main(p.parse_args().prova))
