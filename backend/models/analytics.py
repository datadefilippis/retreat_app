from pydantic import BaseModel
from typing import Optional


class DailyAggregate(BaseModel):
    date: str
    total_sales: float
    total_expenses: float
    total_purchases: float = 0
    total_fixed_costs: float = 0
    net_cashflow: float


class KPIData(BaseModel):
    total_sales: float
    total_expenses: float
    total_purchases: float = 0
    total_fixed_costs: float = 0
    net_cashflow: float
    avg_daily_sales: float
    avg_daily_expenses: float
    sales_trend_pct: float  # vs previous period
    expenses_trend_pct: float
    cashflow_trend_pct: float
    period_days: int


class ChartDataPoint(BaseModel):
    date: str
    sales: float
    expenses: float
    purchases: float = 0
    fixed_costs: float = 0
    net_cashflow: float
    sales_ma7: Optional[float] = None
    expenses_ma7: Optional[float] = None
