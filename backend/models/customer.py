from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List, Dict, Any
from datetime import datetime
from .common import generate_id, utc_now


class CustomerBase(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    external_id: Optional[str] = None   # ID in an external system (ERP, CRM, etc.)
    email: Optional[str] = Field(default=None, max_length=320)
    phone: Optional[str] = None
    address: Optional[str] = None
    tags: List[str] = []
    metadata: Dict[str, Any] = {}


class CustomerCreate(CustomerBase):
    pass


class CustomerUpdate(BaseModel):
    """Pydantic model for PATCH /customers/{id}.

    Only fields present in the request body are applied.
    System fields (id, organization_id, created_at) are intentionally absent
    so they can never be overwritten by a client.
    """
    model_config = ConfigDict(extra="ignore")

    name: Optional[str] = None
    external_id: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    tags: Optional[List[str]] = None
    metadata: Optional[Dict[str, Any]] = None
    is_active: Optional[bool] = None


class Customer(CustomerBase):
    model_config = ConfigDict(extra="ignore")

    id: str = Field(default_factory=generate_id)
    organization_id: str
    customer_account_id: Optional[str] = None      # FK → customer_accounts.id (v9.0)
    is_active: bool = True

    # ── 2026-05-20 — Marketing opt-in snapshot on the CRM ──────────────────
    #
    # Mirrors the fields with the same name on ``customer_account``. Storing
    # them HERE on the CRM Customer covers both REGISTERED customers (who
    # also have a customer_account) and GUEST customers (who don't), so the
    # admin Customer Insights table can read ONE consistent source-of-truth
    # for the merchant's "is this contact opted-in to marketing?" question.
    #
    # consent_audit remains the immutable legal proof; these fields are the
    # denormalised fast-path read used by:
    #   - Customer Insights table (CI-admin-vis "Marketing" column)
    #   - CSV export with unsubscribe_url (Piece 1b)
    #   - Future segmentation queries ("send my newsletter to all opted-in")
    #
    # Write paths that keep these in sync:
    #   - submit_order_request when body.gdpr_marketing_accepted=True
    #     → $set accepted_marketing_at = now, $set marketing_revoked_at = None
    #   - marketing_consent unsubscribe endpoint
    #     → $set marketing_revoked_at = now
    #   - (future) admin manual toggle on the customer profile slide
    #
    # Optional + nullable → existing customer docs deserialise unchanged.
    accepted_marketing_at: Optional[str] = None    # ISO UTC of last opt-in
    marketing_revoked_at: Optional[str] = None     # ISO UTC of last revoke

    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class CustomerResponse(CustomerBase):
    id: str
    organization_id: str
    customer_account_id: Optional[str] = None
    is_active: bool
    # 2026-05-20 — mirror the marketing snapshot fields so admin-side
    # endpoints (Customer Insights) can read them via the standard
    # response shape.
    accepted_marketing_at: Optional[str] = None
    marketing_revoked_at: Optional[str] = None
    created_at: datetime
    updated_at: datetime
