#!/usr/bin/env python3
"""P4 «formato» (6/10/2026) — la regia assegna il formato (ritiro · evento ·
formazione) alle esperienze nate PRIMA del campo. Nessun backfill
automatico: la formazione non si indovina dalle date, la decide chi
guarda il titolo. Si lancia dal container backend in produzione:

  python scripts/formato_esperienze.py --lista
      tutte le esperienze (bozze e pubblicate) con prefisso id, date,
      disciplina, formato attuale e formato suggerito dalle date

  python scripts/formato_esperienze.py --imposta d773d469=formazione --imposta fbea1186=ritiro
      prova generale: dice cosa cambierebbe, non scrive

  python scripts/formato_esperienze.py --imposta ... --scrivi
      scrive davvero (solo metadata.formato, nient'altro sulla riga)

Le chiavi sono i primi 8 caratteri dell'id prodotto (come li stampa
--lista); un prefisso ambiguo ferma tutto. Un formato fuori lista ferma
tutto. Idempotente: un valore gia' uguale non si riscrive.
"""
from __future__ import annotations

import argparse
import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.retreat_taxonomy import FORMATI_ESPERIENZA, formato_suggerito  # noqa: E402


async def _righe():
    from database import event_occurrences_collection, products_collection, organizations_collection
    occs = await event_occurrences_collection.find(
        {"status": {"$in": ["draft", "published"]}},
        {"_id": 0, "product_id": 1, "start_at": 1, "end_at": 1, "status": 1,
         "organization_id": 1}).to_list(5000)
    pids = list({o["product_id"] for o in occs})
    prods = {p["id"]: p async for p in products_collection.find(
        {"id": {"$in": pids}, "item_type": "event_ticket"},
        {"_id": 0, "id": 1, "name": 1, "category": 1, "metadata.formato": 1,
         "organization_id": 1})}
    orgs = {o["id"]: o.get("name") async for o in organizations_collection.find(
        {"id": {"$in": list({o["organization_id"] for o in occs})}},
        {"_id": 0, "id": 1, "name": 1})}
    righe = []
    visti = set()
    for o in sorted(occs, key=lambda x: x.get("start_at") or ""):
        p = prods.get(o["product_id"])
        if not p or p["id"] in visti:
            continue
        visti.add(p["id"])
        righe.append({
            "id": p["id"], "nome": p.get("name"), "categoria": p.get("category"),
            "org": orgs.get(o["organization_id"]), "stato": o.get("status"),
            "inizio": (o.get("start_at") or "")[:10], "fine": (o.get("end_at") or "")[:10],
            "formato": (p.get("metadata") or {}).get("formato"),
            "suggerito": formato_suggerito(o.get("start_at"), o.get("end_at")),
        })
    return righe


def _stampa(righe):
    print(f"{'id':8} | {'stato':9} | {'inizio':10} → {'fine':10} | {'disciplina':12} | {'formato':10} | {'sugg.':10} | nome · professionista")
    for r in righe:
        print(f"{r['id'][:8]} | {r['stato']:9} | {r['inizio']:10} → {r['fine']:10} | "
              f"{(r['categoria'] or '-'):12} | {(r['formato'] or '-'):10} | {r['suggerito']:10} | "
              f"{r['nome']} · {r['org']}")


async def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--lista", action="store_true")
    ap.add_argument("--imposta", action="append", default=[], metavar="PREFISSO=FORMATO")
    ap.add_argument("--scrivi", action="store_true", help="senza questo flag e' una prova generale")
    a = ap.parse_args()

    righe = await _righe()
    if a.lista or not a.imposta:
        _stampa(righe)
        if not a.imposta:
            return 0

    piano = []
    for voce in a.imposta:
        if "=" not in voce:
            print(f"FERMO: «{voce}» non e' PREFISSO=FORMATO"); return 2
        pref, fmt = voce.split("=", 1)
        if fmt not in FORMATI_ESPERIENZA:
            print(f"FERMO: formato «{fmt}» fuori lista ({', '.join(FORMATI_ESPERIENZA)})"); return 2
        trovati = [r for r in righe if r["id"].startswith(pref)]
        if len(trovati) != 1:
            print(f"FERMO: prefisso «{pref}» trova {len(trovati)} esperienze (ne serve una)"); return 2
        piano.append((trovati[0], fmt))

    from database import products_collection
    cambiati = 0
    for r, fmt in piano:
        if r["formato"] == fmt:
            print(f"  = {r['id'][:8]} {r['nome']!r}: gia' «{fmt}»")
            continue
        print(f"  {'SCRIVO' if a.scrivi else 'scriverei'} {r['id'][:8]} {r['nome']!r}: "
              f"«{r['formato'] or '-'}» → «{fmt}»")
        if a.scrivi:
            res = await products_collection.update_one(
                {"id": r["id"], "item_type": "event_ticket"},
                {"$set": {"metadata.formato": fmt}})
            cambiati += res.modified_count
    print(f"{'scritte' if a.scrivi else 'da scrivere (prova generale, aggiungi --scrivi)'}: "
          f"{cambiati if a.scrivi else sum(1 for r, f in piano if r['formato'] != f)}")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
