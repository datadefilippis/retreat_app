#!/usr/bin/env python3
"""LX3 (5/9/2026) — la copia italiana delle pagine, per il renderer.

Il renderer (routers/seo_shell.py) deve dare ai crawler lo STESSO testo
che vede la persona: Chi siamo, Manifesto, Per i professionisti, il
Cerchio. Quel testo vive nei file di traduzione del frontend
(frontend/src/locales/it/*.json), e in produzione il container del
backend non vede il frontend. Questo script copia i due file in
backend/assets/copia_it/ (che entra nell'immagine con `COPY . .`); la
guardia della suite pretende che copia e originale combacino, cosi' un
cambio di copy nel frontend che non viene ricopiato fa la suite rossa
prima del deploy.

Uso:
  python3 scripts/copia_locales.py --scrivi      # aggiorna le copie
  python3 scripts/copia_locales.py --controlla   # esce 1 se divergono
"""
import argparse
import sys
from pathlib import Path

RADICE = Path(__file__).resolve().parent.parent.parent
SORGENTE = RADICE / "frontend" / "src" / "locales" / "it"
DESTINAZIONE = RADICE / "backend" / "assets" / "copia_it"
FILE = ("landings.json", "prelaunch.json")


def main():
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--controlla", action="store_true")
    g.add_argument("--scrivi", action="store_true")
    args = ap.parse_args()
    DESTINAZIONE.mkdir(parents=True, exist_ok=True)
    diversi = []
    for nome in FILE:
        src = (SORGENTE / nome).read_text(encoding="utf-8")
        dst = DESTINAZIONE / nome
        if args.scrivi:
            dst.write_text(src, encoding="utf-8")
        elif not dst.exists() or dst.read_text(encoding="utf-8") != src:
            diversi.append(nome)
    if args.controlla:
        if diversi:
            print("copia_it NON combacia col frontend:", ", ".join(diversi),
                  "\nRigenera con: python3 scripts/copia_locales.py --scrivi")
            sys.exit(1)
        print("OK — copia_it allineata:", ", ".join(FILE))
    else:
        print("copia_it aggiornata:", ", ".join(FILE))


if __name__ == "__main__":
    main()
