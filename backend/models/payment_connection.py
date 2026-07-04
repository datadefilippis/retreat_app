"""
PaymentConnection — organization-level payment provider connection.

Represents a connected payment provider account for an organization.
Each org can have one or more connections (Stripe, PayPal, etc.),
with one marked as the default for direct checkout.

Two-layer status model:
  status (configuration):
    pending       — onboarding started, not yet configured
    active        — admin has configured the connection
    disconnected  — previously configured, now disabled

  runtime_status (readiness for actual checkout):
    unavailable   — no runtime auth exists (default)
    needs_auth    — configuration exists but runtime auth not completed
    ready         — runtime-verified, checkout can be created
    error         — last runtime check failed

Important: status="active" does NOT mean checkout is available.
Only runtime_status="ready" means checkout can actually be created.
"""

from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, Dict, Any, List
from datetime import datetime
from .common import generate_id, utc_now

PAYMENT_PROVIDERS = ("stripe", "paypal")
CONNECTION_STATUSES = ("pending", "active", "disconnected")
RUNTIME_STATUSES = ("unavailable", "needs_auth", "ready", "error")

# Stripe Connect account types.
# "express"   — dedicated child account created by the platform (data isolation = per-platform).
# "standard"  — LEGACY. No new Standard connections are created after Block 6;
#               the value still appears on archived rows and history entries
#               (payment_connection_history) for audit continuity. Kept in
#               the accepted set for pydantic validation of pre-existing data.
CONNECT_TYPES = ("express", "standard")


class PaymentConnectionBase(BaseModel):
    provider: str = "stripe"                          # stripe | paypal
    display_name: Optional[str] = None                # operator-friendly label
    external_account_id: Optional[str] = None         # provider-side account ID
    is_default: bool = False                          # default for direct checkout


class PaymentConnectionCreate(PaymentConnectionBase):
    pass


class PaymentConnection(PaymentConnectionBase):
    model_config = ConfigDict(extra="ignore")

    id: str = Field(default_factory=generate_id)
    organization_id: str
    status: str = "pending"                           # pending | active | disconnected
    runtime_status: str = "unavailable"               # unavailable | needs_auth | ready | error
    runtime_error: Optional[str] = None               # last error message if runtime_status=error
    last_runtime_check_at: Optional[datetime] = None  # when runtime was last verified
    connected_at: Optional[datetime] = None
    # Connect account type. Default is "express" for new records (Block 6).
    # Pre-existing "standard" rows in the DB are preserved — the field set
    # still accepts the value so their validation does not break.
    connect_type: str = "express"
    # Archive flag set by scripts/archive_standard_connections.py (Block 6 / Fase 10a)
    # so legacy Standard rows are hidden from the default queries. Defaults to
    # False for all new records.
    archived: bool = False
    archived_at: Optional[datetime] = None
    # Capability flags, synced from Stripe account.updated webhooks and on-demand
    # retrievals. Populated for Express accounts.
    charges_enabled: bool = False
    payouts_enabled: bool = False
    details_submitted: bool = False
    requirements_currently_due: List[str] = []
    metadata: Dict[str, Any] = {}
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)
