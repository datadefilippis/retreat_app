"""
Insight Service — Phase 2.

Changes (all backward-compatible):
  - Uses ai_insight_service directly (via ai_service facade).
  - schema_version and model_version forwarded from the AI service to the
    persisted Insight document.
"""
from typing import Optional

from models import Insight
from repositories import insight_repository, analytics_repository
from services.ai_service import generate_cashflow_insight
from datetime import datetime, timedelta, timezone


def get_date_range(period: str, start_date: Optional[str], end_date: Optional[str]):
    """Calculate date range based on period or custom dates."""
    today = datetime.now(timezone.utc).date()

    if period == "custom" and start_date and end_date:
        return start_date, end_date

    if period == "data_range" and start_date and end_date:
        return start_date, end_date

    period_days = {"7d": 7, "30d": 30, "90d": 90}
    days = period_days.get(period, 30)
    end = today
    start = today - timedelta(days=days - 1)
    return start.isoformat(), end.isoformat()


async def generate_and_save_insight(
    org_id: str,
    period: str = "30d",
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
) -> dict:
    """Generate AI insight and save to database."""
    start_str, end_str = get_date_range(period, start_date, end_date)

    # Get aggregated data for empty-check
    sales_by_date = await analytics_repository.aggregate_sales_by_date(org_id, start_str, end_str)
    expenses_by_date = await analytics_repository.aggregate_expenses_by_date(org_id, start_str, end_str)

    if not sales_by_date and not expenses_by_date:
        return {"message": "No data available to generate insights"}

    # Generate insight via AI service (Phase 2: returns Insight object with schema_version + model_version)
    insight = await generate_cashflow_insight(
        org_id=org_id,
        period=period,
        start_date=start_date,
        end_date=end_date,
    )

    if not insight:
        return {"message": "Could not generate insight"}

    saved_insight = await insight_repository.create(insight)

    return {
        "id": saved_insight["id"],
        "content": insight.content,
        "period": {"start": start_str, "end": end_str},
    }
