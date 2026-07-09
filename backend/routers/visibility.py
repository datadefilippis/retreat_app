"""Visibilità operatore — GET /analytics/visibility (VT4).

Lo specchietto in UNA chiamata: il funnel IMPRESSION → VISITE →
PRENOTAZIONI del mese (con delta vs mese precedente), la provenienza
per canale, i trend e la tabella per ritiro. È la prova numerica della
promessa commerciale "con Aurya ti trovano".

Fonti (nessun KPI parallelo):
  impression   visibility_stats (VT3, contate server-side nei listing)
  visite       page_views (VT1/VT2: ping JS, dedup visitor giornaliero)
                → visits = somma hits, uniques = numero doc
  prenotazioni orders confermati/completati (fonte già esistente,
                sales_channel incluso)

Cache in-process 60s per org (pattern CF3): pagina di lettura,
il dato non cambia al secondo. ``fresh=true`` la bypassa.
"""

import logging
import time
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends

from auth import get_verified_user
from services.module_access import require_module

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/analytics", tags=["Analytics"],
                   dependencies=[Depends(require_module("visibility"))])

_CACHE_TTL = 60.0
_cache: Dict[str, "tuple[float, dict]"] = {}

_BOOKED = ("confirmed", "completed")
_MAX_ORDERS = 2000
_MAX_RETREAT_ROWS = 30


def _month_prefix(dt: datetime) -> str:
    return dt.strftime("%Y-%m")


def _prev_month(dt: datetime) -> datetime:
    return (dt.replace(day=1) - timedelta(days=1)).replace(day=1)


def _month_bounds(dt: datetime) -> "tuple[datetime, datetime]":
    start = dt.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    nxt = (start + timedelta(days=32)).replace(day=1)
    return start, nxt


async def _month_views(db, org_id: str, prefix: str) -> Dict[str, int]:
    """visits (somma hits) e uniques (doc) del mese."""
    rows = await db.page_views.aggregate([
        {"$match": {"organization_id": org_id,
                    "day": {"$regex": f"^{prefix}"}}},
        {"$group": {"_id": None, "visits": {"$sum": "$hits"},
                    "uniques": {"$sum": 1}}},
    ]).to_list(1)
    r = rows[0] if rows else {}
    return {"visits": r.get("visits", 0), "uniques": r.get("uniques", 0)}


async def _month_impressions(db, org_id: str, prefix: str) -> int:
    rows = await db.visibility_stats.aggregate([
        {"$match": {"organization_id": org_id, "metric": "impressions",
                    "day": {"$regex": f"^{prefix}"}}},
        {"$group": {"_id": None, "n": {"$sum": "$count"}}},
    ]).to_list(1)
    return rows[0]["n"] if rows else 0


async def _build(org_id: str) -> Dict[str, Any]:
    from database import db, orders_collection, event_occurrences_collection

    # VT3: le impression bumpate da pochi secondi sono ancora nel batch
    # in memoria — flushiamo prima di leggere, la dashboard è fresca
    from services.visit_tracking import flush_now
    await flush_now()

    now = datetime.now(timezone.utc)
    cur, prev = _month_prefix(now), _month_prefix(_prev_month(now))

    # ── colpo d'occhio: mese corrente vs precedente ──────────────────
    cur_v = await _month_views(db, org_id, cur)
    prev_v = await _month_views(db, org_id, prev)
    cur_imp = await _month_impressions(db, org_id, cur)
    prev_imp = await _month_impressions(db, org_id, prev)

    cur_start, cur_end = _month_bounds(now)
    prev_start, _ = _month_bounds(_prev_month(now))
    orders = await orders_collection.find(
        {"organization_id": org_id, "status": {"$in": list(_BOOKED)},
         "created_at": {"$gte": prev_start, "$lt": cur_end}},
        {"_id": 0, "created_at": 1, "sales_channel": 1,
         "items.occurrence_id": 1},
    ).to_list(_MAX_ORDERS)
    cur_orders = [o for o in orders
                  if (o.get("created_at") or prev_start) >= cur_start]
    prev_orders = [o for o in orders
                   if (o.get("created_at") or cur_end) < cur_start]

    # ── canali del mese (visite; raggruppati lato UI) ────────────────
    ch_rows = await db.page_views.aggregate([
        {"$match": {"organization_id": org_id,
                    "day": {"$regex": f"^{cur}"}}},
        {"$group": {"_id": "$channel", "visits": {"$sum": "$hits"}}},
    ]).to_list(10)
    channels = {r["_id"]: r["visits"] for r in ch_rows if r["_id"]}

    # ── trend: 12 mesi (mensile) + ultimi 30 giorni ──────────────────
    since_12m = (now - timedelta(days=365)).strftime("%Y-%m-%d")
    trend_rows = await db.page_views.aggregate([
        {"$match": {"organization_id": org_id, "day": {"$gte": since_12m}}},
        {"$group": {"_id": {"$substrCP": ["$day", 0, 7]},
                    "visits": {"$sum": "$hits"}}},
        {"$sort": {"_id": 1}},
    ]).to_list(14)
    trend_12m = [{"month": r["_id"], "visits": r["visits"]}
                 for r in trend_rows]

    since_30d = (now - timedelta(days=30)).strftime("%Y-%m-%d")
    day_rows = await db.page_views.aggregate([
        {"$match": {"organization_id": org_id, "day": {"$gte": since_30d}}},
        {"$group": {"_id": "$day", "visits": {"$sum": "$hits"}}},
        {"$sort": {"_id": 1}},
    ]).to_list(32)
    last_30d = [{"day": r["_id"], "visits": r["visits"]} for r in day_rows]

    # ── per ritiro (mese corrente): visite + prenotazioni ────────────
    ev_rows = await db.page_views.aggregate([
        {"$match": {"organization_id": org_id, "surface": "event",
                    "day": {"$regex": f"^{cur}"}}},
        {"$group": {"_id": {"slug": "$slug", "channel": "$channel"},
                    "visits": {"$sum": "$hits"},
                    "uniques": {"$sum": 1}}},
    ]).to_list(500)
    by_slug: Dict[str, dict] = {}
    for r in ev_rows:
        slug = r["_id"]["slug"]
        b = by_slug.setdefault(slug, {"visits": 0, "uniques": 0,
                                      "channels": {}})
        b["visits"] += r["visits"]
        b["uniques"] += r["uniques"]
        ch = r["_id"].get("channel")
        if ch:
            b["channels"][ch] = b["channels"].get(ch, 0) + r["visits"]

    occ_meta: Dict[str, dict] = {}
    occ_by_id: Dict[str, str] = {}
    if by_slug:
        occs = await event_occurrences_collection.find(
            {"organization_id": org_id,
             "slug": {"$in": list(by_slug.keys())}},
            {"_id": 0, "id": 1, "slug": 1, "title": 1, "start_at": 1,
             "product_id": 1},
        ).to_list(500)
        for o in occs:
            occ_meta[o["slug"]] = o
            occ_by_id[o["id"]] = o["slug"]
        # il nome vive sul PRODOTTO (l'occorrenza ha solo lo slug)
        prod_ids = {o.get("product_id") for o in occs if o.get("product_id")}
        if prod_ids:
            from database import products_collection
            prods = await products_collection.find(
                {"id": {"$in": list(prod_ids)}},
                {"_id": 0, "id": 1, "name": 1},
            ).to_list(500)
            name_by_prod = {p["id"]: p.get("name") for p in prods}
            for o in occs:
                o["title"] = (o.get("title")
                              or name_by_prod.get(o.get("product_id")))

    bookings_by_slug: Dict[str, int] = {}
    for o in cur_orders:
        for it in (o.get("items") or []):
            slug = occ_by_id.get(it.get("occurrence_id") or "")
            if slug:
                bookings_by_slug[slug] = bookings_by_slug.get(slug, 0) + 1

    per_retreat = []
    for slug, b in by_slug.items():
        meta = occ_meta.get(slug) or {}
        booked = bookings_by_slug.get(slug, 0)
        top = max(b["channels"], key=b["channels"].get) \
            if b["channels"] else None
        per_retreat.append({
            "slug": slug,
            "title": meta.get("title") or slug,
            "start_at": meta.get("start_at"),
            "visits": b["visits"],
            "uniques": b["uniques"],
            "bookings": booked,
            "conversion_pct": round(booked / b["visits"] * 100, 1)
            if b["visits"] else 0.0,
            "top_channel": top,
        })
    per_retreat.sort(key=lambda r: -r["visits"])
    per_retreat = per_retreat[:_MAX_RETREAT_ROWS]

    # ── la prova Aurya: visite che lo store da solo non avrebbe ──────
    aurya_visits = channels.get("directory", 0) + channels.get("search", 0)

    return {
        "month": cur,
        "summary": {
            "impressions": {"current": cur_imp, "previous": prev_imp},
            "visits": {"current": cur_v["visits"],
                       "previous": prev_v["visits"]},
            "uniques": {"current": cur_v["uniques"],
                        "previous": prev_v["uniques"]},
            "bookings": {"current": len(cur_orders),
                         "previous": len(prev_orders)},
        },
        "channels": channels,
        "aurya_visits": aurya_visits,
        "trend_12m": trend_12m,
        "last_30d": last_30d,
        "per_retreat": per_retreat,
        "generated_at": now.isoformat(),
    }


@router.get("/visibility")
async def get_visibility(
    current_user: dict = Depends(get_verified_user),
    fresh: Optional[bool] = False,
):
    """Lo specchietto Visibilità in una chiamata (org-scoped)."""
    org_id = current_user["organization_id"]
    now = time.monotonic()
    cached = _cache.get(org_id)
    if cached and not fresh and (now - cached[0]) < _CACHE_TTL:
        return cached[1]
    payload = await _build(org_id)
    _cache[org_id] = (now, payload)
    return payload
