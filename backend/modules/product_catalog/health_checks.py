"""
Product Catalog Health Checks — intelligence behind the dashboard banner.

Each check is a pure async function:

    async def check_<id>(org_id, window, prev_window, ...) -> Optional[CheckResult]

It either returns ``None`` (check passed — no issue worth surfacing) or a
``CheckResult`` describing the problem, its severity, and the data the
frontend needs to render the drill-down.

The orchestrator ``run_all_checks(...)`` calls every check in parallel
via ``asyncio.gather`` and returns a single envelope consumed by the
``GET /modules/product-catalog/health-check`` endpoint.

Why a dedicated module
----------------------
Keeping each check isolated has three concrete benefits:

  1. **Testability** — a check is a pure function. Pass org_id and
     mock collections, assert the CheckResult. No fixtures needed.
  2. **Composability** — adding the next check (e.g. variance alert
     when we ship W1.S8) is one new function + one entry in the
     orchestrator. No refactor of the others.
  3. **i18n locality** — the check function does NOT carry strings;
     it only emits an ``id`` and ``metrics`` dict. The frontend looks
     up ``checks.<id>.{title,body,cause,action}`` in the locale file,
     so translations stay in JSON (where translators expect them).

The reverse-coupling rule that ``features/products/`` rules follow
(R1: no cross-tipo imports) doesn't apply here because we're in the
backend, but the spirit does: checks consult ``sales_records``,
``purchase_records``, ``products_collection`` and ``orders_collection``
directly — they NEVER call other modules' service layers. That keeps
checks immune to refactors in the consumed modules.
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import asdict, dataclass, field
from typing import List, Optional

from database import (
    products_collection,
    purchase_records_collection,
    sales_records_collection,
    orders_collection,
)
from modules.customer_insights.period_filter import (
    PeriodWindow,
    parse_period,
    previous_period,
)

logger = logging.getLogger(__name__)


# ── Constants ────────────────────────────────────────────────────────────────
# Threshold defaults — exposed at module level so a future settings page
# could let merchants tune them per-org without touching individual checks.

# A1 — Products without cost configured
THRESH_A1_CRITICAL_BLIND_REVENUE_PCT = 30  # % of revenue blind → critical
THRESH_A1_WARNING_BLIND_REVENUE_PCT = 5    # % of revenue blind → warning

# A3 — Suspicious margins
THRESH_A3_HIGH_MARGIN = 90    # margin_pct above this → suspect overhead missing
THRESH_A3_NEGATIVE_MARGIN_PCT = 0  # below 0 → cost > price (definitely wrong)

# B1 — Cashflow vs products revenue
THRESH_B1_WARNING_DIFF_PCT = 5
THRESH_B1_INFO_DIFF_PCT = 2

# C1 — Purchases unattributed
THRESH_C1_INFO_UNATTRIBUTED_PCT = 30  # info when >30% of purchases not linked

# D1 — Coverage drop
THRESH_D1_DROP_PP = 10  # ≥10 percentage-points drop vs previous period

# D2 — Margin deterioration
THRESH_D2_DROP_PP = 5  # ≥5 pp margin drop vs previous period


# ── Result dataclass ─────────────────────────────────────────────────────────


@dataclass
class CheckResult:
    """Output of a single health-check.

    The frontend reads ``id`` to look up i18n keys (title, body, cause,
    action labels) under the ``checks.<id>`` namespace. Strings are NOT
    embedded here — separation of concerns between Python (logic) and
    JSON (translations).

    ``metrics`` is a free-form dict carrying the numbers used in the
    i18n placeholders (e.g. {{count}}, {{amount}}, {{pct}}). The
    frontend interpolates them at render time via i18next.

    ``drill_data`` is the optional click-to-expand payload:
      - {"type": "product_list", "items": [{product_id, name, value}, ...]}
      - {"type": "category_list", "items": [...]}
      - {"type": "order_list", "items": [{order_id, order_number, ...}]}
      - None when the check is a pure metric with no drill (e.g. trends)

    ``actions`` is a list of suggested UI affordances. The frontend
    decides how to render them (button, link, etc.); the backend just
    declares intent + target.

    ``business_impact`` (FB.2) is the 0-100 score the frontend uses
    to rank checks beyond raw severity. Severity says "how alarming
    visually"; business_impact says "how much does it affect decisions".
    The Hero layout (FB.3) picks the top-impact check and surfaces it
    prominently, then groups the remaining ones by tier.
    """

    id: str
    category: str          # 'data_quality' | 'cashflow_coherence' | 'purchases_coherence' | 'trends'
    severity: str          # 'critical' | 'warning' | 'info'
    business_impact: int = 0   # 0..100 — higher = more impactful on business decisions
    metrics: dict = field(default_factory=dict)
    drill_data: Optional[dict] = None
    actions: List[dict] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)


# ─────────────────────────────────────────────────────────────────────────────
# Data-quality checks (A.*)
# ─────────────────────────────────────────────────────────────────────────────


async def check_a1_products_without_cost(
    org_id: str, window: PeriodWindow,
) -> Optional[CheckResult]:
    """A1 — Products that generated sales in the period but have no
    ``cost_source`` configured. Without cost, margin = N/D.

    Severity:
      - critical: blind revenue ≥ 30% of total period revenue
      - warning:  blind revenue ≥ 5%
      - info:     any (still surfaces in the banner but as low-priority)
      - passed:   zero products blind

    Drill items: list of (product_id, name, blind_revenue) sorted by
    blind_revenue desc, capped at 20 for the UI.
    """
    pipeline = [
        {"$match": {
            "organization_id": org_id,
            "product_id": {"$ne": None, "$exists": True},
            "date": {"$gte": window.start_iso, "$lte": window.end_iso},
        }},
        {"$group": {
            "_id": "$product_id",
            "revenue": {"$sum": "$amount"},
        }},
    ]
    rev_by_pid = {}
    total_revenue = 0.0
    async for d in sales_records_collection.aggregate(pipeline):
        rev_by_pid[d["_id"]] = d["revenue"]
        total_revenue += d["revenue"]

    if not rev_by_pid:
        return None  # No sales at all — nothing to flag

    # Which of these products has cost_source configured?
    selling_ids = list(rev_by_pid.keys())
    blind_ids = []
    blind_revenue = 0.0
    cursor = products_collection.find(
        {"organization_id": org_id, "id": {"$in": selling_ids}},
        {"_id": 0, "id": 1, "name": 1, "cost_source": 1},
    )
    pname_by_id = {}
    products_with_cost = set()
    async for p in cursor:
        pname_by_id[p["id"]] = p.get("name") or "—"
        cs = p.get("cost_source")
        # "Configured" means cost_source exists AND has at least one component.
        if cs and isinstance(cs, dict) and (cs.get("components") or []):
            products_with_cost.add(p["id"])

    for pid, revenue in rev_by_pid.items():
        if pid not in products_with_cost:
            blind_ids.append(pid)
            blind_revenue += revenue

    if not blind_ids:
        return None  # All selling products have cost configured

    blind_pct = (blind_revenue / total_revenue * 100) if total_revenue > 0 else 0
    if blind_pct >= THRESH_A1_CRITICAL_BLIND_REVENUE_PCT:
        severity = "critical"
    elif blind_pct >= THRESH_A1_WARNING_BLIND_REVENUE_PCT:
        severity = "warning"
    else:
        severity = "info"

    # Drill: top blind products by revenue.
    items = sorted(
        [{"product_id": pid, "name": pname_by_id.get(pid, "—"),
          "value": round(rev_by_pid[pid], 2)} for pid in blind_ids],
        key=lambda x: x["value"], reverse=True,
    )[:20]

    # Business impact: blind revenue share is the direct decision-impact
    # measure. 80% blind = the merchant is flying blind on 80% of sales.
    # Cap at 95 so even worst case leaves headroom for "definitely critical"
    # checks like negative margins.
    impact = min(int(round(blind_pct)), 95)

    return CheckResult(
        id="products_without_cost",
        category="data_quality",
        severity=severity,
        business_impact=impact,
        metrics={
            "count": len(blind_ids),
            "blind_revenue": round(blind_revenue, 2),
            "blind_revenue_pct": round(blind_pct, 1),
            "total_revenue": round(total_revenue, 2),
        },
        drill_data={"type": "product_list", "items": items},
        actions=[
            {"type": "bulk_configure_cost", "target_ids": [i["product_id"] for i in items],
             "label_key": "configure_all"},
            {"type": "navigate", "target": "/products", "label_key": "open_products"},
        ],
    )


async def check_a3_suspicious_margins(
    org_id: str, window: PeriodWindow,
) -> Optional[CheckResult]:
    """A3 — Products whose margin is suspect: either too high (overhead
    likely missing) or negative (cost > price, definitely wrong).

    Severity:
      - warning: ≥1 product with negative margin (the real "alarm" case)
      - info:    ≥1 product with margin > 90% but no negatives
      - passed:  no suspect margins

    Reads per-product margin from the period aggregation, NOT the
    materialised metrics (which are life-of-product and may hide a
    recent pricing change).
    """
    pipeline = [
        {"$match": {
            "organization_id": org_id,
            "product_id": {"$ne": None, "$exists": True},
            "date": {"$gte": window.start_iso, "$lte": window.end_iso},
        }},
        {"$group": {
            "_id": "$product_id",
            "revenue": {"$sum": "$amount"},
            "cost": {"$sum": {"$ifNull": ["$cost_at_sale", 0]}},
        }},
    ]
    by_pid = {}
    async for d in sales_records_collection.aggregate(pipeline):
        revenue = d.get("revenue") or 0
        cost = d.get("cost") or 0
        # Margin only meaningful when cost is known and revenue > 0.
        if revenue > 0 and cost > 0:
            margin = (revenue - cost) / revenue * 100
            by_pid[d["_id"]] = {"margin": margin, "revenue": revenue, "cost": cost}

    if not by_pid:
        return None

    high_items = []
    negative_items = []
    for pid, x in by_pid.items():
        if x["margin"] < THRESH_A3_NEGATIVE_MARGIN_PCT:
            negative_items.append((pid, x))
        elif x["margin"] > THRESH_A3_HIGH_MARGIN:
            high_items.append((pid, x))

    if not high_items and not negative_items:
        return None

    # Severity: negative > high.
    severity = "warning" if negative_items else "info"

    # Resolve names.
    target_ids = [pid for pid, _ in (negative_items + high_items)]
    pname_by_id = {}
    cursor = products_collection.find(
        {"organization_id": org_id, "id": {"$in": target_ids}},
        {"_id": 0, "id": 1, "name": 1},
    )
    async for p in cursor:
        pname_by_id[p["id"]] = p.get("name") or "—"

    drill_items = []
    for pid, x in (negative_items + high_items)[:20]:
        drill_items.append({
            "product_id": pid,
            "name": pname_by_id.get(pid, "—"),
            "margin_pct": round(x["margin"], 1),
            "kind": "negative" if x["margin"] < 0 else "high",
        })

    # Business impact: a negative margin = the merchant is losing money
    # on every sale, top-of-the-pile importance (90). A high-margin
    # outlier just means the cost setup is suspect — important but not
    # immediately damaging (40).
    impact = 90 if negative_items else 40

    return CheckResult(
        id="suspicious_margins",
        category="data_quality",
        severity=severity,
        business_impact=impact,
        metrics={
            "negative_count": len(negative_items),
            "high_count": len(high_items),
            "total_count": len(negative_items) + len(high_items),
        },
        drill_data={"type": "product_list", "items": drill_items},
        actions=[
            {"type": "navigate", "target": "/products", "label_key": "open_products"},
        ],
    )


# ─────────────────────────────────────────────────────────────────────────────
# Cashflow-coherence checks (B.*) — IB.2
# ─────────────────────────────────────────────────────────────────────────────


async def check_b1_cashflow_mismatch(
    org_id: str, window: PeriodWindow,
) -> Optional[CheckResult]:
    """B1 — Products revenue vs Cashflow Monitor revenue diff.

    The Cashflow Monitor's notion of "total_sales" is ``Σ sales_records.amount``
    across the period — including rows with ``product_id = null``. The
    Product Performance page only counts rows with a product link, so
    a divergence means there are unlinked sales the merchant probably
    isn't aware of.

    This check computes both totals from the same source (``sales_records``)
    to guarantee the comparison is apples-to-apples: any difference is
    100% attributable to unlinked sales, not to a different period
    semantic.

    Severity:
      - warning: |diff_pct| ≥ 5 %
      - info:    |diff_pct| ≥ 2 %
      - passed:  closer than 2 % (rounding noise)

    Drill data: a synthetic "narrative" payload with the two numbers
    side by side — the table-style drill makes no sense for a single
    KPI mismatch. The frontend renders it as a two-row comparison.
    """
    pipeline = [
        {"$match": {
            "organization_id": org_id,
            "date": {"$gte": window.start_iso, "$lte": window.end_iso},
        }},
        {"$group": {
            "_id": {"$cond": [
                {"$or": [
                    {"$eq": ["$product_id", None]},
                    {"$not": ["$product_id"]},
                ]},
                "orphan",
                "linked",
            ]},
            "amount": {"$sum": "$amount"},
            "count": {"$sum": 1},
        }},
    ]
    linked_amount = 0.0
    orphan_amount = 0.0
    orphan_count = 0
    async for d in sales_records_collection.aggregate(pipeline):
        if d["_id"] == "linked":
            linked_amount = d.get("amount") or 0
        else:
            orphan_amount = d.get("amount") or 0
            orphan_count = d.get("count") or 0

    cashflow_total = linked_amount + orphan_amount
    if cashflow_total <= 0:
        return None  # no sales — no mismatch possible

    diff = cashflow_total - linked_amount
    diff_pct = (diff / cashflow_total * 100) if cashflow_total > 0 else 0

    if diff_pct < THRESH_B1_INFO_DIFF_PCT:
        return None  # within noise tolerance

    severity = "warning" if diff_pct >= THRESH_B1_WARNING_DIFF_PCT else "info"

    # Business impact: a 4× multiplier on the diff_pct caps at 60 even
    # for catastrophic mismatches — coherence is important but it's
    # rarely the difference between "I'm profitable" and "I'm not".
    impact = min(int(round(diff_pct * 4)), 60)

    return CheckResult(
        id="cashflow_mismatch",
        category="cashflow_coherence",
        severity=severity,
        business_impact=impact,
        metrics={
            "products_revenue": round(linked_amount, 2),
            "cashflow_revenue": round(cashflow_total, 2),
            "diff_amount": round(diff, 2),
            "diff_pct": round(diff_pct, 1),
            "orphan_count": orphan_count,
        },
        drill_data={
            "type": "comparison",
            "rows": [
                {"label_key": "drill.products_revenue", "value": round(linked_amount, 2)},
                {"label_key": "drill.cashflow_revenue", "value": round(cashflow_total, 2)},
                {"label_key": "drill.orphan_sales", "value": round(orphan_amount, 2),
                 "subvalue": orphan_count},
            ],
        },
        actions=[
            {"type": "navigate", "target": "/modules/cashflow_monitor",
             "label_key": "open_cashflow"},
            {"type": "navigate", "target": "/sales?filter=orphan",
             "label_key": "see_orphan_sales"},
        ],
    )


async def check_b2_orphan_sales(
    org_id: str, window: PeriodWindow,
) -> Optional[CheckResult]:
    """B2 — Sales records without a product_id.

    Independent of B1 in that B2 fires even when the absolute diff is
    small (e.g. 1 orphan sale in a long-tail catalog). B1 looks at
    aggregate %, B2 looks at the count — together they cover both the
    "big bag of unlinked sales" and the "long tail of stragglers"
    scenarios.

    Severity:
      - info: ≥ 1 orphan (we never escalate this to warning on its own;
              B1 already covers the value-impact angle)
      - passed: zero orphans
    """
    pipeline = [
        {"$match": {
            "organization_id": org_id,
            "date": {"$gte": window.start_iso, "$lte": window.end_iso},
            "$or": [
                {"product_id": None},
                {"product_id": {"$exists": False}},
            ],
        }},
        {"$group": {
            "_id": None,
            "amount": {"$sum": "$amount"},
            "count": {"$sum": 1},
        }},
    ]
    docs = await sales_records_collection.aggregate(pipeline).to_list(1)
    if not docs:
        return None
    d = docs[0]
    count = d.get("count") or 0
    amount = d.get("amount") or 0
    if count == 0:
        return None

    # Surface the most recent orphan rows for the drill so the merchant
    # can spot them quickly (e.g. CSV row 42 missing SKU).
    sample_cursor = sales_records_collection.find(
        {
            "organization_id": org_id,
            "date": {"$gte": window.start_iso, "$lte": window.end_iso},
            "$or": [{"product_id": None}, {"product_id": {"$exists": False}}],
        },
        {"_id": 0, "date": 1, "amount": 1, "description": 1, "source_label": 1},
    ).sort("date", -1).limit(10)

    sample = []
    async for r in sample_cursor:
        sample.append({
            "date": r.get("date"),
            "amount": round(r.get("amount") or 0, 2),
            "description": r.get("description") or "—",
            "source": r.get("source_label") or "—",
        })

    return CheckResult(
        id="orphan_sales",
        category="cashflow_coherence",
        severity="info",
        business_impact=15,  # housekeeping — useful info, no decision damage
        metrics={
            "count": count,
            "amount": round(amount, 2),
        },
        drill_data={"type": "orphan_sales_list", "items": sample},
        actions=[
            {"type": "navigate", "target": "/sales?filter=orphan",
             "label_key": "see_orphan_sales"},
        ],
    )


async def check_b3_confirmed_orders_without_sales(
    org_id: str, window: PeriodWindow,
) -> Optional[CheckResult]:
    """B3 — Orders that have transitioned to ``confirmed`` but for
    which ``_generate_sales_records`` produced nothing (or didn't run).

    Typically the symptom of:
      - a manual confirmation made before the W1 refresh pipeline
        existed (legacy orders);
      - the metrics view never having been refreshed since the order
        was confirmed.

    Both are "click Refresh and the alert disappears" cases, not real
    data-integrity bugs. We mark them as **info** + offer the refresh
    as the single primary action — the merchant doesn't need to know
    about the internal ``sales_records`` pipeline to act.

    Severity:
      - info: ≥ 1 confirmed order without a matching sales_record
      - passed: every confirmed order has at least one sales_record

    Drill items carry human-readable order_number + date + total so the
    merchant can recognise specific orders, rather than UUIDs that mean
    nothing without a DB query.
    """
    # All confirmed order_ids in the window (using created_at as the
    # period anchor since orders may be confirmed asynchronously).
    confirmed_pipeline = [
        {"$match": {
            "organization_id": org_id,
            "status": "confirmed",
            # Filter on confirmed_at when available; fall back to created_at.
            "$or": [
                {"confirmed_at": {"$gte": window.start_iso, "$lte": window.end_iso + "T23:59:59Z"}},
                {"created_at": {"$gte": window.start_iso, "$lte": window.end_iso + "T23:59:59Z"}},
            ],
        }},
        {"$project": {
            "_id": 0,
            "id": 1,
            "order_number": 1,
            "total": 1,
            "confirmed_at": 1,
            "created_at": 1,
            "customer_name": 1,
        }},
    ]
    confirmed_by_id = {}
    async for o in orders_collection.aggregate(confirmed_pipeline):
        confirmed_by_id[o["id"]] = o
    if not confirmed_by_id:
        return None

    # Order IDs that DID produce sales records (sales_records.source_record_id
    # encodes the originating order_id when generated by order_service).
    docs_with_sales = await sales_records_collection.distinct(
        "source_record_id",
        {
            "organization_id": org_id,
            "source_record_id": {"$in": list(confirmed_by_id.keys())},
        },
    )
    missing_ids = [oid for oid in confirmed_by_id if oid not in docs_with_sales]
    if not missing_ids:
        return None

    # Build human-readable drill items: order_number, customer, total,
    # date — the values a merchant uses to recognise a specific order
    # in their head ("ORD-0042 a Mario Rossi del 12 marzo per €120").
    drill_items = []
    for oid in missing_ids[:20]:
        o = confirmed_by_id[oid]
        # Resolve a friendly date — prefer confirmed_at, fall back to created_at,
        # and chop the time portion since merchants read by day.
        raw_date = o.get("confirmed_at") or o.get("created_at") or ""
        if isinstance(raw_date, str) and "T" in raw_date:
            raw_date = raw_date.split("T")[0]
        drill_items.append({
            "order_id": oid,
            "order_number": o.get("order_number") or oid[:8],
            "customer": o.get("customer_name") or "—",
            "date": raw_date or None,
            "total": round(o.get("total") or 0, 2) if isinstance(o.get("total"), (int, float)) else None,
        })

    return CheckResult(
        id="confirmed_orders_without_sales",
        category="cashflow_coherence",
        severity="info",  # FB.1 — was "warning" but it's just "needs refresh"
        business_impact=20,
        metrics={
            "missing_count": len(missing_ids),
            "total_confirmed": len(confirmed_by_id),
        },
        drill_data={
            "type": "order_list",
            "items": drill_items,
        },
        actions=[
            {"type": "refresh_metrics", "label_key": "refresh_metrics"},
            {"type": "navigate", "target": "/orders", "label_key": "open_orders"},
        ],
    )


# ─────────────────────────────────────────────────────────────────────────────
# Purchases-coherence checks (C.*) + data-quality (A2) — IB.3
# ─────────────────────────────────────────────────────────────────────────────


async def check_a2_products_without_sku(
    org_id: str,
) -> Optional[CheckResult]:
    """A2 — Active products without an SKU.

    Not a margin-killer by itself, but breaks CSV imports (matching by
    SKU) and search-by-code, plus it makes the products table harder
    to scan. Information-level: surfaces in the banner but never
    escalates.

    Severity:
      - info: ≥ 1 active product without SKU
      - passed: every active product has SKU set

    Active products only — drafts may legitimately lack an SKU until
    they're ready for distribution.
    """
    pipeline = [
        {"$match": {
            "organization_id": org_id,
            "is_active": True,
            "$or": [
                {"sku": None},
                {"sku": ""},
                {"sku": {"$exists": False}},
            ],
        }},
        {"$project": {"_id": 0, "id": 1, "name": 1}},
        {"$limit": 20},
    ]
    items = []
    count = 0
    async for p in products_collection.aggregate(pipeline):
        items.append({"product_id": p["id"], "name": p.get("name") or "—"})
        count += 1

    # Need the full count if we hit the $limit cap.
    if count >= 20:
        count = await products_collection.count_documents({
            "organization_id": org_id,
            "is_active": True,
            "$or": [{"sku": None}, {"sku": ""}, {"sku": {"$exists": False}}],
        })

    if count == 0:
        return None

    return CheckResult(
        id="products_without_sku",
        category="data_quality",
        severity="info",
        business_impact=5,  # cosmetic — no margin impact
        metrics={"count": count},
        drill_data={"type": "product_list", "items": items},
        actions=[
            {"type": "navigate", "target": "/products", "label_key": "open_products"},
        ],
    )


async def check_c1_purchases_unattributed(
    org_id: str, window: PeriodWindow,
) -> Optional[CheckResult]:
    """C1 — Share of purchases that don't carry a ``product_id``.

    A high unattributed share means the merchant's COGS aggregation
    can't be tied back to specific products → the margin numbers above
    are based partly on inference rather than direct attribution.

    Severity:
      - info: ≥ 30 % of purchases unattributed (most orgs sit here today;
              alarms would be noisy)
      - passed: < 30 % unattributed

    Note: this check doesn't have a direct "fix it" action because the
    fix is operational (use category-quantity components in product
    cost configuration). The drill surfaces the top spending categories
    so the merchant can prioritise which to link first.
    """
    pipeline = [
        {"$match": {
            "organization_id": org_id,
            "date": {"$gte": window.start_iso, "$lte": window.end_iso},
        }},
        {"$group": {
            "_id": {"$cond": [
                {"$or": [
                    {"$eq": ["$product_id", None]},
                    {"$not": ["$product_id"]},
                ]},
                "unattr",
                "attr",
            ]},
            "amount": {"$sum": {"$ifNull": [
                "$total_price",
                {"$ifNull": [
                    {"$multiply": [
                        {"$ifNull": ["$quantity", 0]},
                        {"$ifNull": ["$unit_price", 0]},
                    ]},
                    {"$ifNull": ["$amount", 0]},
                ]},
            ]}},
        }},
    ]
    attr = 0.0
    unattr = 0.0
    async for d in purchase_records_collection.aggregate(pipeline):
        if d["_id"] == "attr":
            attr = d.get("amount") or 0
        else:
            unattr = d.get("amount") or 0
    total = attr + unattr
    if total <= 0:
        return None  # No purchases — no problem

    unattr_pct = (unattr / total * 100) if total > 0 else 0
    if unattr_pct < THRESH_C1_INFO_UNATTRIBUTED_PCT:
        return None

    # Top categories of unattributed purchases — what the merchant
    # should consider linking to products to improve attribution.
    cat_pipeline = [
        {"$match": {
            "organization_id": org_id,
            "date": {"$gte": window.start_iso, "$lte": window.end_iso},
            "$or": [{"product_id": None}, {"product_id": {"$exists": False}}],
            "category": {"$nin": [None, ""]},
        }},
        {"$group": {
            "_id": "$category",
            "amount": {"$sum": {"$ifNull": [
                "$total_price",
                {"$ifNull": [
                    {"$multiply": [
                        {"$ifNull": ["$quantity", 0]},
                        {"$ifNull": ["$unit_price", 0]},
                    ]},
                    {"$ifNull": ["$amount", 0]},
                ]},
            ]}},
        }},
        {"$sort": {"amount": -1}},
        {"$limit": 10},
    ]
    top_categories = []
    async for d in purchase_records_collection.aggregate(cat_pipeline):
        top_categories.append({
            "category": d["_id"],
            "amount": round(d.get("amount") or 0, 2),
        })

    return CheckResult(
        id="purchases_unattributed",
        category="purchases_coherence",
        severity="info",
        business_impact=10,  # informational — most orgs sit at high % unattributed
        metrics={
            "unattr_amount": round(unattr, 2),
            "total_amount": round(total, 2),
            "unattr_pct": round(unattr_pct, 1),
        },
        drill_data={"type": "category_list", "items": top_categories},
        actions=[
            {"type": "navigate", "target": "/products", "label_key": "open_products"},
        ],
    )


async def check_c2_unlinked_purchase_categories(
    org_id: str,
) -> Optional[CheckResult]:
    """C2 — Purchase categories with records on file that NO product
    references via its ``cost_source.components[].category``.

    Surfaces operational gaps: e.g. the merchant set up "Affitto" and
    "Software" categories for Cashflow tracking but they're irrelevant
    to product margin (good — they shouldn't be linked). Same time
    "Farine" and "Olio" should be linked to pizzas but aren't yet.

    The check filters out a small denylist of "overhead-style"
    categories that NEVER belong on a product — they'd produce
    cosmetic noise without value.

    Severity:
      - info: ≥ 1 unlinked operational category
      - passed: every operational category is linked at least once

    NOT period-filtered: cost_source is a configuration property, the
    period parameter doesn't apply here.
    """
    # Reasonable defaults for "ignore" — these are overhead categories
    # that should NOT carry through to product cost. Made case-insensitive
    # at match time.
    _OVERHEAD_HINTS = (
        "affitto", "rent", "utenz", "utilit", "software", "abbonament",
        "marketing", "advertis", "tasse", "tax", "personale", "salar",
        "formazione", "training", "amministr", "consulen", "legal",
        "assicur", "insur", "interess", "bank", "ammort", "depreciat",
    )

    # All categories that ever appear in purchase_records for this org.
    all_cats = await purchase_records_collection.distinct(
        "category",
        {"organization_id": org_id, "category": {"$nin": [None, ""]}},
    )
    if not all_cats:
        return None

    # All categories referenced by at least one product's cost_source.
    linked = set()
    cursor = products_collection.find(
        {
            "organization_id": org_id,
            "cost_source.components.0": {"$exists": True},
        },
        {"_id": 0, "cost_source.components.category": 1},
    )
    async for p in cursor:
        for comp in p.get("cost_source", {}).get("components", []):
            cat = comp.get("category")
            if cat:
                linked.add(cat)

    # Unlinked AND not overhead-flavoured.
    def _is_overhead(name: str) -> bool:
        lower = name.lower()
        return any(h in lower for h in _OVERHEAD_HINTS)

    unlinked = [c for c in all_cats if c not in linked and not _is_overhead(c)]
    if not unlinked:
        return None

    # Surface the most-used ones first (those the merchant cares about).
    usage_pipeline = [
        {"$match": {
            "organization_id": org_id,
            "category": {"$in": unlinked},
        }},
        {"$group": {"_id": "$category", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}},
        {"$limit": 20},
    ]
    items = []
    async for d in purchase_records_collection.aggregate(usage_pipeline):
        items.append({"category": d["_id"], "purchase_count": d["count"]})

    return CheckResult(
        id="unlinked_purchase_categories",
        category="purchases_coherence",
        severity="info",
        business_impact=5,  # cosmetic — overhead-flavour cats are already filtered
        metrics={"count": len(unlinked)},
        drill_data={"type": "category_list", "items": items},
        actions=[
            {"type": "navigate", "target": "/products", "label_key": "open_products"},
        ],
    )


# ─────────────────────────────────────────────────────────────────────────────
# Trend checks (D.*)
# ─────────────────────────────────────────────────────────────────────────────


async def check_d1_coverage_drop(
    org_id: str, window: PeriodWindow, prev_window: PeriodWindow,
) -> Optional[CheckResult]:
    """D1 — Cost coverage dropped meaningfully versus the previous
    window. Flags new product launches without cost configured or
    legacy products being un-configured.

    Severity: warning when drop ≥ 10 percentage points.
    """
    cur_pct = await _cost_coverage_pct(org_id, window)
    prev_pct = await _cost_coverage_pct(org_id, prev_window)
    if cur_pct is None or prev_pct is None:
        return None

    drop_pp = prev_pct - cur_pct  # positive means coverage worsened
    if drop_pp < THRESH_D1_DROP_PP:
        return None

    # Business impact: each pp of coverage loss = 5 points, capped at 70.
    # Coverage drops are warning-worthy but rarely catastrophic by themselves
    # (the absolute coverage check A1 handles the "blind on revenue" angle).
    impact = min(int(round(drop_pp * 5)), 70)

    return CheckResult(
        id="coverage_drop",
        category="trends",
        severity="warning",
        business_impact=impact,
        metrics={
            "current_pct": round(cur_pct, 1),
            "previous_pct": round(prev_pct, 1),
            "drop_pp": round(drop_pp, 1),
        },
        actions=[
            {"type": "navigate", "target": "/products?filter=missing_cost",
             "label_key": "open_products"},
        ],
    )


async def check_d2_margin_deterioration(
    org_id: str, window: PeriodWindow, prev_window: PeriodWindow,
) -> Optional[CheckResult]:
    """D2 — Weighted margin dropped versus the previous window. May
    indicate rising costs, discount creep, or a mix shift toward
    low-margin products.

    Severity: warning when drop ≥ 5 pp.
    """
    cur = await _weighted_margin_pct(org_id, window)
    prev = await _weighted_margin_pct(org_id, prev_window)
    if cur is None or prev is None:
        return None

    drop_pp = prev - cur
    if drop_pp < THRESH_D2_DROP_PP:
        return None

    # Business impact: a 10× multiplier on the drop_pp captures the
    # decision urgency without overpowering blind-revenue checks. A
    # 5pp margin drop is meaningful but doesn't mean "you're losing
    # money" the way a negative-margin product does.
    impact = min(int(round(drop_pp * 10)), 70)

    return CheckResult(
        id="margin_deterioration",
        category="trends",
        severity="warning",
        business_impact=impact,
        metrics={
            "current_pct": round(cur, 1),
            "previous_pct": round(prev, 1),
            "drop_pp": round(drop_pp, 1),
        },
        actions=[],  # No drill — direct view of products table on the page
    )


# ─────────────────────────────────────────────────────────────────────────────
# Internal helpers
# ─────────────────────────────────────────────────────────────────────────────


async def _cost_coverage_pct(org_id: str, window: PeriodWindow) -> Optional[float]:
    """Share of products-with-sales-in-window that have cost_source set."""
    selling_ids_pipeline = [
        {"$match": {
            "organization_id": org_id,
            "product_id": {"$ne": None, "$exists": True},
            "date": {"$gte": window.start_iso, "$lte": window.end_iso},
        }},
        {"$group": {"_id": "$product_id"}},
    ]
    selling_ids = []
    async for d in sales_records_collection.aggregate(selling_ids_pipeline):
        selling_ids.append(d["_id"])

    if not selling_ids:
        return None

    configured_count = await products_collection.count_documents({
        "organization_id": org_id,
        "id": {"$in": selling_ids},
        "cost_source.components.0": {"$exists": True},
    })
    return configured_count / len(selling_ids) * 100


async def _weighted_margin_pct(org_id: str, window: PeriodWindow) -> Optional[float]:
    """Weighted margin over the window. None when no cost data."""
    pipeline = [
        {"$match": {
            "organization_id": org_id,
            "product_id": {"$ne": None, "$exists": True},
            "date": {"$gte": window.start_iso, "$lte": window.end_iso},
        }},
        {"$group": {
            "_id": None,
            "revenue": {"$sum": "$amount"},
            "cost": {"$sum": {"$ifNull": ["$cost_at_sale", 0]}},
        }},
    ]
    docs = await sales_records_collection.aggregate(pipeline).to_list(1)
    if not docs:
        return None
    d = docs[0]
    revenue = d.get("revenue") or 0
    cost = d.get("cost") or 0
    if revenue <= 0 or cost <= 0:
        return None  # Cost not known → margin undefined for the period
    return (revenue - cost) / revenue * 100


# ─────────────────────────────────────────────────────────────────────────────
# Orchestrator
# ─────────────────────────────────────────────────────────────────────────────


async def run_all_checks(
    org_id: str, period: str = "30d",
    start_date: Optional[str] = None, end_date: Optional[str] = None,
) -> dict:
    """Run every registered check in parallel and assemble the envelope
    the ``/health-check`` endpoint returns.

    Phase 1 of the intelligent-banner roadmap registers 4 checks (A1,
    A3, D1, D2). Cashflow-coherence (B.*) and Purchases-coherence
    (C.*) are added in IB.2 and IB.3 — when they land, they slot into
    this orchestrator without changes elsewhere.
    """
    window = parse_period(period, start=start_date, end=end_date)
    prev_window = previous_period(window)

    # Each check returns Optional[CheckResult]; gather concurrently
    # and drop the Nones (passed checks).
    coroutines = [
        # A — data quality
        check_a1_products_without_cost(org_id, window),
        check_a2_products_without_sku(org_id),
        check_a3_suspicious_margins(org_id, window),
        # B — cashflow coherence (IB.2)
        check_b1_cashflow_mismatch(org_id, window),
        check_b2_orphan_sales(org_id, window),
        check_b3_confirmed_orders_without_sales(org_id, window),
        # C — purchases coherence (IB.3)
        check_c1_purchases_unattributed(org_id, window),
        check_c2_unlinked_purchase_categories(org_id),
        # D — trends
        check_d1_coverage_drop(org_id, window, prev_window),
        check_d2_margin_deterioration(org_id, window, prev_window),
    ]
    raw_results = await asyncio.gather(*coroutines, return_exceptions=True)

    checks: List[CheckResult] = []
    for r in raw_results:
        if isinstance(r, Exception):
            # A failed check shouldn't break the banner. Log and skip.
            logger.warning("health-check failed: %s", r)
            continue
        if r is not None:
            checks.append(r)

    # Summary counts for the badge-closed state.
    # The frontend uses ``top_impact`` (max business_impact across all
    # detected issues) to colour the wrapper border and decide whether
    # to render the Hero layout at all.
    summary = {
        "total_checks_run": len(coroutines),
        "issues_found": len(checks),
        "critical": sum(1 for c in checks if c.severity == "critical"),
        "warnings": sum(1 for c in checks if c.severity == "warning"),
        "info": sum(1 for c in checks if c.severity == "info"),
        "top_impact": max((c.business_impact for c in checks), default=0),
    }

    return {
        "summary": summary,
        "period": {
            "label": window.label,
            "start": window.start_iso,
            "end": window.end_iso,
        },
        "checks": [c.to_dict() for c in checks],
    }
