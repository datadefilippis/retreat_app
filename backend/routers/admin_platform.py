"""SA2/SA3 — /api/admin/platform/* : il business di piattaforma.

Panoramica (SA2) e plancia directory (SA3) per il system admin.
Stesso perimetro degli altri router admin: 100% require_system_admin,
sole letture, cache in-process breve (i numeri non cambiano al
secondo e la pagina si apre spesso).
"""

import time
from typing import Any, Dict

from fastapi import APIRouter, Depends

from auth import require_system_admin

router = APIRouter(prefix="/admin/platform", tags=["Admin Platform"])

_CACHE_TTL = 60.0
_cache: Dict[str, "tuple[float, dict]"] = {}


def _cached(key: str):
    hit = _cache.get(key)
    if hit and (time.monotonic() - hit[0]) < _CACHE_TTL:
        return hit[1]
    return None


@router.get("/overview")
async def platform_overview(
    current_user: dict = Depends(require_system_admin),
) -> Dict[str, Any]:
    """SA2 — la panoramica: i miei soldi (fee dal ledger SA1) + il
    marketplace (GMV per mese/canale/anima) + lo stato directory.
    L'MRR resta sul suo endpoint dedicato (/admin/billing-overview/mrr):
    il frontend compone i due."""
    cached = _cached("overview")
    if cached:
        return cached

    from services.platform_insights import (fee_totals, gmv_aggregates,
                                            directory_snapshot)
    from models.common import utc_now

    fees = await fee_totals()
    gmv = await gmv_aggregates()
    directory = await directory_snapshot()

    fee_by_month = fees["by_month"]
    months = [{
        **m,
        "online": round(
            (fee_by_month.get(m["month"], {}).get("amount_minor", 0)) / 100.0, 2),
        "fees": round(
            (fee_by_month.get(m["month"], {}).get("fee_minor", 0)) / 100.0, 2),
    } for m in gmv["months"]]

    t = fees["totals"]
    payload = {
        "money": {
            "fees_month": t["fee_month_minor"] / 100.0,
            "fees_12m": t["fee_12m_minor"] / 100.0,
            "online_month": t["online_month_minor"] / 100.0,
            "online_12m": t["online_12m_minor"] / 100.0,
        },
        "months": months,
        "by_channel_30d": gmv["by_channel_30d"],
        "by_type_12m": gmv["by_type_12m"],
        "directory": directory["counters"],
        "generated_at": utc_now().isoformat(),
    }
    _cache["overview"] = (time.monotonic(), payload)
    return payload


@router.get("/directory")
async def platform_directory(
    current_user: dict = Depends(require_system_admin),
) -> Dict[str, Any]:
    """SA3 — la plancia directory: una riga per org con lo stato di
    listing (stesse condizioni GT1b), i ritiri dentro/fuori e i
    motivi. La stessa fotografia dei contatori della panoramica."""
    cached = _cached("directory")
    if cached:
        return cached

    from services.platform_insights import directory_snapshot
    from models.common import utc_now

    snap = await directory_snapshot()
    payload = {**snap, "generated_at": utc_now().isoformat()}
    _cache["directory"] = (time.monotonic(), payload)
    return payload


@router.get("/organizations/{org_id}/business-profile")
async def org_business_profile(
    org_id: str,
    current_user: dict = Depends(require_system_admin),
) -> Dict[str, Any]:
    """SA4 — la scheda 360° di UN operatore: presenza pubblica,
    transazioni per canale, quanto guadagna lui e quanto guadagno io
    (fee dal ledger SA1 + canone), relazione. Nessuna cache: si apre
    per decidere, deve essere fresca."""
    from datetime import timedelta
    from collections import defaultdict
    from database import (db, organizations_collection, stores_collection,
                          orders_collection, users_collection,
                          event_occurrences_collection)
    from models.common import utc_now
    from fastapi import HTTPException

    org = await organizations_collection.find_one(
        {"id": org_id},
        {"_id": 0, "id": 1, "name": 1, "commercial_plan_slug": 1,
         "application_fee_percent": 1, "directory_featured": 1,
         "public_slug": 1, "created_at": 1, "reviews_stats": 1,
         "store_settings.is_storefront_published": 1})
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")

    now = utc_now()
    cutoff_12m = (now - timedelta(days=365)).isoformat()[:10]
    month_key = now.isoformat()[:7]

    # ── presenza ─────────────────────────────────────────────────────
    stores = await stores_collection.find(
        {"organization_id": org_id, "is_active": True},
        {"_id": 0, "slug": 1, "name": 1, "is_published": 1},
    ).to_list(20)
    profile_slug = (stores[0]["slug"] if stores else None) \
        or (org.get("public_slug")
            if (org.get("store_settings") or {}).get("is_storefront_published")
            else None)

    # eventi futuri: dentro/fuori directory (riuso snapshot org-level)
    from services.platform_insights import directory_snapshot, _month_buckets
    snap = await directory_snapshot()
    dir_row = next((r for r in snap["rows"]
                    if r["organization_id"] == org_id), None)

    future_events = await event_occurrences_collection.count_documents(
        {"organization_id": org_id, "status": "published",
         "start_at": {"$gte": now.isoformat()[:16]}})

    # ── transazioni (ordini confermati 12m) ──────────────────────────
    by_channel: Dict[str, Dict[str, float]] = {}
    by_month = defaultdict(float)
    paid_online_via_intent = 0.0
    total_gmv = 0.0
    n_orders = 0
    async for o in orders_collection.find(
            {"organization_id": org_id,
             "status": {"$in": ["confirmed", "completed"]},
             "order_date": {"$gte": cutoff_12m}},
            {"_id": 0, "total": 1, "sales_channel": 1, "order_date": 1,
             "payment_intent": 1, "payment_status": 1}).limit(50_000):
        total = float(o.get("total") or 0)
        ch = o.get("sales_channel") or "store"
        slot = by_channel.setdefault(ch, {"orders": 0, "gmv": 0.0})
        slot["orders"] += 1
        slot["gmv"] += total
        by_month[(o.get("order_date") or "")[:7]] += total
        total_gmv += total
        n_orders += 1
        if o.get("payment_intent") == "collected":
            paid_online_via_intent += total

    # ── i miei guadagni (ledger SA1: la verita' timbrata) ────────────
    fees = {"month": 0, "y12": 0, "lifetime": 0,
            "online_month": 0, "online_12m": 0}
    year_ago_iso = (now - timedelta(days=365)).isoformat()
    async for e in db.platform_fee_ledger.find(
            {"organization_id": org_id},
            {"_id": 0, "fee_minor": 1, "amount_minor": 1,
             "collected_at": 1}).limit(50_000):
        fee = int(e.get("fee_minor") or 0)
        amt = int(e.get("amount_minor") or 0)
        at = e.get("collected_at") or ""
        fees["lifetime"] += fee
        if at >= year_ago_iso:
            fees["y12"] += fee
            fees["online_12m"] += amt
        if at[:7] == month_key:
            fees["month"] += fee
            fees["online_month"] += amt

    # canone dal piano (seed o catalogo custom)
    plan_slug = org.get("commercial_plan_slug")
    plan_price = None
    if plan_slug:
        plan_doc = await db.commercial_plans.find_one(
            {"slug": plan_slug}, {"_id": 0, "price_monthly": 1})
        if plan_doc:
            plan_price = float(plan_doc.get("price_monthly") or 0)

    # ── relazione ────────────────────────────────────────────────────
    last_login = None
    async for u in users_collection.find(
            {"organization_id": org_id},
            {"_id": 0, "last_login_at": 1}).limit(50):
        ll = u.get("last_login_at")
        ll = ll.isoformat() if hasattr(ll, "isoformat") else ll
        if ll and (last_login is None or ll > last_login):
            last_login = ll
    newsletter_subs = await db.newsletter_subscriptions.count_documents(
        {"organization_id": org_id})

    return {
        "organization_id": org_id,
        "name": org.get("name"),
        "plan_slug": plan_slug,
        "plan_price_monthly": plan_price,
        "fee_percent": float(org.get("application_fee_percent") or 0),
        "featured": bool(org.get("directory_featured")),
        "created_at": str(org.get("created_at") or "")[:10] or None,
        "presence": {
            "stores": [{"slug": s.get("slug"), "name": s.get("name"),
                        "published": bool(s.get("is_published"))}
                       for s in stores],
            "profile_slug": profile_slug,
            "future_events": future_events,
            "directory": dir_row,   # listed/reasons/retreats (GT1b)
        },
        "transactions": {
            "gmv_12m": round(total_gmv, 2),
            "orders_12m": n_orders,
            "avg_ticket": round(total_gmv / n_orders, 2) if n_orders else None,
            "by_channel": {k: {"orders": v["orders"],
                               "gmv": round(v["gmv"], 2)}
                           for k, v in by_channel.items()},
            # 12 bucket pieni (zeri inclusi): il grafico deve mostrare
            # anche i mesi vuoti, non solo quelli con ordini
            "by_month": [{"month": b, "gmv": round(by_month.get(b, 0.0), 2)}
                         for b in _month_buckets(now)],
            "collected_online_12m": round(paid_online_via_intent, 2),
        },
        "platform_earnings": {
            "fees_month": fees["month"] / 100.0,
            "fees_12m": fees["y12"] / 100.0,
            "fees_lifetime": fees["lifetime"] / 100.0,
            "online_month": fees["online_month"] / 100.0,
            "online_12m": fees["online_12m"] / 100.0,
            # GT2 lato piattaforma: sopra ~967 EUR/mese il Pro conviene
            # all'operatore — il segnale di proposta
            "pro_breakeven_reached": fees["online_month"] / 100.0 > 967
                                     and plan_slug == "retreat_free",
        },
        "relationship": {
            "reviews_stats": org.get("reviews_stats"),
            "newsletter_subscribers": newsletter_subs,
            "last_login_at": last_login,
        },
        "generated_at": now.isoformat(),
    }
