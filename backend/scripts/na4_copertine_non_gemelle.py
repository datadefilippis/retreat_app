"""NA4 — rigenera le copertine con la variazione per articolo.

IL DIFETTO. SW4 aveva reso la cover un sigillo di categoria, e la
conseguenza non voluta era che ogni articolo della stessa categoria
usciva con un file identico al byte. Nel Magazine, dove le copertine
sono grandi per scelta, cinque tessere yoga affiancate e uguali
sembravano un errore di caricamento.

LA CORREZIONE, in services/article_cover.py: colore e segno restano
quelli della categoria — sono il modo in cui si riconosce a colpo
d'occhio dove si sta — mentre luce, rotazione, scala e tono si
derivano dallo slug. Deterministica: lo stesso articolo produce
sempre la stessa copertina.

QUESTO SCRIPT le riscrive tutte. Il nome del file porta l'impronta
del contenuto, quindi cambiando l'immagine cambia l'URL e la cache
`immutable` dei browser non serve piu' la versione vecchia; le
versioni precedenti vengono rimosse da store_article_cover.

    venv/bin/python scripts/na4_copertine_non_gemelle.py [--dry-run]
"""
import asyncio
import hashlib
import os
import sys
from collections import Counter


async def main(dry_run: bool) -> None:
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from database import db
    from models.article import ARTICLE_CATEGORIES
    from services.article_cover import (render_article_cover,
                                        store_article_cover, variation_for)

    arts = [a async for a in db.articles.find(
        {}, {"_id": 0, "slug": 1, "category": 1, "featured_image_url": 1})]
    print(f"{len(arts)} articoli\n")

    impronte = Counter()
    for a in sorted(arts, key=lambda x: (x.get("category") or "", x["slug"])):
        cat = a.get("category")
        dati = render_article_cover(None, cat, ARTICLE_CATEGORIES.get(cat or ""),
                                    a["slug"])
        if not dati:
            print(f"  SALTATO {a['slug']}")
            continue
        impronte[hashlib.sha256(dati).hexdigest()] += 1
        v = variation_for(a["slug"])
        url = a.get("featured_image_url")
        if not dry_run:
            url = store_article_cover(a["slug"], dati)
            await db.articles.update_one({"slug": a["slug"]},
                                         {"$set": {"featured_image_url": url}})
        print(f"  {(cat or '—'):12} rot {v['rotazione']:5.0f}°  "
              f"scala {v['scala']:.2f}  luce {v['luce_x']:.2f}  "
              f"{a['slug'][:40]}")

    gemelle = [n for n in impronte.values() if n > 1]
    print(f"\nimmagini distinte: {len(impronte)} su {sum(impronte.values())}")
    print("copertine gemelle:", sum(gemelle) if gemelle else "nessuna")
    if dry_run:
        print("\n--dry-run: nessuna scrittura")


if __name__ == "__main__":
    asyncio.run(main("--dry-run" in sys.argv))
