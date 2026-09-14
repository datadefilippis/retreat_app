#!/usr/bin/env python3
"""SEO-G (14/9/2026 sera) — il crawl dell'analisi SEO, ripetibile.

Legge le rotte come Googlebot (stessa shell che vedono le persone) e
misura cio' che conta: codice, title e description (lunghezza),
canonical, robots, tipi JSON-LD, H1, link interni, parole. Segnala i
fuori misura e i contraddittori; esce con 1 se qualcosa non va, cosi'
puo' girare a mano dopo un deploy o in un cron.

Uso:
  python scripts/seo_crawl.py                      # rotte cardine su aurya.life
  python scripts/seo_crawl.py --base http://localhost:8000 --shell   # locale via /__seo/
  python scripts/seo_crawl.py /o/ilaria /operatori/yoga               # rotte a scelta
  python scripts/seo_crawl.py --json > crawl.json

Soglie: title 15..70 caratteri, description 70..165, H1 esattamente
uno sulle pagine indicizzabili, canonical presente sulle 200 indicizzabili.
"""
import argparse
import json
import re
import subprocess
import sys

UA = "Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)"
ROTTE_CARDINE = ["/", "/cerca-ritiro", "/entra-nella-rete", "/operatori", "/operatori/yoga",
                 "/esperienze", "/blog", "/costi", "/chi-siamo", "/manifesto", "/sound",
                 "/meditazioni", "/newsletter", "/aziende", "/magazine", "/operatori/",
                 "/pagina-che-non-esiste"]
TITLE = (15, 70)
DESC = (70, 165)


def fetch(base: str, path: str, shell: bool):
    url = base.rstrip("/") + ("/__seo" if shell else "") + path
    def _curl():
        return subprocess.run(["curl", "-s", "--max-time", "40", "-A", UA, "-D", "-",
                               "-w", "\n@@%{http_code}@@", url], capture_output=True, text=True)
    r = _curl()
    m = re.search(r"@@(\d+)@@\s*$", r.stdout)
    if not m or m.group(1) == "000":
        r = _curl()                          # un secondo tentativo: la rete non e' un giudizio
        m = re.search(r"@@(\d+)@@\s*$", r.stdout)
    code = m.group(1) if m else "000"
    raw = r.stdout[:m.start()] if m else r.stdout
    pezzi = raw.split("\r\n\r\n")
    hdr, body = (pezzi[0], pezzi[-1]) if len(pezzi) > 1 else ("", raw)
    return code, hdr, body


def tag(body, pat):
    m = re.search(pat, body, re.S | re.I)
    return m.group(1).strip() if m else None


def analizza(base, path, shell):
    code, hdr, body = fetch(base, path, shell)
    ld = []
    for s in re.findall(r'<script type="application/ld\+json">(.*?)</script>', body, re.S):
        try:
            j = json.loads(s)
            ld.append(j.get("@type") if isinstance(j, dict) else "list")
        except Exception:
            ld.append("BROKEN")
    r = {
        "path": path, "code": code,
        "location": tag(hdr, r"location: (\S+)"),
        "title": tag(body, r"<title>(.*?)</title>") or "",
        "description": tag(body, r'<meta name="description" content="(.*?)"') or "",
        "canonical": tag(body, r'<link rel="canonical" href="(.*?)"'),
        "robots": tag(body, r'<meta name="robots" content="(.*?)"'),
        "h1": [re.sub(r"<[^>]+>", "", h).strip() for h in re.findall(r"<h1[^>]*>(.*?)</h1>", body, re.S | re.I)],
        "jsonld": ld,
        "link_interni": len(re.findall(r'<a [^>]*href="/', body)),
        "parole": len(re.sub(r"<[^>]+>", " ", body).split()),
    }
    r["problemi"] = problemi(r)
    return r


def problemi(r):
    p = []
    if r["code"] in ("301", "302"):
        return p                       # un rimando e' una risposta giusta
    if r["code"] == "404":
        if r["robots"] != "noindex":
            p.append("404 senza noindex")
        return p
    if r["code"] != "200":
        return [f"codice {r['code']}"]
    indicizzabile = r["robots"] != "noindex"
    t, d = len(r["title"]), len(r["description"])
    if not (TITLE[0] <= t <= TITLE[1]):
        p.append(f"title {t} caratteri")
    if indicizzabile and not (DESC[0] <= d <= DESC[1]):
        p.append(f"description {d} caratteri")
    if indicizzabile and not r["canonical"]:
        p.append("canonical mancante")
    if indicizzabile and len(r["h1"]) != 1:
        p.append(f"{len(r['h1'])} h1")
    if "BROKEN" in r["jsonld"]:
        p.append("JSON-LD non valido")
    if indicizzabile and r["parole"] < 120:
        p.append(f"solo {r['parole']} parole")
    return p


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("rotte", nargs="*")
    ap.add_argument("--base", default="https://aurya.life")
    ap.add_argument("--shell", action="store_true", help="in locale: passa da /__seo/")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()
    rotte = a.rotte or ROTTE_CARDINE
    esito = [analizza(a.base, p, a.shell) for p in rotte]
    if a.json:
        print(json.dumps(esito, ensure_ascii=False, indent=1))
    else:
        for r in esito:
            stato = "OK " if not r["problemi"] else "!! "
            extra = f" → {r['location']}" if r["location"] else ""
            print(f"{stato}{r['path']:28} {r['code']}{extra}  t={len(r['title']):2} d={len(r['description']):3} "
                  f"robots={r['robots'] or '-':7} ld={','.join(x or '?' for x in r['jsonld']) or '-'}"
                  + (f"  ← {'; '.join(r['problemi'])}" if r["problemi"] else ""))
    rotti = [r for r in esito if r["problemi"]]
    print(f"\n{len(esito)} rotte, {len(rotti)} con problemi", file=sys.stderr)
    sys.exit(1 if rotti else 0)


if __name__ == "__main__":
    main()
