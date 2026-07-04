"""PricingPlan — admin-managed pricing plans stored in DB.

Each plan belongs to a module_key and defines the feature limits for that module.
Replaces the old hardcoded PLAN_LIMITS dict in ai_access.py.

The `limits` dict maps feature_key -> int.  Feature keys are module-specific:
  - For module "ai_assistant": {"chat": 50, "insights": 5}
  - Future modules will define their own feature keys.
  - A limit of -1 means unlimited.  A limit of 0 means disabled.
"""

from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, Dict
from datetime import datetime
from .common import generate_id, utc_now


class PricingPlan(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: str = Field(default_factory=generate_id)
    module_key: str                              # e.g. "ai_assistant", "cashflow_monitor"
    slug: str                                    # unique per module, e.g. "ai_assistant_starter"
    name: str                                    # display name, e.g. "AI Starter"
    price_monthly: float = 0.0                   # EUR/month (0 = free tier)
    price_yearly: Optional[float] = None         # EUR/year (optional annual pricing)
    currency: str = "EUR"                        # ISO 4217
    limits: Dict[str, int] = {}                  # module-specific feature limits
    is_active: bool = True                       # False = soft-deleted / archived
    sort_order: int = 0                          # display ordering in admin UI
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)
