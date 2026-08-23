#!/usr/bin/env python3
"""C1 (23/8/2026) — la fabbrica dei TAPPETI.

Per ogni base audio piu' lunga di SOGLIA_SEC produce un
`{nome}.tappeto.m4a`: i primi TAPPETO_SEC secondi, confezionati come
file COMPLETO e valido. Perche' esiste: il player chiede alle basi in
loop solo uno spezzone via Range HTTP, ma un m4a monco e' un file
incompleto e il decoder di iOS lo RIFIUTA — anche col moov in testa
(verificato con afinfo il 23/8: il moov dichiara campioni che nel
moncone non ci sono). Il fallback allora scaricava il file INTERO e
lo teneva tutto in RAM: la «Meditazione rinascita» del founder
costava ~114 MB di rete e ~2 GB di PCM decodificato su iPhone.

Un file pre-prodotto non ha niente da farsi perdonare: e' un m4a
normale, lo decodifica chiunque. Gira SUL MAC (afconvert e' di
serie, in prod non c'e' ffmpeg): si genera in locale e si carica.

Uso:
  python3 scripts/prepara_tappeti.py <dir_basi> [dir_uscita]

Scrive i .tappeto.m4a accanto alle basi (o in dir_uscita) e stampa
una riga per file: nome, durata sorgente, esito. Idempotente: salta
i tappeti gia' esistenti e aggiornati.
"""
import os
import struct
import subprocess
import sys
import tempfile

TAPPETO_SEC = 190          # SPEZZONE_SEC (180) + margine per la cucitura
SOGLIA_SEC = 240           # sotto: il file e' gia' piccolo, non serve
BITRATE = "160000"         # AAC ~160 kbps: la qualita' di un tappeto in loop
AUDIO_EXT = {".m4a", ".mp3", ".ogg", ".wav", ".aac", ".flac"}


def durata(path):
    """Secondi dalla riga `estimated duration` di afinfo (0 se illeggibile)."""
    try:
        out = subprocess.run(["afinfo", path], capture_output=True,
                             text=True, timeout=60).stdout
        for riga in out.splitlines():
            if "estimated duration" in riga:
                return float(riga.split(":")[1].strip().split()[0])
    except Exception:
        pass
    return 0.0


def taglia_wav(src, dst, sec):
    """Copia i primi `sec` secondi di un WAV: header intatto, chunk
    `data` accorciato, dimensioni riscritte. Niente ricodifica."""
    with open(src, "rb") as f:
        blob = f.read()
    assert blob[:4] == b"RIFF" and blob[8:12] == b"WAVE", "non e' un WAV"
    # fmt: canali, sample rate, block align
    i = blob.find(b"fmt ")
    canali = struct.unpack_from("<H", blob, i + 10)[0]
    sr = struct.unpack_from("<I", blob, i + 12)[0]
    block = struct.unpack_from("<H", blob, i + 20)[0]
    j = blob.find(b"data")
    dati_off = j + 8
    dati_len = struct.unpack_from("<I", blob, j + 4)[0]
    voluti = min(dati_len, int(sec * sr) * block)
    corpo = blob[dati_off:dati_off + voluti]
    testa = bytearray(blob[:dati_off])
    struct.pack_into("<I", testa, 4, len(testa) - 8 + len(corpo))
    struct.pack_into("<I", testa, j + 4, len(corpo))
    with open(dst, "wb") as f:
        f.write(testa)
        f.write(corpo)
    return canali, sr


def produci(base, uscita):
    with tempfile.TemporaryDirectory() as tmp:
        wav = os.path.join(tmp, "pieno.wav")
        wav190 = os.path.join(tmp, "tappeto.wav")
        subprocess.run(["afconvert", base, wav, "-f", "WAVE", "-d", "LEI16"],
                       check=True, capture_output=True, timeout=600)
        taglia_wav(wav, wav190, TAPPETO_SEC)
        subprocess.run(["afconvert", wav190, uscita, "-f", "m4af",
                        "-d", "aac", "-b", BITRATE, "-q", "127"],
                       check=True, capture_output=True, timeout=600)
    d = durata(uscita)
    assert TAPPETO_SEC - 3 <= d <= TAPPETO_SEC + 3, f"durata sospetta: {d}"
    return d


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    dentro = sys.argv[1]
    fuori = sys.argv[2] if len(sys.argv) > 2 else dentro
    os.makedirs(fuori, exist_ok=True)
    fatti = saltati = errori = 0
    for nome in sorted(os.listdir(dentro)):
        radice, ext = os.path.splitext(nome)
        if ext.lower() not in AUDIO_EXT or nome.endswith(".tappeto.m4a"):
            continue
        src = os.path.join(dentro, nome)
        dst = os.path.join(fuori, radice + ".tappeto.m4a")
        d = durata(src)
        if d < SOGLIA_SEC:
            saltati += 1
            continue
        if os.path.exists(dst) and os.path.getmtime(dst) >= os.path.getmtime(src):
            saltati += 1
            continue
        try:
            dt = produci(src, dst)
            mb = os.path.getsize(dst) / 1048576
            print(f"  OK  {nome}  {d:.0f}s -> tappeto {dt:.0f}s {mb:.1f} MB")
            fatti += 1
        except Exception as exc:  # noqa: BLE001 — una base rotta non ferma le altre
            print(f"  ERR {nome}: {exc}")
            errori += 1
    print(f"\nfatti {fatti}, saltati {saltati} (corti o gia' pronti), errori {errori}")
    sys.exit(1 if errori else 0)


if __name__ == "__main__":
    main()
