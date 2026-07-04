from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime
from .common import generate_id, utc_now


class ModuleMetadata(BaseModel):
    key: str
    name: str
    description: str
    category: str
    icon: str
    is_available: bool = True


class OrganizationModule(BaseModel):
    model_config = ConfigDict(extra="ignore")
    
    id: str = Field(default_factory=generate_id)
    organization_id: str
    module_key: str
    is_active: bool = True
    activated_at: datetime = Field(default_factory=utc_now)
    activated_by: str
