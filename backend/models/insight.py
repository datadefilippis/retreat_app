from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, Dict, Any
from datetime import datetime
from .common import generate_id, utc_now


class InsightBase(BaseModel):
    module_key: str
    title: str
    content: str
    metrics_context: Dict[str, Any] = {}


class Insight(InsightBase):
    model_config = ConfigDict(extra="ignore")

    id: str = Field(default_factory=generate_id)
    organization_id: str
    created_at: datetime = Field(default_factory=utc_now)
    period_start: str
    period_end: str

    # ── Phase-1 additions (all Optional → zero breaking change) ──────────────
    schema_version: Optional[str] = None
    model_version: Optional[str] = None       # LLM model tag used for generation
    confidence_score: Optional[float] = None  # 0.0–1.0 if the AI exposes it
