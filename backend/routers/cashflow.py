"""Cashflow consolidato — GET /analytics/cashflow (CF3, INSIGHTS_ACTION_PLAN).

UNA chiamata per la pagina /incassi: la tesoreria dell'operatore
letta dal libro mastro payment_schedules (la stessa fonte di verità
di payments-overview / aggregate_schedules — nessun KPI parallelo).

Payload:
  summary   incassato (12 mesi) / in arrivo / in ritardo / ticket medio
  months    12 bucket (-8..+3 mesi): incassato per paid_at,
            atteso per due_at delle righe non pagate — la curva
            tratteggiata mostra anche le caparre/saldi FUTURI già
            contrattualizzati (il dato di pianificazione)
  overdue   righe scadute non pagate + contatto cliente → sollecito
  upcoming  righe in scadenza nei prossimi 30 giorni + contatto
  by_product venduto per prodotto (ordini confermati 12 mesi)

Realtà dei dati: solo somme dal ledger e dagli ordini, niente stime.
Cache in-process 60s per org (pattern R13): la pagina è di lettura
frequente, il dato non cambia al secondo.
"""

import logging
import time
from collections import defaultdict
from datetime import timedelta
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends

from auth import get_verified_user
from models.common import utc_now

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/analytics", tags=["Analytics"])

_CACHE_TTL = 60.0
_cache: Dict[str, "tuple[float, dict]"] = {}

_UNPAID = ("pending", "overdue", "processing")
_PAID = ("paid", "paid_manual")

# cap difensivi (org singola: numeri reali molto sotto)
_MAX_SCHEDULES = 5000
_MAX_LIST_ROWS = 50


def _month_key(iso: str) -> str:
    return (iso or "")[:7]  # YYYY-MM


def _month_buckets(now) -> list:
    """12 bucket: 8 mesi passati + corrente + 3 futuri."""
    y, m = now.year, now.month
    out = []
    for off in range(-8, 4):
        mm = m + off
        yy = y + (mm - 1) // 12
        mm = (mm - 1) % 12 + 1
        out.append(f"{yy:04d}-{mm:02d}")
    return out


async def _build(org_id: str) -> Dict[str, Any]:
    """CG1 — la tesoreria è l'UNIONE di tre registri, senza sovrapposizioni:

      A. payment_schedules  — ritiri con caparra/saldo (verità riga per riga)
      B. orders SENZA schedule — ordini manuali/POS/servizi/fisici/digitali/
         corsi: payment_status + due_date (il gestionale classico)
      C. sales_records manuali — entrate registrate a mano nella pagina Dati

      Anti-double-counting: gli ordini con schedule si leggono SOLO dal
      ledger (B li esclude via order_id); i sales_records sincronizzati
      dagli ordini (dataset_id='orders') NON si contano mai qui — il loro
      ordine è già in A o B.
    """
    from database import db, orders_collection, customers_collection

    now = utc_now()
    now_iso = now.isoformat()
    today = now_iso[:10]
    horizon_30d = (now + timedelta(days=30)).isoformat()
    twelve_months_ago = (now - timedelta(days=365)).isoformat()

    schedules = await db.payment_schedules.find(
        {"organization_id": org_id},
        {"_id": 0, "order_id": 1, "currency": 1,
         "rows.kind": 1, "rows.label": 1, "rows.amount_minor": 1,
         "rows.due_at": 1, "rows.status": 1, "rows.paid_at": 1},
    ).to_list(_MAX_SCHEDULES)

    buckets = _month_buckets(now)
    incassato_by_month = defaultdict(int)
    atteso_by_month = defaultdict(int)
    summary = {"incassato_minor": 0, "in_arrivo_minor": 0, "in_ritardo_minor": 0}
    overdue_rows, upcoming_rows = [], []

    # ── Gamba A: libro mastro ritiri ─────────────────────────────────
    # RF1 — solo ordini CONFERMATI/COMPLETATI: la schedule nasce alla
    # creazione dell'ordine (draft), quindi senza questo filtro i
    # carrelli abbandonati e gli annullati finirebbero in "in arrivo/
    # in ritardo" (verificato in simulazione: 8.800€ fantasma).
    # scheduled_order_ids resta su TUTTE le schedule: un ordine draft
    # col ledger non deve comunque entrare dalla gamba B.
    scheduled_order_ids = {doc.get("order_id") for doc in schedules if doc.get("order_id")}
    confirmed_ids: set = set()
    if scheduled_order_ids:
        async for o in orders_collection.find(
                {"id": {"$in": list(scheduled_order_ids)},
                 "organization_id": org_id,
                 "status": {"$in": ["confirmed", "completed"]}},
                {"_id": 0, "id": 1}):
            confirmed_ids.add(o["id"])
    schedules = [d for d in schedules if d.get("order_id") in confirmed_ids]
    for doc in schedules:
        for row in doc.get("rows") or []:
            amount = row.get("amount_minor", 0)
            status = row.get("status")
            if status in _PAID:
                paid_at = row.get("paid_at") or ""
                if paid_at >= twelve_months_ago:
                    summary["incassato_minor"] += amount
                incassato_by_month[_month_key(paid_at)] += amount
            elif status in _UNPAID:
                due_at = row.get("due_at") or ""
                atteso_by_month[_month_key(due_at)] += amount
                entry = {
                    "source": "ledger",
                    "order_id": doc.get("order_id"),
                    "kind": row.get("kind"),
                    "label": row.get("label"),
                    "amount_minor": amount,
                    "due_at": due_at,
                }
                if due_at < now_iso:
                    summary["in_ritardo_minor"] += amount
                    overdue_rows.append(entry)
                else:
                    summary["in_arrivo_minor"] += amount
                    if due_at <= horizon_30d:
                        upcoming_rows.append(entry)

    # ── Gamba B: ordini SENZA schedule (il gestionale) ───────────────
    horizon_30d_day = horizon_30d[:10]
    cutoff_day = twelve_months_ago[:10]
    async for o in orders_collection.find(
            {"organization_id": org_id,
             "status": {"$in": ["confirmed", "completed"]},
             "id": {"$nin": list(scheduled_order_ids)}},
            {"_id": 0, "id": 1, "total": 1, "payment_status": 1,
             "order_date": 1, "due_date": 1, "order_number": 1,
             "customer_id": 1, "contact_phone": 1,
             "items.product_name": 1}).limit(_MAX_SCHEDULES):
        amount_minor = int(round(float(o.get("total") or 0) * 100))
        if amount_minor <= 0:
            continue
        order_day = (o.get("order_date") or "")[:10]
        if o.get("payment_status") == "paid":
            if order_day >= cutoff_day:
                summary["incassato_minor"] += amount_minor
            incassato_by_month[order_day[:7]] += amount_minor
        else:
            # non pagato: scadenza dichiarata, altrimenti la data ordine
            due_day = (o.get("due_date") or order_day or today)[:10]
            atteso_by_month[due_day[:7]] += amount_minor
            items = o.get("items") or []
            entry = {
                "source": "order",
                "order_id": o.get("id"),
                "kind": "order",
                "label": (items[0].get("product_name") if items else None),
                "amount_minor": amount_minor,
                "due_at": due_day,
            }
            if due_day < today:
                summary["in_ritardo_minor"] += amount_minor
                overdue_rows.append(entry)
            else:
                summary["in_arrivo_minor"] += amount_minor
                if due_day <= horizon_30d_day:
                    upcoming_rows.append(entry)

    # ── Gamba C: entrate manuali della pagina Dati ───────────────────
    async for r in db.sales_records.find(
            {"organization_id": org_id, "dataset_id": "manual"},
            {"_id": 0, "id": 1, "date": 1, "amount": 1, "description": 1,
             "category": 1, "payment_status": 1, "payment_date": 1,
             "due_date": 1, "customer_id": 1}).limit(_MAX_SCHEDULES):
        amount_minor = int(round(float(r.get("amount") or 0) * 100))
        if amount_minor == 0:
            continue
        day = (r.get("date") or "")[:10]
        # senza payment_status esplicito un'entrata manuale è incassata:
        # l'operatore registra ciò che è successo, non una previsione
        pstat = r.get("payment_status") or "paid"
        if pstat == "paid":
            paid_day = (r.get("payment_date") or day)[:10]
            if paid_day >= cutoff_day:
                summary["incassato_minor"] += amount_minor
            incassato_by_month[paid_day[:7]] += amount_minor
        else:
            due_day = (r.get("due_date") or day or today)[:10]
            atteso_by_month[due_day[:7]] += amount_minor
            entry = {
                "source": "manual",
                "order_id": None,
                "kind": "manual",
                "label": r.get("description") or r.get("category"),
                "amount_minor": amount_minor,
                "due_at": due_day,
                "customer_id": r.get("customer_id"),
            }
            if due_day < today:
                summary["in_ritardo_minor"] += amount_minor
                overdue_rows.append(entry)
            else:
                summary["in_arrivo_minor"] += amount_minor
                if due_day <= horizon_30d_day:
                    upcoming_rows.append(entry)

    overdue_rows.sort(key=lambda r: r["due_at"])
    upcoming_rows.sort(key=lambda r: r["due_at"])
    overdue_rows = overdue_rows[:_MAX_LIST_ROWS]
    upcoming_rows = upcoming_rows[:_MAX_LIST_ROWS]

    months = [{
        "month": b,
        "incassato": incassato_by_month.get(b, 0) / 100.0,
        "atteso": atteso_by_month.get(b, 0) / 100.0,
    } for b in buckets]

    # ── contatti per le righe azionabili ─────────────────────────────
    order_ids = list({r["order_id"] for r in overdue_rows + upcoming_rows if r.get("order_id")})
    orders_by_id: Dict[str, dict] = {}
    customers_by_id: Dict[str, dict] = {}
    if order_ids:
        async for o in orders_collection.find(
                {"id": {"$in": order_ids}, "organization_id": org_id},
                {"_id": 0, "id": 1, "order_number": 1, "customer_id": 1,
                 "contact_phone": 1, "items.product_name": 1, "locale": 1}):
            orders_by_id[o["id"]] = o
    # cliente: dall'ordine oppure diretto sulla riga (record manuali)
    cust_ids = {o.get("customer_id") for o in orders_by_id.values() if o.get("customer_id")}
    cust_ids |= {r.get("customer_id") for r in overdue_rows + upcoming_rows if r.get("customer_id")}
    if cust_ids:
        async for c in customers_collection.find(
                {"id": {"$in": list(cust_ids)}, "organization_id": org_id},
                {"_id": 0, "id": 1, "name": 1, "email": 1, "phone": 1}):
            customers_by_id[c["id"]] = c

    def _enrich(rows: list) -> list:
        out = []
        for r in rows:
            o = orders_by_id.get(r.get("order_id")) or {}
            c = customers_by_id.get(o.get("customer_id") or r.get("customer_id")) or {}
            items = o.get("items") or []
            out.append({
                **{k: v for k, v in r.items() if k != "customer_id"},
                "amount": r["amount_minor"] / 100.0,
                "order_number": o.get("order_number"),
                "product_name": (items[0].get("product_name") if items else None) or r.get("label"),
                "customer_id": c.get("id"),
                "customer_name": c.get("name"),
                "customer_email": c.get("email"),
                "customer_phone": c.get("phone") or o.get("contact_phone"),
            })
        return out

    # ── venduto per prodotto (ordini confermati, 12 mesi) ────────────
    # order_date è stringa ISO (default: data di created_at) su tutti i
    # doc — confronto lessicografico affidabile; created_at ha tipi misti
    # (datetime/str) sui dati storici.
    by_product = []
    order_date_cutoff = twelve_months_ago[:10]
    pipeline = [
        {"$match": {
            "organization_id": org_id,
            "status": {"$in": ["confirmed", "completed"]},
            "order_date": {"$gte": order_date_cutoff},
        }},
        {"$unwind": "$items"},
        {"$group": {"_id": "$items.product_name",
                    "revenue": {"$sum": "$items.line_total"},
                    "orders": {"$sum": 1}}},
        {"$sort": {"revenue": -1}},
        {"$limit": 8},
    ]
    try:
        async for g in orders_collection.aggregate(pipeline):
            by_product.append({
                "product_name": g["_id"] or "—",
                "revenue": round(g.get("revenue") or 0, 2),
                "orders": g.get("orders", 0),
            })
    except Exception as exc:  # created_at può essere str su doc legacy
        logger.warning("cashflow by_product aggregate failed: %s", exc)

    # ── CG2: venduto per ANIMA (item_type) — la vista olistica ───────
    # "Da cosa guadagno: ritiri, consulenze, fisici, digitali o corsi?"
    # Stessa base del by_product (ordini confermati 12 mesi, tutti i
    # tipi, inclusi quelli col ledger: qui si misura il VENDUTO) + il
    # bucket delle entrate manuali della pagina Dati.
    by_type = []
    try:
        async for g in orders_collection.aggregate([
            {"$match": {
                "organization_id": org_id,
                "status": {"$in": ["confirmed", "completed"]},
                "order_date": {"$gte": order_date_cutoff},
            }},
            {"$unwind": "$items"},
            {"$group": {"_id": {"$ifNull": ["$items.item_type", "physical"]},
                        "revenue": {"$sum": "$items.line_total"},
                        "orders": {"$sum": 1}}},
            {"$sort": {"revenue": -1}},
        ]):
            by_type.append({
                "item_type": g["_id"] or "physical",
                "revenue": round(g.get("revenue") or 0, 2),
                "orders": g.get("orders", 0),
            })
    except Exception as exc:
        logger.warning("cashflow by_type aggregate failed: %s", exc)
    manual_total = 0.0
    async for r in db.sales_records.find(
            {"organization_id": org_id, "dataset_id": "manual",
             "date": {"$gte": order_date_cutoff}},
            {"_id": 0, "amount": 1}).limit(_MAX_SCHEDULES):
        manual_total += float(r.get("amount") or 0)
    if manual_total:
        by_type.append({"item_type": "manual",
                        "revenue": round(manual_total, 2), "orders": 0})

    # ── ticket medio (ordini confermati 12 mesi) ─────────────────────
    ticket = None
    try:
        agg = await orders_collection.aggregate([
            {"$match": {
                "organization_id": org_id,
                "status": {"$in": ["confirmed", "completed"]},
                "order_date": {"$gte": order_date_cutoff},
            }},
            {"$group": {"_id": None, "avg": {"$avg": "$total"}, "n": {"$sum": 1}}},
        ]).to_list(1)
        if agg and agg[0].get("n"):
            ticket = round(agg[0]["avg"], 2)
    except Exception as exc:
        logger.warning("cashflow ticket aggregate failed: %s", exc)

    return {
        "summary": {
            "incassato": summary["incassato_minor"] / 100.0,
            "in_arrivo": summary["in_arrivo_minor"] / 100.0,
            "in_ritardo": summary["in_ritardo_minor"] / 100.0,
            "ticket_medio": ticket,
        },
        "months": months,
        "overdue": _enrich(overdue_rows),
        "upcoming": _enrich(upcoming_rows),
        "by_product": by_product,
        "by_type": by_type,
        "generated_at": now_iso,
    }


@router.get("/cashflow")
async def get_cashflow(
    current_user: dict = Depends(get_verified_user),
    fresh: Optional[bool] = False,
):
    """La tesoreria in una chiamata. ``fresh=true`` bypassa la cache
    (dopo un'azione di pagamento manuale)."""
    org_id = current_user["organization_id"]
    now = time.monotonic()
    cached = _cache.get(org_id)
    if cached and not fresh and (now - cached[0]) < _CACHE_TTL:
        return cached[1]
    payload = await _build(org_id)
    _cache[org_id] = (now, payload)
    return payload
