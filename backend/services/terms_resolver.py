"""
Terms & Conditions resolver (F4 Onda 11).

Single source of truth for "which T&C apply to this order?". The merchant
configures T&C at two levels:

- Store-level (`Store.terms_enabled` + `Store.terms_content`): applied
  by default to every order submitted through the storefront.
- Product-level (`Product.metadata.terms_content`): optional override.
  If set, takes precedence over the store-level T&C for orders
  containing that product.

Precedence order:
  product.metadata.terms_content  (if non-empty)
    → store.terms_content          (only if store.terms_enabled=True
                                     AND content is non-empty)
    → None                         (no T&C required)

Consumers:
  - `routers/public.submit_order_request` — validates acceptance
  - `routers/public._catalog` / `_event_landing` — surfaces the text
    so the storefront can render the acceptance checkbox + expandable
    panel
"""

from typing import Optional


def _nonempty_text(s) -> bool:
    return bool(s) and bool(str(s).strip())


def resolve_effective_terms_sync(
    *,
    product: Optional[dict] = None,
    store: Optional[dict] = None,
) -> Optional[str]:
    """Pure function: given already-loaded product/store dicts, return
    the effective T&C markdown or None.

    Prefer this over the async variant when the caller has already
    loaded both documents (avoids unnecessary DB round-trips).
    """
    # 1) product override
    if product:
        meta = product.get("metadata") or {}
        po = meta.get("terms_content")
        if _nonempty_text(po):
            return str(po)

    # 2) store default (only if explicitly enabled)
    if store and store.get("terms_enabled"):
        so = store.get("terms_content")
        if _nonempty_text(so):
            return str(so)

    return None


async def resolve_effective_terms(
    *,
    org_id: str,
    store_id: Optional[str] = None,
    product_id: Optional[str] = None,
    product: Optional[dict] = None,
    store: Optional[dict] = None,
) -> Optional[str]:
    """Async variant that loads store/product from the DB when they
    haven't been passed in. Returns None if no T&C should be required.
    """
    from database import products_collection, stores_collection

    if product is None and product_id:
        product = await products_collection.find_one(
            {"id": product_id, "organization_id": org_id},
            {"_id": 0, "metadata": 1},
        )

    if store is None and store_id:
        store = await stores_collection.find_one(
            {"id": store_id, "organization_id": org_id},
            {"_id": 0, "terms_enabled": 1, "terms_content": 1},
        )

    return resolve_effective_terms_sync(product=product, store=store)
