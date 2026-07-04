"""
Per-step done evaluators (Fase 2 Track F — Step 2).

For every canonical step in step_registry.STEP_REGISTRY there must be a
matching async handler in this module that decides whether the step is
already completed for a given org/user.

Handlers are registered in `_HANDLERS` keyed by `step.key`. The
public entry point is `is_step_done(step_key, org_id, user_id)`.

Design rules:
  - Read-only: handlers MUST NOT mutate any document.
  - Org-scoped: every Mongo query filters by `organization_id`.
  - Defensive: missing fields → `False` (not done). Never raise.
  - Single source of truth: when a check already exists in
    `routers/store_progress.py` or `routers/store_settings.py`, we import
    or replicate its logic verbatim — never re-invent the rule.
  - Performance: each handler runs at most one Mongo round-trip. The
    wizard service caps the total per request at ~10 round-trips.
  - No HTTP exceptions: handlers return bool; HTTP errors (404, 401)
    happen at the router boundary in routers/setup_wizard.py.
"""

from __future__ import annotations

import logging
from typing import Awaitable, Callable, Dict, Optional

from database import (
    organizations_collection,
    users_collection,
    datasets_collection,
    alerts_collection,
    products_collection,
    orders_collection,
    payment_connections_collection,
    ai_usage_events_collection,
)

logger = logging.getLogger(__name__)

# Type alias for handler signature.
# (org_id, user_id) -> awaitable[bool]
StepDoneHandler = Callable[..., Awaitable[bool]]


# ── Helpers ──────────────────────────────────────────────────────────────────

async def _load_org_store_settings(org_id: str) -> dict:
    """Return org.store_settings dict (empty dict if missing)."""
    org = await organizations_collection.find_one(
        {"id": org_id},
        {"_id": 0, "store_settings": 1},
    )
    if not org:
        return {}
    return org.get("store_settings") or {}


async def _load_org_branding(org_id: str) -> dict:
    """Return org.branding dict (empty dict if missing)."""
    org = await organizations_collection.find_one(
        {"id": org_id},
        {"_id": 0, "branding": 1},
    )
    if not org:
        return {}
    return org.get("branding") or {}


# ── GLOBAL section handlers ──────────────────────────────────────────────────

async def _global_verify_email(org_id: str, user_id: Optional[str], **_) -> bool:
    """User has confirmed the verification email link."""
    if not user_id:
        return False
    user = await users_collection.find_one(
        {"id": user_id},
        {"_id": 0, "email_verified": 1},
    )
    return bool(user and user.get("email_verified"))


async def _global_brand_identity(org_id: str, **_) -> bool:
    """Org has at least one branding field set (logo OR brand color)."""
    branding = await _load_org_branding(org_id)
    return bool(branding.get("logo_url") or branding.get("brand_color"))


# ── CASHFLOW MONITOR section handlers ────────────────────────────────────────

async def _cashflow_upload_first_data(org_id: str, **_) -> bool:
    """Org has uploaded at least one dataset (sales / expenses / purchases / etc)."""
    count = await datasets_collection.count_documents({"organization_id": org_id})
    return count > 0


async def _cashflow_first_alert(org_id: str, **_) -> bool:
    """At least one alert document exists for this org.

    The alert engine creates rows automatically once data is present and
    a threshold is crossed; "configuring" an alert in the UI also
    persists rows. Either way, presence indicates the user has interacted
    with the alerts surface, which is what this step is meant to nudge.
    """
    count = await alerts_collection.count_documents({"organization_id": org_id})
    return count > 0


# ── COMMERCE section handlers ────────────────────────────────────────────────

async def _commerce_identity(org_id: str, **_) -> bool:
    """Store has display_name AND contact_email set (matches setup-progress)."""
    store = await _load_org_store_settings(org_id)
    return bool(store.get("display_name")) and bool(store.get("contact_email"))


async def _commerce_first_product(org_id: str, **_) -> bool:
    """At least one product is published AND truly publishable.

    Reuses the canonical predicate from routers/store_settings to keep the
    rule consistent with the legacy /api/store/setup-progress endpoint.
    """
    # Local import to avoid pulling routers/* into module load order.
    from routers.store_settings import _is_product_truly_publishable

    cursor = products_collection.find(
        {
            "organization_id": org_id,
            "is_published": True,
            "is_active": True,
        },
        {
            "_id": 0,
            "transaction_mode": 1,
            "price_mode": 1,
            "unit_price": 1,
        },
    ).limit(50)

    async for prod in cursor:
        if _is_product_truly_publishable(prod):
            return True
    return False


async def _commerce_email_sender(org_id: str, **_) -> bool:
    """Sender display name AND reply-to email both set (matches setup-progress)."""
    store = await _load_org_store_settings(org_id)
    return bool(store.get("sender_display_name")) and bool(store.get("reply_to_email"))


async def _commerce_stripe_connect(org_id: str, **_) -> bool:
    """Active Stripe Connect / payment connection exists for the org.

    Mirrors `provider_connected` from setup-progress: status=active AND
    runtime_status=ready. Either condition alone would let a half-broken
    connection slip through.
    """
    pc = await payment_connections_collection.find_one(
        {
            "organization_id": org_id,
            "status": "active",
            "runtime_status": "ready",
        },
        {"_id": 0, "id": 1},
    )
    return pc is not None


async def _commerce_publish_storefront(org_id: str, **_) -> bool:
    """Storefront is flagged published in store_settings."""
    store = await _load_org_store_settings(org_id)
    return bool(store.get("is_storefront_published"))


async def _commerce_first_order(org_id: str, **_) -> bool:
    """At least one non-draft order has been recorded.

    `status != "draft"` excludes admin-side scaffolding that hasn't been
    confirmed yet. Confirmed/paid/cancelled all count — what matters is
    that the order pipeline has at least flowed once.
    """
    count = await orders_collection.count_documents({
        "organization_id": org_id,
        "status": {"$ne": "draft"},
    })
    return count > 0


# ── AI ASSISTANT section handlers ────────────────────────────────────────────

async def _ai_first_chat(org_id: str, **_) -> bool:
    """User has triggered at least one AI chat event for this org."""
    count = await ai_usage_events_collection.count_documents({
        "organization_id": org_id,
        "feature": "chat",
    })
    return count > 0


# ── Registry ─────────────────────────────────────────────────────────────────
# Map each canonical step.key from step_registry to its evaluator. Adding a
# new step requires (1) appending to step_registry.STEP_REGISTRY and (2)
# registering its handler here. Mismatches between the two are caught by
# the consistency check at the bottom of this module.

_HANDLERS: Dict[str, StepDoneHandler] = {
    # global
    "global.verify_email":                        _global_verify_email,
    "global.brand_identity":                      _global_brand_identity,
    # cashflow_monitor
    "cashflow_monitor.upload_first_data":         _cashflow_upload_first_data,
    "cashflow_monitor.first_alert":               _cashflow_first_alert,
    # commerce
    "commerce.identity":                          _commerce_identity,
    "commerce.first_product":                     _commerce_first_product,
    "commerce.email_sender":                      _commerce_email_sender,
    "commerce.stripe_connect":                    _commerce_stripe_connect,
    "commerce.publish_storefront":                _commerce_publish_storefront,
    "commerce.first_order":                       _commerce_first_order,
    # ai_assistant
    "ai_assistant.first_chat":                    _ai_first_chat,
}


# ── Public entry point ───────────────────────────────────────────────────────

async def is_step_done(
    step_key: str,
    org_id: str,
    user_id: Optional[str] = None,
) -> bool:
    """Compute the done flag for a single step.

    Args:
        step_key: stable identifier from STEP_REGISTRY (e.g. "commerce.identity").
        org_id:   the organization_id to evaluate against.
        user_id:  the requesting user's id, when the step is account-scoped
                  (e.g. global.verify_email checks the *user's* verification
                  status, not an org-wide flag).

    Returns:
        True iff the step is considered complete. Returns False on:
          - unknown step_key (handler not registered)
          - missing/malformed org or user document
          - any unexpected error (logged at WARNING level)

    Rationale: never raising lets the wizard degrade gracefully — at
    worst a step shows as "to do" when it's actually done. The user can
    re-click the CTA which is idempotent on every destination page.
    """
    handler = _HANDLERS.get(step_key)
    if handler is None:
        logger.warning(
            "setup_wizard: no done-handler registered for step_key=%s — "
            "returning False",
            step_key,
        )
        return False

    try:
        return await handler(org_id=org_id, user_id=user_id)
    except Exception as e:  # pragma: no cover — defensive only
        logger.warning(
            "setup_wizard: handler for step_key=%s raised %s — returning False",
            step_key, type(e).__name__,
            exc_info=True,
        )
        return False


def get_registered_step_keys() -> set[str]:
    """All step keys with a registered handler. Used by consistency tests."""
    return set(_HANDLERS.keys())
