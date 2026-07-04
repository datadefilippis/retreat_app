"""Catalog Audit Entry — audit trail for commercial catalog mutations.

Phase 2a: infrastructure-only. The collection and model are created now;
actual audit entries will be written when catalog mutation endpoints ship
in Phase 2b.

Separated from the general admin audit log because catalog changes affect
the entire platform (not a single org) and need their own query surface.
"""

from datetime import datetime, timezone
from typing import Any, Dict, Optional

from pydantic import BaseModel, ConfigDict, Field

from models.common import generate_id


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class CatalogAuditEntry(BaseModel):
    """Immutable record of a catalog mutation."""

    model_config = ConfigDict(extra="ignore")

    id: str = Field(default_factory=generate_id)

    # What was changed
    entity_type: str          # "commercial_plan", "pricing_plan"
    entity_id: str            # slug or id of the changed entity
    action: str               # "create", "update", "archive", "publish_price_version"

    # Diff: {"field_name": {"old": <value>, "new": <value>}}
    changes: Dict[str, Any] = {}

    # Who and when
    performed_by: str         # admin user_id
    performed_at: datetime = Field(default_factory=_utc_now)

    # Optional admin notes (reason for change)
    notes: Optional[str] = None
