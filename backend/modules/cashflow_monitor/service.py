from typing import Optional, List
from models import DailyAggregate
from database import (
    sales_records_collection, expense_records_collection,
    purchase_records_collection, fixed_costs_collection
)
from datetime import datetime, timedelta, timezone
from repositories import analytics_repository


def get_date_range(period: str, start_date: Optional[str], end_date: Optional[str]):
    """Calculate date range based on period or custom dates"""
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


async def get_aggregated_data(org_id: str, start_date: str, end_date: str) -> List[DailyAggregate]:
    """Get daily aggregated sales and expenses.

    Uses analytics_repository instead of direct collection access so that the
    cashflow module does not import from database.py directly.
    """
    sales_by_date = await analytics_repository.aggregate_sales_by_date(
        org_id, start_date, end_date
    )
    expenses_by_date = await analytics_repository.aggregate_expenses_by_date(
        org_id, start_date, end_date
    )

    all_dates = sorted(set(sales_by_date.keys()) | set(expenses_by_date.keys()))

    result = []
    for date_str in all_dates:
        sales = sales_by_date.get(date_str, 0)
        expenses = expenses_by_date.get(date_str, 0)
        result.append(DailyAggregate(
            date=date_str,
            total_sales=sales,
            total_expenses=expenses,
            net_cashflow=sales - expenses,
        ))

    return result


def calculate_moving_average(data: List[DailyAggregate], field: str, window: int) -> dict:
    """Calculate moving average for a field"""
    ma_dict = {}
    values = [(d.date, getattr(d, field)) for d in data]

    for i, (date, _) in enumerate(values):
        start_idx = max(0, i - window + 1)
        window_values = [v[1] for v in values[start_idx:i + 1]]
        ma_dict[date] = sum(window_values) / len(window_values) if window_values else 0

    return ma_dict
