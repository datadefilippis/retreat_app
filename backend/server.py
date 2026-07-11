from fastapi import FastAPI
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
import os
import logging
from pathlib import Path
from contextlib import asynccontextmanager

ROOT_DIR = Path(__file__).parent
# Track S Step 1.4: override=False — shell env vars (container deploy) prendono
# precedenza sul .env file. In dev funziona uguale perche' shell vars non sono
# set, dotenv riempie. In production container deploy, ENVIRONMENT=production
# nella shell vince sull'eventuale .env stale incluso per errore nell'immagine.
load_dotenv(ROOT_DIR / '.env', override=False)

# ── Observability (Phase 1 — Steps A1 + A3) ──────────────────────────────────
# Order matters:
#   1. init_sentry() must happen BEFORE FastAPI() and router imports so that
#      exceptions during app boot / lifespan are captured.
#   2. init_logging() must run BEFORE any logger.info/warning/error in this
#      module, so the formatter is in place from the very first record.
# Both are opt-in via env: SENTRY_DSN, LOG_FORMAT — missing → silent disable.
from core.observability import init_sentry, init_logging
init_sentry()
init_logging()

# ── Legacy routers (unchanged) ────────────────────────────────────────────────
from routers import auth, organizations, modules, purchases, fixed_costs, sales, expenses
# NOTE: customers_light legacy package removed during Phase-3 single-brain
# consolidation. Its identity (module_key="customers_light") is preserved
# inside customer_insights/__init__.py — orgs activations, pricing plans,
# and AI tool dispatch all keep working under the same key.
from modules.customer_insights import router as customer_insights_router
from modules.product_catalog.router import router as product_catalog_router
import importlib as _il; _il.import_module("modules.commerce")  # gate module, registers on import

# ── Phase-3 new routers ───────────────────────────────────────────────────────
from routers import customers, suppliers, products, purchase_records, fixed_costs, column_mappings
from routers import catalog as catalog_router
from routers import tickets as tickets_router

# ── Phase-4 new routers ───────────────────────────────────────────────────────
from routers import preferences

# ── System Admin control panel (v2.9) ────────────────────────────────────────
# All routes in this router are protected by require_system_admin.
# Org-level users (admin, user) cannot reach /api/admin/* — they receive 403.
from routers import admin as admin_router
from routers import admin_catalog as admin_catalog_router
from routers import admin_feature_flags as admin_feature_flags_router
from routers import admin_platform as admin_platform_router
from routers import articles as articles_router
from routers import tracking as tracking_router
from routers import export as export_router
from routers import billing as billing_router
from routers import orders as orders_router
from routers import coupons as coupons_router
from routers import public as public_router
# Phase 1 Step 12 (2026-05-28) — Embed widget public surface (Stream A)
from routers import embed_public as embed_public_router
from routers import event_occurrences as event_occurrences_router
from routers import service_options as service_options_router
from routers import shipping_options as shipping_options_router
from routers import product_extras as product_extras_router
from routers import issued_reservations as issued_reservations_router
from routers import issued_bookings as issued_bookings_router
from routers import issued_downloads as issued_downloads_router
from routers import calendar as calendar_router
from routers import data_integrity as data_integrity_router
# Release 4 (Courses) Step 2 — admin CRUD for video courses
from routers import courses as courses_router
from routers import payment_connections as payment_connections_router
from routers import payment_diagnostics as payment_diagnostics_router
from routers import payments as payments_router
from routers import store_settings as store_settings_router
from routers import stores as stores_router
# Track E Step 2.2 — Per-store embed configuration (snippet + allowed_origins)
# Separato da stores.py per modularity (single responsibility "embed config").
from routers import store_embed as store_embed_router
from routers import newsletter_forms as newsletter_forms_router
# Wave GDPR-Commerce CG-3 — admin endpoints for per-store merchant legal docs
from routers import store_legal as store_legal_router
from routers import availability as availability_router
from routers import customer_auth as customer_auth_router
from routers import platform_accounts as platform_accounts_router
from routers import seo as seo_router
from routers import seo_shell as seo_shell_router
from routers import reviews as reviews_router
from routers import outreach as outreach_router
from routers import cashflow as cashflow_router
from routers import customer_portal as customer_portal_router
# Phase 1 Step A4 — healthcheck endpoints for load balancer / uptime monitor
from routers import health as health_router
# Phase 1 Step B2 — Brevo transactional email webhook (bounce/complaint)
from routers.webhooks import brevo as brevo_webhook_router
# Wave 8E.2 (2026-05): routers/ai_store.py removed — endpoint had zero
# frontend callers (the 5 wizard endpoints were already removed
# 2026-05-09; the remaining enrich-product had its frontend caller
# silently removed in a later commit, leaving the endpoint dormant).
from routers import store_progress as store_progress_router
# Fase 2 Track F — dynamic merchant onboarding wizard. Read-only endpoint
# at /api/setup/wizard. Coexists with /api/store/setup-progress (legacy).
from routers import setup_wizard as setup_wizard_router
from routers.auth import limiter  # shared rate limiter instance

from database import create_indexes, close_db
from seed import seed_demo_data
from services import background_service
from services.seed_pricing import (
    seed_pricing_plans_if_empty, migrate_pricing_plans,
    ensure_pricing_plans_exist, migrate_plan_redesign_v1,
    migrate_trial_only_core, migrate_plan_limits_v2,
    migrate_plan_relaunch_v5,
)
from services.seed_commercial_plans import seed_commercial_plans
from repositories.usage_repository import backfill_module_key as backfill_usage_module_key
from repositories.usage_repository import setup_indexes as setup_usage_indexes


@asynccontextmanager
async def lifespan(app: FastAPI):
    # ── Startup ───────────────────────────────────────────────────────────────
    # Phase 1 Step A3 — re-apply logging config inside the worker's lifespan.
    # gunicorn replaces root.handlers DURING worker boot (between module import
    # and lifespan), so the JsonFormatter installed at module-load is wiped.
    # Re-applying here, AFTER gunicorn has set up its handlers, attaches our
    # formatter to whatever handlers exist now and is the only point at which
    # subsequent application logs (seed, migrations, request handlers) come out
    # in JSON. Idempotent: same call as the module-level one.
    try:
        from core.observability import init_logging as _li
        _li()
    except Exception as _e:
        logging.warning("lifespan init_logging() failed: %s", _e)

    await create_indexes()
    # Seed pricing plans (idempotent — runs in all environments)
    try:
        await seed_pricing_plans_if_empty()
    except Exception as e:
        logging.error(f"Failed to seed pricing plans: {e}")
    # Migrate existing plan limits to current feature_keys (idempotent)
    try:
        await migrate_pricing_plans()
        # MD1 — organization_modules allineate al piano (self-healing)
        from services.plan_provisioning import reconcile_all_module_activations
        await reconcile_all_module_activations()
        # MD3 — via la promessa vuota dal Pro nei DB esistenti
        from services.seed_pricing import migrate_retreat_pro_features_md3
        await migrate_retreat_pro_features_md3()
    except Exception as e:
        logging.error(f"Failed to migrate pricing plans: {e}")
    # Ensure all pricing plans exist (inserts missing slugs individually)
    try:
        await ensure_pricing_plans_exist()
    except Exception as e:
        logging.error(f"Failed to ensure pricing plans: {e}")
    # Seed commercial plans (idempotent upsert -- runs in all environments)
    try:
        await seed_commercial_plans()
    except Exception as e:
        logging.error(f"Failed to seed commercial plans: {e}")
    # One-time migration: plan redesign v1 (idempotent, flag-gated)
    try:
        await migrate_plan_redesign_v1()
    except Exception as e:
        logging.error(f"Failed to run plan redesign migration: {e}")
    # One-time migration: trial only on Core plan
    try:
        await migrate_trial_only_core()
    except Exception as e:
        logging.error(f"Failed to run trial-only-core migration: {e}")
    # One-time migration: plan limits v2 (AI chat per plan)
    try:
        await migrate_plan_limits_v2()
    except Exception as e:
        logging.error(f"Failed to run plan limits v2 migration: {e}")
    # v5.8 / Onda 5: plan relaunch — rebrand 5 plans + grandfather lock for
    # existing orgs with active Stripe subscriptions. Runs ONCE (flag-gated).
    try:
        await migrate_plan_relaunch_v5()
    except Exception as e:
        logging.error(f"Failed to run plan relaunch v5 migration: {e}")
    # v5.2: Validate free plan integrity — must exist with all 4 module mappings.
    # This is a sanity check for a billing invariant: every org defaults to "free",
    # so the free plan MUST be present and complete, or downgrades/cancellations break.
    try:
        from repositories import billing_repository as _br
        free_plan = await _br.get_commercial_plan("free")
        _required_modules = {"cashflow_monitor", "ai_assistant", "product_catalog", "customers_light"}
        if not free_plan:
            logging.critical("BILLING INVARIANT VIOLATED: 'free' commercial plan not found in DB after seeding!")
        elif _required_modules - set(free_plan.get("module_plans", {}).keys()):
            missing = _required_modules - set(free_plan.get("module_plans", {}).keys())
            logging.critical("BILLING INVARIANT VIOLATED: 'free' plan missing module_plans: %s", missing)
        else:
            logging.info("Free plan integrity check passed (%d module mappings)", len(free_plan["module_plans"]))
    except Exception as e:
        logging.error(f"Free plan integrity check failed: {e}")
    # Backfill module_key on legacy usage events (idempotent, fast no-op after first run)
    try:
        await backfill_usage_module_key()
    except Exception as e:
        logging.error(f"Failed to backfill usage module_key: {e}")
    # Wave 8A.1 — ensure dashboard indices on ai_usage_events.
    # Idempotent: Mongo skips create_index when an index with the same
    # spec already exists. Non-fatal: warns and continues on any single
    # index failure so a missing privilege does not block server boot.
    try:
        await setup_usage_indexes()
    except Exception as e:
        logging.error(f"Failed to set up AI usage indices: {e}")
    # Onda 16 Fase 6: warn when legacy item_type=booking products still exist.
    # Informational only — not a migration — nudges the operator to run
    # `python scripts/migrate_booking_to_rental_slot.py` at their convenience.
    try:
        from database import products_collection
        _leftover = await products_collection.count_documents({"item_type": "booking"})
        if _leftover > 0:
            logging.warning(
                "Onda 16 Fase 6: %d product(s) still use deprecated item_type=booking. "
                "Run `python scripts/migrate_booking_to_rental_slot.py` to finalize migration.",
                _leftover,
            )
    except Exception as e:
        logging.error(f"Failed to count deprecated booking products: {e}")
    # v14.0: Backfill store_id on orders that don't have it (idempotent)
    try:
        from database import orders_collection, stores_collection
        # For each org with orders missing store_id, assign the default store
        orgs_with_missing = await orders_collection.distinct(
            "organization_id",
            {"$or": [{"store_id": None}, {"store_id": {"$exists": False}}]},
        )
        for _org_id in orgs_with_missing:
            default_store = await stores_collection.find_one(
                {"organization_id": _org_id, "is_default": True, "is_active": True},
                {"_id": 0, "id": 1},
            )
            if default_store:
                result = await orders_collection.update_many(
                    {"organization_id": _org_id, "$or": [{"store_id": None}, {"store_id": {"$exists": False}}]},
                    {"$set": {"store_id": default_store["id"]}},
                )
                if result.modified_count > 0:
                    logging.info("Backfilled store_id on %d orders for org=%s", result.modified_count, _org_id[:8])
    except Exception as e:
        logging.error(f"Failed to backfill order store_id: {e}")
    # v14.0: Backfill supplier entities from existing purchase records (idempotent)
    try:
        from database import purchase_records_collection
        from repositories import supplier_repository as _supp_repo
        _orgs_with_purchases = await purchase_records_collection.distinct("organization_id")
        for _org_id in _orgs_with_purchases:
            _unlinked_names = await purchase_records_collection.distinct(
                "supplier_name",
                {"organization_id": _org_id, "$or": [{"supplier_id": None}, {"supplier_id": {"$exists": False}}]},
            )
            _created = 0
            for _name in _unlinked_names:
                if _name and _name.strip():
                    try:
                        await _supp_repo.get_or_create_by_name(_org_id, _name)
                        _created += 1
                    except Exception:
                        pass
            if _created:
                logging.info("Backfilled %d supplier entities for org=%s", _created, _org_id[:8])
            # Retroactive link: assign supplier_id to unlinked purchase records
            _unlinked_count = await purchase_records_collection.count_documents(
                {"organization_id": _org_id, "$or": [{"supplier_id": None}, {"supplier_id": {"$exists": False}}]},
            )
            if _unlinked_count > 0:
                from services.entity_resolver import build_supplier_name_map, resolve_by_name
                _supp_map = await build_supplier_name_map(_org_id)
                if _supp_map:
                    _linked = 0
                    async for _rec in purchase_records_collection.find(
                        {"organization_id": _org_id, "$or": [{"supplier_id": None}, {"supplier_id": {"$exists": False}}]},
                        {"_id": 0, "id": 1, "supplier_name": 1},
                    ):
                        _sid = resolve_by_name(_supp_map, _rec.get("supplier_name", ""))
                        if _sid:
                            await purchase_records_collection.update_one(
                                {"id": _rec["id"], "organization_id": _org_id},
                                {"$set": {"supplier_id": _sid}},
                            )
                            _linked += 1
                    if _linked:
                        logging.info("Retroactive-linked supplier_id on %d purchase records for org=%s", _linked, _org_id[:8])
    except Exception as e:
        logging.error(f"Failed to backfill supplier entities: {e}")
    # v5.7: Warn when Stripe is configured but webhook secret is missing.
    if os.environ.get("STRIPE_SECRET_KEY") and not os.environ.get("STRIPE_WEBHOOK_SECRET"):
        logging.warning(
            "STRIPE_SECRET_KEY is set but STRIPE_WEBHOOK_SECRET is missing. "
            "Stripe billing webhooks will be rejected. "
            "For local dev: stripe listen --forward-to http://localhost:8000/api/billing/webhooks"
        )
    if os.environ.get("STRIPE_SECRET_KEY") and not os.environ.get("STRIPE_WEBHOOK_SECRET_CONNECT"):
        logging.info(
            "STRIPE_WEBHOOK_SECRET_CONNECT is missing while STRIPE_SECRET_KEY is set. "
            "Commerce payment webhooks (Stripe Connect Express) will not be verified. "
            "Set up a Connect webhook endpoint on Stripe Dashboard → Developers → Webhooks "
            "→ 'Events on Connected accounts' and copy the signing secret."
        )

    # Fase 5c: log test/live mode mismatch at boot so ops sees it immediately.
    try:
        from services.stripe_mode_guard import check_platform_mode_at_startup
        check_platform_mode_at_startup()
    except Exception as e:
        logging.error("stripe_mode_guard startup check failed: %s", e)

    # Seed demo data in development
    if os.environ.get('ENVIRONMENT', 'development') == 'development':
        try:
            await seed_demo_data()
        except Exception as e:
            logging.error(f"Failed to seed demo data: {e}")

    # Start periodic background jobs (alerts, digests, billing sweep).
    # Tasks are fire-and-forget; errors inside them are caught and logged.
    # Configure via env: BACKGROUND_ALERT_INTERVAL_HOURS (6), BILLING_SWEEP_INTERVAL_HOURS (1).
    bg_tasks = background_service.start()

    # Fase 2 (retreat) — scheduler con lock Mongo per i job pagamenti
    # (dunning, session saldo, promemoria). Disabilitato con ENVIRONMENT=test
    # o SCHEDULER_ENABLED=false. Vedi services/scheduler_service.py.
    try:
        from services.scheduler_service import start_scheduler
        start_scheduler()
    except Exception as e:
        logging.error("scheduler start failed: %s", e)

    yield

    # ── Shutdown ──────────────────────────────────────────────────────────────
    try:
        from services.scheduler_service import stop_scheduler
        await stop_scheduler()
    except Exception:
        pass
    background_service.stop(bg_tasks)
    for task in bg_tasks:
        try:
            await task
        except Exception:
            pass  # CancelledError and any other exception on shutdown are expected
    close_db()


# ── OpenAPI docs exposure (Track S Step 1.3, env-gated) ─────────────────────
# In production/staging i path /docs (Swagger UI), /redoc (ReDoc) e
# /openapi.json non devono essere esposti pubblicamente — espongono
# schema completo (path, payload shapes, response models) che semplifica
# il reverse-engineering della logica business. In dev restano abilitati
# perche' utilissimi per Postman / curl / SDK generation.
#
# Pinned in tests/test_invariants_security.py::TestSEC_S1_3_DocsExposureGated

def _docs_urls_for_env(environment: str | None) -> tuple[str | None, str | None, str | None]:
    """Return (docs_url, redoc_url, openapi_url) gated by environment.

    production/staging → tutti None (FastAPI risponde 404 ai 3 path).
    development/test/unset → default ("/docs", "/redoc", "/openapi.json").

    NB: la funzione e' pure (no side-effect) per essere testabile in
    isolation. La logica di esposizione e' centralizzata qui per evitare
    drift tra config e sentinel test.
    """
    env = (environment or "development").strip().lower()
    if env in ("production", "staging"):
        return (None, None, None)
    return ("/docs", "/redoc", "/openapi.json")


_docs_url, _redoc_url, _openapi_url = _docs_urls_for_env(
    os.environ.get("ENVIRONMENT")
)

# Create the main app
app = FastAPI(
    title="Aurya",
    description="AI-powered business monitoring platform",
    version="2.0.0",
    lifespan=lifespan,
    docs_url=_docs_url,
    redoc_url=_redoc_url,
    openapi_url=_openapi_url,
)

# ── Rate limiting (slowapi) ───────────────────────────────────────────────────
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


# ── Global exception handler (Track S Step 1.4) ──────────────────────────────
# Catch-all per qualunque Exception non gestita da handler specifici. Senza
# questo, FastAPI default ritorna 500 con stacktrace nel body (se debug=True)
# o messaggio generico ma loggato solo via Starlette → noi vogliamo:
#   1. Stacktrace COMPLETO nei log server-side (per debug + Sentry)
#   2. Body OPACO al client: {"detail": "Internal server error"} + request_id
#   3. NO leak di implementation details (path interni, lib versions, ecc.)
#
# Pin: tests/test_invariants_security.py::TestSEC_S1_4_GlobalExceptionHandler
from fastapi import Request as _Req
from fastapi import Response as _Resp
from fastapi.responses import JSONResponse as _JSONResp

_global_handler_logger = logging.getLogger("afianco.global_exception")


async def _global_exception_handler(request: _Req, exc: Exception) -> _JSONResp:
    """Catch-all handler. Body opaco, log server-side completo."""
    # Pull request_id se l'utente ha l'header (lo aggiunge RequestContextMiddleware)
    request_id = request.headers.get("X-Request-ID", "unknown")
    # Log con exc_info=True → stacktrace completo per debug
    _global_handler_logger.error(
        "Unhandled exception on %s %s (req_id=%s): %r",
        request.method,
        request.url.path,
        request_id,
        exc,
        exc_info=True,
    )
    # Body opaco al client — no stacktrace, no detail interno
    return _JSONResp(
        status_code=500,
        content={
            "detail": "Internal server error",
            "request_id": request_id,
        },
    )


app.add_exception_handler(Exception, _global_exception_handler)


# ── Request context middleware (Phase 1 — Step A3) ───────────────────────────
# Generates / reads X-Request-ID per HTTP request, activates correlation_id
# for the asyncio task so every downstream logger.info/etc carries it, and
# echoes the ID back in the response header for client/support correlation.
# Skips noisy paths (/api/health*, /api/metrics) to keep logs clean.
from core.middleware.request_context_middleware import RequestContextMiddleware
app.add_middleware(RequestContextMiddleware)


# ── R5 — security headers baseline ───────────────────────────────────────────
# Header universali e a rischio zero. NIENTE X-Frame-Options globale:
# l'embed SDK vive dentro iframe su siti terzi e lo romperebbe. La CSP
# completa richiede l'audit degli asset → R6 (mini security pass).
@app.middleware("http")
async def _security_headers(request, call_next):
    response = await call_next(request)
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
    response.headers.setdefault(
        "Permissions-Policy", "camera=(), microphone=(), payment=(self)"
    )
    # HSTS solo in produzione (dietro HTTPS): su localhost HTTP il browser
    # lo ignora, ma meglio non insegnare mai il dominio dev al preload.
    if os.environ.get("ENVIRONMENT", "development").lower() == "production":
        response.headers.setdefault(
            "Strict-Transport-Security", "max-age=31536000; includeSubDomains"
        )
    return response

# ── Static files (product images, logos) ─────────────────────────────────────
import os
from fastapi.staticfiles import StaticFiles
_uploads_dir = os.path.join(os.path.dirname(__file__), "uploads")
os.makedirs(os.path.join(_uploads_dir, "products"), exist_ok=True)
os.makedirs(os.path.join(_uploads_dir, "logos"), exist_ok=True)


# Scalability refinement — HTTP cache headers for /uploads/* responses.
#
# Uploaded media (logos, product images) is content-addressed:
# `/uploads/logos/<store_id>.<ext>`. When the merchant replaces a
# logo the file at the same path is OVERWRITTEN. The frontend
# already cache-busts replace via a `?t=<timestamp>` query in the
# admin preview, but the visitor's cached <img> in the storefront
# will still revalidate on its TTL.
#
# Strategy:
#   - max-age=31536000  (1 year) on every response — these files
#                       don't churn often and visitors get instant
#                       repeat loads from the browser cache.
#   - immutable         signal to skip revalidation entirely on
#                       cache hits (Chrome / Firefox / Safari support).
#   - public            allows shared caches (corporate proxies,
#                       Cloudflare/CloudFront edge) to cache too.
#
# Trade-off: when admin RE-uploads with the same extension, old
# clients with a hot cache see the previous file for up to 1 year.
# Mitigation: the admin UI already appends `?t=<timestamp>` to the
# preview <img> after upload (StoresPage.js handles this), and the
# next storefront visitor on a cold cache always gets the fresh file.
# A future improvement: serve a content-hash-suffixed path so the
# URL itself changes on replace (true immutability) — deferred to a
# bigger CDN/migration commit.
class _UploadsCacheControlMiddleware:
    """ASGI middleware that injects Cache-Control on /uploads/* responses.

    Defensive: only mutates the response headers when:
      - path starts with /uploads/
      - status code is 200/304 (no caching for errors / redirects)
      - no Cache-Control already set by upstream

    Note: Starlette's `add_middleware` calls the constructor with
    `app=...` as a keyword argument, so the param name MUST be `app`
    (not `app_`). Original draft used `app_` and crashed startup.
    """
    def __init__(self, app):
        self._app = app

    async def __call__(self, scope, receive, send):
        if scope.get("type") != "http":
            return await self._app(scope, receive, send)
        path = scope.get("path", "")
        if not path.startswith("/uploads/"):
            return await self._app(scope, receive, send)

        async def _send_with_cache(message):
            if message.get("type") == "http.response.start":
                status = message.get("status", 0)
                if status in (200, 304):
                    headers = list(message.get("headers", []))
                    # Skip if upstream already set Cache-Control.
                    has_cc = any(
                        k.lower() == b"cache-control" for k, _ in headers
                    )
                    if not has_cc:
                        headers.append((
                            b"cache-control",
                            b"public, max-age=31536000, immutable",
                        ))
                        message["headers"] = headers
            await send(message)

        await self._app(scope, receive, _send_with_cache)


app.mount("/uploads", StaticFiles(directory=_uploads_dir), name="uploads")
app.add_middleware(_UploadsCacheControlMiddleware)

# ── Legacy routes (prefix /api — do not change) ───────────────────────────────
app.include_router(auth.router, prefix="/api")
app.include_router(organizations.router, prefix="/api")
app.include_router(modules.router, prefix="/api")
app.include_router(customer_insights_router, prefix="/api")  # /api/customer-insights/*
app.include_router(product_catalog_router, prefix="/api")    # /api/modules/product-catalog/*
app.include_router(purchases.router, prefix="/api")
app.include_router(fixed_costs.router, prefix="/api")
app.include_router(sales.router, prefix="/api")
app.include_router(expenses.router, prefix="/api")

# ── Phase-3 routes (new paths — fully backward-compatible) ────────────────────
app.include_router(customers.router, prefix="/api")          # /api/customers
app.include_router(suppliers.router, prefix="/api")          # /api/suppliers
app.include_router(products.router, prefix="/api")           # /api/products
app.include_router(catalog_router.router, prefix="/api")     # /api/catalog/* (P11)
app.include_router(tickets_router.router, prefix="/api")     # /api/tickets/* (E5)
app.include_router(purchase_records.router, prefix="/api")   # /api/purchase-records
app.include_router(column_mappings.router, prefix="/api")    # /api/column-mappings

# ── Phase-4 routes (new paths — fully backward-compatible) ────────────────────
app.include_router(preferences.router, prefix="/api")        # /api/preferences/*

# ── AI Chat route (v2.5) ─────────────────────────────────────────────────────

# ── AI Digest routes (v2.5) ────────────────────────────────────────────────

# ── Export routes (Blocco 1) ─────────────────────────────────────────────────
app.include_router(export_router.router, prefix="/api")      # /api/export/*

# ── System Admin routes (v2.9) ────────────────────────────────────────────────
app.include_router(admin_router.router, prefix="/api")       # /api/admin/*
app.include_router(admin_catalog_router.router, prefix="/api")  # /api/admin/catalog/*
app.include_router(admin_feature_flags_router.router, prefix="/api")  # /api/admin/feature-flags/* (Phase 0 Step 9)
app.include_router(admin_platform_router.router, prefix="/api")  # /api/admin/platform/* (SA2/SA3)
app.include_router(articles_router.router, prefix="/api")  # /api/public/articles + /api/admin/articles (AN5 blog)
app.include_router(tracking_router.router, prefix="/api")  # /api/public/track (VT visibilita)
from routers import leads as leads_router  # noqa: E402
app.include_router(leads_router.router, prefix="/api")  # /api/public/leads + /api/admin/leads (PL2)
from routers import visibility as visibility_router  # noqa: E402
app.include_router(visibility_router.router, prefix="/api")  # /api/analytics/visibility (VT4)

# ── Billing routes (v5.0) ────────────────────────────────────────────────────
app.include_router(billing_router.router, prefix="/api")     # /api/billing/*

# ── Sales Core: Orders (v7.0) ───────────────────────────────────────────────
app.include_router(orders_router.router, prefix="/api")      # /api/orders/*
app.include_router(coupons_router.router, prefix="/api")     # /api/coupons/*

# ── Public Storefront (v7.0) — no auth required ─────────────────────────
app.include_router(public_router.router, prefix="/api")      # /api/public/*

# ── Public Embed Widget (Phase 1 Step 12) — Stream A cross-origin surface
# Mounted dopo public_router così le route /api/public/embed/* sono
# coperte dal DynamicCORSMiddleware (Phase 0 Step 7) e
# IdempotencyMiddleware (Phase 0 Step 8) per le mutazioni future.
app.include_router(embed_public_router.router, prefix="/api")  # /api/public/embed/*

# ── Wave GDPR-Admin Phase C (2026-05-16) — public legal docs ────────────
from routers import legal as legal_router
app.include_router(legal_router.router, prefix="/api")      # /api/legal/{privacy,terms,versions}

# ── Wave GDPR-Commerce Piece 1b (2026-05-19) — public marketing unsubscribe ──
# Tokenised unsubscribe endpoint (no auth) so guest customers can revoke
# marketing consent via a signed link — required by GDPR Art. 7(3).
from routers import marketing_consent as marketing_consent_router
app.include_router(marketing_consent_router.router, prefix="/api")  # /api/marketing-consent/unsubscribe/{token}
app.include_router(event_occurrences_router.router, prefix="/api")  # /api/event-occurrences/*
app.include_router(service_options_router.router, prefix="/api")    # /api/products/{id}/service-options/* (F5 Onda 12)
app.include_router(shipping_options_router.router, prefix="/api")   # /api/shipping-options/* (Shipping feature)
app.include_router(product_extras_router.router, prefix="/api")    # /api/products/{id}/extras/* (Onda 16)
app.include_router(issued_reservations_router.router, prefix="/api")  # /api/issued-reservations/* (Onda 16)
app.include_router(issued_bookings_router.router, prefix="/api")      # /api/issued-bookings/* (Admin order management consolidation)
app.include_router(issued_downloads_router.router, prefix="/api")     # /api/issued-downloads/* (Release 3 — Digital)
app.include_router(courses_router.router, prefix="/api")              # /api/courses/* (Release 4 — Courses)
app.include_router(calendar_router.router, prefix="/api")         # /api/calendar/*
app.include_router(data_integrity_router.router, prefix="/api")  # /api/data-integrity/*
app.include_router(payment_connections_router.router, prefix="/api")  # /api/payment-connections/*
app.include_router(payment_diagnostics_router.router, prefix="/api")   # /api/diagnostics/*
app.include_router(payments_router.router, prefix="/api")              # /api/payments/* (admin readiness)
app.include_router(store_settings_router.router, prefix="/api")      # /api/store-settings/*
app.include_router(stores_router.router, prefix="/api")              # /api/stores/*
# Track E Step 2.2 — per-store embed config sub-resource:
#   GET   /api/stores/{id}/embed-info
#   PATCH /api/stores/{id}/allowed-origins
app.include_router(store_embed_router.router, prefix="/api")         # /api/stores/{id}/embed-*
app.include_router(newsletter_forms_router.router, prefix="/api")    # /api/newsletter-forms/* (F1)
# Wave GDPR-Commerce CG-3 — mounted under same /api/stores prefix so
# routes appear as /api/stores/{id}/legal/* alongside the existing
# CRUD endpoints. The two routers don't share state — they only share
# the URL space.
app.include_router(store_legal_router.router, prefix="/api")         # /api/stores/{id}/legal/*
app.include_router(availability_router.router, prefix="/api")        # /api/availability/*

# ── Customer Identity Foundation (v9.0) ─────────────────────────────────
app.include_router(customer_auth_router.router, prefix="/api")       # /api/customer-auth/*
app.include_router(platform_accounts_router.router, prefix="/api")   # /api/platform/* (P1 marketplace)
app.include_router(seo_router.router, prefix="/api")                  # /api/public/sitemap.xml (F3)
app.include_router(seo_shell_router.router)                            # /__seo/* — HTML pubblico con meta server-side (S0.2)
app.include_router(reviews_router.router, prefix="/api")               # recensioni operatore (PR2)
app.include_router(outreach_router.router, prefix="/api")              # outreach contestuale (CF2)
app.include_router(cashflow_router.router, prefix="/api")              # cashflow consolidato (CF3)
app.include_router(customer_portal_router.router, prefix="/api")     # /api/customer/*
# Phase 1 Step A4 — /api/health/live + /api/health/ready (no auth, for probes)
app.include_router(health_router.router, prefix="/api")              # /api/health/*
# Phase 1 Step B2 — /api/webhooks/brevo (no auth, validated via X-Webhook-Secret header)
app.include_router(brevo_webhook_router.router, prefix="/api")       # /api/webhooks/brevo
# Wave 8E.2: ai_store_router removed (see import block above).
app.include_router(store_progress_router.router, prefix="/api")      # /api/store/setup-progress
app.include_router(setup_wizard_router.router, prefix="/api")        # /api/setup/wizard (Fase 2 Track F)


# Health check endpoint
@app.get("/sitemap.xml", include_in_schema=False)
async def sitemap_xml():
    """Sitemap dinamica (Fase 5): home calendario, categorie, pagine
    categoria×regione con ritiri, landing dei ritiri pubblicati, profili
    operatore. Cresce col calendario — niente file statico da mantenere."""
    from fastapi.responses import Response
    from datetime import datetime, timezone
    from database import event_occurrences_collection, products_collection
    from models.retreat_taxonomy import RETREAT_CATEGORIES
    from services.url_builder import build_public_url

    now_iso = datetime.now(timezone.utc).isoformat()[:16]
    urls = [build_public_url("/ritiri")]
    for cat in RETREAT_CATEGORIES:
        urls.append(build_public_url(f"/ritiri/{cat}"))

    # landing dei ritiri pubblicati futuri + coppie categoria×regione reali
    occs = await event_occurrences_collection.find(
        {"status": "published", "start_at": {"$gte": now_iso}},
        {"_id": 0, "slug": 1, "region": 1, "product_id": 1, "organization_id": 1},
    ).to_list(2000)
    prod_ids = list({o["product_id"] for o in occs})
    prods = await products_collection.find(
        {"id": {"$in": prod_ids}, "is_active": True, "is_published": True},
        {"_id": 0, "id": 1, "category": 1},
    ).to_list(2000)
    cat_by_prod = {p["id"]: p.get("category") for p in prods}

    cat_region_pairs = set()
    for o in occs:
        cat = cat_by_prod.get(o["product_id"])
        if cat and o.get("region"):
            cat_region_pairs.add((cat, o["region"]))
    for cat, region in sorted(cat_region_pairs):
        urls.append(build_public_url(f"/ritiri/{cat}/{region}"))

    from urllib.parse import quote
    body = ['<?xml version="1.0" encoding="UTF-8"?>',
            '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for u in urls:
        body.append(f"  <url><loc>{quote(u, safe=':/')}</loc></url>")
    body.append("</urlset>")
    return Response("\n".join(body), media_type="application/xml")


@app.get("/robots.txt", include_in_schema=False)
async def robots_txt():
    from fastapi.responses import Response
    from services.url_builder import build_public_url
    # SEO5 — le sotto-sitemap vivono sotto /api/public/: senza gli
    # Allow espliciti, "Disallow: /api/" impediva a Googlebot di
    # scaricarle (indice letto, 0 pagine rilevate in Search Console).
    # Regola robots: il percorso piu' lungo vince, quindi questi
    # Allow battono il Disallow generico.
    txt = (
        "User-agent: *\n"
        "Allow: /ritiri\n"
        "Allow: /e/\n"
        "Allow: /o/\n"
        "Allow: /api/public/sitemap-\n"
        "Disallow: /dashboard\n"
        "Disallow: /api/\n"
        f"Sitemap: {build_public_url('/sitemap.xml')}\n"
    )
    return Response(txt, media_type="text/plain")


@app.get("/llms.txt", include_in_schema=False)
async def llms_txt():
    """SEO4/GEO — presentazione del sito per gli assistenti AI.
    Vive in assets/ e passa dal backend perché il proxy instrada
    TUTTI i *.txt di root qui (regola robots/IndexNow)."""
    from pathlib import Path as _Path
    from fastapi.responses import Response
    p = _Path(__file__).resolve().parent / "assets" / "llms.txt"
    try:
        return Response(p.read_text(encoding="utf-8"),
                        media_type="text/plain; charset=utf-8")
    except OSError:
        return Response("# Aurya — https://aurya.life\n",
                        media_type="text/plain; charset=utf-8")


@app.get("/api/health")
async def health_check(verbose: bool = False):
    """Health check with MongoDB + Stripe connectivity verification.

    Returns HTTP 200 when the critical dependency (MongoDB) is reachable;
    returns 503 only when that dependency is down. Optional ?verbose=true
    adds a Stripe API reachability probe and the Stripe platform mode.
    Stripe being unreachable is NOT a 503 — the app must still serve
    non-payment traffic. Its status surfaces only in the per-component
    `checks` object.
    """
    from fastapi.responses import JSONResponse
    import asyncio as _asyncio

    result = {
        "service": "aurya",
        "version": "2.0.0",
        "checks": {},
    }

    # ── MongoDB (critical) ───────────────────────────────────────────────
    try:
        from database import db
        await db.command("ping")
        result["mongodb"] = "connected"
        result["checks"]["mongodb"] = {"status": "ok"}
    except Exception as e:
        result["status"] = "degraded"
        result["mongodb"] = f"error: {str(e)[:100]}"
        result["checks"]["mongodb"] = {"status": "error", "error": str(e)[:200]}
        return JSONResponse(status_code=503, content=result)

    # ── Stripe (non-critical — reported, not failing) ────────────────────
    if verbose:
        try:
            from services.stripe_mode_guard import platform_stripe_mode
            import os
            stripe_mode = platform_stripe_mode()
            if os.environ.get("STRIPE_SECRET_KEY"):
                # Cheap API reachability probe: Balance.retrieve is fast and
                # authenticated with no side effects. 2s hard timeout so a
                # slow Stripe doesn't slow our health endpoint.
                import stripe as _stripe
                _stripe.api_key = os.environ.get("STRIPE_SECRET_KEY")
                async def _probe():
                    return await _asyncio.to_thread(_stripe.Balance.retrieve)
                try:
                    await _asyncio.wait_for(_probe(), timeout=2.0)
                    result["checks"]["stripe"] = {"status": "ok", "mode": stripe_mode}
                except _asyncio.TimeoutError:
                    result["checks"]["stripe"] = {"status": "timeout", "mode": stripe_mode}
                except Exception as sexc:
                    result["checks"]["stripe"] = {
                        "status": "error", "mode": stripe_mode,
                        "error": str(sexc)[:200],
                    }
            else:
                result["checks"]["stripe"] = {"status": "unconfigured", "mode": stripe_mode}
        except Exception as exc:
            # Never fail the health check because of Stripe probe bugs
            result["checks"]["stripe"] = {"status": "probe_error", "error": str(exc)[:200]}

    result["status"] = "healthy"
    return result


# ── Prometheus metrics endpoint (Phase 0 Step 10 + Track S Step 4.1) ────────
# /metrics expone counter/histogram via core.observability.metrics in
# standard Prometheus text format.
#
# Track S Step 4.1 — AUTH via X-Metrics-Token header:
#   · ENVIRONMENT=production o staging:
#       - METRICS_AUTH_TOKEN env var REQUIRED. Missing → 503 (default-deny)
#       - Token wrong or missing in request → 401 uniform "Unauthorized"
#       - Token matching → 200 con metrics body
#   · ENVIRONMENT=development o unset:
#       - Auth disabilitata (dev convenience per Prometheus / Grafana local)
#
# Pre-S4.1: commit msg diceva "internal scrape only, bind to internal
# network" → affidato solo a reverse-proxy ACL. Se per config error
# arriva su internet, espone metriche interne (request counts per path,
# latency, error rates) → info leak per fingerprinting / timing attack.
# Doppia-defense con app-level token + reverse-proxy ACL.
#
# Pin: tests/test_invariants_security.py::TestSEC_S4_1_MetricsAuth

def _metrics_auth_required() -> bool:
    """True in production/staging where /metrics MUST be authenticated."""
    env = (os.environ.get("ENVIRONMENT") or "development").strip().lower()
    return env in ("production", "staging")


# ── R S3 — IndexNow key file (verifica di proprietà del protocollo) ─────────
# Il motore controlla https://host/{key}.txt: il proxy instrada
# /*.txt sconosciuti qui (regola in DEPLOY_CHECKLIST).
@app.get("/indexnow-key.txt", include_in_schema=False)
@app.get("/{key_txt}.txt", include_in_schema=False)
async def indexnow_key_file(key_txt: str = ""):
    from services.indexnow import indexnow_key
    key = indexnow_key()
    if key and (key_txt == key or not key_txt):
        return _Resp(content=key, media_type="text/plain")
    from fastapi import HTTPException as _HTTPExc
    raise _HTTPExc(status_code=404, detail="Not found")


@app.get("/metrics", include_in_schema=False)
async def prometheus_metrics(request: _Req):
    """Prometheus exposition endpoint. Scrape with Prometheus / Grafana Agent.

    Returns text/plain (Prometheus 0.0.4 format). In production/staging
    requires X-Metrics-Token header matching METRICS_AUTH_TOKEN env var.
    In dev no auth required.
    """
    from fastapi.responses import Response, PlainTextResponse

    # Track S Step 4.1 — auth check (prod/staging only)
    if _metrics_auth_required():
        expected = os.environ.get("METRICS_AUTH_TOKEN", "").strip()
        if not expected:
            # Fail-closed: missing config in prod → 503 (default-deny).
            # Operator must explicitly set METRICS_AUTH_TOKEN env var.
            return PlainTextResponse(
                content="Metrics endpoint not configured.",
                status_code=503,
            )
        provided = (request.headers.get("X-Metrics-Token") or "").strip()
        if not provided or provided != expected:
            # Uniform 401 — no leak whether token missing vs wrong.
            # NOTE: timing-safe comparison NOT needed here (token is
            # high-entropy server-side secret; brute-force impractical
            # anyway. If we ever rotate to short tokens, switch to
            # secrets.compare_digest).
            return PlainTextResponse(content="Unauthorized", status_code=401)

    # Auth passed (or dev mode): render metrics
    from core.observability import metrics as _metrics
    body, content_type = _metrics.render_latest()
    return Response(content=body, media_type=content_type)


# ── CORS middleware ───────────────────────────────────────────────────────────
# CORS_ORIGINS must be set explicitly in production.
# Dev fallback: localhost:3000 only (safe default — never "*").
_cors_env = os.environ.get("CORS_ORIGINS", "").strip()
if _cors_env:
    _cors_origins = [o.strip() for o in _cors_env.split(",") if o.strip()]
else:
    _cors_origins = ["http://localhost:3000", "http://localhost:3001"]
    logging.warning(
        "CORS_ORIGINS not set — using localhost fallback. "
        "Set CORS_ORIGINS=https://yourdomain.com in production."
    )

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=_cors_origins,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"],
)

# ── Middleware order rationale (LIFO ⇒ last-added runs first) ────────────
#
# Phase 1 hardening (F1, 2026-05-28): l'ordine originale di Phase 0 era
# CORSMiddleware → DynamicCORSMiddleware → IdempotencyMiddleware ma LIFO
# significa che Idempotency veniva eseguita per PRIMA. Conseguenza: una
# richiesta da Origin non in allowlist riceveva 400 "missing Idempotency-Key"
# prima del 403 di DynamicCORS, e poteva consumare uno slot di cache se
# arrivava completa di header. Ora gli aggiungiamo nell'ordine inverso così
# l'esecuzione effettiva è: DynamicCORS → Idempotency → endpoint.
#
# Ordine di esecuzione effettivo (dopo questo file):
#   1. DynamicCORSMiddleware (Phase 0 Step 7) — reject Origin non in allowlist
#   2. IdempotencyMiddleware (Phase 0 Step 8) — enforce/grace Idempotency-Key
#   3. CORSMiddleware (statico) — fallback per dashboard admin afianco.app
#   4. endpoint handler

# Phase 0 Step 8 — Idempotency middleware.
# Enforcement (400 if missing): /api/public/embed/*, /api/public/ai-site/*
# Grace period 90gg (warning log): /api/public/order-request
# Cache TTL 24h via idempotency_keys_collection.
# Feature flag IDEMPOTENCY_ENFORCED (default ON) per emergency rollback.
from middleware.idempotency import IdempotencyMiddleware  # noqa: E402
app.add_middleware(IdempotencyMiddleware)

# Phase 0 Step 7 — Dynamic CORS per /api/public/embed/*, /api/public/ai-site/*
# e /api/customer-auth/* (aggiunto in Phase 1 hardening F3).
# Lookup store.allowed_origins[] dal DB con cache 5min. Per route fuori scope
# passa through al CORSMiddleware statico (zero impact su admin SPA legacy).
from middleware.dynamic_cors import DynamicCORSMiddleware  # noqa: E402
app.add_middleware(DynamicCORSMiddleware)

# Track E Step 1.5 — Sentry surface=embed auto-tagging per
# /api/public/embed/* paths. Filterable da alert rule O3.1
# [P2] Embed-SDK error spike + inbox triage faster.
from middleware.embed_surface_tag import EmbedSurfaceTagMiddleware  # noqa: E402
app.add_middleware(EmbedSurfaceTagMiddleware)

# Phase 1 Step A3 — logging is configured by core.observability.init_logging()
# at module import time (top of file). The legacy logging.basicConfig + late
# install_correlation_id_logging() block was removed because:
#   1. basicConfig(...) overwrote the JsonFormatter installed by init_logging,
#      collapsing structured logs back to plain text in production.
#   2. install_correlation_id_logging() unconditionally rebuilt the formatter
#      with logging.Formatter, destroying the JsonFormatter even when the
#      CorrelationIdFilter was already installed by init_logging.
# init_logging() now installs the CorrelationIdFilter atomically with the
# formatter, so the previous late-init pattern is no longer needed.
# Re-apply once here to cover the case where uvicorn/gunicorn added new
# handlers AFTER module import (idempotent: replaces formatter on every
# handler so the format is uniform, no matter who registered the handler).
try:
    from core.observability import init_logging as _reapply_logging
    _reapply_logging()
except Exception as _e:
    logging.warning("late init_logging() failed: %s", _e)
logger = logging.getLogger(__name__)
