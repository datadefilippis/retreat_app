"""
Payment Connections Router — org-level payment provider management.

Endpoints:
  GET   /payment-connections                       — list connections for the org
  GET   /payment-connections/status                — truthful readiness check
  POST  /payment-connections/stripe/express/start         — start Express onboarding
  POST  /payment-connections/stripe/express/refresh       — regenerate onboarding link
  POST  /payment-connections/stripe/express/complete      — verify after return
  POST  /payment-connections/stripe/express/dashboard-link — Express dashboard login URL
  POST  /payment-connections                       — create/register a connection (admin)
  PATCH /payment-connections/{id}                  — update connection (admin)
  GET   /payment-connections/history               — connect_type transition audit log (admin)

Note: legacy Standard OAuth endpoints (GET /stripe/connect-url and
POST /stripe/callback) were removed in Block 6 / Fase 10c.
"""

import logging
from typing import Optional
from pydantic import BaseModel
from fastapi import APIRouter, Depends, HTTPException, status

from auth import get_current_user, get_verified_user, require_admin
from models.common import generate_id, utc_now
from services.module_access import check_module_access

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/payment-connections", tags=["Payment Connections"])


class ConnectionCreate(BaseModel):
    provider: str = "stripe"
    display_name: Optional[str] = None
    external_account_id: Optional[str] = None
    is_default: bool = True


class ConnectionUpdate(BaseModel):
    display_name: Optional[str] = None
    external_account_id: Optional[str] = None
    status: Optional[str] = None
    is_default: Optional[bool] = None


@router.get("")
async def list_connections(current_user: dict = Depends(get_verified_user)):
    """List all payment connections for the organization."""
    from database import payment_connections_collection

    org_id = current_user["organization_id"]
    cursor = payment_connections_collection.find(
        {"organization_id": org_id},
        {"_id": 0},
    ).sort("created_at", -1)

    connections = await cursor.to_list(10)
    return {"connections": connections}


@router.get("/status")
async def get_payment_status(current_user: dict = Depends(get_verified_user)):
    """Truthful payment readiness check for this organization.

    Returns the full resolution result from the central payment resolution service.
    This is the only source of truth for checkout availability.
    """
    from services.payment_resolution import get_org_checkout_readiness
    from database import payment_connections_collection

    org_id = current_user["organization_id"]

    readiness = await get_org_checkout_readiness(org_id)

    # Add connection_count for UI context
    total = await payment_connections_collection.count_documents(
        {"organization_id": org_id}
    )
    readiness["connection_count"] = total

    return readiness


# ── Stripe Connect OAuth (legacy Standard) ────────────────────────────────
# Removed in Fase 10c. Endpoints returned:
#   GET  /stripe/connect-url  → 404
#   POST /stripe/callback     → 404
# Frontend equivalents removed in Fase 10b; the service module that
# powered them will be deleted in Fase 10d. Only Express remains.


# ── Stripe Connect Express (Account Links) ────────────────────────────────

@router.post("/stripe/express/start")
async def start_stripe_express(current_user: dict = Depends(require_admin)):
    """Start (or resume) Express onboarding for this organization.

    Creates a fresh Express connected account if none exists, then returns
    a one-time onboarding link. Idempotent — calling it again for an org
    that already has an Express connection regenerates the link.

    v5.8 / Onda 9.Y.0 — Plan-gated. Only orgs whose plan includes
    `commerce.checkout_stripe` (Commerce Starter and above) may begin
    onboarding. Free / Solo orgs receive 403 FEATURE_NOT_AVAILABLE which
    the frontend axios interceptor converts to a paywall modal.
    """
    from services.stripe_connect_express import start_express_onboarding, is_express_configured

    org_id = current_user["organization_id"]

    # Plan gate FIRST — refuse onboarding for orgs whose plan can't
    # actually use Stripe checkout. Avoids creating orphan Stripe Express
    # accounts that the merchant could never receive payments through.
    await check_module_access(org_id, "commerce", "checkout_stripe")

    if not is_express_configured():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Stripe Connect non è configurato nel sistema",
        )

    email = current_user.get("email")

    result = await start_express_onboarding(org_id, email=email)

    if result.get("status") == "error":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result.get("error", "Impossibile avviare onboarding Express"),
        )

    logger.info(
        "payment_connections: Express onboarding started for org=%s account=%s status=%s",
        org_id, result.get("account_id"), result.get("status"),
    )
    return result


@router.post("/stripe/express/refresh")
async def refresh_stripe_express(current_user: dict = Depends(require_admin)):
    """Regenerate an expired Express onboarding link.

    v5.8 / Onda 9.Y.0 — Plan-gated (same gate as /start).
    """
    from services.stripe_connect_express import refresh_express_link, is_express_configured

    org_id = current_user["organization_id"]

    # Plan gate — same rationale as /start. A merchant whose plan no
    # longer includes checkout_stripe (downgraded after onboarding) can
    # still see their existing connection but can't refresh the link.
    await check_module_access(org_id, "commerce", "checkout_stripe")

    if not is_express_configured():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Stripe Connect non è configurato nel sistema",
        )

    result = await refresh_express_link(org_id)

    if result.get("status") == "error":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result.get("error", "Impossibile rigenerare il link di onboarding"),
        )
    return result


@router.post("/stripe/express/complete")
async def complete_stripe_express(current_user: dict = Depends(require_admin)):
    """Verify Express onboarding completion after merchant returns from Stripe.

    v5.8 / Onda 9.Y.0 — Plan-gated (same gate as /start).
    """
    from services.stripe_connect_express import complete_express_onboarding, is_express_configured

    org_id = current_user["organization_id"]

    # Plan gate — refuse to verify/finalize onboarding for orgs without
    # the entitlement. Defence-in-depth: even if /start was somehow
    # bypassed (legacy account, manual webhook), /complete still gates.
    await check_module_access(org_id, "commerce", "checkout_stripe")

    if not is_express_configured():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Stripe Connect non è configurato nel sistema",
        )

    result = await complete_express_onboarding(org_id)

    if result.get("status") == "error":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result.get("error", "Impossibile verificare onboarding Express"),
        )

    logger.info(
        "payment_connections: Express verification for org=%s account=%s runtime=%s",
        org_id, result.get("account_id"), result.get("status"),
    )
    return result


@router.post("/stripe/express/dashboard-link")
async def express_dashboard_link(current_user: dict = Depends(require_admin)):
    """Generate a one-time Stripe Express Dashboard login URL for this org.

    Express accounts don't appear in the merchant's main dashboard.stripe.com,
    so we expose a "open my Stripe dashboard" entry point from AFianco settings.
    URL is short-lived (minutes) and single-use — frontend should open it
    directly in a new tab without caching.

    v5.8 / Onda 9.Y.0 — Plan-gated (same gate as /start).
    """
    from services.stripe_connect_express import create_dashboard_login_link, is_express_configured

    org_id = current_user["organization_id"]

    # Plan gate — even read-only "open my Stripe dashboard" is blocked
    # for orgs that lost the entitlement. Keeps UX consistent: if you
    # can't onboard / receive payments, you don't get the dashboard hop.
    await check_module_access(org_id, "commerce", "checkout_stripe")

    if not is_express_configured():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Stripe Connect non è configurato nel sistema",
        )

    result = await create_dashboard_login_link(org_id)

    if result.get("status") == "error":
        # 400 when no Express connection or account not onboarded yet;
        # upstream Stripe error message is surfaced in detail.
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result.get("error", "Impossibile generare link Dashboard Stripe"),
        )

    logger.info(
        "payment_connections: Express dashboard link issued for org=%s account=%s",
        org_id, result.get("account_id"),
    )
    return result


# ── Generic CRUD ───────────────────────────────────────────────────────────

@router.post("", status_code=status.HTTP_201_CREATED)
async def create_connection(
    body: ConnectionCreate,
    current_user: dict = Depends(require_admin),
):
    """Register a payment provider connection for the organization.

    v5.8 / Onda 9.Y.0 — Plan-gated. Generic CRUD path for non-Stripe
    providers (PayPal, bank transfer, etc.) — same entitlement applies.
    """
    from database import payment_connections_collection
    from models.payment_connection import PAYMENT_PROVIDERS, PaymentConnection

    org_id = current_user["organization_id"]

    # Plan gate — refuse to register ANY payment provider for orgs whose
    # plan doesn't include checkout. Avoids parallel-providers bypass.
    await check_module_access(org_id, "commerce", "checkout_stripe")

    if body.provider not in PAYMENT_PROVIDERS:
        raise HTTPException(status_code=400, detail=f"Provider must be one of {PAYMENT_PROVIDERS}")

    # Check if connection already exists for this provider
    existing = await payment_connections_collection.find_one(
        {"organization_id": org_id, "provider": body.provider},
        {"_id": 0, "id": 1},
    )
    if existing:
        raise HTTPException(status_code=409, detail=f"Connection for {body.provider} already exists")

    # If this is default, unset other defaults
    if body.is_default:
        await payment_connections_collection.update_many(
            {"organization_id": org_id, "is_default": True},
            {"$set": {"is_default": False}},
        )

    now = utc_now()
    conn = PaymentConnection(
        organization_id=org_id,
        provider=body.provider,
        display_name=body.display_name or f"Account {body.provider.capitalize()}",
        external_account_id=body.external_account_id,
        is_default=body.is_default,
        status="active" if body.external_account_id else "pending",
        connected_at=now if body.external_account_id else None,
    )

    doc = conn.model_dump(mode="json")
    await payment_connections_collection.insert_one(doc)
    doc.pop("_id", None)

    logger.info("payment_connections: created %s connection for org=%s", body.provider, org_id)
    return doc


@router.patch("/{connection_id}")
async def update_connection(
    connection_id: str,
    body: ConnectionUpdate,
    current_user: dict = Depends(require_admin),
):
    """Update a payment connection.

    v5.8 / Onda 9.Y.0 — Plan-gated, but with carve-out: orgs whose plan
    no longer includes checkout MUST still be able to *deactivate* their
    existing connections (to disconnect after a downgrade). The gate
    only blocks "activating" / "promoting to default" mutations.
    """
    from database import payment_connections_collection

    org_id = current_user["organization_id"]
    updates = body.model_dump(exclude_unset=True)

    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")

    # Plan gate — only fires for *upgrading* mutations (activate /
    # promote-to-default). Deactivation, rename, account-id edits are
    # always allowed so a downgraded org can still tidy up its config.
    is_upgrading_mutation = (
        updates.get("is_default") is True
        or updates.get("status") == "active"
    )
    if is_upgrading_mutation:
        await check_module_access(org_id, "commerce", "checkout_stripe")

    if "status" in updates and updates["status"] not in ("pending", "active", "disconnected"):
        raise HTTPException(status_code=400, detail="Invalid status")

    # If setting as default, unset others first
    if updates.get("is_default"):
        await payment_connections_collection.update_many(
            {"organization_id": org_id, "is_default": True, "id": {"$ne": connection_id}},
            {"$set": {"is_default": False}},
        )

    # If activating with external_account_id, set connected_at
    if updates.get("status") == "active" and updates.get("external_account_id"):
        updates["connected_at"] = utc_now()

    updates["updated_at"] = utc_now()

    # Capture prior state for audit log (Fase 7b)
    prior = await payment_connections_collection.find_one(
        {"id": connection_id, "organization_id": org_id},
        {"_id": 0, "status": 1, "connect_type": 1, "external_account_id": 1},
    )

    result = await payment_connections_collection.update_one(
        {"id": connection_id, "organization_id": org_id},
        {"$set": updates},
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Connection not found")

    updated = await payment_connections_collection.find_one(
        {"id": connection_id}, {"_id": 0},
    )

    # Fase 7b: record disconnect events (active → disconnected transitions).
    if prior and updates.get("status") == "disconnected" and prior.get("status") != "disconnected":
        try:
            from services.payment_connection_history import (
                record_transition, EVENT_DISCONNECTED,
            )
            await record_transition(
                org_id=org_id,
                event=EVENT_DISCONNECTED,
                to_connect_type=prior.get("connect_type"),
                from_connect_type=prior.get("connect_type"),
                actor_user_id=current_user.get("id"),
                external_account_id=prior.get("external_account_id"),
                metadata={"prior_status": prior.get("status")},
            )
        except Exception:
            pass  # history is best-effort

    return updated


# ── Connection history (Fase 7b) ──────────────────────────────────────────

@router.get("/history")
async def get_connection_history(
    limit: int = 50,
    current_user: dict = Depends(require_admin),
):
    """Return the connect_type transition history for the current org.

    Scoped strictly to the caller's organization — no cross-org leakage.
    Append-only audit log; newest first. Used by admin tooling to answer
    "when was this org migrated off Standard" without resorting to Mongo
    inspection.
    """
    from database import db

    org_id = current_user["organization_id"]
    safe_limit = max(1, min(200, int(limit or 50)))

    cursor = (
        db.payment_connection_history
        .find({"org_id": org_id}, {"_id": 0})
        .sort("created_at", -1)
        .limit(safe_limit)
    )
    events = await cursor.to_list(safe_limit)
    return {"events": events, "count": len(events)}
