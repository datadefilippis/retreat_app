"""NA10 (14/9/2026 notte) — i primi cinque articoli del piano SEO-editoriale
(docs/PIANO_SEO_EDITORIALE_2026-09.md, calendario §6), uno per porta:

  C  Meditazione guidata per dormire: 10 minuti           → il Cerchio
  O  Corso di yoga 200 ore: come valutarlo, cosa serve dopo → entra-nella-rete
  D  Riflessologia plantare: mappa, seduta, prezzi        → /operatori/riflessologia
  A  Welfare aziendale 2026: esempi, deducibilità, benessere → /aziende
  R  Yoga e ritiri in Toscana: la guida                   → il Cerchio

Regola del founder: nessun doppione dei 47 articoli esistenti (elenco in
docs/seo/articoli_esistenti_2026-09-14.json): questi cinque coprono intenti
che non avevano una pagina. Nessuna firma di operatori. Riscritti la stessa notte in forma
narrativa (feedback founder: «voglio storytelling, stile umano, non
frasi corte a punti»); i testi stanno in na10_testi.py. Ogni pezzo ha
«In breve», FAQ (domande in grassetto, per il FAQPage della shell),
link interni verso articoli che esistono davvero e la chiamata della sua
porta. Le affermazioni sul corpo hanno la fonte o la formula «chi lo
pratica dice».

    venv/bin/python scripts/na10_cinque_articoli_seo.py [--dry-run] [--ping]
"""
import asyncio
import os
import re
import sys
import uuid
from datetime import datetime, timezone

# i testi (narrativi) e i link di ritorno vivono in na10_testi.py
from na10_testi import PEZZI, AGGIUNTE   # noqa: E402

async def main(dry_run: bool, ping: bool) -> None:
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from database import db

    for slug, titolo, descr, in_breve, contenuto, categoria, correlati in PEZZI:
        faq = len(re.findall(r"^\*\*[^*]+\?\*\*$", contenuto, re.M))
        print(f"{titolo}\n  slug: {slug} | categoria: {categoria} | parole: {len(contenuto.split())}"
              f" | descrizione: {len(descr)} car. | FAQ: {faq} | in breve: {len(in_breve)} car.")
        assert len(descr) <= 165 and faq >= 4 and len(titolo) <= 62, "fuori misura"
        esistente = await db.articles.find_one({"slug": slug}, {"_id": 0, "id": 1})
        print("  stato:", "aggiornato" if esistente else "nuovo")
        if dry_run:
            continue
        now = datetime.now(timezone.utc)
        campi = {"title": titolo, "description": descr, "in_breve": in_breve,
                 "content": contenuto, "category": categoria, "author_name": "Aurya",
                 "access": "public", "published": True, "updated_at": now,
                 "translations": {}, "related_slugs": correlati}
        if not esistente:
            campi |= {"id": str(uuid.uuid4()), "slug": slug, "created_at": now, "published_at": now}
        await db.articles.update_one({"slug": slug}, {"$set": campi}, upsert=True)
        doc = await db.articles.find_one({"slug": slug}, {"_id": 0, "featured_image_url": 1})
        if not doc.get("featured_image_url"):
            from routers.articles import _autogen_cover
            url = await _autogen_cover(slug, categoria)
            if url:
                await db.articles.update_one({"slug": slug}, {"$set": {"featured_image_url": url}})
                print(f"  copertina: {url}")

    if not dry_run:
        for slug, vecchio, nuovo in AGGIUNTE:
            d = await db.articles.find_one({"slug": slug}, {"_id": 0, "content": 1})
            if not d:
                print(f"  ASSENTE {slug}")
            elif nuovo.split("\n\n")[0] in d["content"]:
                print(f"  link gia' presente in {slug[:42]}")
            elif vecchio in d["content"]:
                await db.articles.update_one({"slug": slug}, {"$set": {
                    "content": d["content"].replace(vecchio, nuovo, 1),
                    "updated_at": datetime.now(timezone.utc)}})
                print(f"  link aggiunto in {slug[:42]}")
            else:
                print(f"  NON TROVATO in {slug[:42]}")

    print("\n── controlli")
    arts = [a async for a in db.articles.find({"published": True}, {"_id": 0, "slug": 1, "content": 1,
                                                                    "featured_image_url": 1})]
    slugs = {a["slug"] for a in arts}
    rotti = [(a["slug"], l) for a in arts
             for l in re.findall(r"\]\(/blog/([a-z0-9-]+)\)", a["content"]) if l not in slugs]
    nuovi = {p[0] for p in PEZZI}
    orfani = [s for s in nuovi if s in slugs and not any(
        f"/blog/{s})" in b["content"] for b in arts if b["slug"] != s)]
    tic = re.compile(r"(con onest|onestà:|la parte onesta|senza misteri|dalla nostra esperienza)", re.I)
    print(f"  link rotti: {rotti or 'nessuno'}")
    print(f"  nuovi senza link in entrata: {orfani or 'nessuno'}")
    print(f"  tic: {sum(len(tic.findall(a['content'])) for a in arts)}")
    print(f"  TOTALE: {len(arts)} articoli, {sum(len(a['content'].split()) for a in arts)} parole")

    if ping and not dry_run:
        try:
            from services.indexnow import ping_urls_async
            await ping_urls_async([f"/blog/{p[0]}" for p in PEZZI] + ["/blog"])
            print("  IndexNow: ping inviato")
        except Exception as e:      # noqa: BLE001
            print("  IndexNow non inviato:", e)
    if dry_run:
        print("\n--dry-run: nessuna scrittura")


if __name__ == "__main__":
    asyncio.run(main("--dry-run" in sys.argv, "--ping" in sys.argv))
