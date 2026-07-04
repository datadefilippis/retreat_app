from pydantic import BaseModel, Field, ConfigDict, EmailStr
from typing import Optional, List
from datetime import datetime
from enum import Enum
from .common import generate_id, utc_now


class InviteStatus(str, Enum):
    PENDING = "pending"
    USED = "used"
    REVOKED = "revoked"


class InviteCreate(BaseModel):
    """Body for POST /admin/invites."""
    email: EmailStr


class Invite(BaseModel):
    """Platform-level invitation (system admin invites a new org owner)."""
    model_config = ConfigDict(extra="ignore")

    id: str = Field(default_factory=generate_id)
    email: EmailStr
    token_hash: str                                   # SHA-256 hex digest (plaintext never stored)
    created_by: str                                   # system admin user_id
    created_at: datetime = Field(default_factory=utc_now)
    expires_at: datetime                              # token expiry (7 days from creation)
    status: InviteStatus = InviteStatus.PENDING


class InviteResponse(BaseModel):
    """Returned from invite endpoints."""
    id: str
    email: EmailStr
    status: InviteStatus
    created_at: datetime
    expires_at: datetime
    invite_url: Optional[str] = None                  # only set on creation (contains plaintext token)


class InviteListResponse(BaseModel):
    items: List[InviteResponse]
    total: int
