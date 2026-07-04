"""Dynamic CORS middleware — Phase 0 Step 7 (2026-05-28).

CORS dinamico per gli endpoint embed/ai-site cross-origin. Legge
``store.allowed_origins[]`` dal DB (con cache 5min) e fa match esatto
sull'``Origin`` header.

Motivazione
===========
Il ``CORSMiddleware`` legacy (server.py:617) usa una whitelist STATICA
da env var ``CORS_ORIGINS``. Per supportare embed widget su 1.000+ siti
merchant, servirebbe modificare env + restart container per ogni nuovo
hostname — non scala.

Questo middleware si attiva SOLO sui prefix:
  - ``/api/public/embed/*``      (Stream A)
  - ``/api/public/ai-site/*``    (Stream B futuro)

Per tutte le altre route, passa through al CORSMiddleware statico
esistente. Zero impatto sul comportamento esistente afianco.app
storefront classic.

Sicurezza
=========
- Match ESATTO sull'Origin (no wildcard, no regex)
- Lookup atomico Mongo (find_one filtra su slug + allowed_origins)
- Cache TTL breve (5min) — modifiche admin si propagano rapidamente
- Audit log on every blocked request (per ops visibility)
- Preflight OPTIONS gestito esplicitamente
- ``Vary: Origin`` header per evitare cache pollution intermedia
- ``Allow-Credentials: true`` permesso solo con Origin specifico
  (mai con ``*`` — viola CORS spec)

Performance
===========
- Cache LRU 256 voci per (slug, origin) tuple
- TTL 5min — bilancia freshness vs DB load
- Skip middleware completamente se path != /api/public/embed|ai-site/*
  → costo trascurabile sulla 99% del traffico
"""

import logging
import re
import time
from typing import Optional, Tuple

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response, PlainTextResponse

from core.embed_preview import decode_preview_token


logger = logging.getLogger(__name__)


# ── Metrics hook (Phase 0 Step 10) ───────────────────────────────────────
# Soft import: if observability package not loaded, fall back to no-op so
# the middleware test suite doesn't need to mock the metrics module.

def _record_cors_blocked(path: str, reason: str) -> None:
    """Record a CORS rejection. Wrapper isolates metrics import for testability."""
    try:
        # Derive low-cardinality prefix label from path.
        if "/embed/" in path:
            prefix = "embed"
        elif "/ai-site/" in path:
            prefix = "ai-site"
        elif "/customer-auth/" in path:
            prefix = "customer-auth"
        elif "/customer/" in path:
            prefix = "customer-portal"
        else:
            prefix = "other"
        from core.observability import metrics as _metrics
        _metrics.record_cors_blocked(path_prefix=prefix, reason=reason)
    except Exception:
        # Metrics MUST never break the CORS check — silent soft-fail.
        pass


# ── Path prefixes che attivano il middleware ─────────────────────────────
#
# Phase 0 Step 7: solo /embed/* e /ai-site/* (sito merchant esterno).
# Phase 1 hardening F3 (2026-05-28): aggiunti /customer-auth/* e /customer/*
# perché Stream A merchants embedderanno anche la "MyArea" cliente (signup,
# login, profilo, ordini) sul proprio dominio. Senza il middleware questi
# endpoint userebbero solo il CORSMiddleware statico (allow_origins env-fissa),
# impedendo agli embed widget di chiamarli cross-origin.

DYNAMIC_CORS_PATHS = (
    "/api/public/embed/",
    "/api/public/ai-site/",
    "/api/customer-auth/",
    "/api/customer/",
)


# ── Cache per (slug, origin) → allowed bool ──────────────────────────────


_CACHE: dict[Tuple[str, str], Tuple[bool, float]] = {}
_CACHE_TTL_SECONDS = 5 * 60  # 5 minuti
_CACHE_MAX_ENTRIES = 256


def _cache_lookup(slug: str, origin: str) -> Optional[bool]:
    """Read cache; return None if expired or absent."""
    key = (slug, origin)
    cached = _CACHE.get(key)
    if not cached:
        return None
    allowed, ts = cached
    if time.monotonic() - ts > _CACHE_TTL_SECONDS:
        # Expired — purge + miss
        _CACHE.pop(key, None)
        return None
    return allowed


def _cache_store(slug: str, origin: str, allowed: bool) -> None:
    """Write cache; LRU-evict oldest if over capacity."""
    if len(_CACHE) >= _CACHE_MAX_ENTRIES:
        # Simple LRU: pop the entry with the smallest timestamp.
        # O(n) per insert when full — acceptable for 256 entries.
        oldest_key = min(_CACHE, key=lambda k: _CACHE[k][1])
        _CACHE.pop(oldest_key, None)
    _CACHE[(slug, origin)] = (allowed, time.monotonic())


def clear_cache() -> None:
    """Public helper for tests + admin tooling (manual cache flush)."""
    _CACHE.clear()


# ── Slug extraction from request path ────────────────────────────────────

# Pattern: URL path-based slug extraction per gli endpoint embed/ai-site
# che hanno lo slug come path parameter posizionale.
#
# CRITICO — Perche' necessario:
#   ``BaseHTTPMiddleware.dispatch`` runs BEFORE FastAPI routing matches.
#   Pertanto ``request.path_params`` e' SEMPRE vuoto qui (no routing yet).
#   Inoltre i browser NON inviano custom headers (X-Afianco-Store-Slug)
#   sui preflight OPTIONS — solo i CORS standard headers passano.
#
#   Senza path parsing diretto, l'unico slug-signal disponibile sul
#   preflight e' la URL path stessa. Le regex sotto sono il primary
#   signal per i preflight CORS dei browser.
#
# Slug regex: 3-50 char, alphanumeric + hyphen (matches Pydantic Store.slug).
_SLUG_FRAGMENT = r"([a-z0-9][a-z0-9-]{2,49})"

_SLUG_PATH_PATTERNS: Tuple[re.Pattern, ...] = (
    # /api/public/embed/{op}/{slug} where op ∈ {init, categories, products}
    re.compile(rf"^/api/public/embed/(?:init|categories|products)/{_SLUG_FRAGMENT}(?:/|$)"),
    # /api/public/embed/price-preview/{slug}  — E2.4.10
    re.compile(rf"^/api/public/embed/price-preview/{_SLUG_FRAGMENT}(?:/|$)"),
    # /api/public/embed/coupons/validate/{slug}  — E4.1
    re.compile(rf"^/api/public/embed/coupons/validate/{_SLUG_FRAGMENT}(?:/|$)"),
    # /api/public/embed/shipping-options/{slug}  — E4.2
    re.compile(rf"^/api/public/embed/shipping-options/{_SLUG_FRAGMENT}(?:/|$)"),
    # /api/public/ai-site/{op}/{slug} — Stream B future routes
    re.compile(rf"^/api/public/ai-site/(?:init|categories|products)/{_SLUG_FRAGMENT}(?:/|$)"),
)


def _slug_from_path(path: str) -> Optional[str]:
    """Estrae lo slug dalla URL path se match uno dei pattern noti.

    Usato come primary signal dal middleware (path_params non disponibile
    pre-routing in BaseHTTPMiddleware + custom headers non disponibili
    su preflight OPTIONS).

    Returns:
        Slug string se match, ``None`` altrimenti.
    """
    for pat in _SLUG_PATH_PATTERNS:
        m = pat.match(path)
        if m:
            return m.group(1)
    return None


# ── Newsletter embed (F2): risoluzione per form_id (non store-slug) ───────
# Il form newsletter è una risorsa org-scoped con allowed_origins PROPRI,
# eventualmente NON legata a uno store. L'identità embed è il form_id (uuid
# globalmente unico), usato nel path. Per il CORS lo trattiamo come identità
# prefissata "nlform:{id}" così riusa tutto il flusso dispatch + cache, ma il
# lookup va su ``newsletter_forms`` invece che su ``stores``.
_FORM_ID_FRAGMENT = r"([A-Za-z0-9][A-Za-z0-9_-]{2,63})"
_NEWSLETTER_FORM_PREFIX = "nlform:"
_NEWSLETTER_PATH_RE = re.compile(
    rf"^/api/public/embed/newsletter/{_FORM_ID_FRAGMENT}(?:/|$)"
)


def _form_id_from_path(path: str) -> Optional[str]:
    """Estrae il form_id dai path embed newsletter, altrimenti None."""
    m = _NEWSLETTER_PATH_RE.match(path)
    return m.group(1) if m else None


def _extract_slug(request: Request) -> Optional[str]:
    """Extract the store slug from the request.

    Strategy (in order — fallback chain):
      1. URL path regex (e.g. /api/public/embed/init/{slug}) — PRIMARY
         signal, works pre-routing in BaseHTTPMiddleware + on preflight
         OPTIONS dove i custom headers non sono disponibili.
      2. ``request.path_params`` — fallback per consistency (raramente
         popolato in middleware, ma teoricamente possibile con routing
         middleware-stack diverso).
      3. Query param ``?slug=...`` — usato dal SDK per routes senza slug
         in path (cart, checkout) per garantire preflight visibility.
      4. Header ``X-Afianco-Store-Slug`` — Stream A SDK convention per
         le richieste reali (NB: invisible su preflight OPTIONS).

    Returns ``None`` se nessuno trovato → request bloccata 403.
    """
    # 0. Newsletter embed (F2): identità = form_id (lookup su newsletter_forms).
    form_id = _form_id_from_path(request.url.path)
    if form_id:
        return f"{_NEWSLETTER_FORM_PREFIX}{form_id}"

    # 1. URL path parsing (PRIMARY — works on preflight + real request)
    slug = _slug_from_path(request.url.path)
    if slug:
        return slug

    # 2. Path parameter (FastAPI populates path_params on the request via routing)
    if request.path_params and "slug" in request.path_params:
        return request.path_params["slug"]

    # 3. Query param
    slug = request.query_params.get("slug")
    if slug:
        return slug

    # 4. Header (Stream A convention — NB: invisible on preflight OPTIONS)
    return request.headers.get("X-Afianco-Store-Slug")


# ── Origin → allowlist lookup ────────────────────────────────────────────


def _preview_method_ok(request: Request, method: str) -> bool:
    """True se la richiesta e' una LETTURA ammissibile per il bypass preview.

    GET diretto, oppure preflight OPTIONS il cui metodo richiesto e' GET.
    Tutto il resto (POST/PATCH/DELETE) → no bypass (preview read-only).
    """
    if method == "GET":
        return True
    if method == "OPTIONS":
        return (
            request.headers.get("Access-Control-Request-Method", "").upper() == "GET"
        )
    return False


async def _preview_token_authorizes(token: str, slug: str) -> bool:
    """B2 — Autorizza il bypass preview SOLO se il token e': valido (firma+exp+typ),
    per QUESTO slug, E con ``store_id`` corrispondente allo store REALE dello slug.

    Verificare lo store_id (e non solo lo slug) rende esplicita e difesa la
    dipendenza dall'unicita' globale dello slug: se in futuro lo slug non fosse
    piu' globalmente unico, un token resterebbe comunque legato al suo store.
    """
    payload = decode_preview_token(token)
    if not payload or payload.get("slug") != slug:
        return False
    token_store_id = payload.get("store_id")
    if not token_store_id:
        return False
    try:
        from database import stores_collection
        doc = await stores_collection.find_one(
            {"slug": slug, "is_active": True}, {"_id": 0, "id": 1}
        )
    except Exception as exc:
        logger.warning("DynamicCORS preview store lookup failed slug=%s: %s", slug, exc)
        return False
    return bool(doc) and doc.get("id") == token_store_id


async def _is_origin_allowed(slug: str, origin: str) -> bool:
    """Check if (slug, origin) is in the allowlist.

    Lookup atomico su Mongo. Filtra esattamente:
      stores_collection.find_one({slug, allowed_origins: origin})

    Returns True solo se trovato.
    """
    cached = _cache_lookup(slug, origin)
    if cached is not None:
        return cached

    # Mongo lookup — newsletter form (F2) vs store (default).
    try:
        if slug.startswith(_NEWSLETTER_FORM_PREFIX):
            form_id = slug[len(_NEWSLETTER_FORM_PREFIX):]
            from database import newsletter_forms_collection
            doc = await newsletter_forms_collection.find_one(
                {
                    "id": form_id,
                    "is_active": True,
                    "allowed_origins": origin,
                },
                {"_id": 0, "id": 1},
            )
        else:
            from database import stores_collection
            doc = await stores_collection.find_one(
                {
                    "slug": slug,
                    "is_active": True,
                    "allowed_origins": origin,
                },
                {"_id": 0, "id": 1},
            )
        allowed = doc is not None
    except Exception as exc:
        logger.warning(
            "DynamicCORS: allowlist lookup failed id=%s origin=%s: %s",
            slug, origin, exc,
        )
        allowed = False

    _cache_store(slug, origin, allowed)
    return allowed


# ── Middleware ───────────────────────────────────────────────────────────


class DynamicCORSMiddleware(BaseHTTPMiddleware):
    """Custom CORS middleware for embed/ai-site routes.

    Behavior matrix:

      path NOT in DYNAMIC_CORS_PATHS
        → passthrough (legacy CORSMiddleware handles)

      path IN DYNAMIC_CORS_PATHS, no Origin header
        → reject 400 (same-origin not allowed on embed paths)

      path IN, Origin present, slug missing
        → reject 400

      path IN, Origin present, slug present, origin NOT in allowlist
        → reject 403 + audit log

      path IN, Origin present, slug present, origin IN allowlist
        → preflight OPTIONS → 204 with full CORS headers
        → real request → pass through, inject CORS headers on response
    """

    # ── Paths che richiedono SEMPRE l'enforcement (embed/ai-site) ──────
    # Sono percorsi che NON esistono nel mondo afianco.app legacy: una
    # richiesta su /api/public/embed/* può venire SOLO da un sito merchant
    # esterno. Quindi qui esigiamo Origin + slug sempre.
    _STRICT_PATHS = ("/api/public/embed/", "/api/public/ai-site/")

    # ── Top-level navigation bypass paths (Phase 1 Step 17) ────────────
    # Pagine HTML servite come redirect target da provider esterni
    # (es. Stripe Checkout → /api/public/embed/checkout/complete).
    # I browser NON includono Origin header su navigation cross-origin
    # top-level — il middleware rifiuterebbe ogni redirect Stripe.
    # Questi path hanno propria sicurezza (server-derived target origin,
    # CSP rigoroso, no PII leak) → safe da escludere dall'Origin check.
    _NAVIGATION_BYPASS_PATHS = (
        "/api/public/embed/checkout/complete",
    )

    # ── Paths "opt-in" dell'embed (Phase 1 F3) ─────────────────────────
    # /api/customer-auth/* e /api/customer/* esistono già e sono usati
    # dall'admin SPA su afianco.app (stessa origine del backend o gestita
    # dal CORSMiddleware statico). Quindi attiviamo il middleware solo
    # quando la richiesta DICHIARA esplicitamente di essere un embed:
    #   - header X-Afianco-Store-Slug presente, OPPURE
    #   - query param ?slug=... presente, OPPURE
    #   - path contiene un parametro `slug`
    # In tutti gli altri casi (chiamate da afianco.app stessa) passa
    # through al CORSMiddleware statico, preservando il comportamento
    # storico zero-breaking.

    async def dispatch(self, request: Request, call_next):
        path = request.url.path

        # Fast path: not in scope
        if not any(path.startswith(p) for p in DYNAMIC_CORS_PATHS):
            return await call_next(request)

        # Navigation bypass (Phase 1 Step 17): top-level redirect pages
        # have their own security (server-derived origin, CSP, no PII).
        if path in self._NAVIGATION_BYPASS_PATHS:
            return await call_next(request)

        # Opt-in guard per i percorsi non-strict (Phase 1 F3):
        # se NON c'è uno slug dichiarato esplicitamente, presumiamo che
        # la chiamata sia same-origin dall'admin SPA → passthrough.
        is_strict = any(path.startswith(p) for p in self._STRICT_PATHS)
        if not is_strict:
            slug_signal = _extract_slug(request)
            if not slug_signal:
                # Nessun signal di embed → bypass al CORSMiddleware statico
                return await call_next(request)

        origin = request.headers.get("Origin")
        method = request.method.upper()

        # Same-origin requests (no Origin header) are NOT expected on embed
        # paths — they should come from a third-party site only.
        if not origin:
            logger.info(
                "DynamicCORS: rejected path=%s reason=no_origin_header",
                path,
            )
            _record_cors_blocked(path, reason="no_origin_header")
            # Track S Step 3.5: body opaco "Forbidden" — pre-fix rivelava
            # path scoping ("embed endpoints"). Logger server-side mantiene
            # il dettaglio per debug.
            return PlainTextResponse(
                content="Forbidden",
                status_code=403,
            )

        # Extract slug for lookup
        slug = _extract_slug(request)
        if not slug:
            _record_cors_blocked(path, reason="slug_missing")
            # Track S Step 3.5: body opaco — pre-fix rivelava strategie
            # di slug extraction (path/query/header).
            return PlainTextResponse(
                content="Forbidden",
                status_code=403,
            )

        # Lookup allowlist
        allowed = await _is_origin_allowed(slug, origin)

        # Fase 5 — bypass READ-ONLY via preview token (anteprima admin del
        # proprio store). Vale solo per GET (init/products/categories) e per
        # il preflight OPTIONS di un GET. Non tocca l'allowlist pubblica e non
        # consente mutazioni (cart/checkout POST restano bloccate).
        if not allowed:
            preview_token = (
                request.headers.get("X-Afianco-Preview-Token")
                or request.query_params.get("preview_token")
            )
            if (
                preview_token
                and _preview_method_ok(request, method)
                and await _preview_token_authorizes(preview_token, slug)
            ):
                allowed = True

        if not allowed:
            logger.warning(
                "DynamicCORS: blocked origin=%s slug=%s path=%s method=%s",
                origin, slug, path, method,
            )
            _record_cors_blocked(path, reason="origin_not_allowed")
            # Track S Step 3.5: body opaco identico per tutti i 3 reject
            # path — pre-fix esponeva origin + slug nel body, permettendo
            # all'attacker di:
            #   1. Confermare via body diff "questo slug esiste vs no"
            #   2. Estrarre lista degli origin tentati (utile per analytics
            #      di attack pattern)
            # Logger server-side preserva i dettagli per SOC alerting.
            return PlainTextResponse(
                content="Forbidden",
                status_code=403,
            )

        # ── Allowed — handle preflight separately ──
        if method == "OPTIONS":
            # Preflight: short-circuit con CORS headers, no call_next
            return Response(
                status_code=204,
                headers={
                    "Access-Control-Allow-Origin": origin,
                    "Access-Control-Allow-Methods": "GET, POST, PUT, PATCH, DELETE, OPTIONS",
                    "Access-Control-Allow-Headers": (
                        "Content-Type, Authorization, "
                        "Idempotency-Key, X-Afianco-Store-Slug, "
                        "X-Afianco-Preview-Token"
                    ),
                    "Access-Control-Allow-Credentials": "true",
                    "Access-Control-Max-Age": "600",
                    "Vary": "Origin",
                },
            )

        # ── Real request — call downstream + inject headers on response ──
        response = await call_next(request)
        response.headers["Access-Control-Allow-Origin"] = origin
        response.headers["Access-Control-Allow-Credentials"] = "true"
        # Vary: Origin — critical for downstream caches (Cloudflare, CDN)
        # so they don't serve a cached response with the wrong Allow-Origin.
        existing_vary = response.headers.get("Vary", "")
        if "Origin" not in existing_vary:
            response.headers["Vary"] = (
                f"{existing_vary}, Origin".lstrip(", ") if existing_vary else "Origin"
            )
        return response
