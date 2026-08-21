#!/usr/bin/env python3
"""Accorcia le basi oltre la tolleranza, SFUMANDO — mai taglio netto.

Decisione founder (21/8, rivista in serata): STANDARD a 30 minuti
esatti — ogni base che supera i 30:00 si porta a 30 con una dissolvenza
di coda di 12 secondi (mai taglio netto). Il motivo del tetto non è il peso (lo spezzone lo
ha già azzerato): è che l'ascolto a schermo bloccato regge fino a 30
minuti, e nessuna traccia deve restarne esclusa.

Sicurezza cache: i file escono con un NOME NUOVO (uuid) — gli score
referenziano l'asset_id, mai l'URL, quindi le sessioni composte
continuano a suonare; e la cache `immutable` di un anno non può servire
la versione vecchia perché l'indirizzo è nuovo. Ordine: prima il
documento, poi la cancellazione del file vecchio.

    python3 scripts/accorcia_basi_lunghe.py            # elenco
    python3 scripts/accorcia_basi_lunghe.py --esegui

Richiede `afconvert` (macOS). Niente ffmpeg necessario: il fade lo fa
Python sul WAV intermedio (PCM 16 bit, modulo `wave` della stdlib).
"""
import argparse
import asyncio
import math
import os
import shutil
import struct
import subprocess
import sys
import tempfile
import uuid
import wave
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent / "backend"
sys.path.insert(0, str(BACKEND))

# 21/8 sera: il founder RITRATTA la tolleranza — si standardizza a 30
# esatti, sempre con la coda sfumata (mai taglio netto)
TOLLERANZA_SEC = 1800
TARGET_SEC = 1800
FADE_SEC = 12             # la coda si spegne, non si tronca
BITRATE = 160_000


def _sfuma_e_accorcia(src: Path, dst: Path) -> float | None:
    """src (m4a/mp3) → dst (m4a) lungo TARGET_SEC con coda sfumata.
    Ritorna la durata reale o None se qualcosa fallisce."""
    if not shutil.which("afconvert"):
        print("ERRORE: serve afconvert (macOS)")
        return None
    with tempfile.TemporaryDirectory() as td:
        w_in = Path(td) / "in.wav"
        w_out = Path(td) / "out.wav"
        r = subprocess.run(["afconvert", "-f", "WAVE", "-d", "LEI16",
                            str(src), str(w_in)], capture_output=True)
        if r.returncode != 0:
            print(f"  decodifica fallita: {r.stderr.decode()[:150]}")
            return None
        with wave.open(str(w_in), "rb") as fin:
            ch, larghezza, sr = fin.getnchannels(), fin.getsampwidth(), fin.getframerate()
            if larghezza != 2:
                print("  atteso PCM 16 bit"); return None
            frames = min(fin.getnframes(), TARGET_SEC * sr)
            dati = bytearray(fin.readframes(frames))
        # dissolvenza sugli ultimi FADE_SEC: coseno rialzato, come le
        # altre dissolvenze del motore — una curva sola in tutta Aurya
        nf = FADE_SEC * sr
        base = (frames - nf) * ch
        campioni = struct.unpack_from(f"<{nf * ch}h", dati, base * 2)
        sfumati = []
        for i, v in enumerate(campioni):
            u = (i // ch) / nf
            g = 0.5 * (1 + math.cos(math.pi * u))     # 1 → 0
            sfumati.append(int(v * g))
        struct.pack_into(f"<{nf * ch}h", dati, base * 2, *sfumati)
        with wave.open(str(w_out), "wb") as fout:
            fout.setnchannels(ch); fout.setsampwidth(2); fout.setframerate(sr)
            fout.writeframes(bytes(dati))
        r = subprocess.run(["afconvert", "-f", "m4af", "-d", "aac",
                            "-b", str(BITRATE), str(w_out), str(dst)],
                           capture_output=True)
        if r.returncode != 0:
            print(f"  codifica fallita: {r.stderr.decode()[:150]}")
            return None
        return frames / sr


async def main(esegui: bool):
    from database import db
    uploads = BACKEND / "uploads" / "audio"
    trovate = [a async for a in db.audio_assets.find(
        {"duration_sec": {"$gt": TOLLERANZA_SEC}})]
    if not trovate:
        print("Nessuna base oltre la tolleranza: niente da fare.")
        return
    print(f"{len(trovate)} basi oltre i {TOLLERANZA_SEC // 60} minuti:\n")
    for a in trovate:
        print(f"  «{a['title']}» — {a['duration_sec']/60:.1f} min, "
              f"{a['size_bytes']/1048576:.1f} MB")
        if not esegui:
            continue
        vecchio = uploads / Path(a["stream_url"]).name
        if not vecchio.exists():
            print("    file assente: salto"); continue
        nuovo_nome = f"{uuid.uuid4()}.m4a"
        nuovo = uploads / nuovo_nome
        durata = _sfuma_e_accorcia(vecchio, nuovo)
        if durata is None:
            continue
        await db.audio_assets.update_one(
            {"id": a["id"]},
            {"$set": {"stream_url": f"/uploads/audio/{nuovo_nome}",
                      "mime": "audio/mp4",
                      "duration_sec": round(durata, 1),
                      "size_bytes": nuovo.stat().st_size}})
        vecchio.unlink()
        print(f"    → {durata/60:.1f} min, {nuovo.stat().st_size/1048576:.1f} MB, "
              f"coda sfumata in {FADE_SEC}s")
    if not esegui:
        print("\n(elenco soltanto — rilancia con --esegui)")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--esegui", action="store_true")
    ap.parse_args()
    os.environ.setdefault("JWT_SECRET_KEY", "solo-per-importare-database")
    asyncio.run(main(ap.parse_args().esegui))
