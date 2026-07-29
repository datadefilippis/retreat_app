"""
availability_index_service.py — LM4 (docs/LISTINO_MARKETPLACE_PIANO_2026-07.md)

Indice di disponibilita' DENORMALIZZATO per la ricerca cross-operatore:
risponde a "chi ha posto il giorno X?" su /public/operators senza
calcolare gli slot a runtime per ogni operatore della pagina.

Un documento per (organization_id, product_id, date):

    {organization_id, product_id, date: "YYYY-MM-DD",
     first_slot: "HH:MM", last_slot: "HH:MM", slot_count, updated_at}

INVARIANTE ASSOLUTA — l'indice serve SOLO alla ricerca. Il checkout e
gli slot mostrati al cliente restano sul motore esistente: questo
modulo NON duplica una sola regola di calcolo, materializza i prossimi
INDEX_DAYS giorni chiamando slot_generator.generate_available_slots
con scope="agenda" — la stessa identica chiamata di
GET /public/services/{id}/slots (routers/public.py). Se il motore
cambia, l'indice segue da solo al prossimo rebuild.

Scritture BEST-EFFORT: i punti che cambiano la disponibilita' (regole
availability, blocchi calendario, prenotazioni confermate/annullate)
chiamano schedule_rebuild() in fire-and-forget; un rebuild fallito
logga un warning e basta — mai un 500 sul flusso principale, mai
latenza aggiunta alla risposta. Reti di sicurezza:
  · job schedulato "availability_index_refresh" (scheduler S1, giro
    notturno di coerenza);
  · POST /admin/availability-index/rebuild (require_system_admin) per
    il primo popolamento post-deploy — vedi RUNBOOK_DEPLOY_LISTINO.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Dict, List, Optional, Set

from models.common import utc_now

logger = logging.getLogger(__name__)

# Orizzonte dell'indice: allineato al default del picker pubblico
# (GET /public/services/{id}/slots usa days=30).
INDEX_DAYS = 30


async def rebuild_for_product(org_id: str, product_id: str) -> int:
    """Riscrive (delete+insert) i documenti indice di UN servizio.

    Usa il motore slot esistente (generate_available_slots, scope
    "agenda" come l'endpoint pubblico). Se il prodotto non e' piu' un
    service pubblicato/attivo, i suoi documenti vengono solo rimossi.
    Ritorna il numero di giorni indicizzati.
    """
    from database import availability_index_collection, products_collection
    from services.slot_generator import generate_available_slots

    prod = await products_collection.find_one(
        {"id": product_id, "organization_id": org_id,
         "item_type": "service", "is_active": True, "is_published": True},
        {"_id": 0, "metadata": 1},
    )

    docs: List[Dict[str, Any]] = []
    if prod is not None:
        _dur, slots = await generate_available_slots(
            org_id=org_id,
            product_id=product_id,
            metadata=prod.get("metadata") or {},
            days=INDEX_DAYS,
            # Parita' totale con GET /public/services/{id}/slots: i
            # servizi condividono l'agenda del merchant (scope agenda).
            scope="agenda",
        )
        by_date: Dict[str, Dict[str, Any]] = {}
        for s in slots:
            b = by_date.get(s["date"])
            if b is None:
                by_date[s["date"]] = {
                    "first": s["start_time"],
                    "last": s["start_time"],
                    "count": 1,
                }
                continue
            b["count"] += 1
            if s["start_time"] < b["first"]:
                b["first"] = s["start_time"]
            if s["start_time"] > b["last"]:
                b["last"] = s["start_time"]
        now = utc_now().isoformat()
        docs = [{
            "organization_id": org_id,
            "product_id": product_id,
            "date": d,
            "first_slot": b["first"],
            "last_slot": b["last"],
            "slot_count": b["count"],
            "updated_at": now,
        } for d, b in sorted(by_date.items())]

    await availability_index_collection.delete_many(
        {"organization_id": org_id, "product_id": product_id})
    if docs:
        await availability_index_collection.insert_many(docs)
        for d in docs:
            d.pop("_id", None)
    return len(docs)


async def rebuild_for_org(org_id: str) -> int:
    """Ricostruisce l'indice per TUTTI i servizi attivi dell'org e
    rimuove i documenti orfani (prodotti spariti/ritirati).
    Ritorna il totale di giorni indicizzati."""
    from database import availability_index_collection, products_collection

    ids: List[str] = [
        p["id"] for p in await products_collection.find(
            {"organization_id": org_id, "item_type": "service",
             "is_active": True, "is_published": True},
            {"_id": 0, "id": 1},
        ).to_list(500)
    ]
    # Orfani: righe indice di prodotti non piu' a listino.
    await availability_index_collection.delete_many(
        {"organization_id": org_id, "product_id": {"$nin": ids}})
    total = 0
    for pid in ids:
        total += await rebuild_for_product(org_id, pid)
    return total


async def rebuild_all() -> Dict[str, Any]:
    """Rebuild completo (endpoint admin + refresh schedulato).
    Ritorna un summary {orgs, days} per journal/risposta."""
    from database import availability_index_collection, products_collection

    org_ids: List[str] = [
        o for o in await products_collection.distinct(
            "organization_id",
            {"item_type": "service", "is_active": True,
             "is_published": True},
        ) if o
    ]
    # Orfani globali: org senza piu' servizi a listino.
    await availability_index_collection.delete_many(
        {"organization_id": {"$nin": org_ids}})
    days = 0
    for org_id in org_ids:
        days += await rebuild_for_org(org_id)
    return {"orgs": len(org_ids), "days": days}


# ── Hook best-effort (fire-and-forget) ──────────────────────────────────────

# Riferimenti forti ai task in volo: senza, il garbage collector puo'
# cancellare un task fire-and-forget a meta' (asyncio docs).
_TASKS: Set[asyncio.Task] = set()


def schedule_rebuild(org_id: str, product_id: Optional[str] = None) -> None:
    """Aggancia un rebuild in background. MAI bloccante, MAI solleva.

    product_id valorizzato → rebuild del solo prodotto (regola oraria
    per-servizio). product_id None → rebuild dell'org intera: blocchi
    e prenotazioni hanno effetto cross-servizio (scope agenda), quindi
    un cambio su un prodotto puo' spostare gli slot di tutti gli altri.
    """
    async def _run() -> None:
        try:
            if product_id:
                await rebuild_for_product(org_id, product_id)
            else:
                await rebuild_for_org(org_id)
        except Exception as exc:  # noqa: BLE001 — best-effort dichiarato
            logger.warning(
                "availability_index: rebuild fallito org=%s product=%s: %s",
                org_id, product_id, exc)

    try:
        task = asyncio.get_running_loop().create_task(_run())
        _TASKS.add(task)
        task.add_done_callback(_TASKS.discard)
    except Exception as exc:  # noqa: BLE001 — es. nessun event loop
        logger.warning(
            "availability_index: schedule_rebuild saltato org=%s: %s",
            org_id, exc)


# ── Refresh notturno di sicurezza (scheduler S1) ────────────────────────────

from services.scheduler_service import register_job  # noqa: E402


@register_job("availability_index_refresh", interval_seconds=86_400)
async def availability_index_refresh_job() -> Dict[str, Any]:
    """Giro quotidiano di coerenza: anche se un hook best-effort si e'
    perso, entro 24h l'indice torna allineato al motore slot (e i
    giorni passati escono dalla finestra di 30)."""
    return await rebuild_all()
