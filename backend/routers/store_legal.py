"""Store legal admin router — Wave GDPR-Commerce Phase CG-3.

Admin-side endpoints for the merchant to manage their per-store legal
documents (Privacy Policy + Terms of Service). The merchant edits in up
to 4 locales, then picks ONE ``merchant_legal_display_locale`` that is
the SOLE version their customers will see — see CG-1 cornerstone in
``services/merchant_legal_versioning``.

Endpoints (all under ``/api/stores/{store_id}/legal``)
======================================================
- ``POST /generate-draft``        → render a fresh template from vars
                                    (does NOT save — returns markdown
                                    that the admin client renders in
                                    the editor for review)
- ``GET  /``                       → snapshot of all 8 content slots +
                                    display_locale + status + version
                                    (admin only)
- ``PATCH /content``               → save ONE locale slot of ONE doc.
                                    Updates ``last_edited_at``. Does NOT
                                    bump the version (publish does that).
- ``PATCH /display-locale``        → change the locale shown to customers.
                                    Has side-effects: if the store was
                                    already published, the version is
                                    bumped because the customer-visible
                                    bundle now changes — triggers
                                    customer re-consent on next /me poll.
- ``POST /publish``                → compute display-locale hash; bump
                                    version_tag if the hash changed
                                    (idempotent on no-op). Sets
                                    ``published_at = now``.

Security
========
- Every endpoint requires ``require_admin`` (org-level admin role).
- Every query filters by ``organization_id`` derived from the JWT.
  No store_id passed in the URL can ever leak data from another org.
- ``last_edited_at`` and ``published_at`` are written server-side from
  ``utc_now()`` — never trusted from the client.
- Version hash is computed server-side from the display-locale content;
  never accepted from the request.

Re-consent triggering invariant
================================
A re-consent event is triggered for ALL of this store's registered
customers iff the per-store ``merchant_legal_version_string`` changes.
Anything that DOES NOT change the version_string (e.g. saving a draft
in another locale) is invisible to customers — no re-consent.
"""

import logging
from datetime import datetime, timezone
from typing import Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from auth import require_admin
from database import stores_collection
from services.merchant_legal_versioning import (
    SUPPORTED_LOCALES,
    bump_version_tag,
    compute_legal_hash,
    current_version_string,
    get_effective_display_locale,
    merchant_legal_status,
)
from services.merchant_legal_template_service import (
    SUPPORTED_DOC_TYPES,
    TemplateVars,
    render_template,
)


logger = logging.getLogger(__name__)

router = APIRouter(prefix="/stores", tags=["Stores — Legal"])


# ─── Request / response models ──────────────────────────────────────────


class GenerateDraftRequest(BaseModel):
    doc_type: Literal["privacy", "terms"]
    locale: Literal["it", "en", "de", "fr"]
    # CG-3-Polish (2026-05-18): vars is now OPTIONAL on the request.
    # If omitted, the server pulls the persisted ``merchant_legal_template_vars``
    # from the store doc — letting the merchant click "Rigenera bozza"
    # in the editor without filling the wizard form again.
    vars: Optional[TemplateVars] = None


class PatchContentRequest(BaseModel):
    doc_type: Literal["privacy", "terms"]
    locale: Literal["it", "en", "de", "fr"]
    # Max length mirrors the Store model field length cap (30K).
    # We enforce here too so we fail fast before the Mongo update.
    content: str = Field(min_length=0, max_length=30_000)


class PatchDisplayLocaleRequest(BaseModel):
    locale: Literal["it", "en", "de", "fr"]


class PatchTemplateVarsRequest(BaseModel):
    """Wave CG-3-Polish — persistent wizard variables.

    All fields delegate to the same TemplateVars contract used by the
    template service so the schema stays in sync with the renderer.
    Strict subset semantics: server stores whatever fields are present
    (we never invent values; missing fields stay absent in the dict).
    """
    vars: TemplateVars


class PublishRequest(BaseModel):
    # Reserved for future "release notes" feature (CG-N). Empty for now.
    # Field intentionally Optional so the client can call publish with
    # an empty body or no body at all.
    release_notes: Optional[str] = Field(default=None, max_length=500)


# ─── Internal helpers ───────────────────────────────────────────────────


async def _load_store_for_admin(
    store_id: str, org_id: str
) -> dict:
    """Fetch a store doc enforcing org scoping. 404 if not found OR if
    it belongs to another org (the same 404 message in both cases so we
    don't leak cross-org existence)."""
    doc = await stores_collection.find_one(
        {"id": store_id, "organization_id": org_id},
        {"_id": 0},
    )
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Store not found",
        )
    return doc


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# ─── Endpoints ──────────────────────────────────────────────────────────


@router.post("/{store_id}/legal/generate-draft")
async def generate_draft(
    store_id: str,
    body: GenerateDraftRequest,
    current_user: dict = Depends(require_admin),
):
    """Render a fresh template for the chosen doc + locale + vars.

    Stateless — does NOT persist. The admin client renders the returned
    markdown in the editor; the admin reviews and clicks Save (which
    hits PATCH /content) when satisfied.

    Returns:
        {
          "content": "<markdown>",
          "doc_type": "privacy" | "terms",
          "locale":   "it" | "en" | "de" | "fr"
        }

    Org scoping: we load the store doc so we can both verify org
    scope AND fall back to the persisted ``merchant_legal_template_vars``
    when the client omits ``body.vars`` (CG-3-Polish: "Rigenera bozza
    standard" button uses the saved vars without re-asking the wizard).
    """
    org_id = current_user["organization_id"]
    store = await _load_store_for_admin(store_id, org_id)

    # CG-3-Polish: vars resolution order →
    #   1. explicit body.vars                  (wizard active flow)
    #   2. persisted merchant_legal_template_vars (editor "Rigenera")
    #   3. empty TemplateVars()                (defensive — produces a
    #      template with literal placeholders, lets the admin spot
    #      what's missing)
    vars_obj = body.vars
    if vars_obj is None:
        saved = store.get("merchant_legal_template_vars") or {}
        try:
            vars_obj = TemplateVars(**saved)
        except Exception:
            # Stored dict is corrupt — fall back to defaults so the
            # endpoint never 500s on bad data; admin can re-run wizard.
            logger.warning(
                "store_legal.generate_draft: saved template_vars "
                "invalid for store=%s, using defaults", store_id,
            )
            vars_obj = TemplateVars()

    try:
        rendered = render_template(
            doc_type=body.doc_type,
            locale=body.locale,
            vars=vars_obj,
        )
    except FileNotFoundError:
        # Deployment bug — template file missing on disk.
        logger.error(
            "store_legal.generate_draft: template file missing for "
            "doc_type=%s locale=%s", body.doc_type, body.locale,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Template asset missing",
        )
    return {
        "content": rendered,
        "doc_type": body.doc_type,
        "locale": body.locale,
    }


@router.patch("/{store_id}/legal/template-vars")
async def patch_template_vars(
    store_id: str,
    body: PatchTemplateVarsRequest,
    current_user: dict = Depends(require_admin),
):
    """Persist the wizard variables on the store doc.

    These are pure identity / configuration inputs to the template
    service (merchant_name, merchant_email, etc.) — NOT legal content.
    Editing them does NOT bump the legal version_tag nor trigger
    customer re-consent. The admin uses this to update identity data
    once and have it surface across all future "Rigenera bozza"
    operations.

    Returns the updated admin snapshot.
    """
    org_id = current_user["organization_id"]
    await _load_store_for_admin(store_id, org_id)

    # Persist as a plain dict — the TemplateVars pydantic instance
    # already validated the schema on the request body.
    vars_dict = body.vars.model_dump()
    now_iso = _utc_now_iso()
    update_doc = {
        "$set": {
            "merchant_legal_template_vars": vars_dict,
            # Touch updated_at so DB-side index ordering reflects the
            # most recent admin action.
            "updated_at": datetime.now(timezone.utc),
        }
    }
    # CG-3-Polish-2 — strip the deprecated legacy field on writes.
    store_pre = await _load_store_for_admin(store_id, org_id)
    if store_pre.get("merchant_legal_display_locale") is not None:
        update_doc["$unset"] = {"merchant_legal_display_locale": ""}

    await stores_collection.update_one(
        {"id": store_id, "organization_id": org_id},
        update_doc,
    )

    return await get_store_legal(store_id, current_user)


@router.get("/{store_id}/legal")
async def get_store_legal(
    store_id: str,
    current_user: dict = Depends(require_admin),
):
    """Return the full editing snapshot for the admin UI.

    Includes all 8 content slots (privacy/terms × 4 locales), the
    selected display_locale, computed status, and the version metadata.
    The editor uses this single read on mount to populate every tab
    without N+1 calls.
    """
    org_id = current_user["organization_id"]
    store = await _load_store_for_admin(store_id, org_id)

    response = {
        "store_id": store["id"],
        "store_name": store.get("name") or "",
        "store_slug": store.get("slug") or "",
        "store_is_published": store.get("is_published", False),
        "storefront_languages": store.get("storefront_languages") or ["it"],
        # Lifecycle
        # ``display_locale``           — legacy explicit value if set
        #                                (Wave CG-3-Polish deprecated this
        #                                 in favor of effective_display_locale)
        # ``effective_display_locale`` — what the customer actually sees,
        #                                derived from
        #                                ``storefront_languages[0]`` with
        #                                legacy fallback. Frontend uses
        #                                this to mark the "🌟 mostrato ai
        #                                clienti" tab.
        "display_locale": store.get("merchant_legal_display_locale"),
        "effective_display_locale": get_effective_display_locale(store),
        "status": merchant_legal_status(store),
        "version_tag": store.get("merchant_legal_version_tag"),
        "version_hash": store.get("merchant_legal_version_hash"),
        "version_string": current_version_string(store),
        "published_at": store.get("merchant_legal_published_at"),
        "last_edited_at": store.get("merchant_legal_last_edited_at"),
        # CG-3-Polish — persisted wizard variables, surfaced for the
        # editor's "Dati del titolare" panel. None when never set;
        # the frontend renders the wizard form in that case.
        "template_vars": store.get("merchant_legal_template_vars") or None,
    }
    # 8 content slots — explicit fields, no loop, so the response shape
    # is obvious to the frontend type-checker.
    for loc in SUPPORTED_LOCALES:
        response[f"privacy_content_{loc}"] = (
            store.get(f"merchant_privacy_content_{loc}") or ""
        )
        response[f"terms_content_{loc}"] = (
            store.get(f"merchant_terms_content_{loc}") or ""
        )
    return response


@router.patch("/{store_id}/legal/content")
async def patch_legal_content(
    store_id: str,
    body: PatchContentRequest,
    current_user: dict = Depends(require_admin),
):
    """Save ONE content slot (one doc, one locale).

    Saving never bumps the version_tag — that's reserved for the
    publish action so the merchant can iterate freely. We DO update
    ``last_edited_at`` so the status helper can surface "stale_draft"
    state to the admin (something published earlier has unpublished
    edits in progress).

    Returns the post-update snapshot (same shape as GET /legal).
    """
    org_id = current_user["organization_id"]
    store = await _load_store_for_admin(store_id, org_id)

    field = f"merchant_{body.doc_type}_content_{body.locale}"
    now_iso = _utc_now_iso()

    update_doc = {
        "$set": {
            field: body.content,
            "merchant_legal_last_edited_at": now_iso,
            "updated_at": datetime.now(timezone.utc),
        }
    }
    # CG-3-Polish-2: silently clean up the deprecated legacy
    # ``merchant_legal_display_locale`` field on any polish-aware write.
    # This prevents stale CG-3 wizard values from haunting users — once
    # they edit a slot under the polish UI, the legacy field gets unset
    # and ``get_effective_display_locale`` resolves cleanly from
    # ``storefront_languages[0]``.
    if store.get("merchant_legal_display_locale") is not None:
        update_doc["$unset"] = {"merchant_legal_display_locale": ""}

    await stores_collection.update_one(
        {"id": store_id, "organization_id": org_id},
        update_doc,
    )

    # Re-fetch fresh snapshot for the response.
    return await get_store_legal(store_id, current_user)


@router.patch("/{store_id}/legal/display-locale")
async def patch_display_locale(
    store_id: str,
    body: PatchDisplayLocaleRequest,
    current_user: dict = Depends(require_admin),
):
    """DEPRECATED (Wave CG-3-Polish 2026-05-18) — no-op.

    The customer-facing legal locale is now derived automatically from
    the store's ``storefront_languages[0]`` via
    ``services.merchant_legal_versioning.get_effective_display_locale``.
    There is no longer a separate "legal display locale" to set, so
    this endpoint is retained for backward compatibility with stale
    clients but performs NO state change.

    Returns the unchanged admin snapshot. The response shape mirrors
    a successful update so legacy frontends that consume the snapshot
    don't break.

    The admin should change the customer-facing legal language by
    editing the store's primary language in store settings, which
    naturally bumps the hash on next publish.
    """
    org_id = current_user["organization_id"]
    await _load_store_for_admin(store_id, org_id)

    logger.info(
        "store_legal.patch_display_locale: NO-OP (deprecated). "
        "Caller passed locale=%s for store=%s — ignored. The legal "
        "display locale now derives from storefront_languages[0].",
        body.locale, store_id,
    )

    # Return the current snapshot unchanged.
    return await get_store_legal(store_id, current_user)


@router.post("/{store_id}/legal/publish")
async def publish_legal(
    store_id: str,
    body: Optional[PublishRequest] = None,
    current_user: dict = Depends(require_admin),
):
    """Publish the current display-locale content as the customer-facing
    version.

    Behavior (Wave CG-3-Polish):
      - The display locale is auto-derived from
        ``storefront_languages[0]`` (legacy explicit field still
        honoured for backward compat).
      - Requires both privacy AND terms in that locale to be non-empty.
        Otherwise → 422 with a specific actionable message.
      - Computes the bundle hash. If identical to the currently
        published hash, this is a NO-OP (idempotent): we return 200
        with ``no_change=True`` AND a structured ``no_change_reason``
        + ``edited_non_display_locales`` so the frontend can render
        a precise toast ("you edited EN/DE but customers see IT —
        no version bump").
      - Otherwise bumps the version_tag (first publish → "v1.0", else
        minor +1), writes hash + tag + published_at = now.

    Returns the post-publish snapshot + diagnostics flags.
    """
    org_id = current_user["organization_id"]
    store = await _load_store_for_admin(store_id, org_id)

    display = get_effective_display_locale(store)
    if not display:
        # Should never happen because the helper falls back to "it",
        # but defensive: if storefront_languages is empty AND legacy
        # field is unset, refuse with a clear message.
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                "Imposta la lingua primaria del negozio in "
                "'Impostazioni store' prima di pubblicare i documenti "
                "legali."
            ),
        )

    new_hash = compute_legal_hash(store)
    if new_hash is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                "Impossibile pubblicare: la lingua mostrata ai clienti "
                f"({display.upper()}) deve avere sia Privacy che "
                "Termini compilati."
            ),
        )

    current_hash = store.get("merchant_legal_version_hash")
    if current_hash == new_hash:
        # No-op publish — idempotent. CG-3-Polish: enrich the response
        # with WHY there's nothing to publish, so the frontend can
        # disambiguate between:
        #   1. "edited the visible locale but content reverted /
        #       identical text" → "Nessuna modifica da pubblicare"
        #   2. "edited a non-visible locale" → "Hai modificato le tue
        #       traduzioni in EN/DE/FR; quelle non sono ancora
        #       visibili ai clienti (vedono italiano)."
        edited_non_display = _detect_edited_non_display_locales(
            store, display,
        )
        snapshot = await get_store_legal(store_id, current_user)
        snapshot["no_change"] = True
        snapshot["no_change_reason"] = (
            "non_display_edits_only"
            if edited_non_display
            else "identical_content"
        )
        snapshot["edited_non_display_locales"] = edited_non_display
        snapshot["active_locale"] = display
        return snapshot

    new_tag = bump_version_tag(store.get("merchant_legal_version_tag"))
    now_iso = _utc_now_iso()

    publish_update = {
        "$set": {
            "merchant_legal_version_tag": new_tag,
            "merchant_legal_version_hash": new_hash,
            "merchant_legal_published_at": now_iso,
            "updated_at": datetime.now(timezone.utc),
        }
    }
    # CG-3-Polish-2: clean up the deprecated legacy field on publish too.
    if store.get("merchant_legal_display_locale") is not None:
        publish_update["$unset"] = {"merchant_legal_display_locale": ""}

    await stores_collection.update_one(
        {"id": store_id, "organization_id": org_id},
        publish_update,
    )

    logger.info(
        "store_legal.publish: store=%s org=%s bumped to %s:%s "
        "(display_locale=%s)",
        store_id, org_id, new_tag, new_hash, display,
    )
    snapshot = await get_store_legal(store_id, current_user)
    snapshot["no_change"] = False
    snapshot["no_change_reason"] = None
    snapshot["edited_non_display_locales"] = []
    snapshot["active_locale"] = display
    return snapshot


def _detect_edited_non_display_locales(
    store: dict, display_locale: str,
) -> list[str]:
    """Heuristic: return the list of locales (other than display) that
    have non-empty content for BOTH privacy + terms — meaning the
    admin actually filled them in but they're not customer-visible.

    Used by ``publish_legal`` to enrich the no-op response so the
    frontend can guide the user to edit the active locale instead of
    silently swallowing their changes.

    Pure read-only function; no side effects.
    """
    edited = []
    for loc in SUPPORTED_LOCALES:
        if loc == display_locale:
            continue
        priv = (store.get(f"merchant_privacy_content_{loc}") or "").strip()
        terms = (store.get(f"merchant_terms_content_{loc}") or "").strip()
        if priv and terms:
            edited.append(loc)
    return edited
