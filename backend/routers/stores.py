"""
Stores Router — CRUD for multi-store management.

Each organization can have multiple stores. The first store created
is marked as is_default=true and inherits settings from the legacy
org.store_settings (backward compatible migration).

Endpoints:
  GET    /stores              — list stores for current org
  POST   /stores              — create a new store
  GET    /stores/{id}         — get single store
  PATCH  /stores/{id}         — update store
  POST   /stores/{id}/publish — publish a store
  POST   /stores/{id}/unpublish — unpublish a store
"""

import logging
import re
from typing import Optional
import os
from fastapi import APIRouter, HTTPException, Depends, Request, UploadFile, File, status
from routers.auth import limiter
from pydantic import Field

from auth import get_current_user, get_verified_user, require_admin
from database import stores_collection, organizations_collection, products_collection
from models.store import (
    Store,
    StoreCreate,
    StoreUpdate,
    StoreResponse,
    SUPPORTED_FULFILLMENT_MODES,
    SUPPORTED_STOREFRONT_LANGUAGES,
    validate_string_list_field,
    validate_custom_nav_links,
    validate_design_tokens,
)
from models.common import generate_id, utc_now

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/stores", tags=["Stores"])

VALID_VISIBILITIES = {"public", "private", "pos"}
SLUG_PATTERN = re.compile(r'^[a-z0-9][a-z0-9-]{1,48}[a-z0-9]$')

# Storefront language defaulting (MVP-only constraint).
#
# Today the admin UI exposes a single-language picker on the store
# settings — `storefront_languages` ends up as a 1-element array. The
# data model (List[str]) is already designed for the future multi-lang
# rollout where 2+ entries can be enabled without any backend change.
#
# When creating a new store, we default that array to the CREATOR's
# account locale so a German-speaking merchant doesn't have to pick
# Italian-then-immediately-change. Falls back to "it" when the user's
# locale is unset or outside the i18n stack's supported set.
#
# Migration of legacy stores is intentionally out of scope: stores with
# multi-element arrays (created before this constraint) keep their
# values intact — the admin UI shows them with a banner so the merchant
# can downgrade explicitly when ready.
SUPPORTED_LOCALES = {"it", "en", "de", "fr"}


def _resolve_default_storefront_locale(user: Optional[dict]) -> str:
    """Pick the default storefront language for a newly-created store.

    Reads `user.locale` (e.g. "de", "en-US", "FR"), normalizes to a
    short app-supported code, and falls back to "it" when the value is
    missing/invalid. Pure function — no DB access — safe to call from
    helper paths that don't have a user context (returns "it" then).
    """
    if not user:
        return "it"
    raw = (user.get("locale") or "").lower().split("-")[0]
    return raw if raw in SUPPORTED_LOCALES else "it"


# ── Helpers ──────────────────────────────────────────────────────────────

async def _ensure_default_store(
    org_id: str,
    creator_user: Optional[dict] = None,
) -> dict:
    """Ensure the org has at least one store. If not, create a default
    store from legacy org.store_settings (migration path).

    Returns the default store document.
    """
    existing = await stores_collection.find_one(
        {"organization_id": org_id, "is_default": True},
        {"_id": 0},
    )
    if existing:
        return existing

    # No default store — check if any active store exists (e.g. user deleted the default)
    any_active = await stores_collection.find_one(
        {"organization_id": org_id, "is_active": True},
        {"_id": 0},
    )
    if any_active:
        # Promote the first active store to default
        await stores_collection.update_one(
            {"id": any_active["id"]},
            {"$set": {"is_default": True, "updated_at": utc_now()}},
        )
        any_active["is_default"] = True
        logger.info("stores: promoted store %s to default for org=%s", any_active["id"], org_id)
        return any_active

    # Migrate from legacy org.store_settings
    org = await organizations_collection.find_one(
        {"id": org_id},
        {"_id": 0, "name": 1, "public_slug": 1, "store_settings": 1},
    )
    if not org:
        return None

    ss = org.get("store_settings") or {}
    now = utc_now()
    # Default storefront language inherits the creator's account locale
    # when known, falling back to "it" for the legacy migration path
    # (called by GET /stores where the user's locale is always known).
    default_lang = _resolve_default_storefront_locale(creator_user)

    store_doc = {
        "id": generate_id(),
        "organization_id": org_id,
        "slug": org.get("public_slug"),
        "name": ss.get("display_name") or org.get("name", "My Store"),
        "description": ss.get("store_description"),
        "visibility": "public",
        "contact_email": ss.get("contact_email"),
        "contact_phone": ss.get("contact_phone"),
        "sender_display_name": ss.get("sender_display_name"),
        "reply_to_email": ss.get("reply_to_email"),
        "notification_email": ss.get("notification_email"),
        "email_delivery": ss.get("email_delivery", "platform"),
        "fulfillment_modes": ss.get("fulfillment_modes") or ["shipping"],
        # MVP single-language: see _resolve_default_storefront_locale.
        # The List[str] shape stays multi-ready for the future toggle.
        "storefront_languages": [default_lang],
        # Branding (v13.0 — migrate from org.store_settings)
        "logo_url": ss.get("logo_url"),
        "brand_color": ss.get("brand_color"),
        "brand_color_text": ss.get("brand_color_text"),
        "seo_title": ss.get("seo_title"),
        "seo_description": ss.get("seo_description"),
        "is_published": bool(ss.get("is_storefront_published")),
        "last_known_store_status": ss.get("last_known_store_status"),
        "last_status_transition_at": ss.get("last_status_transition_at"),
        "is_default": True,
        "is_active": True,
        "created_at": now,
        "updated_at": now,
    }

    try:
        await stores_collection.insert_one(store_doc)
        store_doc.pop("_id", None)
        logger.info("stores: migrated default store for org=%s store=%s", org_id, store_doc["id"])
    except Exception as e:
        # Might race with another request — re-fetch
        logger.warning("stores: migration race for org=%s: %s", org_id, e)
        existing = await stores_collection.find_one(
            {"organization_id": org_id, "is_default": True},
            {"_id": 0},
        )
        return existing

    return store_doc


def _validate_slug(slug: str) -> None:
    """Validate slug format."""
    if not SLUG_PATTERN.match(slug):
        raise HTTPException(
            status_code=400,
            detail="Lo slug deve contenere solo lettere minuscole, numeri e trattini (3-50 caratteri).",
        )


# ── Endpoints ────────────────────────────────────────────────────────────

@router.get("")
async def list_stores(current_user: dict = Depends(get_verified_user)):
    """List all stores for the current organization.

    Onda 16 — does NOT auto-create a default store anymore. New orgs
    see an empty list until they explicitly create their first store
    via POST /stores. The frontend renders an empty-state CTA.

    S1 (5/7/2026): per le org nel formato legacy mono-store la
    migrazione `_ensure_default_store` viene richiamata QUI (lazy,
    idempotente) cosi' lo store esiste come documento reale e
    l'operatore lo gestisce dalla UI — fine del phantom store.
    """
    org_id = current_user["organization_id"]

    cursor = stores_collection.find(
        {"organization_id": org_id, "is_active": True},
        {"_id": 0},
    ).sort("created_at", 1)

    stores = await cursor.to_list(50)

    # S1 (5/7/2026) — fine del "phantom store": se l'org e' nel formato
    # legacy mono-store (public_slug/store_settings, zero store doc), la
    # migrazione lazy materializza lo store REALE cosi' l'operatore lo
    # VEDE e lo gestisce. Idempotente e race-safe (_ensure_default_store
    # gestisce il duplicato). Le org nuove restano a lista vuota + CTA.
    if not stores:
        org = await organizations_collection.find_one(
            {"id": org_id},
            {"_id": 0, "public_slug": 1, "store_settings": 1},
        )
        if org and (org.get("public_slug") or org.get("store_settings")):
            try:
                migrated = await _ensure_default_store(org_id, current_user)
                if migrated:
                    stores = [migrated]
                    logger.info("stores: legacy org %s materializzata (S1)", org_id)
            except Exception as exc:
                logger.warning("stores: migrazione legacy fallita per %s: %s",
                               org_id, exc)

    return {"stores": stores, "total": len(stores)}


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_store(
    body: StoreCreate,
    current_user: dict = Depends(require_admin),
):
    """Create a new store for the organization."""
    org_id = current_user["organization_id"]

    # Validate visibility
    if body.visibility not in VALID_VISIBILITIES:
        raise HTTPException(status_code=400, detail=f"Visibility must be one of: {', '.join(VALID_VISIBILITIES)}")

    # Validate and check slug uniqueness
    if body.slug:
        _validate_slug(body.slug)
        existing_slug = await stores_collection.find_one({"slug": body.slug}, {"_id": 0, "id": 1})
        if existing_slug:
            raise HTTPException(status_code=409, detail="Questo slug e' gia' in uso.")

    # ── v5.8 / Onda 4: stores_max enforcement ─────────────────────────────
    #
    # Replaces the legacy hardcoded "max 10 stores" check with a plan-aware
    # limit pulled from `commerce.stores_max`:
    #   · Free / Solo / Commerce Starter → 1 store
    #   · Commerce Pro                   → 3 stores
    #   · Custom                         → unlimited
    # `addon_extra_store` (Onda 3) extends `stores_max` by +1 per unit
    # (Pro plan only). The effective_limit helper sums base + addons so
    # an org with Pro + 2× addon_extra_store can create up to 5 stores.
    #
    # Hard cap of 10 retained as defence-in-depth: if a misconfigured
    # PricingPlan sets stores_max=-1 unintentionally, the legacy guard
    # still blocks egregious abuse. Onda 8 system_admin override flow
    # can bypass via custom plan if a strategic customer needs more.
    #
    # v5.8 / Onda 10 Step B.5 — The hard cap is now read from
    # `commercial_plans.{slug}.platform_limits.stores_max_abuse_cap` so
    # system_admin can edit it via catalog UI without redeploy. A reasonable
    # constant (10) remains as defence-in-depth fallback for plans not
    # yet migrated to the catalog.
    from services.module_access import get_effective_limit
    from repositories import billing_repository as _br

    count = await stores_collection.count_documents({"organization_id": org_id, "is_active": True})
    effective_max = await get_effective_limit(org_id, "commerce", "stores_max")

    # Defence-in-depth: even if the plan declares unlimited, refuse
    # abusive counts above the abuse cap. Real customers wanting more
    # go through system_admin custom plan flow (Onda 8).
    HARD_ABUSE_CAP_FALLBACK = 10
    org_summary = await _br.get_org_billing_summary(org_id) or {}
    plan_slug = org_summary.get("commercial_plan_slug", "free")
    plan_doc = await _br.get_commercial_plan(plan_slug) or {}
    pl = plan_doc.get("platform_limits") or {}
    abuse_cap = pl.get("stores_max_abuse_cap")
    if not isinstance(abuse_cap, int) or abuse_cap <= 0:
        abuse_cap = HARD_ABUSE_CAP_FALLBACK

    if effective_max == -1:
        if count >= abuse_cap:
            raise HTTPException(
                status_code=400,
                detail=f"Numero massimo di store raggiunto ({abuse_cap}). Contatta il supporto.",
            )
    else:
        if count >= effective_max:
            # v5.8 / Onda 9.I.1 — standardised on QUOTA_EXCEEDED so the
            # frontend axios interceptor in api/client.js can surface a
            # consistent quota-exceeded paywall (same as ordini, chat AI,
            # data_rows). Extra fields (current_count, feature_key,
            # addon_slug) are passed through as metadata for richer UX.
            raise HTTPException(
                status_code=429,
                detail={
                    "code": "QUOTA_EXCEEDED",
                    "module_key": "commerce",
                    "feature_key": "stores_max",
                    "message": (
                        f"Hai raggiunto il limite di {effective_max} store del tuo piano. "
                        "Aggiorna il piano o aggiungi il pack '+1 store' per crearne altri."
                    ),
                    "current_count": count,
                    "used": count,
                    "effective_limit": effective_max,
                    "limit": effective_max,
                    "addon_slug": "addon_extra_store",
                },
            )

    # Onda 16 — promote the very first store to default. Removes the
    # previous behavior where _ensure_default_store was called BEFORE
    # the user's create_store, which would result in two stores being
    # created on the first ever POST /stores (one auto-default + the
    # user's). New rule: if the org has zero stores, this one becomes
    # the default. Otherwise it's a secondary store.
    is_first_store = (
        await stores_collection.count_documents(
            {"organization_id": org_id},
        )
    ) == 0

    # MVP-only: default storefront language to the admin's account
    # locale. The data model stays a List[str] — when the multi-lang
    # toggle ships, the admin UI sends `body.storefront_languages` and
    # this default is overridden. No backend change needed for that
    # transition.
    default_lang = _resolve_default_storefront_locale(current_user)

    now = utc_now()
    store_doc = {
        "id": generate_id(),
        "organization_id": org_id,
        "slug": body.slug,
        "name": body.name,
        "description": body.description,
        "visibility": body.visibility,
        "fulfillment_modes": ["shipping"],
        "storefront_languages": [default_lang],
        "is_published": False,
        # Onda 16 — first store becomes the org's default automatically.
        "is_default": is_first_store,
        "is_active": True,
        "created_at": now,
        "updated_at": now,
    }

    await stores_collection.insert_one(store_doc)
    store_doc.pop("_id", None)

    logger.info("stores: created store=%s name=%s org=%s", store_doc["id"], body.name, org_id)
    return store_doc


@router.get("/{store_id}")
async def get_store(
    store_id: str,
    current_user: dict = Depends(get_verified_user),
):
    """Get a single store by ID."""
    org_id = current_user["organization_id"]
    store = await stores_collection.find_one(
        {"id": store_id, "organization_id": org_id},
        {"_id": 0},
    )
    if not store:
        raise HTTPException(status_code=404, detail="Store not found")
    return store


@router.patch("/{store_id}")
async def update_store(
    store_id: str,
    body: StoreUpdate,
    current_user: dict = Depends(require_admin),
):
    """Update a store's settings."""
    org_id = current_user["organization_id"]

    store = await stores_collection.find_one(
        {"id": store_id, "organization_id": org_id},
        {"_id": 0, "id": 1},
    )
    if not store:
        raise HTTPException(status_code=404, detail="Store not found")

    updates = body.model_dump(exclude_unset=True)
    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")

    # Validate visibility
    if "visibility" in updates and updates["visibility"] not in VALID_VISIBILITIES:
        raise HTTPException(status_code=400, detail=f"Visibility must be one of: {', '.join(VALID_VISIBILITIES)}")

    # Validate slug uniqueness
    if "slug" in updates and updates["slug"]:
        _validate_slug(updates["slug"])
        existing_slug = await stores_collection.find_one(
            {"slug": updates["slug"], "id": {"$ne": store_id}},
            {"_id": 0, "id": 1},
        )
        if existing_slug:
            raise HTTPException(status_code=409, detail="Questo slug e' gia' in uso.")

    # Validate fulfillment_modes and storefront_languages via the shared
    # helper in models.store. Same rules apply to PATCH /store-settings
    # (see routers/store_settings.update_store_settings) so the two
    # parallel update surfaces stay behaviorally identical — a regression
    # in either path is now caught by the same code.
    #
    # Phase 2 of the Store consolidation plan: previously
    # `storefront_languages` was untyped/uncheckable here, letting an
    # empty array or unsupported code (e.g. "es") slip into the DB and
    # silently break the storefront i18n resolver (which assumes
    # storefront_languages[0] ∈ APP_SUPPORTED).
    for field_name, allowed in (
        ("fulfillment_modes", SUPPORTED_FULFILLMENT_MODES),
        ("storefront_languages", SUPPORTED_STOREFRONT_LANGUAGES),
    ):
        if field_name in updates:
            try:
                validate_string_list_field(
                    updates[field_name],
                    field_name=field_name,
                    allowed=allowed,
                )
            except ValueError as e:
                raise HTTPException(status_code=400, detail=str(e))

    # Phase 8 — custom_nav_links validation.
    #
    # Crosses fields: the label_i18n for each link must have an entry
    # for EVERY language the store has active. Therefore we need to
    # know the effective storefront_languages — which may be the
    # incoming update (admin is changing languages and nav at once)
    # OR the existing DB value (admin only touches nav).
    #
    # Effective resolution order:
    #   1. updates["storefront_languages"] if present in this PATCH
    #   2. existing store doc's storefront_languages
    #   3. ["it"] as defensive fallback (matches the model default)
    if "custom_nav_links" in updates:
        # Resolve the effective language set. The DB doc was already
        # fetched at the top of this endpoint for the visibility check,
        # but we deliberately re-fetch JUST the storefront_languages
        # field here to avoid coupling the validation block to the
        # earlier fetch's projection. Cheap query (indexed by id).
        existing = await stores_collection.find_one(
            {"id": store_id, "organization_id": org_id},
            {"_id": 0, "storefront_languages": 1},
        )
        active_languages = (
            updates.get("storefront_languages")
            or (existing or {}).get("storefront_languages")
            or ["it"]
        )
        try:
            updates["custom_nav_links"] = validate_custom_nav_links(
                updates["custom_nav_links"],
                store_languages=active_languages,
            )
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))

    # Phase 9 — design tokens validation.
    #
    # Same dual-write friendly pattern: when the PATCH carries the
    # field, run the pure validator and replace updates[design_tokens]
    # with the cleaned dict. Empty dict means "clear all tokens"
    # (admin reset to defaults) — DON'T treat None as "untouched"
    # here because the StoreUpdate Pydantic model uses None as
    # "absent from body", which we already gate via the `in` check.
    if "design_tokens" in updates:
        try:
            updates["design_tokens"] = validate_design_tokens(
                updates["design_tokens"],
            )
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))

    updates["updated_at"] = utc_now()

    await stores_collection.update_one(
        {"id": store_id, "organization_id": org_id},
        {"$set": updates},
    )

    updated = await stores_collection.find_one(
        {"id": store_id, "organization_id": org_id},
        {"_id": 0},
    )

    logger.info("stores: updated store=%s fields=%s org=%s", store_id, list(updates.keys()), org_id)
    return updated


@router.post("/{store_id}/publish")
async def publish_store(
    store_id: str,
    current_user: dict = Depends(require_admin),
):
    """Publish a store (make it publicly accessible).

    Wave E.8.1 — gated by DPA acknowledgement (Art. 28 GDPR). The merchant
    org MUST have acknowledged the Data Processing Agreement before any
    NEW publish action. Legacy stores that were ``is_published=True``
    prior to enforcement keep working (soft grace) — verified by the
    audit flag in ``services.dpa_enforcement.is_publish_gated``.
    """
    org_id = current_user["organization_id"]

    # Wave E.8.1 — DPA acknowledgement REQUIRED before publishing.
    # Hard-block on new publish actions. Legacy stores already public
    # are not affected (this endpoint only runs on transition to
    # is_published=True, which is the gate point).
    from services.dpa_enforcement import require_dpa_acknowledged
    await require_dpa_acknowledged(
        organization_id=org_id,
        action="pubblicare lo store",
    )

    store = await stores_collection.find_one(
        {"id": store_id, "organization_id": org_id},
        {"_id": 0},
    )
    if not store:
        raise HTTPException(status_code=404, detail="Store not found")

    if not store.get("slug"):
        raise HTTPException(status_code=400, detail="Configura uno slug prima di pubblicare.")

    if not store.get("name"):
        raise HTTPException(status_code=400, detail="Configura il nome dello store prima di pubblicare.")

    await stores_collection.update_one(
        {"id": store_id, "organization_id": org_id},
        {"$set": {"is_published": True, "updated_at": utc_now()}},
    )

    logger.info("stores: published store=%s org=%s", store_id, org_id)
    return {"message": "Store pubblicato", "is_published": True}


@router.post("/{store_id}/unpublish")
async def unpublish_store(
    store_id: str,
    current_user: dict = Depends(require_admin),
):
    """Unpublish a store (remove from public access)."""
    org_id = current_user["organization_id"]

    await stores_collection.update_one(
        {"id": store_id, "organization_id": org_id},
        {"$set": {"is_published": False, "updated_at": utc_now()}},
    )

    logger.info("stores: unpublished store=%s org=%s", store_id, org_id)
    return {"message": "Store sospeso", "is_published": False}


# ── Logo upload per-store ─────────────────────────────────────────────────

STORE_LOGO_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "uploads", "logos")
STORE_LOGO_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".svg"}
STORE_LOGO_MIMES = {"image/jpeg", "image/png", "image/webp", "image/svg+xml"}


@router.post("/{store_id}/logo")
@limiter.limit("5/minute")
async def upload_store_logo(
    request: Request,
    store_id: str,
    file: UploadFile = File(...),
    current_user: dict = Depends(require_admin),
):
    """Upload logo for a specific store. Max 2MB."""
    org_id = current_user["organization_id"]

    store = await stores_collection.find_one(
        {"id": store_id, "organization_id": org_id}, {"_id": 0, "id": 1})
    if not store:
        raise HTTPException(status_code=404, detail="Store not found")

    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext not in STORE_LOGO_EXTS:
        raise HTTPException(status_code=400, detail=f"Formato non supportato. Usa: {', '.join(STORE_LOGO_EXTS)}")
    if file.content_type and file.content_type not in STORE_LOGO_MIMES:
        raise HTTPException(status_code=400, detail=f"Tipo file non supportato: {file.content_type}")

    contents = await file.read()
    if len(contents) > 2 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="Immagine troppo grande. Max 2MB.")

    # Image optimization refinement — resize + compress before
    # writing to disk. SVG passes through unchanged (vector). Raster
    # formats get resized to ≤512px on the longest side and
    # re-encoded at perceptual-quality 85. Typical savings: 70-95%.
    #
    # Dimension validation (min 100×100, max 5000×5000 input) lives
    # inside the helper so a bad upload raises ValueError → we map
    # to HTTP 400 with the helper's Italian error message.
    from services.image_optimizer import optimize_logo
    try:
        contents, optimization_meta = optimize_logo(contents, ext)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    logger.info(
        "store_logo: optimized store=%s — %s",
        store_id, optimization_meta,
    )

    os.makedirs(STORE_LOGO_DIR, exist_ok=True)
    for old_ext in STORE_LOGO_EXTS:
        old_path = os.path.join(STORE_LOGO_DIR, f"{store_id}{old_ext}")
        if os.path.exists(old_path):
            try:
                os.remove(old_path)
            except OSError:
                pass

    filename = f"{store_id}{ext}"
    from services.object_storage import save_public_upload
    logo_url = save_public_upload("logos", filename, contents,
                                  content_type=f"image/{ext.lstrip('.')}")
    await stores_collection.update_one(
        {"id": store_id, "organization_id": org_id},
        {"$set": {"logo_url": logo_url, "updated_at": utc_now()}},
    )

    return {"logo_url": logo_url}
