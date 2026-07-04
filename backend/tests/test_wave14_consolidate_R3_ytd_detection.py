"""Wave 14.CONSOLIDATE R3 — YTD pattern detection in overview_builder.

Pre-Wave-14 the "previous period for trend comparison" was always
computed as "N days immediately before the requested window". For a
YTD request (Jan 1 → today, e.g. 136 days for May 16) that produces
``Aug → Dec`` of the prior year — a 5-month chunk that has no
business semantics. The chat AI nonetheless reported trend against
it, leading to nonsensical YoY-like comparisons.

The fix: detect the YTD pattern (start = Jan 1 of the requested
year) and redirect prev_period to the **same YTD window of the
prior calendar year**. That gives a meaningful YTD-vs-YTD
comparison. We also surface ``period.semantic`` so the chat AI
knows which type of comparison it's looking at.

Reproduces the user's real prod chat scenario:
  - YTD 2026 (Jan 1 → May 16) compared to YTD 2025 (Jan 1 → May 16)
"""

import os
import sys
from datetime import date
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-not-for-production")
os.environ.setdefault("MONGO_URL", "mongodb://localhost:27017")
os.environ.setdefault("DB_NAME", "test_db")

BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))


# ── YTD detection logic (pure-function test) ──────────────────────────────


class TestYtdDetectionLogic:
    """The detection happens via ``start_dt.month == 1 and
    start_dt.day == 1``. We re-implement the predicate here to lock
    its semantics and to verify edge cases."""

    @staticmethod
    def _is_ytd(start_dt: date) -> bool:
        return start_dt.month == 1 and start_dt.day == 1

    def test_jan_1_is_ytd(self):
        assert self._is_ytd(date(2026, 1, 1)) is True

    def test_jan_2_is_not_ytd(self):
        assert self._is_ytd(date(2026, 1, 2)) is False

    def test_feb_1_is_not_ytd(self):
        assert self._is_ytd(date(2026, 2, 1)) is False

    def test_dec_31_is_not_ytd(self):
        assert self._is_ytd(date(2026, 12, 31)) is False


# ── Integration with overview_builder.build_overview ──────────────────────


@pytest.fixture
def mock_overview_repos_for_ytd():
    """Patch all repositories used by build_overview so we can
    exercise the YTD logic without touching MongoDB."""
    from unittest.mock import MagicMock
    with patch("modules.cashflow_monitor.overview_builder.analytics_repository") as ar, \
         patch("modules.cashflow_monitor.overview_builder.alert_repository") as alr, \
         patch("modules.cashflow_monitor.overview_builder.insight_repository") as ir, \
         patch(
             "modules.cashflow_monitor.overview_builder.generate_health_explanation",
             new_callable=AsyncMock,
             return_value="ok",
         ):
        ar.aggregate_sales_by_date = AsyncMock(return_value={"2026-01-15": 1000.0})
        ar.aggregate_expenses_by_date = AsyncMock(return_value={})
        ar.aggregate_sales_by_category = AsyncMock(return_value=[])
        ar.aggregate_expenses_by_category = AsyncMock(return_value=[])
        ar.aggregate_fixed_costs_total = AsyncMock(return_value=0.0)
        ar.get_analytics_date_range = AsyncMock(return_value={
            "has_data": True, "min_date": "2025-01-01",
            "max_date": "2026-05-16", "days_of_data": 500,
            "suggested_period": "ytd",
        })
        ar.aggregate_purchases_by_date = AsyncMock(return_value={})
        ar.aggregate_purchases_by_supplier = AsyncMock(return_value=[])
        ar.aggregate_open_receivables = AsyncMock(return_value=0.0)
        ar.aggregate_open_payables = AsyncMock(return_value=0.0)
        ar.aggregate_receivables_by_aging = AsyncMock(return_value=[])
        ar.aggregate_payables_by_aging = AsyncMock(return_value=[])
        ar.aggregate_upcoming_receivables = AsyncMock(return_value=[])
        ar.aggregate_upcoming_payables = AsyncMock(return_value=[])
        ar.aggregate_purchases_by_product = AsyncMock(return_value=[])
        ar.aggregate_purchases_by_category_macro = AsyncMock(return_value=[])
        alr.find_by_org = AsyncMock(return_value=[])
        ir.find_latest = AsyncMock(return_value=None)
        yield {"analytics": ar, "alerts": alr, "insights": ir}


@pytest.mark.asyncio
class TestYtdPrevPeriodIsPriorYearYtd:
    async def test_ytd_request_compares_against_prior_year_ytd(
        self, mock_overview_repos_for_ytd,
    ):
        """The canonical scenario from the audit: YTD 2026 (Jan 1 →
        May 16) prev_period must be YTD 2025 (Jan 1 → May 16), NOT
        2025-09-01 → 2025-12-31 (the pre-fix nonsense window)."""
        from modules.cashflow_monitor.overview_builder import build_overview

        result = await build_overview(
            "org_test", "custom", "2026-01-01", "2026-05-16",
        )
        period = result["period"]
        # Explicit semantic flag
        assert period["semantic"] == "ytd"
        # Prev period is YTD of the prior year (NOT 5-months-before)
        prev = period["prev_period"]
        assert prev["start_date"] == "2025-01-01"
        assert prev["end_date"] == "2025-05-16"
        assert prev["semantic"] == "ytd_prior_year"

    async def test_30d_rolling_unaffected(self, mock_overview_repos_for_ytd):
        """Non-YTD windows preserve the pre-Wave-14 behaviour exactly.
        Wave 14.CONSOLIDATE R3 only changes the YTD path."""
        from modules.cashflow_monitor.overview_builder import build_overview

        # 30d window ending May 16 → starts Apr 17
        result = await build_overview(
            "org_test", "custom", "2026-04-17", "2026-05-16",
        )
        period = result["period"]
        assert period["semantic"] == "rolling"
        prev = period["prev_period"]
        # Prev = immediately preceding 30 days
        assert prev["end_date"] == "2026-04-16"
        assert prev["start_date"] == "2026-03-18"  # Apr 16 - 29 days
        assert prev["semantic"] == "rolling_prior_period"

    async def test_q1_is_rolling_not_ytd(self, mock_overview_repos_for_ytd):
        """Q1 starts Jan 1 but ends Mar 31 — should still be detected
        as YTD by start-of-year, which actually IS correct semantically
        (the comparison "Q1 2026 vs Q1 2025" IS year-over-year). This
        test pins that interpretation so future contributors don't
        accidentally narrow the detector."""
        from modules.cashflow_monitor.overview_builder import build_overview

        result = await build_overview(
            "org_test", "custom", "2026-01-01", "2026-03-31",
        )
        period = result["period"]
        # Jan 1 start → detected as YTD pattern (also correct for Q1)
        assert period["semantic"] == "ytd"
        prev = period["prev_period"]
        assert prev["start_date"] == "2025-01-01"
        assert prev["end_date"] == "2025-03-31"

    async def test_mtd_pattern_uses_rolling(self, mock_overview_repos_for_ytd):
        """MTD (May 1 → May 16) is NOT YTD: start_dt.day=1 but
        month != 1 → uses rolling logic. Documented edge case."""
        from modules.cashflow_monitor.overview_builder import build_overview

        result = await build_overview(
            "org_test", "custom", "2026-05-01", "2026-05-16",
        )
        period = result["period"]
        assert period["semantic"] == "rolling"


# ── Source-code regression sentinel ───────────────────────────────────────


class TestYtdDetectionSourceSentinel:
    def test_overview_builder_has_ytd_detector(self):
        import inspect
        from modules.cashflow_monitor import overview_builder
        src = inspect.getsource(overview_builder)
        # The detector predicate must remain
        assert "is_ytd_pattern" in src
        assert "start_dt.month == 1 and start_dt.day == 1" in src
        # Prev period for YTD must use prior-year replacement
        assert "end_dt.replace(year=end_dt.year - 1)" in src
