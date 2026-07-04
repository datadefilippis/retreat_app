"""Tests for ``services.ai_analytics_service._get_date_range`` — Wave 13.1.

Verifies the adapter contract that the legacy entry point now delegates
to ``core.period_resolver.resolve()`` while preserving full backward
compatibility:

  - Existing valid inputs (7d / 30d / 90d / explicit dates) produce
    output IDENTICAL to pre-Wave-13.
  - NEW: ytd / mtd / qtd / 1y and case-insensitive aliases work.
  - Invalid inputs no longer crash MongoDB downstream — they log a
    WARNING and fall back to the safe 30d default.

These tests intentionally do NOT mock the resolver — they exercise the
full adapter+resolver path to catch any wire-up regression.
"""

import os
import sys
import logging
from datetime import date, timedelta, timezone, datetime
from pathlib import Path
from unittest.mock import patch

import pytest

os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-not-for-production")
os.environ.setdefault("MONGO_URL", "mongodb://localhost:27017")
os.environ.setdefault("DB_NAME", "test_db")

BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from services.ai_analytics_service import _get_date_range


# ── Helpers ─────────────────────────────────────────────────────────────────


def _frozen_today(today: date):
    """Patch ``datetime.now(timezone.utc)`` inside the adapter so the
    rolling-window math is deterministic.

    The adapter calls ``datetime.now(timezone.utc).date()`` once to anchor
    "today". We patch the module-level ``datetime`` symbol so the call
    returns a frozen value.
    """
    fixed_dt = datetime(today.year, today.month, today.day, tzinfo=timezone.utc)

    class FrozenDatetime(datetime):
        @classmethod
        def now(cls, tz=None):
            return fixed_dt

    return patch("services.ai_analytics_service.datetime", FrozenDatetime)


# ── Backward compatibility (Pre-Wave-13 behaviour preserved) ─────────────────


class TestBackwardCompat:
    """All pre-Wave-13 valid inputs must produce identical output."""

    def test_30d_default(self):
        # Pre-Wave-13: period_days.get("30d") = 30 → start = today - 29
        T = date(2026, 5, 16)
        with _frozen_today(T):
            s, e = _get_date_range("30d", None, None)
        assert s == "2026-04-17"
        assert e == "2026-05-16"

    def test_7d(self):
        T = date(2026, 5, 16)
        with _frozen_today(T):
            s, e = _get_date_range("7d", None, None)
        assert s == "2026-05-10"
        assert e == "2026-05-16"

    def test_90d(self):
        T = date(2026, 5, 16)
        with _frozen_today(T):
            s, e = _get_date_range("90d", None, None)
        assert s == "2026-02-16"
        assert e == "2026-05-16"

    def test_explicit_dates_win_over_token(self):
        # Pre-Wave-13: if both dates provided, returned verbatim
        T = date(2026, 5, 16)
        with _frozen_today(T):
            s, e = _get_date_range("30d", "2026-01-01", "2026-03-31")
        assert s == "2026-01-01"
        assert e == "2026-03-31"

    def test_explicit_dates_only_no_token(self):
        T = date(2026, 5, 16)
        with _frozen_today(T):
            s, e = _get_date_range(None, "2026-04-01", "2026-04-30")
        assert s == "2026-04-01"
        assert e == "2026-04-30"

    def test_none_period_falls_to_30d(self):
        T = date(2026, 5, 16)
        with _frozen_today(T):
            s, e = _get_date_range(None, None, None)
        assert s == "2026-04-17"
        assert e == "2026-05-16"

    def test_empty_string_period_falls_to_30d(self):
        # Pre-Wave-13: period_days.get("") = None → default 30
        T = date(2026, 5, 16)
        with _frozen_today(T):
            s, e = _get_date_range("", None, None)
        assert s == "2026-04-17"
        assert e == "2026-05-16"


# ── NEW: previously silent-30d tokens now resolve correctly ─────────────────


class TestNewVocabulary:
    """Phase 13.1 unlocks the calendar tokens + aliases. Pre-Wave-13 these
    all silently returned a 30d window — now they return the right one."""

    def test_ytd(self):
        T = date(2026, 5, 16)
        with _frozen_today(T):
            s, e = _get_date_range("ytd", None, None)
        assert s == "2026-01-01"
        assert e == "2026-05-16"

    def test_mtd(self):
        T = date(2026, 5, 16)
        with _frozen_today(T):
            s, e = _get_date_range("mtd", None, None)
        assert s == "2026-05-01"
        assert e == "2026-05-16"

    def test_qtd(self):
        T = date(2026, 5, 16)
        with _frozen_today(T):
            s, e = _get_date_range("qtd", None, None)
        assert s == "2026-04-01"
        assert e == "2026-05-16"

    def test_1y(self):
        T = date(2026, 5, 16)
        with _frozen_today(T):
            s, e = _get_date_range("1y", None, None)
        assert s == "2025-05-17"
        assert e == "2026-05-16"

    def test_alias_last_30_days(self):
        T = date(2026, 5, 16)
        with _frozen_today(T):
            s, e = _get_date_range("last_30_days", None, None)
        assert s == "2026-04-17"
        assert e == "2026-05-16"

    def test_alias_case_insensitive_ytd(self):
        T = date(2026, 5, 16)
        with _frozen_today(T):
            s, e = _get_date_range("YEAR_TO_DATE", None, None)
        assert s == "2026-01-01"
        assert e == "2026-05-16"


# ── Lenient fallback on bad input ────────────────────────────────────────────


class TestLenientFallback:
    """The adapter swallows InvalidPeriodError and falls back to 30d,
    keeping pre-Wave-13 "always returns something" guarantee — but now
    with an audible warning log."""

    def test_unknown_token_falls_back_to_30d(self, caplog):
        T = date(2026, 5, 16)
        with _frozen_today(T), caplog.at_level(logging.WARNING):
            s, e = _get_date_range("q1_2026", None, None)
        assert s == "2026-04-17"
        assert e == "2026-05-16"
        # Warning logged so prod log analysis can spot offenders
        assert any("unknown period token" in rec.message.lower()
                   for rec in caplog.records)
        assert any("q1_2026" in rec.message for rec in caplog.records)

    def test_swapped_explicit_dates_falls_back(self, caplog):
        T = date(2026, 5, 16)
        with _frozen_today(T), caplog.at_level(logging.WARNING):
            s, e = _get_date_range(None, "2026-05-16", "2026-01-01")
        # Falls back to safe 30d
        assert s == "2026-04-17"
        assert e == "2026-05-16"
        assert any("rejected period input" in rec.message.lower()
                   for rec in caplog.records)

    def test_bad_date_format_falls_back(self, caplog):
        T = date(2026, 5, 16)
        with _frozen_today(T), caplog.at_level(logging.WARNING):
            s, e = _get_date_range(None, "not-a-date", "2026-05-16")
        # Falls back, NOT crashes downstream
        assert s == "2026-04-17"
        assert e == "2026-05-16"
        assert any("rejected period input" in rec.message.lower()
                   for rec in caplog.records)

    def test_future_end_date_falls_back(self, caplog):
        T = date(2026, 5, 16)
        with _frozen_today(T), caplog.at_level(logging.WARNING):
            s, e = _get_date_range(None, "2026-01-01", "2099-12-31")
        assert s == "2026-04-17"
        assert e == "2026-05-16"
        assert any("rejected period input" in rec.message.lower()
                   for rec in caplog.records)

    def test_only_start_date_falls_back(self, caplog):
        T = date(2026, 5, 16)
        with _frozen_today(T), caplog.at_level(logging.WARNING):
            s, e = _get_date_range("30d", "2026-01-01", None)
        # Pre-Wave-13: condition `start_date and end_date` was False,
        # so period kicked in → 30d. Same here, via fallback.
        # Note: the resolver raises here (one date but not both), so we
        # take the InvalidPeriodError branch and log "rejected".
        assert s == "2026-04-17"
        assert e == "2026-05-16"


# ── Return shape sanity ──────────────────────────────────────────────────────


class TestReturnShape:
    """Callers consume `_get_date_range` as a 2-tuple of ISO strings.
    The adapter must preserve this exact shape across all paths."""

    @pytest.mark.parametrize("period", [
        "7d", "30d", "90d", "1y", "ytd", "mtd", "qtd",
        "last_30_days", "this_year",
    ])
    def test_token_returns_iso_tuple(self, period):
        T = date(2026, 5, 16)
        with _frozen_today(T):
            result = _get_date_range(period, None, None)
        assert isinstance(result, tuple)
        assert len(result) == 2
        assert all(isinstance(s, str) for s in result)
        assert all(len(s) == 10 and s[4] == "-" and s[7] == "-" for s in result)

    def test_explicit_returns_iso_tuple(self):
        T = date(2026, 5, 16)
        with _frozen_today(T):
            result = _get_date_range(None, "2026-01-01", "2026-03-31")
        assert result == ("2026-01-01", "2026-03-31")

    def test_fallback_returns_iso_tuple(self):
        T = date(2026, 5, 16)
        with _frozen_today(T):
            result = _get_date_range("garbage", None, None)
        assert result == ("2026-04-17", "2026-05-16")
