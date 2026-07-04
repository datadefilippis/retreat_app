"""
Cost Resolver — pure service that computes a product's unit cost (W1.S2).

Given a product carrying a ``cost_source`` (see ``models/cost_source.py``),
this service returns a deterministic unit-cost answer along with a
decomposition that powers:

  - Performance Prodotti gross-margin display (W1.S9)
  - Live cost preview in the admin UI (W1.S3)
  - ``cost_at_sale`` snapshot on confirmed orders (W1.S7)
  - Monthly snapshots in ``product_cost_history`` (W1.S8)
  - AI Analyst grounding (W1.S6 / cost_trend tools)

The resolver is the **single source of truth** for "what is the cost of
this product right now (or at as_of)". Every other module that needs
the answer asks here — so a change in calculation logic propagates
consistently across margin, snapshot, and AI insight.

Design
------
The resolver is a class with a per-call lifetime, holding in-memory
caches for category WAC, category pool, linking products' revenue, and
product units sold. A single ``CostResolver`` instance is meant to be
created at the top of a batch (e.g. refresh_product_metrics) and reused
across all its resolve() calls. This collapses what would be N×M Mongo
round-trips into N + M.

Three high-level operations:

  1. ``resolve(product)`` → ``ResolverResult``
     For ONE product, computes Σ components and returns value, source,
     confidence, decomposition.

  2. ``resolve_many(products)`` → Dict[product_id, ResolverResult]
     Batch variant. Same caches benefit all products of the batch.

  3. The module-level ``resolve_unit_cost(product, org_id, as_of=None)``
     convenience function, for callers that need a one-shot resolve
     without managing the resolver lifecycle.

Method semantics
----------------
``method`` on the CostSource selects the time window for every
category-based component within that source:

  fixed     no rolling — category components fall back to ``latest``
            (single most recent record). Manual components are unaffected.
  latest    only the single most recent purchase record per category.
  wac_30d   weighted average over the last 30 days.
  wac_90d   over 90 days (default for new products).
  wac_180d  over 180 days.
  wac_365d  over 365 days.

The window is computed relative to ``as_of`` (defaults to now). All
windows are inclusive on both ends.

Edge cases (documented honestly, not papered over)
--------------------------------------------------
- A component fails to resolve (no purchases in window, empty pool,
  unknown category): its contribution is None, the decomposition row
  carries ``failed: true`` with a ``reason``. The OTHER components
  still contribute. The final ``value`` is None only if EVERY
  component failed (or there are no components).

- ``org_average`` with ``scope=same_item_type``: filtering purchase
  records by item_type is unreliable today because most
  ``purchase_records`` have ``product_id`` null. We instead use the
  org-wide total spent and divide by the units sold of products that
  share the same item_type. This is approximate; the confidence flag
  is ``estimated_org_average`` so the UI and AI can communicate the
  imprecision.

- Unit mismatch on ``category_quantity``: the WAC of a category is
  computed only on purchase_records with a matching ``unit`` field
  (no auto-conversion in Wave 1). If the merchant linked qty_unit="kg"
  but their actual purchases are recorded in "g", the resolver returns
  None for that component until they normalise.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Set, Tuple

from database import (
    products_collection,
    purchase_records_collection,
    sales_records_collection,
)
from models.cost_source import CostSource, CostComponent
from models.common import utc_now

logger = logging.getLogger(__name__)


# ── Method → window size mapping ─────────────────────────────────────────────
# Single source of truth. Adding a new method (e.g. "wac_730d") requires
# updating this map AND the Literal in CostSource. The two stay in sync
# because mypy / Pydantic will reject any unknown method passed in.

_METHOD_TO_DAYS: Dict[str, int] = {
    "wac_30d": 30,
    "wac_90d": 90,
    "wac_180d": 180,
    "wac_365d": 365,
    # "fixed" and "latest" don't use a rolling window — handled
    # separately by the category resolvers (single-record lookup).
}


# ── Result types ─────────────────────────────────────────────────────────────


@dataclass
class ComponentContribution:
    """Output of resolving a SINGLE component within a CostSource.

    Carries the resolved value plus enough metadata for the
    decomposition row in the UI ("Sugo: 0.15 kg × €4/kg = €0.60").
    """

    value: Optional[float]
    details: Dict[str, Any] = field(default_factory=dict)
    reason: Optional[str] = None  # populated only when value is None


@dataclass
class ResolverResult:
    """Final answer for ONE product's resolve call.

    ``value`` is the sum of every component's contribution. It is None
    when there are no components OR every component failed — i.e. there
    is genuinely no cost to report. Zero is a valid answer (e.g. a free
    course): the resolver distinguishes "configured as zero" from
    "unknown".

    ``source`` labels which kinds of components contributed:
      - "manual"           — only manual components
      - "categories"       — only category_quantity / category_share
      - "mixed"            — both manual and category components
      - "org_average"      — at least one org_average component
      - "none"             — no components or all failed

    ``confidence`` is the downstream-friendly tag:
      - "actual"                — every contributing component was a
                                  category one with real purchase data
      - "declared"              — only manual contributions
      - "mixed"                 — manual + category
      - "estimated_org_average" — at least one org_average contributed
      - "unknown"               — value is None
    """

    value: Optional[float]
    source: str
    confidence: str
    method: str
    period_start: str           # ISO date
    period_end: str             # ISO date
    decomposition: List[dict] = field(default_factory=list)


# ── Internal helpers ─────────────────────────────────────────────────────────


def _spent_expression() -> dict:
    """MongoDB aggregation expression for the "money spent" of a
    purchase_record, with a documented fallback chain.

    Most records have ``total_price``; some have only ``quantity`` and
    ``unit_price`` (in which case we reconstruct); some have only
    ``amount`` (a generic catch-all for legacy imports). Aggregating
    these three signals into a single ``$ifNull`` ladder keeps the
    resolver honest with what's actually on disk in this codebase.

    Reading order:
      1. total_price (most specific)
      2. quantity * unit_price (reconstructed)
      3. amount (legacy fallback)
      4. 0 (last resort — record is malformed but won't break aggregation)
    """
    return {
        "$ifNull": [
            "$total_price",
            {
                "$ifNull": [
                    {"$multiply": [
                        {"$ifNull": ["$quantity", 0]},
                        {"$ifNull": ["$unit_price", 0]},
                    ]},
                    {"$ifNull": ["$amount", 0]},
                ]
            },
        ]
    }


def _iso_date(dt: datetime) -> str:
    """Calendar-day truncation as ISO string (matches what purchase_records
    use for the ``date`` field)."""
    return dt.date().isoformat()


# ── Resolver ─────────────────────────────────────────────────────────────────


class CostResolver:
    """Per-batch unit-cost resolver.

    Construct once for an (org_id, as_of) pair, then call ``resolve()``
    for every product in the batch. The in-memory caches eliminate
    redundant Mongo round-trips when products share categories.

    The resolver does NOT mutate any data. It only reads.
    """

    def __init__(
        self,
        org_id: str,
        as_of: Optional[datetime] = None,
    ):
        self.org_id = org_id
        self.as_of = as_of or utc_now()

        # Caches scoped to this resolver instance. Keys are deliberately
        # specific so we never confuse a wac_30d result with a wac_90d
        # one for the same category.
        self._category_wac_cache: Dict[Tuple[str, str, str], Optional[float]] = {}
        self._category_pool_cache: Dict[Tuple[str, str], Optional[float]] = {}
        self._linking_products_cache: Dict[str, List[str]] = {}
        self._linking_revenue_cache: Dict[Tuple[str, str], Dict[str, float]] = {}
        self._units_sold_cache: Dict[Tuple[str, str], int] = {}
        self._org_scope_cache: Dict[Tuple[str, str, str], Optional[float]] = {}

    # ── Public API ───────────────────────────────────────────────────────────

    async def resolve(self, product: dict) -> ResolverResult:
        """Resolve unit cost for ONE product document.

        ``product`` is expected to carry at least ``id``, ``cost_source``,
        and ``category``/``item_type`` (the latter two only consulted by
        org_average components). Other fields are ignored.
        """
        method = self._product_method(product)
        period_start, period_end = self._period_for(method)

        raw_source = product.get("cost_source") or {}
        components_raw = raw_source.get("components") or []
        if not components_raw:
            return ResolverResult(
                value=None,
                source="none",
                confidence="unknown",
                method=method,
                period_start=period_start,
                period_end=period_end,
                decomposition=[],
            )

        total = 0.0
        decomposition: List[dict] = []
        types_seen: Set[str] = set()
        any_failed = False
        any_success = False

        for raw_comp in components_raw:
            # Parse defensively. A bad component shouldn't crash the
            # whole resolve — it should fail gracefully with a reason.
            try:
                comp = CostComponent(**raw_comp)
            except Exception as e:
                decomposition.append({
                    "type": raw_comp.get("type", "unknown"),
                    "label": raw_comp.get("label", "(invalid)"),
                    "contribution": None,
                    "failed": True,
                    "reason": f"invalid_component: {e}",
                })
                any_failed = True
                continue

            contrib = await self._resolve_component(comp, method, product)
            types_seen.add(comp.type)

            row = {
                "type": comp.type,
                "label": comp.label,
                "contribution": contrib.value,
                "details": contrib.details,
                "failed": contrib.value is None,
            }
            if contrib.reason:
                row["reason"] = contrib.reason
            decomposition.append(row)

            if contrib.value is not None:
                total += contrib.value
                any_success = True
            else:
                any_failed = True

        # If nothing succeeded, the product effectively has no cost.
        if not any_success:
            return ResolverResult(
                value=None,
                source="none",
                confidence="unknown",
                method=method,
                period_start=period_start,
                period_end=period_end,
                decomposition=decomposition,
            )

        return ResolverResult(
            value=round(total, 4),
            source=self._derive_source_label(types_seen),
            confidence=self._derive_confidence(types_seen, any_failed),
            method=method,
            period_start=period_start,
            period_end=period_end,
            decomposition=decomposition,
        )

    async def resolve_many(
        self, products: List[dict]
    ) -> Dict[str, ResolverResult]:
        """Batch resolve. Same caches benefit every product in the list.

        Returns a dict keyed by ``product['id']`` for convenient lookup.
        """
        out: Dict[str, ResolverResult] = {}
        for prod in products:
            pid = prod.get("id")
            if not pid:
                continue
            out[pid] = await self.resolve(prod)
        return out

    # ── Component-level resolvers ────────────────────────────────────────────

    async def _resolve_component(
        self,
        comp: CostComponent,
        method: str,
        product: dict,
    ) -> ComponentContribution:
        """Dispatch to the per-type resolver. Each returns a
        ``ComponentContribution`` even on failure (value=None + reason)
        so the caller can render the decomposition row consistently."""
        if comp.type == "manual":
            # No DB hit, no failure mode. The validator already ensured
            # manual_value is not None.
            return ComponentContribution(
                value=float(comp.manual_value or 0),
                details={"manual_value": comp.manual_value},
            )

        if comp.type == "category_quantity":
            wac = await self._get_category_wac(
                comp.category, comp.qty_unit, method
            )
            if wac is None:
                return ComponentContribution(
                    value=None,
                    details={"category": comp.category, "unit": comp.qty_unit},
                    reason="no_purchases_in_window",
                )
            contribution = (comp.qty_per_unit or 0) * wac
            return ComponentContribution(
                value=round(contribution, 4),
                details={
                    "category": comp.category,
                    "qty_per_unit": comp.qty_per_unit,
                    "qty_unit": comp.qty_unit,
                    "wac": round(wac, 4),
                },
            )

        if comp.type == "category_share":
            pool = await self._get_category_pool(comp.category, method)
            if pool is None or pool <= 0:
                return ComponentContribution(
                    value=None,
                    details={"category": comp.category},
                    reason="empty_pool",
                )

            if comp.share_pct is not None:
                share = comp.share_pct / 100.0
                share_kind = "fixed"
            else:
                share = await self._get_auto_share(
                    product.get("id", ""), comp.category, method
                )
                share_kind = "auto_revenue_proportional"

            units = await self._get_product_units_sold(
                product.get("id", ""), method
            )
            if units == 0:
                return ComponentContribution(
                    value=None,
                    details={"category": comp.category, "pool": pool, "share": share},
                    reason="no_sales_in_window",
                )

            contribution = (pool * share) / units
            return ComponentContribution(
                value=round(contribution, 4),
                details={
                    "category": comp.category,
                    "pool": round(pool, 2),
                    "share": round(share, 4),
                    "share_kind": share_kind,
                    "units_sold": units,
                },
            )

        if comp.type == "org_average":
            value = await self._get_org_average(comp.scope, product, method)
            if value is None:
                return ComponentContribution(
                    value=None,
                    details={"scope": comp.scope},
                    reason="insufficient_data",
                )
            return ComponentContribution(
                value=round(value, 4),
                details={"scope": comp.scope},
            )

        # Defensive — the Pydantic Literal should make this unreachable.
        return ComponentContribution(
            value=None,
            details={"raw_type": comp.type},
            reason="unknown_component_type",
        )

    # ── Mongo readers (cached) ───────────────────────────────────────────────

    async def _get_category_wac(
        self, category: Optional[str], unit: Optional[str], method: str
    ) -> Optional[float]:
        """WAC of ONE category over the method's window, restricted to
        purchase records with the matching ``unit``.

        Two signals must both be present on each record to be counted:
          - quantity > 0  (else division by zero)
          - unit matches  (else we'd be mixing kg with L)

        For methods ``fixed`` and ``latest``, we use the single most
        recent matching record instead of aggregating a window.
        """
        if not category or not unit:
            return None

        key = (category, unit, method)
        if key in self._category_wac_cache:
            return self._category_wac_cache[key]

        if method in ("fixed", "latest"):
            doc = await purchase_records_collection.find_one(
                {
                    "organization_id": self.org_id,
                    "category": category,
                    "unit": unit,
                    "quantity": {"$gt": 0},
                },
                sort=[("date", -1)],
            )
            if not doc:
                self._category_wac_cache[key] = None
                return None
            qty = doc.get("quantity") or 0
            spent = (
                doc.get("total_price")
                or ((doc.get("quantity") or 0) * (doc.get("unit_price") or 0))
                or doc.get("amount")
                or 0
            )
            result = (spent / qty) if qty > 0 else None
            self._category_wac_cache[key] = result
            return result

        period_start, period_end = self._period_for(method)
        pipeline = [
            {
                "$match": {
                    "organization_id": self.org_id,
                    "category": category,
                    "unit": unit,
                    "quantity": {"$gt": 0},
                    "date": {"$gte": period_start, "$lte": period_end},
                }
            },
            {
                "$group": {
                    "_id": None,
                    "total_spent": {"$sum": _spent_expression()},
                    "total_qty": {"$sum": "$quantity"},
                }
            },
        ]
        docs = await purchase_records_collection.aggregate(pipeline).to_list(1)
        if not docs:
            self._category_wac_cache[key] = None
            return None
        d = docs[0]
        total_qty = d.get("total_qty") or 0
        total_spent = d.get("total_spent") or 0
        result = (total_spent / total_qty) if total_qty > 0 else None
        self._category_wac_cache[key] = result
        return result

    async def _get_category_pool(
        self, category: Optional[str], method: str
    ) -> Optional[float]:
        """Total spent on a category in the method's window, regardless
        of unit. Used for ``category_share`` components where the merchant
        attributes a percentage of the bucket to the product."""
        if not category:
            return None

        key = (category, method)
        if key in self._category_pool_cache:
            return self._category_pool_cache[key]

        if method in ("fixed", "latest"):
            doc = await purchase_records_collection.find_one(
                {"organization_id": self.org_id, "category": category},
                sort=[("date", -1)],
            )
            if not doc:
                self._category_pool_cache[key] = None
                return None
            result = (
                doc.get("total_price")
                or ((doc.get("quantity") or 0) * (doc.get("unit_price") or 0))
                or doc.get("amount")
                or 0
            )
            self._category_pool_cache[key] = result
            return result

        period_start, period_end = self._period_for(method)
        pipeline = [
            {
                "$match": {
                    "organization_id": self.org_id,
                    "category": category,
                    "date": {"$gte": period_start, "$lte": period_end},
                }
            },
            {
                "$group": {
                    "_id": None,
                    "total": {"$sum": _spent_expression()},
                }
            },
        ]
        docs = await purchase_records_collection.aggregate(pipeline).to_list(1)
        if not docs:
            self._category_pool_cache[key] = None
            return None
        result = docs[0].get("total") or 0
        self._category_pool_cache[key] = result
        return result

    async def _get_linking_product_ids(self, category: str) -> List[str]:
        """All products in this org whose cost_source links the given
        category (either via category_quantity OR category_share).

        Used to compute auto-proportional share among the products that
        compete for the same category pool. Cached because multiple
        products in the same batch may ask about the same category.
        """
        if category in self._linking_products_cache:
            return self._linking_products_cache[category]

        cursor = products_collection.find(
            {
                "organization_id": self.org_id,
                "cost_source.components": {
                    "$elemMatch": {
                        "category": category,
                        "type": {"$in": ["category_quantity", "category_share"]},
                    }
                },
            },
            {"_id": 0, "id": 1},
        )
        ids = [doc["id"] async for doc in cursor]
        self._linking_products_cache[category] = ids
        return ids

    async def _get_auto_share(
        self, product_id: str, category: str, method: str
    ) -> float:
        """Auto-proportional share for a ``category_share`` component
        with share_pct=None.

        Formula: this product's revenue ÷ Σ revenue of every product
        that links the same category. Auto-balancing: if revenue mix
        shifts, the share automatically follows.

        Edge cases:
          - Only this product links the category → share = 1.0 (gets
            the whole pool).
          - All linking products have zero revenue → split equally
            (defensive: avoids 0/0 = NaN).
        """
        period_start, period_end = self._period_for(method)
        cache_key = (category, method)

        if cache_key not in self._linking_revenue_cache:
            linking_ids = await self._get_linking_product_ids(category)
            if not linking_ids:
                self._linking_revenue_cache[cache_key] = {}
            else:
                pipeline = [
                    {
                        "$match": {
                            "organization_id": self.org_id,
                            "product_id": {"$in": linking_ids},
                            "date": {"$gte": period_start, "$lte": period_end},
                        }
                    },
                    {
                        "$group": {
                            "_id": "$product_id",
                            "revenue": {"$sum": "$amount"},
                        }
                    },
                ]
                rev_by_pid: Dict[str, float] = {pid: 0.0 for pid in linking_ids}
                async for doc in sales_records_collection.aggregate(pipeline):
                    rev_by_pid[doc["_id"]] = doc.get("revenue") or 0
                self._linking_revenue_cache[cache_key] = rev_by_pid

        rev_by_pid = self._linking_revenue_cache[cache_key]
        if not rev_by_pid or product_id not in rev_by_pid:
            return 0.0

        total_rev = sum(rev_by_pid.values())
        if total_rev <= 0:
            # All zero → fair split among linking products.
            return 1.0 / max(len(rev_by_pid), 1)
        return rev_by_pid[product_id] / total_rev

    async def _get_product_units_sold(
        self, product_id: str, method: str
    ) -> int:
        """Count of sales_records for this product in the method's window.

        Note: each sales_record represents ONE unit (verified in
        ``services/order_service._generate_sales_records``). Counting
        documents is therefore equivalent to summing quantity, with the
        bonus of using a cheap count_documents() instead of an aggregation.
        """
        if not product_id:
            return 0
        cache_key = (product_id, method)
        if cache_key in self._units_sold_cache:
            return self._units_sold_cache[cache_key]

        period_start, period_end = self._period_for(method)
        count = await sales_records_collection.count_documents({
            "organization_id": self.org_id,
            "product_id": product_id,
            "date": {"$gte": period_start, "$lte": period_end},
        })
        self._units_sold_cache[cache_key] = count
        return count

    async def _get_org_average(
        self, scope: Optional[str], product: dict, method: str
    ) -> Optional[float]:
        """Org-level WAC as a fallback estimate.

        Three scopes supported:

          ``all``               total org purchases / total org units sold
          ``same_category``     purchases of product.category /
                                units sold of products in that category
          ``same_item_type``    org purchases (no item_type filter — see
                                module docstring for why) /
                                units sold of products with this item_type

        Returns None when there's insufficient data (no purchases, no
        sales, or scoping field missing on the product).
        """
        if not scope:
            return None

        period_start, period_end = self._period_for(method)
        cache_key = (
            scope,
            product.get("category") if scope == "same_category" else product.get("item_type") if scope == "same_item_type" else "",
            method,
        )
        if cache_key in self._org_scope_cache:
            return self._org_scope_cache[cache_key]

        purchase_match: dict = {
            "organization_id": self.org_id,
            "date": {"$gte": period_start, "$lte": period_end},
        }
        sales_match: dict = {
            "organization_id": self.org_id,
            "date": {"$gte": period_start, "$lte": period_end},
        }

        if scope == "same_category":
            cat = product.get("category")
            if not cat:
                self._org_scope_cache[cache_key] = None
                return None
            purchase_match["category"] = cat
            cat_ids = [
                doc["id"] async for doc in products_collection.find(
                    {"organization_id": self.org_id, "category": cat},
                    {"_id": 0, "id": 1},
                )
            ]
            sales_match["product_id"] = {"$in": cat_ids} if cat_ids else {"$in": ["__no_match__"]}

        elif scope == "same_item_type":
            it = product.get("item_type")
            if not it:
                self._org_scope_cache[cache_key] = None
                return None
            it_ids = [
                doc["id"] async for doc in products_collection.find(
                    {"organization_id": self.org_id, "item_type": it},
                    {"_id": 0, "id": 1},
                )
            ]
            sales_match["product_id"] = {"$in": it_ids} if it_ids else {"$in": ["__no_match__"]}

        # Total spent in scope.
        p_pipeline = [
            {"$match": purchase_match},
            {"$group": {"_id": None, "total": {"$sum": _spent_expression()}}},
        ]
        p_docs = await purchase_records_collection.aggregate(p_pipeline).to_list(1)
        total_spent = (p_docs[0].get("total") if p_docs else 0) or 0

        # Total units sold in scope.
        total_units = await sales_records_collection.count_documents(sales_match)

        if total_units <= 0 or total_spent <= 0:
            self._org_scope_cache[cache_key] = None
            return None

        result = total_spent / total_units
        self._org_scope_cache[cache_key] = result
        return result

    # ── Internals ────────────────────────────────────────────────────────────

    def _product_method(self, product: dict) -> str:
        """Read the method from product.cost_source.method with a safe
        default (``wac_90d``) for products missing or malformed."""
        src = product.get("cost_source") or {}
        method = src.get("method") or "wac_90d"
        if method not in (
            "fixed", "latest", "wac_30d", "wac_90d", "wac_180d", "wac_365d"
        ):
            method = "wac_90d"
        return method

    def _period_for(self, method: str) -> Tuple[str, str]:
        """Period bounds (inclusive) as ISO date strings for the given
        method. For ``fixed`` and ``latest`` the window is meaningless
        but we still return something so callers can carry consistent
        metadata in their results.
        """
        end_iso = _iso_date(self.as_of)
        days = _METHOD_TO_DAYS.get(method)
        if days is None:
            # fixed / latest — synthetic "365 days" window so timestamps
            # are present in the result envelope but query helpers
            # ignore the bounds in single-record mode.
            days = 365
        start_dt = self.as_of - timedelta(days=days)
        return _iso_date(start_dt), end_iso

    @staticmethod
    def _derive_source_label(types_seen: Set[str]) -> str:
        """Coarse label of which kinds of components contributed.

        Used in ``ResolverResult.source`` for the AI Analyst grounding
        and the reconciliation widget.
        """
        if "org_average" in types_seen:
            return "org_average"
        category_types = {"category_quantity", "category_share"} & types_seen
        if category_types and "manual" in types_seen:
            return "mixed"
        if category_types:
            return "categories"
        if "manual" in types_seen:
            return "manual"
        return "none"

    @staticmethod
    def _derive_confidence(types_seen: Set[str], any_failed: bool) -> str:
        """Confidence tag for downstream consumers.

        ``estimated_org_average`` always wins when an org_average
        component contributed — the AI Analyst then knows to caveat
        any insight built on top of that number.
        """
        if "org_average" in types_seen:
            return "estimated_org_average"
        category_types = {"category_quantity", "category_share"} & types_seen
        if category_types and "manual" in types_seen:
            return "mixed"
        if category_types:
            return "actual"
        if "manual" in types_seen:
            return "declared"
        return "unknown"


# ── Module-level convenience ─────────────────────────────────────────────────


async def resolve_unit_cost(
    product: dict,
    org_id: str,
    as_of: Optional[datetime] = None,
) -> ResolverResult:
    """One-shot resolve for callers that don't manage a batch.

    Equivalent to creating a CostResolver and calling resolve() once.
    Use the class directly when resolving 2+ products to benefit from
    the in-memory caches.
    """
    resolver = CostResolver(org_id=org_id, as_of=as_of)
    return await resolver.resolve(product)
