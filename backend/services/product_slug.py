"""
Product slug generator (Onda 13).

Mirrors `generate_occurrence_slug()` in event_occurrences router but
scoped to the `Product` model. Used when:

- A product is created without an admin-supplied slug
- A product is updated with slug=None (regenerate from current name)
- A duplicate copy of a product is created (needs a fresh slug that
  doesn't collide with the source)

Design:
  - Slug is derived from `product.name` via slugify → a-z0-9-
  - If the candidate already exists for this org, append `-2`, `-3`, ...
  - Max 80 chars after slugify truncation; deduplication suffix fits in
    reserved 10 chars.
  - Returns the final, collision-free slug (str).

The collision check is intentionally async — slugs are unique per
organization via the sparse index in database.py.
"""

from typing import Optional

from models.event_occurrence import slugify


async def generate_product_slug(
    org_id: str,
    product_name: str,
    exclude_id: Optional[str] = None,
) -> str:
    """Return a unique slug for a product in the org.

    Args:
      org_id: organization scope.
      product_name: free-text name (user input). Slugified internally.
      exclude_id: if provided, the existing product with this id is
        excluded from the collision check (used on update where the
        product may keep its own slug).

    Returns:
      A slug string unique within (organization_id, slug).
    """
    from database import products_collection

    base = slugify(product_name or "")[:70] or "prodotto"
    candidate = base
    n = 2
    while True:
        query = {"organization_id": org_id, "slug": candidate}
        if exclude_id:
            query["id"] = {"$ne": exclude_id}
        hit = await products_collection.find_one(query, {"_id": 0, "id": 1})
        if not hit:
            return candidate
        candidate = f"{base}-{n}"
        n += 1
        if n > 999:
            # Extremely unlikely; bail with base + timestamp to break the loop
            import time
            return f"{base}-{int(time.time())}"
