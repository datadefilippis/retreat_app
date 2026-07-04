"""Feature Flag Service — Phase 0 Step 9 (2026-05-28).

Lettura granulare dei feature flag per-organization. Lettura O(1) con
in-memory cache TTL 60s per minimizzare round-trip DB sui hot path.

Contract
========
``is_enabled(org_id: str, flag_name: str) -> bool``
  Returns True se la flag esiste sull'org E è True; False altrimenti.
  Default False per ogni flag non set.

Cache invalidation
==================
- TTL 60s per (org_id, flag_name) → propagazione modifiche admin rapida
- Manual flush via ``clear_cache()`` (test + admin endpoint dopo update)

Usage
=====
  from services import feature_flag_service

  if await feature_flag_service.is_enabled(org_id, "embed_widget_enabled"):
      # serve embed-specific code path
      ...

Per controllare TUTTE le flag di un'org:
  flags = await feature_flag_service.get_all_flags(org_id)
  # → {"persistent_cart_enabled": False, "embed_widget_enabled": True, ...}
"""

import logging
import time
from typing import Optional

logger = logging.getLogger(__name__)


# ── In-memory cache ─────────────────────────────────────────────────────

_CACHE: dict[str, tuple[dict, float]] = {}
_CACHE_TTL_SECONDS = 60


def _cache_get(org_id: str) -> Optional[dict]:
    cached = _CACHE.get(org_id)
    if not cached:
        return None
    flags, ts = cached
    if time.monotonic() - ts > _CACHE_TTL_SECONDS:
        _CACHE.pop(org_id, None)
        return None
    return flags


def _cache_set(org_id: str, flags: dict) -> None:
    _CACHE[org_id] = (flags, time.monotonic())


def clear_cache(org_id: Optional[str] = None) -> None:
    """Public helper for tests + admin endpoint post-update.

    If org_id provided, clear only that org. Otherwise clear all.
    """
    if org_id is None:
        _CACHE.clear()
    else:
        _CACHE.pop(org_id, None)


# ── Public API ──────────────────────────────────────────────────────────


async def get_all_flags(org_id: str) -> dict:
    """Load all feature flags for an organization.

    Returns dict of {flag_name: bool}. Empty dict if org not found.
    Cached 60s.
    """
    cached = _cache_get(org_id)
    if cached is not None:
        return cached

    try:
        from database import organizations_collection
        doc = await organizations_collection.find_one(
            {"id": org_id},
            {"_id": 0, "feature_flags": 1},
        )
    except Exception as exc:
        logger.warning("FeatureFlag: lookup failed org=%s: %s", org_id, exc)
        return {}

    if not doc:
        return {}

    flags = doc.get("feature_flags") or {}
    if not isinstance(flags, dict):
        # Defensive: legacy orgs may have None or missing entirely
        flags = {}

    _cache_set(org_id, flags)
    return flags


async def is_enabled(org_id: str, flag_name: str) -> bool:
    """Check if a specific flag is enabled for an org.

    Returns False for:
      - Unknown org_id
      - Unknown flag_name (no error — treats as not enabled)
      - Flag explicitly False
      - DB lookup failure (fail-safe to False)

    Returns True only when the flag is explicitly set to True on the org.
    """
    if not org_id or not flag_name:
        return False

    flags = await get_all_flags(org_id)
    val = flags.get(flag_name, False)
    return bool(val)


async def set_flag(org_id: str, flag_name: str, value: bool) -> bool:
    """Atomic update of a single flag. Returns True if org found + updated.

    Use only from admin endpoints — caller MUST verify system_admin role.
    """
    try:
        from database import organizations_collection
        result = await organizations_collection.update_one(
            {"id": org_id},
            {"$set": {f"feature_flags.{flag_name}": bool(value)}},
        )
        if result.matched_count > 0:
            clear_cache(org_id)
            logger.info(
                "FeatureFlag: org=%s flag=%s set to %s",
                org_id, flag_name, value,
            )
            return True
        return False
    except Exception as exc:
        logger.error(
            "FeatureFlag: update failed org=%s flag=%s: %s",
            org_id, flag_name, exc,
        )
        return False


# ── Canonical flag names (string constants for use in calling code) ─────

# Phase 0 Step 4b
FLAG_PERSISTENT_CART = "persistent_cart_enabled"

# Stream A
FLAG_EMBED_WIDGET = "embed_widget_enabled"
FLAG_CUSTOM_DOMAIN = "custom_domain_enabled"

# Stream B
FLAG_AI_SITE_BUILDER = "ai_site_builder_enabled"

# All known flag names — usato da admin endpoint per validation
KNOWN_FLAGS = {
    FLAG_PERSISTENT_CART,
    FLAG_EMBED_WIDGET,
    FLAG_CUSTOM_DOMAIN,
    FLAG_AI_SITE_BUILDER,
}
