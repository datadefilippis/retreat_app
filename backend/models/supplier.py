from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List, Dict, Any
from datetime import datetime
from .common import generate_id, utc_now


class SupplierBase(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    external_id: Optional[str] = None   # ID in an external system
    email: Optional[str] = Field(default=None, max_length=320)
    phone: Optional[str] = None
    address: Optional[str] = None
    category: Optional[str] = None      # e.g. "utilities", "raw_materials"
    tags: List[str] = []
    metadata: Dict[str, Any] = {}


class SupplierCreate(SupplierBase):
    pass


class SupplierUpdate(BaseModel):
    """Pydantic model for PATCH /suppliers/{id}.

    Only fields present in the request body are applied.
    System fields (id, organization_id, created_at) are intentionally absent.
    """
    model_config = ConfigDict(extra="ignore")

    name: Optional[str] = None
    external_id: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    category: Optional[str] = None
    tags: Optional[List[str]] = None
    metadata: Optional[Dict[str, Any]] = None
    is_active: Optional[bool] = None


class Supplier(SupplierBase):
    model_config = ConfigDict(extra="ignore")

    id: str = Field(default_factory=generate_id)
    organization_id: str
    is_active: bool = True
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class SupplierResponse(SupplierBase):
    id: str
    organization_id: str
    is_active: bool
    created_at: datetime
    updated_at: datetime
