"""SA2/SA3 — aggregati di piattaforma per il system admin.

Il business di Aurya ha due motori: il canone (MRR, già coperto da
/admin/billing-overview/mrr) e le FEE sul transato marketplace (ledger
SA1). Qui vivono gli aggregati del secondo motore + lo stato della
directory, con le STESSE condizioni del gate pubblico (GT1b): mai
una "verità admin" diversa dalla verità del calendario.

Solo letture; niente stime: fee dal ledger timbrato, GMV dagli ordini
confermati, directory dalle condizioni reali.
"""

from collections import defaultdict
from datetime import timedelta
from typing import Any, Dict

from models.common import utc_now


def _month_key(iso: str) -> str:
    return (iso or "")[:7]


def _month_buckets(now, back: int = 11) -> list:
    y, m = now.year, now.month
    out = []
    for off in range(-back, 1):
        mm = m + off
        yy = y + (mm - 1) // 12
        mm = (mm - 1) % 12 + 1
        out.append(f"{yy:04d}-{mm:02d}")
    return out


async def fee_totals() -> Dict[str, Any]:
    """Fee e transato online dal ledger SA1 (rimborsi inclusi: le
    righe negative si sommano da sole)."""
    from database import db

    now = utc_now()
    month_start = now.isoformat()[:7]
    year_ago = (now - timedelta(days=365)).isoformat()

    by_month = defaultdict(lambda: {"fee_minor": 0, "amount_minor": 0})
    totals = {"fee_month_minor": 0, "fee_12m_minor": 0,
              "online_month_minor": 0, "online_12m_minor": 0}
    async for e in db.platform_fee_ledger.find(
            {}, {"_id": 0, "collected_at": 1, "fee_minor": 1,
                 "amount_minor": 1}).limit(100_000):
        at = e.get("collected_at") or ""
        mk = _month_key(at)
        by_month[mk]["fee_minor"] += int(e.get("fee_minor") or 0)
        by_month[mk]["amount_minor"] += int(e.get("amount_minor") or 0)
        if at >= year_ago:
            totals["fee_12m_minor"] += int(e.get("fee_minor") or 0)
            totals["online_12m_minor"] += int(e.get("amount_minor") or 0)
        if mk == month_start:
            totals["fee_month_minor"] += int(e.get("fee_minor") or 0)
            totals["online_month_minor"] += int(e.get("amount_minor") or 0)

    return {"totals": totals, "by_month": dict(by_month)}


async def gmv_aggregates() -> Dict[str, Any]:
    """GMV piattaforma dagli ordini confermati/completati: per mese
    (12), per canale (30gg) e per anima (12m)."""
    from database import orders_collection

    now = utc_now()
    cutoff_12m = (now - timedelta(days=365)).isoformat()[:10]
    cutoff_30d = (now - timedelta(days=30)).isoformat()[:10]
    match_base = {"status": {"$in": ["confirmed", "completed"]},
                  "order_date": {"$gte": cutoff_12m}}

    by_month = defaultdict(float)
    by_channel_30d: Dict[str, Dict[str, float]] = {}
    async for o in orders_collection.find(
            match_base,
            {"_id": 0, "order_date": 1, "total": 1, "sales_channel": 1}
    ).limit(100_000):
        day = (o.get("order_date") or "")[:10]
        total = float(o.get("total") or 0)
        by_month[day[:7]] += total
        if day >= cutoff_30d:
            ch = o.get("sales_channel") or "store"
            slot = by_channel_30d.setdefault(ch, {"orders": 0, "gmv": 0.0})
            slot["orders"] += 1
            slot["gmv"] += total

    by_type: list = []
    async for g in orders_collection.aggregate([
        {"$match": match_base},
        {"$unwind": "$items"},
        {"$group": {"_id": {"$ifNull": ["$items.item_type", "physical"]},
                    "revenue": {"$sum": "$items.line_total"}}},
        {"$sort": {"revenue": -1}},
    ]):
        by_type.append({"item_type": g["_id"] or "physical",
                        "revenue": round(g.get("revenue") or 0, 2)})

    months = [{"month": b, "gmv": round(by_month.get(b, 0.0), 2)}
              for b in _month_buckets(now)]
    return {"months": months, "by_channel_30d": by_channel_30d,
            "by_type_12m": by_type}


async def directory_snapshot() -> Dict[str, Any]:
    """Stato directory per org — STESSE condizioni del listing
    pubblico (GT1b): mode direct + Stripe active/ready + occurrence
    pubblicata futura con slug + pagina pubblica raggiungibile.

    Ritorna sia i contatori di piattaforma (SA2) sia le righe per-org
    (SA3): un solo calcolo, una sola verità.
    """
    from database import (db, organizations_collection, stores_collection,
                          payment_connections_collection,
                          products_collection, event_occurrences_collection)

    now_iso = utc_now().isoformat()[:16]

    # le org campione del prelaunch (is_sample) NON sono operatori:
    # fuori da contatori, directory e segnali — l'admin conta il vero
    orgs = {o["id"]: o for o in await organizations_collection.find(
        {"is_active": {"$ne": False}, "deactivated_at": None,
         "is_sample": {"$ne": True}},
        {"_id": 0, "id": 1, "name": 1, "commercial_plan_slug": 1,
         "directory_featured": 1, "public_slug": 1,
         "store_settings.is_storefront_published": 1,
         "reviews_stats": 1},
    ).to_list(2000)}
    org_ids = list(orgs)

    pay_ready = set()
    async for pc in payment_connections_collection.find(
            {"organization_id": {"$in": org_ids},
             "status": "active", "runtime_status": "ready"},
            {"_id": 0, "organization_id": 1}):
        pay_ready.add(pc["organization_id"])

    public_page = set()
    async for s in stores_collection.find(
            {"organization_id": {"$in": org_ids}, "is_published": True,
             "is_active": True, "visibility": "public"},
            {"_id": 0, "organization_id": 1}):
        public_page.add(s["organization_id"])
    for oid, o in orgs.items():
        if oid not in public_page and o.get("public_slug") \
                and (o.get("store_settings") or {}).get("is_storefront_published"):
            public_page.add(oid)

    # ritiri futuri pubblicati, spaccati per modalità del prodotto
    prod_mode: Dict[str, str] = {}
    async for p in products_collection.find(
            {"organization_id": {"$in": org_ids},
             "item_type": "event_ticket", "is_active": True,
             "is_published": True},
            {"_id": 0, "id": 1, "transaction_mode": 1}):
        prod_mode[p["id"]] = p.get("transaction_mode") or "direct"

    future_direct = defaultdict(int)
    future_other = defaultdict(int)
    async for occ in event_occurrences_collection.find(
            {"organization_id": {"$in": org_ids}, "status": "published",
             "slug": {"$nin": [None, ""]}, "start_at": {"$gte": now_iso}},
            {"_id": 0, "organization_id": 1, "product_id": 1}):
        mode = prod_mode.get(occ.get("product_id"))
        if mode is None:
            continue  # prodotto non pubblicato/attivo
        if mode == "direct":
            future_direct[occ["organization_id"]] += 1
        else:
            future_other[occ["organization_id"]] += 1

    # ordini 30gg per org: quanti dal calendario pubblico vs totale
    # (il polso di quanto la directory PORTA a ogni operatore)
    from database import orders_collection
    cutoff_30d = (utc_now() - timedelta(days=30)).isoformat()[:10]
    orders_30d: Dict[str, Dict[str, int]] = {}
    async for g in orders_collection.aggregate([
        {"$match": {"organization_id": {"$in": org_ids},
                    "status": {"$in": ["confirmed", "completed"]},
                    "order_date": {"$gte": cutoff_30d}}},
        {"$group": {"_id": {"org": "$organization_id",
                            "ch": {"$ifNull": ["$sales_channel", "store"]}},
                    "n": {"$sum": 1}}},
    ]):
        slot = orders_30d.setdefault(g["_id"]["org"],
                                     {"marketplace": 0, "total": 0})
        slot["total"] += g["n"]
        if g["_id"]["ch"] == "marketplace":
            slot["marketplace"] += g["n"]

    rows = []
    for oid, o in orgs.items():
        n_direct = future_direct.get(oid, 0)
        n_other = future_other.get(oid, 0)
        reasons = []
        if oid not in pay_ready:
            reasons.append("stripe_not_ready")
        if oid not in public_page:
            reasons.append("no_public_page")
        if n_direct == 0:
            reasons.append("no_direct_retreats")
        listed = not reasons and n_direct > 0
        o30 = orders_30d.get(oid, {"marketplace": 0, "total": 0})
        rows.append({
            "organization_id": oid,
            "name": o.get("name"),
            "plan_slug": o.get("commercial_plan_slug"),
            "featured": bool(o.get("directory_featured")),
            "listed": listed,
            "reasons": reasons,
            "retreats_listed": n_direct if listed else 0,
            "retreats_excluded": (n_direct if not listed else 0) + n_other,
            "orders_marketplace_30d": o30["marketplace"],
            "orders_total_30d": o30["total"],
            "reviews_stats": o.get("reviews_stats"),
        })
    rows.sort(key=lambda r: (not r["listed"], not r["featured"],
                             -(r["retreats_listed"] + r["retreats_excluded"])))

    listed_orgs = [r for r in rows if r["listed"]]
    stripe_only = [r for r in rows
                   if not r["listed"] and r["reasons"] == ["stripe_not_ready"]]
    return {
        "rows": rows,
        "counters": {
            "orgs_total": len(rows),
            "orgs_listed": len(listed_orgs),
            "retreats_listed": sum(r["retreats_listed"] for r in listed_orgs),
            "orgs_blocked_stripe_only": len(stripe_only),
        },
    }


# soglia break-even Gratis→Pro: 29 EUR / (5% - 0%) = 580 EUR/mese di
# transato online (stessa matematica del calcolatore GT2; il Pro e'
# a zero commissioni dal 16/7/2026)
PRO_BREAKEVEN_MONTHLY_EUR = 580.0


async def signals() -> Dict[str, Any]:
    """SA5 — i segnali commerciali del GTM 1-a-1: a chi proporre cosa,
    OGGI. Quattro liste, ognuna con i numeri che giustificano la
    proposta. Riusa lo snapshot directory (GT1b) e il ledger SA1 —
    mai euristiche nuove per dati che esistono gia'."""
    from database import db, orders_collection, users_collection

    now = utc_now()
    month_key = now.isoformat()[:7]
    d30 = (now - timedelta(days=30)).isoformat()[:10]
    d60 = (now - timedelta(days=60)).isoformat()[:10]
    d14_iso = (now - timedelta(days=14)).isoformat()

    snap = await directory_snapshot()
    rows_by_org = {r["organization_id"]: r for r in snap["rows"]}
    org_ids = list(rows_by_org)

    # transato online del mese per org (ledger SA1)
    online_month = defaultdict(int)
    async for e in db.platform_fee_ledger.find(
            {"organization_id": {"$in": org_ids}},
            {"_id": 0, "organization_id": 1, "amount_minor": 1,
             "collected_at": 1}).limit(100_000):
        if (e.get("collected_at") or "")[:7] == month_key:
            online_month[e["organization_id"]] += int(e.get("amount_minor") or 0)

    # GMV per finestra (0-30gg vs 31-60gg) + ultimo ordine per org
    gmv_recent = defaultdict(float)
    gmv_prev = defaultdict(float)
    last_order_day: Dict[str, str] = {}
    async for o in orders_collection.find(
            {"organization_id": {"$in": org_ids},
             "status": {"$in": ["confirmed", "completed"]}},
            {"_id": 0, "organization_id": 1, "total": 1,
             "order_date": 1}).limit(100_000):
        oid = o["organization_id"]
        day = (o.get("order_date") or "")[:10]
        total = float(o.get("total") or 0)
        if day >= d30:
            gmv_recent[oid] += total
        elif day >= d60:
            gmv_prev[oid] += total
        if day > last_order_day.get(oid, ""):
            last_order_day[oid] = day

    # VT7 — visite dallo specchietto (page_views): finestra 0-30gg
    # vs 31-60gg per i due segnali traffico
    visits_recent = defaultdict(int)
    visits_prev = defaultdict(int)
    async for row in db.page_views.aggregate([
            {"$match": {"organization_id": {"$in": org_ids},
                        "day": {"$gte": d60}}},
            {"$group": {"_id": {"org": "$organization_id",
                                "recent": {"$gte": ["$day", d30]}},
                        "visits": {"$sum": "$hits"}}}]):
        key = row["_id"]
        if key.get("recent"):
            visits_recent[key["org"]] = row["visits"]
        else:
            visits_prev[key["org"]] = row["visits"]

    # email del primo admin per il contatto one-click
    admin_email: Dict[str, str] = {}
    async for u in users_collection.find(
            {"organization_id": {"$in": org_ids}, "role": "admin"},
            {"_id": 0, "organization_id": 1, "email": 1}):
        admin_email.setdefault(u["organization_id"], u.get("email"))

    def base(oid: str) -> Dict[str, Any]:
        r = rows_by_org[oid]
        return {"organization_id": oid, "name": r["name"],
                "plan_slug": r["plan_slug"],
                "email": admin_email.get(oid)}

    pro_ready, unlockable, at_risk, growing = [], [], [], []
    for oid, r in rows_by_org.items():
        vol = online_month.get(oid, 0) / 100.0
        if r["plan_slug"] == "retreat_free" and vol > PRO_BREAKEVEN_MONTHLY_EUR:
            saving = round(vol * 0.05 - 29.0, 2)
            pro_ready.append({**base(oid), "online_month": round(vol, 2),
                              "monthly_saving": saving})
        if not r["listed"] and r["reasons"] == ["stripe_not_ready"]:
            # VT7 — le visite recenti rendono il "sbloccalo" urgente:
            # traffico vero che oggi finisce in un vicolo cieco
            unlockable.append({**base(oid),
                               "retreats_ready": r["retreats_excluded"],
                               "visits_30d": visits_recent.get(oid, 0)})
        # a rischio: aveva ordini ma fermo da 60gg, oppure account
        # maturo (>14gg) che non ha mai messo nulla online
        last = last_order_day.get(oid)
        if last and last < d60:
            at_risk.append({**base(oid), "kind": "silent_60d",
                            "last_order": last})
        elif not last and r["retreats_listed"] == 0 \
                and r["retreats_excluded"] == 0:
            org_doc = await db.organizations.find_one(
                {"id": oid}, {"_id": 0, "created_at": 1})
            created = str((org_doc or {}).get("created_at") or "")
            if created and created < d14_iso:
                at_risk.append({**base(oid), "kind": "never_started",
                                "created_at": created[:10]})
        # in crescita: 30gg recenti > 1.5x dei 30 precedenti, sopra
        # un pavimento che esclude il rumore
        rec, prev = gmv_recent.get(oid, 0.0), gmv_prev.get(oid, 0.0)
        if rec >= 500 and rec > prev * 1.5:
            growing.append({**base(oid), "gmv_30d": round(rec, 2),
                            "gmv_prev_30d": round(prev, 2)})

    # VT7 — traffico in calo: chi aveva un pubblico e lo sta perdendo
    # (nudge prima che sparisca). Pavimento anti-rumore: >=20 visite
    # nella finestra precedente, calo di almeno meta'.
    traffic_drop = []
    for oid in rows_by_org:
        prev_n, rec_n = visits_prev.get(oid, 0), visits_recent.get(oid, 0)
        if prev_n >= 20 and rec_n < prev_n * 0.5:
            traffic_drop.append({**base(oid), "visits_30d": rec_n,
                                 "visits_prev_30d": prev_n})
    traffic_drop.sort(key=lambda x: -x["visits_prev_30d"])

    pro_ready.sort(key=lambda x: -x["online_month"])
    growing.sort(key=lambda x: -x["gmv_30d"])
    unlockable.sort(key=lambda x: -x.get("visits_30d", 0))
    return {"pro_ready": pro_ready, "unlockable": unlockable,
            "at_risk": at_risk, "growing": growing,
            "traffic_drop": traffic_drop}
