#!/usr/bin/env python3
"""Collaudo di TUTTE le rotte, una per una (26/8/2026).

Il registro `config/rotte.json` decide chi passa dal renderer, chi va
al frontend e cosa non esiste. È una regola potente, e le regole
potenti vanno provate sul vivo: se una rotta dell'app finisse fra le
sconosciute risponderebbe 404 quando la si apre da un link diretto o
da un refresh — non in navigazione interna, quindi il difetto sarebbe
invisibile a chi sviluppa e visibilissimo a chi lavora.

Questo script apre ogni segmento del registro contro un sito vero e
verifica che si comporti come dichiarato:

  pubblica  → 200, e NON noindex (è contenuto)
  servizio  → 200, con noindex (esiste, non si indicizza)
  app       → 200, con noindex (il gestionale c'è, dietro login)
  inventata → 404 (lo spazio infinito è chiuso)

Uso:
  python3 scripts/collauda_rotte.py https://aurya.life
  python3 scripts/collauda_rotte.py http://localhost:3000 --verboso
"""
import argparse
import json
import sys
import urllib.error
import urllib.request
from pathlib import Path

REGISTRO = Path(__file__).resolve().parent.parent.parent / "config" / "rotte.json"

# esempi concreti per i segmenti che senza una parte variabile
# rimandano o non esistono (un /o/ da solo non è un profilo)
CAMPIONI = {
    "o": "o/ilaria", "e": None, "p": None, "ph": None, "dg": None,
    "co": None, "r": None, "s": None, "l": None, "b": None, "d": None,
    "t": None, "u": None, "rsv": None, "frequenze": None,
}

INVENTATE = ["pagina-inventata", "wp-admin", "a/b/c", "xyz123",
             "blog-non-esiste", "admin-login"]


def apri(base, percorso):
    req = urllib.request.Request(
        f"{base}/{percorso}",
        headers={"User-Agent": "Mozilla/5.0 (compatible; CollaudoAurya/1.0)"})
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            return r.status, r.read().decode("utf-8", "ignore")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "ignore")
    except Exception as e:                      # noqa: BLE001
        return 0, str(e)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("base")
    ap.add_argument("--verboso", action="store_true")
    args = ap.parse_args()
    base = args.base.rstrip("/")

    d = json.loads(REGISTRO.read_text(encoding="utf-8"))
    problemi = []
    provate = 0

    for tipo in ("pubblica", "servizio", "app"):
        for seg in sorted(d[tipo]):
            if seg in CAMPIONI and CAMPIONI[seg] is None:
                continue                        # serve una parte variabile
            percorso = CAMPIONI.get(seg) or seg
            code, html = apri(base, percorso)
            provate += 1
            noindex = 'content="noindex"' in html or "noindex" in html[:2000]
            male = None
            if code != 200:
                male = f"risponde {code}, atteso 200"
            elif tipo == "pubblica" and noindex:
                male = "è contenuto ma dichiara noindex"
            elif tipo in ("servizio", "app") and not noindex:
                male = "non dichiara noindex"
            if male:
                problemi.append(f"  /{percorso:<28} [{tipo}] {male}")
            elif args.verboso:
                print(f"  ok  /{percorso:<28} [{tipo}] {code}")

    for p in INVENTATE:
        code, _ = apri(base, p)
        provate += 1
        if code != 404:
            problemi.append(f"  /{p:<28} [inventata] risponde {code}, atteso 404")
        elif args.verboso:
            print(f"  ok  /{p:<28} [inventata] 404")

    print(f"\nrotte provate: {provate}")
    if problemi:
        print(f"PROBLEMI: {len(problemi)}")
        for p in problemi:
            print(p)
        sys.exit(1)
    print("TUTTE le rotte si comportano come dichiarato nel registro.")


if __name__ == "__main__":
    main()
