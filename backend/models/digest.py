from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, Dict, Any
from datetime import datetime
from .common import generate_id, utc_now


class Digest(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: str = Field(default_factory=generate_id)
    organization_id: str
    digest_type: str  # "weekly" or "monthly"
    content: str
    period_start: str
    period_end: str
    kpis_summary: Dict[str, Any] = {}
    alerts_count: int = 0
    model_version: Optional[str] = None
    created_at: datetime = Field(default_factory=utc_now)

    # v2: Report format fields
    format: str = "text"                        # "text" or "report"
    has_pdf: bool = False                       # True if PDF was generated
    sections: Optional[Dict[str, Any]] = None   # Structured data for frontend
