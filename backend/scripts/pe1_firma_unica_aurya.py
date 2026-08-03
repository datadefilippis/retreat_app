"""PE1 — la firma degli articoli e' sempre "Aurya" (founder, 2 ago 2026).

Undici articoli su venti erano firmati "Valentina · Aurya" o "Davide ·
Aurya", nove "Aurya": tre firme diverse sullo stesso Magazine. La
decisione del founder e' che la voce sia sempre collettiva, anche
quando a scrivere e' una persona sola.

E' una scelta di brand, non una svista da correggere: chi legge trova
un interlocutore solo, e la competenza di prima mano continua a
vedersi dove conta davvero, cioe' nelle voci dei professionisti
citati DENTRO gli articoli.

Idempotente: rilanciarlo non cambia nulla. Tocca SOLO author_name,
mai il testo, mai la data, mai lo slug.

    venv/bin/python scripts/pe1_firma_unica_aurya.py [--dry-run]
"""
import asyncio
import os
import sys

FIRMA = "Aurya"


async def main(dry_run: bool) -> None:
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from database import db

    cur = db.articles.find({}, {"_id": 0, "slug": 1, "author_name": 1})
    da_cambiare = []
    async for a in cur:
        if (a.get("author_name") or "") != FIRMA:
            da_cambiare.append((a["slug"], a.get("author_name")))

    if not da_cambiare:
        print(f"tutte le firme sono gia' '{FIRMA}': niente da fare")
        return

    print(f"{len(da_cambiare)} articoli da rifirmare:")
    for slug, vecchia in da_cambiare:
        print(f"  {vecchia or '(vuoto)':>22}  →  {FIRMA}   {slug}")

    if dry_run:
        print("\n--dry-run: nessuna scrittura")
        return

    res = await db.articles.update_many(
        {"author_name": {"$ne": FIRMA}},
        {"$set": {"author_name": FIRMA}},
    )
    print(f"\naggiornati: {res.modified_count}")


if __name__ == "__main__":
    asyncio.run(main("--dry-run" in sys.argv))
