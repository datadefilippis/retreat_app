"""
Models for purchase_records and fixed_costs collections.

These are Phase-1 new collections.  No existing code references them yet –
they are introduced here as a forward-compatible foundation.
"""
from pydantic import BaseModel, Field, ConfigDict, field_validator, BeforeValidator
from typing import Annotated, Optional, List, Dict, Any
from datetime import datetime
from enum import Enum
from .common import generate_id, utc_now
from core.numeric import coerce_locale_number

LocaleFloat = Annotated[float, BeforeValidator(coerce_locale_number)]


def _validate_iso_date(v: Optional[str]) -> Optional[str]:
    """Validate that a string is a valid YYYY-MM-DD date."""
    if v is not None:
        try:
            datetime.strptime(v, '%Y-%m-%d')
        except ValueError:
            raise ValueError(f"Data non valida: '{v}'. Formato atteso: YYYY-MM-DD")
    return v


# ── Purchase Records ──────────────────────────────────────────────────────────

class PaymentStatus(str, Enum):
    PENDING = "pending"
    PAID = "paid"
    OVERDUE = "overdue"
    CANCELLED = "cancelled"


class PurchaseRecordBase(BaseModel):
    date: str                                   # ISO format: YYYY-MM-DD
    supplier_name: Optional[str] = Field(default=None, max_length=255)
    quantity: Optional[LocaleFloat] = Field(default=None, ge=0)
    unit: Optional[str] = Field(default=None, max_length=50)
    unit_price: Optional[LocaleFloat] = Field(default=None, ge=0)
    total_price: Optional[LocaleFloat] = Field(default=None, ge=0)
    amount: Optional[LocaleFloat] = Field(default=None, ge=0)
    supplier_id: Optional[str] = None          # FK → suppliers._id
    product_id: Optional[str] = None           # FK → products._id
    category: Optional[str] = Field(default=None, max_length=100)
    category_macro: Optional[str] = Field(default=None, max_length=100)
    description: Optional[str] = Field(default=None, max_length=1000)
    invoice_number: Optional[str] = Field(default=None, max_length=100)
    payment_status: Optional[PaymentStatus] = None
    due_date: Optional[str] = None             # ISO format
    tags: List[str] = []

    # ── VAT support (Wave A) ────────────────────────────────────────────────
    iva: Optional[LocaleFloat] = Field(default=None, ge=0, le=100)
    total_with_iva: Optional[LocaleFloat] = None

    @field_validator('date', 'due_date', mode='before')
    @classmethod
    def validate_dates(cls, v):
        return _validate_iso_date(v)


class PurchaseRecordCreate(PurchaseRecordBase):
    """Input model for POST /purchase-records. Same fields as PurchaseRecordBase."""
    pass


class PurchaseRecord(PurchaseRecordBase):
    model_config = ConfigDict(extra="ignore")

    id: str = Field(default_factory=generate_id)
    organization_id: str
    dataset_id: Optional[str] = None           # set when imported from a dataset upload
    source_record_id: Optional[str] = None     # original row ID from source file
    source_label: Optional[str] = None         # v3.0: dataset name or "Manuale"
    metadata: Dict[str, Any] = {}
    created_at: datetime = Field(default_factory=utc_now)


class PurchaseRecordUpdate(BaseModel):
    """Partial update model for PATCH /purchases/{id}.

    Note: total_with_iva is NOT accepted here — it is always server-computed.
    The router explicitly strips it before persistence.
    """
    model_config = ConfigDict(extra="ignore")

    date: Optional[str] = None
    supplier_name: Optional[str] = None
    quantity: Optional[LocaleFloat] = None
    unit: Optional[str] = None
    unit_price: Optional[LocaleFloat] = None
    amount: Optional[LocaleFloat] = None
    category: Optional[str] = None
    category_macro: Optional[str] = None
    description: Optional[str] = None
    invoice_number: Optional[str] = None
    due_date: Optional[str] = None
    payment_status: Optional[str] = None
    tags: Optional[List[str]] = None
    iva: Optional[LocaleFloat] = Field(default=None, ge=0, le=100)
    supplier_id: Optional[str] = None
    product_id: Optional[str] = None


class PurchaseRecordResponse(PurchaseRecordBase):
    id: str
    organization_id: str
    dataset_id: Optional[str]
    created_at: datetime


# ── Fixed Costs ───────────────────────────────────────────────────────────────

class CostFrequency(str, Enum):
    MENSILE = "mensile"
    SETTIMANALE = "settimanale"
    TRIMESTRALE = "trimestrale"
    ANNUALE = "annuale"
    UNA_TANTUM = "una_tantum"


class FixedCostBase(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    amount: LocaleFloat = Field(gt=0)
    frequency: CostFrequency = CostFrequency.MENSILE
    category: Optional[str] = Field(default=None, max_length=100)
    description: Optional[str] = Field(default=None, max_length=1000)
    start_date: Optional[str] = None           # ISO format
    end_date: Optional[str] = None             # ISO format; null = ongoing
    tags: List[str] = []
    metadata: Dict[str, Any] = {}

    @field_validator('start_date', 'end_date', mode='before')
    @classmethod
    def validate_dates(cls, v):
        return _validate_iso_date(v)


class FixedCostCreate(FixedCostBase):
    """Input model for POST /fixed-costs. Same fields as FixedCostBase."""
    pass


class FixedCostUpdate(BaseModel):
    """Pydantic model for PATCH /fixed-costs/{id}.

    Only fields present in the request body are applied.
    System fields (id, organization_id, created_at) are intentionally absent.
    """
    model_config = ConfigDict(extra="ignore")

    name: Optional[str] = None
    amount: Optional[LocaleFloat] = None
    frequency: Optional[CostFrequency] = None
    category: Optional[str] = None
    description: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    tags: Optional[List[str]] = None
    metadata: Optional[Dict[str, Any]] = None
    is_active: Optional[bool] = None


class FixedCost(FixedCostBase):
    model_config = ConfigDict(extra="ignore")

    id: str = Field(default_factory=generate_id)
    organization_id: str
    is_active: bool = True
    source_label: Optional[str] = None         # v3.0: dataset name or "Manuale"
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class FixedCostResponse(FixedCostBase):
    id: str
    organization_id: str
    is_active: bool
    created_at: datetime
    updated_at: datetime
