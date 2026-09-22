#!/usr/bin/env python3
"""Collega i tappeti alle basi (CI, 22/9/2026).

`prepara_tappeti.py` scrive `{nome}.tappeto.m4a` accanto alla base ma non
tocca Mongo (gira sul Mac, senza database). Questo script chiude il giro:
per ogni `audio_assets` con `stream_url` /uploads/audio/{nome}.{ext},
se esiste il file {nome}.tappeto.m4a scrive `tappeto_url`. Idempotente,
rilanciabile in locale e nel container di produzione (`--dir` per la
cartella delle basi, default uploads/audio accanto al backend).

    python scripts/collega_tappeti.py [--dir /app/uploads/audio] [--prova]
"""
import argparse
import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DEFAULT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "uploads", "audio")


async def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", default=DEFAULT_DIR)
    ap.add_argument("--prova", action="store_true")
    args = ap.parse_args()
    from database import audio_assets_collection
    collegati = gia = senza = 0
    async for a in audio_assets_collection.find({}, {"_id": 0, "id": 1, "stream_url": 1, "tappeto_url": 1, "title": 1}):
        url = a.get("stream_url") or ""
        nome = os.path.basename(url)
        base, _, _ = nome.rpartition(".")
        if not base:
            continue
        tappeto = f"{base}.tappeto.m4a"
        if not os.path.exists(os.path.join(args.dir, tappeto)):
            senza += 1
            continue
        atteso = f"/uploads/audio/{tappeto}"
        if a.get("tappeto_url") == atteso:
            gia += 1
            continue
        print(f"  {'[prova] ' if args.prova else ''}collego  {a.get('title', '')[:40]:42} → {tappeto}")
        if not args.prova:
            await audio_assets_collection.update_one({"id": a["id"]}, {"$set": {"tappeto_url": atteso}})
        collegati += 1
    print(f"\ncollegati: {collegati} · gia' collegati: {gia} · senza tappeto (corti): {senza}")


if __name__ == "__main__":
    asyncio.run(main())
