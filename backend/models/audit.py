from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, Dict, Any
from datetime import datetime
from .common import generate_id, utc_now


class AuditLog(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: str = Field(default_factory=generate_id)
    # None for system_admin actions (platform-level, not scoped to any org).
    # Query system admin audit entries with: {"organization_id": None}
    organization_id: Optional[str] = None
    user_id: str
    action: str
    resource_type: str
    resource_id: Optional[str] = None
    details: Dict[str, Any] = {}
    created_at: datetime = Field(default_factory=utc_now)
