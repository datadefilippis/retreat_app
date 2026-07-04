"""Wellness-center case study seed.

Wipes ALL existing demo data for a specific org and seeds a coherent,
realistic dataset for a small Ticino wellness center:

  • Store: "Centro Benessere Lugano" (CHF, IT-first)
  • Products:
      - 4 massaggi (booking, 60-90 min, CHF 95-140)
      - 1 yoga class (event_ticket, weekly group)
      - 1 reiki session (event_ticket, biweekly group)
      - 2 retail items (olio essenziale, voucher regalo)
  • Customers: 22 personas — top regulars, occasional, lapsed, brand new
  • Orders: ~100 spread over last 6 months
      - status mix: 70 % completed, 15 % confirmed (in progress),
        10 % draft (pending), 5 % cancelled
      - line-item mix: 60 % massage bookings, 25 % yoga, 10 % reiki,
        5 % retail
      - per-order amount realistic (CHF 30-280)
  • sales_records aligned with confirmed/completed orders so the
    cashflow side, the customer_metrics analytics, and the AI tools
    all see consistent data.

IDEMPOTENT
----------
Re-running the script wipes ONLY the documents tagged with
``metadata.demo_seed = "wellness_case_v1"`` (or the equivalent
``source_label`` for sales_records). Real merchant data on other orgs
is never touched.

USAGE
-----
    cd backend
    set -a; source .env; set +a
    ./venv/bin/python -m scripts.seed_wellness_case_study

    # different org:
    ./venv/bin/python -m scripts.seed_wellness_case_study --org-id <uuid>
"""

from __future__ import annotations

import argparse
import asyncio
import random
import sys
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

_BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_BACKEND_DIR))


DEFAULT_ORG_ID = "16d64b96-b90f-4705-b6aa-03d279014909"
SEED_TAG = "wellness_case_v1"
SALES_SOURCE_LABEL = "demo_seed_wellness_case_v1"


# ── Personas (22 customers, diversified history) ────────────────────────────


PERSONAS = [
    # ── TOP regulars (high frequency, recent, multi-product) ──────────
    {"name": "Anna Bianchi",   "email": "anna.bianchi@example.test",   "phone": "+41 79 123 45 01", "tier": "top"},
    {"name": "Marco Rossi",    "email": "marco.rossi@example.test",    "phone": "+41 79 123 45 02", "tier": "top"},
    {"name": "Elena Müller",   "email": "elena.mueller@example.test",  "phone": "+41 79 234 56 78", "tier": "top"},

    # ── ACTIVE regulars (recent, moderate freq) ──────────────────────
    {"name": "Sara Conti",     "email": "sara.conti@example.test",     "phone": "+41 79 345 67 89", "tier": "active"},
    {"name": "Giulia Pellegrini", "email": "giulia.p@example.test",    "phone": None,               "tier": "active"},
    {"name": "Davide Ferri",   "email": "davide.ferri@example.test",   "phone": "+41 79 456 78 90", "tier": "active"},
    {"name": "Chiara Greco",   "email": "chiara.greco@example.test",   "phone": "+41 79 567 89 01", "tier": "active"},
    {"name": "Roberto Gilardi", "email": "r.gilardi@example.test",     "phone": "+41 79 678 90 12", "tier": "active"},

    # ── OCCASIONAL (last visit 60-150 days ago) ──────────────────────
    {"name": "Hans Bühler",    "email": "hans.buehler@example.test",   "phone": None,               "tier": "occasional"},
    {"name": "Lorenzo Mazzoni", "email": "lorenzo.mazzoni@example.test", "phone": "+41 79 789 01 23", "tier": "occasional"},
    {"name": "Francesca Vitali", "email": "f.vitali@example.test",     "phone": "+41 79 890 12 34", "tier": "occasional"},
    {"name": "Tommaso Donati", "email": "tommaso.donati@example.test", "phone": None,               "tier": "occasional"},

    # ── INACTIVE (last visit > 200 days) ─────────────────────────────
    {"name": "Paola Schmid",   "email": "paola.schmid@example.test",   "phone": "+41 79 901 23 45", "tier": "inactive"},
    {"name": "Fabio Lombardi", "email": "fabio.lombardi@example.test", "phone": None,               "tier": "inactive"},
    {"name": "Valentina Rinaldi", "email": "v.rinaldi@example.test",   "phone": "+41 79 012 34 56", "tier": "inactive"},

    # ── NEW (first visit in last 30 days) ────────────────────────────
    {"name": "Sofia Bruno",    "email": "sofia.bruno@example.test",    "phone": "+41 79 111 22 33", "tier": "new"},
    {"name": "Antonio Marchi", "email": "antonio.m@example.test",      "phone": "+41 79 222 33 44", "tier": "new"},
    {"name": "Laura Zanetti",  "email": "laura.zanetti@example.test",  "phone": None,               "tier": "new"},

    # ── ONE-SHOT (single visit a while ago — at-risk feel) ──────────
    {"name": "Stefano Rizzo",  "email": "stefano.r@example.test",      "phone": "+41 79 333 44 55", "tier": "one_shot"},
    {"name": "Camilla Verdi",  "email": "camilla.v@example.test",      "phone": "+41 79 444 55 66", "tier": "one_shot"},

    # ── Studio B2B clients (corporate massage gift packs) ───────────
    {"name": "Studio Legale SA",  "email": "info@studiolegale.test",   "phone": "+41 91 555 12 34", "tier": "b2b"},
    {"name": "Hotel Splendido",   "email": "amministrazione@splendido.test", "phone": "+41 91 922 33 44", "tier": "b2b"},
]


# ── Catalog ────────────────────────────────────────────────────────────────


PRODUCTS = [
    # ── Massaggi (service) ────────────────────────────────────────────
    # Use item_type=service (not the deprecated 'booking') so each
    # product gets:
    #   · a dedicated landing page at /p/<org-slug>/<product-slug>
    #   · the "Scopri" CTA on the storefront card (instead of the inline
    #     slot picker which only supports one booking product per page)
    #   · service_options / has_availability_slots / duration in the
    #     catalog response — wired up by the catalog endpoint's
    #     batched fetcher (see routers/public.py Phase 5 refactor).
    #
    # `slug` is REQUIRED for the Link to render (`product.slug && orgSlug`
    # in StorefrontPage.js:583). The seed used to omit it, leaving the
    # storefront card with no clickable action for service products.
    #
    # `duration` (minutes) goes into metadata.duration_minutes and drives
    # the slot picker's grid granularity on the landing page.
    {"key": "msg_relax",   "slug": "massaggio-rilassante-60-min",   "name": "Massaggio Rilassante 60 min",   "price": 95,  "type": "service", "category": "Massaggi", "unit": "sessione", "duration": 60},
    {"key": "msg_decont",  "slug": "massaggio-decontratturante-90-min", "name": "Massaggio Decontratturante 90 min", "price": 140, "type": "service", "category": "Massaggi", "unit": "sessione", "duration": 90},
    {"key": "msg_sport",   "slug": "massaggio-sportivo-60-min",     "name": "Massaggio Sportivo 60 min",     "price": 110, "type": "service", "category": "Massaggi", "unit": "sessione", "duration": 60},
    {"key": "msg_drain",   "slug": "massaggio-drenante-75-min",     "name": "Massaggio Drenante 75 min",     "price": 120, "type": "service", "category": "Massaggi", "unit": "sessione", "duration": 75},

    # ── Yoga + Reiki (event_ticket — gruppo) ──────────────────────────
    {"key": "evt_yoga",    "slug": "lezione-yoga-di-gruppo",        "name": "Lezione Yoga di Gruppo",        "price": 28,  "type": "event_ticket", "category": "Yoga",      "unit": "lezione"},
    {"key": "evt_reiki",   "slug": "sessione-reiki-collettiva",     "name": "Sessione Reiki Collettiva",     "price": 45,  "type": "event_ticket", "category": "Reiki",     "unit": "sessione"},

    # ── Retail (physical) ─────────────────────────────────────────────
    {"key": "ret_oil",     "slug": "olio-essenziale-rilassante-50ml", "name": "Olio Essenziale Rilassante 50ml", "price": 32, "type": "physical",    "category": "Retail",    "unit": "pz"},
    {"key": "ret_voucher", "slug": "buono-regalo-massaggio",         "name": "Buono Regalo Massaggio",         "price": 100, "type": "physical",    "category": "Retail",    "unit": "buono"},
]


# Mapping tier → behaviour (orders count, days range, product mix bias)
TIER_PROFILES = {
    "top":        {"orders": (18, 25), "days": (5,  180), "mix": "varied"},
    "active":     {"orders": (8,  14), "days": (10, 150), "mix": "massage_heavy"},
    "occasional": {"orders": (3,  6),  "days": (60, 150), "mix": "single_category"},
    "inactive":   {"orders": (2,  5),  "days": (210, 360), "mix": "single_category"},
    "new":        {"orders": (1,  3),  "days": (1,  28),  "mix": "trial"},
    "one_shot":   {"orders": (1,  1),  "days": (90, 180), "mix": "single"},
    "b2b":        {"orders": (3,  6),  "days": (10, 180), "mix": "voucher_pack"},
}


# ── Helpers ───────────────────────────────────────────────────────────────


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _gen_id() -> str:
    return str(uuid.uuid4())


def _date_iso(d: datetime) -> str:
    return d.date().isoformat()


def _pick_product_for_mix(mix: str) -> dict:
    if mix == "single":
        return next(p for p in PRODUCTS if p["key"] == "msg_relax")
    if mix == "single_category":
        return random.choice([p for p in PRODUCTS if p["category"] == "Massaggi"])
    if mix == "trial":
        # new customers typically book a trial massage or yoga
        return random.choice([p for p in PRODUCTS if p["key"] in ("msg_relax", "evt_yoga")])
    if mix == "voucher_pack":
        return random.choice([p for p in PRODUCTS if p["key"] in ("ret_voucher", "msg_relax", "msg_decont")])
    if mix == "massage_heavy":
        # 70% massage, 25% event, 5% retail. Massages now use
        # item_type=service (was 'booking' before the Phase-7 hotfix)
        # so the order-mix matcher follows the same type label.
        r = random.random()
        if r < 0.70:
            return random.choice([p for p in PRODUCTS if p["type"] == "service"])
        if r < 0.95:
            return random.choice([p for p in PRODUCTS if p["type"] == "event_ticket"])
        return random.choice([p for p in PRODUCTS if p["type"] == "physical"])
    # varied (default for top customers)
    weights = [40, 40, 25, 25, 30, 15, 8, 12]
    return random.choices(PRODUCTS, weights=weights, k=1)[0]


def _pick_order_status(days_ago: int) -> tuple[str, str]:
    """Return (status, payment_status) skewed by recency.

    Recent (< 7d): more drafts (in-flight)
    7-180d: mostly completed / confirmed
    > 180d: completed or cancelled
    """
    r = random.random()
    if days_ago < 7:
        if r < 0.40:
            return "draft", "pending"
        if r < 0.75:
            return "confirmed", "paid"
        if r < 0.92:
            return "completed", "paid"
        return "cancelled", "pending"
    if days_ago < 180:
        if r < 0.78:
            return "completed", "paid"
        if r < 0.90:
            return "confirmed", "paid"
        if r < 0.97:
            return "draft", "pending"
        return "cancelled", "pending"
    # > 180d
    if r < 0.85:
        return "completed", "paid"
    if r < 0.95:
        return "cancelled", "pending"
    return "completed", "overdue"


# ── Wipe phase ────────────────────────────────────────────────────────────


async def wipe_org_data(org_id: str) -> dict:
    """Hard wipe: remove every commerce + customer document scoped to this org.

    Scope is intentionally broad because the user explicitly asked for a
    clean slate. Other orgs in the same MongoDB are untouched.
    """
    from database import (
        stores_collection,
        products_collection,
        orders_collection,
        customers_collection,
        sales_records_collection,
        customer_metrics_collection,
    )

    # Optional collections — wrap in try since not every install has them
    try:
        from database import product_metrics_collection
    except ImportError:
        product_metrics_collection = None

    try:
        from database import issued_tickets_collection
    except ImportError:
        issued_tickets_collection = None

    try:
        from database import issued_bookings_collection
    except ImportError:
        issued_bookings_collection = None

    try:
        from database import event_occurrences_collection
    except ImportError:
        event_occurrences_collection = None

    r_stores    = await stores_collection.delete_many({"organization_id": org_id})
    r_products  = await products_collection.delete_many({"organization_id": org_id})
    r_orders    = await orders_collection.delete_many({"organization_id": org_id})
    r_customers = await customers_collection.delete_many({"organization_id": org_id})
    r_sales     = await sales_records_collection.delete_many({"organization_id": org_id})
    r_metrics   = await customer_metrics_collection.delete_many({"organization_id": org_id})

    r_pmetrics  = 0
    r_tickets   = 0
    r_bookings  = 0
    r_occur     = 0
    if product_metrics_collection is not None:
        res = await product_metrics_collection.delete_many({"organization_id": org_id})
        r_pmetrics = res.deleted_count
    if issued_tickets_collection is not None:
        res = await issued_tickets_collection.delete_many({"organization_id": org_id})
        r_tickets = res.deleted_count
    if issued_bookings_collection is not None:
        res = await issued_bookings_collection.delete_many({"organization_id": org_id})
        r_bookings = res.deleted_count
    if event_occurrences_collection is not None:
        res = await event_occurrences_collection.delete_many({"organization_id": org_id})
        r_occur = res.deleted_count

    return {
        "stores": r_stores.deleted_count,
        "products": r_products.deleted_count,
        "orders": r_orders.deleted_count,
        "customers": r_customers.deleted_count,
        "sales_records": r_sales.deleted_count,
        "customer_metrics": r_metrics.deleted_count,
        "product_metrics": r_pmetrics,
        "issued_tickets": r_tickets,
        "issued_bookings": r_bookings,
        "event_occurrences": r_occur,
    }


# ── Update org settings ──────────────────────────────────────────────────


async def update_org(org_id: str):
    from database import organizations_collection
    await organizations_collection.update_one(
        {"id": org_id},
        {"$set": {
            "name": "Centro Benessere Lugano",
            "currency": "CHF",
            "industry": "Wellness & Massage",
            "updated_at": _now_iso(),
        }}
    )


# ── Seed phases ───────────────────────────────────────────────────────────


async def seed_store(org_id: str) -> dict:
    from database import stores_collection

    now_iso = _now_iso()
    store_id = _gen_id()
    doc = {
        "id": store_id,
        "organization_id": org_id,
        "slug": "centro-benessere-lugano",
        "name": "Centro Benessere Lugano",
        "description": "Il tuo centro benessere a due passi dal lago. Massaggi su misura, yoga di gruppo e sessioni Reiki collettive — tutto in un'unica oasi di relax.",
        "visibility": "public",
        # Only `shipping` and `local_pickup` are in SUPPORTED_FULFILLMENT_MODES
        # (see models/store.py). A wellness center is a service business —
        # customers come in person — so local_pickup is the natural choice.
        # The legacy `not_required` value was unknown to the frontend
        # selector and would be rejected by Phase 2's StoreUpdate validator.
        "fulfillment_modes": ["local_pickup"],
        "storefront_languages": ["it", "de", "fr", "en"],
        "is_published": True,
        "is_default": True,
        "is_active": True,
        "brand_color": "#9C7B5A",
        "brand_color_text": "#FFFFFF",
        "contact_email": "info@centrobenessere-lugano.ch",
        "contact_phone": "+41 91 555 12 34",
        "notification_email": "admin@centrobenessere-lugano.ch",
        "reply_to_email": "info@centrobenessere-lugano.ch",
        "sender_display_name": "Centro Benessere Lugano",
        "seo_title": "Centro Benessere Lugano — Massaggi, Yoga, Reiki",
        "seo_description": "Centro benessere a Lugano: massaggi, yoga, reiki. Prenota online la tua sessione.",
        "metadata": {"demo_seed": SEED_TAG},
        "created_at": now_iso,
        "updated_at": now_iso,
    }
    await stores_collection.insert_one(doc)
    return doc


async def seed_products(org_id: str, store_id: str) -> dict[str, dict]:
    """Insert the 8 products. Returns {key: product_doc}."""
    from database import products_collection

    now_iso = _now_iso()
    by_key: dict[str, dict] = {}

    for spec in PRODUCTS:
        pid = _gen_id()

        # Build product metadata. Services get `duration_minutes` so the
        # landing-page slot picker knows the slot granularity, and
        # `use_default_schedule: True` so the slot generator synthesizes
        # a Mon-Sat 9-18 schedule without requiring DB rows in
        # availability_rules_collection. The catalog endpoint reads both
        # signals (see routers/public.py:_fetch_availability_rule_signals
        # — the `use_default_schedule` flag is OR'd with rule presence).
        meta: dict = {"demo_seed": SEED_TAG}
        if spec["type"] == "service" and spec.get("duration"):
            meta["duration_minutes"] = spec["duration"]
            meta["use_default_schedule"] = True

        doc = {
            "id": pid,
            "organization_id": org_id,
            # The Product model expects `store_ids: List[str]` (plural),
            # not `store_id`. The public catalog query uses:
            #   $or: [{store_ids: <id>}, {store_ids: $size 0}, {store_ids: $exists False}]
            # so a missing/single `store_id` field would still fall through to
            # the $exists branch — but it leaves the data schema-incoherent
            # with admin tooling that reads `store_ids`. Use the plural form.
            "store_ids": [store_id],
            # `slug` is REQUIRED for service products to render the
            # "Scopri" CTA on the storefront card. Without it the
            # frontend strips the Link and falls back to inline qty
            # controls — which doesn't make sense for services (the
            # customer needs to pick a slot first). Pre-fix the seed
            # left slug=null and the cards looked broken on the demo.
            "slug": spec["slug"],
            "name": spec["name"],
            "sku": spec["key"].upper(),
            "category": spec["category"],
            "unit_price": spec["price"],
            "currency": "CHF",
            "cost_price": round(spec["price"] * 0.35, 2),
            "unit": spec["unit"],
            "description": _description_for(spec["key"]),
            "is_published": True,
            # Pydantic defaults DON'T apply to raw Mongo inserts — without
            # this field the doc has `is_active=None`, and the catalog
            # query (`is_active: True`) filters it out. This was the root
            # cause of the storefront showing zero products.
            "is_active": True,
            "item_type": spec["type"],
            "unit_label": spec["unit"],
            "price_mode": "fixed",
            "transaction_mode": "direct" if spec["type"] != "physical" else "direct",
            "stock_quantity": None,  # services / events / vouchers — no stock tracking
            "tags": [spec["category"].lower()],
            "metadata": meta,
            "created_at": now_iso,
            "updated_at": now_iso,
        }
        await products_collection.insert_one(doc)
        by_key[spec["key"]] = doc

    return by_key


def _description_for(key: str) -> str:
    descs = {
        "msg_relax":   "Massaggio rilassante a corpo intero per allentare lo stress accumulato. Oli essenziali inclusi.",
        "msg_decont":  "Massaggio decontratturante mirato per la cervicale e la schiena. Tecnica profonda.",
        "msg_sport":   "Massaggio sportivo pre/post allenamento. Sblocca le tensioni muscolari profonde.",
        "msg_drain":   "Massaggio drenante linfatico per migliorare la circolazione e ridurre il gonfiore.",
        "evt_yoga":    "Lezione yoga di gruppo (max 10 persone) ogni martedì e giovedì sera. Tutti i livelli.",
        "evt_reiki":   "Sessione Reiki collettiva (max 6 persone) il sabato pomeriggio. Energetica e riequilibrante.",
        "ret_oil":     "Olio essenziale rilassante alla lavanda e camomilla. Per uso quotidiano a casa.",
        "ret_voucher": "Buono regalo di CHF 100 — utilizzabile per qualsiasi servizio del centro.",
    }
    return descs.get(key, "")


async def seed_customers(org_id: str) -> list[dict]:
    from database import customers_collection

    now_iso = _now_iso()
    docs = []
    for p in PERSONAS:
        cid = _gen_id()
        docs.append({
            "id": cid,
            "organization_id": org_id,
            "name": p["name"],
            "email": p["email"],
            "phone": p["phone"],
            "tags": [p["tier"]],
            "is_active": True,
            "metadata": {"demo_seed": SEED_TAG, "tier": p["tier"]},
            "created_at": now_iso,
            "updated_at": now_iso,
        })
    if docs:
        await customers_collection.insert_many(docs)
    return docs


async def seed_orders(org_id: str, store_id: str,
                      customers: list[dict], products: dict[str, dict]) -> tuple[int, int]:
    """Insert orders + matching sales_records. Returns (n_orders, n_sales)."""
    from database import orders_collection, sales_records_collection

    now_dt = datetime.now(timezone.utc)
    now_iso = now_dt.isoformat()

    order_docs = []
    sales_docs = []
    order_counter = 0

    for customer in customers:
        tier = customer["metadata"]["tier"]
        prof = TIER_PROFILES[tier]
        n_orders = random.randint(*prof["orders"])

        for _ in range(n_orders):
            order_counter += 1
            days_ago = random.randint(*prof["days"])
            order_date = now_dt - timedelta(days=days_ago)
            order_iso = order_date.isoformat()
            status, payment_status = _pick_order_status(days_ago)

            # Build line items (most orders are 1 item; some are 2)
            n_items = 2 if (tier == "b2b" or random.random() < 0.15) else 1
            items = []
            order_total = 0.0
            for _ in range(n_items):
                prod_spec = _pick_product_for_mix(prof["mix"])
                product = products[prod_spec["key"]]
                qty = (
                    random.randint(2, 5) if (tier == "b2b" and prod_spec["key"] == "ret_voucher")
                    else 1
                )
                unit_price = product["unit_price"]
                line_total = round(qty * unit_price, 2)
                order_total += line_total

                line: dict = {
                    "product_id": product["id"],
                    "product_name": product["name"],
                    "sku": product["sku"],
                    "category": product["category"],
                    "item_type": product["item_type"],
                    "transaction_mode": product["transaction_mode"],
                    "quantity": qty,
                    "unit_price": unit_price,
                    "discount_pct": 0,
                    "line_total": line_total,
                    "extras": [],
                    "extras_total": 0.0,
                }
                # Service slot snapshot. Pre-hotfix this matched
                # item_type=="booking" — the wellness seed has been
                # migrated to item_type=="service" so the order-line
                # snapshot now keys off the new label. The line shape
                # (booking_date / booking_start_time / booking_end_time)
                # is unchanged so admin order details + customer-portal
                # display keep working without code changes.
                if product["item_type"] == "service":
                    slot_date = order_date + timedelta(days=random.choice([1, 2, 3, 5, 7]))
                    line["booking_date"] = _date_iso(slot_date)
                    line["booking_start_time"] = random.choice(["10:00", "11:00", "14:00", "15:30", "17:00"])
                    line["booking_end_time"] = random.choice(["11:00", "12:00", "15:00", "16:30", "18:00"])
                # Event occurrence snapshot
                elif product["item_type"] == "event_ticket":
                    line["occurrence_id"] = f"occ_{_gen_id()[:12]}"
                    line["occurrence_start_at"] = (order_date + timedelta(days=random.choice([2, 4, 7, 14]))).replace(
                        hour=18 if product["sku"] == "EVT_YOGA" else 16, minute=0, second=0
                    ).isoformat()
                    line["occurrence_location"] = "Sala principale — Centro Benessere Lugano"
                items.append(line)

            order_id = _gen_id()
            # 2026-05-20 — Conform to the canonical order_number format
            # (``ORD-{N:04d}``, see repositories/order_repository.py header).
            # The previous "ORD-CB-XXXX" custom prefix broke the runtime
            # parser in ``get_next_order_number`` (last.split("-",1)[1]
            # → "CB-XXXX" → ValueError → silent fallback to ORD-0001 →
            # confirm_order failed forever with "Impossibile assegnare
            # numero ordine dopo 3 tentativi"). One single source of
            # truth for the format keeps the parser straightforward.
            order_number = f"ORD-{order_counter:04d}"

            order_doc = {
                "id": order_id,
                "organization_id": org_id,
                "store_id": store_id,
                "customer_id": customer["id"],
                "customer_name": customer["name"],
                "customer_email": customer["email"],
                "customer_phone": customer["phone"],
                "order_number": order_number,
                "status": status,
                "payment_status": payment_status,
                "currency": "CHF",
                "subtotal": order_total,
                "total": order_total,
                "items": items,
                "fulfillment": {
                    "mode": "not_required",
                    "status": (
                        "fulfilled" if status == "completed"
                        else "pending" if status == "confirmed"
                        else "cancelled" if status == "cancelled"
                        else "not_required"
                    ),
                },
                "created_at": order_iso,
                "updated_at": now_iso,
                "metadata": {"demo_seed": SEED_TAG},
            }
            order_docs.append(order_doc)

            # Build a sales_record for confirmed/completed orders so the
            # cashflow side has matching revenue rows; this is what the
            # customer_metrics writer aggregates from.
            if status in ("confirmed", "completed"):
                for line in items:
                    sales_docs.append({
                        "id": _gen_id(),
                        "organization_id": org_id,
                        "dataset_id": None,
                        "customer_id": customer["id"],
                        "date": _date_iso(order_date),
                        "amount": line["line_total"],
                        "currency": "CHF",
                        "category": line["category"],
                        "description": line["product_name"],
                        "channel": "Storefront",
                        "payment_status": "paid" if status == "completed" else "pending",
                        "product_id": line["product_id"],
                        "source_label": SALES_SOURCE_LABEL,
                        "created_at": order_iso,
                        "updated_at": now_iso,
                    })

    if order_docs:
        # Chunk inserts to keep payload under Mongo's 16MB doc limit
        await orders_collection.insert_many(order_docs)
    if sales_docs:
        await sales_records_collection.insert_many(sales_docs)

    return len(order_docs), len(sales_docs)


async def trigger_refresh(org_id: str):
    """Re-compute customer_metrics so the AI tools + Insights page see
    the fresh data immediately."""
    from modules.customer_insights.refresh import refresh_customer_metrics
    return await refresh_customer_metrics(org_id)


async def report(org_id: str):
    from database import (
        stores_collection,
        products_collection,
        orders_collection,
        customers_collection,
        sales_records_collection,
        customer_metrics_collection,
    )
    print(f"\nFinal state for org={org_id}:")
    print(f"  Stores               {await stores_collection.count_documents({'organization_id': org_id})}")
    print(f"  Products             {await products_collection.count_documents({'organization_id': org_id})}")
    print(f"  Customers            {await customers_collection.count_documents({'organization_id': org_id})}")
    print(f"  Orders               {await orders_collection.count_documents({'organization_id': org_id})}")
    print(f"  Sales records        {await sales_records_collection.count_documents({'organization_id': org_id})}")
    print(f"  customer_metrics     {await customer_metrics_collection.count_documents({'organization_id': org_id})}")

    # Segment distribution
    seg_pipe = [
        {"$match": {"organization_id": org_id}},
        {"$group": {"_id": "$segment", "count": {"$sum": 1}}},
        {"$sort": {"_id": 1}},
    ]
    seg_cur = customer_metrics_collection.aggregate(seg_pipe)
    seg_rows = await seg_cur.to_list(20)
    if seg_rows:
        print("\nSegment distribution:")
        for r in seg_rows:
            print(f"  {r['_id']:12s} {r['count']}")

    # Order status mix
    st_pipe = [
        {"$match": {"organization_id": org_id}},
        {"$group": {"_id": "$status", "count": {"$sum": 1}, "value": {"$sum": "$total"}}},
        {"$sort": {"_id": 1}},
    ]
    st_cur = orders_collection.aggregate(st_pipe)
    st_rows = await st_cur.to_list(20)
    if st_rows:
        print("\nOrder status mix:")
        for r in st_rows:
            print(f"  {r['_id']:12s} {r['count']:3d}  CHF {r['value']:.2f}")


# ── Entry point ───────────────────────────────────────────────────────────


async def run(org_id: str):
    print("=" * 72)
    print(f"Wellness case study seed — org {org_id}")
    print("=" * 72)

    print("\n[1/6] Wiping existing org data…")
    wiped = await wipe_org_data(org_id)
    for k, v in wiped.items():
        if v > 0:
            print(f"      removed {k:20s} {v}")

    print("\n[2/6] Updating org settings (currency=CHF, name)…")
    await update_org(org_id)

    print("\n[3/6] Seeding store…")
    store = await seed_store(org_id)
    print(f"      ✓ {store['name']} ({store['slug']})")

    print("\n[4/6] Seeding products…")
    products = await seed_products(org_id, store["id"])
    print(f"      ✓ {len(products)} products")
    for p in products.values():
        print(f"        · {p['name']:42s} CHF {p['unit_price']:6.2f}  [{p['item_type']}]")

    print("\n[5/6] Seeding customers + orders + sales_records…")
    customers = await seed_customers(org_id)
    n_orders, n_sales = await seed_orders(org_id, store["id"], customers, products)
    print(f"      ✓ {len(customers)} customers")
    print(f"      ✓ {n_orders} orders")
    print(f"      ✓ {n_sales} sales_records")

    print("\n[6/6] Refreshing customer_metrics…")
    refreshed = await trigger_refresh(org_id)
    print(f"      ✓ {refreshed.get('message')}")

    await report(org_id)

    print("\n" + "=" * 72)
    print("✓ Wellness case study ready. Login as the org admin and visit:")
    print("  http://localhost:3000/modules/customers-light")
    print("  http://localhost:3000/orders")
    print("  http://localhost:3000/products")
    print("=" * 72)


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--org-id", default=DEFAULT_ORG_ID,
                        help=f"Target organisation id (default: {DEFAULT_ORG_ID})")
    parser.add_argument("--seed", type=int, default=42,
                        help="Random seed for reproducibility (default: 42)")
    args = parser.parse_args()
    random.seed(args.seed)
    asyncio.run(run(args.org_id))


if __name__ == "__main__":
    main()
