"""
Store Settings Router — merchant store configuration and commerce readiness.

Endpoints:
  GET  /store-settings     — current settings + computed readiness
  PATCH /store-settings    — update store settings

Store settings are embedded in the Organization document as store_settings dict.
Readiness is always computed (derived), never stored.
"""

import logging
from typing import Optional, List
from pydantic import BaseModel, EmailStr, Field
import os
from fastapi import APIRouter, Depends, HTTPException, Request, UploadFile, File, Response
from routers.auth import limiter

from auth import get_current_user, get_verified_user, require_admin
from database import organizations_collection, stores_collection
from models.common import utc_now, generate_id
from models.store import (
    SUPPORTED_FULFILLMENT_MODES,
    validate_string_list_field,
)


# ── Phase 6 (Store consolidation) — legacy deprecation contract ─────────────
#
# `PATCH /store-settings` writes to `organizations.store_settings` (legacy
# embedded). The new architecture stores the same data in
# `stores_collection`. Phase 6 keeps the legacy endpoint FUNCTIONAL but:
#
#   1. Emits IETF deprecation signals (RFC 8594):
#        `Deprecation: true`
#        `Sunset: <future date>`
#        `Link: </api/stores/...>; rel="successor-version"`
#      so OpenAPI clients + browser DevTools surface the migration
#      warning without breaking any caller.
#
#   2. Dual-writes every legacy update to the org's default store in
#      `stores_collection` via `_dual_write_to_default_store`. This
#      keeps both storage paths in sync so:
#        - the email service (which reads stores_collection first)
#          sees the latest branding/contacts
#        - the public storefront (which reads stores_collection via
#          `_resolve_org`) sees the same data the legacy admin saved
#        - a future sunset of `PATCH /store-settings` is a 1-line
#          removal — no data migration needed at that point.
#
# Field mapping legacy → stores_collection:
#   display_name           -> name
#   contact_email          -> contact_email
#   contact_phone          -> contact_phone
#   notification_email     -> notification_email
#   sender_display_name    -> sender_display_name
#   reply_to_email         -> reply_to_email
#   store_description      -> description
#   logo_url               -> logo_url
#   brand_color            -> brand_color
#   brand_color_text       -> brand_color_text
#   seo_title              -> seo_title
#   seo_description        -> seo_description
#   email_delivery         -> email_delivery
#   fulfillment_modes      -> fulfillment_modes
#   is_storefront_published -> is_published

DEPRECATION_SUNSET_DATE = "Sun, 31 May 2026 00:00:00 GMT"

# Mapping for dual-write (Phase 6). Keys are the LEGACY field names,
# values are the new `stores_collection` field names. Only fields whose
# name differs need to be in this map; same-named fields are pass-through.
LEGACY_TO_STORE_FIELD_MAP = {
    "display_name": "name",
    "store_description": "description",
    "is_storefront_published": "is_published",
}


def _map_legacy_field(legacy_name: str) -> str:
    """Translate a `store_settings.<k>` field name to its
    `stores_collection.<k>` equivalent. Used by the dual-write
    helper to keep both storage paths byte-aligned."""
    return LEGACY_TO_STORE_FIELD_MAP.get(legacy_name, legacy_name)


async def _dual_write_to_default_store(org_id: str, legacy_updates: dict) -> None:
    """Mirror a PATCH /store-settings payload onto the org's default store.

    Idempotent and best-effort:
      · Finds the org's default store; if none exists, looks for any
        active store and promotes it (mirrors the migration logic in
        routers/stores._ensure_default_store).
      · If the org has ZERO stores, creates one seeded from the legacy
        org.store_settings — same as the existing migration path.
      · Translates legacy field names to the new schema via
        LEGACY_TO_STORE_FIELD_MAP.
      · NEVER raises: a failure here must not break the legacy endpoint.
        Logs WARNING so the operator can investigate.

    Phase 6 architectural intent: the legacy endpoint becomes a
    redundant frontdoor that keeps writing in parallel. When the sunset
    date arrives and the endpoint is removed, the new endpoint
    `PATCH /stores/{id}` is already the source of truth — zero data
    loss because dual-write has been syncing all along.
    """
    try:
        default_store = await stores_collection.find_one(
            {"organization_id": org_id, "is_default": True, "is_active": True},
            {"_id": 0, "id": 1},
        )

        if not default_store:
            # Try to promote an existing active store first.
            any_active = await stores_collection.find_one(
                {"organization_id": org_id, "is_active": True},
                {"_id": 0, "id": 1},
            )
            if any_active:
                await stores_collection.update_one(
                    {"id": any_active["id"]},
                    {"$set": {"is_default": True, "updated_at": utc_now()}},
                )
                default_store = any_active
            else:
                # No store at all — create one from the org's legacy
                # store_settings. Matches the bootstrap logic in
                # routers/stores._ensure_default_store. We DON'T call
                # that helper directly to avoid a circular import.
                org = await organizations_collection.find_one(
                    {"id": org_id},
                    {"_id": 0, "name": 1, "public_slug": 1, "store_settings": 1},
                )
                if not org:
                    logger.warning(
                        "store_settings dual-write: org=%s not found, skipping",
                        org_id,
                    )
                    return
                ss = org.get("store_settings") or {}
                now = utc_now()
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
                    "storefront_languages": ["it"],  # safe default; admin can change via /stores/{id}
                    "logo_url": ss.get("logo_url"),
                    "brand_color": ss.get("brand_color"),
                    "brand_color_text": ss.get("brand_color_text"),
                    "seo_title": ss.get("seo_title"),
                    "seo_description": ss.get("seo_description"),
                    "is_published": bool(ss.get("is_storefront_published")),
                    "is_default": True,
                    "is_active": True,
                    "created_at": now,
                    "updated_at": now,
                }
                await stores_collection.insert_one(store_doc)
                logger.info(
                    "store_settings dual-write: bootstrapped default store=%s for org=%s",
                    store_doc["id"], org_id,
                )
                default_store = store_doc

        # Translate legacy field names to new schema and apply the update.
        store_updates: dict = {}
        for legacy_k, v in legacy_updates.items():
            new_k = _map_legacy_field(legacy_k)
            store_updates[new_k] = v
        store_updates["updated_at"] = utc_now()

        await stores_collection.update_one(
            {"id": default_store["id"], "organization_id": org_id},
            {"$set": store_updates},
        )
        logger.info(
            "store_settings dual-write: synced %d field(s) to store=%s org=%s",
            len(legacy_updates), default_store["id"], org_id,
        )
    except Exception as e:
        # Critical: never propagate the exception. Legacy endpoint must
        # stay functional even if the new collection has a transient
        # issue (DuplicateKey, network blip, etc).
        logger.warning(
            "store_settings dual-write: FAILED for org=%s (legacy write succeeded, "
            "new collection drifted): %s",
            org_id, e,
        )


def _attach_deprecation_headers(response: Response) -> None:
    """Inject RFC 8594 deprecation signals on the response.

    Clients reading the OpenAPI spec or inspecting browser DevTools
    will see:
      Deprecation: true
      Sunset: <date>
      Link: </api/stores/{id}>; rel="successor-version"
    The frontend admin UI (Phase 6.5) reads the Sunset header to
    drive the deprecation banner."""
    response.headers["Deprecation"] = "true"
    response.headers["Sunset"] = DEPRECATION_SUNSET_DATE
    response.headers["Link"] = '</api/stores>; rel="successor-version"'

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/store-settings", tags=["Store Settings"])


# ── Request/Response Models ────────────────────────────────────────────────

class StoreSettingsUpdate(BaseModel):
    # Public identity
    display_name: Optional[str] = Field(default=None, max_length=255)
    contact_email: Optional[str] = Field(default=None, max_length=255)
    contact_phone: Optional[str] = Field(default=None, max_length=50)
    # Notification routing (covers orders, requests, payments)
    notification_email: Optional[str] = Field(default=None, max_length=255)
    # Customer email config
    sender_display_name: Optional[str] = Field(default=None, max_length=100)
    reply_to_email: Optional[str] = Field(default=None, max_length=255)
    # Store description (public-facing, shown on storefront)
    store_description: Optional[str] = Field(default=None, max_length=500)
    # Branding (v13.0)
    logo_url: Optional[str] = Field(default=None, max_length=500)
    brand_color: Optional[str] = Field(default=None, max_length=7)  # hex: #FF5500
    brand_color_text: Optional[str] = Field(default=None, max_length=7)  # hex for text on brand_color
    # SEO (v13.0)
    seo_title: Optional[str] = Field(default=None, max_length=100)
    seo_description: Optional[str] = Field(default=None, max_length=300)
    # Email delivery model
    email_delivery: Optional[str] = Field(default=None, pattern="^(platform|custom_domain)$")
    # Fulfillment modes supported by this store (v10.0)
    # Subset of: ["shipping", "local_pickup"]. Default: ["shipping"]
    fulfillment_modes: Optional[List[str]] = None
    # Publish control (v11.0) — explicit merchant decision to expose storefront
    is_storefront_published: Optional[bool] = None


# ── Readiness Computation ──────────────────────────────────────────────────


def _is_product_truly_publishable(product: dict) -> bool:
    """Check if a published product is truly usable (no blocking config errors).

    Mirrors the error-level checks from frontend getProductIssues().
    A product is NOT truly publishable if:
      - direct + inquiry (contradictory)
      - direct + fixed but no price (checkout will fail)
    """
    tm = product.get("transaction_mode", "request")
    pm = product.get("price_mode", "fixed")
    price = product.get("unit_price")

    if tm == "direct" and pm == "inquiry":
        return False
    if tm == "direct" and pm == "fixed" and not price and price != 0:
        return False
    return True


async def compute_readiness(org_id: str, org: dict, store: dict) -> dict:
    """Compute commerce readiness from org + store settings + live data.

    Each check has: key, status (ok/missing), blocking (bool), group (str).
    Groups: storefront, trust, commerce.
    """
    from database import products_collection, payment_connections_collection

    checks = []

    # ── Storefront group ───────────────────────────────────────────────────
    # public_slug check removed — slug now lives per-store in stores collection

    has_display = bool(store.get("display_name"))
    checks.append({"key": "display_name", "status": "ok" if has_display else "missing", "blocking": True, "group": "storefront"})

    has_contact = bool(store.get("contact_email"))
    checks.append({"key": "contact_email", "status": "ok" if has_contact else "missing", "blocking": True, "group": "storefront"})

    # ── Trust group ────────────────────────────────────────────────────────
    has_notif = bool(store.get("notification_email"))
    checks.append({"key": "notification_email", "status": "ok" if has_notif else "missing", "blocking": False, "group": "trust"})

    has_reply = bool(store.get("reply_to_email"))
    checks.append({"key": "reply_to_email", "status": "ok" if has_reply else "missing", "blocking": False, "group": "trust"})

    # ── Commerce group ─────────────────────────────────────────────────────

    # Truly publishable: published + active + no blocking config errors
    published_cursor = products_collection.find(
        {"organization_id": org_id, "is_published": True, "is_active": True},
        {"_id": 0, "transaction_mode": 1, "price_mode": 1, "unit_price": 1},
    ).limit(50)
    truly_publishable = 0
    total_published = 0
    has_direct_products = False
    async for prod in published_cursor:
        total_published += 1
        if _is_product_truly_publishable(prod):
            truly_publishable += 1
        if prod.get("transaction_mode") == "direct":
            has_direct_products = True

    # Payment provider: blocking ONLY if published products use direct checkout
    payment_conn = await payment_connections_collection.find_one(
        {"organization_id": org_id, "status": "active", "runtime_status": "ready"},
        {"_id": 0, "id": 1},
    )
    has_payment = payment_conn is not None
    payment_blocking = has_direct_products and not has_payment
    checks.append({"key": "payment_provider", "status": "ok" if has_payment else "missing", "blocking": payment_blocking, "group": "commerce"})

    has_offer = truly_publishable > 0
    checks.append({"key": "publishable_offer", "status": "ok" if has_offer else "missing", "blocking": True, "group": "commerce"})

    # Derive overall
    has_blocking = any(c["status"] == "missing" and c["blocking"] for c in checks)
    has_warnings = any(c["status"] == "missing" and not c["blocking"] for c in checks)

    overall = "blocked" if has_blocking else ("needs_setup" if has_warnings else "ready")

    # Store operational status (derived, never stored)
    # inactive = storefront not publicly accessible (unpublished, no slug, or org deactivated)
    # degraded = storefront accessible but critical config broken
    # live = fully operational and published
    org_active = org.get("is_active", True)
    is_published = bool(store.get("is_storefront_published"))
    # Check if any store with a slug exists (multi-store) or legacy slug on org
    has_any_slug = bool(org.get("public_slug"))
    if not has_any_slug:
        from database import stores_collection
        has_any_slug = bool(await stores_collection.find_one(
            {"organization_id": org_id, "slug": {"$ne": None}, "is_active": True},
            {"_id": 0, "id": 1},
        ))
    if not has_any_slug or not org_active or not is_published:
        store_status = "inactive"
    elif has_blocking:
        store_status = "degraded"
    else:
        store_status = "live"

    return {
        "overall": overall,
        "store_status": store_status,
        "is_storefront_published": is_published,
        "checks": checks,
        "published_products": total_published,
        "publishable_products": truly_publishable,
        "payment_configured": has_payment,
    }


# ── Store Status Transitions ─────────────────────────────────────────────

# Onda 7 — i18n: `CHECK_LABELS` is now a key map; the resolved label
# comes from EMAIL_TRANSLATIONS via _t() so the alert email reads in
# the recipient's locale instead of always shipping Italian copy.
# Keep this mapping (not the labels themselves) close to the link
# suffix table so all check-key concerns live in one place.
CHECK_LABEL_KEYS = {
    "public_slug": "store_alert_check_public_slug",
    "display_name": "store_alert_check_display_name",
    "contact_email": "store_alert_check_contact_email",
    "payment_provider": "store_alert_check_payment_provider",
    "publishable_offer": "store_alert_check_publishable_offer",
}
CHECK_LINKS_SUFFIX = {
    "public_slug": "/settings",
    "display_name": "/store-settings",
    "contact_email": "/store-settings",
    "payment_provider": "/payment-connections",
    "publishable_offer": "/products",
}


async def _resolve_notification_recipient(org_id: str, store: dict) -> Optional[str]:
    """Get the merchant notification email. Falls back to first org admin."""
    email = store.get("notification_email")
    if email:
        return email
    from database import users_collection
    cursor = users_collection.find(
        {"organization_id": org_id, "role": "admin", "is_active": True},
        {"_id": 0, "email": 1},
    )
    admins = await cursor.to_list(5)
    return admins[0].get("email") if admins else None


async def _handle_status_transition(org_id: str, org: dict, store: dict, readiness: dict) -> None:
    """Detect store_status transitions and send appropriate alerts.

    Transition-based: only sends email when store_status actually changes.
    Persists last_known_store_status in store_settings to detect transitions.

    Supported transitions:
      live → degraded:  degradation alert (with blocking issues list)
      degraded → live:  recovery notification (all clear)

    Best-effort: never raises.
    """
    current_status = readiness.get("store_status")
    if not current_status or current_status == "inactive":
        return  # No alerts for inactive stores (setup phase)

    previous_status = store.get("last_known_store_status")

    # No transition → nothing to do
    if current_status == previous_status:
        return

    try:
        from services.email_service import send_email, _wrap_template, _t, APP_URL
        from services.order_email_service import _resolve_user_email_locale

        store_name = store.get("display_name") or org.get("name", "Store")
        sender_name = store.get("sender_display_name") or None
        recipient = await _resolve_notification_recipient(org_id, store)
        if not recipient:
            return

        # Onda 7 — resolve the recipient's locale so the alert reads in
        # their language. user.locale > storefront default > "it".
        locale = await _resolve_user_email_locale(org_id, recipient)
        settings_url = f"{APP_URL}/store-settings"

        # ── live → degraded: degradation alert ──────────────────────────
        if current_status == "degraded" and previous_status in ("live", None):
            blocking = [c for c in readiness.get("checks", []) if c["status"] == "missing" and c["blocking"]]
            if not blocking:
                return

            configure_label = _t("store_alert_configure_link", locale)
            issues_html = ""
            for c in blocking:
                label = _t(CHECK_LABEL_KEYS.get(c["key"], ""), locale) if c["key"] in CHECK_LABEL_KEYS else c["key"]
                link = f'{APP_URL}{CHECK_LINKS_SUFFIX.get(c["key"], "/store-settings")}'
                issues_html += f'<tr><td style="padding:4px 0;color:#dc2626;">&#9888; {label}</td><td style="padding:4px 8px;"><a href="{link}" style="color:#4f5dca;text-decoration:underline;font-size:13px;">{configure_label}</a></td></tr>'

            intro = _t("store_alert_degraded_intro", locale, store_name=store_name)
            outro = _t("store_alert_degraded_outro", locale)
            cta = _t("store_alert_settings_cta", locale)
            subject = _t("store_alert_degraded_subject", locale, store_name=store_name)
            html = _wrap_template(f"""
                <p>{_t("greeting", locale)},</p>
                <p>{intro}</p>
                <table style="width:100%;border-collapse:collapse;margin:12px 0;">
                  {issues_html}
                </table>
                <p>{outro}</p>
                <p style="text-align:center;">
                    <a href="{settings_url}" class="btn">{cta}</a>
                </p>
            """, locale)

            send_email(
                recipient,
                subject,
                html,
                sender_name=sender_name,
            )
            logger.info("store_transition: degraded alert sent to=%s org=%s locale=%s", recipient, org_id, locale)

        # ── degraded → live: recovery notification ──────────────────────
        elif current_status == "live" and previous_status == "degraded":
            intro = _t("store_alert_recovery_intro", locale, store_name=store_name)
            outro = _t("store_alert_recovery_outro", locale)
            cta = _t("store_alert_settings_cta", locale)
            subject = _t("store_alert_recovery_subject", locale, store_name=store_name)
            html = _wrap_template(f"""
                <p>{_t("greeting", locale)},</p>
                <p>{intro}</p>
                <p>{outro}</p>
                <p style="text-align:center;">
                    <a href="{settings_url}" class="btn">{cta}</a>
                </p>
            """, locale)

            send_email(
                recipient,
                subject,
                html,
                sender_name=sender_name,
            )
            logger.info("store_transition: recovery sent to=%s org=%s locale=%s", recipient, org_id, locale)

        # ── Persist new status ──────────────────────────────────────────
        from datetime import datetime, timezone as tz
        await organizations_collection.update_one(
            {"id": org_id},
            {"$set": {
                "store_settings.last_known_store_status": current_status,
                "store_settings.last_status_transition_at": datetime.now(tz.utc).isoformat(),
            }},
        )

    except Exception as e:
        logger.warning("store_transition: failed org=%s: %s", org_id, e)


# ── Endpoints ──────────────────────────────────────────────────────────────

@router.get("")
async def get_store_settings(
    response: Response,
    current_user: dict = Depends(get_verified_user),
):
    """Return current store settings + computed readiness.

    DEPRECATED (Phase 6 / sunset 2026-05-31): prefer
    `GET /stores/{store_id}` for the per-store configuration. This
    endpoint is kept alive for the legacy admin UI; emits RFC 8594
    deprecation headers so callers can plan their migration.
    """
    _attach_deprecation_headers(response)

    org_id = current_user["organization_id"]

    org = await organizations_collection.find_one(
        {"id": org_id},
        {"_id": 0, "id": 1, "name": 1, "public_slug": 1, "is_active": 1, "store_settings": 1},
    )
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")

    store = org.get("store_settings") or {}
    readiness = await compute_readiness(org_id, org, store)

    # Detect status transitions and send alerts (degradation / recovery)
    await _handle_status_transition(org_id, org, store, readiness)

    return {
        "settings": store,
        "org_name": org.get("name"),
        "public_slug": org.get("public_slug"),
        "readiness": readiness,
    }


@router.patch("")
async def update_store_settings(
    body: StoreSettingsUpdate,
    response: Response,
    current_user: dict = Depends(require_admin),
):
    """Update store settings. Admin only.

    DEPRECATED (Phase 6 / sunset 2026-05-31): prefer
    `PATCH /stores/{store_id}`. The legacy admin UI still drives this
    endpoint; every write is mirrored to the org's default store in
    `stores_collection` via dual-write so the two storage paths stay
    byte-aligned until the legacy frontend is retired.
    """
    _attach_deprecation_headers(response)

    org_id = current_user["organization_id"]

    updates = body.model_dump(exclude_unset=True)
    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")

    # Phase 2 (Store consolidation): validate fulfillment_modes with the
    # same rules as PATCH /stores/{id} so the two parallel update
    # surfaces don't drift. Previously this endpoint accepted any payload
    # (e.g. `[]`, `["shipping","shipping"]`, `["air_drop"]`) and quietly
    # persisted it into `org.store_settings.fulfillment_modes`, breaking
    # the storefront fulfillment selector downstream. The shared helper
    # in models.store mirrors the router-level check in stores.py
    # update_store so a regression in either path is caught by the same
    # code.
    if "fulfillment_modes" in updates:
        try:
            validate_string_list_field(
                updates["fulfillment_modes"],
                field_name="fulfillment_modes",
                allowed=SUPPORTED_FULFILLMENT_MODES,
            )
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))

    # v11.0: Publish validation — can only publish if readiness is not blocked
    if updates.get("is_storefront_published") is True:
        org = await organizations_collection.find_one(
            {"id": org_id},
            {"_id": 0, "id": 1, "name": 1, "public_slug": 1, "is_active": 1, "store_settings": 1},
        )
        if not org:
            raise HTTPException(status_code=404, detail="Organization not found")
        store = org.get("store_settings") or {}
        # Apply pending updates to check readiness with the new values
        for k, v in updates.items():
            if k != "is_storefront_published":
                store[k] = v
        readiness = await compute_readiness(org_id, org, store)
        if readiness["overall"] == "blocked":
            raise HTTPException(
                status_code=400,
                detail="Completa le configurazioni necessarie prima di pubblicare lo store.",
            )

    # Ensure store_settings is an object (not null) before nested $set
    await organizations_collection.update_one(
        {"id": org_id, "store_settings": None},
        {"$set": {"store_settings": {}}},
    )

    # Build $set operations for nested store_settings fields
    set_ops = {f"store_settings.{k}": v for k, v in updates.items()}
    set_ops["store_settings.updated_at"] = utc_now().isoformat()
    set_ops["updated_at"] = utc_now()

    result = await organizations_collection.update_one(
        {"id": org_id},
        {"$set": set_ops},
    )

    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Organization not found")

    logger.info("store_settings: updated for org=%s fields=%s", org_id, list(updates.keys()))

    # Phase 6 — dual-write: mirror this payload to the org's default
    # store in stores_collection so the new storage path stays current.
    # Best-effort: any failure inside the helper is logged but doesn't
    # raise — the legacy write already succeeded above.
    await _dual_write_to_default_store(org_id, updates)

    # Return updated settings + readiness
    return await get_store_settings(response, current_user)


LOGO_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "uploads", "logos")
LOGO_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".svg"}
LOGO_MIMES = {"image/jpeg", "image/png", "image/webp", "image/svg+xml"}
LOGO_MAX_SIZE = 2 * 1024 * 1024  # 2MB


@router.post("/logo")
@limiter.limit("5/minute")
async def upload_store_logo(
    request: Request,
    file: UploadFile = File(...),
    current_user: dict = Depends(require_admin),
):
    """Upload store logo image. Replaces existing. Max 2MB."""
    org_id = current_user["organization_id"]

    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext not in LOGO_EXTENSIONS:
        raise HTTPException(status_code=400, detail=f"Formato non supportato. Usa: {', '.join(LOGO_EXTENSIONS)}")
    if file.content_type and file.content_type not in LOGO_MIMES:
        raise HTTPException(status_code=400, detail=f"Tipo file non supportato: {file.content_type}")

    contents = await file.read()
    if len(contents) > LOGO_MAX_SIZE:
        raise HTTPException(status_code=400, detail="Immagine troppo grande. Max 2MB.")

    os.makedirs(LOGO_DIR, exist_ok=True)

    # Cleanup old logos
    for old_ext in LOGO_EXTENSIONS:
        old_path = os.path.join(LOGO_DIR, f"{org_id}{old_ext}")
        if os.path.exists(old_path):
            try:
                os.remove(old_path)
            except OSError:
                pass

    filename = f"{org_id}{ext}"
    from services.object_storage import save_public_upload
    logo_url = save_public_upload("logos", filename, contents,
                                  content_type=f"image/{ext.lstrip('.')}")

    from database import organizations_collection
    from models.common import utc_now
    await organizations_collection.update_one(
        {"id": org_id},
        {"$set": {"store_settings.logo_url": logo_url, "store_settings.updated_at": utc_now()}},
    )

    return {"logo_url": logo_url}
