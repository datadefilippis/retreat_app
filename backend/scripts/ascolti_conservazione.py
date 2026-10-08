"""CS5 — la conservazione degli ascolti: 24 mesi, poi via.

A secco di default (dice quanti ne toglierebbe); `--applica` cancella.
Idempotente: il backend lo fa gia' a ogni avvio, questo serve alla regia.
  cd backend && venv/bin/python scripts/ascolti_conservazione.py --applica
"""
import argparse
import asyncio
import os
import sys
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


async def main(applica: bool) -> int:
    from database import db
    from services.ascolti_regia import CONSERVAZIONE_GIORNI, conserva
    soglia = datetime.now(timezone.utc) - timedelta(days=CONSERVAZIONE_GIORNI)
    n = await db.sound_ascolti.count_documents({"at": {"$lt": soglia}})
    print(f"eventi oltre i {CONSERVAZIONE_GIORNI} giorni: {n}")
    if applica and n:
        print("cancellati:", await conserva())
    elif n:
        print("a secco: niente cancellato (usa --applica)")
    return 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--applica", action="store_true")
    sys.exit(asyncio.run(main(ap.parse_args().applica)))
