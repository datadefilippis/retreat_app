"""Demo seed for ``demo.afianco@gmail.com`` — business coach / formatore.

Creates a complete, realistic case-study account for screenshots and
live demos. Covers the widest set of features the platform exposes:

  · Org-level admin user with email_verified=True (no email click needed)
  · Modules activated: cashflow_monitor + commerce + customers_light
  · Public storefront with 9 products (1:1 services, group workshops,
    online courses, voucher)
  · 28 customer personas spread across tiers (top, active, occasional,
    inactive, new, one-shot, B2B)
  · ~140 orders over the last 7 months with realistic status/payment mix
  · Matching sales_records (so the cashflow Entrate table + KPI agree)
  · 70+ expenses (subscriptions, travel, marketing, contabile)
  · 30+ purchases (training materials, books, equipment)
  · 6 fixed costs (rent studio, accountant, CRM, hosting, leasing auto,
    abbonamento Notion+Slack)
  · customer_metrics recomputed at the end so the Insights page is hot

Idempotent
----------
Re-runs wipe ONLY docs tagged ``metadata.demo_seed = "coach_demo_v1"``
(or the equivalent ``source_label`` for cashflow records). Other orgs
in the same MongoDB are untouched.

Usage
-----
    cd backend
    set -a; source .env; set +a
    ./venv/bin/python -m scripts.seed_demo_coach_account

    # to reset password:
    ./venv/bin/python -m scripts.seed_demo_coach_account --reset-password

Login
-----
    URL: http://localhost:3000
    email: demo.afianco@gmail.com
    password: AfiancoDemo2026!
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


# ── Demo identity ────────────────────────────────────────────────────────

DEMO_EMAIL = "demo.afianco@gmail.com"
DEMO_PASSWORD = "AfiancoDemo2026!"
DEMO_OWNER_NAME = "Marco Conti"
DEMO_ORG_NAME = "Marco Conti — Business Coaching"
DEMO_INDUSTRY = "Coaching & Formazione"
DEMO_CURRENCY = "EUR"
DEMO_STORE_SLUG = "marco-conti-coaching"

SEED_TAG = "coach_demo_v1"
SALES_SOURCE_LABEL = "demo_seed_coach_v1"


# ── Catalog: 9 products covering every flow ──────────────────────────────

PRODUCTS = [
    # 1:1 services (service item_type — schedule-bound)
    {"key": "svc_1to1_60",      "slug": "sessione-1-1-coaching-60-min", "name": "Sessione 1:1 Coaching — 60 min",      "price": 120, "type": "service",      "category": "Coaching 1:1", "unit": "sessione", "duration": 60},
    {"key": "svc_1to1_90",      "slug": "sessione-1-1-coaching-90-min", "name": "Sessione 1:1 Coaching — 90 min",      "price": 170, "type": "service",      "category": "Coaching 1:1", "unit": "sessione", "duration": 90},
    {"key": "svc_assessment",   "slug": "assessment-iniziale",          "name": "Assessment iniziale + piano di sviluppo", "price": 200, "type": "service",  "category": "Coaching 1:1", "unit": "sessione", "duration": 120},

    # Group workshops (event_ticket — group sessions on a schedule)
    {"key": "evt_leadership",   "slug": "workshop-leadership-operativa", "name": "Workshop Leadership Operativa",       "price": 280, "type": "event_ticket", "category": "Workshop",     "unit": "posto"},
    {"key": "evt_speaking",     "slug": "workshop-public-speaking",      "name": "Workshop Public Speaking",            "price": 240, "type": "event_ticket", "category": "Workshop",     "unit": "posto"},
    {"key": "evt_mastermind",   "slug": "mastermind-mensile",            "name": "Mastermind mensile (10 imprenditori)", "price": 180, "type": "event_ticket", "category": "Workshop",     "unit": "mese"},

    # Digital / pre-paid (physical-mode for simple checkout, no slot)
    {"key": "phy_pack5",        "slug": "pacchetto-5-sessioni-1-1",      "name": "Pacchetto 5 sessioni 1:1",            "price": 550, "type": "physical",    "category": "Pacchetti",    "unit": "pacchetto"},
    {"key": "phy_corso_tm",     "slug": "corso-time-management",         "name": "Corso online: Time Management",        "price": 97,  "type": "physical",    "category": "Corsi online", "unit": "accesso"},
    {"key": "phy_corso_focus",  "slug": "mini-corso-giornata-produttiva", "name": "Mini-corso: La giornata produttiva",  "price": 37,  "type": "physical",    "category": "Corsi online", "unit": "accesso"},
]


# ── Product imagery (Unsplash CDN — free, no API key, stable URLs) ───────
# Each photo was hand-picked for semantic fit with the product and
# verified to return 200 from images.unsplash.com. Square-cropped
# 800×600 by default; the storefront landing page also uses a wider
# crop via _hero_image_url() below.
#
# Usage: ``product["image_url"]`` populates the catalog card hero,
# ``metadata.cover_image_url`` populates the dedicated landing page.

_UNSPLASH_BASE = "https://images.unsplash.com"
_CARD_PARAMS = "?w=800&h=600&fit=crop&q=80"
_HERO_PARAMS = "?w=1600&h=900&fit=crop&q=80"

IMAGE_URLS = {
    # 1:1 coaching — mentoring conversation
    "svc_1to1_60":     "photo-1573497491765-dccce02b29df",
    "svc_1to1_90":     "photo-1573164574572-cb89e39749b4",
    "svc_assessment":  "photo-1486312338219-ce68d2c6f44d",

    # Group workshops
    "evt_leadership":  "photo-1517048676732-d65bc937f952",
    "evt_speaking":    "photo-1551836022-d5d88e9218df",
    "evt_mastermind":  "photo-1556761175-5973dc0f32e7",

    # Pacchetti + corsi digitali
    "phy_pack5":       "photo-1505373877841-8d25f7d46678",
    "phy_corso_tm":    "photo-1454165804606-c3d57bc86b40",
    "phy_corso_focus": "photo-1499750310107-5fef28a66643",
}


def _card_image_url(key: str) -> str:
    return f"{_UNSPLASH_BASE}/{IMAGE_URLS[key]}{_CARD_PARAMS}"


def _hero_image_url(key: str) -> str:
    return f"{_UNSPLASH_BASE}/{IMAGE_URLS[key]}{_HERO_PARAMS}"


def _description_for(key: str) -> str:
    d = {
        "svc_1to1_60":      "Sessione individuale di coaching mirata su un obiettivo specifico. Confidenziale, online o in studio a Milano.",
        "svc_1to1_90":      "Sessione 1:1 estesa per chi ha bisogno di lavorare su più aree (leadership, gestione team, transizione di ruolo).",
        "svc_assessment":   "Prima sessione approfondita: questionario, mappatura competenze, definizione del piano di sviluppo 3-6 mesi.",
        "evt_leadership":   "Workshop intensivo di mezza giornata per manager e imprenditori. Massimo 12 partecipanti. Casi reali + simulazioni.",
        "evt_speaking":     "Workshop pratico sul public speaking. Tecniche di voce, postura, gestione dell'ansia. Massimo 10 partecipanti.",
        "evt_mastermind":   "Gruppo chiuso di 10 imprenditori che si incontra una volta al mese per 90 minuti. Peer-coaching strutturato.",
        "phy_pack5":        "Cinque sessioni 1:1 da 60 minuti prepagate. Validità 6 mesi. Ideale per percorsi su obiettivi a medio termine.",
        "phy_corso_tm":     "Corso online self-paced sul time management. 4 ore di video + workbook PDF + accesso a vita.",
        "phy_corso_focus":  "Mini-corso pratico (1 ora) sulle abitudini per una giornata produttiva. Ideale per iniziare.",
    }
    return d.get(key, "")


# ── Customer personas (28 — coach mix) ───────────────────────────────────

PERSONAS = [
    # ── TOP — high frequency, recent, varied product mix ─────────────────
    {"name": "Alessandro Pini",      "email": "a.pini@example.test",         "phone": "+39 333 111 22 01", "tier": "top",        "marketing": True},
    {"name": "Federica Romano",      "email": "federica.romano@example.test","phone": "+39 333 111 22 02", "tier": "top",        "marketing": True},
    {"name": "Stefano Bianchi",      "email": "stefano.b@example.test",      "phone": "+39 333 111 22 03", "tier": "top",        "marketing": True},

    # ── ACTIVE — recent, moderate frequency ──────────────────────────────
    {"name": "Giulia Marchetti",     "email": "giulia.marchetti@example.test","phone":"+39 333 222 33 04", "tier": "active",     "marketing": True},
    {"name": "Andrea Rossi",         "email": "andrea.rossi@example.test",   "phone": "+39 333 222 33 05", "tier": "active",     "marketing": True},
    {"name": "Chiara Conti",         "email": "chiara.conti@example.test",   "phone": "+39 333 222 33 06", "tier": "active",     "marketing": True},
    {"name": "Marco Esposito",       "email": "marco.e@example.test",        "phone": "+39 333 222 33 07", "tier": "active",     "marketing": False},
    {"name": "Sara Caputo",          "email": "sara.caputo@example.test",    "phone": "+39 333 222 33 08", "tier": "active",     "marketing": True},
    {"name": "Davide Greco",         "email": "davide.greco@example.test",   "phone": None,                "tier": "active",     "marketing": False},

    # ── OCCASIONAL — last visit 60-150 days ago ──────────────────────────
    {"name": "Luca Ferrari",         "email": "luca.ferrari@example.test",   "phone": "+39 333 333 44 09", "tier": "occasional", "marketing": True},
    {"name": "Valentina De Luca",    "email": "v.deluca@example.test",       "phone": "+39 333 333 44 10", "tier": "occasional", "marketing": False},
    {"name": "Roberto Costa",        "email": "r.costa@example.test",        "phone": None,                "tier": "occasional", "marketing": True},
    {"name": "Elena Galli",          "email": "elena.galli@example.test",    "phone": "+39 333 333 44 12", "tier": "occasional", "marketing": False},

    # ── INACTIVE — last visit > 200 days ─────────────────────────────────
    {"name": "Tommaso Riva",         "email": "tommaso.riva@example.test",   "phone": "+39 333 444 55 13", "tier": "inactive",   "marketing": False},
    {"name": "Francesca Mancini",    "email": "f.mancini@example.test",      "phone": None,                "tier": "inactive",   "marketing": False},
    {"name": "Paolo Serra",          "email": "paolo.serra@example.test",    "phone": "+39 333 444 55 15", "tier": "inactive",   "marketing": False},

    # ── NEW — first visit < 30 days ──────────────────────────────────────
    {"name": "Martina Vitali",       "email": "m.vitali@example.test",       "phone": "+39 333 555 66 16", "tier": "new",        "marketing": True},
    {"name": "Lorenzo Donati",       "email": "l.donati@example.test",       "phone": "+39 333 555 66 17", "tier": "new",        "marketing": True},
    {"name": "Anna Pellegrini",      "email": "anna.p@example.test",         "phone": None,                "tier": "new",        "marketing": False},

    # ── ONE-SHOT — single visit a while ago (at-risk signal) ────────────
    {"name": "Giorgio Bruno",        "email": "g.bruno@example.test",        "phone": "+39 333 666 77 19", "tier": "one_shot",   "marketing": False},
    {"name": "Silvia Carbone",       "email": "silvia.c@example.test",       "phone": "+39 333 666 77 20", "tier": "one_shot",   "marketing": True},

    # ── B2B — companies booking workshops + mastermind for execs ─────────
    {"name": "Tech4Growth SRL",      "email": "hr@tech4growth.test",         "phone": "+39 02 555 12 34",  "tier": "b2b",        "marketing": False},
    {"name": "Studio Architetti Verdi", "email": "info@studio-verdi.test",   "phone": "+39 02 555 23 45",  "tier": "b2b",        "marketing": True},
    {"name": "Acme Consulting Group", "email": "contact@acme-consulting.test", "phone": "+39 02 555 34 56", "tier": "b2b",       "marketing": False},
    {"name": "Innovate Hub SPA",     "email": "people@innovatehub.test",     "phone": "+39 02 555 45 67",  "tier": "b2b",        "marketing": True},

    # ── Extra ACTIVE for richer screenshots ──────────────────────────────
    {"name": "Riccardo Negri",       "email": "r.negri@example.test",        "phone": "+39 333 777 88 25", "tier": "active",     "marketing": True},
    {"name": "Elisa Fontana",        "email": "e.fontana@example.test",      "phone": "+39 333 777 88 26", "tier": "active",     "marketing": False},
    {"name": "Pietro Moretti",       "email": "p.moretti@example.test",      "phone": "+39 333 777 88 27", "tier": "occasional", "marketing": True},
]


TIER_PROFILES = {
    "top":        {"orders": (12, 20), "days": (3,  200), "mix": "varied"},
    "active":     {"orders": (5,  10), "days": (10, 180), "mix": "service_heavy"},
    "occasional": {"orders": (2,  4),  "days": (60, 150), "mix": "single_category"},
    "inactive":   {"orders": (1,  3),  "days": (220, 365), "mix": "single_category"},
    "new":        {"orders": (1,  2),  "days": (2,  25),  "mix": "trial"},
    "one_shot":   {"orders": (1,  1),  "days": (100, 180), "mix": "single"},
    "b2b":        {"orders": (2,  5),  "days": (15, 210), "mix": "workshop_bulk"},
}


# ── Helpers ──────────────────────────────────────────────────────────────


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _gen_id() -> str:
    return str(uuid.uuid4())


def _date_iso(d: datetime) -> str:
    return d.date().isoformat()


def _pick_product_for_mix(mix: str) -> dict:
    if mix == "single":
        return next(p for p in PRODUCTS if p["key"] == "svc_1to1_60")
    if mix == "single_category":
        return random.choice([p for p in PRODUCTS if p["category"] == "Coaching 1:1"])
    if mix == "trial":
        return random.choice([p for p in PRODUCTS if p["key"] in ("svc_assessment", "phy_corso_focus", "phy_corso_tm")])
    if mix == "workshop_bulk":
        return random.choice([p for p in PRODUCTS if p["key"] in ("evt_leadership", "evt_speaking", "phy_pack5")])
    if mix == "service_heavy":
        r = random.random()
        if r < 0.55:
            return random.choice([p for p in PRODUCTS if p["type"] == "service"])
        if r < 0.80:
            return random.choice([p for p in PRODUCTS if p["type"] == "event_ticket"])
        return random.choice([p for p in PRODUCTS if p["type"] == "physical"])
    # varied (top customers)
    weights = [30, 25, 12, 15, 12, 18, 10, 14, 10]
    return random.choices(PRODUCTS, weights=weights, k=1)[0]


def _pick_order_status(days_ago: int) -> tuple[str, str]:
    """Status + payment_status skewed by recency."""
    r = random.random()
    if days_ago < 7:
        if r < 0.35:
            return "draft", "pending"
        if r < 0.75:
            return "confirmed", "paid"
        if r < 0.92:
            return "completed", "paid"
        return "cancelled", "pending"
    if days_ago < 180:
        if r < 0.80:
            return "completed", "paid"
        if r < 0.92:
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


# ── User + Organization (idempotent ensure_*) ────────────────────────────


async def ensure_organization() -> dict:
    """Create or fetch the demo org by name. Returns the org doc."""
    from database import organizations_collection
    existing = await organizations_collection.find_one({"name": DEMO_ORG_NAME})
    if existing:
        # Refresh fields that may have drifted
        await organizations_collection.update_one(
            {"id": existing["id"]},
            {"$set": {
                "currency": DEMO_CURRENCY,
                "industry": DEMO_INDUSTRY,
                "is_active": True,
                "updated_at": _now_iso(),
            }},
        )
        return existing

    org_id = _gen_id()
    now_iso = _now_iso()
    doc = {
        "id": org_id,
        "name": DEMO_ORG_NAME,
        "industry": DEMO_INDUSTRY,
        "currency": DEMO_CURRENCY,
        "is_active": True,
        "created_at": now_iso,
        "updated_at": now_iso,
    }
    await organizations_collection.insert_one(doc)
    return doc


async def ensure_user(org_id: str, reset_password: bool = False) -> dict:
    """Create or update the demo owner. Returns the user doc.

    Always sets ``email_verified=True`` and ``accepted_terms_at=now`` so
    the account skips both the email-click and the legal-consent gates
    on login.
    """
    from database import users_collection
    from auth import get_password_hash

    now_iso = _now_iso()
    existing = await users_collection.find_one({"email": DEMO_EMAIL})

    if existing:
        update_fields = {
            "name": DEMO_OWNER_NAME,
            "organization_id": org_id,
            "role": "admin",
            "is_active": True,
            "email_verified": True,
            "must_change_password": False,
            "locale": "it",
            "accepted_terms_at": now_iso,
            "accepted_terms_locale": "it",
            # Best-effort current version marker — backfill default for
            # legacy users; lets the ReconsentModal stay dismissed.
            "accepted_terms_version": existing.get("accepted_terms_version") or "v0.demo:seeded",
            # Clear any verification / lockout artefacts from previous runs.
            "verification_token_hash": None,
            "verification_token_expires": None,
            "failed_login_attempts": 0,
            "locked_until": None,
            "lockout_count_today": 0,
            "updated_at": now_iso,
        }
        if reset_password:
            update_fields["password_hash"] = get_password_hash(DEMO_PASSWORD)
            update_fields["password_changed_at"] = now_iso
        await users_collection.update_one({"id": existing["id"]}, {"$set": update_fields})
        return {**existing, **update_fields}

    uid = _gen_id()
    doc = {
        "id": uid,
        "email": DEMO_EMAIL,
        "name": DEMO_OWNER_NAME,
        "role": "admin",
        "organization_id": org_id,
        "password_hash": get_password_hash(DEMO_PASSWORD),
        "is_active": True,
        "email_verified": True,
        "locale": "it",
        "must_change_password": False,
        "failed_login_attempts": 0,
        "locked_until": None,
        "lockout_count_today": 0,
        "last_failed_login_at": None,
        "accepted_terms_at": now_iso,
        "accepted_terms_locale": "it",
        "accepted_terms_version": "v0.demo:seeded",
        "verification_token_hash": None,
        "verification_token_expires": None,
        "created_at": now_iso,
        "updated_at": now_iso,
    }
    await users_collection.insert_one(doc)
    return doc


async def ensure_modules(org_id: str, admin_user_id: str):
    """Activate cashflow_monitor + commerce + customers_light idempotently."""
    from database import organization_modules_collection

    now_iso = _now_iso()
    for module_key in ("cashflow_monitor", "commerce", "customers_light"):
        existing = await organization_modules_collection.find_one({
            "organization_id": org_id,
            "module_key": module_key,
        })
        if existing:
            await organization_modules_collection.update_one(
                {"organization_id": org_id, "module_key": module_key},
                {"$set": {"is_active": True, "updated_at": now_iso}},
            )
            continue
        await organization_modules_collection.insert_one({
            "id": _gen_id(),
            "organization_id": org_id,
            "module_key": module_key,
            "is_active": True,
            "activated_by": admin_user_id,
            "activated_at": now_iso,
            "updated_at": now_iso,
        })


# ── Wipe phase ───────────────────────────────────────────────────────────


async def wipe_org_data(org_id: str) -> dict:
    """Hard wipe of every commerce + cashflow document for the demo org.

    Scope is intentionally aggressive on THIS ORG ID only — the demo
    seed is meant to be re-run from clean slates.
    """
    from database import (
        stores_collection,
        products_collection,
        orders_collection,
        customers_collection,
        sales_records_collection,
        expense_records_collection,
        purchase_records_collection,
        fixed_costs_collection,
        customer_metrics_collection,
    )

    try:
        from database import consent_audit_collection
    except ImportError:
        consent_audit_collection = None
    try:
        from database import product_metrics_collection
    except ImportError:
        product_metrics_collection = None
    try:
        from database import event_occurrences_collection
    except ImportError:
        event_occurrences_collection = None

    counts = {}
    for name, coll in [
        ("stores", stores_collection),
        ("products", products_collection),
        ("orders", orders_collection),
        ("customers", customers_collection),
        ("sales_records", sales_records_collection),
        ("expense_records", expense_records_collection),
        ("purchase_records", purchase_records_collection),
        ("fixed_costs", fixed_costs_collection),
        ("customer_metrics", customer_metrics_collection),
    ]:
        r = await coll.delete_many({"organization_id": org_id})
        counts[name] = r.deleted_count
    for name, coll in [
        ("consent_audit", consent_audit_collection),
        ("product_metrics", product_metrics_collection),
        ("event_occurrences", event_occurrences_collection),
    ]:
        if coll is None:
            counts[name] = 0
            continue
        r = await coll.delete_many({"organization_id": org_id})
        counts[name] = r.deleted_count
    return counts


# ── Store + products ─────────────────────────────────────────────────────


async def seed_store(org_id: str) -> dict:
    from database import stores_collection

    now_iso = _now_iso()
    store_id = _gen_id()
    doc = {
        "id": store_id,
        "organization_id": org_id,
        "slug": DEMO_STORE_SLUG,
        "name": DEMO_ORG_NAME,
        "description": (
            "Coaching e formazione per manager, imprenditori e team in crescita. "
            "Sessioni 1:1, workshop di gruppo, mastermind mensile e corsi online."
        ),
        "visibility": "public",
        # Service business + digital products → local_pickup (sessione in
        # studio o online) + shipping (per i corsi online lo si tratta
        # come un fulfillment "consegna accesso").
        "fulfillment_modes": ["local_pickup", "shipping"],
        "storefront_languages": ["it", "en"],
        "is_published": True,
        "is_default": True,
        "is_active": True,
        "brand_color": "#1F2A44",
        "brand_color_text": "#FFFFFF",
        "contact_email": DEMO_EMAIL,
        "contact_phone": "+39 02 555 99 88",
        "notification_email": DEMO_EMAIL,
        "reply_to_email": DEMO_EMAIL,
        "sender_display_name": DEMO_OWNER_NAME,
        "seo_title": "Marco Conti — Business Coaching & Formazione",
        "seo_description": "Coaching individuale e formazione per manager e imprenditori. Sessioni 1:1, workshop, mastermind mensile.",
        "metadata": {"demo_seed": SEED_TAG},
        "created_at": now_iso,
        "updated_at": now_iso,
    }
    await stores_collection.insert_one(doc)
    return doc


async def seed_products(org_id: str, store_id: str) -> dict[str, dict]:
    from database import products_collection

    now_iso = _now_iso()
    by_key: dict[str, dict] = {}

    for spec in PRODUCTS:
        pid = _gen_id()

        # Imagery — Unsplash CDN URLs (see IMAGE_URLS map at the top of
        # the file). Card uses 800×600 crop, landing-page hero uses
        # 1600×900 wide crop — same source photo, different sizes.
        card_image = _card_image_url(spec["key"])
        hero_image = _hero_image_url(spec["key"])

        meta: dict = {
            "demo_seed": SEED_TAG,
            # Surfaces on Product landing pages (see ProductLandingPage.js
            # line 389-391: hero = product.cover_image_url || product.image_url).
            "cover_image_url": hero_image,
        }
        if spec["type"] == "service" and spec.get("duration"):
            meta["duration_minutes"] = spec["duration"]
            meta["use_default_schedule"] = True

        doc = {
            "id": pid,
            "organization_id": org_id,
            "store_ids": [store_id],
            "slug": spec["slug"],
            "name": spec["name"],
            "sku": spec["key"].upper(),
            "category": spec["category"],
            "unit_price": spec["price"],
            "currency": DEMO_CURRENCY,
            "cost_price": round(spec["price"] * 0.25, 2),
            "unit": spec["unit"],
            "description": _description_for(spec["key"]),
            # Card hero on the storefront grid — see
            # frontend/.../CommerceCardVariants.js heroSrc = product.image_url.
            "image_url": card_image,
            "is_published": True,
            "is_active": True,
            "item_type": spec["type"],
            "unit_label": spec["unit"],
            "price_mode": "fixed",
            "transaction_mode": "direct",
            "stock_quantity": None,
            "tags": [spec["category"].lower().replace(" ", "_")],
            "metadata": meta,
            "created_at": now_iso,
            "updated_at": now_iso,
        }
        await products_collection.insert_one(doc)
        by_key[spec["key"]] = doc

    return by_key


# ── Customers ────────────────────────────────────────────────────────────


async def seed_customers(org_id: str) -> list[dict]:
    from database import customers_collection
    try:
        from database import consent_audit_collection
    except ImportError:
        consent_audit_collection = None

    now_dt = datetime.now(timezone.utc)
    now_iso = now_dt.isoformat()
    docs = []
    consent_docs = []

    for p in PERSONAS:
        cid = _gen_id()
        opted_at = (now_dt - timedelta(days=random.randint(20, 180))).isoformat() if p["marketing"] else None

        customer_doc = {
            "id": cid,
            "organization_id": org_id,
            "name": p["name"],
            "email": p["email"],
            "phone": p["phone"],
            "tags": [p["tier"]],
            "is_active": True,
            # Marketing opt-in fields (most-recent-wins semantics — see
            # backend/services/marketing.py).
            "accepted_marketing_at": opted_at,
            "marketing_revoked_at": None,
            "metadata": {"demo_seed": SEED_TAG, "tier": p["tier"]},
            "created_at": (now_dt - timedelta(days=random.randint(30, 365))).isoformat(),
            "updated_at": now_iso,
        }
        docs.append(customer_doc)

        # Immutable consent_audit record for marketing opt-in (CRM legal
        # proof — Wave GDPR-Commerce CG-3). One row per opt-in event.
        if opted_at and consent_audit_collection is not None:
            consent_docs.append({
                "id": _gen_id(),
                "organization_id": org_id,
                "customer_id": cid,
                "customer_email": p["email"],
                "event_type": "marketing_opt_in",
                "source": "demo_seed",
                "ip_address": "127.0.0.1",
                "user_agent": "DemoSeed/1.0",
                "occurred_at": opted_at,
                "metadata": {"demo_seed": SEED_TAG},
            })

    if docs:
        await customers_collection.insert_many(docs)
    if consent_docs and consent_audit_collection is not None:
        await consent_audit_collection.insert_many(consent_docs)

    return docs


# ── Orders + sales_records (commerce side) ───────────────────────────────


async def seed_orders(
    org_id: str,
    store_id: str,
    customers: list[dict],
    products: dict[str, dict],
) -> tuple[int, int]:
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

            # Most orders 1 item; B2B and top sometimes 2 items.
            n_items = 2 if (tier == "b2b" or random.random() < 0.18) else 1
            items = []
            order_total = 0.0
            for _ in range(n_items):
                prod_spec = _pick_product_for_mix(prof["mix"])
                product = products[prod_spec["key"]]
                qty = (
                    random.randint(3, 8) if (tier == "b2b" and prod_spec["key"].startswith("evt_"))
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
                if product["item_type"] == "service":
                    slot_date = order_date + timedelta(days=random.choice([1, 2, 3, 5, 7, 10]))
                    line["booking_date"] = _date_iso(slot_date)
                    line["booking_start_time"] = random.choice(["09:00", "10:30", "14:00", "15:30", "17:00", "18:30"])
                    line["booking_end_time"] = random.choice(["10:00", "11:30", "15:00", "16:30", "18:00", "19:30"])
                elif product["item_type"] == "event_ticket":
                    line["occurrence_id"] = f"occ_{_gen_id()[:12]}"
                    occ_dt = (order_date + timedelta(days=random.choice([7, 14, 21, 28]))).replace(
                        hour=18, minute=0, second=0, microsecond=0,
                    )
                    line["occurrence_start_at"] = occ_dt.isoformat()
                    line["occurrence_location"] = "Studio Marco Conti, Milano — Via Solferino 12" if random.random() < 0.7 else "Online (Zoom)"
                items.append(line)

            order_id = _gen_id()
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
                "currency": DEMO_CURRENCY,
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

            if status in ("confirmed", "completed"):
                for line in items:
                    sales_docs.append({
                        "id": _gen_id(),
                        "organization_id": org_id,
                        "dataset_id": None,
                        "customer_id": customer["id"],
                        "date": _date_iso(order_date),
                        "amount": line["line_total"],
                        "currency": DEMO_CURRENCY,
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
        await orders_collection.insert_many(order_docs)
    if sales_docs:
        await sales_records_collection.insert_many(sales_docs)

    return len(order_docs), len(sales_docs)


# ── Cashflow: expenses, purchases, fixed_costs (out side) ────────────────

EXPENSE_TEMPLATES = [
    # (category, supplier, amount_min, amount_max, freq_per_month)
    ("Marketing",   "Meta Ads",                40, 320,  2.5),
    ("Marketing",   "Google Ads",              60, 280,  2.0),
    ("Marketing",   "LinkedIn Ads",            45, 210,  1.3),
    ("Trasporti",   "Trenitalia",              25,  90,  3.5),
    ("Trasporti",   "Uber Italia",             12,  45,  4.0),
    ("Software",    "Notion",                  10,  16,  1.0),
    ("Software",    "Calendly",                12,  16,  1.0),
    ("Software",    "Zoom Pro",                14,  20,  1.0),
    ("Ristorazione", "Pranzo cliente — Camparino", 35,  120, 1.2),
    ("Ristorazione", "Pranzo cliente — Trattoria Milanese", 28,  95,  1.0),
    ("Formazione",  "Audible",                 12,  16,  1.0),
    ("Formazione",  "Coursera Plus",           45,  50,  0.3),
    ("Spese bancarie", "Banca Sella",          10,  35,  1.0),
    ("Cancelleria", "Mondadori Store",         18,  85,  0.8),
]

PURCHASE_TEMPLATES = [
    # (supplier_name, product_desc, category, unit_price_min, unit_price_max, qty_max)
    ("Amazon Business",   "Libro: Atomic Habits",                    "Libri",       18, 24,  2),
    ("Amazon Business",   "Libro: Drive (Daniel Pink)",              "Libri",       15, 20,  1),
    ("Amazon Business",   "Libro: The Coaching Habit",               "Libri",       14, 18,  2),
    ("Amazon Business",   "Set lavagne Post-it XL (6 pz)",           "Materiale",   42, 48,  2),
    ("Amazon Business",   "Pennarelli Stabilo Boss assortiti",       "Materiale",    9, 14,  3),
    ("Apple Store",       "iPad Pro 11\" 256GB",                     "Attrezzatura", 1199, 1199, 1),
    ("Apple Store",       "Apple Pencil 2",                          "Attrezzatura", 135, 135, 1),
    ("Logitech Store",    "Webcam Brio 4K",                          "Attrezzatura", 199, 199, 1),
    ("Rode IT",           "Microfono Podcaster",                     "Attrezzatura", 219, 245, 1),
    ("Materiale didattico Editore Hoepli", "Workbook stampati — 100 pz",  "Materiale",  3,  4, 100),
    ("Vistaprint",        "Biglietti da visita — 250 pz",            "Materiale",   42,  68, 1),
    ("Vistaprint",        "Flyer A5 workshop — 100 pz",              "Marketing",   38,  62, 1),
]

FIXED_COSTS = [
    {"name": "Affitto studio Milano",         "category": "affitto",        "amount": 1200, "frequency": "mensile"},
    {"name": "Commercialista (Studio Bianchi)", "category": "altro",        "amount": 380,  "frequency": "mensile"},
    {"name": "Software CRM (HubSpot Starter)", "category": "abbonamento",   "amount": 45,   "frequency": "mensile"},
    {"name": "Hosting + dominio sito web",     "category": "abbonamento",   "amount": 18,   "frequency": "mensile"},
    {"name": "Leasing auto (Volvo XC40)",      "category": "leasing",       "amount": 520,  "frequency": "mensile"},
    {"name": "Abbonamento Notion + Slack",     "category": "abbonamento",   "amount": 32,   "frequency": "mensile"},
]


# ── Historical baseline ────────────────────────────────────────────────────
# Months 8-26 ago carry a thin layer of sales_records + expense_records +
# purchase_records (NO orders, NO fake customers) so the cashflow aggregates
# have continuity all the way back to ~2 years.
#
# Why this matters for the health score:
#   - Dim 2 "Dinamica Ricavi" computes sales_trend_pct = (now / prev) — 1
#     and margin_trend_pp = current_margin% - prev_margin%. For a 12m
#     period selection the prev window is months 13-24, for YTD it's
#     last year's YTD window, for 1y it's months 13-24.
#   - Dim 3 "Resilienza Strutturale" needs fixed_costs_total active in
#     the selected period — fixed costs now start 26 months ago.
#   - YoY (overview_builder lines 130-241) compares "same period last
#     year" — without history, all YoY widgets show "n/a".
#
# Volume is modest (8-12 sales / month, ~14 expenses, ~3 purchases)
# because the persona-driven months 0-7 already carry the bulk of the
# narrative; the baseline is just to ensure prev-period aggregates
# never come back empty.

HISTORICAL_MONTHS_BACK = 26   # how far back the baseline goes (must be ≥ 24 to cover 1y prev window + YoY)
HISTORICAL_START_MONTH = 7    # baseline picks up where the persona-driven data ends

# Monthly volume bands for the historical baseline.
HIST_SALES_PER_MONTH = (8, 14)         # n_records per month
HIST_EXPENSES_PER_MONTH = (12, 18)
HIST_PURCHASES_PER_MONTH = (3, 6)

# Categories the historical baseline uses (kept consistent with the
# persona-driven catalog so the cashflow categories chart looks coherent
# across the full 24-month window).
HIST_SALES_CATEGORIES = [
    ("Coaching 1:1",   "Sessione 1:1 (storico)",         (90, 180)),
    ("Workshop",       "Workshop di gruppo (storico)",    (180, 320)),
    ("Pacchetti",      "Pacchetto sessioni (storico)",    (500, 700)),
    ("Corsi online",   "Corso online (storico)",          (37, 120)),
]
HIST_EXPENSE_CATEGORIES = [
    ("Marketing",      "Meta Ads",                        (40, 280)),
    ("Marketing",      "Google Ads",                      (60, 240)),
    ("Trasporti",      "Trenitalia",                      (25,  85)),
    ("Trasporti",      "Uber Italia",                     (12,  40)),
    ("Software",       "Zoom Pro",                        (14,  18)),
    ("Software",       "Notion",                          (10,  14)),
    ("Ristorazione",   "Pranzo cliente",                  (28, 110)),
    ("Spese bancarie", "Banca Sella",                     (10,  35)),
    ("Cancelleria",    "Mondadori Store",                 (18,  85)),
    ("Formazione",     "Audible",                         (12,  16)),
]
HIST_PURCHASE_TEMPLATES = [
    ("Amazon Business", "Libri di management (storico)",   "Libri",       18, 24,  3),
    ("Amazon Business", "Materiale workshop (storico)",    "Materiale",    9, 50,  4),
    ("Vistaprint",      "Stampa materiali (storico)",      "Marketing",   30, 80,  1),
]


async def seed_expenses(org_id: str) -> int:
    from repositories import expenses_repository

    now_dt = datetime.now(timezone.utc)
    now_iso = now_dt.isoformat()
    docs = []

    # Generate ~7 months of expenses
    for month_offset in range(7):
        for tmpl in EXPENSE_TEMPLATES:
            category, supplier, amin, amax, freq = tmpl
            n = max(1, int(round(freq + random.uniform(-0.5, 0.5))))
            for _ in range(n):
                day_offset = month_offset * 30 + random.randint(0, 28)
                date = now_dt - timedelta(days=day_offset)
                docs.append({
                    "id": _gen_id(),
                    "organization_id": org_id,
                    "dataset_id": "manual",
                    "date": _date_iso(date),
                    "amount": round(random.uniform(amin, amax), 2),
                    "category": category,
                    "description": f"{supplier} — {date.strftime('%Y-%m')}",
                    "supplier": supplier,
                    "source_label": SALES_SOURCE_LABEL,
                    "created_at": date.isoformat(),
                    "updated_at": now_iso,
                })

    if docs:
        await expenses_repository.insert_many(docs)
    return len(docs)


async def seed_purchases(org_id: str) -> int:
    from repositories import purchase_repository

    now_dt = datetime.now(timezone.utc)
    now_iso = now_dt.isoformat()
    docs = []

    # ~30-40 purchases over 7 months
    for month_offset in range(7):
        n_in_month = random.randint(3, 6)
        chosen = random.sample(PURCHASE_TEMPLATES, k=min(n_in_month, len(PURCHASE_TEMPLATES)))
        for tmpl in chosen:
            supplier, desc, category, pmin, pmax, qty_max = tmpl
            day_offset = month_offset * 30 + random.randint(0, 28)
            date = now_dt - timedelta(days=day_offset)
            quantity = 1 if qty_max == 1 else random.randint(1, qty_max)
            unit_price = round(random.uniform(pmin, pmax), 2)
            total_price = round(quantity * unit_price, 2)
            iva = random.choice([22, 22, 22, 10, 4])  # 22% most common
            total_with_iva = round(total_price * (1 + iva / 100), 2)
            docs.append({
                "id": _gen_id(),
                "organization_id": org_id,
                "dataset_id": "manual",
                "date": _date_iso(date),
                "supplier_name": supplier,
                "supplier_id": None,
                "product_id": None,
                "quantity": quantity,
                "unit": "pezzo" if category in ("Libri", "Attrezzatura", "Marketing") else "unità",
                "unit_price": unit_price,
                "total_price": total_price,
                "iva": iva,
                "total_with_iva": total_with_iva,
                "category": desc.split(" — ")[0][:32],
                "category_macro": category,
                "description": desc,
                "invoice_number": f"FT-{date.year}-{random.randint(100, 9999):04d}",
                "due_date": _date_iso(date + timedelta(days=30)),
                "payment_status": random.choices(["paid", "pending"], weights=[85, 15])[0],
                "source_label": SALES_SOURCE_LABEL,
                "created_at": date.isoformat(),
                "updated_at": now_iso,
            })

    if docs:
        await purchase_repository.insert_many(docs)
    return len(docs)


async def seed_fixed_costs(org_id: str) -> int:
    from repositories import fixed_cost_repository

    now_dt = datetime.now(timezone.utc)
    now_iso = now_dt.isoformat()
    docs = []
    # Start ~26 months back so the health score's "Resilienza
    # Strutturale" (which proratizza fixed_costs over the selected
    # period) has values even for 1y / YTD / YoY windows. The
    # aggregate_fixed_costs_total query uses an effective-date
    # overlap check, so a start in the distant past is harmless for
    # short windows but unlocks long-window aggregates.
    start = now_dt - timedelta(days=HISTORICAL_MONTHS_BACK * 31)
    for fc in FIXED_COSTS:
        docs.append({
            "id": _gen_id(),
            "organization_id": org_id,
            "dataset_id": "manual",
            "name": fc["name"],
            "category": fc["category"],
            "amount": fc["amount"],
            "frequency": fc["frequency"],
            "start_date": _date_iso(start),
            "end_date": None,
            "is_active": True,
            "source_label": SALES_SOURCE_LABEL,
            "created_at": now_iso,
            "updated_at": now_iso,
        })

    if docs:
        await fixed_cost_repository.insert_many(docs)
    return len(docs)


# ── Recent-activity floor (guarantees the 7d window is non-empty) ───────


async def ensure_recent_activity(org_id: str) -> int:
    """Make sure the LAST 7 DAYS have at least 5 sales records.

    Without this, the persona-driven random generator can land zero
    sales in the most recent week — leaving the 7d health score with
    ``net_margin`` and ``structural_strength`` not computable (both
    require ``total_sales > 0``). The seed script aims to make EVERY
    period selection show a complete score, so we top-up here when
    needed.

    Records are tagged with ``source_label=demo_seed_coach_recent`` so
    they're wiped + re-created on the next seed run.
    """
    from database import sales_records_collection
    from repositories import sales_repository

    now_dt = datetime.now(timezone.utc)
    now_iso = now_dt.isoformat()
    seven_days_ago = (now_dt - timedelta(days=7)).date().isoformat()

    existing = await sales_records_collection.count_documents({
        "organization_id": org_id,
        "date": {"$gte": seven_days_ago},
    })

    target = 5
    if existing >= target:
        return 0

    n_to_add = target - existing
    docs = []
    for i in range(n_to_add):
        # Spread across the last 5 days (0..4 ago), bias to weekdays.
        d_ago = (i * 1 + 1) % 5
        sale_dt = (now_dt - timedelta(days=d_ago)).replace(
            hour=10 + (i % 6), minute=0, second=0, microsecond=0,
        )
        cat, label, (amin, amax) = random.choice(HIST_SALES_CATEGORIES)
        docs.append({
            "id": _gen_id(),
            "organization_id": org_id,
            "dataset_id": None,
            "customer_id": None,
            "date": _date_iso(sale_dt),
            "amount": round(random.uniform(amin, amax), 2),
            "currency": DEMO_CURRENCY,
            "category": cat,
            "description": f"{label} (settimana corrente)",
            "channel": "Storefront",
            "payment_status": "paid",
            "product_id": None,
            "source_label": f"{SALES_SOURCE_LABEL}_recent",
            "created_at": sale_dt.isoformat(),
            "updated_at": now_iso,
        })

    if docs:
        await sales_repository.insert_many(docs)
    return len(docs)


# ── Historical baseline (24+ months back) ────────────────────────────────


async def seed_historical_data(org_id: str) -> dict:
    """Seed a lightweight 8-26 month backlog of sales / expense / purchase
    records so all health-score dimensions stay computable for every
    period the cashflow page exposes (7d / 30d / 90d / 1y / YTD / MTD /
    QTD + custom).

    No orders + no fake customers — just raw rows in the three cashflow
    collections, tagged with ``source_label = "demo_seed_coach_historical"``
    so they're separable from the persona-driven data on re-runs.

    Why no orders here: the orders table is meant for managing recent
    open work; back-dating 18 months of fake orders would mess up
    customer_metrics (LTV, recency) and the Insights segmentation.
    The cashflow aggregates read the three records collections directly,
    which is exactly what the health score uses.
    """
    from repositories import (
        sales_repository,
        expenses_repository,
        purchase_repository,
    )

    now_dt = datetime.now(timezone.utc)
    now_iso = now_dt.isoformat()
    historical_tag = f"{SALES_SOURCE_LABEL}_historical"

    sales_docs = []
    expense_docs = []
    purchase_docs = []

    # Iterate from month 7 (where persona data thins out) to month 26 ago.
    for month_offset in range(HISTORICAL_START_MONTH, HISTORICAL_MONTHS_BACK + 1):
        # Seasonal modulation: Aug-Dec slightly higher, Jul-Aug lower
        # for an Italian coach (summer = slowdown, autumn = peak).
        # Compute the calendar month being seeded.
        bucket_dt = now_dt - timedelta(days=month_offset * 30)
        cal_month = bucket_dt.month
        if cal_month in (7, 8):
            volume_factor = 0.6
        elif cal_month in (10, 11):
            volume_factor = 1.25
        elif cal_month in (1, 12):
            volume_factor = 0.85
        else:
            volume_factor = 1.0

        # ── Sales ──────────────────────────────────────────────────────────
        n_sales = max(3, int(round(random.uniform(*HIST_SALES_PER_MONTH) * volume_factor)))
        for _ in range(n_sales):
            day_in_month = random.randint(1, 28)
            sale_dt = bucket_dt.replace(day=day_in_month, hour=12, minute=0, second=0, microsecond=0)
            cat, label, (amin, amax) = random.choice(HIST_SALES_CATEGORIES)
            amount = round(random.uniform(amin, amax), 2)
            sales_docs.append({
                "id": _gen_id(),
                "organization_id": org_id,
                "dataset_id": None,
                "customer_id": None,
                "date": _date_iso(sale_dt),
                "amount": amount,
                "currency": DEMO_CURRENCY,
                "category": cat,
                "description": label,
                "channel": "Storico",
                # 92% paid (historical data is typically settled by now)
                "payment_status": random.choices(["paid", "overdue"], weights=[92, 8])[0],
                "product_id": None,
                "source_label": historical_tag,
                "created_at": sale_dt.isoformat(),
                "updated_at": now_iso,
            })

        # ── Expenses ───────────────────────────────────────────────────────
        n_exp = max(5, int(round(random.uniform(*HIST_EXPENSES_PER_MONTH) * volume_factor)))
        for _ in range(n_exp):
            day_in_month = random.randint(1, 28)
            exp_dt = bucket_dt.replace(day=day_in_month, hour=10, minute=0, second=0, microsecond=0)
            cat, supplier, (amin, amax) = random.choice(HIST_EXPENSE_CATEGORIES)
            expense_docs.append({
                "id": _gen_id(),
                "organization_id": org_id,
                "dataset_id": "manual",
                "date": _date_iso(exp_dt),
                "amount": round(random.uniform(amin, amax), 2),
                "category": cat,
                "description": f"{supplier} — {exp_dt.strftime('%Y-%m')}",
                "supplier": supplier,
                "source_label": historical_tag,
                "created_at": exp_dt.isoformat(),
                "updated_at": now_iso,
            })

        # ── Purchases ──────────────────────────────────────────────────────
        n_pur = max(1, int(round(random.uniform(*HIST_PURCHASES_PER_MONTH) * volume_factor)))
        for _ in range(n_pur):
            tmpl = random.choice(HIST_PURCHASE_TEMPLATES)
            supplier, desc, category, pmin, pmax, qty_max = tmpl
            day_in_month = random.randint(1, 28)
            pur_dt = bucket_dt.replace(day=day_in_month, hour=11, minute=0, second=0, microsecond=0)
            quantity = 1 if qty_max == 1 else random.randint(1, qty_max)
            unit_price = round(random.uniform(pmin, pmax), 2)
            total_price = round(quantity * unit_price, 2)
            iva = random.choice([22, 22, 22, 10])
            total_with_iva = round(total_price * (1 + iva / 100), 2)
            purchase_docs.append({
                "id": _gen_id(),
                "organization_id": org_id,
                "dataset_id": "manual",
                "date": _date_iso(pur_dt),
                "supplier_name": supplier,
                "supplier_id": None,
                "product_id": None,
                "quantity": quantity,
                "unit": "pezzo",
                "unit_price": unit_price,
                "total_price": total_price,
                "iva": iva,
                "total_with_iva": total_with_iva,
                "category": desc.split(" — ")[0][:32],
                "category_macro": category,
                "description": desc,
                "invoice_number": f"FT-{pur_dt.year}-{random.randint(100, 9999):04d}",
                "due_date": _date_iso(pur_dt + timedelta(days=30)),
                # Historical → all paid by now
                "payment_status": "paid",
                "source_label": historical_tag,
                "created_at": pur_dt.isoformat(),
                "updated_at": now_iso,
            })

    if sales_docs:
        await sales_repository.insert_many(sales_docs)
    if expense_docs:
        await expenses_repository.insert_many(expense_docs)
    if purchase_docs:
        await purchase_repository.insert_many(purchase_docs)

    return {
        "historical_sales":     len(sales_docs),
        "historical_expenses":  len(expense_docs),
        "historical_purchases": len(purchase_docs),
        "months_covered":       HISTORICAL_MONTHS_BACK - HISTORICAL_START_MONTH + 1,
    }


# ── Customer metrics refresh ─────────────────────────────────────────────


async def trigger_metrics_refresh(org_id: str) -> dict:
    try:
        from modules.customer_insights.refresh import refresh_customer_metrics
        return await refresh_customer_metrics(org_id)
    except Exception as exc:
        return {"message": f"refresh skipped: {exc!r}"}


# ── Report ───────────────────────────────────────────────────────────────


async def report(org_id: str, user: dict):
    from database import (
        organizations_collection,
        stores_collection,
        products_collection,
        orders_collection,
        customers_collection,
        sales_records_collection,
        expense_records_collection,
        purchase_records_collection,
        fixed_costs_collection,
        customer_metrics_collection,
    )

    org = await organizations_collection.find_one({"id": org_id})

    def count(coll):
        return coll.count_documents({"organization_id": org_id})

    counts = {
        "stores":           await count(stores_collection),
        "products":         await count(products_collection),
        "customers":        await count(customers_collection),
        "orders":           await count(orders_collection),
        "sales_records":    await count(sales_records_collection),
        "expense_records":  await count(expense_records_collection),
        "purchase_records": await count(purchase_records_collection),
        "fixed_costs":      await count(fixed_costs_collection),
        "customer_metrics": await count(customer_metrics_collection),
    }

    bar = "=" * 72
    print()
    print(bar)
    print(f"  DEMO ACCOUNT READY — {DEMO_ORG_NAME}")
    print(bar)
    print(f"  Login email:    {DEMO_EMAIL}")
    print(f"  Password:       {DEMO_PASSWORD}")
    print(f"  Role:           admin (org owner)")
    print(f"  Email verified: ✓ (no email click needed)")
    print(f"  Org id:         {org_id}")
    print(f"  Org currency:   {org.get('currency')}")
    print()
    print(f"  → Frontend:     http://localhost:3000")
    print(f"  → Storefront:   http://localhost:3000/s/{DEMO_STORE_SLUG}")
    print()
    print("  Data populated:")
    for k, v in counts.items():
        print(f"    {k:20s} {v}")
    print(bar)


# ── Entry point ──────────────────────────────────────────────────────────


async def run(reset_password: bool):
    print("=" * 72)
    print(f"DEMO coach/formatore seed — {DEMO_EMAIL}")
    print("=" * 72)

    print("\n[1/8] Ensuring organization…")
    org = await ensure_organization()
    org_id = org["id"]
    print(f"      ✓ {org['name']} ({org_id})")

    print("\n[2/8] Ensuring owner user (email_verified=True)…")
    user = await ensure_user(org_id, reset_password=reset_password)
    print(f"      ✓ {user['email']} role={user.get('role')} verified={user.get('email_verified')}")

    print("\n[3/8] Activating modules…")
    await ensure_modules(org_id, user["id"])
    print("      ✓ cashflow_monitor + commerce + customers_light")

    print("\n[4/8] Wiping previous demo data for this org…")
    wiped = await wipe_org_data(org_id)
    for k, v in wiped.items():
        if v > 0:
            print(f"      removed {k:20s} {v}")

    print("\n[5/8] Seeding store + products…")
    store = await seed_store(org_id)
    products = await seed_products(org_id, store["id"])
    print(f"      ✓ store '{store['slug']}' + {len(products)} products")

    print("\n[6/8] Seeding customers + orders + sales_records…")
    customers = await seed_customers(org_id)
    n_orders, n_sales = await seed_orders(org_id, store["id"], customers, products)
    print(f"      ✓ {len(customers)} customers, {n_orders} orders, {n_sales} sales_records")

    print("\n[7/9] Seeding cashflow OUT side (expenses + purchases + fixed_costs)…")
    n_exp = await seed_expenses(org_id)
    n_pur = await seed_purchases(org_id)
    n_fc  = await seed_fixed_costs(org_id)
    print(f"      ✓ {n_exp} expenses, {n_pur} purchases, {n_fc} fixed_costs")

    print("\n[8/9] Seeding historical baseline (months 8-26 ago)…")
    print("      (so Dinamica Ricavi / YoY / 1y / YTD always have prev-period data)")
    hist = await seed_historical_data(org_id)
    print(f"      ✓ {hist['historical_sales']} historical sales")
    print(f"      ✓ {hist['historical_expenses']} historical expenses")
    print(f"      ✓ {hist['historical_purchases']} historical purchases")
    print(f"      ✓ {hist['months_covered']} months of backlog covered")

    print("\n      Ensuring last-7-days has ≥5 sales (so 7d health score is complete)…")
    topped_up = await ensure_recent_activity(org_id)
    if topped_up:
        print(f"      ✓ added {topped_up} recent sales to fill the 7d window")
    else:
        print("      ✓ last 7 days already populated")

    print("\n[9/9] Refreshing customer_metrics…")
    refreshed = await trigger_metrics_refresh(org_id)
    print(f"      ✓ {refreshed.get('message', 'done')}")

    await report(org_id, user)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--reset-password",
        action="store_true",
        help="Reset the password to the canonical demo password.",
    )
    args = parser.parse_args()

    asyncio.run(run(reset_password=args.reset_password))


if __name__ == "__main__":
    main()
