#!/usr/bin/env python3
"""P1 (24/9/2026) — il nome della PERSONA per gli operatori gia' iscritti.

I profili nati prima di P1 non hanno `public_profile.nome_persona`: il
pubblico continua a vedere solo il marchio, identico a prima. Questo
script NON decide da solo: `users.name` in produzione e' a qualita'
mista («Ilaria Barbaccia Barbaccia», «claudia Rossato», «Anpoche»).

  proponi  → CSV con una riga per operatore: org, marchio attuale, nome
             utente, PROPOSTA ripulita (maiuscole, doppioni), come
             verrebbe il nome pubblico, e una nota dove serve un occhio.
             Il founder corregge la colonna `nome_persona` (o la svuota).
  applica  → legge il CSV rivisto e scrive `nome_persona` SOLO dove la
             colonna e' piena; --prova mostra prima/dopo senza scrivere.

Uso:
  python3 scripts/proponi_nome_persona.py proponi docs/sound/../nomi.csv
  python3 scripts/proponi_nome_persona.py applica nomi.csv [--prova]
"""
import argparse
import asyncio
import csv
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.nome_pubblico import nome_pubblico, contiene_persona  # noqa: E402

PARTICELLE = {"di", "de", "del", "della", "da", "dal", "la", "le", "lo", "e", "van", "von"}


def ripulisci(nome: str) -> str:
    parole = [p for p in re.split(r"\s+", (nome or "").strip()) if p]
    out = []
    for p in parole:
        if out and out[-1].casefold() == p.casefold():
            continue                      # «Barbaccia Barbaccia»
        if p.casefold() in PARTICELLE and out:
            out.append(p.lower())
        else:
            out.append("-".join(x[:1].upper() + x[1:].lower() for x in p.split("-")))
    return " ".join(out)


async def proponi(percorso: str) -> None:
    from database import organizations_collection, users_collection
    righe = []
    async for o in organizations_collection.find(
            {"public_slug": {"$exists": True, "$ne": None}, "is_sample": {"$ne": True}},
            {"_id": 0, "id": 1, "name": 1, "public_slug": 1, "public_profile.nome_persona": 1}).sort("created_at", 1):
        u = await users_collection.find_one({"organization_id": o["id"], "role": "admin"},
                                            {"_id": 0, "name": 1}, sort=[("created_at", 1)])
        attuale = ((o.get("public_profile") or {}).get("nome_persona") or "")
        utente = (u or {}).get("name") or ""
        proposta = attuale or ripulisci(utente)
        nota = ""
        if not attuale:
            if not proposta:
                nota = "nessun nome utente: scriverlo a mano"
            elif len(proposta.split()) < 2:
                nota = "una parola sola: aggiungere il cognome?"
            if proposta and proposta.casefold() == (o.get("name") or "").casefold():
                nota = "nome utente = marchio: e' una persona?"
        anteprima = nome_pubblico({"name": o.get("name"), "public_profile": {"nome_persona": proposta}})
        righe.append({"org_id": o["id"], "slug": o.get("public_slug"), "marchio": o.get("name") or "",
                      "nome_utente": utente, "nome_persona": proposta, "nome_pubblico_risultante": anteprima,
                      "gia_impostato": "si" if attuale else "", "nota": nota})
    with open(percorso, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(righe[0].keys()))
        w.writeheader()
        w.writerows(righe)
    print(f"proposte: {len(righe)} → {percorso}")
    for r in righe:
        print(f"  {r['marchio'][:34]:34} | {r['nome_persona'][:26]:26} → {r['nome_pubblico_risultante'][:50]:50} {r['nota']}")


async def applica(percorso: str, prova: bool) -> None:
    from database import organizations_collection
    n = 0
    for r in csv.DictReader(open(percorso, encoding="utf-8")):
        nome = " ".join((r.get("nome_persona") or "").split()).strip()[:80]
        if not nome:
            continue
        o = await organizations_collection.find_one({"id": r["org_id"]}, {"_id": 0, "name": 1, "public_profile": 1})
        if not o:
            print(f"  MANCA {r['org_id']}")
            continue
        prima = nome_pubblico(o)
        dopo = nome_pubblico({**o, "public_profile": {**(o.get("public_profile") or {}), "nome_persona": nome}})
        print(f"  {'[prova] ' if prova else ''}{prima[:44]:44} → {dopo}")
        if not prova:
            await organizations_collection.update_one({"id": r["org_id"]}, {"$set": {"public_profile.nome_persona": nome}})
        n += 1
    print(f"{'PROVA' if prova else 'APPLICATI'}: {n}")


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("proponi"); p.add_argument("csv")
    a = sub.add_parser("applica"); a.add_argument("csv"); a.add_argument("--prova", action="store_true")
    args = ap.parse_args()
    asyncio.run(proponi(args.csv) if args.cmd == "proponi" else applica(args.csv, args.prova))


if __name__ == "__main__":
    main()
