#!/usr/bin/env python3
"""Censimento di sound_new (24/8/2026) — la tabella prima dell'import.

Il founder ha 128 tracce organizzate per MOMENTO del viaggio (Arrivo,
Attivazione, Ascesa, Catarsi, Rientro): un asse che l'app non ha e che
serve a comporre. L'app le classifica per TIMBRO (ambient, natura,
droni…): un asse diverso, non alternativo.

Questo script non importa nulla: MISURA e PROPONE, perché la revisione
la faccia una persona. Per ogni file: durata reale (afinfo), peso,
momento (la cartella), categoria proposta (dai nomi, con la confidenza
dichiarata) e i duplicati.

Uso:
  python3 scripts/censimento_sound_new.py ~/Desktop/sound_new [uscita.csv]
"""
import csv
import hashlib
import os
import re
import subprocess
import sys
from collections import Counter

# Le parole che tradiscono il timbro. L'ordine conta: la prima che
# combacia vince (le piu' specifiche stanno in alto).
INDIZI = [
    ("campane", ("bowl", "bell", "chime", "gong", "tibetan", "singing-bowl",
                 "handpan", "kalimba", "koshi")),
    ("natura", ("nature", "rain", "ocean", "wave", "forest", "bird", "water",
                "river", "storm", "wind", "fire", "stream", "jungle")),
    ("droni", ("drone", "bordone", "hum", "sustained", "deep-space")),
    ("ritmi", ("drum", "percussion", "tribal", "beat", "rhythm", "shaman",
               "afrobeat", "groove", "taiko")),
    ("voce", ("chant", "chanting", "mantra", "voice", "vocal", "om-",
              "whisper", "throat", "choir")),
    ("corpo", ("heart", "breath", "pulse", "body", "chakra")),
    ("transizioni", ("transition", "riser", "sweep", "impact", "whoosh")),
    ("ambient", ("ambient", "meditation", "calm", "relax", "spa", "zen",
                 "healing", "cinematic", "piano", "acoustic", "guitar",
                 "flute", "atmosphere", "soundscape", "yoga", "sleep")),
]
MOMENTI = ("Arrivo", "Attivazione", "Ascesa", "Catarsi", "Rientro")


def durata(path):
    try:
        out = subprocess.run(["afinfo", path], capture_output=True,
                             text=True, timeout=120).stdout
        for riga in out.splitlines():
            if "estimated duration" in riga:
                return round(float(riga.split(":")[1].strip().split()[0]), 1)
    except Exception:
        pass
    return 0.0


def proponi(nome):
    """(categoria, confidenza, parola che l'ha decisa)."""
    n = nome.lower()
    for cat, parole in INDIZI:
        for p in parole:
            if p in n:
                # «ambient» e' l'ultimo scaffale: utile ma generico
                return cat, ("media" if cat == "ambient" else "alta"), p
    return "ambient", "bassa", "—"


def titolo_umano(nome):
    """Dal nome di banca audio a un titolo leggibile: via autore in
    testa e id numerico in coda, trattini in spazi, iniziali su."""
    base = re.sub(r"\.[a-z0-9]+$", "", nome, flags=re.I)
    base = re.sub(r"[ _-]*\(\d+\)$", "", base)
    base = re.sub(r"-\d{4,}$", "", base)
    pezzi = base.split("-")
    if len(pezzi) > 2 and len(pezzi[0]) <= 16:
        pezzi = pezzi[1:]                     # l'autore in testa se ne va
    testo = " ".join(p for p in pezzi if p and not p.isdigit())
    testo = testo.replace("_", " ").strip()
    return (testo[:1].upper() + testo[1:])[:80] or base[:80]


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    radice = os.path.expanduser(sys.argv[1])
    uscita = sys.argv[2] if len(sys.argv) > 2 else os.path.join(radice, "censimento.csv")

    righe, visti = [], {}
    for momento in MOMENTI:
        cartella = os.path.join(radice, momento)
        if not os.path.isdir(cartella):
            continue
        for nome in sorted(os.listdir(cartella)):
            if not nome.lower().endswith((".mp3", ".m4a", ".wav", ".ogg", ".flac")):
                continue
            path = os.path.join(cartella, nome)
            peso = os.path.getsize(path)
            d = durata(path)
            cat, conf, parola = proponi(nome)
            # il duplicato si dichiara SOLO sull'impronta del file:
            # peso e durata uguali capitano per caso (verificato: 3
            # coppie «sospette» erano brani diversi dello stesso autore)
            with open(path, "rb") as fh:
                impronta = hashlib.md5(fh.read()).hexdigest()
            dup = visti.get(impronta)
            visti.setdefault(impronta, f"{momento}/{nome}")
            righe.append({
                "momento": momento,
                "file": nome,
                "titolo_proposto": titolo_umano(nome),
                "durata_sec": d,
                "durata": f"{int(d // 60)}:{int(d % 60):02d}",
                "MB": round(peso / 1048576, 1),
                "categoria_proposta": cat,
                "confidenza": conf,
                "indizio": parola,
                "tappeto_serve": "si" if d > 240 else "no",
                "duplicato_di": dup or "",
            })

    with open(uscita, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(righe[0].keys()))
        w.writeheader()
        w.writerows(righe)

    print(f"tracce censite: {len(righe)}  →  {uscita}\n")
    for m in MOMENTI:
        gruppo = [r for r in righe if r["momento"] == m]
        if not gruppo:
            continue
        cats = Counter(r["categoria_proposta"] for r in gruppo)
        mb = sum(r["MB"] for r in gruppo)
        print(f"{m:12} {len(gruppo):3} tracce  {mb:6.0f} MB  "
              f"{', '.join(f'{c}×{n}' for c, n in cats.most_common())}")
    print()
    conf = Counter(r["confidenza"] for r in righe)
    print("confidenza della proposta:",
          ", ".join(f"{k} {v}" for k, v in conf.most_common()))
    dupli = [r for r in righe if r["duplicato_di"]]
    print(f"duplicati (stesso file, impronta md5): {len(dupli)}")
    for r in dupli:
        print(f"  · {r['momento']}/{r['file']}  =  {r['duplicato_di']}")
    lunghe = [r for r in righe if r["tappeto_serve"] == "si"]
    print(f"tracce che vorranno un tappeto (>4 min): {len(lunghe)}")
    print(f"peso totale: {sum(r['MB'] for r in righe):.0f} MB")


if __name__ == "__main__":
    main()
