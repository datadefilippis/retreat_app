"""Tests for ``modules.customer_insights.period_filter``.

Pure functions, fully synchronous — no DB, no I/O. Pinning the
"30d window ending today" semantics here prevents off-by-one
regressions on the period selector that would silently shift the
KPI baseline by a day every release.
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

from modules.customer_insights.period_filter import (
    PeriodWindow,
    parse_period,
    previous_period,
)


# ── parse_period — relative codes ─────────────────────────────────────────


class TestParsePeriodRelative:
    TODAY = date(2026, 5, 10)

    def test_30d_window_inclusive_endpoints(self):
        # "30d" means the last 30 days *inclusive* of today, so the
        # span is exactly 30 calendar days.
        w = parse_period("30d", today=self.TODAY)
        assert w.end == self.TODAY
        assert w.start == date(2026, 4, 11)
        assert w.days == 30
        assert w.label == "30d"

    def test_7d_window(self):
        w = parse_period("7d", today=self.TODAY)
        assert w.end == self.TODAY
        assert w.start == date(2026, 5, 4)
        assert w.days == 7

    def test_90d_window(self):
        w = parse_period("90d", today=self.TODAY)
        assert (w.end - w.start).days + 1 == 90

    def test_12m_window_uses_365_days(self):
        w = parse_period("12m", today=self.TODAY)
        assert w.days == 365
        assert w.label == "12m"

    def test_unknown_code_falls_back_to_30d(self):
        # Defensive: a malformed query parameter on the URL must not
        # raise — we degrade to the canonical default.
        w = parse_period("frob", today=self.TODAY)
        assert w.days == 30
        assert w.label == "30d"

    def test_empty_string_falls_back_to_30d(self):
        w = parse_period("", today=self.TODAY)
        assert w.days == 30

    def test_case_insensitive(self):
        w = parse_period("30D", today=self.TODAY)
        assert w.label == "30d"


class TestParsePeriodAll:
    def test_all_anchors_to_epoch_fallback(self):
        # ``all`` still has a concrete start so Mongo $gte queries are
        # uniform across paths.
        w = parse_period("all", today=date(2026, 5, 10))
        assert w.start.year == 2020
        assert w.end == date(2026, 5, 10)
        assert w.label == "all"


class TestParsePeriodCustom:
    TODAY = date(2026, 5, 10)

    def test_explicit_start_end(self):
        w = parse_period(
            "custom", start="2026-01-01", end="2026-01-31",
            today=self.TODAY,
        )
        assert w.start == date(2026, 1, 1)
        assert w.end == date(2026, 1, 31)
        assert w.days == 31
        assert w.label == "custom"

    def test_swapped_start_end_corrected(self):
        # Defensive: caller put end before start — we swap.
        w = parse_period(
            "custom", start="2026-01-31", end="2026-01-01",
            today=self.TODAY,
        )
        assert w.start < w.end

    def test_missing_start_uses_30d_default(self):
        w = parse_period("custom", end="2026-05-10", today=self.TODAY)
        assert (self.TODAY - w.start).days == 29
        assert w.end == self.TODAY

    def test_missing_end_uses_today(self):
        w = parse_period("custom", start="2026-04-01", today=self.TODAY)
        assert w.start == date(2026, 4, 1)
        assert w.end == self.TODAY

    def test_invalid_dates_use_defaults(self):
        # Both dates malformed — fall through to default behaviour.
        w = parse_period(
            "custom", start="garbage", end="oops", today=self.TODAY,
        )
        assert w.end == self.TODAY


# ── previous_period — same-length, immediately preceding ──────────────────


class TestPreviousPeriod:
    def test_basic_30d_preceding(self):
        curr = PeriodWindow(
            start=date(2026, 5, 1), end=date(2026, 5, 30), label="30d",
        )
        prev = previous_period(curr)
        assert prev.start == date(2026, 4, 1)
        assert prev.end == date(2026, 4, 30)
        assert prev.days == curr.days
        assert prev.label == "previous-30d"

    def test_one_day_window(self):
        curr = PeriodWindow(
            start=date(2026, 5, 10), end=date(2026, 5, 10), label="custom",
        )
        prev = previous_period(curr)
        assert prev.start == prev.end == date(2026, 5, 9)
        assert prev.days == 1

    def test_all_window_yields_pre_history_window(self):
        curr = parse_period("all", today=date(2026, 5, 10))
        prev = previous_period(curr)
        # "Pre-history" — same length immediately before the epoch.
        assert prev.end == date(2019, 12, 31)
        assert prev.label == "previous-all"

    def test_iso_strings_match(self):
        # Sanity — start_iso / end_iso reflect the date fields.
        curr = parse_period("7d", today=date(2026, 5, 10))
        assert curr.start_iso == "2026-05-04"
        assert curr.end_iso == "2026-05-10"
