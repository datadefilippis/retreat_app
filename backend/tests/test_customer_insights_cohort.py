"""Tests for ``modules.customer_insights.cohort``.

Pure cohort math — no DB. Verifies the bucket diff logic, the cohort
table assembly, and the retention percentage cascade.
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

from modules.customer_insights.cohort import (
    CohortRow,
    bucket_for_date,
    bucket_index_diff,
    build_cohort_table,
)


# ── bucket_for_date ────────────────────────────────────────────────────────


class TestBucketForDate:
    def test_month(self):
        assert bucket_for_date(date(2026, 5, 10), "month") == "2026-05"

    def test_month_zero_padded(self):
        assert bucket_for_date(date(2026, 1, 1), "month") == "2026-01"

    def test_quarter_q1(self):
        assert bucket_for_date(date(2026, 2, 15), "quarter") == "2026-Q1"

    def test_quarter_q2(self):
        assert bucket_for_date(date(2026, 5, 10), "quarter") == "2026-Q2"

    def test_quarter_q4(self):
        assert bucket_for_date(date(2026, 12, 31), "quarter") == "2026-Q4"

    def test_week_iso(self):
        # Jan 6 2026 is a Tuesday → ISO week 02.
        assert bucket_for_date(date(2026, 1, 6), "week") == "2026-W02"

    def test_unknown_bucket_defaults_to_month(self):
        assert bucket_for_date(date(2026, 5, 10), "fortnight") == "2026-05"


# ── bucket_index_diff ──────────────────────────────────────────────────────


class TestBucketDiff:
    def test_month_diff_positive(self):
        assert bucket_index_diff("2026-01", "2026-05", "month") == 4

    def test_month_diff_zero(self):
        assert bucket_index_diff("2026-01", "2026-01", "month") == 0

    def test_month_diff_clamped_at_zero(self):
        # b before a — never negative.
        assert bucket_index_diff("2026-05", "2026-01", "month") == 0

    def test_month_diff_across_years(self):
        assert bucket_index_diff("2025-10", "2026-02", "month") == 4

    def test_quarter_diff(self):
        assert bucket_index_diff("2026-Q1", "2026-Q3", "quarter") == 2

    def test_quarter_diff_across_years(self):
        assert bucket_index_diff("2025-Q4", "2026-Q2", "quarter") == 2

    def test_week_diff(self):
        # Jan 6 (W02) → Jan 27 (W05) = 3 weeks.
        assert bucket_index_diff("2026-W02", "2026-W05", "week") == 3

    def test_invalid_inputs_safe(self):
        # Defensive: garbage input never raises.
        assert bucket_index_diff("garbage", "2026-05", "month") == 0
        assert bucket_index_diff("2026-05", "garbage", "month") == 0


# ── build_cohort_table — happy paths ──────────────────────────────────────


class TestBuildCohortTable:
    def test_empty_input(self):
        assert build_cohort_table({}) == []

    def test_single_customer_single_purchase(self):
        rows = build_cohort_table(
            {"c1": [date(2026, 1, 5)]},
            bucket="month", horizon=4,
        )
        assert len(rows) == 1
        assert rows[0].acquisition_bucket == "2026-01"
        assert rows[0].size == 1
        # M0 active, M1-M3 silent.
        assert rows[0].retention == [1, 0, 0, 0]

    def test_multi_customer_multi_period(self):
        # Documented example from the cohort.py docstring.
        rows = build_cohort_table({
            "c1": [date(2026, 1, 5), date(2026, 2, 10), date(2026, 3, 1)],
            "c2": [date(2026, 1, 20), date(2026, 4, 3)],
            "c3": [date(2026, 2, 1), date(2026, 2, 25)],
        }, bucket="month", horizon=4)

        # 2 cohorts: Jan and Feb.
        assert len(rows) == 2

        # Jan cohort: c1 (5 Jan) + c2 (20 Jan) → size 2.
        jan = next(r for r in rows if r.acquisition_bucket == "2026-01")
        assert jan.size == 2
        # M0 (Jan): both. M1 (Feb): c1 only. M2 (Mar): c1 only. M3 (Apr): c2 only.
        assert jan.retention == [2, 1, 1, 1]

        # Feb cohort: c3 only.
        feb = next(r for r in rows if r.acquisition_bucket == "2026-02")
        assert feb.size == 1
        # All c3's purchases land in February → only M0 active.
        assert feb.retention == [1, 0, 0, 0]

    def test_horizon_caps_retention_length(self):
        rows = build_cohort_table(
            {"c1": [date(2026, 1, 1), date(2027, 1, 1)]},
            bucket="month", horizon=6,
        )
        # 12-month gap > horizon=6 → retention length = 6, last cells 0.
        assert len(rows[0].retention) == 6
        assert rows[0].retention[0] == 1
        assert rows[0].retention[5] == 0

    def test_same_day_purchases_dedupe_to_one_active(self):
        # Customer made 3 purchases on the same day — should still count
        # as 1 active in M0, not 3.
        rows = build_cohort_table(
            {"c1": [
                date(2026, 1, 5), date(2026, 1, 5), date(2026, 1, 5),
            ]},
            bucket="month", horizon=2,
        )
        assert rows[0].size == 1
        assert rows[0].retention == [1, 0]

    def test_quarter_bucket(self):
        rows = build_cohort_table(
            {"c1": [date(2026, 1, 5), date(2026, 5, 10)]},
            bucket="quarter", horizon=3,
        )
        assert rows[0].acquisition_bucket == "2026-Q1"
        assert rows[0].retention == [1, 1, 0]

    def test_customer_with_empty_dates_skipped(self):
        rows = build_cohort_table({"c1": []}, bucket="month", horizon=2)
        assert rows == []


# ── retention_pct property ────────────────────────────────────────────────


class TestRetentionPct:
    def test_basic(self):
        row = CohortRow(
            acquisition_bucket="2026-01", size=10,
            retention=[10, 8, 6, 5],
        )
        assert row.retention_pct == [100.0, 80.0, 60.0, 50.0]

    def test_zero_size_returns_none(self):
        # Should never happen in practice but be defensive.
        row = CohortRow(
            acquisition_bucket="2026-01", size=0, retention=[0, 0, 0],
        )
        assert row.retention_pct == [None, None, None]
