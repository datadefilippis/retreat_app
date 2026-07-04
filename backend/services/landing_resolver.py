"""
landing_resolver.py — single source of truth for admin-dashboard landing URLs.

Admin dashboards (ReservationDashboard, ServiceDashboard, PhysicalDashboard,
DigitalDashboard, EventDashboard) need to surface a "Preview landing" button
and a "Copy landing link" action. The URL they show MUST match what the public
storefront at _resolve_org / get_product_landing will accept, otherwise the
admin hands a 404 link to their customer.

Before this module each dashboard derived `orgSlug` client-side by picking the
first published store in the org:

    const published = stores.find(s => s.is_published);
    setOrgSlug(published?.slug || null);

That's wrong in three ways:
  1. It ignores `product.store_ids` — a product assigned only to store B
     would get a URL with store A's slug, which get_product_landing rejects
     with a 404.
  2. It ignores `visibility` / `is_active` constraints that _resolve_org
     enforces for public reachability.
  3. Each dashboard replicated the same logic, so a fix would drift.

This helper centralizes resolution with the SAME precedence rules the public
storefront uses. If this function says the URL is good, the storefront MUST
accept it (barring race conditions like an admin unpublishing mid-flight).

Contract:
    resolve_best_landing_store(org_id, product_store_ids) -> store dict | None

Selection order:
    1. If product_store_ids is non-empty: first store whose id is in that list
       AND is published/active/public-visibility.
    2. If product_store_ids is empty (= product is global to the org): first
       published/active/public-visibility store in the org (any one works —
       the storefront `_resolve_org` will serve the product under any such
       store's slug).
    3. None — no eligible store; caller emits a `blockers` entry explaining
       why ("no published store", "product only in private store", etc.).

Never raises. All DB errors degrade to `None` + a logged warning so the
dashboard gracefully shows "Landing non disponibile" instead of crashing.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional


logger = logging.getLogger(__name__)


# Constraints applied when deciding whether a store can legitimately serve
# a public landing URL. Kept in one place so updates here (e.g. adding
# "pos" visibility support) propagate to admin + public in lockstep.
_STORE_ELIGIBLE_FILTER: Dict[str, Any] = {
    "is_published": True,
    "is_active": True,
    "visibility": "public",
}


async def resolve_best_landing_store(
    *,
    org_id: str,
    product_store_ids: Optional[List[str]],
) -> Optional[Dict[str, Any]]:
    """Return the eligible store whose slug should appear in landing URLs.

    Returns a dict with at least `{id, slug, name, ...}` or None.
    """
    from database import stores_collection

    store_ids = [sid for sid in (product_store_ids or []) if sid]

    try:
        if store_ids:
            # Product is scoped to specific stores. Pick the first eligible
            # one whose id matches. We sort by name so the selection is
            # deterministic across dashboard reloads — otherwise Mongo's
            # natural order could flip between calls.
            store = await stores_collection.find_one(
                {
                    "organization_id": org_id,
                    "id": {"$in": store_ids},
                    **_STORE_ELIGIBLE_FILTER,
                },
                {"_id": 0},
                sort=[("name", 1)],
            )
            if store:
                return store

            # At this point the product has store_ids but none of them is
            # publicly reachable. Return None so the caller surfaces a
            # "blocker" instead of silently falling through to a random
            # global store — which would produce a 404 from
            # get_product_landing due to the store_ids membership check.
            return None

        # Global product: any eligible store in the org works.
        store = await stores_collection.find_one(
            {"organization_id": org_id, **_STORE_ELIGIBLE_FILTER},
            {"_id": 0},
            sort=[("name", 1)],
        )
        return store
    except Exception as exc:
        logger.warning(
            "landing_resolver: store lookup failed for org=%s store_ids=%s: %s",
            org_id, store_ids, exc,
        )
        return None


# Prefix mapping — keyed by the value of `product.item_type` + a secondary
# key for rental where the flavor changes nothing (both range + slot land
# on `/r/`). Legacy `booking` maps to the same prefix since Onda 16 merged
# bookings into rental+slot. event_ticket uses a per-occurrence route
# (`/e/:org/:occurrence_slug`) that is resolved in event_occurrences.py,
# NOT here — we return None for it so the caller falls back to its own
# logic.
_PREFIX_BY_ITEM_TYPE: Dict[str, str] = {
    "rental":   "/r",
    "service":  "/p",
    "physical": "/ph",
    "digital":  "/dg",
    "booking":  "/r",   # deprecated — served by ReservationLandingPage
}


def landing_prefix_for_item_type(item_type: Optional[str]) -> Optional[str]:
    """Return the route prefix for a given product type, or None.

    None means "this type has no single-product landing URL" (event_ticket
    today, or any future type we haven't wired yet). Callers should treat
    None as has_landing=False with an explanatory blocker.
    """
    if not item_type:
        return None
    return _PREFIX_BY_ITEM_TYPE.get(item_type)


def build_landing_path(
    *,
    item_type: Optional[str],
    store_slug: Optional[str],
    product_slug: Optional[str],
) -> Optional[str]:
    """Return `/<prefix>/<store_slug>/<product_slug>` or None when any
    component is missing. Safe to call with missing inputs — returns None
    instead of a broken URL.
    """
    prefix = landing_prefix_for_item_type(item_type)
    if not prefix or not store_slug or not product_slug:
        return None
    return f"{prefix}/{store_slug}/{product_slug}"


async def resolve_landing_info(
    *,
    org_id: str,
    product: Dict[str, Any],
    public_base_url: Optional[str] = None,
) -> Dict[str, Any]:
    """Build the full landing-info payload for a product.

    Runs the resolver, assembles the URL when viable, and collects the
    human-readable blockers so the dashboard can display exactly why the
    "Preview landing" button is disabled. Same shape the EventDashboard
    already consumes (`blockers: str[]`), so the frontend pattern is
    reusable.

    `public_base_url` is optional; when absent only `landing_url_path`
    is set and the caller (router) fills in the absolute URL from env.

    Never raises.
    """
    item_type = product.get("item_type")
    product_slug = product.get("slug")
    product_is_published = bool(product.get("is_published", False))
    product_is_active = product.get("is_active", True) is not False

    store = await resolve_best_landing_store(
        org_id=org_id,
        product_store_ids=product.get("store_ids") or [],
    )
    store_slug = (store or {}).get("slug")
    store_name = (store or {}).get("name")

    blockers: List[str] = []

    prefix = landing_prefix_for_item_type(item_type)
    if not prefix:
        blockers.append(
            "Questa tipologia di prodotto non ha una landing dedicata "
            "(es. event_ticket usa una landing per-occurrence)."
        )
    if not product_slug:
        blockers.append(
            "Lo slug del prodotto non è impostato (apri ✏️ Identità per generarlo)."
        )
    if not product_is_active:
        blockers.append("Il prodotto è stato disattivato.")
    if not product_is_published:
        blockers.append("Il prodotto è offline. Imposta su Online per renderlo visibile.")
    if not store_slug:
        ids = product.get("store_ids") or []
        if ids:
            blockers.append(
                "Nessuno store pubblicato corrisponde all'assegnazione del prodotto. "
                "Verifica che almeno uno degli store selezionati sia Online e pubblico."
            )
        else:
            blockers.append(
                "Nessuno store pubblico trovato nell'organizzazione. "
                "Pubblica almeno uno store per rendere il prodotto accessibile."
            )

    landing_url_path = build_landing_path(
        item_type=item_type,
        store_slug=store_slug,
        product_slug=product_slug,
    ) if not blockers else None

    landing_url_absolute = None
    if landing_url_path and public_base_url:
        landing_url_absolute = f"{public_base_url.rstrip('/')}{landing_url_path}"

    return {
        "has_landing": bool(landing_url_path),
        "landing_url_path": landing_url_path,
        "landing_url_absolute": landing_url_absolute,
        "store_id": (store or {}).get("id"),
        "store_slug": store_slug,
        "store_name": store_name,
        "product_slug": product_slug,
        "item_type": item_type,
        "blockers": blockers,
    }
