"""
AI Analytics Service — Phase 2 extraction from ai_service.py.

Responsibility: raw data aggregation and metrics computation needed
by the AI layer.  No LLM calls here.

The public interface is identical to what ai_service.py previously
exposed, so existing callers that import from ai_service still work
via the facade.
"""
import logging
from typing import Optional
from datetime import datetime, timedelta, timezone

from database import sales_records_collection, expense_records_collection

logger = logging.getLogger(__name__)


def _get_date_range(period: str, start_date: Optional[str], end_date: Optional[str]):
    """Calculate date range based on period or custom dates.

    Wave 13.1 — now a thin adapter over ``core.period_resolver.resolve()``.
    The legacy 30d-only vocabulary has been promoted to the full canonical
    set (7d/30d/90d/1y/ytd/mtd/qtd + aliases) through the central resolver.

    Backward-compat contract:
      * Valid pre-Wave-13 inputs (7d/30d/90d or explicit date pairs)
        produce IDENTICAL output. Existing callers, tests, and mocks
        continue to work without change.
      * NEW: calendar tokens (ytd, mtd, qtd, 1y) and case-insensitive
        aliases (``last_30_days``, ``year_to_date``, ``this_month``, …)
        now resolve correctly instead of silently falling back to 30 days.
        This is the root-cause fix for the Wave 13 audit's BUG #1
        ("Chat AI says 48/100 for YTD but actually computed 30d").
      * Invalid inputs (bad date format, swapped dates, future end_date,
        unknown tokens) emit a WARNING log and fall back to the safe
        30d default. Pre-Wave-13 the silent fallback was identical for
        bad tokens and "pass-through-then-MongoDB-crash" for bad explicit
        dates — the new behaviour is uniformly safer AND observable.

    Strict validation (unknown tokens raise instead of falling back) will
    be enabled module-wide once the ``STRICT_PERIOD_VALIDATION`` env flag
    flips in Phase 13.1.C, after prod log analysis confirms no legitimate
    caller still emits unknown tokens.

    Returns:
        tuple[str, str]: ``(start_iso, end_iso)`` in ``YYYY-MM-DD`` form.
    """
    # Lazy import — period_resolver is stdlib-only at import time so the
    # cycle risk is nil, but keeping the import inside the function keeps
    # the module-level surface unchanged for callers that patch this
    # symbol via ``unittest.mock.patch("services.ai_analytics_service._get_date_range")``.
    from core.period_resolver import (
        resolve,
        ResolutionSource,
        InvalidPeriodError,
    )

    # Anchor "today" in UTC to match pre-Wave-13 behaviour exactly. Prod
    # Docker runs in UTC; on dev machines with non-UTC TZ this keeps the
    # math identical to before instead of silently shifting by a few hours
    # around midnight.
    today_utc = datetime.now(timezone.utc).date()

    try:
        resolved = resolve(
            period=period,
            start_date=start_date,
            end_date=end_date,
            today=today_utc,
            strict=False,  # Wave 13.1.A: lenient; flipped to True in 13.1.C
        )
        if resolved.resolution_source == ResolutionSource.FALLBACK_UNKNOWN_TOKEN:
            logger.warning(
                "ai_analytics_service: unknown period token %r — falling "
                "back to %s (%s → %s). When STRICT_PERIOD_VALIDATION "
                "is enabled this will become a hard error.",
                resolved.requested_period, resolved.label,
                resolved.start_iso, resolved.end_iso,
            )
        return resolved.start_iso, resolved.end_iso
    except InvalidPeriodError as exc:
        # Pre-Wave-13 the adapter silently returned bad explicit dates
        # verbatim (then MongoDB would crash) OR fell back to 30d for
        # unknown tokens. We now unify on the safer "log + 30d fallback"
        # — no downstream crash, plus a visible warning so we can spot
        # the offender in prod logs.
        logger.warning(
            "ai_analytics_service: rejected period input "
            "(period=%r, start_date=%r, end_date=%r): %s — "
            "falling back to the safe 30d window.",
            period, start_date, end_date, exc,
        )
        return (
            (today_utc - timedelta(days=29)).isoformat(),
            today_utc.isoformat(),
        )


async def get_analytics_summary(org_id: str, start_date: str, end_date: str) -> Optional[dict]:
    """Build the metrics dict consumed by the AI insight generator."""
    sales_pipeline = [
        {"$match": {"organization_id": org_id, "date": {"$gte": start_date, "$lte": end_date}}},
        {"$group": {"_id": "$date", "total": {"$sum": "$amount"}}},
    ]
    expenses_pipeline = [
        {"$match": {"organization_id": org_id, "date": {"$gte": start_date, "$lte": end_date}}},
        {"$group": {"_id": "$date", "total": {"$sum": "$amount"}}},
    ]

    sales_by_date = {doc["_id"]: doc["total"] async for doc in sales_records_collection.aggregate(sales_pipeline)}
    expenses_by_date = {doc["_id"]: doc["total"] async for doc in expense_records_collection.aggregate(expenses_pipeline)}

    if not sales_by_date and not expenses_by_date:
        return None

    total_sales = sum(sales_by_date.values())
    total_expenses = sum(expenses_by_date.values())
    net_cashflow = total_sales - total_expenses

    days = len(set(sales_by_date.keys()) | set(expenses_by_date.keys()))
    avg_sales = total_sales / days if days > 0 else 0
    avg_expenses = total_expenses / days if days > 0 else 0

    # Previous period comparison
    start_dt = datetime.strptime(start_date, "%Y-%m-%d").date()
    end_dt = datetime.strptime(end_date, "%Y-%m-%d").date()
    period_length = (end_dt - start_dt).days + 1
    prev_end = start_dt - timedelta(days=1)
    prev_start = prev_end - timedelta(days=period_length - 1)

    prev_sales_cursor = sales_records_collection.aggregate([
        {"$match": {"organization_id": org_id, "date": {"$gte": prev_start.isoformat(), "$lte": prev_end.isoformat()}}},
        {"$group": {"_id": None, "total": {"$sum": "$amount"}}},
    ])
    prev_sales_doc = await prev_sales_cursor.to_list(1)
    prev_sales = prev_sales_doc[0]["total"] if prev_sales_doc else 0

    prev_expenses_cursor = expense_records_collection.aggregate([
        {"$match": {"organization_id": org_id, "date": {"$gte": prev_start.isoformat(), "$lte": prev_end.isoformat()}}},
        {"$group": {"_id": None, "total": {"$sum": "$amount"}}},
    ])
    prev_expenses_doc = await prev_expenses_cursor.to_list(1)
    prev_expenses = prev_expenses_doc[0]["total"] if prev_expenses_doc else 0

    # Anomaly detection
    all_dates = sorted(set(sales_by_date.keys()) | set(expenses_by_date.keys()))
    negative_days, low_sales_days, high_expense_days = [], [], []
    for date in all_dates:
        s = sales_by_date.get(date, 0)
        e = expenses_by_date.get(date, 0)
        if s - e < 0:
            negative_days.append(date)
        if avg_sales > 0 and s < avg_sales * 0.7:
            low_sales_days.append({"date": date, "amount": s})
        if avg_expenses > 0 and e > avg_expenses * 1.3:
            high_expense_days.append({"date": date, "amount": e})

    return {
        "period": {"start": start_date, "end": end_date, "days": days},
        "totals": {
            "sales": round(total_sales, 2),
            "expenses": round(total_expenses, 2),
            "net_cashflow": round(net_cashflow, 2),
        },
        "averages": {
            "daily_sales": round(avg_sales, 2),
            "daily_expenses": round(avg_expenses, 2),
        },
        "trends": {
            "sales_change_pct": round(((total_sales - prev_sales) / prev_sales * 100) if prev_sales > 0 else 0, 1),
            "expenses_change_pct": round(((total_expenses - prev_expenses) / prev_expenses * 100) if prev_expenses > 0 else 0, 1),
        },
        "concerns": {
            "negative_cashflow_days": len(negative_days),
            "low_sales_days": low_sales_days[:3],
            "high_expense_days": high_expense_days[:3],
        },
    }
