#!/usr/bin/env python3
"""CI-F1 (22/9/2026) — importa i clip del respiro nella libreria.

Legge `respiro.csv` (scritto da scripts/prepara_respiro.py), copia i
file in uploads/audio con nome content-addressed e crea i documenti in
`audio_assets`: categoria `respiro`, momento `attivazione`, e i due
campi della GUIDA DEL RESPIRO:

  · guida      ciclo | inspira | espira | conta | soffio_in | soffio_out
  · ciclo_sec  per i `ciclo`: ogni quanti secondi il clip ricomincia

E' l'unico posto in cui la voce del founder entra nella piattaforma:
`owner: platform`, licenza «Aurya · voce registrata dal founder».
Idempotente per impronta (sha1): si rilancia senza duplicare.

In produzione: docker cp della cartella in /app/uploads/respiro_in e
  compose exec backend python scripts/importa_respiro.py /app/uploads/respiro_in

Uso:
  python3 scripts/importa_respiro.py ~/Desktop/memo_pronti [--prova]
"""
import argparse
import asyncio
import csv
import hashlib
import os
import shutil
import sys
import uuid

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

AUDIO_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                         "uploads", "audio")
LICENZA = "Aurya · voce registrata dal founder (22/9/2026)"


async def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cartella")
    ap.add_argument("--prova", action="store_true")
    args = ap.parse_args()
    radice = os.path.expanduser(args.cartella)
    percorso_csv = os.path.join(radice, "respiro.csv")
    if not os.path.exists(percorso_csv):
        sys.exit(f"manca {percorso_csv}: lancia prima scripts/prepara_respiro.py")

    from database import audio_assets_collection
    from models.audio_asset import clean_guida, clean_ciclo_sec
    from models.common import utc_now

    esistenti = set()
    async for a in audio_assets_collection.find({"sha1": {"$exists": True}}, {"_id": 0, "sha1": 1}):
        esistenti.add(a["sha1"])

    fatti = gia = errori = 0
    for r in csv.DictReader(open(percorso_csv, encoding="utf-8")):
        origine = os.path.join(radice, r["file"])
        if not os.path.exists(origine):
            print(f"  MANCA  {r['file']}"); errori += 1; continue
        guida = clean_guida(r.get("guida"))
        ciclo = clean_ciclo_sec(r.get("ciclo_sec")) if guida == "ciclo" else None
        if not guida or (guida == "ciclo" and not ciclo):
            print(f"  RIGA NON VALIDA  {r['file']} guida={r.get('guida')} ciclo={r.get('ciclo_sec')}")
            errori += 1; continue
        dati = open(origine, "rb").read()
        impronta = hashlib.sha1(dati).hexdigest()
        if impronta in esistenti:
            gia += 1; continue
        asset_id = str(uuid.uuid4())
        nome_file = f"{asset_id}.m4a"
        if args.prova:
            print(f"  [prova] {r['titolo'][:48]:50} {guida:10} {ciclo or ''}")
        else:
            os.makedirs(AUDIO_DIR, exist_ok=True)
            shutil.copyfile(origine, os.path.join(AUDIO_DIR, nome_file))
            await audio_assets_collection.insert_one({
                "id": asset_id,
                "owner": "platform",
                "title": r["titolo"][:80],
                "category": "respiro",
                "moment": "attivazione",
                "guida": guida,
                "ciclo_sec": ciclo,
                "tags": ["guida", "respiro", guida],
                "duration_sec": round(float(r.get("durata_sec") or 0), 2),
                "size_bytes": len(dati),
                "mime": "audio/mp4",
                "stream_url": f"/uploads/audio/{nome_file}",
                "license_note": LICENZA,
                "sha1": impronta,
                "uploaded_by": "import:respiro",
                "created_at": utc_now(),
            })
        esistenti.add(impronta)
        fatti += 1
    print(f"\n{'PROVA' if args.prova else 'IMPORTATI'}: {fatti} · gia' in libreria: {gia} · errori: {errori}")


if __name__ == "__main__":
    asyncio.run(main())
