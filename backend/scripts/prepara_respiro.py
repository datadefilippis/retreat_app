#!/usr/bin/env python3
"""CI-F1 (22/9/2026) — prepara le REGISTRAZIONI DEL RESPIRO del founder.

I memo del telefono (AAC stereo, livelli diversi: le parole a -15/-22
dBFS, i soffi a -35) diventano clip mono normalizzati, pronti per la
libreria. Solo sul Mac (afconvert), come prepara_tappeti.py.

Per ogni riga del CSV (docs/sound/respiro_founder_*.csv):
  1. m4a → WAV mono 44100 (afconvert)
  2. normalizzazione del PICCO a `picco_dbfs` (le parole a -3, i soffi
     a -6: un soffio portato a -3 alza troppo il fruscio)
  3. WAV → m4a AAC 96 kbps mono (afconvert), nome = il file d'origine
     senza spazi

Scrive nella cartella d'uscita anche `respiro.csv`, che
scripts/importa_respiro.py legge per creare i documenti.

Uso:
  python3 scripts/prepara_respiro.py ~/Desktop/memo \\
      docs/sound/respiro_founder_2026-09-22.csv ~/Desktop/memo_pronti
"""
import array
import csv
import math
import os
import shutil
import subprocess
import sys
import tempfile
import wave


def afconvert(*args):
    subprocess.run(["afconvert", *args], check=True,
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def normalizza(wav_in, wav_out, picco_dbfs):
    w = wave.open(wav_in)
    sr, n = w.getframerate(), w.getnframes()
    a = array.array("h", w.readframes(n))
    w.close()
    picco = max(abs(x) for x in a) or 1
    target = 32767 * (10 ** (picco_dbfs / 20))
    g = target / picco
    out = array.array("h", (max(-32768, min(32767, int(round(x * g)))) for x in a))
    w2 = wave.open(wav_out, "wb")
    w2.setnchannels(1); w2.setsampwidth(2); w2.setframerate(sr)
    w2.writeframes(out.tobytes())
    w2.close()
    return n / sr, 20 * math.log10(picco / 32768), g


def main():
    if len(sys.argv) != 4:
        sys.exit(__doc__)
    memo, csv_in, uscita = (os.path.expanduser(p) for p in sys.argv[1:4])
    os.makedirs(uscita, exist_ok=True)
    righe = list(csv.DictReader(open(csv_in, encoding="utf-8")))
    pronte = []
    with tempfile.TemporaryDirectory() as tmp:
        for r in righe:
            origine = os.path.join(memo, r["file"])
            if not os.path.exists(origine):
                print(f"  MANCA  {r['file']}")
                continue
            base = r["file"].rsplit(".", 1)[0].replace(" ", "_").replace("-_", "-")
            w1 = os.path.join(tmp, base + ".raw.wav")
            w2 = os.path.join(tmp, base + ".wav")
            afconvert("-f", "WAVE", "-d", "LEI16@44100", "-c", "1", origine, w1)
            dur, picco, g = normalizza(w1, w2, float(r["picco_dbfs"] or -3))
            nome = base + ".m4a"
            afconvert("-f", "m4af", "-d", "aac", "-b", "96000", w2, os.path.join(uscita, nome))
            pronte.append({**r, "file": nome, "durata_sec": f"{dur:.2f}"})
            print(f"  {nome:40} {dur:5.2f}s  picco {picco:6.1f} dBFS  x{g:5.1f}  → {r['guida']}"
                  f"{' ciclo ' + r['ciclo_sec'] + ' s' if r.get('ciclo_sec') else ''}")
    with open(os.path.join(uscita, "respiro.csv"), "w", encoding="utf-8", newline="") as fh:
        wr = csv.DictWriter(fh, fieldnames=["file", "titolo", "guida", "ciclo_sec",
                                            "picco_dbfs", "durata_sec", "note"])
        wr.writeheader()
        for p in pronte:
            wr.writerow({k: p.get(k, "") for k in wr.fieldnames})
    print(f"\nPRONTE: {len(pronte)} in {uscita}\nORA: scripts/importa_respiro.py {uscita} [--prova]")


if __name__ == "__main__":
    main()
