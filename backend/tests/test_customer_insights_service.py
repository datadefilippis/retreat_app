"""Tests for ``modules.customer_insights.service`` — orchestrator.

Mock the repository and legacy collection reads so the test runs in
milliseconds without a database. Pin the response shape that the
Phase 2 frontend will consume.
"""

import os
import sys
from datetime import date
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-not-for-production")
os.environ.setdefault("MONGO_URL", "mongodb://localhost:27017")
os.environ.setdefault("DB_NAME", "test_db")

from modules.customer_insights import service


# ── Fixtures ──────────────────────────────────────────────────────────────


def _aggregate(customer_id, revenue, count=1):
    return {
        "_id": customer_id,
        "total_revenue": revenue,
        "count": count,
        "first_date": "2026-04-15",
        "last_date": "2026-05-01",
    }


def _metric(cid, **overrides):
    base = {
        "customer_id": cid,
        "customer_name": f"Customer {cid}",
        "total_revenue": 100.0,
        "transaction_count": 5,
        "segment": "active",
        "customer_status": "healthy",
        "churn_risk_score": 10,
        "trend_direction": "stable",
        "last_purchase_date": "2026-05-01",
        "days_since_last_purchase": 9,
    }
    base.update(overrides)
    return base


# ── build_overview ────────────────────────────────────────────────────────


class TestBuildOverview:
    """Pin the response shape and KPI delta math."""

    @pytest.mark.asyncio
    async def test_response_shape_is_complete(self):
        with patch(
            "modules.customer_insights.repository.aggregate_revenue_in_period",
            new_callable=AsyncMock, return_value=[_aggregate("c1", 100.0)],
        ), patch(
            "modules.customer_insights.repository.count_new_customers_in_period",
            new_callable=AsyncMock, return_value=2,
        ), patch(
            "modules.customer_insights.repository.count_active_customers_at",
            new_callable=AsyncMock, return_value=10,
        ), patch(
            "modules.customer_insights.repository.find_metrics_by_org",
            new_callable=AsyncMock, return_value=[_metric("c1")],
        ):
            result = await service.build_overview(
                "org_test", period="30d", today_override=date(2026, 5, 10),
            )

        # Every Phase 2 key the UI consumes must be present.
        for key in ("period", "compare", "kpis", "segments",
                    "concentration", "suggested_actions"):
            assert key in result

        # Window labels carry the right metadata for Phase 2 i18n.
        assert result["period"]["label"] == "30d"
        assert result["compare"]["label"] == "previous-30d"
        assert result["period"]["days"] == result["compare"]["days"]

    @pytest.mark.asyncio
    async def test_kpi_delta_basic_growth(self):
        # Current period sees more revenue than previous → positive delta.
        # First call (current) = 200, second (previous) = 100 → +100 %.
        agg_mock = AsyncMock(side_effect=[
            [_aggregate("c1", 200.0)],  # current
            [_aggregate("c1", 100.0)],  # previous
        ])
        with patch(
            "modules.customer_insights.repository.aggregate_revenue_in_period",
            new=agg_mock,
        ), patch(
            "modules.customer_insights.repository.count_new_customers_in_period",
            new_callable=AsyncMock, return_value=0,
        ), patch(
            "modules.customer_insights.repository.count_active_customers_at",
            new_callable=AsyncMock, return_value=5,
        ), patch(
            "modules.customer_insights.repository.find_metrics_by_org",
            new_callable=AsyncMock, return_value=[],
        ):
            result = await service.build_overview(
                "org_test", today_override=date(2026, 5, 10),
            )

        revenue = result["kpis"]["total_revenue"]
        assert revenue["value"] == 200.0
        assert revenue["previous"] == 100.0
        assert revenue["delta_pct"] == 100.0

    @pytest.mark.asyncio
    async def test_kpi_delta_none_when_previous_zero(self):
        agg_mock = AsyncMock(side_effect=[
            [_aggregate("c1", 50.0)],
            [],  # previous: empty
        ])
        with patch(
            "modules.customer_insights.repository.aggregate_revenue_in_period",
            new=agg_mock,
        ), patch(
            "modules.customer_insights.repository.count_new_customers_in_period",
            new_callable=AsyncMock, return_value=0,
        ), patch(
            "modules.customer_insights.repository.count_active_customers_at",
            new_callable=AsyncMock, return_value=0,
        ), patch(
            "modules.customer_insights.repository.find_metrics_by_org",
            new_callable=AsyncMock, return_value=[],
        ):
            result = await service.build_overview("org_test")

        # Previous == 0 → delta_pct must be None (not +∞).
        assert result["kpis"]["total_revenue"]["delta_pct"] is None

    @pytest.mark.asyncio
    async def test_segments_breakdown(self):
        metrics = [
            _metric("c1", segment="top", total_revenue=500),
            _metric("c2", segment="active", total_revenue=200),
            _metric("c3", segment="active", total_revenue=300),
            _metric("c4", segment="inactive", total_revenue=0),
        ]
        with patch(
            "modules.customer_insights.repository.aggregate_revenue_in_period",
            new_callable=AsyncMock, return_value=[],
        ), patch(
            "modules.customer_insights.repository.count_new_customers_in_period",
            new_callable=AsyncMock, return_value=0,
        ), patch(
            "modules.customer_insights.repository.count_active_customers_at",
            new_callable=AsyncMock, return_value=0,
        ), patch(
            "modules.customer_insights.repository.find_metrics_by_org",
            new_callable=AsyncMock, return_value=metrics,
        ):
            result = await service.build_overview("org_test")

        segs = {s["segment"]: s for s in result["segments"]}
        assert set(segs.keys()) == {"top", "active", "inactive"}
        assert segs["active"]["count"] == 2
        assert segs["active"]["revenue"] == 500.0
        assert segs["top"]["pct_of_revenue"] == 50.0  # 500 / 1000

    @pytest.mark.asyncio
    async def test_suggested_actions_at_risk(self):
        metrics = [
            _metric("c1", customer_status="at_risk"),
            _metric("c2", customer_status="at_risk"),
            _metric("c3", customer_status="at_risk"),
        ]
        with patch(
            "modules.customer_insights.repository.aggregate_revenue_in_period",
            new_callable=AsyncMock, return_value=[],
        ), patch(
            "modules.customer_insights.repository.count_new_customers_in_period",
            new_callable=AsyncMock, return_value=0,
        ), patch(
            "modules.customer_insights.repository.count_active_customers_at",
            new_callable=AsyncMock, return_value=0,
        ), patch(
            "modules.customer_insights.repository.find_metrics_by_org",
            new_callable=AsyncMock, return_value=metrics,
        ):
            result = await service.build_overview("org_test")

        triggers = [s["trigger"] for s in result["suggested_actions"]]
        assert "at_risk_followup" in triggers
        risk_block = next(
            s for s in result["suggested_actions"] if s["trigger"] == "at_risk_followup"
        )
        assert risk_block["count"] == 3
        assert len(risk_block["preview_customer_ids"]) == 3

    @pytest.mark.asyncio
    async def test_resilient_to_aggregation_failure(self):
        # Mongo error in the period aggregation must NOT 500 the
        # overview — degrade to zero counts.
        with patch(
            "modules.customer_insights.repository.aggregate_revenue_in_period",
            new_callable=AsyncMock, side_effect=RuntimeError("mongo down"),
        ), patch(
            "modules.customer_insights.repository.count_new_customers_in_period",
            new_callable=AsyncMock, return_value=0,
        ), patch(
            "modules.customer_insights.repository.count_active_customers_at",
            new_callable=AsyncMock, return_value=0,
        ), patch(
            "modules.customer_insights.repository.find_metrics_by_org",
            new_callable=AsyncMock, return_value=[],
        ):
            result = await service.build_overview("org_test")

        # Returns the empty skeleton, not an exception.
        assert result["kpis"]["total_revenue"]["value"] == 0
        assert result["kpis"]["total_revenue"]["previous"] == 0


# ── build_customer_list ───────────────────────────────────────────────────


class TestBuildCustomerList:
    """Pagination + filter chain semantics."""

    @pytest.mark.asyncio
    async def test_pagination_basic(self):
        metrics = [_metric(f"c{i}") for i in range(120)]
        with patch(
            "modules.customer_insights.repository.find_metrics_by_org",
            new_callable=AsyncMock, return_value=metrics,
        ), patch(
            "repositories.customer_repository.find_by_org",
            new_callable=AsyncMock, return_value=[],
        ):
            result = await service.build_customer_list(
                "org_test", page=2, page_size=50,
            )

        assert result["total"] == 120
        assert result["page"] == 2
        assert len(result["rows"]) == 50

    @pytest.mark.asyncio
    async def test_min_revenue_filter(self):
        metrics = [
            _metric("c1", total_revenue=50.0),
            _metric("c2", total_revenue=150.0),
            _metric("c3", total_revenue=300.0),
        ]
        with patch(
            "modules.customer_insights.repository.find_metrics_by_org",
            new_callable=AsyncMock, return_value=metrics,
        ), patch(
            "repositories.customer_repository.find_by_org",
            new_callable=AsyncMock, return_value=[],
        ):
            result = await service.build_customer_list(
                "org_test", min_revenue=100.0,
            )

        assert result["total"] == 2
        assert all(r["total_revenue"] >= 100.0 for r in result["rows"])

    @pytest.mark.asyncio
    async def test_status_filter(self):
        metrics = [
            _metric("c1", customer_status="healthy"),
            _metric("c2", customer_status="at_risk"),
            _metric("c3", customer_status="at_risk"),
        ]
        with patch(
            "modules.customer_insights.repository.find_metrics_by_org",
            new_callable=AsyncMock, return_value=metrics,
        ), patch(
            "repositories.customer_repository.find_by_org",
            new_callable=AsyncMock, return_value=[],
        ):
            result = await service.build_customer_list(
                "org_test", status="at_risk",
            )

        assert result["total"] == 2
        for r in result["rows"]:
            assert r["customer_status"] == "at_risk"

    @pytest.mark.asyncio
    async def test_search_substring(self):
        metrics = [
            _metric("c1", customer_name="Mario Rossi"),
            _metric("c2", customer_name="Luigi Verdi"),
            _metric("c3", customer_name="Mario Bianchi"),
        ]
        with patch(
            "modules.customer_insights.repository.find_metrics_by_org",
            new_callable=AsyncMock, return_value=metrics,
        ), patch(
            "repositories.customer_repository.find_by_org",
            new_callable=AsyncMock, return_value=[],
        ):
            result = await service.build_customer_list(
                "org_test", search="mario",
            )

        assert result["total"] == 2
        names = sorted(r["customer_name"] for r in result["rows"])
        assert names == ["Mario Bianchi", "Mario Rossi"]

    @pytest.mark.asyncio
    async def test_has_email_filter(self):
        metrics = [_metric("c1"), _metric("c2"), _metric("c3")]

        # Hydrate contact: c1 has email, c2 phone, c3 nothing.
        contact_c1 = MagicMock(id="c1", email="m@e.com", phone=None)
        contact_c2 = MagicMock(id="c2", email=None, phone="+41 79 ...")
        contact_c3 = MagicMock(id="c3", email=None, phone=None)

        with patch(
            "modules.customer_insights.repository.find_metrics_by_org",
            new_callable=AsyncMock, return_value=metrics,
        ), patch(
            "repositories.customer_repository.find_by_org",
            new_callable=AsyncMock,
            return_value=[contact_c1, contact_c2, contact_c3],
        ):
            res_yes = await service.build_customer_list(
                "org_test", has_email=True,
            )
            res_no = await service.build_customer_list(
                "org_test", has_email=False,
            )

        assert res_yes["total"] == 1
        assert res_yes["rows"][0]["email"] == "m@e.com"
        assert res_no["total"] == 2


# ── build_cohort_response ─────────────────────────────────────────────────


class TestBuildCohortResponse:
    @pytest.mark.asyncio
    async def test_serialises_rows_to_dicts(self):
        purchases = {
            "c1": [date(2026, 1, 5), date(2026, 2, 10)],
            "c2": [date(2026, 1, 20)],
        }
        with patch(
            "modules.customer_insights.repository.fetch_purchase_dates_per_customer",
            new_callable=AsyncMock, return_value=purchases,
        ):
            result = await service.build_cohort_response(
                "org_test", bucket="month", horizon=3,
            )

        assert result["bucket"] == "month"
        assert result["horizon"] == 3
        assert len(result["rows"]) == 1  # both customers in Jan
        row = result["rows"][0]
        assert row["acquisition_bucket"] == "2026-01"
        assert row["size"] == 2
        assert row["retention"] == [2, 1, 0]
        # retention_pct serialised as numeric list (or None for size=0)
        assert row["retention_pct"][0] == 100.0
        assert row["retention_pct"][1] == 50.0


# ── log_outreach_action ───────────────────────────────────────────────────


class TestLogOutreachAction:
    @pytest.mark.asyncio
    async def test_writes_audit_log(self):
        fake_repo = MagicMock()
        fake_repo.create = AsyncMock()
        with patch("repositories.audit_repository", fake_repo):
            await service.log_outreach_action(
                "org_test", "user_1", "cust_42",
                channel="email", template="at_risk_followup",
            )

        fake_repo.create.assert_called_once()
        log = fake_repo.create.call_args[0][0]
        assert log.action == "customer.outreach.sent"
        assert log.resource_id == "cust_42"
        assert log.details["channel"] == "email"

    @pytest.mark.asyncio
    async def test_audit_failure_does_not_raise(self):
        # Audit log failure is logged but never propagates — outreach
        # UX must keep working even if the audit collection is unhealthy.
        fake_repo = MagicMock()
        fake_repo.create = AsyncMock(side_effect=RuntimeError("audit down"))
        with patch("repositories.audit_repository", fake_repo):
            # Must NOT raise.
            await service.log_outreach_action(
                "org_test", "user_1", "cust_42",
                channel="email", template="x",
            )
