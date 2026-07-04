"""
ProductCostHistory — periodic snapshot of computed unit costs (W1.S1).

Why this collection exists
--------------------------
The resolver computes a product's unit cost dynamically from the current
state of ``cost_source`` + ``purchase_records``. That's correct for
"what is the cost RIGHT NOW", but it loses the historical view that
matters most to a business owner:

  - "Why did my Pizza Margherita margin drop in March?"
  - "How volatile is the cost of my Frutta fresca?"
  - "Has the supplier hike of last month stabilised?"

To answer those, we need the unit cost as it was at the *end of each
period*, stored, immutable. This collection persists those snapshots —
appended monthly by the ``cost_history_service`` cron (W1.S8) and on
event triggers (new purchase record on a linked category, cost_source
edit). It powers:

  1. Trend charts in the product detail drill-down (Wave 1 W1.S9)
  2. Variance detection (mom delta > threshold) for alerting (W1.S8)
  3. AI Analyst grounding — the LLM reads from this collection to give
     specific "X went up 22% in March" answers instead of generic
     "your margin dropped" hand-waving.

Append-only contract
--------------------
Snapshots are never updated or deleted. The merchant's audit trail is
the entire point — if a margin reading is challenged six months later,
we can show exactly what the system computed and why. The
``decomposition`` field carries the per-component breakdown as loose
dicts so adding fields to ``CostComponent`` in the future doesn't
require migrating historical entries.

Storage envelope
----------------
At one snapshot per product per month, an org with 100 products produces
~1.2k entries/year ≈ 600 KB at 500 bytes/doc — well within Mongo
free-tier comfort. For very large orgs (10k SKUs), we'd snapshot less
frequently or compress decomposition; not a Wave 1 concern.
"""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field

from .common import generate_id, utc_now


# Valid ``confidence`` values for downstream consumers (AI Analyst,
# Reconciliation widget). Exposed as a constant so the i18n keys and the
# AI tool prompts stay aligned without duplicating string literals.
CONFIDENCE_LEVELS = (
    "actual",                # all category components have real purchase data
    "declared",              # only manual components — value is what user said
    "mixed",                 # combination of manual + category components
    "estimated_org_average", # fell back to org-wide WAC; treat as approximate
    "unknown",               # no components at all; unit_cost is 0 or null
)


class CostHistoryEntry(BaseModel):
    """One row in ``product_cost_history_collection``.

    Created by ``cost_history_service.snapshot_product(product_id, period_end)``.
    Idempotent on (organization_id, product_id, period_end): rerunning
    the cron for the same period overwrites only the latest snapshot,
    never older ones.
    """

    model_config = ConfigDict(extra="ignore")

    id: str = Field(default_factory=generate_id)
    organization_id: str
    product_id: str

    # End-of-period boundary in ISO 8601 date format ("YYYY-MM-DD").
    # Stored as string (not datetime) because Mongo string indexes are
    # smaller and queries by period are always equality / range on
    # the calendar boundary, never wall-clock semantics.
    period_end: str

    # The resolved unit cost at the time of snapshot. Stored even when 0
    # so trend charts have an explicit "configured but zero" data point
    # (different from "missing snapshot").
    unit_cost: float

    # Which method produced this number — preserved so a later config
    # change (merchant switches from wac_30d to wac_90d) is visible in
    # the historical timeline as a method jump, not a mysterious value
    # discontinuity.
    method: str

    # How many components contributed to this snapshot. Quick filter for
    # the UI: "show me snapshots with at least one category component".
    components_count: int

    # MoM delta % of unit_cost vs the immediately previous snapshot
    # for the same product. Null when this is the first snapshot. The
    # variance detector uses this to fire alerts above the configured
    # threshold without recomputing on every read.
    delta_vs_prev_pct: Optional[float] = None

    # See ``CONFIDENCE_LEVELS`` above for semantics.
    confidence: str

    # Per-component contribution at this snapshot. Each dict carries:
    #   { type, label, contribution, [type-specific fields] }
    # Loose-typed so future CostComponent additions don't break old rows.
    decomposition: List[dict] = Field(default_factory=list)

    computed_at: datetime = Field(default_factory=utc_now)
