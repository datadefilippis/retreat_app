"""Backfill del legame dei cappelli — ciclo ID (20/8/2026).

Trova le email che vivono VERIFICATE in entrambi i mondi (`users` e
`platform_accounts`) e mette in piedi il legame che la porta unica usa
per l'SSO. Riusa identity_link_service: stesse regole, zero logica
duplicata. Idempotente: rilanciarlo non cambia nulla di gia' collegato.

Uso:
    venv/bin/python -m scripts.link_identity_hats           # esegue
    venv/bin/python -m scripts.link_identity_hats --dry-run # solo conta
"""

import asyncio
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))


async def main(dry_run: bool):
    from database import platform_accounts_collection, users_collection
    from services.identity_link_service import auto_link_by_email

    emails = await platform_accounts_collection.distinct("email")
    fatti = saltati = 0
    for email in emails:
        user = await users_collection.find_one({"email": email}, {"_id": 1})
        if not user:
            continue
        if dry_run:
            print(f"  ~ candidata: {email}")
            fatti += 1
            continue
        if await auto_link_by_email(email):
            print(f"  ✓ collegata: {email}")
            fatti += 1
        else:
            # esiste nei due mondi ma NON verificata da entrambe le
            # parti: il legame nascera' da solo alla verifica (hook)
            print(f"  · in attesa di verifica: {email}")
            saltati += 1
    print(f"\n{fatti} legami{' candidati' if dry_run else ''}, "
          f"{saltati} in attesa di verifica")


if __name__ == "__main__":
    asyncio.run(main("--dry-run" in sys.argv))
