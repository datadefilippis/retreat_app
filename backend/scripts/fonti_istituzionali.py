#!/usr/bin/env python3
"""Fonti istituzionali negli articoli (26/8/2026) — il pass chirurgico.

MISURA che ha ridimensionato la diagnosi: «zero link esterni in 47
articoli» era un'estrapolazione da UN articolo. La verità: la
redazione già linka dove conta (normattiva ×4, JAMA, Nature, MBSR ×3).
Restavano NUDE solo alcune menzioni istituzionali.

LA REGOLA: si automatizza solo l'INEQUIVOCABILE — leggi e istituzioni,
il cui link ufficiale è uno e uno solo. Le menzioni di *studi*
(Britton, «uno studio su JAMA», Stanford, Kabat-Zinn) NON si toccano:
linkare lo studio sbagliato è peggio che non linkare, e serve chi sa
quale studio era. Per quelle c'è il rapporto in fondo, da girare alla
redazione.

Ogni sostituzione è ancorata alla FRASE ESATTA letta in produzione:
se il testo è cambiato nel frattempo, si salta e si dice. Solo la
PRIMA occorrenza per articolo — un articolo pieno di link ripetuti è
rumore, non autorevolezza.

Uso:
  python3 scripts/fonti_istituzionali.py --prova
  python3 scripts/fonti_istituzionali.py --esegui
"""
import argparse
import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

NORMATTIVA = ("https://www.normattiva.it/uri-res/N2Ls?urn:nir:stato:"
              "legge:2013-01-14;4")

# slug → lista di (testo esatto atteso, testo con link)
RITOCCHI = {
    "bio-professionale-operatore-olistico": [(
        "**Devo mettere la dicitura della legge 4/2013?**",
        f"**Devo mettere la dicitura della [legge 4/2013]({NORMATTIVA})?**",
    )],
    "discipline-olistiche-la-mappa": [(
        "regolate dalla legge 4/2013:",
        f"regolate dalla [legge 4/2013]({NORMATTIVA}):",
    )],
    "assicurazione-rc-operatore-olistico": [(
        "Molte associazioni professionali della legge 4/2013",
        f"Molte associazioni professionali della [legge 4/2013]({NORMATTIVA})",
    )],
    "shiatsu-cose-come-funziona-una-seduta": [(
        "fra le professioni non organizzate della legge 4/2013.",
        f"fra le professioni non organizzate della [legge 4/2013]({NORMATTIVA}).",
    )],
    "massaggio-olistico-tipi-cosa-aspettarsi": [(
        "associazione professionale della legge 4/2013.",
        f"associazione professionale della [legge 4/2013]({NORMATTIVA}).",
    )],
    "codice-ateco-operatore-olistico": [(
        "usata da Agenzia delle Entrate, INPS e Camere di commercio.",
        "usata da [Agenzia delle Entrate](https://www.agenziaentrate.gov.it), "
        "[INPS](https://www.inps.it) e Camere di commercio.",
    )],
    "partita-iva-operatore-olistico-fiscalita-guida": [(
        "oltre la quale scattano i contributi INPS.",
        "oltre la quale scattano i contributi "
        "[INPS](https://www.inps.it).",
    )],
}

# Le menzioni di STUDI che restano alla redazione: qui solo il
# rapporto, mai l'automatismo.
DA_REDAZIONE = [
    ("meditazione-per-chi-inizia-guida-semplice / pratiche intensive",
     "menzione degli studi di Britton sugli effetti avversi"),
    ("un articolo cita «uno studio su JAMA» senza estremi",
     "identificare lo studio esatto prima di linkare"),
    ("mindfulness: le menzioni di Kabat-Zinn e MBSR non linkate",
     "valutare il link alla pagina ufficiale del Center for Mindfulness"),
    ("una menzione di Stanford", "identificare il lavoro citato"),
]


async def main():
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--prova", action="store_true")
    g.add_argument("--esegui", action="store_true")
    args = ap.parse_args()

    from database import db
    from models.common import utc_now

    fatti = saltati = 0
    for slug, coppie in sorted(RITOCCHI.items()):
        doc = await db.articles.find_one({"slug": slug},
                                         {"_id": 0, "content": 1})
        if not doc:
            print(f"  !  {slug}: non trovato")
            continue
        c = doc["content"]
        nuovo = c
        applicati = []
        for atteso, con_link in coppie:
            if con_link in nuovo:
                print(f"  =  {slug}: già linkato")
                continue
            if atteso not in nuovo:
                print(f"  ?  {slug}: la frase attesa non c'è più — SALTO")
                saltati += 1
                continue
            nuovo = nuovo.replace(atteso, con_link, 1)
            applicati.append(atteso[:56])
        if nuovo != c:
            if args.esegui:
                await db.articles.update_one(
                    {"slug": slug},
                    {"$set": {"content": nuovo, "updated_at": utc_now()}})
            for a in applicati:
                print(f"  +  {slug}: {a}…")
            fatti += 1

    print(f"\n{'PROVA' if args.prova else 'FATTI'}: {fatti} articoli · saltati: {saltati}")
    print("\nPER LA REDAZIONE (gli studi non si linkano alla cieca):")
    for dove, cosa in DA_REDAZIONE:
        print(f"  · {dove}\n    → {cosa}")


if __name__ == "__main__":
    asyncio.run(main())
