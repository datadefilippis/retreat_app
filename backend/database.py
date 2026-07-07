from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv
from pathlib import Path
import os

ROOT_DIR = Path(__file__).parent
# override=False: l'ambiente della shell/container vince sul file .env
# (12-factor; allineato a server.py). Con override=True un .env con valori
# vuoti azzerava le variabili passate da shell/CI — bug ereditato dal fork.
load_dotenv(ROOT_DIR / '.env', override=False)

# MongoDB connection
mongo_url = os.environ['MONGO_URL']

# Wave 3.6 (2026-05) — connection pool tuning for 150-user target.
#
# Default motor maxPoolSize is 100. At ~25 concurrent chats × multiple
# parallel tool calls (each tool fans out to 3-5 aggregations) we can
# hit the pool ceiling and the loop starts waiting for a free
# connection — silent latency spike from the merchant's POV.
#
# Raising to 200 doubles headroom without a meaningful memory cost
# (each connection is ~70KB). MONGO_POOL_SIZE env lets the system
# admin tune higher (e.g. 400 for the 300-user tier) without a
# code change. minPoolSize=10 keeps idle connections warm so the
# first request after a quiet period doesn't pay the handshake.
_pool_size = int(os.environ.get("MONGO_POOL_SIZE", "200"))
_min_pool_size = int(os.environ.get("MONGO_MIN_POOL_SIZE", "10"))
client = AsyncIOMotorClient(
    mongo_url,
    maxPoolSize=_pool_size,
    minPoolSize=_min_pool_size,
    serverSelectionTimeoutMS=5000,  # fail fast if Mongo is unreachable
)
db = client[os.environ['DB_NAME']]

# ── Legacy collections (do not rename – referenced by existing code) ──────────
organizations_collection = db.organizations
users_collection = db.users
datasets_collection = db.datasets
sales_records_collection = db.sales_records
expense_records_collection = db.expense_records
organization_modules_collection = db.organization_modules
alerts_collection = db.alerts
insights_collection = db.insights
audit_logs_collection = db.audit_logs
# Wave GDPR-Admin Phase B — immutable consent audit trail.
# One record per acceptance of Privacy Policy + T&C (at signup,
# re-acceptance after policy update, etc.). Append-only by contract.
# See repositories/consent_audit_repository.py for the API.
consent_audit_collection = db.consent_audit
# ── Phase-1 new collections (additive, zero breaking change) ──────────────────
# Canonical business entities
customers_collection = db.customers
suppliers_collection = db.suppliers
products_collection = db.products

# Financial transaction types not yet modelled
purchase_records_collection = db.purchase_records
fixed_costs_collection = db.fixed_costs

# Phase 0 Step 4 (2026-05-28) — Server-side persistent shopping cart.
# Bound to (organization_id, store_id) with 60-day TTL.
# See models/cart.py + repositories/cart_repository.py.
# Cookie ``afianco_cart_id`` carries the id across requests.
carts_collection = db.carts

# Phase 0 Step 8 (2026-05-28) — Idempotency keys cache for /embed/* + /ai-site/*
# Stores idempotency response cache keyed by (key, org_id) with TTL 24h.
# Mongo TTL index on expires_at fa cleanup automatico.
idempotency_keys_collection = db.idempotency_keys

# Dataset intelligence
column_mappings_collection = db.column_mappings
dataset_column_profiles_collection = db.dataset_column_profiles
data_validation_rules_collection = db.data_validation_rules

# Pre-computed KPI layer
kpi_snapshots_collection = db.kpi_snapshots

# Per-module configuration (separate from activation state in organization_modules)
module_configs_collection = db.module_configs

# Temporary upload staging (for interactive column mapping; auto-expires via TTL)
temp_uploads_collection = db.temp_uploads

# Customers Light — computed per-customer intelligence (materialized analytics)
customer_metrics_collection = db.customer_metrics

# Product Catalog — computed per-product intelligence (materialized analytics)
product_metrics_collection = db.product_metrics

# ── Product Cost History (Wave 1, W1.S1) ──────────────────────────────────────
# Append-only periodic snapshots of each product's computed unit cost.
# Powers the trend chart in the product detail drill-down, the variance
# detection alert engine, and the AI Analyst grounding for "why did my
# margin change" questions. See ``models/cost_history.py`` for the schema
# and lifecycle rationale.
product_cost_history_collection = db.product_cost_history

# Sales Core — Orders (structured sales transactions)
orders_collection = db.orders

# Event Occurrences — dated instances of event_ticket products
event_occurrences_collection = db.event_occurrences

# P7: Atomic seat reservations for event_ticket occurrences. One row per
# (order_id, occurrence_id) — used for idempotency and safe release on
# order cancel. Authoritative capacity counter lives on the occurrence
# document itself (`reserved_seats` field).
event_seat_reservations_collection = db.event_seat_reservations

# E1: Ticket tiers per occurrence — multi-tier pricing and per-tier
# capacity. A tier is always scoped to one occurrence; when an
# occurrence has zero tiers the storefront falls back to mono-tier
# behavior using occurrence.price_override + occurrence.capacity.
event_ticket_tiers_collection = db.event_ticket_tiers

# E4: Issued tickets — one row per seat sold, carrying a unique
# human-readable code (EVT-XXXX-XXXX) used by the email + door scanner
# (E5). Never deleted: cancelled orders transition rows to
# status="voided" so audit trails stay intact.
issued_tickets_collection = db.issued_tickets

# F5 (Onda 12): Service options — radio-select choices for a service
# product (e.g. "Consulenza 30 min" / "Pacchetto 3 sedute"). Unlike
# event ticket tiers (scoped to an occurrence) these are scoped
# directly to the product since services don't have occurrences.
service_options_collection = db.service_options

# Onda 14: IssuedBooking — analog of IssuedTicket for service products
# (consulenze). One row per confirmed appointment/slot. Carries a unique
# human-readable code (BKG-XXXX-XXXX) used by the confirmation email
# and the customer-facing booking landing page (/b/{access_token}).
# Cancelled bookings transition to status="cancelled", never deleted.
issued_bookings_collection = db.issued_bookings

# Onda 16 (Prenotazione consolidation): ProductExtra — generalized
# add-ons for any product type. Supersedes ServiceOption for new writes;
# service_options_collection kept as back-compat read-only alias for
# one release. Three kinds: mandatory (auto-applied), optional (checkbox
# multi-select), radio_variant (mutually exclusive within group_key).
product_extras_collection = db.product_extras

# Onda 16: IssuedReservation — analog of IssuedTicket / IssuedBooking
# for rental products (both range flavor: B&B, cars; and slot flavor:
# meeting rooms, courts). Unique code RSV-XXXX-XXXX and public landing
# /rsv/{access_token}. Idempotent per (order_id, order_line_index).
issued_reservations_collection = db.issued_reservations

# Release 3 (Digital): IssuedDownload — analog of IssuedReservation for
# item_type=digital products. One row per (order_id, order_line_index);
# public landing at /d/{access_token} serves the file via a token-gated
# stream that decrements `download_count` atomically.
issued_downloads_collection = db.issued_downloads

# Release 4 (Courses): Course is the content entity for video courses
# (item_type="course"). Hierarchy: Course → CourseModule → Lesson, with
# each Lesson holding a Bunny Stream video GUID. Bunny remains the only
# host for video files. The Course is the "content" side of the
# Product+Entity pattern (Product.metadata.course_id → Course.id).
courses_collection = db.courses

# Release 4 (Courses): IssuedCourseAccess — one fulfilled enrollment per
# (order_id, order_line_index). Customer-account-scoped (mandatory),
# never guest. Customer-facing URL /account/courses/{enrollment_id} is
# JWT-protected; signed Bunny URLs are minted per-request with a 2h TTL.
issued_course_accesses_collection = db.issued_course_accesses

# Shipping: merchant-configured delivery options for the storefront.
# Each doc is either scoped to one store (store_id) or is org-global
# (store_id=null → visible in every store of the org at checkout).
shipping_options_collection = db.shipping_options

# Payment Connections — org-level payment provider accounts
payment_connections_collection = db.payment_connections

# AI Digests (weekly/monthly financial summaries)
digests_collection = db.digests

# AI Usage Events (append-only log for monetization tracking)
ai_usage_events_collection = db.ai_usage_events

# AI Chat Sessions (persisted conversation history, replaces in-memory storage)
chat_sessions_collection = db.chat_sessions
# PR2 — recensioni operatore + OTP di verifica email
reviews_collection = db.reviews
review_otps_collection = db.review_otps

# ── Modular Subscription Architecture (v4.0) ──────────────────────────────────
# Pricing plans: admin-managed plans per module_key (replaces hardcoded PLAN_LIMITS)
pricing_plans_collection = db.pricing_plans
# Module subscriptions: per-org per-module subscription linking to a pricing plan
module_subscriptions_collection = db.module_subscriptions
# v5.8 / Onda 3 — Add-on subscriptions: per-org per-addon record. One per
# (organization_id, addon_slug). Sits beside module_subscriptions; never
# replaces it. See models/addon_subscription.py.
addon_subscriptions_collection = db.addon_subscriptions
# v5.8 / Onda 6 — Idempotency log for quota-warning emails. Unique compound
# index on (organization_id, metric_key, level, period_start) prevents the
# quota_warning_sweep cron from sending the same email twice in one period.
# See models/org_quota_notice.py.
org_quota_notices_collection = db.org_quota_notices

# Migration tracking
schema_versions_collection = db.schema_versions

# ── v5.0: Commercial Billing Architecture ─────────────────────────────────────
# Commercial plans: user-facing plan catalog (Free/Core/Pro/Enterprise)
commercial_plans_collection = db.commercial_plans
# Billing events: idempotent webhook processing log
billing_events_collection = db.billing_events

# ── Phase 2a: Catalog Governance ─────────────────────────────────────────────
# Catalog audit log: dedicated audit trail for commercial catalog mutations
catalog_audit_log_collection = db.catalog_audit_log

# ── Controlled Access (v6.0) ─────────────────────────────────────────────────
# Platform-wide settings (registration mode, etc.) — one doc per key
platform_settings_collection = db.platform_settings
# Platform-level invitations (system admin → new org owner sign-up)
invites_collection = db.invites

# Wave 8B — AI Governance budgets (per-org/user/global hard limits on Anthropic spend)
ai_budgets_collection = db.ai_budgets

# ── Multi-Store Architecture (v12.0) ─────────────────────────────────────────
# Each org can have multiple stores (storefronts), each with own slug,
# catalog subset, visibility, and settings.
stores_collection = db.stores

# ── Calendar & Availability (v12.0) ──────────────────────────────────────────
availability_rules_collection = db.availability_rules
blocked_slots_collection = db.blocked_slots
coupons_collection = db.coupons
# R5 — redemption per-cliente: una riga per (coupon, cliente) consumato.
# Unique index su (org, coupon_id, customer_key) impedisce il riuso.
coupon_redemptions_collection = db.coupon_redemptions

# ── Newsletter / form embeddabili (F1) ───────────────────────────────────
# Form org-scoped (store opzionale) con identità embed propria (slug + origins).
newsletter_forms_collection = db.newsletter_forms
# Eventi di iscrizione (con tracciamento sorgente D7).
newsletter_subscriptions_collection = db.newsletter_subscriptions

# ── Customer Identity Foundation (v9.0) ──────────────────────────────────────
# Global customer login accounts (not org-scoped). Linked to org-scoped
# `customers` records and `orders` via customer_account_id FK.
customer_accounts_collection = db.customer_accounts

# Platform accounts (P1, 5/7/2026) — identita' unica marketplace, sopra
# i customer_accounts org-scoped. Vedi docs/PLATFORM_ACCOUNT_PLAN.md.
platform_accounts_collection = db.platform_accounts
platform_magic_tokens_collection = db.platform_magic_tokens


# ── Phase 3 (Store consolidation) — slug-index lifecycle helpers ────────────
#
# Centralised, idempotent index management for `stores_collection`.
# Refactored out of `create_indexes()` so the slug-uniqueness story —
# the most subtle invariant in the multi-store architecture — has a
# single, testable home. See the long comment in `create_indexes()`
# at the `stores_collection` block for the architectural rationale.


# Canonical specs (single source of truth). The migration script
# `scripts/migrate_stores_slug_index.py` imports these constants so the
# CLI and runtime stay aligned. Changing these requires updating both
# the script's idempotency check AND the test in
# tests/test_stores_indexes.py.
_STORES_COMPOSITE_SLUG_NAME = "organization_id_1_slug_1"
_STORES_COMPOSITE_SLUG_KEYS = [("organization_id", 1), ("slug", 1)]
_STORES_COMPOSITE_SLUG_OPTIONS = {
    "unique": True,
    "partialFilterExpression": {"slug": {"$type": "string"}},
}

_STORES_GLOBAL_SLUG_NAME = "slug_1"
_STORES_GLOBAL_SLUG_OPTIONS = {
    "unique": True,
    "partialFilterExpression": {"slug": {"$type": "string"}},
}


def _index_spec_matches(existing: dict, expected_options: dict) -> bool:
    """Return True when an existing index document matches the expected
    options (unique flag + partialFilterExpression). Used to decide
    whether to leave the index alone or drop-and-recreate it.

    Doesn't compare `key` here — callers pre-filter by index name and
    name uniquely identifies the (key, options) tuple in our schema.
    """
    if expected_options.get("unique") and not existing.get("unique"):
        return False
    expected_pfe = expected_options.get("partialFilterExpression")
    actual_pfe = existing.get("partialFilterExpression")
    if expected_pfe and actual_pfe != expected_pfe:
        return False
    # Legacy sparse=True without partialFilterExpression is the
    # exact pattern Onda 9.Z fixed. Treat as mismatch so we migrate.
    if expected_pfe and existing.get("sparse"):
        return False
    return True


async def _ensure_stores_indexes() -> None:
    """Create / migrate the four canonical indexes on stores_collection.

    Called from `create_indexes()` on app startup. Idempotent:
      - First boot: creates all four indexes from scratch.
      - Steady state: lists existing, finds spec matches, no-ops.
      - Legacy migration (sparse → partial): detects mismatched spec
        on `slug_1` (most likely scenario), drops and recreates.

    Logs at INFO when it takes action, WARNING on unexpected errors.
    Never swallows errors silently — a failed slug-index creation must
    be loud, because public routing depends on it.
    """
    import logging as _logging
    logger = _logging.getLogger(__name__)

    # Non-unique helper indexes — cheap, no migration concern.
    await stores_collection.create_index("organization_id")
    await stores_collection.create_index(
        [("organization_id", 1), ("is_default", 1)],
    )

    # Snapshot current index state. We compare names rather than keys
    # because index keys serialise differently across Motor versions
    # (SON vs dict ordering quirks).
    current_indexes: dict = {}
    async for idx in stores_collection.list_indexes():
        name = idx.get("name")
        if name:
            current_indexes[name] = idx

    # ── Composite (org_id, slug) unique partial ──────────────────────
    composite = current_indexes.get(_STORES_COMPOSITE_SLUG_NAME)
    if composite and _index_spec_matches(composite, _STORES_COMPOSITE_SLUG_OPTIONS):
        logger.debug("stores.%s: spec matches, no action", _STORES_COMPOSITE_SLUG_NAME)
    else:
        if composite:
            logger.info(
                "stores.%s: legacy spec detected, dropping and recreating",
                _STORES_COMPOSITE_SLUG_NAME,
            )
            try:
                await stores_collection.drop_index(_STORES_COMPOSITE_SLUG_NAME)
            except Exception as e:
                logger.warning(
                    "stores.%s: drop_index failed (continuing): %s",
                    _STORES_COMPOSITE_SLUG_NAME, e,
                )
        await stores_collection.create_index(
            _STORES_COMPOSITE_SLUG_KEYS,
            name=_STORES_COMPOSITE_SLUG_NAME,
            **_STORES_COMPOSITE_SLUG_OPTIONS,
        )
        logger.info("stores.%s: index created", _STORES_COMPOSITE_SLUG_NAME)

    # ── Global slug unique partial (REQUIRED for public routing) ─────
    global_idx = current_indexes.get(_STORES_GLOBAL_SLUG_NAME)
    if global_idx and _index_spec_matches(global_idx, _STORES_GLOBAL_SLUG_OPTIONS):
        logger.debug("stores.%s: spec matches, no action", _STORES_GLOBAL_SLUG_NAME)
    else:
        if global_idx:
            # Legacy sparse=True from pre-Onda 9.Z. The migration script
            # is the authoritative drop+recreate path; this is the
            # runtime safety net so a fresh container in a half-migrated
            # cluster still ends up in the canonical state.
            logger.info(
                "stores.%s: legacy spec detected (sparse or stale partial), "
                "dropping and recreating",
                _STORES_GLOBAL_SLUG_NAME,
            )
            try:
                await stores_collection.drop_index(_STORES_GLOBAL_SLUG_NAME)
            except Exception as e:
                logger.warning(
                    "stores.%s: drop_index failed (continuing): %s",
                    _STORES_GLOBAL_SLUG_NAME, e,
                )
        try:
            await stores_collection.create_index(
                "slug",
                name=_STORES_GLOBAL_SLUG_NAME,
                **_STORES_GLOBAL_SLUG_OPTIONS,
            )
            logger.info("stores.%s: index created", _STORES_GLOBAL_SLUG_NAME)
        except Exception as e:
            # No silent swallow — public routing depends on this.
            logger.error(
                "stores.%s: CRITICAL — could not create global slug "
                "uniqueness index. Public routing (/co/<slug>) becomes "
                "non-deterministic. Run scripts/migrate_stores_slug_index.py "
                "to investigate. Error: %s",
                _STORES_GLOBAL_SLUG_NAME, e,
            )


async def create_indexes():
    """Create database indexes for better query performance.

    Rules:
    - Existing indexes are listed first and must never be removed.
    - Phase-1 additions are clearly marked and append-only.
    """

    # ── Fase 5 (retreat) — indici del calendario pubblico ────────────────────
    # Decisi ORA perché costosi da cambiare dopo (master plan §note scalabilità):
    # la query del calendario filtra status+start_at (+region) e ordina per
    # start_at — compound index dedicati, append-only.
    await event_occurrences_collection.create_index(
        [("status", 1), ("start_at", 1)], name="f5_calendar_status_start")
    await event_occurrences_collection.create_index(
        [("region", 1), ("status", 1), ("start_at", 1)],
        name="f5_calendar_region", sparse=True)
    # G1 (geo search) — ricerca per raggio sul calendario pubblico.
    # `geo` e' il GeoJSON Point derivato da latitude/longitude al save
    # (services/geocoding.enrich_occurrence_geo). Sparse: gli eventi
    # senza pin restano fuori dall'indice ma visibili in lista.
    await event_occurrences_collection.create_index(
        [("geo", "2dsphere")], name="g1_geo", sparse=True)
    # AN3 — posizione dell'OPERATORE (profilo pubblico): la scoperta
    # geografica non dipende dai ritiri futuri. Sparse: chi non ha
    # configurato la località resta fuori dall'indice ma in lista.
    await organizations_collection.create_index(
        [("public_profile.geo", "2dsphere")], name="an3_org_geo", sparse=True)
    # cache geocoding Nominatim (policy OSM: mai ri-geocodare)
    await db.geocode_cache.create_index("query", unique=True, name="g1_geocache")
    # AN5 blog: slug unico + listing pubblico per data di pubblicazione
    await db.articles.create_index("slug", unique=True, name="an5_article_slug")
    await db.articles.create_index(
        [("published", 1), ("published_at", -1)], name="an5_article_pub")
    # payment_schedules: lookup per ordine (hot path webhook/dashboard) e
    # per occurrence (dashboard incassi), eventi per ordine (tracciabilità)
    await db.payment_schedules.create_index(
        [("order_id", 1), ("organization_id", 1)], name="f5_sched_order")
    await db.payment_schedules.create_index(
        [("organization_id", 1), ("occurrence_id", 1)], name="f5_sched_occ")
    await db.payment_schedules.create_index(
        [("rows.pay_token", 1)], name="f5_sched_paytoken", sparse=True)
    await db.payment_events.create_index(
        [("order_id", 1), ("at", 1)], name="f5_events_order")

    # ── EXISTING INDEXES (unchanged) ─────────────────────────────────────────

    # Users
    await users_collection.create_index("email", unique=True)
    await users_collection.create_index("organization_id")

    # Datasets
    await datasets_collection.create_index("organization_id")
    await datasets_collection.create_index([("organization_id", 1), ("dataset_type", 1)])

    # Sales records
    await sales_records_collection.create_index("organization_id")
    await sales_records_collection.create_index([("organization_id", 1), ("date", 1)])
    await sales_records_collection.create_index("dataset_id")

    # Expense records
    await expense_records_collection.create_index("organization_id")
    await expense_records_collection.create_index([("organization_id", 1), ("date", 1)])
    await expense_records_collection.create_index("dataset_id")
    await expense_records_collection.create_index(
        [("organization_id", 1), ("supplier_id", 1)]
    )

    # Organization modules
    await organization_modules_collection.create_index("organization_id")
    await organization_modules_collection.create_index(
        [("organization_id", 1), ("module_key", 1)], unique=True
    )

    # Alerts
    await alerts_collection.create_index("organization_id")
    await alerts_collection.create_index([("organization_id", 1), ("status", 1)])
    await alerts_collection.create_index([("organization_id", 1), ("created_at", -1)])

    # Insights
    await insights_collection.create_index("organization_id")
    await insights_collection.create_index([("organization_id", 1), ("created_at", -1)])

    # Audit logs
    await audit_logs_collection.create_index("organization_id")
    await audit_logs_collection.create_index([("organization_id", 1), ("created_at", -1)])
    # Phase 1 Step D3 — TTL index on expire_at (BSON Date) auto-deletes audit
    # entries older than 365 days. Documents created BEFORE this index was
    # added (or that lack the expire_at field) are NOT affected — TTL only
    # acts on documents whose expire_at value exists and is a Date type.
    # GDPR-friendly retention: 1 year covers the typical "right to know"
    # retention requirement for operational logs without unbounded growth.
    await audit_logs_collection.create_index(
        "expire_at",
        expireAfterSeconds=60 * 60 * 24 * 365,  # 365 days
        name="audit_logs_ttl",
    )

    # ── Wave GDPR-Admin Phase B — consent_audit indexes ─────────────────────
    # Lookup patterns:
    #   1. "show me everything user X accepted, newest first" → user_id + accepted_at DESC
    #   2. "find all acceptances of policy version Y" → version_tag
    #   3. legal hold dispute resolution → user_id + version_tag
    #
    # Retention: same 365-day TTL as audit_logs (Art. 17 right to erasure
    # already removes the user record; the consent_audit is PII-light
    # by design — only user_id + version + locale + IP/UA hash).
    await consent_audit_collection.create_index("user_id")
    await consent_audit_collection.create_index([("user_id", 1), ("accepted_at", -1)])
    await consent_audit_collection.create_index("version_tag")
    await consent_audit_collection.create_index(
        "expire_at",
        expireAfterSeconds=60 * 60 * 24 * 365,  # 365 days
        name="consent_audit_ttl",
    )

    # ── PHASE-1: MISSING INDEXES ON EXISTING COLLECTIONS ─────────────────────
    # These were absent and causing full-collection scans on common category queries.

    # Sales records – category aggregations (used by cashflow_monitor)
    await sales_records_collection.create_index(
        [("organization_id", 1), ("category", 1)]
    )

    # Expense records – category aggregations
    await expense_records_collection.create_index(
        [("organization_id", 1), ("category", 1)]
    )

    # Alerts – triple compound for filtered UI queries (org + severity + status)
    await alerts_collection.create_index(
        [("organization_id", 1), ("severity", 1), ("status", 1)]
    )

    # Insights – module + time queries
    await insights_collection.create_index(
        [("organization_id", 1), ("module_key", 1), ("created_at", -1)]
    )

    # ── PHASE-1: NEW COLLECTION INDEXES ──────────────────────────────────────

    # Customers
    await customers_collection.create_index("organization_id")
    # Unique external_id per org — only enforced when external_id is a string (not null)
    try:
        await customers_collection.drop_index("organization_id_1_external_id_1")
    except Exception:
        pass
    await customers_collection.create_index(
        [("organization_id", 1), ("external_id", 1)], unique=True,
        partialFilterExpression={"external_id": {"$type": "string"}},
    )
    await customers_collection.create_index([("organization_id", 1), ("name", 1)])

    # Phase 4 (Store consolidation) — race-safe customer upsert by email.
    #
    # Storefront checkout and POS order creation both invoke
    # `repositories.customer_repository.upsert_by_email` keyed on
    # (organization_id, email). Without a unique constraint at the
    # storage layer, two concurrent calls could each insert a row
    # (pre-Phase-4 code did find-then-insert with a multi-second
    # race window). This index closes the window at Mongo level:
    # `find_one_and_update(upsert=True)` deterministically converges
    # on a single document under contention; if some legacy code path
    # ever bypassed the upsert helper, the second insert would hit a
    # DuplicateKey at the index instead of silently corrupting state.
    #
    # `partialFilterExpression: {email: {$type: "string"}}` means:
    #   - email present and string  → uniqueness enforced
    #   - email null / missing      → bypassed
    # POS walk-in sales without an email keep working — multiple
    # anonymous customer rows per org are allowed (each gets a fresh
    # `id` and lives in the standard customers list, just not keyed
    # by email).
    await customers_collection.create_index(
        [("organization_id", 1), ("email", 1)],
        unique=True,
        partialFilterExpression={"email": {"$type": "string"}},
        name="organization_id_1_email_1",
    )

    # Suppliers
    await suppliers_collection.create_index("organization_id")
    try:
        await suppliers_collection.drop_index("organization_id_1_external_id_1")
    except Exception:
        pass
    await suppliers_collection.create_index(
        [("organization_id", 1), ("external_id", 1)], unique=True,
        partialFilterExpression={"external_id": {"$type": "string"}},
    )
    await suppliers_collection.create_index([("organization_id", 1), ("name", 1)])

    # Products
    await products_collection.create_index("organization_id")
    try:
        await products_collection.drop_index("organization_id_1_sku_1")
    except Exception:
        pass
    await products_collection.create_index(
        [("organization_id", 1), ("sku", 1)], unique=True,
        partialFilterExpression={"sku": {"$type": "string"}},
    )
    await products_collection.create_index([("organization_id", 1), ("category", 1)])

    # Onda 13 — unique slug per organization (sparse: legacy products
    # without slug coexist with new ones). Used by the public product
    # landing page endpoint /api/public/products/{org_slug}/{product_slug}.
    await products_collection.create_index(
        [("organization_id", 1), ("slug", 1)], unique=True,
        partialFilterExpression={"slug": {"$type": "string"}},
    )

    # Track E Step 1.3 — full-text search index per /embed/products
    # endpoint. Mongo permette UN solo text index per collection;
    # questo copre name (weight 3) + description (weight 1).
    #
    # default_language="italian":
    #   - stemmer italiano (es. "panini" matches "panino", "panini")
    #   - stopwords italiane ignorate ("il", "la", "di", ecc.)
    #   - V2 multi-lingua: switch to "none" + Python lemmatization
    #
    # Idempotent: ignore IndexOptionsConflict / OperationFailure (re-deploy
    # tipico: index already exists with same spec → no-op).
    try:
        await products_collection.create_index(
            [("name", "text"), ("description", "text")],
            weights={"name": 3, "description": 1},
            default_language="italian",
            name="embed_search_text_idx",
        )
    except Exception as e:
        # Index may already exist with different spec; log and continue.
        # In production we want strict assertion via migration script
        # (V2). For now: warn + continue → API search still works,
        # just non-optimal performance until index is fixed.
        import logging as _log
        _log.getLogger(__name__).warning(
            "products_collection text index create failed (may already "
            "exist with different spec, run migration): %s", e,
        )

    # Purchase records
    await purchase_records_collection.create_index("organization_id")
    await purchase_records_collection.create_index(
        [("organization_id", 1), ("date", 1)]
    )
    await purchase_records_collection.create_index(
        [("organization_id", 1), ("supplier_id", 1)]
    )
    await purchase_records_collection.create_index("dataset_id")
    # supplier_name index added from main for denormalised-name queries
    await purchase_records_collection.create_index(
        [("organization_id", 1), ("supplier_name", 1)]
    )
    await purchase_records_collection.create_index(
        [("organization_id", 1), ("product_id", 1)]
    )

    # Fixed costs
    await fixed_costs_collection.create_index("organization_id")
    await fixed_costs_collection.create_index(
        [("organization_id", 1), ("is_active", 1)]
    )
    await fixed_costs_collection.create_index(
        [("organization_id", 1), ("category", 1)]
    )
    await fixed_costs_collection.create_index("dataset_id")

    # Column mappings
    await column_mappings_collection.create_index("organization_id")
    await column_mappings_collection.create_index(
        [("organization_id", 1), ("dataset_type", 1)]
    )

    # Dataset column profiles (one profile per dataset)
    await dataset_column_profiles_collection.create_index("organization_id")
    await dataset_column_profiles_collection.create_index("dataset_id", unique=True)

    # Data validation rules
    await data_validation_rules_collection.create_index("organization_id")
    await data_validation_rules_collection.create_index(
        [("organization_id", 1), ("dataset_type", 1), ("is_active", 1)]
    )

    # KPI snapshots (unique per org + module + period start)
    await kpi_snapshots_collection.create_index("organization_id")
    await kpi_snapshots_collection.create_index(
        [("organization_id", 1), ("module_key", 1), ("period_start", 1)],
        unique=True,
    )
    await kpi_snapshots_collection.create_index(
        [("organization_id", 1), ("created_at", -1)]
    )
    # TTL: auto-purge snapshots older than 90 days. They are regenerated
    # on every upload so stale snapshots are dead weight.
    await kpi_snapshots_collection.create_index(
        "created_at", expireAfterSeconds=90 * 24 * 60 * 60,
    )

    # Module configs (one config document per org + module)
    await module_configs_collection.create_index(
        [("organization_id", 1), ("module_key", 1)], unique=True
    )

    # Temp uploads — TTL index: documents expire 1 hour after creation
    await temp_uploads_collection.create_index(
        "created_at", expireAfterSeconds=3600
    )

    # Schema versions (one document per collection being tracked)
    await schema_versions_collection.create_index("collection_name", unique=True)
    await schema_versions_collection.create_index([("applied_at", -1)])

    # ── v2.4: SCADENZARIO INDEXES — payment status + due date queries ──────
    await sales_records_collection.create_index(
        [("organization_id", 1), ("payment_status", 1)]
    )
    await sales_records_collection.create_index(
        [("organization_id", 1), ("due_date", 1)]
    )
    await purchase_records_collection.create_index(
        [("organization_id", 1), ("payment_status", 1)]
    )
    await purchase_records_collection.create_index(
        [("organization_id", 1), ("due_date", 1)]
    )

    # ── Performance: compound indexes for scadenzario + trend queries ─────
    # Scadenzario queries filter on payment_status AND due_date together;
    # separate single-field indexes force MongoDB to intersect two scans.
    # Compound index lets a single B-tree walk satisfy both conditions.
    await sales_records_collection.create_index(
        [("organization_id", 1), ("payment_status", 1), ("due_date", 1)]
    )
    await purchase_records_collection.create_index(
        [("organization_id", 1), ("payment_status", 1), ("due_date", 1)]
    )

    # Customer revenue trend queries group by customer_id within a date range.
    # Without this, MongoDB uses the (org_id, customer_id) index but still
    # scans all dates for each customer.
    await sales_records_collection.create_index(
        [("organization_id", 1), ("customer_id", 1), ("date", 1)]
    )


    # ── AI Usage Events — org + module + feature + time queries ─────────────
    await ai_usage_events_collection.create_index("organization_id")
    await ai_usage_events_collection.create_index(
        [("organization_id", 1), ("feature", 1), ("created_at", -1)]
    )
    # v4.0-C: module-aware compound index — prevents feature_key collisions
    await ai_usage_events_collection.create_index(
        [("organization_id", 1), ("module_key", 1), ("feature", 1), ("created_at", -1)]
    )

    # ── v2.5: DIGEST INDEXES ───────────────────────────────────────────────
    await digests_collection.create_index("organization_id")
    await digests_collection.create_index(
        [("organization_id", 1), ("digest_type", 1), ("created_at", -1)]
    )

    # ── v4.0: MODULAR SUBSCRIPTION INDEXES ─────────────────────────────────
    await pricing_plans_collection.create_index("module_key")
    await pricing_plans_collection.create_index(
        [("module_key", 1), ("slug", 1)], unique=True
    )
    await module_subscriptions_collection.create_index("organization_id")
    await module_subscriptions_collection.create_index(
        [("organization_id", 1), ("module_key", 1), ("status", 1)]
    )
    await module_subscriptions_collection.create_index("pricing_plan_id")

    # v5.8 / Onda 9.Y.0.2 — Partial unique index: at most ONE active
    # module_subscription per (organization_id, module_key). Cancelled rows
    # are kept for audit so the index is filtered to status=active.
    #
    # Without this guard, a race between concurrent webhooks
    # (`checkout.session.completed` and a delayed
    # `customer.subscription.updated`) could produce two `active` rows for
    # the same (org, module). The entitlement gate at module_access.py:218
    # picks the first one returned by Mongo and ignores the rest, so a
    # higher-tier orphan row (e.g. cashflow_monitor_pro) would silently
    # outrank a freshly-provisioned free row → quota bypass.
    #
    # Existing duplicates (if any) must be repaired BEFORE rolling this out
    # via `python -m scripts.repair_module_subscription_drift --apply`.
    # If a duplicate slips through anyway, MongoDB will raise E11000 on
    # insert; the upstream caller (`provision_commercial_plan`) already
    # cancels existing actives first, so a well-formed flow is unaffected.
    try:
        await module_subscriptions_collection.create_index(
            [("organization_id", 1), ("module_key", 1)],
            unique=True,
            partialFilterExpression={"status": "active"},
            name="uniq_active_per_org_module",
        )
    except Exception as e:  # pragma: no cover — index already exists
        # If the database has duplicate active rows the create_index
        # itself fails. Don't crash startup — log and let the operator
        # run the repair script.
        import logging as _logging
        _logging.getLogger(__name__).warning(
            "module_subscriptions: could not create uniq_active_per_org_module "
            "index: %s. Run scripts/repair_module_subscription_drift.py to "
            "clean up duplicates and retry on next boot.", e,
        )

    # ── v5.8 / Onda 3 — addon_subscriptions ──────────────────────────────────
    # `(organization_id, addon_slug)` is unique among ACTIVE rows: an org can
    # only have one active subscription per add-on slug at a time. Cancelled
    # rows are kept for audit so the unique index is partial.
    await addon_subscriptions_collection.create_index("organization_id")
    await addon_subscriptions_collection.create_index(
        [("organization_id", 1), ("addon_slug", 1), ("status", 1)]
    )
    await addon_subscriptions_collection.create_index("stripe_subscription_id")
    # Onda 9.Z Step D — partialFilterExpression instead of sparse=True.
    # See migrate_unique_sparse_indices.py for rationale and migration path.
    # try/except: when an existing legacy sparse=True index is still in
    # place, create_index raises IndexKeySpecsConflict. The migration
    # script is the authoritative path to drop+recreate; here we skip
    # silently so a partial-migration state never blocks startup.
    try:
        await addon_subscriptions_collection.create_index(
            "stripe_subscription_item_id",
            unique=True,
            partialFilterExpression={"stripe_subscription_item_id": {"$type": "string"}},
            name="stripe_subscription_item_id_1",
        )
    except Exception as _e:
        import logging as _logging
        _logging.getLogger(__name__).warning(
            "addon_subscriptions.stripe_subscription_item_id_1: %s. "
            "Run scripts/migrate_unique_sparse_indices.py.", _e,
        )

    # ── v5.8 / Onda 6 — org_quota_notices idempotency ────────────────────────
    # Unique compound index makes "send quota email at most once per period"
    # an atomic invariant: duplicate inserts raise DuplicateKeyError which
    # the cron sweep catches and skips. No locking needed.
    await org_quota_notices_collection.create_index(
        [("organization_id", 1), ("metric_key", 1), ("level", 1), ("period_start", 1)],
        unique=True,
    )
    await org_quota_notices_collection.create_index("organization_id")
    await org_quota_notices_collection.create_index("sent_at")

    # ── Customers Light: customer_metrics indexes ────────────────────────────
    await customer_metrics_collection.create_index("organization_id")
    await customer_metrics_collection.create_index(
        [("organization_id", 1), ("customer_id", 1)], unique=True
    )
    await customer_metrics_collection.create_index(
        [("organization_id", 1), ("segment", 1)]
    )
    await customer_metrics_collection.create_index(
        [("organization_id", 1), ("total_revenue", -1)]
    )

    # ── Product Catalog: product_metrics indexes ─────────────────────────────
    await product_metrics_collection.create_index("organization_id")
    await product_metrics_collection.create_index(
        [("organization_id", 1), ("product_id", 1)], unique=True
    )
    await product_metrics_collection.create_index(
        [("organization_id", 1), ("total_revenue", -1)]
    )
    await product_metrics_collection.create_index(
        [("organization_id", 1), ("abc_class", 1)]
    )

    # ── Product Cost History (Wave 1, W1.S1) ─────────────────────────────────
    # Three indexes serving the three primary access patterns:
    #
    #   1. (org_id, product_id, period_end) UNIQUE  — idempotent upserts by
    #      the cost_history_service cron; rerunning for the same period
    #      replaces the existing row instead of duplicating.
    #
    #   2. (org_id, product_id, period_end DESC)    — drives the trend chart
    #      on the product detail page (latest N periods for a product).
    #
    #   3. (org_id, period_end DESC)                — drives the variance
    #      detector cron which scans the most recent period across all
    #      products of an org to flag MoM jumps above threshold.
    await product_cost_history_collection.create_index(
        [("organization_id", 1), ("product_id", 1), ("period_end", 1)],
        unique=True,
        name="org_product_period_unique",
    )
    await product_cost_history_collection.create_index(
        [("organization_id", 1), ("product_id", 1), ("period_end", -1)],
        name="org_product_period_desc",
    )
    await product_cost_history_collection.create_index(
        [("organization_id", 1), ("period_end", -1)],
        name="org_period_desc",
    )

    # ── Product Catalog: product_id index on sales_records ─────────────────
    await sales_records_collection.create_index(
        [("organization_id", 1), ("product_id", 1)]
    )

    # ── Customers Light: customer_id index on sales_records ──────────────────
    # Enables efficient GROUP BY customer_id aggregations.
    await sales_records_collection.create_index(
        [("organization_id", 1), ("customer_id", 1)]
    )

    # ── Sales Core: Orders ────────────────────────────────────────────────────
    await orders_collection.create_index("organization_id")
    await orders_collection.create_index(
        [("organization_id", 1), ("status", 1)]
    )
    await orders_collection.create_index(
        [("organization_id", 1), ("customer_id", 1)]
    )
    await orders_collection.create_index(
        [("organization_id", 1), ("created_at", -1)]
    )
    # Partial filter: unique constraint only on documents where order_number
    # is a string (i.e., assigned).  Drafts with order_number=None are excluded.
    await orders_collection.create_index(
        [("organization_id", 1), ("order_number", 1)],
        unique=True,
        partialFilterExpression={"order_number": {"$type": "string"}},
    )
    # 2026-05-20 — Legacy import provenance (Order.external_*).
    # Compound NON-unique index for two purposes:
    #   1. Idempotent re-imports: the import service does
    #      ``find_one({org_id, external_source, external_order_number})``
    #      to skip rows already imported. Without the index that lookup
    #      collection-scans 10k+ docs per row.
    #   2. Admin search: "find my order by Shopify ID #1001" is a
    #      common workflow once import lands.
    # Not unique: two import sources can legitimately share the same
    # external_order_number (e.g. invoice "#1" from Shopify and
    # invoice "#1" from WooCommerce). Sparse so legacy orders without
    # these fields don't bloat the index.
    await orders_collection.create_index(
        [
            ("organization_id", 1),
            ("external_source", 1),
            ("external_order_number", 1),
        ],
        sparse=True,
    )
    # Fulfillment dashboard queries filter on nested fulfillment.status;
    # without this index MongoDB scans all orders for the org.
    await orders_collection.create_index(
        [("organization_id", 1), ("fulfillment.status", 1)]
    )
    # Dashboard revenue queries filter by (org, status) and sort by order_date.
    # Without this compound index the dashboard aggregation scans all confirmed
    # orders for the org (up to the date filter). Sparse because older orders
    # written pre-field migration may not have order_date.
    await orders_collection.create_index(
        [("organization_id", 1), ("status", 1), ("order_date", -1)],
        sparse=True,
    )

    # ── Event Occurrences ─────────────────────────────────────────────────────
    await event_occurrences_collection.create_index("organization_id")
    await event_occurrences_collection.create_index(
        [("organization_id", 1), ("product_id", 1), ("start_at", 1)]
    )
    await event_occurrences_collection.create_index(
        [("organization_id", 1), ("status", 1)]
    )
    # Public storefront lists read all published occurrences for an org
    # ordered by recency. Without this index every /api/public/catalog call
    # does a full scan of the org's occurrences.
    await event_occurrences_collection.create_index(
        [("organization_id", 1), ("is_published", 1), ("created_at", -1)],
        sparse=True,
    )

    # E3: partial-unique slug per organization for the public landing page.
    # `sparse=True` on a COMPOUND index still includes docs that have
    # organization_id but not slug (MongoDB indexes them with slug=null,
    # which defeats our uniqueness). partialFilterExpression is the
    # correct tool: the index only covers docs where slug is actually
    # set, so pre-E3 rows (or any null/missing slug) are NOT indexed.
    # Safe migration: drop the initial sparse variant if present before
    # recreating with partialFilterExpression, since MongoDB forbids
    # redefining an index's options in place.
    try:
        await event_occurrences_collection.drop_index("organization_id_1_slug_1")
    except Exception:
        pass
    await event_occurrences_collection.create_index(
        [("organization_id", 1), ("slug", 1)],
        unique=True,
        partialFilterExpression={"slug": {"$exists": True, "$type": "string"}},
    )

    # ── P7+E1: Event Seat Reservations ───────────────────────────────────────
    # Composite unique constraint on (order_id, occurrence_id, tier_id)
    # makes the idempotency upsert safe at the server level for BOTH
    # mono-tier reservations (tier_id=None) and multi-tier reservations
    # (one row per distinct tier). E1 migration: the pre-E1 unique index
    # was on (order_id, occurrence_id) — we drop it if present before
    # creating the new one so fresh deploys don't duplicate-index.
    try:
        await event_seat_reservations_collection.drop_index("order_id_1_occurrence_id_1")
    except Exception:
        pass  # index did not exist — fresh deploy or already migrated

    await event_seat_reservations_collection.create_index(
        [("order_id", 1), ("occurrence_id", 1), ("tier_id", 1)], unique=True
    )
    await event_seat_reservations_collection.create_index(
        [("organization_id", 1), ("order_id", 1)]
    )
    await event_seat_reservations_collection.create_index(
        [("organization_id", 1), ("occurrence_id", 1)]
    )

    # ── E1: Event Ticket Tiers ───────────────────────────────────────────────
    # Primary lookup is by occurrence_id (tier picker on the storefront).
    # Org-scoped index for admin tier lists and cross-occurrence reporting.
    await event_ticket_tiers_collection.create_index(
        [("occurrence_id", 1), ("sort_order", 1)]
    )
    await event_ticket_tiers_collection.create_index(
        [("organization_id", 1), ("occurrence_id", 1)]
    )

    # ── F5 (Onda 12): Service Options ─────────────────────────────────────────
    # Primary lookup at storefront is by product_id (option picker). Active
    # options ordered by sort_order render first. Org-scoped secondary
    # supports admin tools and cross-product reporting.
    await service_options_collection.create_index(
        [("product_id", 1), ("sort_order", 1)]
    )
    await service_options_collection.create_index(
        [("organization_id", 1), ("product_id", 1), ("is_active", 1)]
    )

    # ── E4: Issued Tickets ───────────────────────────────────────────────────
    # Globally-unique `code` is the primary lookup key for the door
    # scanner (E5). Making it unique cross-org prevents scanning
    # confusion between tenants. Additional indexes support:
    #   - order-cancel release and buyer email rendering (order_id)
    #   - per-event attendance lists (org + occurrence)
    await issued_tickets_collection.create_index("code", unique=True)
    await issued_tickets_collection.create_index(
        [("organization_id", 1), ("order_id", 1)]
    )
    await issued_tickets_collection.create_index(
        [("organization_id", 1), ("occurrence_id", 1), ("status", 1)]
    )
    # F1 Onda 8 — unique (sparse: only set on new tickets, legacy rows lack it)
    # public landing token. Lookup is "find by access_token", no org scope since
    # tokens are unguessable + globally unique.
    # Onda 9.Z Step D — partialFilterExpression vs sparse, see Step A rationale.
    try:
        await issued_tickets_collection.create_index(
            "access_token",
            unique=True,
            partialFilterExpression={"access_token": {"$type": "string"}},
            name="access_token_1",
        )
    except Exception as _e:
        import logging as _logging
        _logging.getLogger(__name__).warning(
            "issued_tickets.access_token_1: %s", _e,
        )

    # ── Onda 14: Issued Bookings (service appointments) ──────────────────────
    # Indexes mirror issued_tickets purposes:
    #   - unique code for code→booking lookup (resend, admin actions)
    #   - order_id for order-cancel release + email rendering
    #   - per-admin calendar listing (org + booking_date)
    #   - public token for customer landing page /b/{token}
    await issued_bookings_collection.create_index("code", unique=True)
    await issued_bookings_collection.create_index(
        [("organization_id", 1), ("order_id", 1)]
    )
    await issued_bookings_collection.create_index(
        [("organization_id", 1), ("booking_date", 1), ("booking_start_time", 1)]
    )
    await issued_bookings_collection.create_index(
        [("organization_id", 1), ("status", 1), ("booking_date", 1)]
    )
    # Onda 9.Z Step D — partialFilterExpression vs sparse.
    try:
        await issued_bookings_collection.create_index(
            "access_token",
            unique=True,
            partialFilterExpression={"access_token": {"$type": "string"}},
            name="access_token_1",
        )
    except Exception as _e:
        import logging as _logging
        _logging.getLogger(__name__).warning(
            "issued_bookings.access_token_1: %s", _e,
        )

    # ── Onda 16: Product Extras (generalized add-ons) ────────────────────────
    # Storefront reads by (product_id, is_active) sorted by sort_order.
    # Kind filter is used by the admin editor and by server-side mandatory
    # auto-merge. Radio variants with the same group_key form a picker group
    # so an index on group_key helps admin analytics.
    await product_extras_collection.create_index(
        [("organization_id", 1), ("product_id", 1), ("sort_order", 1)]
    )
    await product_extras_collection.create_index(
        [("organization_id", 1), ("product_id", 1), ("kind", 1), ("is_active", 1)]
    )
    await product_extras_collection.create_index(
        [("organization_id", 1), ("product_id", 1), ("group_key", 1)]
    )

    # ── Onda 16: Issued Reservations (rental range + slot) ───────────────────
    # Mirrors issued_bookings purposes with an additional idempotency guard
    # on (order_id, order_line_index) so confirm_order retries never create
    # duplicate reservations.
    await issued_reservations_collection.create_index("code", unique=True)
    # Onda 9.Z Step D — partialFilterExpression vs sparse.
    try:
        await issued_reservations_collection.create_index(
            "access_token",
            unique=True,
            partialFilterExpression={"access_token": {"$type": "string"}},
            name="access_token_1",
        )
    except Exception as _e:
        import logging as _logging
        _logging.getLogger(__name__).warning(
            "issued_reservations.access_token_1: %s", _e,
        )
    await issued_reservations_collection.create_index(
        [("order_id", 1), ("order_line_index", 1)], unique=True
    )
    await issued_reservations_collection.create_index(
        [("organization_id", 1), ("order_id", 1)]
    )
    # Calendar listing per-flavor (range slots in date_from..date_to;
    # slot bookings identified by slot_date + slot_start_time).
    await issued_reservations_collection.create_index(
        [("organization_id", 1), ("reservation_flavor", 1), ("date_from", 1)]
    )
    await issued_reservations_collection.create_index(
        [("organization_id", 1), ("reservation_flavor", 1), ("slot_date", 1), ("slot_start_time", 1)]
    )
    await issued_reservations_collection.create_index(
        [("organization_id", 1), ("status", 1), ("created_at", -1)]
    )

    # ── Shipping options ─────────────────────────────────────────────────────
    # Fast per-store resolution at public checkout time — the most common
    # query is "all active options for org+store (plus store_id=null
    # globals) ordered by sort_order". The index covers both the per-store
    # and the global lookups; admin listing queries piggy-back on it.
    await shipping_options_collection.create_index(
        [("organization_id", 1), ("store_id", 1), ("sort_order", 1)]
    )
    # Admin listing with active filter.
    await shipping_options_collection.create_index(
        [("organization_id", 1), ("is_active", 1), ("created_at", -1)]
    )

    # ── Release 3 (Digital): Issued Downloads ────────────────────────────────
    # Same idempotency + uniqueness guarantees as issued_reservations so
    # confirm_order retries cannot duplicate the delivery.
    await issued_downloads_collection.create_index("code", unique=True)
    # Onda 9.Z Step D — partialFilterExpression vs sparse.
    try:
        await issued_downloads_collection.create_index(
            "access_token",
            unique=True,
            partialFilterExpression={"access_token": {"$type": "string"}},
            name="access_token_1",
        )
    except Exception as _e:
        import logging as _logging
        _logging.getLogger(__name__).warning(
            "issued_downloads.access_token_1: %s", _e,
        )
    await issued_downloads_collection.create_index(
        [("order_id", 1), ("order_line_index", 1)], unique=True
    )
    await issued_downloads_collection.create_index(
        [("organization_id", 1), ("order_id", 1)]
    )
    # Admin-side listing: recent deliveries + filter by status.
    await issued_downloads_collection.create_index(
        [("organization_id", 1), ("status", 1), ("created_at", -1)]
    )
    # Admin-side per-product dashboard view.
    await issued_downloads_collection.create_index(
        [("organization_id", 1), ("product_id", 1), ("created_at", -1)]
    )

    # ── Release 4 (Courses): Courses ─────────────────────────────────────────
    # Slug uniqueness scoped per-org so different merchants can use the
    # same slug independently. Sparse-not-needed: slug is mandatory.
    await courses_collection.create_index(
        [("organization_id", 1), ("slug", 1)], unique=True
    )
    # Admin listing: recent courses + filter by active state.
    await courses_collection.create_index(
        [("organization_id", 1), ("is_active", 1), ("created_at", -1)]
    )

    # ── Release 4 (Courses): Issued Course Accesses (enrollments) ────────────
    # Same idempotency guarantee as issued_downloads: confirm_order
    # retries cannot duplicate an enrollment. access_token is a global
    # unguessable handle.
    # Onda 9.Z Step D — partialFilterExpression vs sparse so historical
    # rows without an access_token (or with explicit null) survive.
    try:
        await issued_course_accesses_collection.create_index(
            "access_token",
            unique=True,
            partialFilterExpression={"access_token": {"$type": "string"}},
            name="access_token_1",
        )
    except Exception as _e:
        import logging as _logging
        _logging.getLogger(__name__).warning(
            "issued_course_accesses.access_token_1: %s", _e,
        )
    await issued_course_accesses_collection.create_index(
        [("order_id", 1), ("order_line_index", 1)], unique=True
    )
    # "My courses" list query — sorted by recency at app layer.
    await issued_course_accesses_collection.create_index(
        [("customer_account_id", 1), ("organization_id", 1)]
    )
    # Admin-side per-course dashboard view (Step 8: enrolled customers tab).
    await issued_course_accesses_collection.create_index(
        [("organization_id", 1), ("course_id", 1), ("created_at", -1)]
    )

    # ── Payment Connections ──────────────────────────────────────────────────
    await payment_connections_collection.create_index(
        [("organization_id", 1), ("provider", 1)], unique=True
    )
    await payment_connections_collection.create_index(
        [("organization_id", 1), ("is_default", 1)]
    )

    # ── AI Chat Sessions (R4: feature RIMOSSA — resta solo la pulizia) ──────
    # La chat AI non esiste più; i documenti legacy si auto-eliminano.
    # TTL 30 giorni su updated_at: entro un mese la collection si svuota
    # da sola, senza migrazione.
    try:
        await chat_sessions_collection.drop_index("expires_at_1")
    except Exception:
        pass  # indice del vecchio sistema per-document, può non esserci
    await chat_sessions_collection.create_index(
        "updated_at", expireAfterSeconds=30 * 24 * 3600,
        name="r4_chat_sessions_ttl",
    )

    # ── PR2 — recensioni operatore ───────────────────────────────────────────
    await reviews_collection.create_index(
        [("organization_id", 1), ("status", 1), ("created_at", -1)],
        name="pr2_reviews_org_status")
    await reviews_collection.create_index(
        [("organization_id", 1), ("author_email_hash", 1)],
        unique=True, name="pr2_reviews_one_per_email")
    # OTP: TTL a 1h (i documenti scaduti/usati si puliscono da soli)
    await review_otps_collection.create_index(
        "created_at", expireAfterSeconds=3600, name="pr2_review_otps_ttl")
    await review_otps_collection.create_index(
        [("org_slug", 1), ("email_hash", 1)], name="pr2_review_otps_lookup")

    # ── v5.0: COMMERCIAL BILLING INDEXES ─────────────────────────────────────
    await commercial_plans_collection.create_index("slug", unique=True)
    await billing_events_collection.create_index("stripe_event_id", unique=True)
    await billing_events_collection.create_index("organization_id")
    await billing_events_collection.create_index(
        [("organization_id", 1), ("created_at", -1)]
    )
    # Sparse indexes on Stripe IDs (only orgs with Stripe have these fields)
    await organizations_collection.create_index(
        "stripe_customer_id", sparse=True
    )
    await module_subscriptions_collection.create_index(
        "stripe_subscription_id", sparse=True
    )

    # ── Phase 2a: CATALOG AUDIT LOG INDEXES ──────────────────────────────
    await catalog_audit_log_collection.create_index(
        [("entity_type", 1), ("entity_id", 1)]
    )
    await catalog_audit_log_collection.create_index(
        [("performed_at", -1)]
    )

    # ── v6.0: ACCOUNT DEACTIVATION INDEX ─────────────────────────────────
    # Sparse: most orgs don't have deactivated_at. Enables efficient background
    # job query for orgs pending hard delete (deactivated_at < 30 days ago).
    await organizations_collection.create_index("deactivated_at", sparse=True)

    # ── v7.0: Public Layer — Onda 9.Z fix
    # Originally `unique=True, sparse=True`. MongoDB 7's sparse indexes
    # DO include explicit null values (only missing fields are excluded).
    # Pydantic `Organization.public_slug = None` default + `model_dump()`
    # produced `{public_slug: null}` documents which all collided in the
    # sparse-unique index, breaking every signup after the first.
    # `partialFilterExpression` rigorously includes only string values,
    # so null + missing + non-string types all bypass the unique constraint.
    # Behaviour-equivalent to "sparse unique" for the intended use case
    # (uniqueness of actual published slugs only).
    try:
        await organizations_collection.create_index(
            "public_slug",
            unique=True,
            partialFilterExpression={"public_slug": {"$type": "string"}},
            name="public_slug_1",
        )
    except Exception as e:
        # If a legacy `public_slug_1` (sparse=True) exists, the create
        # call no-ops (Mongo treats name match as already-exists). The
        # migration script `scripts/migrate_public_slug_index.py` is
        # the authoritative path to drop+recreate; this `try` keeps
        # startup non-fatal in case of partial migration state.
        import logging as _logging
        _logging.getLogger(__name__).warning(
            "organizations.public_slug_1: could not create with partialFilterExpression: %s. "
            "Run scripts/migrate_public_slug_index.py to migrate.", e,
        )

    # ── v6.0: CONTROLLED ACCESS INDEXES ───────────────────────────────────
    await platform_settings_collection.create_index("key", unique=True)
    await invites_collection.create_index("token_hash", unique=True)
    await invites_collection.create_index("email")
    await invites_collection.create_index([("status", 1), ("expires_at", 1)])

    # ── v12.0: Calendar & Availability ──────────────────────────────────
    await availability_rules_collection.create_index("organization_id")
    await availability_rules_collection.create_index(
        [("organization_id", 1), ("store_id", 1), ("day_of_week", 1)],
    )
    # R3 (audit scalabilita' 10/7) — hot path del catalogo servizi:
    # lookup regole per (org, product_id) sul public catalog.
    await availability_rules_collection.create_index(
        [("organization_id", 1), ("product_id", 1)], name="r3_rules_org_product")
    # blocked_slots per prodotto nel range date (checkout servizi)
    await blocked_slots_collection.create_index(
        [("organization_id", 1), ("product_id", 1), ("date", 1)],
        name="r3_blocks_org_product_date", sparse=True)
    await blocked_slots_collection.create_index("organization_id")
    await blocked_slots_collection.create_index(
        [("organization_id", 1), ("date", 1)],
    )
    await blocked_slots_collection.create_index(
        [("organization_id", 1), ("store_id", 1), ("date", 1)],
    )
    await blocked_slots_collection.create_index("reference_id", sparse=True)
    await blocked_slots_collection.create_index(
        [("organization_id", 1), ("product_id", 1), ("date", 1)],
    )

    # ── v13.0: Coupons ─────────────────────────────────────────────────
    await coupons_collection.create_index("organization_id")
    await coupons_collection.create_index(
        [("organization_id", 1), ("code", 1)], unique=True,
    )
    await coupons_collection.create_index(
        [("organization_id", 1), ("store_ids", 1)],
    )

    # ── R5: coupon redemptions per-customer ─────────────────────────────
    # Unique → un cliente non può redimere lo stesso coupon due volte.
    # customer_key = customer_account_id se loggato, altrimenti email lower.
    await coupon_redemptions_collection.create_index(
        [("organization_id", 1), ("coupon_id", 1), ("customer_key", 1)],
        unique=True,
    )
    # Lookup per rollback su cancellazione ordine.
    await coupon_redemptions_collection.create_index(
        [("organization_id", 1), ("order_id", 1)],
    )

    # ── F1: Newsletter forms + subscriptions ────────────────────────────
    await newsletter_forms_collection.create_index("organization_id")
    # slug unico per org (identità del form nell'org).
    await newsletter_forms_collection.create_index(
        [("organization_id", 1), ("slug", 1)], unique=True,
    )
    # Lookup pubblico per slug (submit endpoint + CORS resolution).
    await newsletter_forms_collection.create_index("slug")
    await newsletter_subscriptions_collection.create_index("organization_id")
    await newsletter_subscriptions_collection.create_index(
        [("organization_id", 1), ("form_id", 1)],
    )
    # Dedup iscrizione per (form, email): un'email = una riga per form.
    await newsletter_subscriptions_collection.create_index(
        [("organization_id", 1), ("form_id", 1), ("email", 1)], unique=True,
    )

    # ── v12.0: Product-Store association ────────────────────────────────
    await products_collection.create_index(
        [("organization_id", 1), ("store_ids", 1)],
    )

    # ── v12.0: Multi-Store Architecture ─────────────────────────────────
    # Phase 3 (Store consolidation) — slug-index hardening.
    #
    # Two distinct indexes intentionally coexist on `stores_collection`:
    #
    #   1. composite (organization_id, slug) UNIQUE partial
    #         defense-in-depth + fast org-scoped lookups
    #
    #   2. global `slug` UNIQUE partial  (named `slug_1`)
    #         REQUIRED for deterministic public routing. The public URL
    #         scheme `/co/<slug>` carries no org context, so
    #         `_resolve_org()` in routers/public.py queries by slug
    #         alone. Without the global uniqueness guarantee that
    #         find_one() is non-deterministic when two orgs share a slug.
    #
    # Both indexes use a partialFilterExpression on `{slug: {$type: "string"}}`
    # — null / missing slugs (unpublished drafts) bypass the constraint,
    # so multiple orgs can have stores with no slug yet.
    #
    # Historical migration:
    #   Pre-Onda 9.Z the global slug index was `unique=True, sparse=True`.
    #   MongoDB 7's sparse indexes ALSO index explicit `null` values
    #   (only missing fields are excluded), which caused DuplicateKey on
    #   `{slug: null}` after the first store was created without a slug.
    #   The migration to partialFilterExpression fixes that. The script
    #   `scripts/migrate_stores_slug_index.py` (analogous to the
    #   existing `migrate_public_slug_index.py`) performs the one-shot
    #   drop+recreate on existing deployments. This `_ensure_stores_indexes`
    #   helper is the runtime safety net: on startup it inspects the
    #   index spec and only re-creates when the current one is missing
    #   or has the legacy options. Idempotent — safe to call repeatedly.
    await _ensure_stores_indexes()

    # ── v9.0 → v9.1: Customer Identity Foundation (org-scoped) ──────────
    # Drop legacy global email unique index if it exists (v9.0 → v9.1 migration)
    try:
        await customer_accounts_collection.drop_index("email_1")
    except Exception:
        pass  # Index may not exist (fresh deploy or already migrated)
    # Unique per org: same email can exist in different organizations
    await customer_accounts_collection.create_index(
        [("organization_id", 1), ("email", 1)], unique=True
    )
    await customer_accounts_collection.create_index("organization_id")
    await customer_accounts_collection.create_index(
        "verification_token_hash", sparse=True
    )
    await customer_accounts_collection.create_index(
        "reset_token_hash", sparse=True
    )
    # Sparse FK on customers and orders — most records won't have it initially
    await customers_collection.create_index("customer_account_id", sparse=True)
    await orders_collection.create_index("customer_account_id", sparse=True)

    # ── Track S Step 3.2: Idempotency race condition fix ─────────────────
    # UNIQUE index on `digest` is critical for the claim-the-lock pattern
    # in middleware/idempotency.py. Without it, two concurrent requests
    # with the same Idempotency-Key both pass the cache lookup miss check
    # and both proceed to call_next (e.g. both create Stripe orders).
    #
    # The middleware now tries `insert_one({digest, status: pending})`
    # before call_next; the unique index ensures only ONE request wins
    # the race. Losers get DuplicateKeyError and poll for completion.
    #
    # TTL index on expires_at lets MongoDB auto-clean stale records
    # (24h after creation) — keeps the collection bounded without a cron.
    await idempotency_keys_collection.create_index("digest", unique=True)
    # NB: TTL index on ISO string field works because MongoDB compares
    # them lexicographically AND expireAfterSeconds=0 means "expire
    # when expires_at < now" — but TTL only fires when the field is a
    # BSON Date. We store ISO string, so TTL won't auto-clean.
    # Fallback: lookup helper filters expired manually. Acceptable since
    # collection is small (24h window × low write rate).


    # Platform accounts (P1 marketplace) — email unica, token magic, TTL
    from services.platform_account_service import ensure_indexes as _pa_idx
    await _pa_idx()

def close_db():
    client.close()
