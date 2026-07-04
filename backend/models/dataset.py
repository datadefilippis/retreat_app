from pydantic import BaseModel, Field, ConfigDict, BeforeValidator
from typing import Annotated, Optional, List, Dict
from datetime import datetime
from enum import Enum
from .common import generate_id, utc_now
from core.numeric import coerce_locale_number

# Reusable annotated type: accepts locale-formatted strings ("1.234,56")
# and coerces them to float before Pydantic's standard float validation.
LocaleFloat = Annotated[float, BeforeValidator(coerce_locale_number)]


class DatasetType(str, Enum):
    SALES = "sales"
    EXPENSES = "expenses"
    PURCHASES = "purchases"
    FIXED_COSTS = "fixed_costs"


class DatasetBase(BaseModel):
    name: str
    dataset_type: DatasetType
    row_count: int = 0


class DatasetCreate(BaseModel):
    name: str
    dataset_type: DatasetType


class Dataset(DatasetBase):
    model_config = ConfigDict(extra="ignore")

    id: str = Field(default_factory=generate_id)
    organization_id: str
    file_path: str
    uploaded_by: str
    created_at: datetime = Field(default_factory=utc_now)
    is_active: bool = True

    # ── Phase-1 additions (all Optional → zero breaking change) ──────────────
    original_filename: Optional[str] = None   # raw filename from the upload
    schema_version: Optional[str] = None      # document schema version tracker
    source_type: Optional[str] = None         # "file_upload" | "api" | "manual"
    tags: Optional[List[str]] = None
    s3_key: Optional[str] = None              # Phase-2: S3 object key (replaces file_path)


class DatasetResponse(DatasetBase):
    id: str
    organization_id: str
    uploaded_by: str
    created_at: datetime
    is_active: bool


class UploadResponse(DatasetResponse):
    """Upload-specific response — extends DatasetResponse with per-upload reporting fields.

    All fields have defaults so existing callers that deserialize as DatasetResponse
    are unaffected.  Future extensions: error_report_url, preview_rows,
    column_mapping_applied.
    """
    errors: List[str] = Field(default_factory=list)
    validation_rows_skipped: int = 0
    validation_rules_active: int = 0
    total_rows_attempted: int = 0   # row_count + validation_rows_skipped + duplicate_rows_skipped
    duplicate_warning: Optional[str] = None  # v3.0: advisory duplicate file warning
    duplicate_rows_skipped: int = 0  # v3.1: rows removed because they already exist in DB
    entity_linking_stats: Optional[Dict[str, int]] = None  # v7.0: match/unresolved counts per entity type


class SalesRecord(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: str = Field(default_factory=generate_id)
    organization_id: str
    dataset_id: str
    date: str  # ISO format date
    amount: float
    category: Optional[str] = None
    description: Optional[str] = None
    channel: Optional[str] = None

    # ── Phase-1 additions (all Optional → zero breaking change) ──────────────
    source_record_id: Optional[str] = None    # original row identifier from source file
    customer_id: Optional[str] = None         # FK → customers._id (future linkage)
    product_id: Optional[str] = None          # FK → products._id (future linkage)
    tags: Optional[List[str]] = None

    # ── v2.1 cash-basis fields (all Optional → zero breaking change) ─────────
    payment_status: Optional[str] = None      # "paid" | "pending" | "overdue"
    payment_date: Optional[str] = None        # ISO date — when cash was actually received

    # ── v2.4 scadenzario (all Optional → zero breaking change) ───────────────
    due_date: Optional[str] = None            # ISO date — payment due date

    # ── v3.0 source tracking ──────────────────────────────────────────────────
    source_label: Optional[str] = None        # Dataset name or "Manuale"

    # ── Wave 1 (W1.S7) — per-sale cost snapshot ─────────────────────────────
    # 2026-05-20: the Performance Prodotti page aggregates ``$sum cost_at_sale``
    # to compute period-filtered margin. Until now the field was READ but
    # never WRITTEN, so every aggregate came out as 0. order_service now
    # populates this at confirm-order time using CostResolver against the
    # product's cost_source — so the snapshot reflects what the merchant
    # had configured at the moment of sale (historically accurate).
    #
    # Per-unit cost (each SalesRecord is 1 unit by repo convention —
    # quantities >1 explode into N records by ``order_service``).
    # Optional + nullable for backward compat: legacy records without
    # the field still deserialize cleanly and the $ifNull guard in the
    # aggregations keeps the existing math intact.
    cost_at_sale: Optional[float] = None


class ExpenseRecord(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: str = Field(default_factory=generate_id)
    organization_id: str
    dataset_id: str
    date: str  # ISO format date
    amount: float
    category: Optional[str] = None
    description: Optional[str] = None
    supplier: Optional[str] = None

    # ── Phase-1 additions (all Optional → zero breaking change) ──────────────
    source_record_id: Optional[str] = None    # original row identifier from source file
    supplier_id: Optional[str] = None         # FK → suppliers._id (future linkage)
    product_id: Optional[str] = None          # FK → products._id (future linkage)
    tags: Optional[List[str]] = None
    is_fixed: Optional[bool] = None           # True if this maps to a known fixed cost

    # ── v2.1 cash-basis fields (all Optional → zero breaking change) ─────────
    is_paid: Optional[bool] = None            # True when payment has been made
    payment_date: Optional[str] = None        # ISO date — when cash was actually paid out

    # ── v3.0 source tracking ──────────────────────────────────────────────────
    source_label: Optional[str] = None        # Dataset name or "Manuale"


class PurchaseRecord(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: str = Field(default_factory=generate_id)
    organization_id: str
    dataset_id: Optional[str] = None
    date: str  # ISO format date
    supplier_name: str
    quantity: float
    unit: str = "kg"  # kg, pezzi, metri, litri
    unit_price: float
    total_price: float  # quantity * unit_price
    category: Optional[str] = None
    category_macro: Optional[str] = None     # Macro category (Wave A.1)
    description: Optional[str] = None
    source_record_id: Optional[str] = None
    source_label: Optional[str] = None        # Dataset name or "Manuale"
    supplier_id: Optional[str] = None         # FK → suppliers._id
    product_id: Optional[str] = None          # FK → products._id

    # ── VAT support (Wave A) ────────────────────────────────────────────────
    iva: Optional[float] = None              # VAT percentage (22, 10, 4, 0). None = not specified.
    total_with_iva: Optional[float] = None   # total_price * (1 + iva/100). None when iva is None.


class PurchaseRecordCreate(BaseModel):
    date: str
    supplier_name: str = Field(min_length=1, max_length=255)
    quantity: LocaleFloat = Field(gt=0)
    unit: str = "kg"
    unit_price: LocaleFloat = Field(gt=0)
    iva: Optional[LocaleFloat] = Field(default=None, ge=0, le=100)
    category: Optional[str] = Field(default=None, max_length=100)
    category_macro: Optional[str] = Field(default=None, max_length=100)
    description: Optional[str] = Field(default=None, max_length=1000)
    supplier_id: Optional[str] = Field(default=None)
    product_id: Optional[str] = Field(default=None)


class FixedCostFrequency(str, Enum):
    MENSILE = "mensile"
    SETTIMANALE = "settimanale"
    TRIMESTRALE = "trimestrale"
    ANNUALE = "annuale"


class FixedCostCategory(str, Enum):
    AFFITTO = "affitto"
    STIPENDIO = "stipendio"
    FINANZIAMENTO = "finanziamento"
    LEASING = "leasing"
    ABBONAMENTO = "abbonamento"
    ALTRO = "altro"


class FixedCost(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: str = Field(default_factory=generate_id)
    organization_id: str
    dataset_id: Optional[str] = None
    name: str
    category: str = "altro"
    amount: float
    frequency: str = "mensile"
    start_date: str  # ISO format date
    end_date: Optional[str] = None  # None = no expiry
    source_record_id: Optional[str] = None
    source_label: Optional[str] = None        # Dataset name or "Manuale"


class FixedCostCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    category: str = Field(default="altro", max_length=100)
    amount: LocaleFloat = Field(gt=0)
    frequency: str = "mensile"
    start_date: str
    end_date: Optional[str] = None


class SalesRecordCreate(BaseModel):
    date: str
    amount: LocaleFloat = Field(gt=0)
    category: Optional[str] = Field(default=None, max_length=100)
    description: Optional[str] = Field(default=None, max_length=1000)
    channel: Optional[str] = Field(default=None, max_length=50)
    payment_status: Optional[str] = Field(default=None)   # v2.4
    due_date: Optional[str] = Field(default=None)          # v2.4
    customer_id: Optional[str] = Field(default=None)
    product_id: Optional[str] = Field(default=None)


class SalesRecordUpdate(BaseModel):
    """Partial update model for PATCH /sales/{id}."""
    date: Optional[str] = None
    amount: Optional[LocaleFloat] = None
    category: Optional[str] = None
    description: Optional[str] = None
    channel: Optional[str] = None
    payment_status: Optional[str] = None   # v2.4
    due_date: Optional[str] = None          # v2.4
    customer_id: Optional[str] = None
    product_id: Optional[str] = None


class ExpenseRecordCreate(BaseModel):
    date: str
    amount: LocaleFloat = Field(gt=0)
    category: Optional[str] = Field(default=None, max_length=100)
    description: Optional[str] = Field(default=None, max_length=1000)
    supplier: Optional[str] = Field(default=None, max_length=255)
    supplier_id: Optional[str] = Field(default=None)


class ExpenseRecordUpdate(BaseModel):
    """Partial update model for PATCH /expenses/{id}."""
    date: Optional[str] = None
    amount: Optional[LocaleFloat] = None
    category: Optional[str] = None
    description: Optional[str] = None
    supplier: Optional[str] = None
    supplier_id: Optional[str] = None
