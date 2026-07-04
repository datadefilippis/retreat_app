"""
Sentry SDK initialization for AFianco backend.

Opt-in via env vars:
    SENTRY_DSN          → if unset, Sentry is fully disabled (noop)
    ENVIRONMENT         → tag events (production/staging/development)
    RELEASE_SHA         → tag events with git SHA for release tracking
    SENTRY_TRACES_RATE  → 0.0–1.0, override del default env-based

Default traces sample rate (Track O Step 1.2 — Sentry free tier friendly):
    - production:  0.0001 (0.01%)  ~13k traces/mese a 50 req/s sustained
    - staging:     0.01   (1%)     utile per testing senza burn quota
    - development: 0.1    (10%)    full debug locale (no impact su free quota)
    - unset:       0.1    (default development behavior)

Errori (events) NON sono throttled da traces_sample_rate — sono contati
separatamente da Sentry (Developer free tier: 5k errors + 10k transactions
per mese). Quindi i bug rimangono visibili anche con sampling basso.

PII protection (3 layers):
    1. send_default_pii=False     → SDK doesn't auto-include user data
    2. before_send=scrub_event    → custom scrubber removes sensitive fields
    3. before_breadcrumb=...      → strips tokens/passwords from breadcrumbs

Fail-safe:
    Any error during init is logged and swallowed. The app boots regardless.
"""
import logging
import os

logger = logging.getLogger(__name__)


def _default_traces_rate_for_env(environment: str | None) -> float:
    """Smart default per traces_sample_rate basato su ENVIRONMENT.

    Pure function (no side effects, no os.environ read) → testable in isolation.
    Calibrazione mirata a stare nel Sentry Developer free tier
    (10k transactions/mese) anche su production con 50 req/s sustained.
    """
    env = (environment or "development").strip().lower()
    if env == "production":
        return 0.0001  # 0.01% — ~13k traces/mese a 50 req/s, sotto free quota
    if env == "staging":
        return 0.01    # 1% — utile testing senza burn budget
    # development / test / unset → debug attivo (locale, no impact)
    return 0.1


def init_sentry() -> bool:
    """
    Initialize Sentry SDK if SENTRY_DSN is set.

    Returns:
        True if Sentry was initialized, False if disabled or init failed.
    """
    dsn = os.getenv("SENTRY_DSN", "").strip()
    if not dsn:
        logger.info("Sentry disabled (SENTRY_DSN not set)")
        return False

    try:
        import sentry_sdk
        from sentry_sdk.integrations.fastapi import FastApiIntegration
        from sentry_sdk.integrations.starlette import StarletteIntegration
        from sentry_sdk.integrations.asyncio import AsyncioIntegration
    except ImportError as e:
        logger.error(
            "Sentry SDK not installed (sentry-sdk[fastapi] missing in requirements). "
            "Continuing without Sentry. Error: %s",
            e,
        )
        return False

    from ._pii_scrubber import scrub_event, scrub_breadcrumb

    environment = os.getenv("ENVIRONMENT", "development")
    release = os.getenv("RELEASE_SHA", "unknown")

    # Track O Step 1.2: traces_sample_rate env-based default (Sentry free
    # tier friendly). Override esplicito via SENTRY_TRACES_RATE env var.
    explicit_rate = os.getenv("SENTRY_TRACES_RATE", "").strip()
    if explicit_rate:
        try:
            traces_rate = float(explicit_rate)
        except (TypeError, ValueError):
            traces_rate = _default_traces_rate_for_env(environment)
    else:
        traces_rate = _default_traces_rate_for_env(environment)

    try:
        sentry_sdk.init(
            dsn=dsn,
            environment=environment,
            release=release,
            traces_sample_rate=traces_rate,
            send_default_pii=False,
            before_send=scrub_event,
            before_breadcrumb=scrub_breadcrumb,
            integrations=[
                FastApiIntegration(),
                StarletteIntegration(),
                AsyncioIntegration(),
            ],
            attach_stacktrace=True,
            max_breadcrumbs=50,
        )
        logger.info(
            "Sentry initialized (environment=%s, release=%s, traces_rate=%.4f)",
            environment, release, traces_rate,
        )
        return True
    except Exception as e:
        logger.error("Sentry init failed: %s. App will continue without Sentry.", e)
        return False


# ─────────────────────────────────────────────────────────────────────────────
# Track O Step 3.2 — Tagged exception capture helper
# ─────────────────────────────────────────────────────────────────────────────
#
# Centralized capture-with-tags so hot paths use ONE consistent API instead of
# scattering `sentry_sdk.set_tag(...); sentry_sdk.capture_exception(...)` blocks
# everywhere. Tags align with the Sentry alert rules defined in
# docs/operations/sentry-alert-rules.md (O3.1):
#
#   action: payment_charge | payment_refund | payment_webhook |
#           auth_login | auth_signup | auth_token_verify | auth_password_reset |
#           email_send | ai_complete | mongo_query
#   surface: api | embed | admin_ui | customer_portal
#
# Anti-PII: never accept email/phone/name as parameter. The `extra` dict is
# best-effort serialized by the SDK; the before_send scrubber still strips
# known PII fields as last defense.
#
# Safe-no-op when sentry_sdk is not installed (dev container without it):
# returns None silently. Hot paths can always call this — never raises.


# Canonical action vocabulary — keep in sync with sentry-alert-rules.md
# tag taxonomy table + the alert rule filters. Adding a new action here is
# free; using one NOT listed will still work (Sentry accepts any string) but
# defeats the point of the alert filter — flagged at lint level by sentinel.
_KNOWN_ACTIONS = frozenset({
    "payment_charge",
    "payment_refund",
    "payment_webhook",
    "auth_login",
    "auth_signup",
    "auth_token_verify",
    "auth_password_reset",
    "email_send",
    "ai_complete",
    "mongo_query",
})

_KNOWN_SURFACES = frozenset({
    "api",
    "embed",
    "admin_ui",
    "customer_portal",
})


def capture_with_tags(
    exception: BaseException,
    *,
    action: str,
    surface: str = "api",
    extra: dict | None = None,
) -> str | None:
    """Capture an exception to Sentry with canonical alert-filter tags.

    Args:
        exception: the BaseException to send.
        action: tag value from `_KNOWN_ACTIONS` — drives alert rule filters.
                Free-form strings allowed but discouraged (won't match rules).
        surface: tag value from `_KNOWN_SURFACES` — defaults to 'api'.
        extra: optional dict of additional context (NO PII — emails, phones,
               names). The before_send scrubber strips known PII fields as
               defense-in-depth.

    Returns:
        Sentry event ID if captured, None if Sentry SDK is missing/disabled
        (the function never raises — hot paths can call it unconditionally).

    Example:
        try:
            stripe.PaymentIntent.create(...)
        except Exception as e:
            capture_with_tags(e, action="payment_charge", surface="api")
            raise
    """
    try:
        import sentry_sdk
    except ImportError:
        # Sentry SDK not installed (dev container or stripped deploy) — silent.
        return None

    try:
        # sentry_sdk 2.x: new_scope() replaces push_scope() (deprecated).
        # Falls back to push_scope() if new_scope is missing (sentry-sdk < 2.0).
        scope_cm = getattr(sentry_sdk, "new_scope", None) or sentry_sdk.push_scope
        with scope_cm() as scope:
            scope.set_tag("action", action)
            scope.set_tag("surface", surface)
            if extra:
                for key, value in extra.items():
                    # set_extra accepts JSON-serializable values; SDK handles
                    # repr() fallback for non-serializable objects.
                    scope.set_extra(key, value)
            return sentry_sdk.capture_exception(exception)
    except Exception as capture_err:
        # Defensive: capture itself should never break the calling hot path.
        # Log + swallow.
        logger.warning(
            "capture_with_tags failed (action=%s surface=%s): %s",
            action, surface, capture_err,
        )
        return None
