"""OrgQuotaNotice — idempotent record of a quota-warning email sent to an org.

Onda 6 (v5.8). One record per (organization_id, metric_key, level, period_start)
guarantees that the quota_warning_sweep cron job sends each warning email
AT MOST ONCE per billing period, even if the cron runs many times in the
same period (default cadence is every 6h).

Levels:
    "warn_80"   — usage reached 80% of effective_limit (advisory upsell)
    "exceeded"  — usage hit the effective_limit (informational only — quotas
                  are soft-enforced; transactional emails still go through)

Period_start is `YYYY-MM` for monthly-billed quotas (chat, orders_monthly,
data_rows, digest). Stable identifiers like `stores_max` / `products` use
`YYYY-MM` of the day the email was sent — they are state-based, not period-
based, so the unique key still works.

Why a separate collection (vs reusing email_usage_events):
    · Event log entries are append-only; this collection has unique-key
      semantics for idempotency.
    · Sweep performance: one targeted compound-index lookup per (org,
      metric, level, period) instead of scanning the full event history.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from .common import generate_id, utc_now


class OrgQuotaNotice(BaseModel):
    """A single quota-warning notice already delivered to an org.

    Inserted by `quota_email_service.notify_quota_warning_email` AFTER the
    email send returns successfully (or returns False, treated as
    "attempted, don't retry this period"). The unique compound index on
    (organization_id, metric_key, level, period_start) is the idempotency
    primitive — duplicate sends raise DuplicateKeyError which the sweep
    catches and skips silently.
    """

    model_config = ConfigDict(extra="ignore")

    id: str = Field(default_factory=generate_id)
    organization_id: str
    metric_key: str          # e.g. "chat", "orders_monthly", "data_rows"
    module_key: str          # e.g. "ai_assistant", "commerce", "cashflow_monitor"
    level: str               # "warn_80" | "exceeded"
    period_start: str        # "YYYY-MM" (e.g. "2026-04")
    used: int = 0
    effective_limit: int = 0  # base + addons at the moment the email was sent

    # Audit
    recipient_email: Optional[str] = None
    locale: Optional[str] = None       # locale used for the email body

    sent_at: datetime = Field(default_factory=utc_now)
    created_at: datetime = Field(default_factory=utc_now)
