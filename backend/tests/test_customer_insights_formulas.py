"""Unit tests for the pure formula layer of Customer Insights.

Every formula in ``modules.customer_insights.formulas`` is exercised
here at least three ways:

  1. Happy path with the canonical example.
  2. Boundary cases (empty input, zero division, single record).
  3. The specific "Before/After" scenarios that motivated the five
     corrections in Phase 0 — see docstrings for each test class.

These tests run in milliseconds (no DB, no I/O) and are the *first
gate* of the customer insights work: until they're green, nothing
else moves.
"""

import os
import sys
from datetime import date
from pathlib import Path

import pytest

BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-not-for-production")
os.environ.setdefault("MONGO_URL", "mongodb://localhost:27017")
os.environ.setdefault("DB_NAME", "test_db")

from modules.customer_insights import formulas as F


# ════════════════════════════════════════════════════════════════════════════
# 1. Date helpers — unit tests
# ════════════════════════════════════════════════════════════════════════════


class TestDateHelpers:
    """``_parse_iso_date`` and ``days_since`` are foundation utilities;
    every downstream formula relies on them. Edge cases here prevent
    silent NaN propagation."""

    def test_parse_valid_iso_date(self):
        assert F._parse_iso_date("2026-01-15") == date(2026, 1, 15)

    def test_parse_none_returns_none(self):
        assert F._parse_iso_date(None) is None

    def test_parse_empty_string_returns_none(self):
        assert F._parse_iso_date("") is None

    def test_parse_invalid_format_returns_none(self):
        # Catches the three common malformed strings we've seen in prod
        # imports: European date, US date, plain garbage.
        assert F._parse_iso_date("15/01/2026") is None
        assert F._parse_iso_date("2026/01/15") is None
        assert F._parse_iso_date("not-a-date") is None

    def test_days_since_basic(self):
        assert F.days_since(date(2026, 1, 31), "2026-01-01") == 30

    def test_days_since_today(self):
        today = date(2026, 1, 31)
        assert F.days_since(today, "2026-01-31") == 0

    def test_days_since_missing_returns_zero(self):
        # Legacy contract: returns 0 (not None) so downstream segment
        # classification treats "no last date" as "active today" rather
        # than crashing. The UI uses transaction_count == 0 to detect
        # the "never purchased" case separately.
        assert F.days_since(date(2026, 1, 31), None) == 0
        assert F.days_since(date(2026, 1, 31), "garbage") == 0

    def test_months_active_floor_one_month(self):
        # Same-day first/last → 1.0 month minimum. Prevents division
        # by zero in frequency math when a customer made all their
        # purchases on the same day.
        assert F.months_active_between("2026-01-15", "2026-01-15") == 1.0

    def test_months_active_basic(self):
        assert F.months_active_between("2026-01-01", "2026-04-01") == 3.0

    def test_months_active_missing_data_floor(self):
        assert F.months_active_between(None, "2026-04-01") == 1.0
        assert F.months_active_between("2026-04-01", None) == 1.0


# ════════════════════════════════════════════════════════════════════════════
# 2. Per-customer derived metrics
# ════════════════════════════════════════════════════════════════════════════


class TestAvgTransactionValue:
    def test_basic(self):
        assert F.avg_transaction_value(1000.0, 4) == 250.0

    def test_zero_count_returns_zero(self):
        # Legacy contract.
        assert F.avg_transaction_value(0.0, 0) == 0.0

    def test_negative_count_safe(self):
        # Defensive: negative count should never happen but we don't
        # want to propagate a negative number.
        assert F.avg_transaction_value(100.0, -1) == 0.0


class TestPurchaseFrequencyMonthly:
    """Correction #2 — only return a value when history is meaningful.

    Before Phase 0, a customer with 1 purchase 5 days ago returned
    ``1.0/month`` (because months_active was floored at 1.0, yielding
    1/1 = 1.0). That's misleading: we have no signal. After the fix,
    short-history customers return None and the UI shows "Storia
    troppo breve".
    """

    def test_too_few_purchases_returns_none(self):
        # 1 or 2 purchases is always "too short to assess".
        assert F.purchase_frequency_monthly(1, "2026-01-01", "2026-01-05") is None
        assert F.purchase_frequency_monthly(2, "2026-01-01", "2026-01-05") is None

    def test_zero_purchases_returns_none(self):
        # Edge case: empty customer.
        assert F.purchase_frequency_monthly(0, None, None) is None

    def test_three_purchases_baseline(self):
        # 3 purchases over 90 days → 1.0/month.
        assert F.purchase_frequency_monthly(3, "2026-01-01", "2026-04-01") == 1.0

    def test_high_frequency_customer(self):
        # 12 purchases over 90 days → 4/month.
        assert F.purchase_frequency_monthly(12, "2026-01-01", "2026-04-01") == 4.0

    def test_same_day_purchases(self):
        # 5 purchases all on the same day → floor 1.0 month → 5/1 = 5.
        # This is a corner case but the floor preserves legacy behaviour.
        assert F.purchase_frequency_monthly(5, "2026-01-01", "2026-01-01") == 5.0


class TestRevenueShare:
    def test_basic(self):
        assert F.revenue_share_pct(150.0, 1000.0) == 15.0

    def test_zero_org_revenue(self):
        # Critical: division-by-zero must return 0, not crash.
        assert F.revenue_share_pct(150.0, 0.0) == 0.0

    def test_zero_customer_revenue(self):
        assert F.revenue_share_pct(0.0, 1000.0) == 0.0


class TestRevenueRankPct:
    def test_top_customer_returns_zero(self):
        assert F.revenue_rank_pct(0, 100) == 0.0

    def test_bottom_customer(self):
        assert F.revenue_rank_pct(99, 100) == 0.99

    def test_single_customer_returns_zero(self):
        # Solo customer is trivially in top percentile.
        assert F.revenue_rank_pct(0, 1) == 0.0


class TestProjectedAnnualRevenue:
    """Correction #1 — was named ``lifetime_value``. Renamed to honest
    label and explicitly returns None when frequency is None
    (cascading from history-too-short case)."""

    def test_basic_projection(self):
        # 50 € avg × 2/month × 12 = 1200.
        assert F.projected_annual_revenue(50.0, 2.0) == 1200.0

    def test_none_frequency_cascades(self):
        # Insufficient history → no projection.
        assert F.projected_annual_revenue(50.0, None) is None

    def test_zero_avg_returns_zero(self):
        # Free customer with frequency → projection is 0.
        assert F.projected_annual_revenue(0.0, 1.0) == 0.0


# ════════════════════════════════════════════════════════════════════════════
# 3. Churn risk — score and breakdown
# ════════════════════════════════════════════════════════════════════════════


class TestChurnRiskBreakdown:
    """Correction #3 — same score, but with transparent component
    decomposition for the info-box."""

    def test_power_user_score_zero(self):
        # Recent (≤ 30 d), frequent (≥ 2/month), repeat → score 0.
        br = F.compute_churn_risk_breakdown(10, 5.0, 10)
        assert br.score == 0
        assert br.recency == 0
        assert br.frequency == 0
        assert br.single_penalty == 0

    def test_lost_customer_score_caps_at_100(self):
        # Old (> 180 d), infrequent (< 0.5/month), single purchase, lots
        # of cancellations → all components fire, capped at 100.
        br = F.compute_churn_risk_breakdown(
            days_since_last=200,
            frequency_monthly=0.1,
            transaction_count=1,
            cancellation_rate_pct=50.0,
        )
        assert br.score == 100  # capped
        # Sum of raw components would be 50 + 30 + 20 + 20 = 120.
        assert br.recency == 50
        assert br.frequency == 30
        assert br.single_penalty == 20
        assert br.cancel_penalty == 20

    def test_recency_linear_in_band(self):
        # 60 d should yield (60-30)/150 * 50 = 10.
        br = F.compute_churn_risk_breakdown(60, 1.0, 5)
        assert br.recency == 10

    def test_recency_below_band_zero(self):
        br = F.compute_churn_risk_breakdown(30, 1.0, 5)
        assert br.recency == 0

    def test_recency_above_band_capped_at_50(self):
        br = F.compute_churn_risk_breakdown(365, 1.0, 5)
        assert br.recency == 50

    def test_none_frequency_treated_as_worst_case(self):
        # New correction: history-too-short customers default to
        # frequency=30 (worst). Better to flag for follow-up than
        # silently treat as "frequent".
        br = F.compute_churn_risk_breakdown(10, None, 1)
        assert br.frequency == 30

    def test_single_purchase_penalty(self):
        br = F.compute_churn_risk_breakdown(10, None, 1)
        assert br.single_penalty == 20

    def test_no_single_penalty_for_repeat(self):
        br = F.compute_churn_risk_breakdown(10, 1.0, 5)
        assert br.single_penalty == 0

    def test_cancel_penalty_high_rate(self):
        br = F.compute_churn_risk_breakdown(10, 1.0, 5, cancellation_rate_pct=35.0)
        assert br.cancel_penalty == 20

    def test_cancel_penalty_many_orders(self):
        br = F.compute_churn_risk_breakdown(
            10, 1.0, 5, cancellation_rate_pct=10.0, orders_cancelled=4
        )
        assert br.cancel_penalty == 10

    def test_no_cancel_penalty(self):
        br = F.compute_churn_risk_breakdown(10, 1.0, 5)
        assert br.cancel_penalty == 0


class TestChurnRiskScoreLegacyWrapper:
    """The thin wrapper preserves legacy ``modules.customers_light``
    behaviour bit-for-bit so the materialized ``customer_metrics``
    collection doesn't shift unexpectedly."""

    def test_matches_breakdown_score(self):
        score = F.churn_risk_score(60, 1.0, 5)
        breakdown = F.compute_churn_risk_breakdown(60, 1.0, 5)
        assert score == breakdown.score


# ════════════════════════════════════════════════════════════════════════════
# 4. Segment classification — with configurable thresholds (Correction #4)
# ════════════════════════════════════════════════════════════════════════════


class TestClassifySegment:
    TODAY = date(2026, 6, 1)

    def test_new_priority_over_top(self):
        # Even a top-revenue customer who first bought 30 days ago is "new".
        seg = F.classify_segment(2, "2026-05-02", 0.05, today=self.TODAY)
        assert seg == "new"

    def test_top_when_not_new(self):
        seg = F.classify_segment(45, "2024-01-01", 0.05, today=self.TODAY)
        assert seg == "top"

    def test_active_when_not_top_not_new(self):
        seg = F.classify_segment(45, "2024-01-01", 0.5, today=self.TODAY)
        assert seg == "active"

    def test_occasional_61_to_180_days(self):
        seg = F.classify_segment(120, "2024-01-01", 0.5, today=self.TODAY)
        assert seg == "occasional"

    def test_inactive_over_180_days(self):
        seg = F.classify_segment(300, "2024-01-01", 0.5, today=self.TODAY)
        assert seg == "inactive"

    def test_no_first_date_skips_new_check(self):
        # If first_date is missing, "new" detection is impossible —
        # fall through to top/active/etc.
        seg = F.classify_segment(45, None, 0.5, today=self.TODAY)
        assert seg == "active"

    def test_invalid_first_date_skips_new_check(self):
        seg = F.classify_segment(45, "garbage", 0.5, today=self.TODAY)
        assert seg == "active"

    def test_yoga_studio_thresholds(self):
        # Yoga studio: weekly cadence. A customer who hasn't booked in
        # 2 weeks should already be "occasional" (with the merchant's
        # own thresholds), not "active".
        tight = F.LifecycleThresholds(
            new_days=14, active_days=7, occasional_days=30, top_pct=0.10
        )
        seg = F.classify_segment(
            10, "2024-01-01", 0.5, today=self.TODAY, thresholds=tight
        )
        assert seg == "occasional"

    def test_wedding_photographer_thresholds(self):
        # Wedding photographer: annual cadence. Customer 200 days out
        # is still "active" by the merchant's own cycle.
        wide = F.LifecycleThresholds(
            new_days=180, active_days=400, occasional_days=900, top_pct=0.10
        )
        seg = F.classify_segment(
            200, "2024-01-01", 0.5, today=self.TODAY, thresholds=wide
        )
        assert seg == "active"

    def test_top_pct_boundary(self):
        # rank_pct == top_pct → still "top" (≤ comparison).
        seg = F.classify_segment(45, "2024-01-01", 0.10, today=self.TODAY)
        assert seg == "top"


# ════════════════════════════════════════════════════════════════════════════
# 5. Trend classification — configurable threshold (Correction #5)
# ════════════════════════════════════════════════════════════════════════════


class TestClassifyTrend:
    def test_growing_at_default_threshold(self):
        # +20 % exactly → triggers growing (≥ comparison).
        assert F.classify_trend(120, 100, "active") == "growing"

    def test_declining_at_default_threshold(self):
        # -20 % exactly → triggers declining (≤ comparison).
        assert F.classify_trend(80, 100, "active") == "declining"

    def test_stable_within_band(self):
        assert F.classify_trend(105, 100, "active") == "stable"
        assert F.classify_trend(95, 100, "active") == "stable"

    def test_new_customer_always_new(self):
        # Segment "new" wins regardless of revenue.
        assert F.classify_trend(100, 100, "new") == "new"

    def test_no_previous_revenue_with_new_recent(self):
        assert F.classify_trend(100, 0, "active") == "new"

    def test_no_previous_revenue_no_recent(self):
        assert F.classify_trend(0, 0, "active") == "stable"

    def test_negative_previous_treated_as_zero(self):
        # Defensive — refunds could push previous_revenue negative.
        assert F.classify_trend(50, -10, "active") == "new"

    def test_sensitive_thresholds_for_coach(self):
        # Coach with 1-2 sessions/month: 10 % shifts matter.
        sensitive = F.TrendThresholds(growth_factor=1.10, decline_factor=0.90)
        assert F.classify_trend(112, 100, "active", thresholds=sensitive) == "growing"
        # Same data with default thresholds would be "stable".
        assert F.classify_trend(112, 100, "active") == "stable"


# ════════════════════════════════════════════════════════════════════════════
# 6. Status classification — operational signal
# ════════════════════════════════════════════════════════════════════════════


class TestClassifyStatus:
    def test_inactive_segment_always_lost(self):
        assert F.classify_status("inactive", 0, "stable") == "lost"
        # Even with growing trend on inactive segment → still lost.
        assert F.classify_status("inactive", 100, "growing") == "lost"

    def test_high_churn_at_risk(self):
        assert F.classify_status("active", 75, "growing") == "at_risk"

    def test_churn_60_boundary(self):
        # ≥ 60 triggers at_risk.
        assert F.classify_status("active", 60, "stable") == "at_risk"
        assert F.classify_status("active", 59, "stable") == "healthy"

    def test_occasional_is_watch(self):
        assert F.classify_status("occasional", 30, "stable") == "watch"

    def test_declining_is_watch(self):
        assert F.classify_status("active", 30, "declining") == "watch"

    def test_default_healthy(self):
        assert F.classify_status("active", 10, "growing") == "healthy"


# ════════════════════════════════════════════════════════════════════════════
# 7. Concentration metrics — org-level
# ════════════════════════════════════════════════════════════════════════════


class TestTopNShare:
    def test_basic(self):
        # Top 2 of [100, 50, 30, 20] = 150 / 200 = 75.0.
        assert F.top_n_share_pct([100, 50, 30, 20], 2) == 75.0

    def test_top_n_exceeds_pool(self):
        # When N > pool size, return 100 % (everyone is in top N).
        assert F.top_n_share_pct([100, 50, 30, 20], 10) == 100.0

    def test_empty_pool(self):
        assert F.top_n_share_pct([], 5) == 0.0

    def test_zero_revenue_pool(self):
        # All-zero customers shouldn't crash with NaN.
        assert F.top_n_share_pct([0, 0, 0], 2) == 0.0

    def test_unsorted_input_handled(self):
        # Caller must not have to pre-sort.
        assert F.top_n_share_pct([20, 100, 30, 50], 2) == 75.0


class TestAvgCustomerValue:
    def test_basic(self):
        assert F.avg_customer_value(1000.0, 4) == 250.0

    def test_zero_customers(self):
        # Critical: never crash on division by zero.
        assert F.avg_customer_value(1000.0, 0) == 0.0


class TestInactiveRate:
    def test_basic(self):
        assert F.inactive_rate_pct(15, 100) == 15.0

    def test_zero_total(self):
        assert F.inactive_rate_pct(5, 0) == 0.0


# ════════════════════════════════════════════════════════════════════════════
# 8. Payment reliability + order metrics
# ════════════════════════════════════════════════════════════════════════════


class TestPaymentReliability:
    def test_basic(self):
        assert F.payment_reliability_pct(8, 10) == 80.0

    def test_zero_invoices_returns_none(self):
        # None ≠ 0 — distinguishes "no data" from "always late".
        # The UI renders the two states differently.
        assert F.payment_reliability_pct(0, 0) is None

    def test_zero_paid(self):
        assert F.payment_reliability_pct(0, 5) == 0.0


class TestCancellationRate:
    def test_basic(self):
        assert F.cancellation_rate_pct(2, 10) == 20.0

    def test_zero_orders(self):
        assert F.cancellation_rate_pct(0, 0) == 0.0


class TestFulfillmentSuccess:
    def test_basic(self):
        assert F.fulfillment_success_rate(7, 10) == 70.0

    def test_zero_returns_none(self):
        assert F.fulfillment_success_rate(0, 0) is None

    def test_perfect_score(self):
        assert F.fulfillment_success_rate(10, 10) == 100.0


class TestAvgOrderValue:
    def test_basic(self):
        assert F.avg_order_value(450.0, 3) == 150.0

    def test_zero_orders(self):
        assert F.avg_order_value(0.0, 0) == 0.0


# ════════════════════════════════════════════════════════════════════════════
# 9. Period delta — for MoM/YoY in Phase 1
# ════════════════════════════════════════════════════════════════════════════


class TestPercentageDelta:
    def test_growth(self):
        assert F.percentage_delta(120, 100) == 20.0

    def test_decline(self):
        assert F.percentage_delta(80, 100) == -20.0

    def test_no_change(self):
        assert F.percentage_delta(100, 100) == 0.0

    def test_zero_previous_returns_none(self):
        # None preserves "no comparison possible" — better than +∞.
        assert F.percentage_delta(50, 0) is None

    def test_zero_current_with_nonzero_previous(self):
        assert F.percentage_delta(0, 100) == -100.0


# ════════════════════════════════════════════════════════════════════════════
# 10. Cross-cutting integration: composite scenarios
# ════════════════════════════════════════════════════════════════════════════


class TestCompositeScenarios:
    """End-to-end scenarios that combine several formulas, mirroring
    what ``customer_insights.service`` will assemble in Phase 1."""

    def test_brand_new_customer_one_purchase_yesterday(self):
        # A customer bought once yesterday — the page should show:
        #   segment = "new"  (first ≤ 90 d)
        #   frequency = None (history too short)
        #   projected_annual_revenue = None (cascades from None freq)
        #   churn_risk = high (single-purchase + None freq → 30 + 20 = 50)
        today = date(2026, 6, 1)
        first_date_iso = "2026-05-31"
        last_date_iso = "2026-05-31"
        days = F.days_since(today, last_date_iso)
        freq = F.purchase_frequency_monthly(1, first_date_iso, last_date_iso)
        avg = F.avg_transaction_value(50.0, 1)
        ltv = F.projected_annual_revenue(avg, freq)
        seg = F.classify_segment(days, first_date_iso, 0.5, today=today)
        risk = F.churn_risk_score(days, freq, 1)

        assert seg == "new"
        assert freq is None
        assert ltv is None  # cascades from None freq
        assert risk == 50   # 0 recency + 30 freq + 20 single

    def test_loyal_repeat_customer(self):
        # 10 purchases over 6 months, last one 5 days ago.
        today = date(2026, 6, 1)
        first_date_iso = "2025-12-01"
        last_date_iso = "2026-05-27"
        days = F.days_since(today, last_date_iso)
        freq = F.purchase_frequency_monthly(10, first_date_iso, last_date_iso)
        avg = F.avg_transaction_value(2000.0, 10)
        ltv = F.projected_annual_revenue(avg, freq)
        seg = F.classify_segment(days, first_date_iso, 0.05, today=today)
        risk = F.churn_risk_score(days, freq, 10)

        assert freq is not None
        assert freq > 1.0  # ~10/6 ≈ 1.67/month
        assert ltv is not None
        assert ltv > 0
        # Customer's first purchase was 6 months ago, so segment
        # falls through "new" to "top" (rank 5 %).
        assert seg == "top"
        # Recent + frequent + repeat → low risk.
        assert risk <= 20

    def test_dormant_customer(self):
        today = date(2026, 6, 1)
        first_date_iso = "2024-01-01"
        last_date_iso = "2025-10-01"  # 243 days ago
        days = F.days_since(today, last_date_iso)
        freq = F.purchase_frequency_monthly(8, first_date_iso, last_date_iso)
        seg = F.classify_segment(days, first_date_iso, 0.5, today=today)
        risk = F.churn_risk_score(days, freq, 8)

        assert seg == "inactive"
        assert risk >= 50  # recency alone triggers max recency component

    def test_churn_risk_reflects_breakdown_components(self):
        # Pin the contract: score == sum of components (capped).
        for case in [
            (10, 5.0, 10, 0, 0),          # power user
            (45, 1.5, 8, 5, 0),           # mostly fine, slight cancel
            (200, 0.1, 1, 50, 0),         # everything fires
        ]:
            br = F.compute_churn_risk_breakdown(*case)
            raw_sum = (
                br.recency + br.frequency + br.single_penalty + br.cancel_penalty
            )
            assert br.score == min(100, raw_sum)
