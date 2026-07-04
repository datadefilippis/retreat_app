from pydantic import BaseModel, Field, ConfigDict
from typing import Optional
from datetime import datetime
from enum import Enum
from .common import generate_id, utc_now


class RegistrationMode(str, Enum):
    OPEN = "open"
    INVITE_ONLY = "invite_only"


class PlatformSettings(BaseModel):
    """Global platform-level settings (one document per key)."""
    model_config = ConfigDict(extra="ignore")

    id: str = Field(default_factory=generate_id)
    key: str                                          # unique identifier, e.g. "registration"
    registration_mode: RegistrationMode = RegistrationMode.OPEN
    updated_at: datetime = Field(default_factory=utc_now)
    updated_by: Optional[str] = None                  # user_id of system admin who changed it
