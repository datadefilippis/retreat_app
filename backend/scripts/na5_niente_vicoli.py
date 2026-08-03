"""NA5 — i due articoli che nessuno linkava.

L'AUDIT dopo l'ondata sui nuovi argomenti ha trovato due pezzi senza
un solo link in entrata: i tarocchi evolutivi e la guida fiscale.
Un articolo che nessuno linka e' un vicolo: ci si arriva solo dalla
ricerca, e chi ci arriva non ha dove andare dopo. Vale doppio in un
Magazine che deve invogliare a girare.

DA DOVE LI AGGANCIO, e non a caso.

I tarocchi dalla lettura del tema natale, perche' sono le due pratiche
che le persone confondono di piu': entrambe leggono un simbolo per
parlare del presente, e la differenza sta in cosa si guarda.

La guida fiscale dal calcolo del prezzo, dove il discorso arriva da
solo: chi ha appena letto che il proprio lavoro va contato come costo
si sta gia' chiedendo come lo fattura.

    venv/bin/python scripts/na5_niente_vicoli.py [--dry-run]
"""
import asyncio
import os
import re
import sys

TAROCCHI = "/blog/tarocchi-oracoli-strumento-evolutivo"
IVA = "/blog/partita-iva-operatore-olistico-fiscalita-guida"

CAMBI = [
    ("lettura-tema-natale-cosa-aspettarsi",
     "## Domande frequenti",
     f"Una pratica che viene confusa con questa piu' spesso di ogni altra "
     f"e' la [lettura dei tarocchi]({TAROCCHI}): entrambe leggono un "
     f"simbolo per parlare del presente, e la differenza sta in cosa si "
     f"guarda — un cielo fermo alla nascita da una parte, una carta "
     f"estratta adesso dall'altra.\n\n## Domande frequenti"),

    ("prezzo-giusto-ritiro-come-calcolarlo",
     "## Domande frequenti",
     f"Un ultimo passaggio che il prezzo tira dentro da solo: come si "
     f"fattura tutto questo. Ne abbiamo scritto nella [guida a partita IVA "
     f"e fiscalita' per operatori olistici]({IVA}).\n\n"
     f"## Domande frequenti"),
]


async def main(dry_run: bool) -> None:
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from database import db

    for slug, vecchio, nuovo in CAMBI:
        d = await db.articles.find_one({"slug": slug}, {"_id": 0, "content": 1})
        if not d:
            print(f"  ASSENTE {slug}")
        elif nuovo.split("\n\n")[0] in d["content"]:
            print(f"  gia' presente in {slug[:44]}")
        elif vecchio in d["content"]:
            if not dry_run:
                await db.articles.update_one({"slug": slug}, {"$set": {
                    "content": d["content"].replace(vecchio, nuovo, 1)}})
            print(f"  aggancio aggiunto a {slug[:44]}")
        else:
            print(f"  NON TROVATO in {slug[:44]}")

    arts = [a async for a in db.articles.find({}, {"_id": 0, "slug": 1,
                                                   "content": 1})]
    slugs = {a["slug"] for a in arts}
    rotti = [(a["slug"], l) for a in arts
             for l in re.findall(r"\]\(/blog/([a-z0-9-]+)\)", a["content"])
             if l not in slugs]
    orfani = [a["slug"] for a in arts
              if not any(f"/blog/{a['slug']})" in b["content"]
                         for b in arts if b["slug"] != a["slug"])]
    print(f"\nlink rotti: {rotti or 'nessuno'}")
    print(f"senza link in entrata: {orfani or 'nessuno'}")
    if dry_run:
        print("\n--dry-run: nessuna scrittura")


if __name__ == "__main__":
    asyncio.run(main("--dry-run" in sys.argv))
