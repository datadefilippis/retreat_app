"""
Alert Engine v3 — orchestrates intelligent alert generation.

Entry point: run_alert_engine(org_id, locale="it") -> List[Alert]

1. Loads threshold preset for the org
2. Preloads ALL financial data in parallel (single asyncio.gather)
3. Builds AlertContext
4. Runs all rules in parallel
5. Auto-resolves stale alerts
6. Returns new alerts
"""

import asyncio
import logging
from datetime import date, timedelta
from typing import List, Optional

from models import Alert
from repositories import alert_repository, analytics_repository
from modules.cashflow_monitor.alert_thresholds import get_thresholds
from modules.cashflow_monitor.kpi_formulas import net_margin_pct, cost_to_revenue_ratio

# Import all rule modules (side effect: populates ALL_RULES)
from modules.cashflow_monitor.rules import AlertContext, ALL_RULES
from modules.cashflow_monitor.rules import category_a_liquidity      # noqa: F401
from modules.cashflow_monitor.rules import category_b_profitability  # noqa: F401
from modules.cashflow_monitor.rules import category_c_cash_cycle     # noqa: F401
from modules.cashflow_monitor.rules import category_d_patterns       # noqa: F401
from modules.cashflow_monitor.rules import category_e_dependencies   # noqa: F401
from modules.cashflow_monitor.rules import category_f_commerce       # noqa: F401
from modules.cashflow_monitor.rules import category_g_data_quality   # noqa: F401

# Pillar 1 (v14.1) — data quality gate. The engine asks ``should_run_rule``
# for every rule before invoking it; rules without a ``@requires_data``
# contract are unconditionally allowed (backward-compat).
from modules.cashflow_monitor.data_quality import (
    DataQualitySnapshot,
    should_run_rule,
)

logger = logging.getLogger(__name__)

MODULE_KEY = "cashflow_monitor"


async def run_alert_engine(org_id: str, locale: str = "it") -> List[Alert]:
    """Main entry point — replaces run_alert_checks from alert_rules.py.

    Signature compatible with module_registry.alert_rules callback:
    receives org_id, returns List[Alert].
    """
    try:
        # ── 1. Load threshold preset ────────────────────────────────────
        preset = await _get_org_alert_preset(org_id)
        thresholds = get_thresholds(preset)

        # ── 2. Load dedup keys ──────────────────────────────────────────
        existing_keys = await alert_repository.find_active_dedup_keys_v3(
            org_id, MODULE_KEY,
        )

        # ── 2b. Load recently-resolved alert_types (Pillar 2.3) ─────────
        # 60-day cooldown after a merchant resolves an alert — prevents
        # the same alert_type from re-firing with a new entity_key
        # (different month, supplier rename, etc.) before the merchant
        # has reasonable time to forget the previous one. Empty set on
        # error → fail-open (no rule short-circuited by query failure).
        recently_resolved = await alert_repository.find_recently_resolved_types(
            org_id, MODULE_KEY, lookback_days=60,
        )

        # ── 3. Preload all financial data in parallel ───────────────────
        ctx = await _build_context(
            org_id, locale, thresholds, existing_keys,
            recently_resolved_alert_types=recently_resolved,
        )

        if not ctx.has_data:
            return []

        # ── 3b. Load disabled categories from preferences ──────────────
        from database import module_configs_collection
        _config = await module_configs_collection.find_one(
            {"organization_id": org_id, "module_key": MODULE_KEY},
            {"_id": 0, "settings.disabled_categories": 1},
        )
        _disabled = set((_config or {}).get("settings", {}).get("disabled_categories", []))

        # Map rule function names to categories (by module file name convention)
        _CAT_MAP = {
            "category_a": "A", "category_b": "B", "category_c": "C",
            "category_d": "D", "category_e": "E", "category_f": "F",
            "category_g": "G",
        }

        def _rule_category(rule_fn) -> str:
            """Extract category letter from the rule function's module."""
            mod = getattr(rule_fn, "__module__", "")
            for key, cat in _CAT_MAP.items():
                if key in mod:
                    return cat
            return ""

        active_rules = [
            r for r in ALL_RULES
            if _rule_category(r) not in _disabled
        ]
        if _disabled:
            logger.info(
                "alert_engine: org=%s disabled categories=%s, running %d/%d rules",
                org_id, sorted(_disabled), len(active_rules), len(ALL_RULES),
            )

        # ── 3c. Data-quality gate (Pillar 1, v14.1) ─────────────────────
        # Each rule may declare a @requires_data(...) contract. We
        # evaluate the contract once per rule against the context's
        # ``data_quality`` snapshot and drop the rule from this tick if
        # the contract is not satisfied. Rules without a contract pass
        # through unconditionally (the old behaviour).
        #
        # Two reasons we split this from the disabled-categories filter:
        # 1. The category filter is a user preference (merchant turned
        #    off cat F). The data-quality gate is an automatic
        #    safeguard (not enough data to trust). Mixing them in one
        #    list would conflate two concepts in the logs.
        # 2. Telemetry: we want to log skip reason and rule name in a
        #    structured way so a downstream dashboard can identify
        #    which rules are most often suppressed by data conditions.
        eligible_rules = []
        if ctx.data_quality is not None:
            skipped_by_gate = {}
            for rule in active_rules:
                outcome = should_run_rule(rule, ctx.data_quality)
                if outcome.allowed:
                    eligible_rules.append(rule)
                else:
                    skipped_by_gate.setdefault(outcome.reason, []).append(
                        rule.__name__
                    )
            if skipped_by_gate:
                logger.info(
                    "alert_engine: org=%s data-quality gate skipped %d rule(s): %s",
                    org_id,
                    sum(len(v) for v in skipped_by_gate.values()),
                    {k: len(v) for k, v in skipped_by_gate.items()},
                )
        else:
            # Backward-compat: if no snapshot was built (e.g. legacy
            # tests calling the engine without populating ctx.data_quality)
            # we run every rule, exactly as before v14.1.
            eligible_rules = active_rules

        # ── 4. Run all eligible rules in parallel ───────────────────────
        results = await asyncio.gather(
            *[rule(ctx) for rule in eligible_rules],
            return_exceptions=True,
        )

        new_alerts: List[Alert] = []
        active_entities: set = set()

        # Wave 13.4 — default analysis window used when a rule does NOT
        # explicitly pin a different one. Most rules in the engine work
        # off the 30-day-back window (see _build_context), so the safe
        # default is that span. Rules that work off 90d / 365d can
        # override by setting period_start / period_end / window_label
        # directly on the Alert they emit.
        today_iso = date.today().isoformat()
        default_window_start = (date.today() - timedelta(days=29)).isoformat()
        default_window_label = "30d"

        for i, result in enumerate(results):
            if isinstance(result, Exception):
                rule_name = eligible_rules[i].__name__ if i < len(eligible_rules) else "unknown"
                logger.error(
                    "alert_engine: rule %s failed for org=%s: %s",
                    rule_name, org_id, result,
                )
                continue
            if result:
                for alert in result:
                    # Wave 13.4 — stamp the default analysis window if
                    # the rule did not set one. We touch the alert via
                    # ``model_copy(update=...)`` because Alert is a
                    # pydantic model; in-place mutation works on v2 but
                    # the copy is explicit + future-proof.
                    if alert.period_start is None and alert.period_end is None:
                        alert = alert.model_copy(update={
                            "period_start": default_window_start,
                            "period_end": today_iso,
                            "window_label": default_window_label,
                        })

                    new_alerts.append(alert)
                    payload = alert.metric_payload or {}
                    alert_type = payload.get("alert_type", "")
                    entity_key = alert.entity_key or ""
                    if alert_type and entity_key:
                        active_entities.add((alert_type, entity_key))

        # ── 5. Auto-resolve stale alerts ────────────────────────────────
        if active_entities:
            try:
                resolved = await alert_repository.auto_resolve_stale(
                    org_id, MODULE_KEY, active_entities,
                )
                if resolved > 0:
                    logger.info(
                        "alert_engine: auto-resolved %d stale alerts for org=%s",
                        resolved, org_id,
                    )
            except Exception as exc:
                logger.warning(
                    "alert_engine: auto-resolve failed for org=%s: %s",
                    org_id, exc,
                )

        logger.info(
            "alert_engine: generated %d new alerts for org=%s (preset=%s, rules=%d)",
            len(new_alerts), org_id, preset, len(ALL_RULES),
        )
        return new_alerts

    except Exception as exc:
        logger.error(
            "alert_engine: fatal error for org=%s: %s", org_id, exc, exc_info=True,
        )
        return []


async def _get_org_alert_preset(org_id: str) -> str:
    """Get the org's configured alert sensitivity preset."""
    try:
        from database import module_configs_collection
        doc = await module_configs_collection.find_one(
            {"organization_id": org_id, "module_key": MODULE_KEY},
            {"_id": 0, "settings": 1},
        )
        if doc:
            settings = doc.get("settings") or {}
            return settings.get("alert_sensitivity", "standard")
    except Exception:
        pass
    return "standard"


async def _build_context(
    org_id: str,
    locale: str,
    thresholds: dict,
    existing_keys: set,
    recently_resolved_alert_types: Optional[set] = None,
) -> AlertContext:
    """Preload all data needed by alert rules in a single gather."""
    today = date.today()
    end_str = today.isoformat()

    # Date ranges
    start_90d = (today - timedelta(days=89)).isoformat()
    start_365d = (today - timedelta(days=364)).isoformat()
    start_30d = (today - timedelta(days=29)).isoformat()
    start_60d = (today - timedelta(days=59)).isoformat()

    # ── Parallel data loading ───────────────────────────────────────────
    (
        sales_90d,
        expenses_90d,
        purchases_90d,
        sales_365d,
        sales_30d_total,
        expenses_30d_total,
        purchases_30d_total,
        fixed_costs_30d,
        sales_prev_30d_total,
        expenses_prev_30d_total,
        purchases_prev_30d_total,
        open_receivables,
        open_payables,
        receivables_aging,
        customers_by_rev,
        suppliers_by_amt,
        sales_by_cat,
        expenses_by_cat_30d,
        expenses_by_cat_prev_30d,
        date_range,
    ) = await asyncio.gather(
        analytics_repository.aggregate_sales_by_date(org_id, start_90d, end_str),
        analytics_repository.aggregate_expenses_by_date(org_id, start_90d, end_str),
        analytics_repository.aggregate_purchases_by_date(org_id, start_90d, end_str),
        analytics_repository.aggregate_sales_by_date(org_id, start_365d, end_str),
        _sum_by_date(analytics_repository.aggregate_sales_by_date, org_id, start_30d, end_str),
        _sum_by_date(analytics_repository.aggregate_expenses_by_date, org_id, start_30d, end_str),
        _sum_purchases(org_id, start_30d, end_str),
        analytics_repository.aggregate_fixed_costs_total(org_id, start_30d, end_str),
        _sum_by_date(analytics_repository.aggregate_sales_by_date, org_id, start_60d, start_30d),
        _sum_by_date(analytics_repository.aggregate_expenses_by_date, org_id, start_60d, start_30d),
        _sum_purchases(org_id, start_60d, start_30d),
        analytics_repository.aggregate_open_receivables(org_id),
        analytics_repository.aggregate_open_payables(org_id),
        analytics_repository.aggregate_receivables_by_aging(org_id),
        _safe_call(analytics_repository.aggregate_customers_by_revenue_period, org_id, start_30d, end_str, 10),
        _safe_call(analytics_repository.aggregate_purchases_by_supplier, org_id, start_30d, end_str),
        _safe_call(analytics_repository.aggregate_sales_by_category, org_id, start_30d, end_str),
        _safe_call(analytics_repository.aggregate_expenses_by_category, org_id, start_30d, end_str),
        _safe_call(analytics_repository.aggregate_expenses_by_category, org_id, start_60d, start_30d),
        analytics_repository.get_date_range(org_id),
    )

    # ── Build monthly snapshots ─────────────────────────────────────────
    monthly_snapshots = _build_monthly_snapshots(
        sales_365d, expenses_90d, purchases_90d, fixed_costs_30d, today,
    )

    # ── Build overdue invoices from aging data ──────────────────────────
    overdue_invoices = _extract_overdue_invoices(receivables_aging)

    # ── Commerce operations data (v13.0) ─────────────────────────────
    from database import orders_collection, blocked_slots_collection, products_collection
    from datetime import datetime as _dt, timedelta as _td

    _now = _dt.utcnow()
    _3d_ago = _now - _td(days=3)
    _7d_ago = _now - _td(days=7)
    _24h_ago = _now - _td(hours=24)
    _30d_ago_str = (today - _td(days=30)).isoformat()
    _3d_future = (today + _td(days=3)).isoformat()

    try:
        # Draft orders older than 3 days + total value
        draft_count = await orders_collection.count_documents(
            {"organization_id": org_id, "status": "draft"})
        draft_old = await orders_collection.count_documents(
            {"organization_id": org_id, "status": "draft", "created_at": {"$lt": _3d_ago}})
        draft_val_agg = await orders_collection.aggregate([
            {"$match": {"organization_id": org_id, "status": "draft", "created_at": {"$lt": _3d_ago}}},
            {"$group": {"_id": None, "total": {"$sum": {"$ifNull": ["$total", 0]}}}},
        ]).to_list(1)
        draft_total_value = round(draft_val_agg[0]["total"], 2) if draft_val_agg else 0

        # Fulfillment delays (confirmed + pending > 7 days)
        ff_delay_cursor = orders_collection.find(
            {"organization_id": org_id, "status": {"$in": ["confirmed", "completed"]},
             "fulfillment.status": "pending", "created_at": {"$lt": _7d_ago}},
            {"_id": 0, "id": 1, "order_number": 1, "customer_name": 1, "created_at": 1, "total": 1},
        ).limit(20)
        ff_delays = []
        ff_delays_total = 0.0
        async for o in ff_delay_cursor:
            cr = o.get("created_at")
            days = (_now - cr).days if isinstance(cr, _dt) else 0
            val = o.get("total", 0)
            ff_delays.append({"order_id": o["id"], "order_number": o.get("order_number"),
                              "customer_name": o.get("customer_name"), "days_pending": days,
                              "order_value": val})
            ff_delays_total += val

        # Payment limbo (collected but still draft > 24h)
        limbo_cursor = orders_collection.find(
            {"organization_id": org_id, "status": "draft", "payment_intent": "collected",
             "created_at": {"$lt": _24h_ago}},
            {"_id": 0, "id": 1, "order_number": 1, "total": 1, "created_at": 1},
        ).limit(20)
        limbo_orders = []
        limbo_total = 0.0
        async for o in limbo_cursor:
            cr = o.get("created_at")
            hours = int((_now - cr).total_seconds() / 3600) if isinstance(cr, _dt) else 0
            amt = o.get("total", 0)
            limbo_orders.append({"order_id": o["id"], "order_number": o.get("order_number"),
                                 "amount": amt, "hours_since": hours})
            limbo_total += amt

        # Events upcoming 3 days with low fill
        eo_coll = __import__("database", fromlist=["db"]).db.event_occurrences
        upcoming_cursor = eo_coll.find(
            {"organization_id": org_id, "status": "published",
             "start_at": {"$gte": today.isoformat(), "$lte": _3d_future + "T23:59:59"}},
            {"_id": 0, "id": 1, "product_name": 1, "start_at": 1, "capacity": 1},
        ).limit(50)
        upcoming_events = []
        async for occ in upcoming_cursor:
            cap = occ.get("capacity")
            if not cap:
                continue
            booked_agg = await orders_collection.aggregate([
                {"$match": {"organization_id": org_id, "status": {"$ne": "cancelled"},
                             "items.occurrence_id": occ["id"]}},
                {"$unwind": "$items"},
                {"$match": {"items.occurrence_id": occ["id"]}},
                {"$group": {"_id": None, "total": {"$sum": "$items.quantity"}}},
            ]).to_list(1)
            booked = int(booked_agg[0]["total"]) if booked_agg else 0
            fill = round(booked / cap * 100, 1) if cap > 0 else 0
            upcoming_events.append({
                "occ_id": occ["id"], "name": occ.get("product_name", ""),
                "date": occ.get("start_at", "")[:10], "capacity": cap,
                "booked": booked, "fill_rate_pct": fill,
            })

        # Rental products with 0 utilization in 30 days
        rental_prods = await products_collection.find(
            {"organization_id": org_id, "item_type": "rental", "is_active": True, "is_published": True},
            {"_id": 0, "id": 1, "name": 1},
        ).to_list(50)
        booked_rental_pids = set()
        if rental_prods:
            rental_pid_list = [p["id"] for p in rental_prods]
            booked_agg = await blocked_slots_collection.aggregate([
                {"$match": {"organization_id": org_id, "reason": "rental",
                             "date": {"$gte": _30d_ago_str}, "product_id": {"$in": rental_pid_list}}},
                {"$group": {"_id": "$product_id"}},
            ]).to_list(100)
            booked_rental_pids = {d["_id"] for d in booked_agg}
        idle_rentals = [{"product_id": p["id"], "name": p["name"]}
                        for p in rental_prods if p["id"] not in booked_rental_pids]

        # Low stock products (stock_quantity tracked and <= 3)
        low_stock_cursor = products_collection.find(
            {"organization_id": org_id, "is_active": True, "is_published": True,
             "stock_quantity": {"$ne": None, "$lte": 3}},
            {"_id": 0, "id": 1, "name": 1, "stock_quantity": 1},
        ).limit(20)
        low_stock_prods = [{"product_id": p["id"], "name": p["name"], "stock_quantity": p["stock_quantity"]}
                           async for p in low_stock_cursor]

        # Cancellation rate last 7 days
        cancel_agg = await orders_collection.aggregate([
            {"$match": {"organization_id": org_id, "status": "cancelled", "updated_at": {"$gte": _7d_ago}}},
            {"$group": {"_id": None, "count": {"$sum": 1}, "value": {"$sum": {"$ifNull": ["$total", 0]}}}},
        ]).to_list(1)
        cancelled_7d = cancel_agg[0]["count"] if cancel_agg else 0
        cancelled_value_7d = round(cancel_agg[0]["value"], 2) if cancel_agg else 0
        total_7d = await orders_collection.count_documents(
            {"organization_id": org_id, "created_at": {"$gte": _7d_ago}})
    except Exception as _e:
        logger.warning("alert_engine: commerce data preload failed: %s", _e)
        draft_count = draft_old = 0
        ff_delays = limbo_orders = upcoming_events = idle_rentals = low_stock_prods = []
        cancelled_7d = total_7d = 0

    # ── Data quality metrics (v14.0) ───────────────────────────────────
    _cov_pct = 100
    _total_sr = 0
    _prod_no_cost_pct = 0
    _total_active_prods = 0
    try:
        from repositories.analytics_repository import count_sales_with_customer_id
        _cov = await count_sales_with_customer_id(org_id)
        _total_sr = _cov.get("total", 0)
        _with_cid = _cov.get("with_customer_id", 0)
        _cov_pct = round(_with_cid / _total_sr * 100) if _total_sr > 0 else 100
    except Exception:
        pass
    try:
        _total_active_prods = await products_collection.count_documents(
            {"organization_id": org_id, "is_active": True})
        if _total_active_prods > 0:
            _no_cost = await products_collection.count_documents(
                {"organization_id": org_id, "is_active": True,
                 "$or": [{"cost_price": None}, {"cost_price": 0}]})
            _prod_no_cost_pct = round(_no_cost / _total_active_prods * 100)
    except Exception:
        pass

    # ── Data availability ───────────────────────────────────────────────
    has_data = date_range.get("has_data", False)
    min_date = date_range.get("min_date")
    max_date = date_range.get("max_date")
    days_of_data = 0
    days_since_first = 0
    last_upload_age_days = 999
    if min_date and max_date:
        try:
            from datetime import datetime
            d1 = datetime.fromisoformat(str(min_date)).date()
            d2 = datetime.fromisoformat(str(max_date)).date()
            days_of_data = (d2 - d1).days + 1
            # "days_since_first_record" measures the AGE of the org's
            # oldest data point relative to TODAY. Used by the
            # onboarding gate. Distinct from days_of_data which only
            # measures the SPAN between min and max.
            days_since_first = (today - d1).days
            last_upload_age_days = (today - d2).days
        except Exception:
            pass

    # ── Pillar 1 (v14.1) — DataQualitySnapshot ──────────────────────────
    # Cheap to build: every input is already loaded above. We materialise
    # it once here so all 26 rules (decorated or not) see the SAME view.
    # If a rule needs a field that doesn't exist yet on the snapshot,
    # the right action is to add it to the snapshot here — not to query
    # the DB ad-hoc inside the rule body.

    # v14.2 fix (Pillar 2 smoke): due_date / payment_status coverage were
    # hard-coded to 0.0 in the snapshot, which silently blocked C1
    # (dso_worsening_trend) and C2 (high_risk_invoice) even on
    # perfectly-populated data — their @requires_data contract demands
    # `min_field_coverage={"due_dates": 30}` and 0 < 30 → skip. We now
    # compute the real coverage with two extra Mongo count_documents
    # calls (~few ms each, fail-open on any error).
    _due_cov_pct = 0.0
    _payst_cov_pct = 0.0
    try:
        from repositories.analytics_repository import (
            count_sales_with_due_date,
            count_sales_with_payment_status,
        )
        _due_res = await count_sales_with_due_date(org_id, start_30d, end_str)
        _due_cov_pct = float(_due_res.get("coverage_pct", 0.0))
        _payst_res = await count_sales_with_payment_status(org_id, start_30d, end_str)
        _payst_cov_pct = float(_payst_res.get("coverage_pct", 0.0))
    except Exception:
        pass

    data_quality_snapshot = _build_data_quality_snapshot(
        sales_by_date_90d=sales_90d or {},
        expenses_by_date_90d=expenses_90d or {},
        purchases_by_date_90d=purchases_90d or {},
        sales_count_90d_total=len(sales_90d or {}),
        expenses_count_90d_total=len(expenses_90d or {}),
        purchases_count_90d_total=len(purchases_90d or {}),
        fixed_costs_30d=fixed_costs_30d or 0.0,
        days_since_first_record=days_since_first,
        last_upload_age_days=last_upload_age_days,
        customer_id_coverage_pct=_cov_pct,
        due_date_coverage_pct=_due_cov_pct,
        payment_status_coverage_pct=_payst_cov_pct,
        sales_30d_total=sales_30d_total,
        expenses_30d_total=expenses_30d_total,
        purchases_30d_total=purchases_30d_total,
    )

    return AlertContext(
        org_id=org_id,
        locale=locale,
        thresholds=thresholds,
        existing_keys=existing_keys,
        today=today,
        current_month_day=today.day,
        sales_by_date_90d=sales_90d or {},
        expenses_by_date_90d=expenses_90d or {},
        purchases_by_date_90d=purchases_90d or {},
        sales_by_date_365d=sales_365d or {},
        monthly_snapshots=monthly_snapshots,
        total_sales_30d=sales_30d_total,
        total_expenses_30d=expenses_30d_total,
        total_purchases_30d=purchases_30d_total,
        total_fixed_costs_30d=fixed_costs_30d or 0.0,
        total_sales_prev_30d=sales_prev_30d_total,
        total_expenses_prev_30d=expenses_prev_30d_total,
        total_purchases_prev_30d=purchases_prev_30d_total,
        open_receivables=open_receivables or 0.0,
        open_payables=open_payables or 0.0,
        overdue_invoices=overdue_invoices,
        customers_by_revenue=customers_by_rev or [],
        suppliers_by_amount=suppliers_by_amt or [],
        sales_by_category=sales_by_cat or [],
        expenses_by_category_30d=expenses_by_cat_30d or [],
        expenses_by_category_prev_30d=expenses_by_cat_prev_30d or [],
        has_data=has_data,
        min_date=str(min_date) if min_date else None,
        max_date=str(max_date) if max_date else None,
        days_of_data=days_of_data,
        # Commerce operations (v13.0)
        orders_draft_count=draft_count,
        orders_draft_older_than_3d=draft_old,
        orders_draft_total_value=draft_total_value,
        fulfillment_delays=ff_delays,
        fulfillment_delays_total_value=round(ff_delays_total, 2),
        payment_limbo_orders=limbo_orders,
        payment_limbo_total=round(limbo_total, 2),
        events_upcoming_3d=upcoming_events,
        rental_products_idle=idle_rentals,
        orders_cancelled_7d=cancelled_7d,
        orders_cancelled_value_7d=cancelled_value_7d,
        orders_total_7d=total_7d,
        low_stock_products=low_stock_prods,
        # Data quality (v14.0)
        customer_id_coverage_pct=_cov_pct,
        total_sales_records=_total_sr,
        products_without_cost_pct=_prod_no_cost_pct,
        total_active_products=_total_active_prods,
        # Data quality snapshot (v14.1, Pillar 1)
        data_quality=data_quality_snapshot,
        # Anti-ridondanza cross-month (Pillar 2.3): set populated by
        # the engine entry point before calling _build_context. Default
        # empty so legacy hand-built contexts in unit tests pass through
        # untouched (rules that read this set just see no recently-
        # resolved types → don't short-circuit).
        recently_resolved_alert_types=recently_resolved_alert_types or set(),
    )


def _build_data_quality_snapshot(
    *,
    sales_by_date_90d: dict,
    expenses_by_date_90d: dict,
    purchases_by_date_90d: dict,
    sales_count_90d_total: int,
    expenses_count_90d_total: int,
    purchases_count_90d_total: int,
    fixed_costs_30d: float,
    days_since_first_record: int,
    last_upload_age_days: int,
    customer_id_coverage_pct: int,
    sales_30d_total: float,
    expenses_30d_total: float,
    purchases_30d_total: float,
    # v14.2 fix: these were always 0.0 → C1/C2 were silently blocked.
    # The caller now computes them via the analytics repository helpers
    # ``count_sales_with_due_date`` / ``count_sales_with_payment_status``.
    # Default 0.0 keeps the function backward-compatible for any caller
    # that doesn't pass them (tests, legacy code paths).
    due_date_coverage_pct: float = 0.0,
    payment_status_coverage_pct: float = 0.0,
    min_date: Optional[str] = None,  # for date-validity flag
    max_date: Optional[str] = None,
) -> DataQualitySnapshot:
    """Pure builder — no DB access, no I/O. All inputs come from the
    engine's parallel preload above. Lives next to _build_context for
    locality and is private to the engine module.

    The 30-day counts here are approximated from the count of distinct
    DATES with non-zero amounts (the by_date dicts use date strings as
    keys with float sums). For typical small-business datasets the
    approximation is conservative — actual record count is ≥ day count.
    Rules whose ``min_samples_30d`` requirement matters most (patterns,
    margin erosion) all use thresholds well above this lower bound, so
    the approximation is safe in practice.
    """
    from datetime import date, timedelta

    today = date.today()
    cutoff_30d = (today - timedelta(days=30)).isoformat()
    sales_30d_count = sum(1 for d, v in sales_by_date_90d.items() if d >= cutoff_30d and v > 0)
    expenses_30d_count = sum(1 for d, v in expenses_by_date_90d.items() if d >= cutoff_30d and v > 0)
    purchases_30d_count = sum(1 for d, v in purchases_by_date_90d.items() if d >= cutoff_30d and v > 0)

    # Build available_datasets — a dataset counts as "available" when
    # at least one day in the last 30 has a non-zero entry. This is the
    # most useful signal for rules that ask "do I have data on this?"
    available: set = set()
    if sales_30d_count > 0:
        available.add("sales")
    if expenses_30d_count > 0:
        available.add("expenses")
    if purchases_30d_count > 0:
        available.add("purchases")
    if fixed_costs_30d > 0:
        available.add("fixed_costs")
    # Field-coverage based datasets — derived from existing metrics so
    # we don't issue extra DB queries here.
    if customer_id_coverage_pct >= 1:
        available.add("customer_ids")
    # Note: "orders", "due_dates", "payment_status" are not derivable
    # from the by_date aggregates we have here. Rules requiring them
    # use ``min_field_coverage`` instead, which short-circuits to "no
    # constraint" when the snapshot doesn't carry the field — safe by
    # design (treated as 100% coverage = no skip).

    # ── Outlier detection (P1.6) ────────────────────────────────────────
    # Cheap 5-sigma scan over the 30-day daily aggregates. If any single
    # day deviates from the mean by more than 5 standard deviations, we
    # flag the window — rules marked ``outlier_robust=True`` will skip
    # this tick to avoid emitting "spike +500%" alerts driven by a
    # single anomalous record (e.g. an admin re-imported a CSV).
    has_outlier = _detect_5sigma_outlier_30d(
        sales_by_date_90d, cutoff_30d
    ) or _detect_5sigma_outlier_30d(
        expenses_by_date_90d, cutoff_30d
    ) or _detect_5sigma_outlier_30d(
        purchases_by_date_90d, cutoff_30d
    )

    # ── Date validity (P1.8) ────────────────────────────────────────────
    # Flag suspicious dates so an admin can be alerted to clean them up.
    # Suspicious = future > 7 days, or pre-2020 (common date typos).
    # We don't EXCLUDE these from aggregates here (that's the engine's
    # job via $match clauses); we just count them so we can warn.
    suspicious = _count_suspicious_dates(
        sales_by_date_90d, today.isoformat()
    ) + _count_suspicious_dates(
        expenses_by_date_90d, today.isoformat()
    ) + _count_suspicious_dates(
        purchases_by_date_90d, today.isoformat()
    )

    return DataQualitySnapshot(
        days_since_first_record=days_since_first_record,
        last_upload_age_days=last_upload_age_days,
        sales_count_30d=sales_30d_count,
        expenses_count_30d=expenses_30d_count,
        purchases_count_30d=purchases_30d_count,
        fixed_costs_active=int(fixed_costs_30d > 0),
        sales_count_90d=sales_count_90d_total,
        expenses_count_90d=expenses_count_90d_total,
        purchases_count_90d=purchases_count_90d_total,
        customer_id_coverage_pct=float(customer_id_coverage_pct or 0),
        # v14.2: real coverage values now flow in from the caller —
        # see _build_context for the source query. Defaulting to 0.0
        # at the parameter level preserves the prior contract for any
        # legacy caller that doesn't pass them.
        payment_status_coverage_pct=float(payment_status_coverage_pct or 0.0),
        due_date_coverage_pct=float(due_date_coverage_pct or 0.0),
        has_outlier_5sigma_30d=has_outlier,
        suspicious_dates_count=suspicious,
        available_datasets=frozenset(available),
    )


def _detect_5sigma_outlier_30d(by_date: dict, cutoff_iso: str) -> bool:
    """Return True if any day in the last 30d is far from the median.

    Why median-based (MAD), not mean+stddev:
    Classical 5σ has a self-defeating property — a single huge outlier
    inflates the stddev so much that it itself falls below the
    threshold (mean+5σ). We saw this on a Demo Restaurant test: 9 days
    of €100 + 1 day of €100k → stddev so large that the €100k spike
    isn't flagged.

    The MAD approach (Median Absolute Deviation × 1.4826 ≈ σ for
    normal distributions) is the textbook robust alternative: the
    median doesn't move with one outlier, so the threshold stays in
    a meaningful range.

    Threshold of 5 × scaled_MAD chosen to be conservative: catches
    catastrophic spikes (10x+ baseline) without flagging normal
    business variance (2-3x baseline).
    """
    values = sorted(v for d, v in by_date.items() if d >= cutoff_iso and v > 0)
    if len(values) < 5:
        return False
    n = len(values)
    median = values[n // 2] if n % 2 else (values[n // 2 - 1] + values[n // 2]) / 2
    if median <= 0:
        return False
    abs_devs = sorted(abs(v - median) for v in values)
    mad = abs_devs[n // 2] if n % 2 else (abs_devs[n // 2 - 1] + abs_devs[n // 2]) / 2
    # If MAD is 0 (all values identical or nearly so), fall back to a
    # simple "5x median" heuristic — same intent, different scale.
    if mad <= 0:
        threshold = median * 5
    else:
        scaled_sigma = 1.4826 * mad
        threshold = median + 5 * scaled_sigma
    return any(v > threshold for v in values)


def _count_suspicious_dates(by_date: dict, today_iso: str) -> int:
    """Count date keys that look like data-entry mistakes.

    Suspicious = future > 7 days from today, or before 2020-01-01.
    Pure function — pure date-string lex comparison (ISO format is
    safe for chronological ordering as long as the date is yyyy-mm-dd).
    Returns 0 for any malformed entries (no crash on partial dates).
    """
    from datetime import date as _date, timedelta as _td
    try:
        today = _date.fromisoformat(today_iso)
    except ValueError:
        return 0
    future_cutoff = (today + _td(days=7)).isoformat()
    past_cutoff = "2020-01-01"
    suspicious = 0
    for d in by_date.keys():
        if not isinstance(d, str) or len(d) < 10:
            suspicious += 1
            continue
        if d > future_cutoff or d < past_cutoff:
            suspicious += 1
    return suspicious


# ── Helper functions ─────────────────────────────────────────────────────────

async def _sum_by_date(agg_fn, org_id: str, start: str, end: str) -> float:
    """Call an aggregate_*_by_date function and return the sum."""
    try:
        data = await agg_fn(org_id, start, end)
        return sum(data.values()) if data else 0.0
    except Exception:
        return 0.0


async def _sum_purchases(org_id: str, start: str, end: str) -> float:
    """Sum purchase amounts for a period."""
    try:
        data = await analytics_repository.aggregate_purchases_by_date(org_id, start, end)
        return sum(data.values()) if data else 0.0
    except Exception:
        return 0.0


async def _safe_call(fn, *args, **kwargs):
    """Call an async function, return empty list on error."""
    try:
        return await fn(*args, **kwargs)
    except Exception:
        return []


def _build_monthly_snapshots(
    sales_365d: dict,
    expenses_90d: dict,
    purchases_90d: dict,
    fixed_costs_monthly: float,
    today: date,
) -> list:
    """Build monthly aggregated snapshots from daily data."""
    from collections import defaultdict

    monthly: dict = defaultdict(lambda: {"sales": 0, "expenses": 0, "purchases": 0})

    for d_str, amt in (sales_365d or {}).items():
        month = d_str[:7]  # "YYYY-MM"
        monthly[month]["sales"] += amt

    for d_str, amt in (expenses_90d or {}).items():
        month = d_str[:7]
        monthly[month]["expenses"] += amt

    for d_str, amt in (purchases_90d or {}).items():
        month = d_str[:7]
        monthly[month]["purchases"] += amt

    snapshots = []
    for month in sorted(monthly.keys()):
        data = monthly[month]
        sales = data["sales"]
        expenses = data["expenses"]
        purchases = data["purchases"]
        fc = fixed_costs_monthly or 0
        total_outflows = expenses + purchases + fc
        margin = net_margin_pct(sales - total_outflows, sales)
        ratio = cost_to_revenue_ratio(total_outflows, sales)

        snapshots.append({
            "month": month,
            "sales": round(sales, 2),
            "expenses": round(expenses, 2),
            "purchases": round(purchases, 2),
            "fixed_costs": round(fc, 2),
            "net_margin_pct": margin,
            "cost_ratio": ratio,
        })

    return snapshots


def _extract_overdue_invoices(aging_data: list) -> list:
    """Extract individual overdue invoices from aging bucket data."""
    overdue = []
    if not aging_data:
        return overdue

    for bucket in aging_data:
        bucket_name = bucket.get("_id") or bucket.get("bucket", "")
        if "61" in str(bucket_name) or "90" in str(bucket_name) or ">" in str(bucket_name):
            # These are significantly overdue
            overdue.append({
                "customer": bucket.get("customer", "Multiple"),
                "amount": bucket.get("total", 0),
                "overdue_days": 90 if "90" in str(bucket_name) else 75,
                "bucket": bucket_name,
            })

    return overdue
