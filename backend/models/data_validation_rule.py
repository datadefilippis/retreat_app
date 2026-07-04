"""
Data Validation Rule model.

Per-organisation rules applied during dataset parsing.
Rules are evaluated in the dataset_service pipeline (Phase 2).
Defined here in Phase 1 so the collection and indexes are ready.
"""
from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, Any
from datetime import datetime
from enum import Enum
from .common import generate_id, utc_now


class ValidationRuleType(str, Enum):
    REQUIRED = "required"               # field must be present and non-null
    MIN_VALUE = "min_value"             # numeric minimum
    MAX_VALUE = "max_value"             # numeric maximum
    DATE_RANGE = "date_range"           # date must be within bounds
    CATEGORY_WHITELIST = "category_whitelist"  # value must be in list
    REGEX = "regex"                     # value must match pattern


class DataValidationRuleBase(BaseModel):
    dataset_type: str                   # "sales" | "expenses" | "purchases"
    field_name: str                     # canonical field: date/amount/category/…
    rule_type: ValidationRuleType
    rule_value: Optional[Any] = None    # depends on rule_type (number, list, regex…)
    error_message: Optional[str] = None
    is_active: bool = True


class DataValidationRule(DataValidationRuleBase):
    model_config = ConfigDict(extra="ignore")

    id: str = Field(default_factory=generate_id)
    organization_id: str
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class DataValidationRuleResponse(DataValidationRuleBase):
    id: str
    organization_id: str
    created_at: datetime
    updated_at: datetime


class DataValidationRuleUpdate(BaseModel):
    """Partial update payload for PATCH /validation-rules/{id}.

    Only safe fields are updatable.  Structural fields (dataset_type,
    field_name, rule_type) cannot be changed — delete and re-create instead.
    """
    is_active: Optional[bool] = None
    rule_value: Optional[Any] = None
    error_message: Optional[str] = None
