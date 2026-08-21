#!/usr/bin/env python3
"""ES2 — comprime le basi entrate in libreria NON compresse.

Il difetto: due basi sono WAV a 1.411 kbps — 5 MB per 30 secondi di
suono. Non e' una scelta di qualita', e' un difetto di ingestione: chi
le ascolta scarica 8 volte i byte che servono, e finiscono cosi' anche
nel backup settimanale.

Perche' e' sicuro cambiare il file sotto un asset esistente:
gli score referenziano l'`asset_id`, MAI l'URL (resolveAudioLayers
risolve `stream_url` al momento dell'ascolto). E siccome la
ricodifica cambia l'estensione (.wav → .m4a), cambia anche l'URL:
nessun rischio con la cache `immutable` di un anno, che e' il motivo
per cui non si sostituiscono MAI i byte sotto lo stesso indirizzo.

Quindi: si ricodifica, si aggiorna il documento, si cancella il vecchio
file. Le sessioni gia' composte continuano a suonare senza toccarle.

    python3 scripts/comprimi_basi_non_compresse.py            # elenco
    python3 scripts/comprimi_basi_non_compresse.py --esegui

Richiede `afconvert` (macOS) oppure `ffmpeg`.
"""
import argparse
import asyncio
import os
import shutil
import subprocess
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent / "backend"
sys.path.insert(0, str(BACKEND))

# oltre questa soglia una base non e' "di qualita'": e' non compressa
SOGLIA_KBPS = 800
BITRATE = 160_000


def _ricodifica(src: Path, dst: Path) -> bool:
    if shutil.which("afconvert"):
        cmd = ["afconvert", "-f", "m4af", "-d", "aac",
               "-b", str(BITRATE), str(src), str(dst)]
    elif shutil.which("ffmpeg"):
        cmd = ["ffmpeg", "-y", "-i", str(src), "-c:a", "aac",
               "-b:a", f"{BITRATE // 1000}k", "-movflags", "+faststart",
               str(dst)]
    else:
        print("ERRORE: serve afconvert (macOS) o ffmpeg")
        return False
    r = subprocess.run(cmd, capture_output=True)
    if r.returncode != 0:
        print(f"  ricodifica fallita: {r.stderr.decode()[:200]}")
        return False
    return dst.exists() and dst.stat().st_size > 0


async def main(esegui: bool):
    from database import db
    uploads = BACKEND / "uploads" / "audio"
    trovate = []
    async for a in db.audio_assets.find({}):
        d, s = a.get("duration_sec") or 0, a.get("size_bytes") or 0
        if d and (s * 8 / 1000 / d) > SOGLIA_KBPS:
            trovate.append(a)

    if not trovate:
        print("Nessuna base non compressa: niente da fare.")
        return

    print(f"{len(trovate)} basi non compresse:\n")
    risparmio = 0
    for a in trovate:
        vecchio_url = a["stream_url"]
        vecchio = uploads / Path(vecchio_url).name
        nuovo = vecchio.with_suffix(".m4a")
        kbps = a["size_bytes"] * 8 / 1000 / a["duration_sec"]
        print(f"  «{a['title']}» ({a['category']}) — "
              f"{a['size_bytes']/1048576:.2f} MB a {kbps:.0f} kbps")

        if not esegui:
            continue
        if not vecchio.exists():
            print("    file assente sul disco: salto")
            continue
        if nuovo.exists():
            print("    il .m4a esiste gia': salto")
            continue
        if not _ricodifica(vecchio, nuovo):
            continue

        nuova_dim = nuovo.stat().st_size
        # PRIMA il documento, POI la cancellazione: se il processo
        # muore in mezzo si resta con un file .wav orfano (innocuo),
        # non con un asset che punta a un file inesistente (muto).
        await db.audio_assets.update_one(
            {"id": a["id"]},
            {"$set": {"stream_url": str(Path(vecchio_url).with_suffix(".m4a")),
                      "mime": "audio/mp4",
                      "size_bytes": nuova_dim}})
        vecchio.unlink()
        risparmio += a["size_bytes"] - nuova_dim
        print(f"    → {nuova_dim/1048576:.2f} MB "
              f"(-{100*(1-nuova_dim/a['size_bytes']):.0f}%)")

    if esegui:
        print(f"\nRisparmiati {risparmio/1048576:.1f} MB "
              f"— per file, a ogni ascolto e in ogni backup.")
    else:
        print("\n(elenco soltanto — rilancia con --esegui)")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--esegui", action="store_true")
    args = ap.parse_args()
    os.environ.setdefault("JWT_SECRET_KEY", "solo-per-importare-database")
    asyncio.run(main(args.esegui))
