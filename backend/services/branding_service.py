"""
Branding resolver — single source of truth for the cascade

    Store value > Org value > None (platform-level fallback at the edge)

Step 1 of the "olistic settings" feature. Replaces the inline cascade
that used to live in `routers/public.py` (storefront catalog) and was
about to be duplicated for every other surface that wants branding
(auth pages, future widget embeds, transactional email headers, …).

Adding a new branding field (favicon, footer text, email sender name)
is a one-line change here + the corresponding line in the model + the
admin form. No router change needed: the catalog endpoint reads the
resolved dict, never the raw fields.

## Semantics — "explicit override vs inheritance"

A Store field is treated as an **explicit override** when its value is
**anything except None** — including the empty string. Rationale: an
admin who sets `store.logo_url = ""` is saying "this store explicitly
has no logo, do not inherit from the org." A field that is `None` (or
missing entirely from the document) means "no opinion, fall through to
the org default."

This is intentionally stricter than Python's truthiness (`or`) which
would treat "" as falsy and inherit anyway. The previous inline
cascade in `public.py` used `or`, which was lossy. We preserve the
old behavior for backward compatibility through a `strict_override`
flag (default True for new code, False to mimic the legacy `or`).

## Usage

    from services.branding_service import resolve_for_store, resolve_for_org

    # Inside a router that already has the org doc and the store doc:
    branding = resolve_for_store(store_doc, org_doc)
    # branding == {"logo_url": "...", "brand_color": "...", ...}

    # When there is no store context (e.g. a system-level email):
    branding = resolve_for_org(org_doc)
"""

from typing import Any, Dict, Optional


# Single list of branding fields. Adding a new field is a one-line
# change: append to this tuple and the resolvers pick it up. The
# routes that produce StoreInfo (and any future BrandingResponse) just
# spread the dict.
_BRANDING_FIELDS = (
    "logo_url",
    "brand_color",
    "brand_color_text",
    "favicon_url",
)


def _pick(store: Optional[Dict[str, Any]],
          org_branding: Dict[str, Any],
          field: str,
          *,
          strict_override: bool = True) -> Optional[Any]:
    """Pick the resolved value for one field.

    `strict_override=True` (default): a Store field is an override when
    its value is not None. This means `""` from the Store wins over a
    populated Org value — useful for "explicit clear" UX in the future.

    `strict_override=False`: matches the legacy `or` cascade. Falsy
    Store values (None, "", 0, …) inherit from Org. Use this when
    porting old call sites that relied on the lossy behavior; new
    callers should use the default.
    """
    store_val = (store or {}).get(field)
    if strict_override:
        if store_val is not None:
            return store_val
    else:
        if store_val:
            return store_val
    org_val = org_branding.get(field)
    return org_val if org_val is not None else None


def resolve_for_store(store: Optional[Dict[str, Any]],
                      org: Optional[Dict[str, Any]],
                      *,
                      strict_override: bool = False) -> Dict[str, Any]:
    """Resolve branding fields for a (store, org) pair.

    Returns a flat dict with every key in `_BRANDING_FIELDS`. Missing
    values are explicitly `None` — callers can spread the result into
    response models that expect Optional[str].

    `strict_override` defaults to **False** here to preserve byte-for-
    byte backward compatibility with the previous inline cascade in
    `public.py`. New code that wants the cleaner "" semantics can pass
    `strict_override=True`. We'll flip the default once every consumer
    has migrated.
    """
    org_branding = ((org or {}).get("branding") or {})
    return {
        field: _pick(store, org_branding, field, strict_override=strict_override)
        for field in _BRANDING_FIELDS
    }


def resolve_for_org(org: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """Resolve branding for surfaces that have no store context.

    Used by transactional emails (where the customer might span N
    stores of the same org) and by the auth pages when arrived without
    a slug query param. Returns the org-level `branding` sub-object
    expanded to a fully-populated dict (None for fields not configured).
    """
    org_branding = ((org or {}).get("branding") or {})
    return {field: org_branding.get(field) for field in _BRANDING_FIELDS}


def list_branding_fields() -> tuple:
    """Public accessor for the field list — useful for tests and for
    any UI that wants to render the resolved values in the same order
    as the model declares them. Returns a tuple (immutable)."""
    return _BRANDING_FIELDS
