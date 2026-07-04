"""
Column Mapping and Dataset Column Profile models.

ColumnMapping: user/org-defined rules that map raw file column names to
               canonical field names (date, amount, category, …).

DatasetColumnProfile: statistical profile of columns detected after upload.
                      One document per dataset_id.
"""
from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List, Dict, Any
from datetime import datetime
from .common import generate_id, utc_now


# ── Column Mapping ────────────────────────────────────────────────────────────

class ColumnMappingBase(BaseModel):
    dataset_type: str                       # "sales" | "expenses" | "purchases"
    source_column: str                      # raw column name from the file
    target_field: str                       # canonical field: date/amount/category/…
    transform: Optional[str] = None        # e.g. "divide_by_100", "uppercase"
    is_active: bool = True


class ColumnMapping(ColumnMappingBase):
    model_config = ConfigDict(extra="ignore")

    id: str = Field(default_factory=generate_id)
    organization_id: str
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class ColumnMappingResponse(ColumnMappingBase):
    id: str
    organization_id: str
    created_at: datetime
    updated_at: datetime


# ── Dataset Column Profile ────────────────────────────────────────────────────

class ColumnStat(BaseModel):
    """Statistical summary of a single column in a dataset."""
    column_name: str
    detected_type: str                      # "date" | "amount" | "text" | "number"
    non_null_count: int = 0
    null_count: int = 0
    unique_count: int = 0
    sample_values: List[str] = []          # up to 5 representative values
    suggested_mapping: Optional[str] = None  # auto-detected target_field hint


class DatasetColumnProfile(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: str = Field(default_factory=generate_id)
    organization_id: str
    dataset_id: str                         # unique FK → datasets._id
    columns: List[ColumnStat] = []
    total_rows: int = 0
    error_rows: int = 0
    created_at: datetime = Field(default_factory=utc_now)


class DatasetColumnProfileResponse(BaseModel):
    id: str
    organization_id: str
    dataset_id: str
    columns: List[ColumnStat]
    total_rows: int
    error_rows: int
    created_at: datetime
