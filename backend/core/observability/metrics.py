"""Prometheus metrics — Phase 0 Step 10 (2026-05-28).

Counters, gauges e histogrami per la nuova superficie e-commerce.
Tutto opt-in: se ``prometheus-client`` non è installato (es. dev senza
``pip install -r requirements.txt``) il modulo ricade su un no-op shim
e il server boota normalmente.

Public API
==========
``record_cart_op(operation, status, source="storefront")``
    Counter: cart_operations_total{operation, status, source}

``record_order(source, status)``
    Counter: orders_created_total{source, status}

``record_cors_blocked(path_prefix, reason)``
    Counter: cors_blocked_total{path_prefix, reason}

``record_idempotency(result, scope)``
    Counter: idempotency_cache_total{result, scope}
    result ∈ {hit, miss, enforced_reject, grace_warn}

``record_api_latency(endpoint, status, seconds)``
    Histogram: api_response_time_seconds (buckets standard)

``render_latest() -> tuple[bytes, str]``
    Ritorna (body, content_type) per /metrics endpoint.

Design rationale
================
- Labels: cardinalità MOLTO bassa (≤10 valori per dim) → no explosion.
- ``path_prefix`` (es. "embed", "ai-site") NON path completo per evitare
  cardinality explosion da slug merchant variabili.
- Histogram buckets default di prometheus_client (0.005 .. 10s) OK per
  hot path API. NO custom buckets per default (KISS).
- Module-level singletons → init una volta sola, thread-safe by design.
"""

from __future__ import annotations

import logging
from typing import Tuple

logger = logging.getLogger(__name__)


# ── Soft dependency su prometheus_client ────────────────────────────────

try:
    from prometheus_client import (
        Counter,
        Histogram,
        CollectorRegistry,
        generate_latest,
        CONTENT_TYPE_LATEST,
    )
    _PROMETHEUS_AVAILABLE = True
except ImportError:  # pragma: no cover — defensive
    _PROMETHEUS_AVAILABLE = False
    logger.warning(
        "prometheus_client not installed; metrics will be no-op. "
        "Run: pip install prometheus-client"
    )


def is_available() -> bool:
    """True se prometheus_client è importabile."""
    return _PROMETHEUS_AVAILABLE


# ── Metric definitions (lazily-initialized singletons) ──────────────────

if _PROMETHEUS_AVAILABLE:
    # Default registry (process-wide). Re-use per multi-worker scenarios:
    # uvicorn workers ognuno mantiene il proprio registry → Prometheus
    # scrape al worker singolo. Per multi-worker production, use
    # PROMETHEUS_MULTIPROC_DIR + multiprocess collector (futuro).

    CART_OPERATIONS = Counter(
        "cart_operations_total",
        "Cart line/quantity operations on persistent cart_service.",
        labelnames=("operation", "status", "source"),
    )

    ORDERS_CREATED = Counter(
        "orders_created_total",
        "Orders created via storefront/embed/ai-site/admin flows.",
        labelnames=("source", "status"),
    )

    CORS_BLOCKED = Counter(
        "cors_blocked_total",
        "Requests rejected by DynamicCORSMiddleware (origin not allowlisted).",
        labelnames=("path_prefix", "reason"),
    )

    IDEMPOTENCY_CACHE = Counter(
        "idempotency_cache_total",
        "Idempotency-Key cache hit/miss + enforcement outcomes.",
        labelnames=("result", "scope"),
    )

    API_LATENCY = Histogram(
        "api_response_time_seconds",
        "HTTP response time on /api/public/* hot path.",
        labelnames=("endpoint", "status"),
    )

    # ── Phase 1 Step 12 — Embed widget funnel ──
    # Bootstrap calls per slug → tasso visitors widget + cache effectiveness.
    EMBED_INIT_REQUESTS = Counter(
        "embed_init_requests_total",
        "GET /api/public/embed/init/{slug} requests (Stream A widget bootstrap).",
        labelnames=("slug", "cache_result"),
    )

    # ── Phase 1 Step 13 — Embed categories endpoint ──
    # Lookup tasso categorie per slug + thumbnail toggle. Permette di
    # capire se la maggior parte dei widget filter-nav abilita le
    # immagini (impatto Mongo extra round-trip).
    EMBED_CATEGORY_LOOKUPS = Counter(
        "embed_category_lookups_total",
        "GET /api/public/embed/categories/{slug} requests.",
        labelnames=("slug", "with_thumbnail"),
    )

    # ── Phase 1 Step 14 — Embed products search endpoint ──
    # has_filter ∈ {"true", "false"} → indica se la richiesta usa
    # category/type filter o no (per stimare uso filter UI).
    EMBED_PRODUCT_SEARCHES = Counter(
        "embed_product_searches_total",
        "GET /api/public/embed/products/{slug} requests.",
        labelnames=("slug", "has_filter"),
    )

    # ── Track E Step 2.4.5 — Embed product detail endpoint ──
    # Tracks click-to-detail funnel: customer ha cliccato un product card
    # nel widget grid e ha aperto il drawer detail. Conversion-relevant
    # signal — alta correlazione con add-to-cart e checkout downstream.
    EMBED_PRODUCT_DETAILS = Counter(
        "embed_product_details_total",
        "GET /api/public/embed/products/{slug}/{product_id} requests.",
        labelnames=("slug",),
    )

    # ── Phase 1 Step 16 — Embed checkout funnel start ──
    # outcome ∈ {success, return_url_rejected, cart_invalid, gdpr_missing,
    # order_failed, ...} → funnel di abbandono / errori del widget checkout.
    EMBED_CHECKOUT_STARTED = Counter(
        "embed_checkout_started_total",
        "POST /api/public/embed/checkout/start requests (Stream A funnel start).",
        labelnames=("slug", "outcome"),
    )

    # ── Phase 1 Step 17 — postMessage bridge serving rate ──
    # status ∈ {served, not_found, malformed_return_url}.
    # slug e' un proxy soft (estratto dall'order metadata se disponibile,
    # altrimenti "unknown") — il bridge endpoint NON ha slug nel path.
    EMBED_POSTMESSAGE_BRIDGES = Counter(
        "embed_postmessage_bridges_total",
        "GET /api/public/embed/checkout/complete bridge HTML served.",
        labelnames=("slug", "status"),
    )

    # ── Track O Step 3.3 — Open beta business metrics ──
    #
    # Razionale: per il piano open beta (50-200 merchant) operatore deve
    # avere visibility su 3 health KPI lato business:
    #   - payments: e' il money flow OK?
    #   - signups: il funnel acquisizione funziona?
    #   - emails: la deliverability tiene?
    #
    # Cardinalita' MOLTO bassa per ogni metric (≤10 valori per dim) → no
    # explosion anche con 200 merchant. NO slug/org_id labels (sarebbe
    # esplosione). Org-level breakdown disponibile via audit_logs query
    # (O1.4) per investigation puntuale.

    # payments_total — Stripe webhook outcomes (post signature verify).
    # event_type ∈ {checkout_completed, payment_refunded, payment_disputed,
    #               unknown}
    # status     ∈ {ok, error, invalid_signature}
    PAYMENTS_TOTAL = Counter(
        "payments_total",
        "Stripe webhook events received, by canonical event type + outcome.",
        labelnames=("event_type", "status"),
    )

    # signups_total — merchant + customer signup funnel outcomes.
    # flow   ∈ {merchant, customer}
    # status ∈ {success, validation_failed, duplicate, rate_limited, error}
    SIGNUPS_TOTAL = Counter(
        "signups_total",
        "Signup attempts by flow and outcome (merchant + customer).",
        labelnames=("flow", "status"),
    )

    # email_sends_total — Brevo deliverability summary.
    # status ∈ {success, network_error, http_error, gated, dry_run}
    # NO `purpose` label (welcome/verify/forgot/etc) → cardinality stays
    # at 5 values vs purpose×status = 20+. Per-purpose breakdown live nei
    # logs (logger.info "email_service: sent to=... subject=...").
    EMAIL_SENDS_TOTAL = Counter(
        "email_sends_total",
        "Brevo email send attempts, by terminal outcome status.",
        labelnames=("status",),
    )

else:  # pragma: no cover — no-op shim
    class _Noop:
        def labels(self, *_args, **_kwargs):
            return self

        def inc(self, *_args, **_kwargs):
            return None

        def observe(self, *_args, **_kwargs):
            return None

    CART_OPERATIONS = _Noop()
    ORDERS_CREATED = _Noop()
    CORS_BLOCKED = _Noop()
    IDEMPOTENCY_CACHE = _Noop()
    API_LATENCY = _Noop()
    EMBED_INIT_REQUESTS = _Noop()
    EMBED_CATEGORY_LOOKUPS = _Noop()
    EMBED_PRODUCT_SEARCHES = _Noop()
    EMBED_PRODUCT_DETAILS = _Noop()
    EMBED_CHECKOUT_STARTED = _Noop()
    EMBED_POSTMESSAGE_BRIDGES = _Noop()
    # Track O Step 3.3 — Open beta business metrics
    PAYMENTS_TOTAL = _Noop()
    SIGNUPS_TOTAL = _Noop()
    EMAIL_SENDS_TOTAL = _Noop()


# ── Public recording helpers ────────────────────────────────────────────


def record_cart_op(
    operation: str,
    status: str,
    source: str = "storefront",
) -> None:
    """Increment cart_operations_total.

    operation ∈ {add, update, remove, clear, get}
    status    ∈ {success, error, not_found}
    source    ∈ {storefront, embed, ai-site}
    """
    try:
        CART_OPERATIONS.labels(
            operation=operation, status=status, source=source
        ).inc()
    except Exception as exc:  # pragma: no cover — soft fail
        logger.debug("metrics.record_cart_op failed: %s", exc)


def record_order(source: str, status: str) -> None:
    """Increment orders_created_total.

    source ∈ {storefront, embed, ai-site, admin}
    status ∈ {success, error, validation_failed}
    """
    try:
        ORDERS_CREATED.labels(source=source, status=status).inc()
    except Exception as exc:  # pragma: no cover
        logger.debug("metrics.record_order failed: %s", exc)


def record_cors_blocked(path_prefix: str, reason: str) -> None:
    """Increment cors_blocked_total.

    path_prefix ∈ {embed, ai-site, other}
    reason      ∈ {origin_not_allowed, slug_missing, store_inactive}
    """
    try:
        CORS_BLOCKED.labels(path_prefix=path_prefix, reason=reason).inc()
    except Exception as exc:  # pragma: no cover
        logger.debug("metrics.record_cors_blocked failed: %s", exc)


def record_idempotency(result: str, scope: str = "enforcement") -> None:
    """Increment idempotency_cache_total.

    result ∈ {hit, miss, stored, enforced_reject, grace_warn}
    scope  ∈ {enforcement, grace}
    """
    try:
        IDEMPOTENCY_CACHE.labels(result=result, scope=scope).inc()
    except Exception as exc:  # pragma: no cover
        logger.debug("metrics.record_idempotency failed: %s", exc)


def record_api_latency(endpoint: str, status: str, seconds: float) -> None:
    """Observe API response time."""
    try:
        API_LATENCY.labels(endpoint=endpoint, status=status).observe(seconds)
    except Exception as exc:  # pragma: no cover
        logger.debug("metrics.record_api_latency failed: %s", exc)


def record_embed_init(slug: str, cache_result: str) -> None:
    """Increment embed_init_requests_total.

    Phase 1 Step 12 — Stream A widget bootstrap funnel.

    slug         → identifies the store (low cardinality at scale: 1
                   widget per merchant, bounded by paying customer count).
    cache_result ∈ {miss, hit, if_none_match}.
    """
    try:
        EMBED_INIT_REQUESTS.labels(slug=slug, cache_result=cache_result).inc()
    except Exception as exc:  # pragma: no cover
        logger.debug("metrics.record_embed_init failed: %s", exc)


def record_embed_category_lookup(slug: str, with_thumbnail: bool) -> None:
    """Increment embed_category_lookups_total.

    Phase 1 Step 13 — categories endpoint usage tracking.

    slug           → store identifier
    with_thumbnail → bool flag (True triggers per-cat extra Mongo lookup)
    """
    try:
        EMBED_CATEGORY_LOOKUPS.labels(
            slug=slug,
            with_thumbnail=str(bool(with_thumbnail)).lower(),
        ).inc()
    except Exception as exc:  # pragma: no cover
        logger.debug("metrics.record_embed_category_lookup failed: %s", exc)


def record_embed_product_search(slug: str, has_filter: bool) -> None:
    """Increment embed_product_searches_total.

    Phase 1 Step 14 — products list endpoint usage tracking.

    slug       → store identifier
    has_filter → bool (True if category_slug OR type_filter was passed)
    """
    try:
        EMBED_PRODUCT_SEARCHES.labels(
            slug=slug,
            has_filter=str(bool(has_filter)).lower(),
        ).inc()
    except Exception as exc:  # pragma: no cover
        logger.debug("metrics.record_embed_product_search failed: %s", exc)


def record_embed_product_detail(slug: str) -> None:
    """Increment embed_product_details_total.

    Track E Step 2.4.5 — product detail drawer click tracking.
    Conversion-relevant: click-to-detail e' un signal forte di intent.

    slug → store identifier
    """
    try:
        EMBED_PRODUCT_DETAILS.labels(slug=slug).inc()
    except Exception as exc:  # pragma: no cover
        logger.debug("metrics.record_embed_product_detail failed: %s", exc)


def record_embed_checkout_start(slug: str, outcome: str) -> None:
    """Increment embed_checkout_started_total.

    Phase 1 Step 16 — checkout funnel start tracking.

    slug    → store identifier
    outcome ∈ {success, return_url_rejected, cart_invalid, cart_empty,
              cart_cross_tenant, gdpr_missing, order_failed,
              idempotency_replay, ...}
    """
    try:
        EMBED_CHECKOUT_STARTED.labels(slug=slug, outcome=outcome).inc()
    except Exception as exc:  # pragma: no cover
        logger.debug("metrics.record_embed_checkout_start failed: %s", exc)


def record_embed_postmessage_bridge(slug: str, status: str) -> None:
    """Increment embed_postmessage_bridges_total.

    Phase 1 Step 17 — bridge HTML served tracking.

    slug   → store identifier (or "unknown" when order has no slug attribution)
    status ∈ {served, not_found, malformed_return_url}
    """
    try:
        EMBED_POSTMESSAGE_BRIDGES.labels(slug=slug, status=status).inc()
    except Exception as exc:  # pragma: no cover
        logger.debug("metrics.record_embed_postmessage_bridge failed: %s", exc)


# ── Track O Step 3.3 — Open beta business metrics recording helpers ────


def record_payment(event_type: str, status: str = "ok") -> None:
    """Increment payments_total counter (Stripe webhook outcomes).

    event_type ∈ {checkout_completed, payment_refunded, payment_disputed,
                  unknown}
                  Map Stripe raw type → canonical via NormalizedEvent
                  constants where possible.
    status     ∈ {ok, error, invalid_signature}
                  ok                 → handler completed successfully
                  error              → handler raised / returned error status
                  invalid_signature  → webhook signature verification failed

    Call this from the router-level webhook handler (e.g. routers/billing.py
    stripe_webhook) — single integration point covers all event types.
    """
    try:
        PAYMENTS_TOTAL.labels(event_type=event_type, status=status).inc()
    except Exception as exc:  # pragma: no cover
        logger.debug("metrics.record_payment failed: %s", exc)


def record_signup(flow: str, status: str) -> None:
    """Increment signups_total counter (merchant + customer funnel).

    flow   ∈ {merchant, customer}
    status ∈ {success, validation_failed, duplicate, rate_limited, error}
             success           → account created (verification email sent
                                 separately tracked via record_email)
             validation_failed → input rejected (password too weak, terms
                                 not accepted, invalid email format)
             duplicate         → email already registered (409)
             rate_limited      → slowapi or check_email_rate fired
             error             → generic 500 (unexpected exception)

    Call from router signup handler in BOTH success path AND except branches.
    """
    try:
        SIGNUPS_TOTAL.labels(flow=flow, status=status).inc()
    except Exception as exc:  # pragma: no cover
        logger.debug("metrics.record_signup failed: %s", exc)


def record_email_send(status: str) -> None:
    """Increment email_sends_total counter (Brevo deliverability summary).

    status ∈ {success, network_error, http_error, gated, dry_run}
             success       → Brevo returned 2xx (delivered to Brevo, not
                             necessarily to inbox — for inbox deliverability
                             see email-reputation.md monitoring)
             network_error → all retries exhausted (DNS, timeout, connect)
             http_error    → Brevo returned non-2xx (auth fail, validation,
                             rate limit from Brevo side)
             gated         → pre-flight email_gate blocked (suppression list,
                             bounce, complaint)
             dry_run       → email_service not configured (BREVO_API_KEY
                             missing) — no actual send attempted

    Call from email_service.send_email + send_email_with_attachment terminal
    branches.
    """
    try:
        EMAIL_SENDS_TOTAL.labels(status=status).inc()
    except Exception as exc:  # pragma: no cover
        logger.debug("metrics.record_email_send failed: %s", exc)


# ── /metrics endpoint backing function ───────────────────────────────────


def render_latest() -> Tuple[bytes, str]:
    """Return (body, content_type) suitable for /metrics endpoint.

    If prometheus_client is unavailable, returns plain-text comment.
    """
    if not _PROMETHEUS_AVAILABLE:
        body = b"# prometheus_client not installed; metrics disabled\n"
        return body, "text/plain; charset=utf-8"
    return generate_latest(), CONTENT_TYPE_LATEST
