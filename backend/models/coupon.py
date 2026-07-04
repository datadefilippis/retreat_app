"""
Coupon model — promotional discount codes for orders.
"""

from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional
from datetime import datetime
from .common import generate_id, utc_now


class Coupon(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: str = Field(default_factory=generate_id)
    organization_id: str
    code: str                                    # e.g. "SUMMER2026", case-insensitive
    store_ids: List[str] = []                    # empty = valid on all stores in org
    discount_pct: Optional[float] = None         # 0-100, e.g. 10 = 10% off
    discount_amount: Optional[float] = None      # fixed amount off, e.g. 5.00 = €5 off
    min_order_amount: Optional[float] = None     # minimum subtotal to apply
    max_uses: Optional[int] = None               # null = unlimited
    current_uses: int = 0
    valid_from: Optional[str] = None             # ISO date
    valid_to: Optional[str] = None               # ISO date
    is_active: bool = True
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class CouponCreate(BaseModel):
    code: str = Field(min_length=2, max_length=30, pattern=r'^[A-Za-z0-9\-_]+$')
    store_ids: List[str] = []  # empty = all stores
    discount_pct: Optional[float] = Field(default=None, ge=0, le=100)
    discount_amount: Optional[float] = Field(default=None, ge=0)
    min_order_amount: Optional[float] = Field(default=None, ge=0)
    max_uses: Optional[int] = Field(default=None, ge=1)
    valid_from: Optional[str] = None
    valid_to: Optional[str] = None


class CouponUpdate(BaseModel):
    model_config = ConfigDict(extra="ignore")
    store_ids: Optional[List[str]] = None
    discount_pct: Optional[float] = None
    discount_amount: Optional[float] = None
    min_order_amount: Optional[float] = None
    max_uses: Optional[int] = None
    valid_from: Optional[str] = None
    valid_to: Optional[str] = None
    is_active: Optional[bool] = None
