"""
Schema Version model.

Tracks which Phase migrations have been applied to each MongoDB collection.
One document per collection_name, upserted on each migration run.
"""
from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, Dict, Any
from datetime import datetime
from .common import generate_id, utc_now


class SchemaVersion(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: str = Field(default_factory=generate_id)
    collection_name: str                    # e.g. "sales_records"
    version: str                            # e.g. "1.0", "1.1", "2.0"
    description: str                        # human-readable summary of the migration
    applied_at: datetime = Field(default_factory=utc_now)
    applied_by: str = "system"             # "system" or user_id
    details: Optional[Dict[str, Any]] = None  # migration metadata / rollback hints


class SchemaVersionResponse(BaseModel):
    id: str
    collection_name: str
    version: str
    description: str
    applied_at: datetime
    applied_by: str
