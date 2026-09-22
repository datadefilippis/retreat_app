#!/usr/bin/env python3
"""IL PACCHETTO DELLA LIBRERIA (22/9/2026) — porta in produzione i suoni
importati in locale CON GLI STESSI ID.

Perche' esiste: gli script di import (importa_sound_new, importa_respiro)
generano l'id alla creazione, e i tappeti si chiamano con quell'id.
Rilanciare l'import in produzione darebbe id diversi, tappeti da
rifare (afconvert non c'e' nel container) e due libreria che non si
parlano. Il pacchetto invece e' una copia esatta: documenti + file
+ tappeti, idempotente per impronta (sha1) e per id.

  esporta   scrive <dir>/documenti.json e copia i file (base + tappeto)
            di ogni asset creato da --dal (default: oggi UTC) o con
            --uploaded-by; in prod si porta la cartella con docker cp.
  importa   inserisce i documenti che mancano (ne' id ne' sha1 gia'
            presenti) e copia i file in uploads/audio; --prova dice cosa
            farebbe. Un asset presente per sha1 ma con un altro id NON
            viene toccato: lo si dice, e si decide a mano.

Uso:
  python3 scripts/pacchetto_libreria.py esporta ~/Desktop/pacchetto_2026-09-22 --dal 2026-09-22
  # in prod (nel container backend):
  python3 scripts/pacchetto_libreria.py importa /app/uploads/pacchetto [--prova]
"""
import argparse
import asyncio
import json
import os
import shutil
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

AUDIO_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                         "uploads", "audio")
CAMPI_DATA = ("created_at", "updated_at")


def _nome(url):
    return url.rsplit("/", 1)[-1] if url else None


async def esporta(args):
    from database import audio_assets_collection
    filtro = {}
    if args.uploaded_by:
        filtro["uploaded_by"] = {"$in": args.uploaded_by}
    dal = datetime.strptime(args.dal, "%Y-%m-%d").replace(tzinfo=timezone.utc) if args.dal else None
    if dal:
        filtro["created_at"] = {"$gte": dal}
    docs = await audio_assets_collection.find(filtro, {"_id": 0}).sort("created_at", 1).to_list(5000)
    if not docs:
        sys.exit("nessun asset corrisponde al filtro")
    os.makedirs(os.path.join(args.dir, "file"), exist_ok=True)
    mancanti = 0
    for d in docs:
        for k in CAMPI_DATA:
            if isinstance(d.get(k), datetime):
                d[k] = d[k].isoformat()
        for url in (d.get("stream_url"), d.get("tappeto_url")):
            nome = _nome(url)
            if not nome:
                continue
            src = os.path.join(AUDIO_DIR, nome)
            if not os.path.exists(src):
                print(f"  MANCA IL FILE  {nome}  ({d['title']})")
                mancanti += 1
                continue
            shutil.copyfile(src, os.path.join(args.dir, "file", nome))
    with open(os.path.join(args.dir, "documenti.json"), "w", encoding="utf-8") as fh:
        json.dump(docs, fh, ensure_ascii=False, indent=1)
    peso = sum(os.path.getsize(os.path.join(args.dir, "file", f))
               for f in os.listdir(os.path.join(args.dir, "file")))
    print(f"ESPORTATI {len(docs)} documenti, {len(os.listdir(os.path.join(args.dir, 'file')))} file, "
          f"{peso / 1048576:.0f} MB in {args.dir} · file mancanti: {mancanti}")


async def importa(args):
    from database import audio_assets_collection
    percorso = os.path.join(args.dir, "documenti.json")
    if not os.path.exists(percorso):
        sys.exit(f"manca {percorso}")
    docs = json.load(open(percorso, encoding="utf-8"))
    ids = {a["id"] for a in await audio_assets_collection.find({}, {"_id": 0, "id": 1}).to_list(5000)}
    sha = {a["sha1"]: a["id"] for a in await audio_assets_collection.find(
        {"sha1": {"$exists": True}}, {"_id": 0, "id": 1, "sha1": 1}).to_list(5000)}
    fatti = gia = conflitti = senza_file = 0
    for d in docs:
        if d["id"] in ids:
            gia += 1
            continue
        if d.get("sha1") and d["sha1"] in sha:
            print(f"  STESSA IMPRONTA, ALTRO ID  «{d['title']}»: qui e' {sha[d['sha1']]} — non tocco")
            conflitti += 1
            continue
        nomi = [n for n in (_nome(d.get("stream_url")), _nome(d.get("tappeto_url"))) if n]
        sorgenti = [os.path.join(args.dir, "file", n) for n in nomi]
        if not all(os.path.exists(s) for s in sorgenti):
            print(f"  FILE MANCANTE NEL PACCHETTO  «{d['title']}»")
            senza_file += 1
            continue
        if args.prova:
            print(f"  [prova] {d['title'][:48]:50} {d.get('category', ''):12} {d.get('moment') or '-':12}"
                  f"{' +tappeto' if d.get('tappeto_url') else ''}")
        else:
            os.makedirs(AUDIO_DIR, exist_ok=True)
            for n, s in zip(nomi, sorgenti):
                dest = os.path.join(AUDIO_DIR, n)
                if not os.path.exists(dest):
                    shutil.copyfile(s, dest)
            doc = dict(d)
            for k in CAMPI_DATA:
                if isinstance(doc.get(k), str):
                    doc[k] = datetime.fromisoformat(doc[k])
            await audio_assets_collection.insert_one(doc)
        ids.add(d["id"])
        fatti += 1
    print(f"\n{'PROVA' if args.prova else 'IMPORTATI'}: {fatti} · gia' presenti (id): {gia} · "
          f"conflitti d'impronta: {conflitti} · senza file: {senza_file}")


async def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    e = sub.add_parser("esporta")
    e.add_argument("dir")
    e.add_argument("--dal", default=datetime.now(timezone.utc).strftime("%Y-%m-%d"))
    e.add_argument("--uploaded-by", nargs="*", default=None)
    i = sub.add_parser("importa")
    i.add_argument("dir")
    i.add_argument("--prova", action="store_true")
    args = ap.parse_args()
    args.dir = os.path.expanduser(args.dir)
    await (esporta(args) if args.cmd == "esporta" else importa(args))


if __name__ == "__main__":
    asyncio.run(main())
