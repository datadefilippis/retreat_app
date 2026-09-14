"""NA11 (14/9/2026 notte) — revisione editoriale completa del Magazine nella
voce di Aurya (docs/REDAZIONE_VOCE_AURYA.md, brief del founder).

Legge `revisioni.json` ({slug: {title, description, in_breve, content}}),
prodotto dal validatore in locale dopo la revisione articolo per articolo
(titolo invariato, link identici, FAQ invariate nel numero, numeri e
fonti invariati, lunghezza 75-110%), e aggiorna content/description/
in_breve con `updated_at` vero. Non tocca slug, categoria, copertina,
related_slugs, access, published_at.

    python scripts/na11_revisione_voce.py [--dry-run] [--file percorso.json] [--ping]
"""
import asyncio
import json
import os
import re
import sys
from datetime import datetime, timezone


async def main(dry_run: bool, percorso: str, ping: bool) -> None:
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from database import db
    rev = json.load(open(percorso, encoding="utf-8"))
    print(f"{len(rev)} revisioni in {percorso}")
    fatti, saltati = [], []
    for slug, r in rev.items():
        doc = await db.articles.find_one({"slug": slug}, {"_id": 0, "title": 1, "content": 1})
        if not doc:
            saltati.append((slug, "assente")); continue
        if doc.get("title") != r["title"]:
            saltati.append((slug, "titolo diverso")); continue
        if doc.get("content", "").strip() == r["content"].strip():
            saltati.append((slug, "identico")); continue
        prima, dopo = len(doc.get("content", "").split()), len(r["content"].split())
        print(f"  {slug[:52]:52} {prima:5} → {dopo:5} parole")
        if dry_run:
            continue
        await db.articles.update_one({"slug": slug}, {"$set": {
            "content": r["content"], "description": r["description"], "in_breve": r["in_breve"],
            "updated_at": datetime.now(timezone.utc)}})
        fatti.append(slug)
    for s, perche in saltati:
        print(f"  SALTATO {s[:52]:52} ({perche})")
    # controlli finali sui link interni
    arts = [a async for a in db.articles.find({"published": True}, {"_id": 0, "slug": 1, "content": 1})]
    slugs = {a["slug"] for a in arts}
    rotti = [(a["slug"], l) for a in arts for l in re.findall(r"\]\(/blog/([a-z0-9-]+)\)", a["content"]) if l not in slugs]
    print(f"\n{'--dry-run: nessuna scrittura' if dry_run else f'aggiornati: {len(fatti)}'} | link rotti: {rotti or 'nessuno'}")
    if ping and not dry_run and fatti:
        try:
            from services.indexnow import ping_urls_async
            await ping_urls_async([f"/blog/{s}" for s in fatti] + ["/blog"])
            print("IndexNow: ping inviato")
        except Exception as e:      # noqa: BLE001
            print("IndexNow non inviato:", e)


if __name__ == "__main__":
    args = sys.argv[1:]
    percorso = args[args.index("--file") + 1] if "--file" in args else os.path.join(os.path.dirname(__file__), "revisioni.json")
    asyncio.run(main("--dry-run" in args, percorso, "--ping" in args))
