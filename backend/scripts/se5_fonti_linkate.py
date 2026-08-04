"""SE5 — le fonti citate diventano fonti LINKATE.

PERCHE'. Sette articoli citano studi con autore e rivista ("Goyal e
colleghi, JAMA Internal Medicine, 2014") ma nessun articolo del sito
aveva UN link esterno. Il link alla fonte primaria e' il segnale di
competenza piu' economico che esista (E-E-A-T), e per i motori
generativi e' la differenza fra "afferma" e "documenta".

UNA CORREZIONE, trovata verificando le fonti: l'articolo sulla
meditazione attribuiva lo studio di popolazione sugli effetti avversi
a *JAMA Psychiatry* 2022. Lo studio (Goldberg, Lam, Britton, Davidson,
"Prevalence of meditation-related adverse effects in a population-based
sample in the United States") e' uscito su *Psychotherapy Research*
2022;32(3):291-305 — PubMed 34074221. La citazione viene corretta,
non solo linkata.

REGOLE DEI LINK. Solo fonti primarie verificate: doi.org per gli
articoli scientifici (stabile per costruzione), PubMed dove il DOI
contiene parentesi (romperebbero il parser markdown dei due renderer),
Normattiva per la legge 4/2013. MAI link dentro i grassetti: i
renderer (client e shell) non sono ricorsivi e il markdown annidato
uscirebbe crudo.

Idempotente; da rieseguire in produzione al lancio.

    venv/bin/python scripts/se5_fonti_linkate.py [--dry-run]
"""
import asyncio
import os
import sys

NORMATTIVA = ("https://www.normattiva.it/uri-res/N2Ls?"
              "urn:nir:stato:legge:2013-01-14;4")

# (slug, testo esatto da sostituire, sostituto)
CAMBI = [
    # ── la correzione: rivista giusta + link ─────────────────────────
    ("meditazione-per-chi-inizia-guida-semplice",
     "e uno studio pubblicato su *JAMA Psychiatry* nel 2022 su un "
     "campione di popolazione ha trovato",
     "e uno [studio su un campione di popolazione, pubblicato su "
     "*Psychotherapy Research* nel 2022]"
     "(https://pubmed.ncbi.nlm.nih.gov/34074221/), ha trovato"),

    # ── link alle fonti primarie ─────────────────────────────────────
    ("kit-pratiche-quotidiane-15-minuti",
     "(Goyal e colleghi, *JAMA Internal Medicine*, 2014)",
     "([Goyal e colleghi, *JAMA Internal Medicine*, 2014]"
     "(https://doi.org/10.1001/jamainternmed.2013.13018))"),

    ("ayurveda-cose-i-tre-dosha-cosa-aspettarsi",
     "Due indagini pubblicate su *JAMA* da Robert Saper e colleghi, "
     "nel 2004 e nel 2008,",
     "Due indagini pubblicate su *JAMA* da Robert Saper e colleghi, "
     "[nel 2004](https://doi.org/10.1001/jama.292.23.2868) e "
     "[nel 2008](https://doi.org/10.1001/jama.300.8.915),"),

    ("camminare-bagni-di-foresta-cammini",
     "Uno studio pubblicato su *Scientific Reports* nel 2019 da White "
     "e colleghi,",
     "Uno [studio pubblicato su *Scientific Reports* nel 2019]"
     "(https://doi.org/10.1038/s41598-019-44097-3) da White e colleghi,"),

    ("lettura-tema-natale-cosa-aspettarsi",
     "Lo studio più noto è di Shawn Carlson, pubblicato su *Nature* "
     "nel 1985.",
     "Lo studio più noto è di Shawn Carlson, [pubblicato su *Nature* "
     "nel 1985](https://doi.org/10.1038/318419a0)."),

    # il DOI di Kabat-Zinn 1982 contiene parentesi: si usa PubMed
    ("mindfulness-cose-mbsr-come-funziona",
     "ed è nato al centro medico dell'Università del Massachusetts.",
     "ed è nato al centro medico dell'Università del Massachusetts "
     "([il primo studio pubblicato è del 1982]"
     "(https://pubmed.ncbi.nlm.nih.gov/7042457/))."),

    # ── la legge 4/2013, testo ufficiale ─────────────────────────────
    ("come-capire-se-un-operatore-olistico-e-serio",
     "disciplinate dalla **legge 4 del 14 gennaio 2013**.",
     "disciplinate dalla **legge 4 del 14 gennaio 2013** "
     f"([testo della norma]({NORMATTIVA}))."),

    ("partita-iva-operatore-olistico-fiscalita-guida",
     "regolate dalla legge 4 del 2013, e questo",
     f"regolate dalla [legge 4 del 2013]({NORMATTIVA}), e questo"),
]


async def main(dry_run: bool) -> None:
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from database import db

    fatti = gia = persi = 0
    for slug, vecchio, nuovo in CAMBI:
        d = await db.articles.find_one({"slug": slug},
                                       {"_id": 0, "content": 1})
        if not d:
            print(f"  ASSENTE {slug}")
            persi += 1
            continue
        c = d["content"]
        if nuovo in c:
            gia += 1
            continue
        if vecchio not in c:
            print(f"  NON TROVATO in {slug}: {vecchio[:60]!r}")
            persi += 1
            continue
        if not dry_run:
            await db.articles.update_one(
                {"slug": slug},
                {"$set": {"content": c.replace(vecchio, nuovo, 1)}})
        print(f"  ok  {slug}")
        fatti += 1

    print(f"\nfatti: {fatti}, gia': {gia}, persi: {persi}")
    # audit: ogni link esterno inserito e' https e su dominio fidato
    import re
    fidati = ("doi.org", "pubmed.ncbi.nlm.nih.gov", "normattiva.it")
    async for a in db.articles.find({"published": True},
                                    {"_id": 0, "slug": 1, "content": 1}):
        for m in re.finditer(r"\]\((https?://[^)\s]+)\)", a["content"]):
            url = m.group(1)
            assert url.startswith("https://"), f"{a['slug']}: {url}"
            assert any(f in url for f in fidati), \
                f"{a['slug']}: dominio non in whitelist: {url}"
    print("audit link esterni: tutti https su domini fidati")
    if dry_run:
        print("\n--dry-run: nessuna scrittura")


if __name__ == "__main__":
    asyncio.run(main("--dry-run" in sys.argv))
