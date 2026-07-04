"""
Payment Resolution Service — single source of truth for org payment readiness.

Answers the critical question: can this organization accept direct checkout payments?

This service is the ONLY place that should determine checkout availability.
All checkout logic and UI must query this service, not check raw connection records.

Resolution layers:
  1. Connection exists? → connection_exists
  2. Connection configured (status=active)? → connection_configured
  3. Runtime auth verified? → runtime_ready
  4. All conditions met? → checkout_available

Reason codes:
  no_connection        — no payment connection record for this org
  connection_inactive  — connection exists but status != active
  no_default           — connection exists but none is_default
  runtime_unavailable  — connection active but runtime auth not verified
  runtime_needs_auth   — runtime auth flow started but not completed
  runtime_error        — last runtime check failed
  provider_not_configured — global provider SDK not configured
  ready                — all checks pass, checkout can be created
"""

import logging
import os
from typing import Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class PaymentReadiness:
    """Structured result from payment readiness resolution."""
    checkout_available: bool
    connection_exists: bool = False
    connection_configured: bool = False
    runtime_ready: bool = False
    provider: Optional[str] = None
    connection_id: Optional[str] = None
    is_default: bool = False
    reason_code: str = "no_connection"
    reason_message: str = "Nessun provider di pagamento configurato"

    def to_dict(self) -> dict:
        return {
            "checkout_available": self.checkout_available,
            "connection_exists": self.connection_exists,
            "connection_configured": self.connection_configured,
            "runtime_ready": self.runtime_ready,
            "provider": self.provider,
            "connection_id": self.connection_id,
            "is_default": self.is_default,
            "reason_code": self.reason_code,
            "reason_message": self.reason_message,
        }


# ── Reason messages (Italian) ─────────────────────────────────────────────

_REASONS = {
    "no_connection": "Nessun provider di pagamento configurato",
    "connection_inactive": "Connessione pagamento non attiva",
    "no_default": "Nessun provider impostato come predefinito",
    "runtime_unavailable": "Autorizzazione runtime non completata",
    "runtime_needs_auth": "Autorizzazione runtime in corso",
    "runtime_error": "Errore nella verifica del provider",
    "provider_not_configured": "Provider non configurato nel sistema",
    "ready": "Checkout diretto disponibile",
}


async def resolve_org_payment_readiness(org_id: str) -> PaymentReadiness:
    """
    Resolve the complete payment readiness state for an organization.

    This is the single source of truth. All checkout and UI logic
    should call this instead of checking raw connection records.
    """
    from database import payment_connections_collection

    # 1. Find the default connection
    conn = await payment_connections_collection.find_one(
        {"organization_id": org_id, "is_default": True},
        {"_id": 0},
    )

    # No connection at all?
    if not conn:
        # Check if any connection exists (just not default)
        any_conn = await payment_connections_collection.find_one(
            {"organization_id": org_id},
            {"_id": 0, "id": 1},
        )
        if any_conn:
            return PaymentReadiness(
                checkout_available=False,
                connection_exists=True,
                reason_code="no_default",
                reason_message=_REASONS["no_default"],
            )
        return PaymentReadiness(
            checkout_available=False,
            reason_code="no_connection",
            reason_message=_REASONS["no_connection"],
        )

    provider = conn.get("provider", "stripe")
    connection_id = conn.get("id")
    base = PaymentReadiness(
        checkout_available=False,
        connection_exists=True,
        provider=provider,
        connection_id=connection_id,
        is_default=True,
    )

    # 2. Connection configured (status=active)?
    if conn.get("status") != "active":
        base.reason_code = "connection_inactive"
        base.reason_message = _REASONS["connection_inactive"]
        return base

    base.connection_configured = True

    # 3. Runtime status check
    runtime_status = conn.get("runtime_status", "unavailable")

    if runtime_status == "ready":
        # 4. Final check: is the global provider SDK available?
        if provider == "stripe" and not os.environ.get("STRIPE_SECRET_KEY"):
            base.reason_code = "provider_not_configured"
            base.reason_message = _REASONS["provider_not_configured"]
            return base

        base.runtime_ready = True
        base.checkout_available = True
        base.reason_code = "ready"
        base.reason_message = _REASONS["ready"]
        return base

    if runtime_status == "needs_auth":
        base.reason_code = "runtime_needs_auth"
        base.reason_message = _REASONS["runtime_needs_auth"]
        return base

    if runtime_status == "error":
        base.reason_code = "runtime_error"
        base.reason_message = conn.get("runtime_error") or _REASONS["runtime_error"]
        return base

    # Default: unavailable
    base.reason_code = "runtime_unavailable"
    base.reason_message = _REASONS["runtime_unavailable"]
    return base


async def get_org_checkout_readiness(org_id: str) -> dict:
    """Convenience wrapper returning a plain dict for API responses."""
    readiness = await resolve_org_payment_readiness(org_id)
    return readiness.to_dict()
