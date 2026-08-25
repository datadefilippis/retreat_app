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

REGISTRO = Path(__file__).resolve().parent.parent / "config" / "rotte.json"

# esempi concreti per i segmenti che senza una parte variabile
# rimandano o non esistono (un /o/ da solo non è un profilo)
CAMPIONI = {
    "o": "o/ilaria", "e": None, "p": None, "ph": None, "dg": None,
    "co": None, "r": None, "s": None, "l": None, "b": None, "d": None,
    "t": None, "u": None, "rsv": None, "frequenze": None,
}

INVENTATE = ["pagina-inventata", "wp-admin", "a/b/c", "xyz123",
             "blog-non-esiste", "admin-login"]

# «pubblica» non vuol dire «sempre in SERP»: in fase rete alcune
# superfici del marketplace sono spente per scelta (RT5) e altre si
# spengono da sole quando sono vuote (anti thin-content). Sono
# comportamenti VOLUTI, non difetti — e vanno dichiarati qui invece
# che scoperti ogni volta.
FASE_NOINDEX = {"ritiri", "destinazioni", "esplora-ritiri", "esperienze"}
# /come-funziona racconta il percorso d'acquisto: in fase rete non
# esiste e risponde 404 apposta (LC2)
FASE_404 = {"come-funziona"}


def apri(base, percorso):
    """Ritorna (stato, html, noindex). Il noindex si cerca in DUE posti:
    il meta nella pagina (rotte servite dal renderer) e l'header
    X-Robots-Tag (rotte dell'app, che il renderer non vede mai — è
    nginx a dichiararlo). Guardare solo l'HTML dava 29 falsi allarmi."""
    req = urllib.request.Request(
        f"{base}/{percorso}",
        headers={"User-Agent": "Mozilla/5.0 (compatible; CollaudoAurya/1.0)"})
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            html = r.read().decode("utf-8", "ignore")
            hdr = r.headers.get("X-Robots-Tag", "")
            return r.status, html, ("noindex" in hdr
                                    or 'content="noindex"' in html)
    except urllib.error.HTTPError as e:
        html = e.read().decode("utf-8", "ignore")
        return e.code, html, ("noindex" in (e.headers.get("X-Robots-Tag") or "")
                              or 'content="noindex"' in html)
    except Exception as e:                      # noqa: BLE001
        return 0, str(e), False


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
            code, html, noindex = apri(base, percorso)
            provate += 1
            male = None
            if code != 200 and not (tipo == "pubblica" and seg in FASE_404):
                male = f"risponde {code}, atteso 200"
            elif tipo == "pubblica" and noindex and seg not in FASE_NOINDEX:
                male = "è contenuto ma dichiara noindex"
            elif tipo in ("servizio", "app") and not noindex:
                male = "non dichiara noindex"
            if male:
                problemi.append(f"  /{percorso:<28} [{tipo}] {male}")
            elif args.verboso:
                print(f"  ok  /{percorso:<28} [{tipo}] {code}")

    for p in INVENTATE:
        code, _, _ = apri(base, p)
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
