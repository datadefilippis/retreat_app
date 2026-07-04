"""
Alert Rules v3 — modular, intelligent alert system.

Each category module exports async functions with signature:
    async def check_<rule>(ctx: AlertContext) -> List[Alert]

AlertContext is a dataclass preloaded by the engine with all data needed.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional, Set, Tuple
from datetime import date


@dataclass
class AlertContext:
    """Shared context for all alert rules, preloaded by the engine."""

    org_id: str
    locale: str
    thresholds: dict
    existing_keys: Set[Tuple[str, str]]  # (alert_type, entity_key)
    today: date = field(default_factory=date.today)
    current_month_day: int = 0  # Day of month (1-31), for partial-month awareness

    # ── Preloaded financial data ─────────────────────────────────────────
    # Daily aggregations (last 90 days)
    sales_by_date_90d: Dict[str, float] = field(default_factory=dict)
    expenses_by_date_90d: Dict[str, float] = field(default_factory=dict)
    purchases_by_date_90d: Dict[str, float] = field(default_factory=dict)

    # Daily aggregations (last 365 days, for YoY)
    sales_by_date_365d: Dict[str, float] = field(default_factory=dict)

    # Monthly snapshots (for trend analysis)
    monthly_snapshots: List[dict] = field(default_factory=list)
    # Each: {month: "YYYY-MM", sales: float, expenses: float, purchases: float,
    #         fixed_costs: float, net_margin_pct: float, cost_ratio: float}

    # Totals for current 30-day period
    total_sales_30d: float = 0.0
    total_expenses_30d: float = 0.0
    total_purchases_30d: float = 0.0
    total_fixed_costs_30d: float = 0.0

    # Totals for previous 30-day period
    total_sales_prev_30d: float = 0.0
    total_expenses_prev_30d: float = 0.0
    total_purchases_prev_30d: float = 0.0

    # Cash cycle data
    open_receivables: float = 0.0
    open_payables: float = 0.0
    overdue_invoices: List[dict] = field(default_factory=list)
    # Each: {customer: str, amount: float, due_date: str, overdue_days: int}

    # Concentration data
    customers_by_revenue: List[dict] = field(default_factory=list)
    # Each: {customer_name: str, total_revenue: float, pct: float}
    suppliers_by_amount: List[dict] = field(default_factory=list)
    # Each: {supplier: str, total: float, pct: float}
    sales_by_category: List[dict] = field(default_factory=list)
    # Each: {category: str, total: float, pct: float}
    expenses_by_category_30d: List[dict] = field(default_factory=list)
    expenses_by_category_prev_30d: List[dict] = field(default_factory=list)

    # Data availability
    has_data: bool = False
    min_date: Optional[str] = None
    max_date: Optional[str] = None
    days_of_data: int = 0

    # ── Commerce operations data (v13.0) ────────────────────────────────
    orders_draft_count: int = 0
    orders_draft_older_than_3d: int = 0
    orders_draft_total_value: float = 0.0
    fulfillment_delays: List[dict] = field(default_factory=list)
    # Each: {order_id, order_number, customer_name, days_pending, order_value}
    fulfillment_delays_total_value: float = 0.0
    payment_limbo_orders: List[dict] = field(default_factory=list)
    # Each: {order_id, order_number, amount, hours_since}
    payment_limbo_total: float = 0.0
    events_upcoming_3d: List[dict] = field(default_factory=list)
    # Each: {occ_id, name, date, capacity, booked, fill_rate_pct, unit_price}
    rental_products_idle: List[dict] = field(default_factory=list)
    # Each: {product_id, name}
    orders_cancelled_7d: int = 0
    orders_cancelled_value_7d: float = 0.0
    orders_total_7d: int = 0
    low_stock_products: List[dict] = field(default_factory=list)
    # Each: {product_id, name, stock_quantity}

    # ── Data quality metrics (v14.0) ────────────────────────────────────
    customer_id_coverage_pct: int = 100  # % of sales_records with customer_id
    total_sales_records: int = 0
    products_without_cost_pct: int = 0  # % of active products missing cost_price
    total_active_products: int = 0

    # ── Data quality snapshot (v14.1, Pillar 1) ─────────────────────────
    # Optional so existing tests that hand-build an AlertContext don't
    # break. The engine populates it inside _build_context (production
    # path). Rules query it via the @requires_data decorator side-channel
    # — they never read the field directly, keeping the rule body
    # decoupled from the snapshot shape.
    #
    # Reading the snapshot directly inside a rule body is DISCOURAGED:
    # it bypasses the centralised contract evaluation and makes the
    # rule harder to test in isolation. Use @requires_data instead.
    data_quality: Optional["DataQualitySnapshot"] = None  # type: ignore[name-defined]  # noqa: F821

    # ── Anti-ridondanza cross-month (v14.2, Pillar 2.3) ─────────────────
    # Set of (alert_type) strings that were RESOLVED in the recent past
    # (default lookback: 60 days). Used by rules that suffer from the
    # "same alert every new month" pattern: a rule fires in May, the
    # merchant clicks resolve, but the entity_key (e.g. "cat_X_2026-06")
    # changes in June and would re-fire identically. Checking this set
    # gives the merchant a 60-day quiet period after they took action.
    #
    # Why a *set of alert_types* (not (alert_type, entity_key) pairs):
    # the merchant's resolve action expresses an intent — "I have
    # acknowledged this PROBLEM, don't tell me again for a while". The
    # specific entity_key changes naturally over time (new month, new
    # supplier name variant) and shouldn't restart the cooldown.
    #
    # Populated by the engine in _build_context from
    # alert_repository.find_recently_resolved_types. Default empty set
    # means no rule short-circuits, preserving v14.1 behaviour for any
    # legacy test that builds AlertContext directly.
    recently_resolved_alert_types: Set[str] = field(default_factory=set)

    def is_dedup(self, alert_type: str, entity_key: str) -> bool:
        """Check if this (alert_type, entity_key) already has an open alert."""
        return (alert_type, entity_key) in self.existing_keys

    def was_recently_resolved(self, alert_type: str) -> bool:
        """True when the merchant resolved this alert_type within the
        cooldown window (default 60 days). Rules that suffer from
        cross-month ridondanza should call this AS WELL AS is_dedup."""
        return alert_type in self.recently_resolved_alert_types


def _fmt_eur(amount: float) -> str:
    """Format EUR amount for display in alerts."""
    if abs(amount) >= 1000:
        return f"€{amount:,.0f}".replace(",", ".")
    return f"€{amount:,.2f}"


# v14.2 (P2.4c): UUID-shaped names get into alert narratives when the
# upstream aggregate falls back to customer_id because customer_name is
# null/missing in sales_records. Example PROD seen in a macelleria
# import: customer_name field absent, customer_id = "7a4d-...-...-...".
# The aggregate's $ifNull substitutes the UUID, which then surfaces as
# "Cliente 7a4d-..." in the alert summary — completely unparseable for
# a merchant. This helper detects the canonical UUID v4 shape and
# returns a localised fallback. Used at the boundary between the data
# layer (which legitimately needs SOMETHING to group by) and the
# narrative layer (which needs human-readable strings).
import re as _re
_UUID_RE = _re.compile(
    r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-"
    r"[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$"
)


# v14.2 (P2.4d): defensive cap for share-of-total percentages. A
# customer's share of revenue cannot mathematically exceed 100%, but
# data inconsistencies (re-attributed records, deleted parent customers,
# stale aggregations vs current snapshot) can push the computed ratio
# above 100. Showing "101% del fatturato" in an alert undermines
# merchant trust. Use this helper for any *share* percentage where the
# numerator is structurally bounded by the denominator. NOT for delta/
# change percentages (e.g. YoY decline) where >100 is meaningful news.
def cap_share_pct(pct: float, lower: float = 0.0, upper: float = 100.0) -> float:
    """Clamp a share-of-total percentage to [lower, upper] (default 0..100).

    Defensive: returns ``lower`` when the input is None / NaN / negative
    sentinel; returns ``upper`` when above the cap. Anything in-between
    passes through untouched.
    """
    try:
        if pct is None:
            return lower
        return max(lower, min(upper, float(pct)))
    except (TypeError, ValueError):
        return lower


def humanize_entity_name(name, fallback: str = "Sconosciuto") -> str:
    """Return ``name`` if it's a real human-readable string, else fallback.

    Detection rules:
      • None / empty / whitespace-only → fallback
      • Canonical UUID v4 (36 chars, 8-4-4-4-12 hex) → fallback
      • Anything else → name (stripped)

    Why not parse all hex-only strings: legitimate supplier codes
    (e.g. "AB12CD" SKU prefixes) would false-positive. UUID v4 is the
    only shape that actually leaks from the customers/suppliers
    collections in our schema.
    """
    if name is None:
        return fallback
    s = str(name).strip()
    if not s:
        return fallback
    if _UUID_RE.match(s):
        return fallback
    return s


# ── Rule registry ────────────────────────────────────────────────────────────
# Populated by category modules at import time

ALL_RULES: List[Any] = []
