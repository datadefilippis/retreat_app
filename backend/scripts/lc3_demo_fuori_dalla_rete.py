"""LC3 — le organizzazioni demo fuori dalla rete pubblica.

IL PROBLEMA. La pagina /operatori (fase rete) elenca le org con
network_member=True, flag che assegna il system admin. In locale — e
potenzialmente in prod, dove il flag è stato provato durante RT3 — il
solo membro della rete era «Masseria Montanari Demo»: un profilo con
"Demo" nel nome, sulla pagina che racconta la selezione uno-a-uno
della rete. La revisione pre-lancio l'ha trovato linkato pubblicamente
(schermata 7.3 di /operatori) con tanto di recensione e "2 ritiri
organizzati" di prova.

LA REGOLA. Un'org è "demo" se: is_sample=True, oppure il nome o lo
slug pubblico contengono la parola "demo" come parola (non dentro
un'altra: "Demetra" non matcha). A queste org il flag network_member
viene tolto. Il flag resta assegnabile dall'admin: quando la masseria
vera entrerà nella rete, entrerà col suo nome vero.

Idempotente: rieseguirlo a flag già tolto non fa nulla. Da rieseguire
in produzione al lancio, come tutti gli script di contenuto.

    venv/bin/python scripts/lc3_demo_fuori_dalla_rete.py [--dry-run]
"""
import asyncio
import os
import re
import sys

_DEMO = re.compile(r"\bdemo\b", re.IGNORECASE)


def e_demo(org: dict) -> bool:
    return bool(org.get("is_sample")
                or _DEMO.search(org.get("name") or "")
                or _DEMO.search(org.get("public_slug") or ""))


async def main(dry_run: bool) -> None:
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from database import db

    membri = await db.organizations.find(
        {"network_member": True},
        {"_id": 0, "id": 1, "name": 1, "public_slug": 1, "is_sample": 1},
    ).to_list(1000)

    da_togliere = [o for o in membri if e_demo(o)]
    print(f"membri della rete: {len(membri)}")
    for o in membri:
        segno = "TOLGO " if o in da_togliere else "resta "
        print(f"  {segno} {o['name']!r} (slug={o.get('public_slug')})")

    if not dry_run and da_togliere:
        r = await db.organizations.update_many(
            {"id": {"$in": [o["id"] for o in da_togliere]}},
            {"$unset": {"network_member": ""}})
        print(f"aggiornate: {r.modified_count}")

    # audit: dopo lo script nessun membro pubblico deve essere demo
    if not dry_run:
        rimasti = await db.organizations.find(
            {"network_member": True},
            {"_id": 0, "name": 1, "public_slug": 1, "is_sample": 1},
        ).to_list(1000)
        sporchi = [o for o in rimasti if e_demo(o)]
        print(f"membri dopo: {len(rimasti)}, demo rimasti: "
              f"{[o['name'] for o in sporchi] or 'nessuno'}")

    if dry_run:
        print("\n--dry-run: nessuna scrittura")


if __name__ == "__main__":
    asyncio.run(main("--dry-run" in sys.argv))
