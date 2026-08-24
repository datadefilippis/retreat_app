#!/usr/bin/env python3
"""Import di sound_new nella libreria di Aurya (24/8/2026).

Legge il CSV del censimento (scripts/censimento_sound_new.py) — che
l'autore può aver corretto a mano nella colonna `categoria_proposta` —
copia i file nella cartella delle basi con nome content-addressed e
crea i documenti in `audio_assets` con:

  · titolo leggibile (dal censimento, correggibile nel CSV)
  · categoria   — com'è fatto il suono (timbro)
  · momento     — a che punto del viaggio serve (l'asse del founder)
  · licenza     — la nota che dichiara la fonte (--licenza)

Salta i duplicati (impronta md5, colonna `duplicato_di`) e i file già
importati (stessa impronta già in libreria): si può rilanciare senza
paura di raddoppiare la libreria.

NON genera i tappeti: quelli li fa scripts/prepara_tappeti.py, che va
lanciato dopo sulla cartella delle basi (serve afconvert, sul Mac).

Uso:
  python3 scripts/importa_sound_new.py ~/Desktop/sound_new \\
      --licenza "Pixabay Content License" [--prova]
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
MIME = {"mp3": "audio/mpeg", "m4a": "audio/mp4",
        "ogg": "audio/ogg", "wav": "audio/wav"}


async def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cartella")
    ap.add_argument("--csv", default=None, help="default: <cartella>/censimento.csv")
    ap.add_argument("--licenza", default="", help="la fonte, scritta su ogni traccia")
    ap.add_argument("--prova", action="store_true", help="dice cosa farebbe, non tocca nulla")
    args = ap.parse_args()

    radice = os.path.expanduser(args.cartella)
    percorso_csv = args.csv or os.path.join(radice, "censimento.csv")
    if not os.path.exists(percorso_csv):
        sys.exit(f"censimento non trovato: {percorso_csv}\n"
                 f"Lancia prima scripts/censimento_sound_new.py")

    from database import audio_assets_collection
    from models.audio_asset import clean_category, clean_moment
    from models.common import utc_now

    # cio' che la libreria ha GIA': si riconosce dall'impronta, non dal
    # nome (lo stesso brano puo' essere stato caricato con un titolo
    # diverso) — cosi' lo script si rilancia senza duplicare
    esistenti = {}
    async for a in audio_assets_collection.find({}, {"_id": 0, "id": 1, "stream_url": 1,
                                                     "sha1": 1, "title": 1}):
        if a.get("sha1"):
            esistenti[a["sha1"]] = a.get("title")

    righe = list(csv.DictReader(open(percorso_csv, encoding="utf-8")))
    fatti = saltati_dup = saltati_gia = errori = 0
    per_momento = {}

    for r in righe:
        if r.get("duplicato_di"):
            saltati_dup += 1
            continue
        origine = os.path.join(radice, r["momento"], r["file"])
        if not os.path.exists(origine):
            print(f"  MANCA  {r['momento']}/{r['file']}")
            errori += 1
            continue
        with open(origine, "rb") as fh:
            dati = fh.read()
        impronta = hashlib.sha1(dati).hexdigest()
        if impronta in esistenti:
            saltati_gia += 1
            continue

        cat = clean_category((r.get("categoria_proposta") or "").strip()) or "ambient"
        mom = clean_moment(r["momento"])
        ext = r["file"].rsplit(".", 1)[-1].lower()
        asset_id = str(uuid.uuid4())
        nome_file = f"{asset_id}.{ext}"

        if args.prova:
            print(f"  [prova] {r['titolo_proposto'][:44]:46} {cat:12} {mom:12} {r['durata']}")
        else:
            os.makedirs(AUDIO_DIR, exist_ok=True)
            shutil.copyfile(origine, os.path.join(AUDIO_DIR, nome_file))
            await audio_assets_collection.insert_one({
                "id": asset_id,
                "owner": "platform",
                "title": r["titolo_proposto"][:80],
                "category": cat,
                "moment": mom,
                "duration_sec": round(float(r["durata_sec"] or 0), 1),
                "size_bytes": len(dati),
                "mime": MIME.get(ext, "audio/mpeg"),
                "stream_url": f"/uploads/audio/{nome_file}",
                "license_note": args.licenza[:300],
                "sha1": impronta,          # l'impronta: il riconoscimento
                "uploaded_by": "import:sound_new",
                "created_at": utc_now(),
            })
        esistenti[impronta] = r["titolo_proposto"]
        per_momento[mom] = per_momento.get(mom, 0) + 1
        fatti += 1

    print(f"\n{'PROVA — nulla e stato scritto' if args.prova else 'IMPORTATE'}: {fatti}")
    for m in ("arrivo", "attivazione", "catarsi", "ascesa", "rientro"):
        if per_momento.get(m):
            print(f"  {m:14} {per_momento[m]}")
    print(f"saltati duplicati: {saltati_dup} · gia' in libreria: {saltati_gia} · errori: {errori}")
    if not args.prova and fatti:
        print("\nORA: lancia scripts/prepara_tappeti.py sulla cartella delle basi,\n"
              "poi carica file + tappeti in produzione e collega tappeto_url.")


if __name__ == "__main__":
    asyncio.run(main())
