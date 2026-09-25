"""25/9/2026 — le email degli utenti in minuscolo, una volta per tutte.

Caso vero (24/9): «Spaziomarilisa@gmail.com» e «spaziomarilisa@gmail.com»
erano due account, perche' l'indice unico distingue le maiuscole e la
registrazione non normalizzava. Da oggi i modelli normalizzano; questo
script allinea il pregresso. Se la versione minuscola esiste GIA' (un
doppione vero) NON tocca nulla e lo segnala: quello si risolve a mano.

Uso:
  python3 scripts/normalizza_email_utenti.py --prova
  python3 scripts/normalizza_email_utenti.py
"""
import argparse
import asyncio
import os
import re
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import db  # noqa: E402


async def main(prova: bool) -> None:
    n_ok = n_conf = 0
    async for u in db.users.find({"email": re.compile("[A-Z]")}, {"_id": 0, "id": 1, "email": 1, "organization_id": 1}):
        basso = u["email"].strip().lower()
        altro = await db.users.find_one({"email": basso}, {"_id": 0, "id": 1, "organization_id": 1, "created_at": 1})
        if altro:
            n_conf += 1
            print(f"  DOPPIONE {u['email']} (org {u['organization_id']}) ↔ {basso} (org {altro['organization_id']}, dal {str(altro.get('created_at'))[:10]}): non tocco, si decide a mano")
            continue
        print(f"  {'[prova] ' if prova else ''}{u['email']} → {basso}")
        if not prova:
            await db.users.update_one({"id": u["id"]}, {"$set": {"email": basso, "updated_at": datetime.now(timezone.utc).isoformat()}})
        n_ok += 1
    print(f"{'PROVA' if prova else 'FATTO'}: normalizzate {n_ok}, doppioni da risolvere a mano {n_conf}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--prova", action="store_true")
    asyncio.run(main(ap.parse_args().prova))
