"""SA2/SA3 — /api/admin/platform/* : il business di piattaforma.

Panoramica (SA2) e plancia directory (SA3) per il system admin.
Stesso perimetro degli altri router admin: 100% require_system_admin,
sole letture, cache in-process breve (i numeri non cambiano al
secondo e la pagina si apre spesso).
"""

import re
import time
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field

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


@router.get("/lunedi")
async def numeri_del_lunedi(
    current_user: dict = Depends(require_system_admin),
) -> Dict[str, Any]:
    """RB14 (10/9/2026, rebranding onda 3; piano di business §7.8) — i
    numeri di ogni lunedi', in un posto solo e senza stime: il Cerchio
    (e quanti con la citta'), i ritiri in programma, le visite, gli
    operatori attivi negli ultimi 90 giorni, le richieste di regia e
    team building, gli euro per motore. Cache 60s come la panoramica."""
    cached = _cached("lunedi")
    if cached:
        return cached
    from datetime import timedelta
    from database import (db, organizations_collection, products_collection,
                          event_occurrences_collection, users_collection,
                          richieste_struttura_collection)
    from models.common import utc_now
    from services.platform_insights import gmv_aggregates

    now = utc_now()
    iso = lambda d: d.isoformat()          # noqa: E731
    d7, d30, d90 = (now - timedelta(days=n) for n in (7, 30, 90))
    giorno7 = (now - timedelta(days=7)).strftime("%Y-%m-%d")
    giorno14 = (now - timedelta(days=14)).strftime("%Y-%m-%d")

    # 1. Il Cerchio (la fila): confermati, con la citta', nuovi in 7 giorni,
    #    quanti vogliono i ritiri, e le porte da cui sono entrati (RB13)
    sub_ = db.aurya_subscribers
    confermati = await sub_.count_documents({"status": "confirmed"})
    con_citta = await sub_.count_documents(
        {"status": "confirmed", "profile.city": {"$nin": [None, ""]}})
    con_ritiri = await sub_.count_documents(
        {"status": "confirmed", "preferences.retreat_alert.enabled": True})
    nuovi_7g = await sub_.count_documents(
        {"status": "confirmed",
         "$or": [{"confirmed_at": {"$gte": d7}}, {"confirmed_at": {"$gte": iso(d7)}}]})
    porte = {}
    async for row in sub_.aggregate([
            {"$match": {"$or": [{"created_at": {"$gte": d30}}, {"created_at": {"$gte": iso(d30)}}]}},
            {"$group": {"_id": "$source", "n": {"$sum": 1}}}]):
        porte[row["_id"] or "(sconosciuta)"] = row["n"]

    # 2. I ritiri in programma (pubblicati, futuri, online o su richiesta)
    prods = await products_collection.find(
        {"item_type": "event_ticket", "is_active": True, "is_published": True,
         "transaction_mode": {"$in": ["direct", "request"]}},
        {"_id": 0, "id": 1, "transaction_mode": 1, "organization_id": 1}).to_list(2000)
    campioni = {o["id"] async for o in organizations_collection.find(
        {"is_sample": True}, {"_id": 0, "id": 1})}
    prods = [p for p in prods if p["organization_id"] not in campioni]
    modo = {p["id"]: p.get("transaction_mode") for p in prods}
    occs = await event_occurrences_collection.find(
        {"product_id": {"$in": list(modo)}, "status": "published",
         "start_at": {"$gte": iso(now)}},
        {"_id": 0, "product_id": 1}).to_list(2000)
    ritiri = {"in_programma": len(occs),
              "online": sum(1 for o in occs if modo.get(o["product_id"]) == "direct"),
              "su_richiesta": sum(1 for o in occs if modo.get(o["product_id"]) == "request")}

    # 3. Le visite ai profili (page_views), 7 giorni contro i 7 prima
    visite = {"ultimi_7g": 0, "precedenti_7g": 0}
    async for row in db.page_views.aggregate([
            {"$match": {"day": {"$gte": giorno14}}},
            {"$group": {"_id": {"$gte": ["$day", giorno7]}, "hits": {"$sum": "$hits"}}}]):
        visite["ultimi_7g" if row["_id"] else "precedenti_7g"] = row["hits"]

    # 4. Gli operatori: quanti, quanti nella rete, quanti attivi (login 90g)
    orgs = await organizations_collection.find(
        {"is_sample": {"$ne": True}, "is_active": {"$ne": False},
         "legacy_commerce": {"$ne": True}, "deactivated_at": None},
        {"_id": 0, "id": 1, "network_member": 1, "public_profile": 1}).to_list(5000)
    org_ids = [o["id"] for o in orgs]
    attivi = set()
    async for u in users_collection.find(
            {"organization_id": {"$in": org_ids},
             "$or": [{"last_login_at": {"$gte": d90}}, {"last_login_at": {"$gte": iso(d90)}}]},
            {"_id": 0, "organization_id": 1}):
        attivi.add(u["organization_id"])
    from routers.fondatori import conteggio
    fond = await conteggio()
    operatori = {"totali": len(orgs),
                 "attivi_90g": len(attivi),
                 "nella_rete": sum(1 for o in orgs if o.get("network_member")),
                 "fondatori_presi": fond["presi"], "fondatori_tetto": fond["tetto"]}

    # 5. Le richieste (struttura, regia, team building): 30 giorni e aperte
    richieste = {"struttura": 0, "regia": 0, "team_building": 0, "aperte": 0}
    async for r in richieste_struttura_collection.find(
            {"creato_il": {"$gte": iso(d30)}}, {"_id": 0, "tipo": 1}):
        richieste[r.get("tipo") or "struttura"] = richieste.get(r.get("tipo") or "struttura", 0) + 1
    richieste["aperte"] = await richieste_struttura_collection.count_documents(
        {"stato": {"$in": ["nuova", "in_lavorazione"]}})

    # 6. Gli euro per motore: piattaforma (transato dei ritiri, 30g);
    #    i servizi non passano da qui finche' sono ordini manuali
    gmv = await gmv_aggregates()
    euro = {"ritiri_30g": round(sum(float(v.get("gmv") or 0) for v in gmv["by_channel_30d"].values()), 2)}

    # 7. Le sequenze (FV2): quante email di ogni passo sono partite in 30 giorni
    from services.sequenze import conta_invii
    sequenze = await conta_invii(d30)

    payload = {"cerchio": {"confermati": confermati, "con_citta": con_citta,
                           "con_ritiri": con_ritiri, "nuovi_7g": nuovi_7g, "porte_30g": porte},
               "ritiri": ritiri, "visite": visite, "operatori": operatori,
               "richieste": richieste, "euro": euro, "sequenze_30g": sequenze,
               "generated_at": iso(now)}
    _cache["lunedi"] = (time.monotonic(), payload)
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


@router.get("/signals")
async def platform_signals(
    current_user: dict = Depends(require_system_admin),
) -> Dict[str, Any]:
    """SA5 — i segnali del GTM: a chi proporre cosa, oggi. Quattro
    liste coi numeri che giustificano la proposta (break-even Pro,
    sbloccabili-Stripe, a rischio, in crescita)."""
    cached = _cached("signals")
    if cached:
        return cached

    from services.platform_insights import signals
    from models.common import utc_now

    payload = {**(await signals()), "generated_at": utc_now().isoformat()}
    _cache["signals"] = (time.monotonic(), payload)
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
    from services.platform_insights import PRO_BREAKEVEN_MONTHLY_EUR

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
    # NW4 — il numero che l'operatore vede nella SUA pagina newsletter e'
    # form + consensi dal checkout: qui l'admin deve vedere lo stesso
    # mondo, non solo i form (i checkout opt-in erano invisibili).
    form_subs = await db.newsletter_subscriptions.count_documents(
        {"organization_id": org_id})
    form_emails = await db.newsletter_subscriptions.distinct(
        "email", {"organization_id": org_id})
    checkout_optins = await db.customers.count_documents({
        "organization_id": org_id,
        "accepted_marketing_at": {"$ne": None},
        "marketing_revoked_at": None,
        "email": {"$nin": [e for e in form_emails if e]},
    })
    newsletter_subs = form_subs + checkout_optins

    # ── VT7: traffico dallo specchietto Visibilita' (stesse fonti) ───
    from routers.visibility import (_month_views, _month_impressions,
                                    _month_prefix, _prev_month)
    cur_p, prev_p = _month_prefix(now), _month_prefix(_prev_month(now))
    cur_v = await _month_views(db, org_id, cur_p)
    prev_v = await _month_views(db, org_id, prev_p)
    traffic = {
        "visits_month": cur_v["visits"],
        "uniques_month": cur_v["uniques"],
        "visits_prev_month": prev_v["visits"],
        "impressions_month": await _month_impressions(db, org_id, cur_p),
    }

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
            # GT2 lato piattaforma: sopra la soglia break-even il Pro
            # conviene all'operatore — il segnale di proposta
            "pro_breakeven_reached": fees["online_month"] / 100.0
                                     > PRO_BREAKEVEN_MONTHLY_EUR
                                     and plan_slug == "retreat_free",
        },
        "relationship": {
            "reviews_stats": org.get("reviews_stats"),
            "newsletter_subscribers": newsletter_subs,
            "last_login_at": last_login,
        },
        # VT7 — il traffico che Aurya gli porta (specchietto VT lato
        # piattaforma): il numero del pitch commerciale
        "traffic": traffic,
        "generated_at": now.isoformat(),
    }


# ── UT1 — Utenti finali (clientela marketplace) ─────────────────────────────
#
# Chi compra e si iscrive, NON gli operatori. Un "utente" e' una EMAIL:
# platform_accounts (account Aurya) ∪ email degli ordini guest (ordini il
# cui customer CRM ha un'email senza account piattaforma). Sola lettura.

# Coerenza tesoreria (RF1): lo "speso" conta solo ordini confermati/completati.
_UT1_SPENT_STATUSES = ["confirmed", "completed"]


def _ut1_base_pipeline() -> list:
    """Pipeline che unisce account e guest in UNA lista per email.

    1. platform_accounts → una riga per account (kind=account)
    2. $unionWith orders: lookup del customer CRM (orders non portano
       l'email: vive su customers via customer_id), group per email →
       una riga di statistiche ordini (kind=orders)
    3. $group finale per email: fonde anagrafica account + numeri ordini
    4. $lookup aurya_subscribers per lo stato newsletter
    """
    return [
        {"$project": {
            "_id": 0,
            "email": {"$toLower": "$email"},
            "kind": {"$literal": "account"},
            "account_name": "$name",
            "guest_name": {"$literal": None},
            "email_verified": {"$eq": ["$email_verified", True]},
            "created_at": "$created_at",
            "last_login_at": "$last_login_at",
            "aurya_accepted_at": "$aurya_legal.accepted_at",
            "orders_count": {"$literal": 0},
            "confirmed_orders": {"$literal": 0},
            "total_spent": {"$literal": 0.0},
            "last_order_at": {"$literal": None},
            "org_ids": {"$literal": []},
            "marketing": {"$literal": False},
        }},
        {"$unionWith": {"coll": "orders", "pipeline": [
            {"$lookup": {
                "from": "customers",
                "localField": "customer_id",
                "foreignField": "id",
                "as": "_cust",
                "pipeline": [{"$project": {
                    "_id": 0, "email": 1, "name": 1,
                    "accepted_marketing_at": 1,
                    "marketing_revoked_at": 1}}],
            }},
            {"$set": {"_cust": {"$first": "$_cust"}}},
            {"$set": {"email": {"$toLower":
                                {"$ifNull": ["$_cust.email", ""]}}}},
            # solo ordini con un'email vera dietro (POS anonimi esclusi)
            {"$match": {"email": {"$regex": "@"}}},
            {"$group": {
                "_id": "$email",
                "orders_count": {"$sum": 1},
                "confirmed_orders": {"$sum": {"$cond": [
                    {"$in": ["$status", _UT1_SPENT_STATUSES]}, 1, 0]}},
                "total_spent": {"$sum": {"$cond": [
                    {"$in": ["$status", _UT1_SPENT_STATUSES]},
                    {"$ifNull": ["$total", 0]}, 0]}},
                "last_order_at": {"$max": "$created_at"},
                "org_ids": {"$addToSet": "$organization_id"},
                "guest_name": {"$max": "$_cust.name"},
                # NW4 — il consenso marketing VERO: il checkout scrive
                # accepted_marketing_at / marketing_revoked_at, non un
                # flag booleano (che non esiste: era sempre False)
                "marketing": {"$max": {"$and": [
                    {"$ne": [{"$ifNull": ["$_cust.accepted_marketing_at",
                                          None]}, None]},
                    {"$eq": [{"$ifNull": ["$_cust.marketing_revoked_at",
                                          None]}, None]},
                ]}},
            }},
            {"$project": {
                "_id": 0,
                "email": "$_id",
                "kind": {"$literal": "orders"},
                "account_name": {"$literal": None},
                "guest_name": 1,
                "email_verified": {"$literal": False},
                "created_at": {"$literal": None},
                "last_login_at": {"$literal": None},
                "aurya_accepted_at": {"$literal": None},
                "orders_count": 1,
                "confirmed_orders": 1,
                "total_spent": 1,
                "last_order_at": 1,
                "org_ids": 1,
                "marketing": 1,
            }},
        ]}},
        # fusione per email: l'anagrafica arriva dalla riga account, i
        # numeri dalla riga ordini ($max scavalca i neutri dell'altra riga)
        {"$group": {
            "_id": "$email",
            "has_account": {"$max": {"$eq": ["$kind", "account"]}},
            "account_name": {"$max": "$account_name"},
            "guest_name": {"$max": "$guest_name"},
            "email_verified": {"$max": "$email_verified"},
            "created_at": {"$max": "$created_at"},
            "last_login_at": {"$max": "$last_login_at"},
            "aurya_accepted_at": {"$max": "$aurya_accepted_at"},
            "orders_count": {"$max": "$orders_count"},
            "confirmed_orders": {"$max": "$confirmed_orders"},
            "total_spent": {"$max": "$total_spent"},
            "last_order_at": {"$max": "$last_order_at"},
            "org_ids": {"$max": "$org_ids"},
            "marketing_opted_in": {"$max": "$marketing"},
        }},
        {"$lookup": {
            "from": "aurya_subscribers",
            "localField": "_id",
            "foreignField": "email",
            "as": "_nl",
            "pipeline": [{"$project": {"_id": 0, "status": 1}}],
        }},
        {"$set": {
            "email": "$_id",
            "name": {"$ifNull": ["$account_name", "$guest_name"]},
            "type": {"$cond": ["$has_account", "account", "guest"]},
            "newsletter_status": {"$first": "$_nl.status"},
            # FA5 (FARO, 30/8) — la FONTE dell'iscrizione in riga:
            # il founder targhettizza per canale (sound:*, cancello:*,
            # frequenze:*, newsletter...) senza aprire ogni dettaglio.
            "newsletter_source": {"$first": "$_nl.source"},
        }},
        {"$unset": ["_nl", "account_name", "guest_name", "has_account"]},
    ]


_UT1_SORTS = {
    "last_order": "last_order_at",
    "orders": "orders_count",
    "spent": "total_spent",
    "created": "created_at",
}


@router.get("/users")
async def platform_users(
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    search: Optional[str] = Query(None, max_length=120),
    has_orders: Optional[bool] = None,
    newsletter: Optional[bool] = None,
    verified: Optional[bool] = None,
    guests_only: bool = False,
    accounts_only: bool = False,
    sort: str = Query("last_order"),
    order: str = Query("desc"),
    current_user: dict = Depends(require_system_admin),
) -> Dict[str, Any]:
    """UT1 — la clientela finale in una tabella: account Aurya + guest
    (raggruppati per email), con newsletter, ordini, speso e operatori.
    Le StatCard (stats) sono GLOBALI, items/total rispettano i filtri."""
    from database import db, organizations_collection
    from models.common import utc_now

    match: Dict[str, Any] = {}
    if search and search.strip():
        rx = {"$regex": re.escape(search.strip()), "$options": "i"}
        match["$or"] = [{"email": rx}, {"name": rx}]
    if has_orders is True:
        match["orders_count"] = {"$gt": 0}
    elif has_orders is False:
        match["orders_count"] = 0
    if newsletter is True:
        match["newsletter_status"] = "confirmed"
    elif newsletter is False:
        match["newsletter_status"] = {"$ne": "confirmed"}
    if verified is True:
        match["email_verified"] = True
    elif verified is False:
        match["email_verified"] = False
    if guests_only:
        match["type"] = "guest"
    elif accounts_only:
        match["type"] = "account"

    sort_field = _UT1_SORTS.get(sort, "last_order_at")
    sort_dir = 1 if order == "asc" else -1
    filtered = [{"$match": match}] if match else []

    pipeline = _ut1_base_pipeline() + [{"$facet": {
        "stats": [{"$group": {
            "_id": None,
            "users_total": {"$sum": 1},
            "verified": {"$sum": {"$cond": ["$email_verified", 1, 0]}},
            "newsletter_confirmed": {"$sum": {"$cond": [
                {"$eq": ["$newsletter_status", "confirmed"]}, 1, 0]}},
            "with_orders": {"$sum": {"$cond": [
                {"$gt": ["$orders_count", 0]}, 1, 0]}},
        }}],
        "total": filtered + [{"$count": "n"}],
        "items": filtered + [
            {"$sort": {sort_field: sort_dir, "email": 1}},
            {"$skip": (page - 1) * page_size},
            {"$limit": page_size},
        ],
    }}]

    res = await db.platform_accounts.aggregate(pipeline).to_list(1)
    facet = res[0] if res else {}
    stats_row = (facet.get("stats") or [{}])[0]
    items = facet.get("items") or []

    # nomi operatori (solo per la pagina corrente, una query)
    org_ids = sorted({oid for it in items for oid in (it.get("org_ids") or [])})
    org_names: Dict[str, str] = {}
    if org_ids:
        async for o in organizations_collection.find(
                {"id": {"$in": org_ids}}, {"_id": 0, "id": 1, "name": 1}):
            org_names[o["id"]] = o.get("name") or o["id"][:8]

    out_items = []
    for it in items:
        ops = sorted(org_names.get(oid, oid[:8])
                     for oid in (it.get("org_ids") or []))
        out_items.append({
            "email": it.get("email"),
            "name": it.get("name"),
            "type": it.get("type"),
            "email_verified": bool(it.get("email_verified")),
            "created_at": it.get("created_at"),
            "last_login_at": it.get("last_login_at"),
            "newsletter_status": it.get("newsletter_status"),
            "newsletter_source": it.get("newsletter_source"),
            "orders_count": it.get("orders_count") or 0,
            "confirmed_orders": it.get("confirmed_orders") or 0,
            "total_spent": round(float(it.get("total_spent") or 0), 2),
            "operators": ops[:5],
            "operators_count": len(ops),
            "last_order_at": it.get("last_order_at"),
            "marketing_opted_in": bool(it.get("marketing_opted_in")),
            "aurya_accepted_at": it.get("aurya_accepted_at"),
        })

    total = (facet.get("total") or [{}])
    total_n = total[0].get("n", 0) if total else 0
    return {
        "items": out_items,
        "total": total_n,
        "page": page,
        "page_size": page_size,
        "stats": {
            "users_total": stats_row.get("users_total", 0),
            "verified": stats_row.get("verified", 0),
            "newsletter_confirmed": stats_row.get("newsletter_confirmed", 0),
            "with_orders": stats_row.get("with_orders", 0),
        },
        "generated_at": utc_now().isoformat(),
    }


@router.get("/users/detail")
async def platform_user_detail(
    email: Optional[str] = Query(None, max_length=254),
    account_id: Optional[str] = Query(None, max_length=64),
    current_user: dict = Depends(require_system_admin),
) -> Dict[str, Any]:
    """UT1 — il drill-down di UN utente finale: anagrafica, ordini (con
    operatore), record customer per-org, newsletter, consensi. Read-only:
    nessun dato viene toccato. Niente segreti (hash/token MAI esposti)."""
    from fastapi import HTTPException
    from database import (customers_collection, db, orders_collection,
                          organizations_collection,
                          platform_accounts_collection)
    from models.common import utc_now

    _ACCOUNT_SAFE = {"_id": 0, "id": 1, "email": 1, "name": 1, "phone": 1,
                     "language": 1, "email_verified": 1, "is_active": 1,
                     "created_at": 1, "last_login_at": 1, "aurya_legal": 1}

    account = None
    if account_id:
        account = await platform_accounts_collection.find_one(
            {"id": account_id}, _ACCOUNT_SAFE)
        if not account:
            raise HTTPException(status_code=404, detail="Account not found")
        email = account["email"]
    if not email or "@" not in email:
        raise HTTPException(status_code=400,
                            detail="Provide email or account_id")
    email_n = email.strip().lower()
    if account is None:
        account = await platform_accounts_collection.find_one(
            {"email": email_n}, _ACCOUNT_SAFE)

    # record CRM per-org con quella email (case-insensitive: i customer
    # storici possono avere l'email non normalizzata)
    email_rx = {"$regex": f"^{re.escape(email_n)}$", "$options": "i"}
    customers = await customers_collection.find(
        {"email": email_rx},
        {"_id": 0, "id": 1, "organization_id": 1, "name": 1,
         "accepted_marketing_at": 1, "marketing_revoked_at": 1,
         "created_at": 1},
    ).to_list(50)

    # ordini: via customer CRM (l'email vive li') + stamp platform_account_id
    or_clauses = []
    cust_ids = [c["id"] for c in customers if c.get("id")]
    if cust_ids:
        or_clauses.append({"customer_id": {"$in": cust_ids}})
    if account:
        or_clauses.append({"platform_account_id": account["id"]})
    orders = []
    if or_clauses:
        orders = await orders_collection.find(
            {"$or": or_clauses},
            {"_id": 0, "id": 1, "order_number": 1, "organization_id": 1,
             "status": 1, "payment_status": 1, "sales_channel": 1,
             "total": 1, "currency": 1, "created_at": 1, "order_date": 1},
        ).sort("created_at", -1).to_list(100)

    if not account and not customers and not orders:
        raise HTTPException(status_code=404, detail="User not found")

    # nomi operatori per ordini + record customer (una query)
    org_ids = sorted({o["organization_id"] for o in orders}
                     | {c["organization_id"] for c in customers})
    org_names: Dict[str, str] = {}
    if org_ids:
        async for o in organizations_collection.find(
                {"id": {"$in": org_ids}}, {"_id": 0, "id": 1, "name": 1}):
            org_names[o["id"]] = o.get("name") or o["id"][:8]
    for o in orders:
        o["operator_name"] = org_names.get(o["organization_id"],
                                           o["organization_id"][:8])
    for c in customers:
        c["organization_name"] = org_names.get(c["organization_id"],
                                               c["organization_id"][:8])
        # NW4 — dai timestamp veri (il flag booleano non esiste a DB)
        c["marketing_opted_in"] = bool(
            c.get("accepted_marketing_at")
            and not c.get("marketing_revoked_at"))
        c.pop("accepted_marketing_at", None)
        c.pop("marketing_revoked_at", None)

    newsletter = await db.aurya_subscribers.find_one(
        {"email": email_n},
        {"_id": 0, "status": 1, "source": 1, "created_at": 1,
         "confirmed_at": 1, "unsubscribed_at": 1})

    # consensi: stamp aurya_legal + audit immutabile contato per source
    audit_match: Dict[str, Any] = {"customer_email": email_n}
    if account:
        audit_match = {"$or": [{"customer_email": email_n},
                               {"user_id": account["id"]}]}
    audit_by_source = []
    async for row in db.consent_audit.aggregate([
            {"$match": audit_match},
            {"$group": {"_id": "$source", "n": {"$sum": 1},
                        "last_at": {"$max": "$accepted_at"}}},
            {"$sort": {"n": -1}},
            {"$limit": 20}]):
        audit_by_source.append({"source": row["_id"] or "(sconosciuta)",
                                "n": row["n"], "last_at": row.get("last_at")})

    spent = sum(float(o.get("total") or 0) for o in orders
                if o.get("status") in _UT1_SPENT_STATUSES)
    return {
        "email": email_n,
        "type": "account" if account else "guest",
        "account": account,
        "orders": orders,
        "orders_count": len(orders),
        "total_spent": round(spent, 2),
        "customers": customers,
        "newsletter": newsletter,
        "consents": {
            "aurya_legal": (account or {}).get("aurya_legal"),
            "audit_by_source": audit_by_source,
        },
        "generated_at": utc_now().isoformat(),
    }


# ── Le sequenze: i passi e l'anteprima (FV4, 10/9/2026 sera) ─────────────────
# Il founder deve poter LEGGERE ogni email prima che parta, per un
# destinatario vero. Stesso codice che invia, niente invio, niente
# marcatura.

@router.get("/sequenze/passi")
async def sequenze_passi(current_user: dict = Depends(require_system_admin)) -> Dict[str, Any]:
    from services.sequenze import elenco_passi
    return {"pubblici": elenco_passi()}


@router.get("/sequenze/anteprima")
async def sequenze_anteprima(
    pubblico: str = Query(..., max_length=20),
    passo: str = Query(..., max_length=30),
    email: Optional[str] = Query(default=None, max_length=200),
    current_user: dict = Depends(require_system_admin),
) -> Dict[str, Any]:
    from fastapi import HTTPException
    from services.sequenze import anteprima
    try:
        return await anteprima(pubblico, passo, email)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


# ── Gli ordini di tutta la piattaforma (SA-R, 10/9/2026 sera) ───────────────
# «controllo sugli ordini degli utenti, quali operatori»: gli ultimi
# ordini con operatore, cliente, righe, totale, stati; e il riepilogo per
# operatore degli ultimi 30 giorni. Sola lettura.

@router.get("/ordini")
async def ordini_piattaforma(
    limit: int = Query(default=100, ge=1, le=500),
    org_id: Optional[str] = Query(default=None, max_length=64),
    stato: Optional[str] = Query(default=None, max_length=20),
    current_user: dict = Depends(require_system_admin),
) -> Dict[str, Any]:
    from datetime import timedelta
    from database import (customers_collection, orders_collection, organizations_collection)
    from models.common import utc_now
    now = utc_now()
    d30 = now - timedelta(days=30)
    campioni = {o["id"] async for o in organizations_collection.find({"is_sample": True}, {"_id": 0, "id": 1})}
    q: Dict[str, Any] = {"organization_id": {"$nin": list(campioni)}}
    if org_id:
        q["organization_id"] = org_id
    if stato in ("draft", "confirmed", "completed", "cancelled"):
        q["status"] = stato
    rows = await orders_collection.find(
        q, {"_id": 0, "id": 1, "order_number": 1, "organization_id": 1, "customer_id": 1,
            "total": 1, "currency": 1, "status": 1, "payment_status": 1, "source": 1,
            "created_at": 1, "items.product_name": 1, "items.quantity": 1},
    ).sort("created_at", -1).limit(limit).to_list(limit)
    org_ids = {r["organization_id"] for r in rows}
    nomi = {o["id"]: o.get("name") or "" async for o in organizations_collection.find(
        {"id": {"$in": list(org_ids)}}, {"_id": 0, "id": 1, "name": 1})}
    clienti = {}
    async for c in customers_collection.find(
            {"id": {"$in": [r.get("customer_id") for r in rows if r.get("customer_id")]}},
            {"_id": 0, "id": 1, "email": 1, "name": 1, "first_name": 1, "last_name": 1, "full_name": 1}):
        nome = c.get("full_name") or c.get("name") or " ".join(x for x in (c.get("first_name"), c.get("last_name")) if x)
        clienti[c["id"]] = {"nome": nome or None, "email": c.get("email")}
    items = [{
        "id": r["id"], "order_number": r.get("order_number"),
        "org": {"id": r["organization_id"], "nome": nomi.get(r["organization_id"], "")},
        "customer": clienti.get(r.get("customer_id"), {"nome": None, "email": None}),
        "righe": [{"nome": it.get("product_name"), "qty": it.get("quantity")} for it in (r.get("items") or [])],
        "total": r.get("total"), "currency": r.get("currency") or "EUR",
        "status": r.get("status"), "payment_status": r.get("payment_status"),
        "source": r.get("source"), "created_at": r.get("created_at"),
    } for r in rows]
    # il riepilogo per operatore: 30 giorni, senza gli annullati
    per_op: Dict[str, Dict[str, Any]] = {}
    async for r in orders_collection.aggregate([
            {"$match": {"organization_id": {"$nin": list(campioni)}, "status": {"$ne": "cancelled"},
                        "$or": [{"created_at": {"$gte": d30}}, {"created_at": {"$gte": d30.isoformat()}}]}},
            {"$group": {"_id": "$organization_id", "ordini": {"$sum": 1}, "totale": {"$sum": "$total"}}},
            {"$sort": {"ordini": -1}}]):
        per_op[r["_id"]] = {"org_id": r["_id"], "ordini": r["ordini"], "totale": round(float(r["totale"] or 0), 2)}
    if per_op:
        async for o in organizations_collection.find({"id": {"$in": list(per_op)}}, {"_id": 0, "id": 1, "name": 1}):
            per_op[o["id"]]["nome"] = o.get("name") or o["id"][:8]
    operatori = [{"id": k, "nome": v} for k, v in sorted(nomi.items(), key=lambda kv: kv[1].lower())]
    return {"items": items, "per_operatore": list(per_op.values()), "operatori": operatori,
            "generated_at": now.isoformat()}


class ProvaSequenza(BaseModel):
    pubblico: str = Field(max_length=20)
    passo: str = Field(max_length=30)
    email: Optional[str] = Field(default=None, max_length=200)   # come la vedrebbe (destinatario vero)
    a: str = Field(max_length=200)                                # a chi mandare la prova


@router.post("/sequenze/prova")
async def sequenze_prova(payload: ProvaSequenza, current_user: dict = Depends(require_system_admin)) -> Dict[str, Any]:
    """SA-R (10/9/2026 sera, founder: «vedere le email in anteprima e poterle
    mandare»): la stessa email dell'anteprima, spedita SOLO all'indirizzo
    scritto (di norma il proprio), con [PROVA] nell'oggetto. Non marca
    nessuna sequenza."""
    import re as _re
    from fastapi import HTTPException
    from services.email_service import send_email
    from services.email_sequenze import risposte_a
    from services.sequenze import anteprima
    a = (payload.a or "").strip().lower()
    if not _re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", a):
        raise HTTPException(status_code=400, detail="Indirizzo della prova non valido")
    try:
        reso = await anteprima(payload.pubblico, payload.passo, payload.email or None)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    if not reso.get("oggetto"):
        return {"inviata": False, "nota": reso.get("nota")}
    ok = send_email(a, f"[PROVA] {reso['oggetto']}", reso["html"], reply_to=risposte_a(), bypass_gate=True)
    return {"inviata": True, "a": a, "oggetto": reso["oggetto"], "consegnata": bool(ok)}
