"""
KPI Snapshot model.

Pre-computed KPI aggregates stored per (organization, module, period).
Decouples dashboard read performance from live aggregation pipelines.
"""
from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, Dict, Any
from datetime import datetime
from .common import generate_id, utc_now


class KPISnapshotGranularity:
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    CUSTOM = "custom"


class KPISnapshotBase(BaseModel):
    module_key: str
    period_start: str                       # ISO date YYYY-MM-DD
    period_end: str                         # ISO date YYYY-MM-DD
    granularity: str = KPISnapshotGranularity.MONTHLY
    metrics: Dict[str, Any] = {}            # flexible bag: {"total_sales": 0, ...}
    metadata: Optional[Dict[str, Any]] = None


class KPISnapshot(KPISnapshotBase):
    model_config = ConfigDict(extra="ignore")

    id: str = Field(default_factory=generate_id)
    organization_id: str
    created_at: datetime = Field(default_factory=utc_now)
    # Schema version lets consumers detect stale snapshots after model changes
    schema_version: str = "1.0"


class KPISnapshotResponse(KPISnapshotBase):
    id: str
    organization_id: str
    created_at: datetime
    schema_version: str
