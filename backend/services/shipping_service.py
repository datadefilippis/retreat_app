"""
shipping_service.py — pure helpers for shipping option resolution + cost.

Two responsibilities, both callable from multiple sites without taking
HTTP concerns:

  1. `resolve_shipping_options(org_id, store_id)`:
     Return the ACTIVE shipping options that should surface at the given
     store's checkout. Unions per-store options (store_id==X) with
     org-global ones (store_id==None). Ordered deterministically.

  2. `compute_shipping_for_order(...)`:
     Compute the shipping cost + label snapshot that will be persisted
     on Order.fulfillment. Enforces:
       - mode != "shipping" → cost 0, option cleared
       - mode == "shipping" + order has physical items → option_id required
       - free_shipping_threshold: when physical subtotal >= threshold → 0
       - option must exist, be active, and belong to the store's scope

No HTTP exceptions here; the helper raises `ValueError` with a stable
`code:...` prefix that routers translate to 400. This keeps the service
reusable from create_order, price-preview, and tests without importing
FastAPI.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Iterable, List, Optional


logger = logging.getLogger(__name__)


# Canonical reason codes raised by compute_shipping_for_order as the
# leading part of a ValueError message, so routers can map them to HTTP
# responses with stable frontend-facing strings.
SHIPPING_OPTION_REQUIRED = "shipping_option_required"
SHIPPING_OPTION_NOT_FOUND = "shipping_option_not_found"
SHIPPING_OPTION_INACTIVE = "shipping_option_inactive"
SHIPPING_OPTION_WRONG_SCOPE = "shipping_option_wrong_scope"


def _raise(code: str, detail: str) -> None:
    raise ValueError(f"{code}: {detail}")


async def resolve_shipping_options(
    *, org_id: str, store_id: str,
) -> List[Dict[str, Any]]:
    """Return the ACTIVE options visible at checkout for a given store.

    Union of:
      - docs with store_id == <the passed store_id>
      - docs with store_id == None (org-global fallbacks)

    Sorted by (sort_order ASC, label ASC). Inactive options are
    excluded. An empty list is a legitimate answer — the storefront
    surfaces that with a "no options configured" banner.
    """
    from database import shipping_options_collection

    cursor = shipping_options_collection.find(
        {
            "organization_id": org_id,
            "is_active": True,
            "$or": [{"store_id": store_id}, {"store_id": None}],
        },
        {"_id": 0},
    ).sort([("sort_order", 1), ("label", 1)])
    return await cursor.to_list(None)


def _has_physical_items(items: Iterable[Dict[str, Any]]) -> bool:
    """True when at least one line in the cart is item_type=physical."""
    for item in items or []:
        # Accept both Pydantic model instances and plain dicts.
        t = item.get("item_type") if isinstance(item, dict) else getattr(item, "item_type", None)
        if t == "physical":
            return True
    return False


def _sum_physical_subtotal(items: Iterable[Dict[str, Any]]) -> float:
    """Sum line_total of physical lines only — free-shipping threshold
    is applied against this value, not against the grand total (so
    adding a service doesn't accidentally unlock free shipping)."""
    total = 0.0
    for item in items or []:
        if isinstance(item, dict):
            t = item.get("item_type")
            lt = item.get("line_total", 0)
        else:
            t = getattr(item, "item_type", None)
            lt = getattr(item, "line_total", 0)
        if t == "physical":
            try:
                total += float(lt or 0)
            except (TypeError, ValueError):
                continue
    return round(total, 2)


async def compute_shipping_for_order(
    *,
    org_id: str,
    store_id: Optional[str],
    option_id: Optional[str],
    mode: Optional[str],
    items: Iterable[Dict[str, Any]],
) -> Dict[str, Any]:
    """Compute the shipping snapshot to persist on Order.fulfillment.

    Returns:
        {
          "shipping_option_id":    str | None,
          "shipping_option_label": str | None,
          "shipping_cost":         float,
        }

    Semantics:
      - `mode in ("local_pickup", "manual_arrangement", "not_required", None)`
        → zero-cost, option cleared regardless of what the client sent.
      - `mode == "shipping"` with no physical items in the cart → zero-cost
        (defensive: the rest of the stack shouldn't even ask, but we won't
        charge fictitious shipping).
      - `mode == "shipping"` with physical items:
          → option_id MUST be present AND resolvable to an active option in
            this org whose scope (store or global) covers `store_id`.
          → cost = 0 if `free_shipping_threshold` is set AND physical
            subtotal >= threshold; otherwise cost = `base_price`.
          → label snapshot includes a "(Gratis sopra €X)" hint when the
            threshold is met, so the admin/customer see why it's free.

    Never raises HTTP exceptions. Raises ValueError(f"<code>: <detail>")
    with a stable `code:` prefix when validation fails, so callers can
    map codes to 400s.
    """
    from database import shipping_options_collection

    # Non-shipping modes always produce zero-cost. Preserve None semantics
    # so Fulfillment defaults clean up nicely.
    if mode != "shipping":
        return {
            "shipping_option_id": None,
            "shipping_option_label": None,
            "shipping_cost": 0.0,
        }

    has_physical = _has_physical_items(items)
    if not has_physical:
        # Cart is all-virtual even in mode=shipping (edge case, e.g. a
        # merchant-forced mode). No shipping to charge.
        return {
            "shipping_option_id": None,
            "shipping_option_label": None,
            "shipping_cost": 0.0,
        }

    if not option_id:
        _raise(
            SHIPPING_OPTION_REQUIRED,
            "Seleziona un'opzione di spedizione prima di procedere.",
        )

    option = await shipping_options_collection.find_one(
        {"id": option_id, "organization_id": org_id},
        {"_id": 0},
    )
    if not option:
        _raise(
            SHIPPING_OPTION_NOT_FOUND,
            f"Opzione '{option_id}' non trovata per questa organizzazione.",
        )
    if not option.get("is_active", True):
        _raise(
            SHIPPING_OPTION_INACTIVE,
            f"L'opzione '{option.get('label') or option_id}' non è più attiva.",
        )

    # Scope check: the option must be either a global (store_id None) or
    # match the order's store_id. This mirrors the public resolver so the
    # server never accepts an option that couldn't have been listed.
    option_store = option.get("store_id")
    if option_store not in (None, store_id):
        _raise(
            SHIPPING_OPTION_WRONG_SCOPE,
            "L'opzione scelta non è disponibile per questo store.",
        )

    base_price = float(option.get("base_price") or 0)
    threshold = option.get("free_shipping_threshold")
    try:
        threshold = float(threshold) if threshold is not None else None
    except (TypeError, ValueError):
        threshold = None

    physical_subtotal = _sum_physical_subtotal(items)
    free = threshold is not None and physical_subtotal >= threshold
    cost = 0.0 if free else round(base_price, 2)

    # Label snapshot captured at order confirm time — subsequent admin
    # edits to the option row won't rewrite historical orders.
    base_label = option.get("label") or "Spedizione"
    if free:
        label = f"{base_label} (Gratis, raggiunta soglia €{threshold:.2f})"
    else:
        label = base_label

    return {
        "shipping_option_id": option.get("id"),
        "shipping_option_label": label,
        "shipping_cost": cost,
    }


def compute_shipping_cost_preview(
    *, option: Dict[str, Any], physical_subtotal: float,
) -> float:
    """Lightweight synchronous preview of the effective cost.

    Used by price-preview endpoints that have already resolved the
    option doc and just need the number. Mirrors the pricing logic in
    `compute_shipping_for_order` without re-hitting the DB.
    """
    try:
        base = float(option.get("base_price") or 0)
    except (TypeError, ValueError):
        base = 0.0
    threshold = option.get("free_shipping_threshold")
    try:
        threshold = float(threshold) if threshold is not None else None
    except (TypeError, ValueError):
        threshold = None
    if threshold is not None and physical_subtotal >= threshold:
        return 0.0
    return round(base, 2)
