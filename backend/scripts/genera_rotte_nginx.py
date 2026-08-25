#!/usr/bin/env python3
"""Genera i blocchi di rotte per nginx dal registro (26/8/2026).

Il registro `config/rotte.json` è la fonte; questo script ne deriva le
due espressioni che nginx usa per decidere dove mandare una richiesta.
Il risultato si SCRIVE nel file di nginx fra due marcatori, e una
guardia della suite verifica che i due combacino: se qualcuno modifica
nginx a mano, o aggiunge una rotta al registro senza rigenerare, la
suite diventa rossa prima del deploy.

Perché generare invece di scrivere a mano: il sito ha 79 segmenti di
primo livello. Scriverli a mano una volta è fattibile; tenerli allineati
per un anno mentre il prodotto cresce, no — ed è esattamente il modo in
cui /meditazioni e /costi sono rimaste mute per settimane.

Uso:
  python3 scripts/genera_rotte_nginx.py --controlla   # esce 1 se diverge
  python3 scripts/genera_rotte_nginx.py --scrivi      # aggiorna nginx.conf
"""
import argparse
import json
import re
import sys
from pathlib import Path

RADICE = Path(__file__).resolve().parent.parent.parent
REGISTRO = RADICE / "config" / "rotte.json"
NGINX = RADICE / "deploy" / "nginx" / "nginx.conf"

INIZIO_SHELL = "    # <<< ROTTE-RENDERER (generato: scripts/genera_rotte_nginx.py) >>>"
FINE_SHELL = "    # <<< FINE ROTTE-RENDERER >>>"
INIZIO_APP = "    # <<< ROTTE-APP (generato: scripts/genera_rotte_nginx.py) >>>"
FINE_APP = "    # <<< FINE ROTTE-APP >>>"


def carica():
    dati = json.loads(REGISTRO.read_text(encoding="utf-8"))
    # il renderer serve pubbliche E servizio: le prime per le meta vere,
    # le seconde per dichiarare noindex dal server (un crawler che non
    # può leggere la pagina non ne vedrebbe mai il noindex)
    renderer = sorted(set(dati["pubblica"]) | set(dati["servizio"]))
    app = sorted(set(dati["app"]))
    doppi = set(renderer) & set(app)
    if doppi:
        sys.exit(f"REGISTRO INCOERENTE: {sorted(doppi)} in due categorie")
    return renderer, app


def blocchi():
    renderer, app = carica()
    b1 = f"""{INIZIO_SHELL}
    # Le pagine che hanno (o devono avere) meta server-side.
    location ~ ^/({'|'.join(renderer)})(/|$) {{
        proxy_pass http://backend:8000/__seo$request_uri;
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-Proto $scheme;
    }}
{FINE_SHELL}"""
    b2 = f"""{INIZIO_APP}
    # Il gestionale: servito dal frontend, mai indicizzato. Il noindex
    # sta QUI e non nella pagina perche' queste rotte non passano dal
    # renderer: e' l'unico punto in cui possiamo dirlo.
    location ~ ^/({'|'.join(app)})(/|$) {{
        add_header X-Robots-Tag "noindex, nofollow" always;
        proxy_pass http://frontend:80;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }}
{FINE_APP}"""
    return b1, b2


def sostituisci(testo, inizio, fine, nuovo):
    pat = re.compile(re.escape(inizio) + r".*?" + re.escape(fine), re.S)
    if not pat.search(testo):
        sys.exit(f"marcatori non trovati in nginx.conf: {inizio}")
    return pat.sub(nuovo, testo)


def main():
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--controlla", action="store_true")
    g.add_argument("--scrivi", action="store_true")
    args = ap.parse_args()

    b1, b2 = blocchi()
    attuale = NGINX.read_text(encoding="utf-8")
    atteso = sostituisci(sostituisci(attuale, INIZIO_SHELL, FINE_SHELL, b1),
                         INIZIO_APP, FINE_APP, b2)

    if args.controlla:
        if attuale != atteso:
            print("nginx.conf NON combacia col registro.\n"
                  "Rigenera con: python3 scripts/genera_rotte_nginx.py --scrivi")
            sys.exit(1)
        renderer, app = carica()
        print(f"OK — nginx allineato: {len(renderer)} rotte al renderer, "
              f"{len(app)} all'app.")
        return

    NGINX.write_text(atteso, encoding="utf-8")
    renderer, app = carica()
    print(f"nginx.conf aggiornato: {len(renderer)} al renderer, {len(app)} all'app.")


if __name__ == "__main__":
    main()
