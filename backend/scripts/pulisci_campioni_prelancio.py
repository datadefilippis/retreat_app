#!/usr/bin/env python3
"""Rimuove i CAMPIONI del pre-lancio (25/8/2026, decisione founder).

Il 10 luglio, per non aprire con una vetrina vuota, furono seminate 6
organizzazioni di esempio con 10 ritiri inventati in località reali
(Ostuni, Bolzano, Todi…). Servivano al soft-launch; oggi la rete ha
professionisti VERI e quelle schede sono l'unica cosa che, se
indicizzata, direbbe a Google e alle persone qualcosa di falso.

Il founder (25/8): «i ritiri fake possiamo rimuoverli e ripulirli, il
marketplace dei ritiri lo lasciamo vuoto e lo indicizziamo così».

COSA TOCCA: solo le organizzazioni con `is_sample: true` e ciò che
appartiene a loro (store, prodotti, occorrenze, indici derivati).

COSA NON TOCCA MAI: qualunque organizzazione senza quel flag. E se una
campione avesse anche UN ordine o UN cliente, si ferma tutto — quel
flag sarebbe finito per errore su un'organizzazione vera, e cancellare
sarebbe l'errore irreparabile. Verificato prima di scrivere questo
script: 0 ordini, 0 clienti.

Uso:
  python3 scripts/pulisci_campioni_prelancio.py --prova     # dice cosa farebbe
  python3 scripts/pulisci_campioni_prelancio.py --esegui    # lo fa
"""
import argparse
import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


async def main():
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--prova", action="store_true", help="non scrive nulla")
    g.add_argument("--esegui", action="store_true", help="cancella davvero")
    args = ap.parse_args()

    from database import (organizations_collection, products_collection,
                          event_occurrences_collection, stores_collection,
                          orders_collection, customers_collection)
    try:
        from database import availability_index_collection
    except ImportError:
        availability_index_collection = None

    orgs = await organizations_collection.find(
        {"is_sample": True},
        {"_id": 0, "id": 1, "name": 1, "public_slug": 1},
    ).to_list(200)
    if not orgs:
        print("Nessuna organizzazione campione: niente da fare.")
        return
    ids = [o["id"] for o in orgs]

    print(f"Organizzazioni campione trovate: {len(orgs)}")
    for o in orgs:
        print(f"  · {o.get('name')}  ({o.get('public_slug')})")

    # ── LE GUARDIE ────────────────────────────────────────────────────
    # 1. nessuna di loro deve avere un proprietario: un campione non ha
    #    account collegati. Se ne ha uno, e' una persona vera.
    from database import users_collection
    con_utenti = await users_collection.count_documents(
        {"organization_id": {"$in": ids}})
    # 2. nessun ordine, nessun cliente: se qualcuno ha comprato, quei
    #    dati sono di una persona reale e non si cancellano mai.
    ordini = await orders_collection.count_documents(
        {"organization_id": {"$in": ids}})
    clienti = await customers_collection.count_documents(
        {"organization_id": {"$in": ids}})
    print(f"\nControlli: utenti collegati={con_utenti} · "
          f"ordini={ordini} · clienti={clienti}")
    if con_utenti or ordini or clienti:
        sys.exit("FERMO: una campione ha utenti, ordini o clienti veri.\n"
                 "Il flag is_sample e' finito su un'organizzazione reale: "
                 "va tolto a mano, non si cancella niente.")

    prodotti = await products_collection.count_documents(
        {"organization_id": {"$in": ids}})
    occorrenze = await event_occurrences_collection.count_documents(
        {"organization_id": {"$in": ids}})
    negozi = await stores_collection.count_documents(
        {"organization_id": {"$in": ids}})
    print(f"Da rimuovere: {negozi} store · {prodotti} prodotti · "
          f"{occorrenze} occorrenze · {len(ids)} organizzazioni")

    if args.prova:
        print("\nPROVA: non e' stato scritto nulla.")
        return

    filtro = {"organization_id": {"$in": ids}}
    r_occ = await event_occurrences_collection.delete_many(filtro)
    r_pro = await products_collection.delete_many(filtro)
    r_sto = await stores_collection.delete_many(filtro)
    if availability_index_collection is not None:
        await availability_index_collection.delete_many(filtro)
    r_org = await organizations_collection.delete_many({"id": {"$in": ids}})

    print(f"\nFATTO: occorrenze={r_occ.deleted_count} "
          f"prodotti={r_pro.deleted_count} store={r_sto.deleted_count} "
          f"organizzazioni={r_org.deleted_count}")
    print("Il marketplace dei ritiri e' ora VUOTO e onesto: si riempira'"
          "\nda solo quando i professionisti pubblicheranno i loro eventi.")


if __name__ == "__main__":
    asyncio.run(main())
