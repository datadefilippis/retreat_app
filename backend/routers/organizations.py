import logging
import os
from fastapi import APIRouter, HTTPException, status, Depends, Request, UploadFile, File

logger = logging.getLogger(__name__)
from typing import List, Optional
from pydantic import BaseModel, Field, field_validator
from routers.auth import limiter
from models import Organization, UserResponse, UserInvite, UserInviteResponse, User, UserRole, AuditLog
from models.organization import BunnyIntegration, OrgIntegrations, OrgBranding
from auth import get_current_user, get_verified_user, require_admin, get_password_hash
from repositories import organization_repository, user_repository, audit_repository
from services.email_service import send_team_invite
from datetime import datetime, timezone
import secrets


class OrganizationUpdate(BaseModel):
    """Whitelist of fields org-admin may update."""
    name: Optional[str] = Field(default=None, min_length=1, max_length=255)
    industry: Optional[str] = Field(default=None, max_length=100)
    timezone: Optional[str] = Field(default=None, max_length=50)
    currency: Optional[str] = Field(default=None, max_length=10)
    default_iva: Optional[float] = Field(default=None, ge=0, le=100)
    public_slug: Optional[str] = Field(default=None, min_length=3, max_length=50)

    @field_validator('currency', mode='before')
    @classmethod
    def validate_currency(cls, v):
        """Mirror the validator on Organization.currency: accept None or
        an ISO code in the supported set. Immutability (block if orders
        already exist) is enforced at the handler layer where DB access
        is available.
        """
        if v is None or v == "":
            return None
        from services.currency_service import (
            UnsupportedCurrencyError,
            validate_currency_code,
        )
        try:
            return validate_currency_code(v)
        except UnsupportedCurrencyError as e:
            raise ValueError(str(e)) from e

router = APIRouter(prefix="/organizations", tags=["Organizations"])


@router.get("/current", response_model=Organization)
async def get_current_organization(current_user: dict = Depends(get_verified_user)):
    org_doc = await organization_repository.find_by_id(current_user['organization_id'])
    
    if not org_doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found"
        )
    
    # Parse dates
    for field in ['created_at', 'updated_at']:
        if isinstance(org_doc.get(field), str):
            org_doc[field] = datetime.fromisoformat(org_doc[field])
    
    return Organization(**org_doc)


@router.put("/current", response_model=Organization)
async def update_organization(
    org_data: OrganizationUpdate,
    current_user: dict = Depends(require_admin)
):
    update_fields = org_data.model_dump(exclude_none=True)

    # CH compliance v1: currency is immutable once any order exists for
    # the org. First-time set (existing currency is None/empty) is fine;
    # equal values are a no-op; only a real change after orders is blocked.
    if 'currency' in update_fields:
        org_doc_current = await organization_repository.find_by_id(current_user['organization_id'])
        existing_currency = (org_doc_current or {}).get('currency')
        new_currency = update_fields['currency']
        if existing_currency and existing_currency != new_currency:
            from services.currency_service import is_change_allowed_for_org
            if not await is_change_allowed_for_org(current_user['organization_id']):
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail={
                        "code": "currency_change_blocked",
                        "message": "Currency cannot be changed once orders exist for this organization.",
                        "current_currency": existing_currency,
                        "requested_currency": new_currency,
                    },
                )

    # v6.0: Store default_iva inside the flexible settings dict
    if 'default_iva' in update_fields:
        iva_val = update_fields.pop('default_iva')
        org_doc_current = await organization_repository.find_by_id(current_user['organization_id'])
        current_settings = (org_doc_current.get('settings') or {}) if org_doc_current else {}
        current_settings['default_iva'] = iva_val
        update_fields['settings'] = current_settings

    if update_fields:
        update_fields['updated_at'] = datetime.now(timezone.utc).isoformat()
        await organization_repository.update(
            current_user['organization_id'],
            update_fields
        )
        await audit_repository.create(AuditLog(
            organization_id=current_user['organization_id'],
            user_id=current_user['user_id'],
            action="update_org_settings",
            resource_type="organization",
            resource_id=current_user['organization_id'],
            details={"updated_fields": list(update_fields.keys())},
        ))

        # CH compliance v1 — Sub-stream 2.x: when an org switches to CHF
        # *after* Stripe has already been connected, retro-request the
        # ``twint_payments`` capability on the existing Stripe account.
        # New accounts created after this commit already get the
        # capability at creation time. This branch handles the legacy
        # case (account predates the fix) and the merchant-relocates
        # case (org migrating from EUR/IT to CHF/CH).
        #
        # Best-effort: a Stripe API failure here MUST NOT roll back the
        # currency change — the merchant can always retry by toggling
        # currency in settings, and the next "Connetti Stripe" or
        # webhook sync will pick it up. We log + continue.
        if 'currency' in update_fields and update_fields.get('currency') == 'CHF':
            try:
                from services.stripe_connect_express import (
                    ensure_twint_capability_for_org,
                )
                result = await ensure_twint_capability_for_org(
                    current_user['organization_id']
                )
                if result.get("status") == "country_mismatch":
                    # Surface to logs only — we don't want to surprise the
                    # admin in the middle of a "save settings" with an
                    # unrelated Stripe modal. The Settings → Payment
                    # Methods card will already render an "account
                    # country mismatch" hint via the capabilities preflight.
                    pass
            except Exception:
                # Pure best-effort — never break currency save.
                pass

    org_doc = await organization_repository.find_by_id(current_user['organization_id'])

    for field in ['created_at', 'updated_at']:
        if isinstance(org_doc.get(field), str):
            org_doc[field] = datetime.fromisoformat(org_doc[field])

    return Organization(**org_doc)


# ── CH compliance v1: currency info ─────────────────────────────────────────
#
# The frontend setup wizard / settings page calls this before rendering the
# currency selector. The selector becomes read-only when `can_change` is
# false (i.e. orders already exist for the org). We expose `current` and
# `supported` here too so the UI can render labels without duplicating the
# constant list — single source of truth lives in `services.currency_service`.


@router.get("/current/currency-info")
async def get_currency_info(current_user: dict = Depends(get_verified_user)):
    """Return the org's currency state and whether it may still be changed.

    Response:
        {
          "current": "EUR" | "CHF" | None,
          "can_change": bool,
          "supported": ["EUR", "CHF"]
        }
    """
    from services.currency_service import (
        SUPPORTED_CURRENCIES,
        get_currency_for_org,
        is_change_allowed_for_org,
    )

    org_doc = await organization_repository.find_by_id(current_user['organization_id'])
    if not org_doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found",
        )

    raw_currency = org_doc.get('currency')
    return {
        "current": raw_currency if raw_currency else None,
        "effective": get_currency_for_org(org_doc),  # always falls back to default
        "can_change": await is_change_allowed_for_org(current_user['organization_id']),
        "supported": list(SUPPORTED_CURRENCIES),
    }


# ── CH compliance v1 — Sub-stream 2.4: payment capabilities preflight ───────
#
# Reports which payment methods the merchant's connected payment provider
# (Stripe today, Datatrans/PostFinance v1.5) actually has enabled. The
# Settings page reads this to render:
#   - "TWINT active" check vs "Activate TWINT on Stripe →" deep link
#   - Card status (always active when account is connected)
#
# Cached in-process for 5 minutes per (org_id, account_id). Stripe's
# capability dict doesn't change minute-to-minute and the call is a
# round-trip to Stripe's API; we don't want to hammer it on every
# settings page render.

# Module-level cache: {(org_id, account_id) -> (timestamp_iso, payload_dict)}
_capabilities_cache: dict = {}
_CAPABILITIES_TTL_SECONDS = 300  # 5 minutes


@router.get("/current/payment-capabilities")
async def get_payment_capabilities(
    current_user: dict = Depends(get_verified_user),
    force_refresh: bool = False,
):
    """Return the connected payment provider's enabled methods for the org.

    Response shape (always returns 200; never raises Stripe errors at
    callers — those become ``status="error"`` in the body so the UI can
    render a degraded state):

        {
          "provider": "stripe" | "none",
          "connected_account": "acct_xxx" | null,
          "status": "ok" | "not_connected" | "error",
          "error_message": str | null,
          "currency": "EUR" | "CHF",
          "capabilities": {
            "card_active": bool,
            "twint_active": bool,
            "sepa_debit_active": bool,
            "other": {...}
          },
          "active_methods": ["card", "twint"],
          "stripe_dashboard_payment_methods_url": str  # deep link
        }

    Query parameters:
      ``force_refresh`` (bool, default False) — when true, bypass the
      5-min in-process capabilities cache AND invalidate the cached
      entry, forcing a fresh round-trip to the payment provider's API.
      Used by the Settings UI ↻ refresh button so the merchant can
      verify a Stripe-side change (e.g. just toggled TWINT off in their
      dashboard) without waiting out the TTL. Auto-fetches on mount /
      org-change should NOT pass this flag — they benefit from the
      cache hit-rate which keeps Stripe API call volume bounded.
    """
    org_id = current_user['organization_id']
    org_doc = await organization_repository.find_by_id(org_id)
    if not org_doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found",
        )

    from services.currency_service import get_currency_for_org
    from services.payment_checkout_service import _get_connected_account_id
    from payment_providers import (
        AccountCapabilities,
        PaymentProviderRegistry,
        ProviderError,
    )
    from payment_providers.stripe.method_types import resolve_payment_method_types

    org_currency = get_currency_for_org(org_doc)
    connected_account_id = await _get_connected_account_id(org_id)

    # Always-present skeleton; we mutate fields below as we learn more.
    response = {
        "provider": "none",
        "connected_account": connected_account_id,
        "status": "not_connected",
        "error_message": None,
        "currency": org_currency,
        "capabilities": {
            "card_active": False,
            "twint_active": False,
            "sepa_debit_active": False,
            "other": {},
        },
        "active_methods": [],
        "stripe_dashboard_payment_methods_url": "https://dashboard.stripe.com/settings/payment_methods",
    }

    if not connected_account_id:
        return response

    provider = PaymentProviderRegistry.get_for_org(org_doc)
    response["provider"] = provider.name

    # Cache lookup — TTL 5 min keyed by (org_id, account_id). The
    # ``force_refresh`` query param bypasses both the read AND evicts
    # the existing entry so a subsequent un-forced read also gets the
    # fresh value (avoids the "I clicked refresh but the next render
    # showed the stale value again" footgun).
    import time
    cache_key = (org_id, connected_account_id)
    if force_refresh:
        _capabilities_cache.pop(cache_key, None)
    cached = _capabilities_cache.get(cache_key)
    now = time.time()
    if cached and (now - cached[0]) < _CAPABILITIES_TTL_SECONDS:
        caps: AccountCapabilities = cached[1]
    else:
        try:
            caps = await provider.get_account_capabilities(connected_account_id)
            _capabilities_cache[cache_key] = (now, caps)
        except ProviderError as exc:
            response["status"] = "error"
            response["error_message"] = str(exc)
            return response
        except Exception as exc:
            logger.warning(
                "payment_capabilities: unexpected error org=%s err=%s",
                org_id, exc,
            )
            response["status"] = "error"
            response["error_message"] = "Could not reach the payment provider"
            return response

    response["status"] = "ok"
    response["capabilities"] = {
        "card_active": caps.card_active,
        "twint_active": caps.twint_active,
        "sepa_debit_active": caps.sepa_debit_active,
        "other": dict(caps.other),
    }
    response["active_methods"] = list(
        resolve_payment_method_types(org_currency, caps)
    )
    return response


# ── Release 4 (Courses) Step 2: integrations config ─────────────────────────
#
# The Bunny credentials live on the Organization as `integrations.bunny`.
# We expose a dedicated endpoint (instead of widening OrganizationUpdate)
# so these sensitive fields have an explicit audit trail and are not
# accidentally touched by the generic settings form.

class BunnyIntegrationPayload(BaseModel):
    """PATCH payload for integrations.bunny. All fields optional so an
    admin can update the API key without re-sending the library ID.
    Passing every field as null is the canonical way to clear the
    integration (see DELETE endpoint below)."""

    library_id: Optional[str] = Field(default=None, min_length=1, max_length=64)
    api_key: Optional[str] = Field(default=None, min_length=1, max_length=255)
    cdn_hostname: Optional[str] = Field(default=None, max_length=255)
    watermark_enabled: Optional[bool] = None


@router.patch("/current/integrations/bunny", response_model=Organization)
async def update_bunny_integration(
    payload: BunnyIntegrationPayload,
    current_user: dict = Depends(require_admin),
):
    """Create or update the Bunny Stream integration for the current org.

    Merge semantics: existing fields are kept unless overridden. The
    first call must include both library_id and api_key (we cannot
    signature-sign anything without them); subsequent calls may
    update a single field.
    """
    org_id = current_user['organization_id']
    org_doc = await organization_repository.find_by_id(org_id)
    if not org_doc:
        raise HTTPException(status_code=404, detail="Organization not found")

    existing_integrations = (org_doc.get("integrations") or {})
    existing_bunny = (existing_integrations.get("bunny") or {})
    merged = {**existing_bunny, **payload.model_dump(exclude_none=True)}

    # Validate the merged doc through the Pydantic model so a partial
    # update that leaves library_id/api_key empty is still rejected.
    try:
        validated = BunnyIntegration(**merged)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Invalid bunny config: {exc}")

    # ── Auto-verify against Bunny BEFORE persisting (Step 3) ────────────
    # The probe runs synchronously so the response carries the verified
    # status — admin sees the truth immediately without a second click.
    # Bounded by the 5s default timeout in services/bunny/verifier.py
    # (admin worst-case wait: 5s on top of the regular PATCH latency).
    #
    # Decision (invariant D in the plan): the PATCH SUCCEEDS regardless
    # of probe outcome. Bad credentials persist with status=unauthorized
    # so the admin can fix them later without losing partial input. The
    # UI then shows the honest "errato" badge. Blocking the save would
    # be more annoying than helpful (admin might be saving partial work).
    verify_result = await verify_credentials(
        validated.library_id, validated.api_key,
    )

    # Merge probe outcome into the document we're about to save. Stored
    # as flat string + datetime for Mongo simplicity.
    bunny_to_save = validated.model_dump()
    bunny_to_save["last_verified_at"] = datetime.now(timezone.utc).isoformat()
    bunny_to_save["last_verification_status"] = verify_result.status.value
    bunny_to_save["last_verification_error"] = verify_result.error_message
    bunny_to_save["library_name"] = verify_result.library_name
    bunny_to_save["video_count"] = verify_result.video_count

    new_integrations = {**existing_integrations, "bunny": bunny_to_save}
    await organization_repository.update(
        org_id,
        {
            "integrations": new_integrations,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        },
    )
    await audit_repository.create(AuditLog(
        organization_id=org_id,
        user_id=current_user['user_id'],
        action="update_bunny_integration",
        resource_type="organization",
        resource_id=org_id,
        # Never log the api_key value — only record which keys changed
        # AND the verification outcome (useful for debugging "why does
        # this org keep getting unauthorized?").
        details={
            "updated_fields": list(payload.model_dump(exclude_none=True).keys()),
            "verification_status": verify_result.status.value,
        },
    ))

    org_doc = await organization_repository.find_by_id(org_id)
    for field in ['created_at', 'updated_at']:
        if isinstance(org_doc.get(field), str):
            org_doc[field] = datetime.fromisoformat(org_doc[field])
    return Organization(**org_doc)


@router.delete("/current/integrations/bunny", response_model=Organization)
async def clear_bunny_integration(current_user: dict = Depends(require_admin)):
    """Remove the Bunny integration entirely. Existing enrollments stop
    being playable (the play-url endpoint returns 503) but data is
    preserved, so re-enabling later is a single PATCH."""
    org_id = current_user['organization_id']
    org_doc = await organization_repository.find_by_id(org_id)
    if not org_doc:
        raise HTTPException(status_code=404, detail="Organization not found")

    integrations = (org_doc.get("integrations") or {})
    integrations.pop("bunny", None)
    # Empty out the container when no integrations remain, so the
    # Organization document doesn't keep a dangling {} sub-object.
    new_integrations = integrations if integrations else None

    await organization_repository.update(
        org_id,
        {
            "integrations": new_integrations,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        },
    )
    await audit_repository.create(AuditLog(
        organization_id=org_id,
        user_id=current_user['user_id'],
        action="clear_bunny_integration",
        resource_type="organization",
        resource_id=org_id,
        details={},
    ))

    org_doc = await organization_repository.find_by_id(org_id)
    for field in ['created_at', 'updated_at']:
        if isinstance(org_doc.get(field), str):
            org_doc[field] = datetime.fromisoformat(org_doc[field])
    return Organization(**org_doc)


# ── Bunny Stream verification (Step 2 of bunny consolidation) ──────────────
#
# Two endpoints for honest connection status:
#
#   POST /current/integrations/bunny/test   — probe (does NOT persist).
#       Body optional: if omitted, tests the saved credentials. With a
#       payload, tests the supplied values without touching the DB
#       (used by the frontend "Testa connessione" button before save).
#
#   GET  /current/integrations/bunny/status — last cached status.
#       Read-only; returns whatever the last successful probe (manual or
#       auto-on-PATCH) recorded. No auth audit log.
#
# The actual auto-verification on PATCH is wired in Step 3.

from services.bunny import verify_credentials, BunnyStatus
from routers.auth import limiter as _bunny_limiter


@router.post("/current/integrations/bunny/test")
@_bunny_limiter.limit("10/minute")
async def test_bunny_connection(
    request: Request,
    payload: Optional[BunnyIntegrationPayload] = None,
    current_user: dict = Depends(require_admin),
):
    """Probe Bunny once with the supplied (or saved) credentials.

    Returns `{status, library_name, video_count, error_message}`. No
    DB write — this is an explicit "test before save" / "test current
    config" affordance. Rate-limited to 10/minute so an admin clicking
    rapidly is fine but a script can't hammer Bunny on our behalf.

    Resolution rule: if the payload supplies a field, use it; else fall
    back to the saved value. This lets the frontend test partial edits
    (e.g. "I changed only the api_key, test that against the saved
    library_id") without forcing a round-trip to fetch the saved doc.
    """
    org_id = current_user["organization_id"]
    org_doc = await organization_repository.find_by_id(org_id)
    if not org_doc:
        raise HTTPException(status_code=404, detail="Organization not found")

    saved = (org_doc.get("integrations") or {}).get("bunny") or {}
    overrides = payload.model_dump(exclude_none=True) if payload else {}

    library_id = overrides.get("library_id") or saved.get("library_id")
    api_key = overrides.get("api_key") or saved.get("api_key")

    result = await verify_credentials(library_id, api_key)
    return {
        "status": result.status.value,
        "library_name": result.library_name,
        "video_count": result.video_count,
        "error_message": result.error_message,
    }


@router.get("/current/integrations/bunny/status")
async def get_bunny_status(current_user: dict = Depends(get_verified_user)):
    """Read the last cached verification status.

    Open to any authenticated org user (not just admin) so admin-side
    panels rendering the Bunny widget can fetch the status without
    bumping the role gate. Mutations stay admin-only (PATCH/DELETE/test).

    Returns NOT_CONFIGURED when the integration is missing entirely —
    distinct from "configured but never tested". The frontend uses
    this to render "Mai testato" vs "Errato" vs "Connesso".
    """
    org_id = current_user["organization_id"]
    org_doc = await organization_repository.find_by_id(org_id)
    if not org_doc:
        raise HTTPException(status_code=404, detail="Organization not found")

    bunny = (org_doc.get("integrations") or {}).get("bunny") or {}
    if not bunny.get("library_id") or not bunny.get("api_key"):
        return {
            "status": BunnyStatus.NOT_CONFIGURED.value,
            "last_verified_at": None,
            "library_name": None,
            "video_count": None,
            "error_message": None,
        }

    return {
        "status": bunny.get("last_verification_status"),  # may be None for legacy orgs
        "last_verified_at": bunny.get("last_verified_at"),
        "library_name": bunny.get("library_name"),
        "video_count": bunny.get("video_count"),
        "error_message": bunny.get("last_verification_error"),
    }


# ── Multi-library Bunny endpoints (Step 5 of multi-library feature) ──────
#
# Manages `org.integrations.bunny_libraries[]` — N independent libraries
# per org, each with its own credentials + verification status. The
# legacy single-library `org.integrations.bunny` field is untouched by
# these endpoints (it's reachable only through the older PATCH/DELETE
# /bunny endpoints above). Migration from legacy to multi-library is
# explicit via POST /migrate-legacy.
#
# Pattern mirrors the legacy single-library block:
#   • Auto-verify on POST + PATCH (status persisted on the library doc)
#   • POST /test for probe-without-save (rate-limited 10/min)
#   • POST /default to mark a library as the org default
#   • DELETE blocks (409) when the library is referenced by lessons
#     — admin sees the count + must clear references first
#
# All endpoints require admin role except GET (status visibility for
# course editor sidebar widgets).

from models.organization import BunnyLibrary as _BunnyLibrary  # alias to avoid
                                                               # shadowing


class BunnyLibraryCreatePayload(BaseModel):
    """POST /libraries body. Every credential field required at create;
    aliases must be unique within the org (enforced server-side).
    `is_default` defaults False; the FIRST library created on an org
    is auto-promoted to default."""

    alias: str = Field(min_length=1, max_length=64)
    library_id: str = Field(min_length=1, max_length=64)
    api_key: str = Field(min_length=1, max_length=255)
    token_security_key: Optional[str] = Field(default=None, max_length=255)
    cdn_hostname: Optional[str] = Field(default=None, max_length=255)
    watermark_enabled: bool = True
    is_default: bool = False


class BunnyLibraryUpdatePayload(BaseModel):
    """PATCH /libraries/{id} body. All fields optional (partial update).
    Cannot change `id` (server-managed) or `is_default` directly via
    PATCH — use POST /default to change the default, which atomically
    clears the flag on all other libraries. Avoids an inconsistent
    state where two libraries are simultaneously default."""

    alias: Optional[str] = Field(default=None, min_length=1, max_length=64)
    library_id: Optional[str] = Field(default=None, min_length=1, max_length=64)
    api_key: Optional[str] = Field(default=None, min_length=1, max_length=255)
    token_security_key: Optional[str] = Field(default=None, max_length=255)
    cdn_hostname: Optional[str] = Field(default=None, max_length=255)
    watermark_enabled: Optional[bool] = None


def _serialize_library(lib: dict) -> dict:
    """Mongo→API mapping. Strips MongoDB internals; api_key + signing
    key are masked as the legacy admin GET doesn't echo them either."""
    return {
        "id": lib.get("id"),
        "alias": lib.get("alias"),
        "is_default": bool(lib.get("is_default")),
        "library_id": lib.get("library_id"),
        # Mask the secrets — legacy single-library status endpoint
        # also masks them, so the frontend already knows what to do.
        "api_key": ("•" * 8 + str(lib.get("api_key"))[-4:]) if lib.get("api_key") else None,
        "token_security_key": (
            "•" * 8 + str(lib.get("token_security_key"))[-4:]
        ) if lib.get("token_security_key") else None,
        "cdn_hostname": lib.get("cdn_hostname"),
        "watermark_enabled": lib.get("watermark_enabled", True),
        # Status fields
        "last_verified_at": lib.get("last_verified_at"),
        "last_verification_status": lib.get("last_verification_status"),
        "last_verification_error": lib.get("last_verification_error"),
        "library_name": lib.get("library_name"),
        "video_count": lib.get("video_count"),
        "created_at": lib.get("created_at"),
        "updated_at": lib.get("updated_at"),
    }


async def _persist_libraries(org_id: str, libraries: list) -> None:
    """Atomic write of the libraries array + bumping org.updated_at.

    We read the current `integrations` sub-document and write it back
    as a whole object instead of using dot-notation
    (`integrations.bunny_libraries`) for the `$set` payload.

    Reason: when an organization document was created (or migrated) with
    `integrations: null` set EXPLICITLY — as opposed to missing — the
    Mongo server rejects a dot-notation $set with
        "Cannot create field 'bunny_libraries' in element {integrations: null}"
    because the path traverses through a null instead of an object.
    Multiple legacy orgs in production carry that shape.

    The other call sites in this file that touch `integrations`
    (PATCH /bunny on line ~159 and ~204, POST /migrate-legacy on
    line ~803) already use this whole-object pattern. This function
    was the lone outlier; bringing it in line eliminates the legacy
    incompatibility and keeps the write semantics uniform.
    """
    org_doc = await organization_repository.find_by_id(org_id) or {}
    # Tolerate both shapes: missing key (KeyError-safe via .get) and
    # explicit `integrations: null` (the bug shape).
    current_integrations = org_doc.get("integrations") or {}
    new_integrations = dict(current_integrations)
    new_integrations["bunny_libraries"] = libraries

    await organization_repository.update(
        org_id,
        {
            "integrations": new_integrations,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        },
    )


@router.get("/current/integrations/bunny/libraries")
async def list_bunny_libraries(current_user: dict = Depends(get_verified_user)):
    """List all Bunny libraries on the current org.

    Open to any authenticated org user so the course editor sidebar
    can render a "library" dropdown without bumping the role gate.
    Returns a list (possibly empty for legacy/never-configured orgs).
    Each entry is masked — secrets never leave the server in full.
    """
    org_id = current_user["organization_id"]
    org_doc = await organization_repository.find_by_id(org_id)
    if not org_doc:
        raise HTTPException(status_code=404, detail="Organization not found")

    libs = (org_doc.get("integrations") or {}).get("bunny_libraries") or []
    return {"libraries": [_serialize_library(l) for l in libs]}


@router.post("/current/integrations/bunny/libraries", status_code=201)
async def create_bunny_library(
    payload: BunnyLibraryCreatePayload,
    current_user: dict = Depends(require_admin),
):
    """Create a new Bunny library on the current org.

    Auto-verifies the credentials before persisting. The library is
    saved REGARDLESS of probe outcome (same invariant as legacy: bad
    creds save with status=unauthorized so the admin can fix later).

    Default-library invariants:
      • If this is the FIRST library → auto-promoted to is_default=True
        (the org always has at least one default when libraries exist)
      • If `payload.is_default=True` → all other libraries lose default
        flag atomically (exactly one default at any time)
    """
    org_id = current_user["organization_id"]
    org_doc = await organization_repository.find_by_id(org_id)
    if not org_doc:
        raise HTTPException(status_code=404, detail="Organization not found")

    integrations = (org_doc.get("integrations") or {})
    libraries = list(integrations.get("bunny_libraries") or [])

    # Alias uniqueness within the org (case-insensitive — admin
    # shouldn't have to remember exact casing).
    new_alias = payload.alias.strip()
    if any(l.get("alias", "").lower() == new_alias.lower() for l in libraries):
        raise HTTPException(
            status_code=409,
            detail=f"Una libreria con alias '{new_alias}' esiste già su questa organizzazione.",
        )

    # Auto-verify — runs the full 3-check diagnostic so the row we
    # persist already reflects whether embed and CDN are healthy. The
    # admin sees the granular status without having to click "Test"
    # right after saving.
    from services.url_builder import PUBLIC_APP_URL
    verify_result = await verify_credentials(
        payload.library_id, payload.api_key,
        token_security_key=payload.token_security_key,
        cdn_hostname=payload.cdn_hostname,
        referrer=PUBLIC_APP_URL,
    )

    # Build the new library doc
    new_lib = _BunnyLibrary(
        alias=new_alias,
        library_id=payload.library_id,
        api_key=payload.api_key,
        token_security_key=payload.token_security_key,
        cdn_hostname=payload.cdn_hostname,
        watermark_enabled=payload.watermark_enabled,
        is_default=payload.is_default,
        last_verified_at=datetime.now(timezone.utc),
        last_verification_status=verify_result.status.value,
        last_verification_error=verify_result.error_message,
        library_name=verify_result.library_name,
        video_count=verify_result.video_count,
    )

    # First library → auto-default. Or explicit `is_default=True` →
    # demote all others atomically.
    if not libraries:
        new_lib.is_default = True
    elif new_lib.is_default:
        for l in libraries:
            l["is_default"] = False

    libraries.append(new_lib.model_dump())
    await _persist_libraries(org_id, libraries)

    await audit_repository.create(AuditLog(
        organization_id=org_id,
        user_id=current_user["user_id"],
        action="create_bunny_library",
        resource_type="organization",
        resource_id=org_id,
        # Never log api_key — record alias + verification outcome.
        details={
            "alias": new_alias,
            "library_id": payload.library_id,
            "verification_status": verify_result.status.value,
            "is_default": new_lib.is_default,
        },
    ))

    return _serialize_library(new_lib.model_dump())


@router.get("/current/integrations/bunny/libraries/{library_id}")
async def get_bunny_library(
    library_id: str,
    current_user: dict = Depends(get_verified_user),
):
    """Read a single library by AFianco-side id."""
    org_id = current_user["organization_id"]
    org_doc = await organization_repository.find_by_id(org_id)
    libs = ((org_doc or {}).get("integrations") or {}).get("bunny_libraries") or []
    for lib in libs:
        if lib.get("id") == library_id:
            return _serialize_library(lib)
    raise HTTPException(status_code=404, detail="Library not found")


@router.patch("/current/integrations/bunny/libraries/{library_id}")
async def update_bunny_library(
    library_id: str,
    payload: BunnyLibraryUpdatePayload,
    current_user: dict = Depends(require_admin),
):
    """Update a library. Re-verifies when credentials change."""
    org_id = current_user["organization_id"]
    org_doc = await organization_repository.find_by_id(org_id)
    if not org_doc:
        raise HTTPException(status_code=404, detail="Organization not found")

    libraries = list((org_doc.get("integrations") or {}).get("bunny_libraries") or [])
    idx = next((i for i, l in enumerate(libraries) if l.get("id") == library_id), None)
    if idx is None:
        raise HTTPException(status_code=404, detail="Library not found")

    incoming = payload.model_dump(exclude_none=True)
    if not incoming:
        return _serialize_library(libraries[idx])  # no-op

    # Alias uniqueness check (excluding the library being updated)
    if "alias" in incoming:
        new_alias = incoming["alias"].strip()
        for i, l in enumerate(libraries):
            if i != idx and l.get("alias", "").lower() == new_alias.lower():
                raise HTTPException(
                    status_code=409,
                    detail=f"Una libreria con alias '{new_alias}' esiste già.",
                )
        incoming["alias"] = new_alias

    # Merge incoming over existing
    target = dict(libraries[idx])
    target.update(incoming)

    # Re-verify only when credentials changed (avoid spurious probes
    # when the admin only renames the alias).
    creds_changed = bool(
        {"library_id", "api_key", "token_security_key"} & set(incoming.keys())
    )
    if creds_changed:
        verify_result = await verify_credentials(
            target.get("library_id"), target.get("api_key"),
        )
        target["last_verified_at"] = datetime.now(timezone.utc).isoformat()
        target["last_verification_status"] = verify_result.status.value
        target["last_verification_error"] = verify_result.error_message
        target["library_name"] = verify_result.library_name
        target["video_count"] = verify_result.video_count

    target["updated_at"] = datetime.now(timezone.utc).isoformat()
    libraries[idx] = target

    await _persist_libraries(org_id, libraries)

    await audit_repository.create(AuditLog(
        organization_id=org_id,
        user_id=current_user["user_id"],
        action="update_bunny_library",
        resource_type="organization",
        resource_id=org_id,
        details={
            "library_alias": target.get("alias"),
            "updated_fields": list(incoming.keys()),
            "reverified": creds_changed,
        },
    ))

    return _serialize_library(target)


@router.delete("/current/integrations/bunny/libraries/{library_id}")
async def delete_bunny_library(
    library_id: str,
    current_user: dict = Depends(require_admin),
):
    """Delete a library. BLOCKED with 409 when lessons reference it.

    Invariant E (multi-library plan): no silent cascade. The admin
    sees the count + must clear references before deletion. We don't
    auto-clear the references because that would silently change
    which library plays the customer's videos.

    When the deleted library was the default and other libraries
    remain, the next-oldest one is auto-promoted to default so the
    "always one default" invariant holds.
    """
    org_id = current_user["organization_id"]
    org_doc = await organization_repository.find_by_id(org_id)
    if not org_doc:
        raise HTTPException(status_code=404, detail="Organization not found")

    libraries = list((org_doc.get("integrations") or {}).get("bunny_libraries") or [])
    idx = next((i for i, l in enumerate(libraries) if l.get("id") == library_id), None)
    if idx is None:
        raise HTTPException(status_code=404, detail="Library not found")

    # Reference check — count lessons that point at this library.
    from database import courses_collection
    referenced = await courses_collection.count_documents({
        "organization_id": org_id,
        "modules.lessons.bunny_library_id": library_id,
    })
    if referenced > 0:
        raise HTTPException(
            status_code=409,
            detail={
                "error": "library_in_use",
                "message": (
                    f"{referenced} {'lezione fa' if referenced == 1 else 'lezioni fanno'} "
                    "riferimento a questa libreria. Riassegnale a un'altra libreria "
                    "(o lasciale senza riferimento per usare la default) prima di eliminarla."
                ),
                "lesson_count": referenced,
            },
        )

    deleted = libraries.pop(idx)
    deleted_was_default = bool(deleted.get("is_default"))

    # Promote next-oldest to default if needed
    if deleted_was_default and libraries:
        # Pick the library with the earliest created_at, defensive
        # against missing timestamps on legacy data.
        def _key(l):
            return l.get("created_at") or ""
        oldest_idx = min(range(len(libraries)), key=lambda i: _key(libraries[i]))
        libraries[oldest_idx]["is_default"] = True

    await _persist_libraries(org_id, libraries)

    await audit_repository.create(AuditLog(
        organization_id=org_id,
        user_id=current_user["user_id"],
        action="delete_bunny_library",
        resource_type="organization",
        resource_id=org_id,
        details={
            "alias": deleted.get("alias"),
            "was_default": deleted_was_default,
        },
    ))

    return {"deleted_id": library_id, "was_default": deleted_was_default}


@router.post("/current/integrations/bunny/libraries/{library_id}/test")
@_bunny_limiter.limit("10/minute")
async def test_bunny_library(
    request: Request,
    library_id: str,
    payload: Optional[BunnyLibraryUpdatePayload] = None,
    current_user: dict = Depends(require_admin),
):
    """Probe a library without persisting.

    Runs the full 3-check diagnostic (API access + embed signing + CDN
    referrer) so the admin sees in one click whether each layer of the
    Bunny pipeline is healthy. Optional payload overrides saved values
    so the admin can validate edits before saving.

    The CDN check uses PUBLIC_APP_URL as the test referrer because that
    is the host customers will actually load the player from. Local-dev
    deployments without PUBLIC_APP_URL set get a meaningful CDN check
    against http://localhost:3000 (the url_builder fallback).

    Rate-limited 10/min like its single-library cousin.
    """
    from services.url_builder import PUBLIC_APP_URL

    org_id = current_user["organization_id"]
    org_doc = await organization_repository.find_by_id(org_id)
    libs = ((org_doc or {}).get("integrations") or {}).get("bunny_libraries") or []
    saved = next((l for l in libs if l.get("id") == library_id), None)
    if not saved:
        raise HTTPException(status_code=404, detail="Library not found")

    overrides = payload.model_dump(exclude_none=True) if payload else {}

    # All four credentials use the same "override-or-saved" rule so the
    # admin can mix-and-match (e.g. only re-pasting the Token Auth Key
    # to verify a fresh value without touching api_key).
    test_lib_id = overrides.get("library_id") or saved.get("library_id")
    test_api_key = overrides.get("api_key") or saved.get("api_key")
    test_token_key = overrides.get("token_security_key") or saved.get("token_security_key")
    test_cdn_host = overrides.get("cdn_hostname") or saved.get("cdn_hostname")

    result = await verify_credentials(
        test_lib_id, test_api_key,
        token_security_key=test_token_key,
        cdn_hostname=test_cdn_host,
        referrer=PUBLIC_APP_URL,
    )
    return {
        "status": result.status.value,
        "library_name": result.library_name,
        "video_count": result.video_count,
        "error_message": result.error_message,
        # New granular fields — frontend renders a 3-line checklist
        "api_check_passed": result.api_check_passed,
        "embed_check_passed": result.embed_check_passed,
        "cdn_check_passed": result.cdn_check_passed,
        "bunny_panel_url": result.bunny_panel_url,
    }


@router.post("/current/integrations/bunny/libraries/{library_id}/default")
async def set_bunny_library_default(
    library_id: str,
    current_user: dict = Depends(require_admin),
):
    """Mark a library as the org default. Atomically clears the flag
    on every other library so exactly one is default at any time."""
    org_id = current_user["organization_id"]
    org_doc = await organization_repository.find_by_id(org_id)
    if not org_doc:
        raise HTTPException(status_code=404, detail="Organization not found")

    libraries = list((org_doc.get("integrations") or {}).get("bunny_libraries") or [])
    if not any(l.get("id") == library_id for l in libraries):
        raise HTTPException(status_code=404, detail="Library not found")

    new_default_alias = None
    for l in libraries:
        l["is_default"] = (l.get("id") == library_id)
        if l["is_default"]:
            new_default_alias = l.get("alias")

    await _persist_libraries(org_id, libraries)

    await audit_repository.create(AuditLog(
        organization_id=org_id,
        user_id=current_user["user_id"],
        action="set_default_bunny_library",
        resource_type="organization",
        resource_id=org_id,
        details={"new_default_alias": new_default_alias},
    ))

    return {"default_id": library_id}


@router.post("/current/integrations/bunny/migrate-legacy")
async def migrate_legacy_bunny(current_user: dict = Depends(require_admin)):
    """One-shot migration: legacy `integrations.bunny` → `bunny_libraries[0]`.

    Idempotent. Behavior:
      • Legacy field absent → 204 (no-op, safe to call repeatedly)
      • Multi-library already populated AND legacy absent → 204
      • Both populated → preserves multi-library, no-op on the legacy
        field (defensive — we don't overwrite admin's intent)
      • Legacy populated, multi-library empty → copies legacy as
        bunny_libraries[0] with alias='Default' + is_default=True,
        clears the legacy field

    The migration is reversible while admin doesn't delete the
    promoted library — the data is identical, just under a new
    structural location.
    """
    org_id = current_user["organization_id"]
    org_doc = await organization_repository.find_by_id(org_id)
    if not org_doc:
        raise HTTPException(status_code=404, detail="Organization not found")

    integrations = dict(org_doc.get("integrations") or {})
    legacy = integrations.get("bunny")
    libraries = integrations.get("bunny_libraries") or []

    if not legacy:
        return {"status": "noop", "message": "Nessuna configurazione Bunny legacy da migrare."}

    if libraries:
        return {
            "status": "noop",
            "message": "Multi-library già configurato; il campo legacy verrà ignorato dal resolver.",
        }

    # Build a BunnyLibrary from the legacy fields. Default alias is
    # readable enough that the admin can rename it later.
    promoted = _BunnyLibrary(
        alias="Default",
        is_default=True,
        library_id=legacy.get("library_id", ""),
        api_key=legacy.get("api_key", ""),
        token_security_key=legacy.get("token_security_key"),
        cdn_hostname=legacy.get("cdn_hostname"),
        watermark_enabled=legacy.get("watermark_enabled", True),
        # Carry over any cached verification status — saves the admin
        # waiting for a re-probe.
        last_verified_at=legacy.get("last_verified_at"),
        last_verification_status=legacy.get("last_verification_status"),
        last_verification_error=legacy.get("last_verification_error"),
        library_name=legacy.get("library_name"),
        video_count=legacy.get("video_count"),
    )

    new_integrations = {
        **integrations,
        "bunny_libraries": [promoted.model_dump()],
        "bunny": None,  # explicitly clear so the resolver no longer falls back
    }
    await organization_repository.update(
        org_id,
        {
            "integrations": new_integrations,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        },
    )

    await audit_repository.create(AuditLog(
        organization_id=org_id,
        user_id=current_user["user_id"],
        action="migrate_bunny_legacy",
        resource_type="organization",
        resource_id=org_id,
        details={"promoted_library_id": promoted.id, "legacy_library_id": legacy.get("library_id")},
    ))

    return {
        "status": "migrated",
        "library": _serialize_library(promoted.model_dump()),
    }


# ── Org-level branding (Step 2 of "olistic settings" feature) ──────────────
#
# Endpoints to read/write the org-wide branding defaults that cascade
# down to every store under this org. Pattern mirrors the Bunny
# integration block above:
#
#   • Dedicated payload model with ALL fields Optional → admins can
#     update one field at a time without re-sending the rest.
#   • Merge semantics: existing values are kept unless overridden.
#   • DELETE clears the entire sub-object (org falls back to platform
#     default for every field).
#   • Logo upload is a separate multipart endpoint mirroring the
#     per-store upload in routers/stores.py:329 (same MIME whitelist,
#     same 2MB limit, file lives under uploads/logos/org/ to avoid
#     name collisions with per-store logos).
#
# All endpoints require admin role. Audit log entries record which
# field names changed, never their values (logos can be PII-adjacent
# in some industries, colors are uninteresting).


class OrgBrandingPayload(BaseModel):
    """PATCH payload for org-level branding. Every field Optional so
    a single PATCH can update one field at a time. Passing every
    field as None is a no-op (use DELETE to actually clear)."""

    logo_url: Optional[str] = Field(default=None, max_length=512)
    brand_color: Optional[str] = Field(default=None, max_length=32)
    brand_color_text: Optional[str] = Field(default=None, max_length=32)
    favicon_url: Optional[str] = Field(default=None, max_length=512)


# ── Logo upload constants ────────────────────────────────────────────────
# Defined here (above the endpoints that consume them) so the
# `clear_org_branding` DELETE — which wipes the file from disk to
# avoid orphans — can reference them without forward-declaration
# tricks. The /uploads/logos/org/ subdirectory keeps these files
# segregated from per-store logos at /uploads/logos/<store_id>.<ext>
# so a colliding org_id and store_id never clobber each other.

ORG_LOGO_DIR = os.path.join(
    os.path.dirname(os.path.dirname(__file__)), "uploads", "logos", "org"
)
ORG_LOGO_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".svg"}
ORG_LOGO_MIMES = {"image/jpeg", "image/png", "image/webp", "image/svg+xml"}
ORG_LOGO_MAX_BYTES = 2 * 1024 * 1024  # 2MB — same as per-store


@router.get("/current/branding")
async def get_org_branding(current_user: dict = Depends(get_verified_user)):
    """Return the org-level branding doc (or empty dict when not yet set).

    Read access is open to any authenticated user of the org so that
    admin-side panels rendering the cascade (e.g. StoreEditor showing
    an "Inherited from global" badge) can read both Store and Org
    branding without a separate role check. Mutations remain admin-only.
    """
    org_id = current_user["organization_id"]
    org_doc = await organization_repository.find_by_id(org_id)
    if not org_doc:
        raise HTTPException(status_code=404, detail="Organization not found")
    branding = (org_doc.get("branding") or {})
    return {
        "logo_url": branding.get("logo_url"),
        "brand_color": branding.get("brand_color"),
        "brand_color_text": branding.get("brand_color_text"),
        "favicon_url": branding.get("favicon_url"),
    }


@router.patch("/current/branding", response_model=Organization)
async def update_org_branding(
    payload: OrgBrandingPayload,
    current_user: dict = Depends(require_admin),
):
    """Create or update the org-level branding sub-object.

    Merge semantics: only the fields explicitly present in the PATCH
    body (i.e. non-None in the payload) are touched. Existing values
    for unspecified fields are preserved. To clear a single field,
    send an explicit empty string ("") — the resolver treats that as
    "explicit clear, do not inherit the field from a higher level".
    """
    org_id = current_user["organization_id"]
    org_doc = await organization_repository.find_by_id(org_id)
    if not org_doc:
        raise HTTPException(status_code=404, detail="Organization not found")

    # Merge with existing values. `exclude_unset=True` would be ideal
    # but Pydantic v2 model_dump doesn't differentiate "absent" from
    # "explicit None" easily — use exclude_none which gives the same
    # effect for our None-default fields.
    existing = (org_doc.get("branding") or {})
    incoming = payload.model_dump(exclude_none=True)
    if not incoming:
        # No-op PATCH: return the current state without touching DB.
        org_doc = await organization_repository.find_by_id(org_id)
        for f in ('created_at', 'updated_at'):
            if isinstance(org_doc.get(f), str):
                org_doc[f] = datetime.fromisoformat(org_doc[f])
        return Organization(**org_doc)

    merged = {**existing, **incoming}

    # Validate the merged doc through the Pydantic model so a
    # malformed value (e.g. brand_color longer than 32 chars) is
    # rejected even when the rest of the body is fine.
    try:
        validated = OrgBranding(**merged)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Invalid branding payload: {exc}")

    await organization_repository.update(
        org_id,
        {
            "branding": validated.model_dump(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        },
    )
    await audit_repository.create(AuditLog(
        organization_id=org_id,
        user_id=current_user["user_id"],
        action="update_org_branding",
        resource_type="organization",
        resource_id=org_id,
        details={"updated_fields": list(incoming.keys())},
    ))

    org_doc = await organization_repository.find_by_id(org_id)
    for f in ('created_at', 'updated_at'):
        if isinstance(org_doc.get(f), str):
            org_doc[f] = datetime.fromisoformat(org_doc[f])
    return Organization(**org_doc)


@router.delete("/current/branding", response_model=Organization)
async def clear_org_branding(current_user: dict = Depends(require_admin)):
    """Remove the entire branding sub-object from the org.

    Stores keep their per-store branding intact — only the cascade's
    inheritance level is removed. The store falls back directly to
    the platform-level default ("AFianco") when its own field is
    None.

    Side effect: the org logo file is also wiped from disk so we
    don't leak storage when the admin "starts over". This mirrors
    the per-store pattern (where a deleted store cleans up its files).
    """
    org_id = current_user["organization_id"]
    org_doc = await organization_repository.find_by_id(org_id)
    if not org_doc:
        raise HTTPException(status_code=404, detail="Organization not found")

    # Delete any logo file currently on disk for this org. Best-effort
    # — if the file is gone or the cleanup fails we still wipe the DB
    # pointer (the inverse — DB clean but file lingering — would leave
    # an orphan, which is what we want to avoid).
    for old_ext in ORG_LOGO_EXTS:
        old_path = os.path.join(ORG_LOGO_DIR, f"{org_id}{old_ext}")
        if os.path.exists(old_path):
            try:
                os.remove(old_path)
            except OSError:
                pass

    await organization_repository.update(
        org_id,
        {
            "branding": None,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        },
    )
    await audit_repository.create(AuditLog(
        organization_id=org_id,
        user_id=current_user["user_id"],
        action="clear_org_branding",
        resource_type="organization",
        resource_id=org_id,
        details={},
    ))

    org_doc = await organization_repository.find_by_id(org_id)
    for f in ('created_at', 'updated_at'):
        if isinstance(org_doc.get(f), str):
            org_doc[f] = datetime.fromisoformat(org_doc[f])
    return Organization(**org_doc)


# ── Org logo upload (multipart) ───────────────────────────────────────────
#
# Mirrors the per-store logo upload at routers/stores.py:329. Files
# live under uploads/logos/org/<org_id>.<ext> so they don't clash with
# per-store logos at uploads/logos/<store_id>.<ext>. The endpoint
# auto-updates `org.branding.logo_url` so the admin doesn't need a
# follow-up PATCH (the only realistic next action after upload).
# Constants (ORG_LOGO_DIR / ORG_LOGO_EXTS / ORG_LOGO_MIMES /
# ORG_LOGO_MAX_BYTES) are defined above so the DELETE-branding
# endpoint can also clean up the file in one go.


@router.post("/current/branding/logo")
@limiter.limit("5/minute")
async def upload_org_logo(
    request: Request,
    file: UploadFile = File(...),
    current_user: dict = Depends(require_admin),
):
    """Upload a logo at the org level. Persists the file under
    uploads/logos/org/<org_id>.<ext> and AUTO-UPDATES
    `org.branding.logo_url` to the new URL so the admin doesn't have
    to issue a follow-up PATCH. Returns the resolved URL for UI preview.

    Auto-update is the right default here because the only useful
    next action after uploading a logo is to set it as the active one.
    The dedicated PATCH still exists for callers that want to point at
    an external CDN URL without uploading a file.

    Rate-limited at 5/minute (matches per-store endpoint) — protects
    against compromised admin tokens hammering the disk with 2MB writes.
    """
    org_id = current_user["organization_id"]
    org_doc = await organization_repository.find_by_id(org_id)
    if not org_doc:
        raise HTTPException(status_code=404, detail="Organization not found")

    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext not in ORG_LOGO_EXTS:
        raise HTTPException(
            status_code=400,
            detail=f"Formato non supportato. Usa: {', '.join(sorted(ORG_LOGO_EXTS))}",
        )
    if file.content_type and file.content_type not in ORG_LOGO_MIMES:
        raise HTTPException(
            status_code=400,
            detail=f"Tipo file non supportato: {file.content_type}",
        )

    contents = await file.read()
    if len(contents) > ORG_LOGO_MAX_BYTES:
        raise HTTPException(status_code=400, detail="Immagine troppo grande. Max 2MB.")

    # Clean up any previous extension for the same org so we don't
    # leave a .png next to a .jpg when the admin replaces the logo.
    os.makedirs(ORG_LOGO_DIR, exist_ok=True)
    for old_ext in ORG_LOGO_EXTS:
        old_path = os.path.join(ORG_LOGO_DIR, f"{org_id}{old_ext}")
        if os.path.exists(old_path):
            try:
                os.remove(old_path)
            except OSError:
                pass

    filename = f"{org_id}{ext}"
    from services.object_storage import save_public_upload
    logo_url = save_public_upload("logos/org", filename, contents,
                                  content_type=f"image/{ext.lstrip('.')}")

    # Auto-set on the org so the next /catalog request picks it up
    # immediately. Merge with any existing branding fields.
    existing = (org_doc.get("branding") or {})
    new_branding = {**existing, "logo_url": logo_url}
    await organization_repository.update(
        org_id,
        {
            "branding": new_branding,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        },
    )
    await audit_repository.create(AuditLog(
        organization_id=org_id,
        user_id=current_user["user_id"],
        action="upload_org_logo",
        resource_type="organization",
        resource_id=org_id,
        details={"filename": filename, "size_bytes": len(contents)},
    ))

    return {"logo_url": logo_url}


@router.delete("/current/branding/logo")
async def delete_org_logo(current_user: dict = Depends(require_admin)):
    """Remove the org-level logo (file + DB pointer). Other branding
    fields (colors, favicon) are preserved — only logo_url is cleared.
    """
    org_id = current_user["organization_id"]
    org_doc = await organization_repository.find_by_id(org_id)
    if not org_doc:
        raise HTTPException(status_code=404, detail="Organization not found")

    # Delete any file extension we might have written. Best-effort —
    # missing files are not an error (they may have been cleaned up
    # manually or never existed).
    for old_ext in ORG_LOGO_EXTS:
        old_path = os.path.join(ORG_LOGO_DIR, f"{org_id}{old_ext}")
        if os.path.exists(old_path):
            try:
                os.remove(old_path)
            except OSError:
                pass

    existing = (org_doc.get("branding") or {})
    new_branding = {**existing, "logo_url": None}
    await organization_repository.update(
        org_id,
        {
            "branding": new_branding,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        },
    )
    await audit_repository.create(AuditLog(
        organization_id=org_id,
        user_id=current_user["user_id"],
        action="delete_org_logo",
        resource_type="organization",
        resource_id=org_id,
        details={},
    ))
    return {"logo_url": None}


@router.get("/team", response_model=List[UserResponse])
async def get_team_members(current_user: dict = Depends(get_verified_user)):
    users = await user_repository.find_by_org(current_user['organization_id'])
    
    result = []
    for user_doc in users:
        created_at = user_doc['created_at']
        if isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at)
        
        result.append(UserResponse(
            id=user_doc['id'],
            email=user_doc['email'],
            name=user_doc['name'],
            role=UserRole(user_doc['role']),
            organization_id=user_doc['organization_id'],
            created_at=created_at,
            is_active=user_doc.get('is_active', True),
            email_verified=user_doc.get('email_verified', False),
        ))
    
    return result


@router.post("/team/invite", response_model=UserInviteResponse)
async def invite_team_member(
    invite_data: UserInvite,
    current_user: dict = Depends(require_admin)
):
    # Guard: system_admin cannot be assigned via this endpoint.
    if invite_data.role.value == "system_admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot assign system_admin role via invite",
        )

    # ── Plan gating: team member limit ────────────────────────────────────
    # v5.8 / Onda 9.L — Switched from plain-string 403 to coded 429 dict so
    # the frontend axios interceptor (api/client.js) recognises this as a
    # quota event and shows <UpgradePaywall> with an upgrade CTA, instead
    # of a generic toast that leaves the admin guessing.
    #
    # v5.8 / Onda 10 Step B.1 — Limit is now read from
    # `commercial_plans.platform_limits.team_members` (admin-editable via
    # catalog UI). The hardcoded `_TEAM_LIMITS_FALLBACK` dict survives only
    # as a defence-in-depth fallback for plan slugs not yet migrated to
    # the catalog (returns 1 by default — the safest choice).
    _TEAM_LIMITS_FALLBACK = {"free": 1, "starter": 2, "core": 5, "pro": 15, "enterprise": -1}
    org_id = current_user['organization_id']
    org_doc = await organization_repository.find_by_id(org_id)
    plan_slug = (org_doc or {}).get("commercial_plan_slug", "free")
    # Read team_members limit from catalog (Step B.1) with fallback.
    from repositories import billing_repository as _br
    plan_doc = await _br.get_commercial_plan(plan_slug) or {}
    platform_limits = plan_doc.get("platform_limits") or {}
    team_limit = platform_limits.get("team_members")
    if team_limit is None:
        team_limit = _TEAM_LIMITS_FALLBACK.get(plan_slug, 1)
    if team_limit != -1:
        members = await user_repository.find_by_org(org_id)
        active_members = len([m for m in members if m.get("is_active", True)])
        if active_members >= team_limit:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail={
                    "code": "QUOTA_EXCEEDED",
                    "module_key": "team",
                    "feature_key": "team_members",
                    "message": (
                        f"Hai raggiunto il limite di {team_limit} membri team del tuo piano. "
                        "Aggiorna il piano per invitare altri."
                    ),
                    "current_count": active_members,
                    "used": active_members,
                    "effective_limit": team_limit,
                    "limit": team_limit,
                },
            )

    # Check if email already exists
    existing = await user_repository.find_by_email(invite_data.email)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )

    # Generate temporary password
    temp_password = secrets.token_urlsafe(12)
    
    user = User(
        email=invite_data.email,
        name=invite_data.name,
        role=invite_data.role,
        organization_id=current_user['organization_id'],
        password_hash=get_password_hash(temp_password),
        # Force the invited user to change the temp password on first login.
        must_change_password=True,
        # v6.0: Auto-verify email — admin invited this user explicitly.
        email_verified=True,
    )
    
    await user_repository.create(user)
    
    # Audit log
    audit = AuditLog(
        organization_id=current_user['organization_id'],
        user_id=current_user['user_id'],
        action="invite_user",
        resource_type="user",
        resource_id=user.id,
        details={"invited_email": invite_data.email, "role": invite_data.role.value}
    )
    await audit_repository.create(audit)
    
    # Send team invite email (non-blocking — failure must not abort the request)
    try:
        org_doc = await organization_repository.find_by_id(current_user['organization_id'])
        org_name = org_doc.get("name", "") if org_doc else ""
        inviter_doc = await user_repository.find_by_id(current_user['user_id'])
        inviter_name = inviter_doc.get("name", "") if inviter_doc else ""
        send_team_invite(invite_data.email, org_name, inviter_name, temp_password, locale=current_user.get("locale", "it"))
    except Exception:
        pass

    # Return temp_password once — the admin must share it out-of-band.
    # It is never stored in plaintext; password_hash is stored instead.
    return UserInviteResponse(
        id=user.id,
        email=user.email,
        name=user.name,
        role=user.role,
        organization_id=user.organization_id,
        created_at=user.created_at,
        is_active=user.is_active,
        email_verified=False,
        temp_password=temp_password
    )


@router.put("/team/{user_id}/role")
async def update_user_role(
    user_id: str,
    role_data: dict,
    current_user: dict = Depends(require_admin)
):
    # Check user exists in same org
    user_doc = await user_repository.find_by_id(user_id)
    
    if not user_doc or user_doc.get('organization_id') != current_user['organization_id']:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Cannot change own role
    if user_id == current_user['user_id']:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot change your own role"
        )
    
    new_role = role_data.get('role')
    # Explicit allowlist: 'system_admin' is intentionally excluded.
    # Org admins can only assign org-level roles; system_admin is a
    # platform-level role that must be set via the CLI script only.
    _ASSIGNABLE_ROLES = {"admin", "user"}
    if new_role not in _ASSIGNABLE_ROLES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid role. Allowed values: {sorted(_ASSIGNABLE_ROLES)}",
        )
    
    await user_repository.update(user_id, {
        "role": new_role,
        "updated_at": datetime.now(timezone.utc).isoformat()
    })

    await audit_repository.create(AuditLog(
        organization_id=current_user['organization_id'],
        user_id=current_user['user_id'],
        action="update_user_role",
        resource_type="user",
        resource_id=user_id,
        details={"new_role": new_role, "target_email": user_doc.get("email")},
    ))

    return {"message": "Role updated successfully"}


@router.delete("/team/{user_id}")
async def remove_team_member(
    user_id: str,
    current_user: dict = Depends(require_admin)
):
    # Check user exists in same org
    user_doc = await user_repository.find_by_id(user_id)
    
    if not user_doc or user_doc.get('organization_id') != current_user['organization_id']:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Cannot remove yourself
    if user_id == current_user['user_id']:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot remove yourself"
        )
    
    # Deactivate instead of delete
    await user_repository.update(user_id, {
        "is_active": False,
        "updated_at": datetime.now(timezone.utc).isoformat()
    })

    await audit_repository.create(AuditLog(
        organization_id=current_user['organization_id'],
        user_id=current_user['user_id'],
        action="deactivate_user",
        resource_type="user",
        resource_id=user_id,
        details={"target_email": user_doc.get("email")},
    ))

    return {"message": "User removed successfully"}


@router.post("/team/{user_id}/reactivate")
async def reactivate_team_member(
    user_id: str,
    current_user: dict = Depends(require_admin)
):
    """Org admin can reactivate a previously deactivated member of their org."""
    user_doc = await user_repository.find_by_id(user_id)

    if not user_doc or user_doc.get('organization_id') != current_user['organization_id']:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    if user_id == current_user['user_id']:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot reactivate yourself (account is already active)"
        )

    if user_doc.get('is_active', True):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User is already active"
        )

    await user_repository.update(user_id, {
        "is_active": True,
        "updated_at": datetime.now(timezone.utc).isoformat()
    })

    await audit_repository.create(AuditLog(
        organization_id=current_user['organization_id'],
        user_id=current_user['user_id'],
        action="reactivate_user",
        resource_type="user",
        resource_id=user_id,
        details={"target_email": user_doc.get("email")},
    ))

    return {"message": "User reactivated successfully"}


# ── F2.0 Profilo pubblico operatore (5/7/2026) ───────────────────────────────
# docs/DIRECTORY_DESIGN_PLAN.md — l'operatore configura la SUA pagina
# /o/:slug: bio, cover, citta'/regione, social, contatti opzionali.
# Vive su organizations.public_profile (dict whitelisted). Il pubblico
# la legge da /public/operator/{slug}.

_PUBLIC_PROFILE_FIELDS = {
    "bio": 600, "city": 80, "region": 40, "cover_url": 500,
    "instagram": 120, "website": 200, "facebook": 200,
    "public_email": 254, "public_phone": 40,
    # PR1 — carta d'identità
    "tagline": 80, "portrait_url": 500, "founded_year": 4,
}

# PR1 — campi LISTA (validati a parte: la whitelist sopra è solo stringhe)
_PP_PHOTOS_MAX = 8
_PP_LANGS = ("it", "en", "de", "fr", "es", "pt")

PROFILE_COVER_DIR = os.path.join(
    os.path.dirname(ORG_LOGO_DIR), "profile-covers",
)


@router.get("/current/public-profile")
async def get_public_profile(current_user: dict = Depends(require_admin)):
    org_doc = await organization_repository.find_by_id(current_user["organization_id"])
    if not org_doc:
        raise HTTPException(status_code=404, detail="Organization not found")
    pp = org_doc.get("public_profile") or {}
    return {**{k: pp.get(k) for k in _PUBLIC_PROFILE_FIELDS},
            "photos": pp.get("photos") or [],
            "languages": pp.get("languages") or [],
            # AN3 — la posizione configurata (autocomplete o geocoding)
            "latitude": pp.get("latitude"),
            "longitude": pp.get("longitude"),
            "show_contacts": bool(pp.get("show_contacts"))}


@router.patch("/current/public-profile")
async def update_public_profile(
    body: dict,
    current_user: dict = Depends(require_admin),
):
    """Whitelist rigida + limiti lunghezza: nessun campo arbitrario
    puo' entrare nel documento org da un endpoint pubblico-facing."""
    updates = {}
    for field, max_len in _PUBLIC_PROFILE_FIELDS.items():
        if field in body:
            val = body[field]
            if val is None or val == "":
                updates[f"public_profile.{field}"] = None
            elif isinstance(val, str):
                updates[f"public_profile.{field}"] = val.strip()[:max_len]
    if "show_contacts" in body:
        updates["public_profile.show_contacts"] = bool(body["show_contacts"])
    # PR1 — liste con validazione dedicata
    if "photos" in body:
        photos = body["photos"] if isinstance(body["photos"], list) else []
        updates["public_profile.photos"] = [
            str(u).strip()[:500] for u in photos
            if isinstance(u, str) and u.strip()
        ][:_PP_PHOTOS_MAX]
    if "languages" in body:
        langs = body["languages"] if isinstance(body["languages"], list) else []
        updates["public_profile.languages"] = [
            l for l in langs if l in _PP_LANGS][:6]
    # AN3 — posizione dell'operatore: lat/lng espliciti (autocomplete
    # località nel form) vincono; validati e trasformati in GeoJSON per
    # l'indice 2dsphere. La scoperta geografica non dipende più dai
    # ritiri futuri: è il PROFILO a dire dove sei.
    lat_raw, lng_raw = body.get("latitude"), body.get("longitude")
    if lat_raw is not None and lng_raw is not None:
        try:
            lat_f, lng_f = float(lat_raw), float(lng_raw)
            if -90 <= lat_f <= 90 and -180 <= lng_f <= 180:
                updates["public_profile.latitude"] = lat_f
                updates["public_profile.longitude"] = lng_f
                updates["public_profile.geo"] = {
                    "type": "Point", "coordinates": [lng_f, lat_f]}
        except (TypeError, ValueError):
            pass

    if not updates:
        raise HTTPException(status_code=400, detail="Nessun campo valido")

    from database import organizations_collection
    await organizations_collection.update_one(
        {"id": current_user["organization_id"]}, {"$set": updates},
    )
    # AN3 — geocoding best-effort: city presente ma niente coordinate
    # (form senza autocomplete, profili vecchi) → stessa cache
    # Nominatim delle occurrence. Mai bloccante.
    await _geocode_profile_if_needed(current_user["organization_id"])
    # GT6 — gradino 0 profilo-first: il primo profilo con bio accende
    # la vetrina pubblica anche senza store ne' prodotti
    await _ensure_public_surface(current_user["organization_id"])
    return await get_public_profile(current_user)


async def _geocode_profile_if_needed(org_id: str) -> None:
    """AN3 — deriva le coordinate del profilo dalla city quando
    l'operatore non le ha fornite. Best-effort: timeout/errori
    assorbiti, il salvataggio del profilo non fallisce mai per il
    geocoding."""
    from database import organizations_collection
    try:
        org = await organizations_collection.find_one(
            {"id": org_id},
            {"_id": 0, "public_profile.city": 1, "public_profile.region": 1,
             "public_profile.latitude": 1})
        pp = (org or {}).get("public_profile") or {}
        if not pp.get("city") or pp.get("latitude") is not None:
            return
        from services.geocoding import geocode, to_geojson
        coords = await geocode(pp.get("region"), city=pp["city"],
                               country="Italia")
        if coords:
            await organizations_collection.update_one(
                {"id": org_id},
                {"$set": {"public_profile.latitude": coords["lat"],
                          "public_profile.longitude": coords["lng"],
                          "public_profile.geo": to_geojson(
                              coords["lat"], coords["lng"])}})
    except Exception:  # noqa: BLE001 — best-effort dichiarato
        pass


async def _ensure_public_surface(org_id: str) -> None:
    """GT6 — la scala del valore parte dalla VETRINA (gradino 0):
    «la tua pagina professionale, gratis, 10 minuti — nessuno Stripe,
    nessun prodotto». Quando l'operatore salva un profilo con bio e
    non ha ancora uno store, gli diamo un indirizzo pubblico:
    public_slug dal nome org + flag legacy is_storefront_published,
    che fanno risolvere /o/{slug} a _resolve_org. Idempotente; con uno
    store attivo non tocca nulla (lo slug vero e' quello dello store).
    """
    from database import organizations_collection, stores_collection
    from models.event_occurrence import slugify

    org = await organizations_collection.find_one(
        {"id": org_id},
        {"_id": 0, "name": 1, "public_slug": 1, "public_profile.bio": 1,
         "store_settings": 1})
    if not org or not (org.get("public_profile") or {}).get("bio"):
        return
    if await stores_collection.find_one(
            {"organization_id": org_id, "is_active": True}, {"_id": 1}):
        return
    updates = {}
    if not org.get("public_slug"):
        base = slugify(org.get("name") or "")[:60] or "operatore"
        slug, n = base, 2
        while await organizations_collection.find_one(
                {"public_slug": slug, "id": {"$ne": org_id}}, {"_id": 1}) \
                or await stores_collection.find_one({"slug": slug}, {"_id": 1}):
            slug = f"{base}-{n}"
            n += 1
        updates["public_slug"] = slug
    ss = org.get("store_settings")
    if not (ss or {}).get("is_storefront_published"):
        # sulle org fresche store_settings e' null: il path puntato
        # fallirebbe (WriteError 28) — si scrive l'oggetto intero
        if isinstance(ss, dict):
            updates["store_settings.is_storefront_published"] = True
        else:
            updates["store_settings"] = {"is_storefront_published": True}
    if updates:
        await organizations_collection.update_one(
            {"id": org_id}, {"$set": updates})


@router.post("/current/public-profile/cover")
@limiter.limit("5/minute")
async def upload_profile_cover(
    request: Request,
    file: UploadFile = File(...),
    current_user: dict = Depends(require_admin),
):
    """Upload cover del profilo — stesso pattern (e stesse difese) del
    logo org: whitelist estensioni/MIME, max 2MB, un file per org."""
    org_id = current_user["organization_id"]
    ext = os.path.splitext(file.filename or "")[1].lower()
    allowed = {".jpg", ".jpeg", ".png", ".webp"}   # niente svg per le cover
    if ext not in allowed:
        raise HTTPException(
            status_code=400,
            detail=f"Formato non supportato. Usa: {', '.join(sorted(allowed))}",
        )
    if file.content_type and file.content_type not in ORG_LOGO_MIMES:
        raise HTTPException(status_code=400,
                            detail=f"Tipo file non supportato: {file.content_type}")
    contents = await file.read()
    if len(contents) > ORG_LOGO_MAX_BYTES:
        raise HTTPException(status_code=400, detail="Immagine troppo grande. Max 2MB.")

    os.makedirs(PROFILE_COVER_DIR, exist_ok=True)
    for old_ext in allowed:
        old = os.path.join(PROFILE_COVER_DIR, f"{org_id}{old_ext}")
        if os.path.exists(old) and old_ext != ext:
            os.remove(old)
    from services.object_storage import save_public_upload
    cover_url = save_public_upload("profile-covers", f"{org_id}{ext}", contents,
                                   content_type=f"image/{ext.lstrip('.')}")
    from database import organizations_collection
    await organizations_collection.update_one(
        {"id": org_id}, {"$set": {"public_profile.cover_url": cover_url}},
    )
    return {"cover_url": cover_url}


# PR1 — ritratto (foto a lato) + galleria: stesse difese della cover.
# Le foto passano dalla pipeline WebP di S6 (save_public_upload).

_PROFILE_IMG_EXT = {".jpg", ".jpeg", ".png", ".webp"}


async def _read_profile_image(file: UploadFile) -> tuple:
    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext not in _PROFILE_IMG_EXT:
        raise HTTPException(
            status_code=400,
            detail=f"Formato non supportato. Usa: {', '.join(sorted(_PROFILE_IMG_EXT))}")
    if file.content_type and file.content_type not in ORG_LOGO_MIMES:
        raise HTTPException(status_code=400,
                            detail=f"Tipo file non supportato: {file.content_type}")
    contents = await file.read()
    if len(contents) > ORG_LOGO_MAX_BYTES:
        raise HTTPException(status_code=400,
                            detail="Immagine troppo grande. Max 2MB.")
    return ext, contents


@router.post("/current/public-profile/portrait")
@limiter.limit("5/minute")
async def upload_profile_portrait(
    request: Request,
    file: UploadFile = File(...),
    current_user: dict = Depends(require_admin),
):
    org_id = current_user["organization_id"]
    ext, contents = await _read_profile_image(file)
    from services.object_storage import save_public_upload
    url = save_public_upload("profile-portraits", f"{org_id}{ext}", contents,
                             content_type=f"image/{ext.lstrip('.')}")
    from database import organizations_collection
    await organizations_collection.update_one(
        {"id": org_id}, {"$set": {"public_profile.portrait_url": url}})
    return {"portrait_url": url}


@router.post("/current/public-profile/photos")
@limiter.limit("10/minute")
async def upload_profile_photo(
    request: Request,
    file: UploadFile = File(...),
    current_user: dict = Depends(require_admin),
):
    """Aggiunge UNA foto alla galleria (max 8: il client manda un file
    per volta, ordine gestito dal PATCH photos)."""
    import uuid as _uuid
    org_id = current_user["organization_id"]
    ext, contents = await _read_profile_image(file)
    from database import organizations_collection
    org = await organizations_collection.find_one(
        {"id": org_id}, {"_id": 0, "public_profile.photos": 1})
    photos = ((org or {}).get("public_profile") or {}).get("photos") or []
    if len(photos) >= _PP_PHOTOS_MAX:
        raise HTTPException(status_code=400,
                            detail=f"Massimo {_PP_PHOTOS_MAX} foto in galleria")
    from services.object_storage import save_public_upload
    url = save_public_upload(
        "profile-photos", f"{org_id}-{_uuid.uuid4().hex[:10]}{ext}", contents,
        content_type=f"image/{ext.lstrip('.')}")
    await organizations_collection.update_one(
        {"id": org_id}, {"$push": {"public_profile.photos": url}})
    return {"photos": photos + [url]}


# ── O2 Onboarding operatore (5/7/2026) ───────────────────────────────────────
# docs/ONBOARDING_PLAN.md — stato SEMPRE derivato dai dati (mai flag):
# chi salta la checklist e fa a modo suo la vede comunque aggiornarsi.

@router.get("/current/onboarding-status")
async def onboarding_status(current_user: dict = Depends(require_admin)):
    from database import (
        event_occurrences_collection,
        payment_connections_collection,
        stores_collection,
    )

    org_id = current_user["organization_id"]
    org_doc = await organization_repository.find_by_id(org_id) or {}

    # 1. Stripe collegato: connection attiva
    conn = await payment_connections_collection.find_one(
        {"organization_id": org_id, "provider": "stripe", "status": "active"},
        {"_id": 1},
    )

    # 2. Store: attivo, o public_slug legacy (org migrate)
    store = await stores_collection.find_one(
        {"organization_id": org_id, "is_active": True},
        {"_id": 0, "slug": 1},
    )
    store_slug = (store or {}).get("slug") or org_doc.get("public_slug")

    # 3/4. Ritiri: creato (anche bozza) / pubblicato
    any_occ = await event_occurrences_collection.find_one(
        {"organization_id": org_id}, {"_id": 1},
    )
    pub_occ = await event_occurrences_collection.find_one(
        {"organization_id": org_id, "status": "published",
         "slug": {"$nin": [None, ""]}},
        {"_id": 0, "slug": 1}, sort=[("start_at", 1)],
    )

    # 5. Profilo: bio + (cover o almeno un social) = "presentabile"
    pp = org_doc.get("public_profile") or {}
    profile_ok = bool(pp.get("bio")) and bool(
        pp.get("cover_url") or pp.get("instagram")
        or pp.get("website") or pp.get("facebook"))

    steps = {
        "stripe_connected": bool(conn),
        # GT6 — store VERO (il gradino 0 profilo-first assegna un
        # public_slug anche senza store: non deve spuntare questo step)
        "store_created": bool(store),
        "retreat_created": bool(any_occ),
        "retreat_published": bool(pub_occ),
        "profile_completed": profile_ok,
    }
    completed = sum(1 for v in steps.values() if v)

    # I link espliciti di dove vivono le pagine (richiesta founder):
    # si mostrano nella card "Sei online!"
    links = {}
    if store_slug:
        # il profilo vive anche sul solo public_slug (gradino 0)
        links["profile"] = f"/o/{store_slug}"
        if store:
            links["store"] = f"/s/{store_slug}"
        if pub_occ:
            links["landing"] = f"/e/{store_slug}/{pub_occ['slug']}"
    links["directory"] = "/ritiri"

    return {"steps": steps, "completed_count": completed,
            "total": len(steps), "is_complete": completed == len(steps),
            "links": links}
