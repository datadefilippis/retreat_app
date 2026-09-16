"""NA13 (16/9/2026) — pubblica articoli NUOVI del Magazine da un file JSON
prodotto dal validatore in locale (sistema editoriale:
docs/AURYA_MAGAZINE_SISTEMA_EDITORIALE.md, piano: docs/PIANO_SEO_EDITORIALE_2026-09.md).

Formato del JSON:
  {"articoli": [{"slug", "title", "description", "in_breve", "content",
                 "category", "related_slugs": [...]}],
   "aggiunte": [{"slug", "vecchio", "nuovo"}]}     # rimandi negli articoli esistenti

Un articolo già esistente con lo stesso slug viene aggiornato (title,
description, in_breve, content, category, related_slugs, updated_at) senza
toccare id, copertina, published_at. Le aggiunte sostituiscono «vecchio» con
«nuovo» una sola volta e solo se «vecchio» è ancora nel testo. Copertina
autogenerata se manca. Alla fine: link rotti e articoli orfani.

    python scripts/na13_nuovi_articoli.py --file percorso.json [--dry-run] [--ping]
"""
import asyncio
import json
import os
import re
import sys
import uuid
from datetime import datetime, timezone


async def main(percorso: str, dry_run: bool, ping: bool) -> None:
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from database import db
    dati = json.load(open(percorso, encoding="utf-8"))
    articoli, aggiunte = dati.get("articoli", []), dati.get("aggiunte", [])
    print(f"{len(articoli)} articoli, {len(aggiunte)} aggiunte in {percorso}")
    fatti = []
    for a in articoli:
        faq = len(re.findall(r"^\*\*[^*]+\?\*\*\s*$", a["content"], re.M))
        print(f"  {a['title']}\n    slug: {a['slug']} | categoria: {a['category']} | parole: {len(a['content'].split())}"
              f" | description: {len(a['description'])} car. | FAQ: {faq}")
        assert len(a["description"]) <= 165 and faq >= 4 and len(a["title"]) <= 62, "fuori misura"
        esistente = await db.articles.find_one({"slug": a["slug"]}, {"_id": 0, "id": 1})
        print("    stato:", "aggiornato" if esistente else "nuovo")
        if dry_run:
            continue
        now = datetime.now(timezone.utc)
        campi = {"title": a["title"], "description": a["description"], "in_breve": a["in_breve"],
                 "content": a["content"], "category": a["category"], "author_name": "Aurya",
                 "access": "public", "published": True, "updated_at": now,
                 "related_slugs": a.get("related_slugs", [])}
        if not esistente:
            campi |= {"id": str(uuid.uuid4()), "slug": a["slug"], "created_at": now, "published_at": now, "translations": {}}
        await db.articles.update_one({"slug": a["slug"]}, {"$set": campi}, upsert=True)
        fatti.append(a["slug"])
        doc = await db.articles.find_one({"slug": a["slug"]}, {"_id": 0, "featured_image_url": 1})
        if not doc.get("featured_image_url"):
            from routers.articles import _autogen_cover
            url = await _autogen_cover(a["slug"], a["category"])
            if url:
                await db.articles.update_one({"slug": a["slug"]}, {"$set": {"featured_image_url": url}})
                print(f"    copertina: {url}")

    toccati = []
    for g in aggiunte:
        d = await db.articles.find_one({"slug": g["slug"]}, {"_id": 0, "content": 1})
        if not d:
            print(f"  AGGIUNTA su slug assente: {g['slug']}"); continue
        if g["nuovo"] in d["content"]:
            print(f"  aggiunta già presente in {g['slug'][:44]}"); continue
        if g["vecchio"] not in d["content"]:
            print(f"  AGGIUNTA NON APPLICABILE in {g['slug'][:44]} (frase non trovata)"); continue
        print(f"  aggiunta in {g['slug'][:44]}")
        if dry_run:
            continue
        await db.articles.update_one({"slug": g["slug"]}, {"$set": {
            "content": d["content"].replace(g["vecchio"], g["nuovo"], 1), "updated_at": datetime.now(timezone.utc)}})
        toccati.append(g["slug"])

    arts = [x async for x in db.articles.find({"published": True}, {"_id": 0, "slug": 1, "content": 1})]
    slugs = {x["slug"] for x in arts}
    rotti = [(x["slug"], l) for x in arts for l in re.findall(r"\]\(/blog/([a-z0-9-]+)\)", x["content"]) if l not in slugs]
    nuovi = [a["slug"] for a in articoli]
    orfani = [s for s in nuovi if s in slugs and not any(f"/blog/{s})" in b["content"] for b in arts if b["slug"] != s)]
    print(f"\n{'--dry-run: nessuna scrittura' if dry_run else f'pubblicati: {len(fatti)}, articoli con rimandi nuovi: {len(set(toccati))}'}"
          f" | link rotti: {rotti or 'nessuno'} | orfani: {orfani or 'nessuno'}")
    if ping and not dry_run and (fatti or toccati):
        try:
            from services.indexnow import ping_urls_async
            await ping_urls_async([f"/blog/{s}" for s in fatti + sorted(set(toccati))] + ["/blog"])
            print("IndexNow: ping inviato")
        except Exception as e:      # noqa: BLE001
            print("IndexNow non inviato:", e)


if __name__ == "__main__":
    args = sys.argv[1:]
    if "--file" not in args:
        sys.exit("serve --file percorso.json")
    asyncio.run(main(args[args.index("--file") + 1], "--dry-run" in args, "--ping" in args))
