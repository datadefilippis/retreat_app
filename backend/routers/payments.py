"""
Payments Router — payment-provider readiness for the admin UI.

Currently exposes a single endpoint, `GET /api/payments/readiness`, used
by the admin product editor to decide whether the "Pagamento diretto"
option can be selected. Without this surface the admin can configure
`transaction_mode="direct"` on a product even though Stripe Connect is
not active for the org — and the storefront then silently falls back
to "request" mode at checkout time, which is confusing.

The router is intentionally thin: all readiness logic lives in
`services/payment_resolution.py`. This file is the HTTP boundary, not
business logic. Future provider additions (PayPal, Sumup) are expected
to slot into the same shape — the `provider` field already lets the
client distinguish, and the contract returned here is provider-agnostic.

Auth: every endpoint requires a logged-in admin user via
`Depends(get_verified_user)`. The org is derived from the user's JWT,
not from a query param, so cross-org reads are impossible.
"""

import logging

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from typing import Optional

from auth import get_current_user, get_verified_user, get_verified_user
from services.payment_resolution import resolve_org_payment_readiness

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/payments", tags=["Payments"])


# ── Response model ──────────────────────────────────────────────────────────
#
# Why a Pydantic model instead of just `to_dict()`:
#   - keeps the public contract pinned (frontend hooks won't drift)
#   - documents the shape in OpenAPI (the admin UI hook reads this)
#   - lets us add a localised `message` and `action_url` without touching
#     the underlying readiness service (those concerns are HTTP-shaped,
#     not domain-shaped).


class PaymentReadinessResponse(BaseModel):
    """Whether the org can accept direct Stripe checkout payments."""

    stripe_configured: bool = Field(
        description=(
            "True when transaction_mode=direct will produce a working "
            "Stripe checkout URL. The admin can flip a product to direct "
            "mode safely. False means the storefront would fall back to "
            "request mode at checkout time."
        ),
    )
    reason_code: str = Field(
        description=(
            "Stable identifier for the readiness state — frontend can "
            "branch on this. See services/payment_resolution.py for the "
            "exhaustive list (no_connection, connection_inactive, "
            "no_default, runtime_unavailable, runtime_needs_auth, "
            "runtime_error, provider_not_configured, ready)."
        ),
    )
    message_it: str = Field(
        description="Human-readable Italian status string for the admin.",
    )
    provider: Optional[str] = Field(
        default=None,
        description=(
            "Identifier of the connected provider (today: 'stripe'). "
            "None when no connection exists yet."
        ),
    )
    action_url: Optional[str] = Field(
        default=None,
        description=(
            "When stripe_configured is False, the in-app destination "
            "the admin should be sent to in order to fix the situation. "
            "Today this always points at the settings/payments page; "
            "the page itself decides whether to start onboarding, "
            "resume an interrupted onboarding, or show a diagnostic."
        ),
    )


# Where to send the admin to resolve a non-ready state. Kept as a constant
# instead of inlined so the route can move (e.g. /settings/billing) with
# a single edit, and so tests can assert on it without a magic string.
_PAYMENTS_SETTINGS_PATH = "/settings/payments"


# ── Endpoint ────────────────────────────────────────────────────────────────


@router.get("/readiness", response_model=PaymentReadinessResponse)
async def get_payment_readiness(
    current_user: dict = Depends(get_verified_user),
) -> PaymentReadinessResponse:
    """Return whether this org can accept direct Stripe checkout payments.

    Read-only, scoped to the user's organization (no `org_id` query param —
    that would be a tenant-isolation hole). No caching at the HTTP layer:
    the underlying Mongo lookup is one indexed read keyed on
    `(organization_id, is_default=true)` and the admin UI calls this at
    most once per page render.
    """
    org_id = current_user["organization_id"]

    readiness = await resolve_org_payment_readiness(org_id)

    # Only expose the action URL when the admin can act on it. A "ready"
    # state shouldn't surface a "go fix this" button to click.
    action_url = None if readiness.checkout_available else _PAYMENTS_SETTINGS_PATH

    return PaymentReadinessResponse(
        stripe_configured=readiness.checkout_available,
        reason_code=readiness.reason_code,
        message_it=readiness.reason_message,
        provider=readiness.provider,
        action_url=action_url,
    )
