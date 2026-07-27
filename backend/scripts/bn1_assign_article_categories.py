"""BN1 — assegna la categoria ai 10 articoli orfani (per slug).

Idempotente: aggiorna solo se la categoria e' diversa. Da eseguire in
locale per la verifica e in prod al deploy di BN1 (docker compose exec
backend python scripts/bn1_assign_article_categories.py).

Mappa decisa in docs/BLOG_NEWSLETTER_STRATEGIA_2026-07.md:
- energia: pratiche energetiche/divinatorie (reiki, tarocchi, tema
  natale, costellazioni)
- ritiri: il mondo ritiri trasversale (scegliere, prepararsi)
- operatori: il cluster B2B (converte alla rete, non alla newsletter)
- meditazione: la rassegna anti-stress (il suo cuore e' MBSR)
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

CATEGORY_BY_SLUG = {
    "reiki-cose-come-funziona-una-sessione": "energia",
    "tarocchi-oracoli-strumento-evolutivo": "energia",
    "lettura-tema-natale-cosa-aspettarsi": "energia",
    "costellazioni-familiari-cosa-sono-come-funzionano": "energia",
    "pratiche-olistiche-contro-stress-cosa-funziona": "meditazione",
    "ritiri-olistici-in-italia-come-scegliere": "ritiri",
    "cosa-portare-a-un-ritiro-lista-completa": "ritiri",
    "prezzo-giusto-ritiro-come-calcolarlo": "operatori",
    "partita-iva-operatore-olistico-fiscalita-guida": "operatori",
    "come-promuovere-un-ritiro-e-riempire-i-posti": "operatori",
}


async def main() -> None:
    from database import db
    from models.article import ARTICLE_CATEGORIES
    from models.common import utc_now

    unknown = set(CATEGORY_BY_SLUG.values()) - set(ARTICLE_CATEGORIES)
    assert not unknown, f"categorie sconosciute: {unknown}"

    changed = 0
    for slug, cat in CATEGORY_BY_SLUG.items():
        doc = await db.articles.find_one({"slug": slug}, {"_id": 0, "category": 1})
        if doc is None:
            print(f"  SKIP (assente): {slug}")
            continue
        if doc.get("category") == cat:
            print(f"  ok (gia' {cat}): {slug}")
            continue
        await db.articles.update_one(
            {"slug": slug},
            {"$set": {"category": cat, "updated_at": utc_now()}})
        changed += 1
        print(f"  {doc.get('category')} -> {cat}: {slug}")
    print(f"aggiornati: {changed}/{len(CATEGORY_BY_SLUG)}")


if __name__ == "__main__":
    asyncio.run(main())
