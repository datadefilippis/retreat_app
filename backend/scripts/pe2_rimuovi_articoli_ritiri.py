"""PE2 — via dal Magazine gli articoli sui ritiri (founder, 2 ago 2026).

RAGIONE. Finche' non c'e' un ritiro da prenotare, portare qui chi
cerca "ritiri yoga in Puglia" e' traffico che rimbalza, e il rimbalzo
insegna ai motori che la pagina non serve. Il founder ha scelto di
cancellarli invece di spubblicarli, dopo aver saputo cosa si perde
(sono i cinque pezzi piu' lunghi e gia' indicizzati del Magazine).

QUELLO CHE FACCIAMO PERCHE' LA SCELTA RESTI REVERSIBILE. Prima di
toccare qualsiasi cosa il contenuto integrale finisce in un file
JSON versionato: se un domani il marketplace si accende, si
ripubblicano con un comando invece di riscriverli. La decisione e'
del founder, il rischio di perderli per sempre no.

    venv/bin/python scripts/pe2_rimuovi_articoli_ritiri.py [--dry-run]
    venv/bin/python scripts/pe2_rimuovi_articoli_ritiri.py --ripristina

Le copertine autogenerate NON vengono toccate: pesano pochi KB e se
gli articoli tornano tornano con la loro immagine.
"""
import asyncio
import json
import os
import sys
from pathlib import Path

SLUG = [
    "ritiri-olistici-in-italia-come-scegliere",
    "ritiri-yoga-toscana-guida",
    "ritiri-yoga-puglia-masserie-ulivi-mare",
    "quanto-costa-un-ritiro-yoga-in-italia",
    "cosa-portare-a-un-ritiro-lista-completa",
]

BACKUP = (Path(__file__).resolve().parent / "data"
          / "pe2_articoli_ritiri_backup.json")


def _serializza(doc: dict) -> dict:
    """Le date non stanno in JSON: diventano stringhe e tornano tali.
    Il ripristino le riscrive come sono, il modello le rilegge."""
    out = {}
    for k, v in doc.items():
        out[k] = v.isoformat() if hasattr(v, "isoformat") else v
    return out


async def _esporta(db, dry_run: bool) -> list:
    docs = []
    async for a in db.articles.find({"slug": {"$in": SLUG}}, {"_id": 0}):
        docs.append(_serializza(a))
    trovati = {d["slug"] for d in docs}
    for s in SLUG:
        if s not in trovati:
            print(f"  ATTENZIONE: {s} non e' nel database")
    if not dry_run and docs:
        BACKUP.parent.mkdir(parents=True, exist_ok=True)
        BACKUP.write_text(json.dumps(docs, ensure_ascii=False, indent=1),
                          encoding="utf-8")
        print(f"copia salvata: {BACKUP} ({BACKUP.stat().st_size // 1024} KB)")
    return docs


async def main(dry_run: bool, ripristina: bool) -> None:
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from database import db

    if ripristina:
        if not BACKUP.exists():
            print(f"nessuna copia in {BACKUP}")
            return
        docs = json.loads(BACKUP.read_text(encoding="utf-8"))
        for d in docs:
            await db.articles.update_one({"slug": d["slug"]},
                                         {"$set": d}, upsert=True)
        print(f"ripristinati {len(docs)} articoli")
        return

    docs = await _esporta(db, dry_run)
    if not docs:
        print("niente da rimuovere")
        return

    print(f"\n{len(docs)} articoli da rimuovere:")
    for d in docs:
        print(f"  {d.get('title', d['slug'])[:66]}")

    if dry_run:
        print("\n--dry-run: nessuna scrittura")
        return

    res = await db.articles.delete_many({"slug": {"$in": SLUG}})
    print(f"\nrimossi: {res.deleted_count}")
    print("per riaverli: scripts/pe2_rimuovi_articoli_ritiri.py --ripristina")


if __name__ == "__main__":
    asyncio.run(main("--dry-run" in sys.argv, "--ripristina" in sys.argv))
