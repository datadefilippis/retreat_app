"""
Module Config model.

Stores per-module configuration for an organisation.
Separate from OrganizationModule (which tracks activation state).
One document per (organization_id, module_key).
"""
from pydantic import BaseModel, Field, ConfigDict
from typing import Dict, Any
from datetime import datetime
from .common import generate_id, utc_now


class ModuleConfigBase(BaseModel):
    module_key: str
    config: Dict[str, Any] = {}         # flexible config bag, schema varies by module


class ModuleConfig(ModuleConfigBase):
    model_config = ConfigDict(extra="ignore")

    id: str = Field(default_factory=generate_id)
    organization_id: str
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class ModuleConfigResponse(ModuleConfigBase):
    id: str
    organization_id: str
    created_at: datetime
    updated_at: datetime
