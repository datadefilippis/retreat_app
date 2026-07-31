"""SW4 — rigenera le copertine autogenerate del Magazine.

Il generatore (services/article_cover.py) non stampa piu' il titolo
dentro l'immagine: le cover gia' pubblicate vanno rifatte, altrimenti
l'indice mostra il vecchio e il nuovo insieme.

REGOLA CHE NON SI TOCCA: si rigenerano SOLO le copertine che abbiamo
generato noi, cioe' quelle che vivono sotto `article-covers/`. Una
foto caricata a mano dall'operatore o dall'admin non si sostituisce
mai, per nessun motivo: e' una scelta editoriale di qualcun altro.

L'endpoint admin (POST /api/admin/articles/{id}/cover) rifa' UNA
cover e sovrascrive anche un'immagine propria, perche' li' e' un
gesto esplicito su un articolo scelto. Questo script e' l'altro caso:
tanti articoli, nessuna scelta caso per caso, quindi il filtro.

Il nome del file resta {slug}.webp: l'URL non cambia, i link e le
card social gia' in giro continuano a puntare all'immagine giusta.

    cd backend && venv/bin/python scripts/sw4_regen_article_covers.py
    cd backend && venv/bin/python scripts/sw4_regen_article_covers.py --dry-run
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# Il prefisso della cartella in cui salviamo le cover autogenerate
# (services/object_storage.save_public_upload → .../article-covers/x.webp).
AUTOGEN_MARKER = "/article-covers/"


async def main(dry_run: bool = False) -> None:
    from database import db
    from models.article import ARTICLE_CATEGORIES
    from models.common import utc_now
    from services.article_cover import render_article_cover
    from services.object_storage import save_public_upload

    docs = await db.articles.find(
        {}, {"_id": 0, "id": 1, "slug": 1, "category": 1,
             "featured_image_url": 1}).to_list(1000)

    fatte, saltate, fallite = 0, 0, 0
    for doc in docs:
        url = doc.get("featured_image_url") or ""
        if AUTOGEN_MARKER not in url:
            saltate += 1
            motivo = "immagine propria" if url else "nessuna cover"
            print(f"  skip ({motivo}): {doc['slug']}")
            continue
        category = doc.get("category")
        label = ARTICLE_CATEGORIES.get(category or "")
        if dry_run:
            fatte += 1
            print(f"  [dry] {doc['slug']} → {label or 'Aurya'}")
            continue
        data = await asyncio.to_thread(render_article_cover, None,
                                       category, label)
        if not data:
            fallite += 1
            print(f"  FALLITA (generatore non disponibile): {doc['slug']}")
            continue
        nuovo = save_public_upload("article-covers", f"{doc['slug']}.webp",
                                   data, "image/webp")
        await db.articles.update_one(
            {"id": doc["id"]},
            {"$set": {"featured_image_url": nuovo,
                      "updated_at": utc_now()}})
        fatte += 1
        print(f"  ok ({label or 'Aurya'}, {len(data)} B): {doc['slug']}")

    print(f"\nrigenerate: {fatte} | non toccate: {saltate} | fallite: {fallite}")


if __name__ == "__main__":
    asyncio.run(main(dry_run="--dry-run" in sys.argv))
