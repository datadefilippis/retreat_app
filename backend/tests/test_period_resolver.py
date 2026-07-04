"""Tests for the canonical period resolver — Wave 13.0 foundation.

Covers:
  - Each token: correct date math (rolling, calendar-to-date)
  - Aliases: case-insensitive, alternative spellings
  - Explicit dates: win over token, support no-token usage
  - Validation: bad format, swapped, future, only-one-of-pair
  - Strict mode: unknown tokens raise
  - Non-strict mode: unknown tokens fall back with FALLBACK source
  - Edge cases: leap day, year/quarter boundaries, inclusive count
  - ResolvedPeriod immutability + audit serialisation
  - Default config validation

No DB, no async, no I/O. Pure unit tests.
"""

import os
import sys
from datetime import date
from pathlib import Path

import pytest

os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-not-for-production")
os.environ.setdefault("MONGO_URL", "mongodb://localhost:27017")
os.environ.setdefault("DB_NAME", "test_db")

BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from core.period_resolver import (
    ACCEPTED_TOKENS,
    DEFAULT_PERIOD,
    InvalidPeriodError,
    ResolutionSource,
    ResolvedPeriod,
    resolve,
)


# Fixed "today" for deterministic tests across all classes. May 16, 2026
# was chosen because it sits comfortably mid-month, mid-Q2, mid-year and
# is the same date used in the Wave 13 audit doc that motivated this
# module — so test failures map cleanly to audit scenarios.
T = date(2026, 5, 16)


# ── Tokens: rolling windows ──────────────────────────────────────────────────


class TestRollingTokens:
    def test_7d(self):
        r = resolve("7d", today=T)
        assert r.label == "7d"
        assert r.start == date(2026, 5, 10)  # T - 6 days (7-day inclusive)
        assert r.end == T
        assert r.days == 7
        assert r.resolution_source == ResolutionSource.TOKEN

    def test_30d(self):
        r = resolve("30d", today=T)
        assert r.start == date(2026, 4, 17)   # T - 29 days
        assert r.end == T
        assert r.days == 30

    def test_90d(self):
        r = resolve("90d", today=T)
        # Day-of-year 136 (May 16) minus 89 = day 47 = Feb 16
        assert r.start == date(2026, 2, 16)
        assert r.days == 90

    def test_1y(self):
        r = resolve("1y", today=T)
        assert r.days == 365
        assert r.end == T
        # 365 days back inclusive: 2025-05-17
        assert r.start == date(2025, 5, 17)


# ── Tokens: calendar-to-date ─────────────────────────────────────────────────


class TestCalendarTokens:
    def test_ytd(self):
        r = resolve("ytd", today=T)
        assert r.label == "ytd"
        assert r.start == date(2026, 1, 1)
        assert r.end == T
        # Jan(31) + Feb(28) + Mar(31) + Apr(30) + 16 = 136
        assert r.days == 136
        assert r.resolution_source == ResolutionSource.TOKEN

    def test_mtd(self):
        r = resolve("mtd", today=T)
        assert r.start == date(2026, 5, 1)
        assert r.end == T
        assert r.days == 16

    def test_qtd_in_q2(self):
        # T = May 16 → Q2 (Apr-Jun)
        r = resolve("qtd", today=T)
        assert r.start == date(2026, 4, 1)
        assert r.end == T
        # Apr(30) + 16 = 46
        assert r.days == 46

    def test_qtd_in_q1(self):
        feb = date(2026, 2, 14)
        r = resolve("qtd", today=feb)
        assert r.start == date(2026, 1, 1)
        assert r.end == feb
        assert r.days == 45   # Jan(31) + 14

    def test_qtd_in_q3(self):
        sept = date(2026, 9, 15)
        r = resolve("qtd", today=sept)
        assert r.start == date(2026, 7, 1)
        assert r.end == sept

    def test_qtd_in_q4(self):
        dec = date(2026, 12, 1)
        r = resolve("qtd", today=dec)
        assert r.start == date(2026, 10, 1)
        assert r.end == dec


# ── Aliases ──────────────────────────────────────────────────────────────────


class TestAliases:
    @pytest.mark.parametrize("alias,canonical", [
        # rolling — case variations
        ("last_7_days", "7d"),
        ("LAST_7_DAYS", "7d"),
        ("7days", "7d"),
        ("last_30_days", "30d"),
        ("LAST_30_DAYS", "30d"),
        ("30Days", "30d"),
        ("last_90_days", "90d"),
        ("90DAYS", "90d"),
        ("last_12_months", "1y"),
        ("last_365_days", "1y"),
        ("last_year_rolling", "1y"),
        # calendar
        ("year_to_date", "ytd"),
        ("YEAR_TO_DATE", "ytd"),
        ("this_year", "ytd"),
        ("month_to_date", "mtd"),
        ("this_month", "mtd"),
        ("quarter_to_date", "qtd"),
        ("this_quarter", "qtd"),
    ])
    def test_alias_resolves_to_canonical(self, alias, canonical):
        r = resolve(alias, today=T)
        assert r.label == canonical
        assert r.resolution_source == ResolutionSource.TOKEN
        # requested_period preserves the original un-normalised input
        # for audit logs ("what the model actually emitted").
        assert r.requested_period == alias

    def test_leading_trailing_whitespace_stripped(self):
        r = resolve("  30d  ", today=T)
        assert r.label == "30d"
        assert r.resolution_source == ResolutionSource.TOKEN


# ── Explicit dates ───────────────────────────────────────────────────────────


class TestExplicitDates:
    def test_both_dates_win_over_token(self):
        # Token says 30d but explicit dates are Q1 → dates must win.
        # This is the safety guarantee that lets the frontend pre-resolve
        # ytd/mtd into dates without worrying about token leakage.
        r = resolve(
            period="30d",
            start_date="2026-01-01",
            end_date="2026-03-31",
            today=T,
        )
        assert r.start == date(2026, 1, 1)
        assert r.end == date(2026, 3, 31)
        assert r.days == 90
        assert r.resolution_source == ResolutionSource.EXPLICIT_DATES
        # Label preserves the token hint when one was provided alongside
        # the dates — useful for "user is on YTD view" context.
        assert r.label == "30d"
        # And the raw inputs survive for the audit log.
        assert r.requested_period == "30d"
        assert r.requested_start == "2026-01-01"
        assert r.requested_end == "2026-03-31"

    def test_both_dates_no_token_labelled_custom(self):
        r = resolve(start_date="2026-04-01", end_date="2026-04-30", today=T)
        assert r.label == "custom"
        assert r.days == 30
        assert r.resolution_source == ResolutionSource.EXPLICIT_DATES

    def test_only_start_date_raises(self):
        with pytest.raises(InvalidPeriodError, match="must be provided together"):
            resolve(start_date="2026-01-01", today=T)

    def test_only_end_date_raises(self):
        with pytest.raises(InvalidPeriodError, match="must be provided together"):
            resolve(end_date="2026-05-16", today=T)

    def test_swapped_dates_raise(self):
        with pytest.raises(InvalidPeriodError, match="must be <="):
            resolve(
                start_date="2026-05-16",
                end_date="2026-01-01",
                today=T,
            )

    def test_future_end_date_raises_by_default(self):
        with pytest.raises(InvalidPeriodError, match="future"):
            resolve(
                start_date="2026-05-01",
                end_date="2027-01-01",
                today=T,
            )

    def test_future_end_date_allowed_when_flag_set(self):
        # Forward-looking surfaces (rentals upcoming, agenda) need this.
        r = resolve(
            start_date="2026-05-01",
            end_date="2026-12-31",
            today=T,
            allow_future=True,
        )
        assert r.end == date(2026, 12, 31)

    def test_invalid_format_start_raises(self):
        with pytest.raises(InvalidPeriodError, match="not a valid YYYY-MM-DD"):
            resolve(start_date="not-a-date", end_date="2026-05-16", today=T)

    def test_invalid_format_end_raises(self):
        with pytest.raises(InvalidPeriodError, match="not a valid YYYY-MM-DD"):
            resolve(start_date="2026-05-01", end_date="2026-13-99", today=T)

    def test_same_day_range_valid(self):
        r = resolve(
            start_date="2026-05-16",
            end_date="2026-05-16",
            today=T,
        )
        assert r.days == 1


# ── custom / data_range require explicit dates ───────────────────────────────


class TestExplicitRequiredTokens:
    @pytest.mark.parametrize("token", ["custom", "data_range"])
    def test_token_without_dates_raises(self, token):
        with pytest.raises(InvalidPeriodError, match="requires explicit"):
            resolve(period=token, today=T)

    @pytest.mark.parametrize("token", ["custom", "data_range"])
    def test_token_with_dates_works(self, token):
        r = resolve(
            period=token,
            start_date="2026-01-01",
            end_date="2026-03-31",
            today=T,
        )
        # Label uses the provided token so the audit log shows which
        # frontend flow the request came from.
        assert r.label == token
        assert r.resolution_source == ResolutionSource.EXPLICIT_DATES


# ── Unknown tokens: strict vs non-strict ─────────────────────────────────────


class TestUnknownTokens:
    def test_unknown_token_strict_raises(self):
        with pytest.raises(InvalidPeriodError, match="Unknown period token"):
            resolve(period="q1_2026", today=T, strict=True)

    def test_unknown_token_non_strict_falls_back_to_default(self):
        r = resolve(period="q1_2026", today=T, strict=False)
        assert r.resolution_source == ResolutionSource.FALLBACK_UNKNOWN_TOKEN
        assert r.label == DEFAULT_PERIOD
        # Original (rejected) token preserved for the audit log so we
        # can tell "the model emitted 'q1_2026' but we used 30d".
        assert r.requested_period == "q1_2026"

    def test_unknown_token_non_strict_uses_custom_default(self):
        r = resolve(period="bogus", today=T, strict=False, default="ytd")
        assert r.resolution_source == ResolutionSource.FALLBACK_UNKNOWN_TOKEN
        assert r.label == "ytd"
        assert r.start == date(2026, 1, 1)

    def test_strict_error_message_lists_accepted_tokens(self):
        with pytest.raises(InvalidPeriodError) as exc_info:
            resolve(period="last_month", today=T, strict=True)
        msg = str(exc_info.value)
        # Spot-check that the error tells the caller what IS accepted.
        assert "7d" in msg
        assert "ytd" in msg
        assert "start_date" in msg


# ── Default behaviour ────────────────────────────────────────────────────────


class TestDefaultBehavior:
    def test_no_input_uses_default(self):
        r = resolve(today=T)
        assert r.label == DEFAULT_PERIOD
        assert r.resolution_source == ResolutionSource.DEFAULT
        assert r.requested_period is None

    def test_default_can_be_overridden(self):
        r = resolve(today=T, default="ytd")
        assert r.label == "ytd"
        assert r.resolution_source == ResolutionSource.DEFAULT

    def test_invalid_default_custom_raises(self):
        # "custom" needs explicit dates → cannot be a default value.
        with pytest.raises(InvalidPeriodError, match="invalid default"):
            resolve(today=T, default="custom")

    def test_invalid_default_unknown_raises(self):
        with pytest.raises(InvalidPeriodError, match="invalid default"):
            resolve(today=T, default="garbage")


# ── Edge cases ───────────────────────────────────────────────────────────────


class TestEdgeCases:
    def test_leap_day(self):
        leap = date(2024, 2, 29)
        r = resolve("30d", today=leap)
        assert r.end == leap
        assert r.days == 30

    def test_year_boundary_ytd_jan_1(self):
        r = resolve("ytd", today=date(2026, 1, 1))
        # Jan 1 itself: start == end, days == 1
        assert r.start == r.end == date(2026, 1, 1)
        assert r.days == 1

    def test_quarter_boundary_first_day_of_q(self):
        # Apr 1 = first day of Q2 → qtd window is just that one day.
        r = resolve("qtd", today=date(2026, 4, 1))
        assert r.start == r.end == date(2026, 4, 1)
        assert r.days == 1

    def test_30d_inclusive_count(self):
        # Sanity: a 30d window covers 30 dates inclusive — the delta in
        # days is 29 (exclusive), but .days is 30 (inclusive).
        r = resolve("30d", today=T)
        assert (r.end - r.start).days == 29
        assert r.days == 30

    def test_empty_string_period_treated_as_none(self):
        r = resolve(period="", today=T)
        assert r.resolution_source == ResolutionSource.DEFAULT

    def test_whitespace_only_period_treated_as_none(self):
        r = resolve(period="   ", today=T)
        assert r.resolution_source == ResolutionSource.DEFAULT

    def test_none_period_no_dates_uses_default(self):
        r = resolve(period=None, today=T)
        assert r.resolution_source == ResolutionSource.DEFAULT


# ── Resolved shape + serialisation ───────────────────────────────────────────


class TestResolvedPeriod:
    def test_iso_properties(self):
        r = resolve("ytd", today=T)
        assert r.start_iso == "2026-01-01"
        assert r.end_iso == "2026-05-16"

    def test_to_audit_dict_token(self):
        r = resolve(period="ytd", today=T)
        d = r.to_audit_dict()
        assert d == {
            "label": "ytd",
            "start": "2026-01-01",
            "end": "2026-05-16",
            "days": 136,
            "resolution_source": "token",
            "requested": {
                "period": "ytd",
                "start_date": None,
                "end_date": None,
            },
        }

    def test_to_audit_dict_explicit_dates(self):
        r = resolve(
            period="30d",
            start_date="2026-01-01",
            end_date="2026-03-31",
            today=T,
        )
        d = r.to_audit_dict()
        assert d["resolution_source"] == "explicit_dates"
        assert d["requested"] == {
            "period": "30d",
            "start_date": "2026-01-01",
            "end_date": "2026-03-31",
        }

    def test_to_audit_dict_fallback(self):
        r = resolve(period="q1_2026", today=T, strict=False)
        d = r.to_audit_dict()
        assert d["resolution_source"] == "fallback_unknown_token"
        assert d["label"] == "30d"
        assert d["requested"]["period"] == "q1_2026"

    def test_to_audit_dict_default(self):
        r = resolve(today=T)
        d = r.to_audit_dict()
        assert d["resolution_source"] == "default"
        assert d["requested"]["period"] is None

    def test_immutable(self):
        r = resolve("30d", today=T)
        with pytest.raises(Exception):
            r.label = "ytd"   # frozen dataclass → setattr should fail


# ── Constants introspectable ─────────────────────────────────────────────────


class TestConstants:
    def test_accepted_tokens_contains_all_canonical(self):
        for tok in ["7d", "30d", "90d", "1y", "ytd", "mtd", "qtd",
                    "custom", "data_range"]:
            assert tok in ACCEPTED_TOKENS

    def test_default_period_resolves(self):
        # If a future contributor changes DEFAULT_PERIOD, this test
        # catches incompatibility immediately.
        r = resolve(today=T)
        assert r.label == DEFAULT_PERIOD
        assert r.start <= r.end

    def test_accepted_tokens_frozen(self):
        # Cannot mutate the public contract by mistake.
        assert isinstance(ACCEPTED_TOKENS, frozenset)


# ── Cross-flow sanity ────────────────────────────────────────────────────────


class TestCrossFlowSanity:
    """End-to-end checks that mirror real chat-AI scenarios.

    These are the user-facing scenarios that motivated Wave 13. Each one
    documents a failure mode pre-Wave-13 and asserts the resolver now
    handles it correctly.
    """

    def test_scenario_model_emits_ytd_no_dates(self):
        # PRE-WAVE-13: model emits period="ytd" with no dates because the
        # frontend forgot to pre-resolve → _get_date_range silently
        # returned 30d. Post-Wave-13: ytd is in the vocabulary, resolver
        # computes the correct YTD window.
        r = resolve(period="ytd", today=T)
        assert r.start == date(2026, 1, 1)
        assert r.end == T
        assert r.resolution_source == ResolutionSource.TOKEN

    def test_scenario_frontend_pre_resolves_dates(self):
        # Today's working flow: frontend converts "ytd" → start/end dates
        # before sending. Resolver respects the dates and the token hint.
        r = resolve(
            period="ytd",
            start_date="2026-01-01",
            end_date="2026-05-16",
            today=T,
        )
        assert r.resolution_source == ResolutionSource.EXPLICIT_DATES
        assert r.label == "ytd"
        assert r.days == 136

    def test_scenario_alert_window_explicit(self):
        # Wave 13.4 use-case: replay an alert's analysis window. Alert
        # was generated 30 days ago for a 30d-back window.
        r = resolve(
            start_date="2026-03-15",
            end_date="2026-04-15",
            today=T,
        )
        assert r.label == "custom"
        assert r.days == 32

    def test_scenario_unknown_quarter_label_strict_blocks(self):
        # Phase 13.1.C goal: once strict mode is enabled, the model
        # cannot accidentally cause silent 30d fallbacks.
        with pytest.raises(InvalidPeriodError):
            resolve(period="Q2_2026", today=T, strict=True)
