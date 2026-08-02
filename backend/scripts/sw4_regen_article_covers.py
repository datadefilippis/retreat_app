"""SW4/SW4b — rigenera le copertine autogenerate del Magazine.

SW4: il generatore (services/article_cover.py) non stampa piu' il
titolo dentro l'immagine, quindi le cover gia' pubblicate vanno
rifatte.

SW4b: e non basta rifarle. Il nome del file era `{slug}.webp`, sempre
lo stesso, e le cover si servono con `cache-control: immutable,
max-age=31536000`: chi aveva gia' visto il blog continuava a vedere la
copertina vecchia, per un anno, e nessuna purge di CDN arriva alla
cache di un browser. Adesso il nome porta l'impronta dell'immagine
(`{slug}-{hash8}.webp`, services/article_cover.store_article_cover):
immagine nuova, URL nuovo, e il campo `featured_image_url` del
documento si aggiorna qui.

REGOLA CHE NON SI TOCCA: si rigenerano SOLO le copertine che abbiamo
generato noi, cioe' quelle che vivono sotto `article-covers/`. Una
foto caricata a mano dall'operatore o dall'admin non si sostituisce
mai, per nessun motivo: e' una scelta editoriale di qualcun altro.

L'endpoint admin (POST /api/admin/articles/{id}/cover) rifa' UNA
cover e sovrascrive anche un'immagine propria, perche' li' e' un
gesto esplicito su un articolo scelto. Questo script e' l'altro caso:
tanti articoli, nessuna scelta caso per caso, quindi il filtro.

IDEMPOTENTE: stesso template, stessi byte, stesso nome. Rilanciarlo
non cambia un URL e non scrive sul documento — cosi' `updated_at`
resta la data in cui e' cambiato qualcosa davvero.

    cd backend && venv/bin/python scripts/sw4_regen_article_covers.py
    cd backend && venv/bin/python scripts/sw4_regen_article_covers.py --dry-run
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


async def main(dry_run: bool = False) -> None:
    from database import db
    from models.article import ARTICLE_CATEGORIES
    from models.common import utc_now
    from services.article_cover import (cover_asset_name,
                                        is_autogen_cover_url,
                                        render_article_cover,
                                        store_article_cover)

    docs = await db.articles.find(
        {}, {"_id": 0, "id": 1, "slug": 1, "category": 1,
             "featured_image_url": 1}).to_list(1000)

    fatte, invariate, saltate, fallite = 0, 0, 0, 0
    for doc in docs:
        url = doc.get("featured_image_url") or ""
        if not is_autogen_cover_url(url):
            saltate += 1
            motivo = "immagine propria" if url else "nessuna cover"
            print(f"  skip ({motivo}): {doc['slug']}")
            continue
        category = doc.get("category")
        label = ARTICLE_CATEGORIES.get(category or "")
        data = await asyncio.to_thread(render_article_cover, None,
                                       category, label)
        if not data:
            fallite += 1
            print(f"  FALLITA (generatore non disponibile): {doc['slug']}")
            continue
        atteso = cover_asset_name(doc["slug"], data)
        if url.endswith(f"/{atteso}"):
            invariate += 1
            print(f"  gia' aggiornata: {atteso}")
            continue
        if dry_run:
            fatte += 1
            print(f"  [dry] {doc['slug']} → {atteso} ({label or 'Aurya'})")
            continue
        nuovo = await asyncio.to_thread(store_article_cover, doc["slug"], data)
        await db.articles.update_one(
            {"id": doc["id"]},
            {"$set": {"featured_image_url": nuovo,
                      "updated_at": utc_now()}})
        fatte += 1
        print(f"  ok ({label or 'Aurya'}, {len(data)} B): {nuovo}")

    print(f"\nrigenerate: {fatte} | gia' a posto: {invariate} | "
          f"non toccate: {saltate} | fallite: {fallite}")


if __name__ == "__main__":
    asyncio.run(main(dry_run="--dry-run" in sys.argv))
