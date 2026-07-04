"""Wave 14.HOTFIX3 — fixed_costs proration respects end_date.

2026-05-16 (~12:30 UTC, second prod bug found post-Wave-14 deploy).
User on Macelleria da Piero (org fccb21fc-...) asks "costi fissi
YTD 2026 vs YTD 2025". The chat AI reports "6.050 EUR for both
periods, INVARIATI". The user objects: "but I closed Finanziament
Attività 3 in March 2026, that should reduce my 2026 fixed costs".

Forensic dump from MongoDB:

  fixed_costs for org fccb21fc-...:
    - "Finanziament Attività 3"  | 277.70/mo | 2024-05-01 → 2026-02-28
    - "Mutuo iptecario"          | 663.64/mo | 2024-05-01 → 2028-02-29
    - "Finanziamento Privato"    | 285.00/mo | 2024-05-01 → 2027-03-10
    - "Assicurazione sulla Vita" | 108.19/mo | 2024-05-01 → null
    - 2 more financings already expired in 2024 (end=2024-07-21)

  Expected YTD 2026 (2026-01-01 → 2026-05-16):
    Att.3 active only Jan-Feb → 59 days of 277.70/mo ≈ 546 EUR
    Mutuo full period         → 137 days ≈ 3030 EUR
    Privato full period       → 137 days ≈ 1301 EUR
    Assic full period         → 137 days ≈ 494 EUR
    TOTAL ≈ 5371 EUR

  Expected YTD 2025 (2025-01-01 → 2025-05-16):
    Att.3 full period         → 136 days ≈ 1259 EUR
    + same Mutuo, Privato, Assic
    TOTAL ≈ 6072 EUR

  Expected delta: 2026 should be ~700 EUR LOWER than 2025.

  Reported: 2026 = 2025 = 6.050 EUR. WRONG.

Root cause: ``_prorate()`` in repositories/analytics_repository.py
was using ``period_days`` (the full period length) for ALL recurring
costs, ignoring ``end_date`` on the cost. A financing that closed
in Feb 2026 was charged for the FULL Jan-May 2026 window.

Fix: ``_prorate`` now accepts a ``cost_end_str`` argument and uses
the OVERLAP days between [cost_start, cost_end] and [range_start,
range_end] for proration instead of the raw period_days.

Both call sites in analytics_repository.py
(aggregate_fixed_costs_total, aggregate_fixed_costs_by_category)
pass doc.get("end_date") into the call.
"""

import os
import sys
from datetime import date
from pathlib import Path

import pytest

os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-not-for-production")
os.environ.setdefault("MONGO_URL", "mongodb://localhost:27017")
os.environ.setdefault("DB_NAME", "test_db")
os.environ.setdefault("ANTHROPIC_API_KEY", "test-key-not-real")

BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))


# ── Direct unit tests of the fixed _prorate function ──────────────────────


class TestProrateUsesEndDate:
    """The _prorate function must clamp the cost window to its
    end_date before computing overlap."""

    def test_cost_ending_mid_period_is_only_charged_for_active_days(self):
        """The exact prod scenario: Finanziament Attività 3,
        277.70/mo, active until 2026-02-28. Query period:
        2026-01-01 to 2026-05-16."""
        from repositories.analytics_repository import _prorate

        amount = 277.70
        frequency = "monthly"
        range_start = date(2026, 1, 1)
        range_end = date(2026, 5, 16)
        period_days = (range_end - range_start).days + 1  # 136

        # Pre-HOTFIX3: this returned 277.70 * 136/30 ≈ 1258 EUR
        # Post-HOTFIX3: should return 277.70 * 59/30 ≈ 546 EUR
        # (59 = (Feb 28 - Jan 1).days + 1)
        result = _prorate(
            amount, frequency, period_days,
            cost_start_str="2024-05-01",
            range_start=range_start,
            range_end=range_end,
            cost_end_str="2026-02-28",
        )
        # Active overlap = Jan 1 - Feb 28 inclusive = 59 days
        expected = 277.70 * (59 / 30)
        assert abs(result - expected) < 0.5, (
            f"HOTFIX3 regression — _prorate did not clamp to end_date. "
            f"Got {result:.2f}, expected ~{expected:.2f} (cost active "
            f"only 59 days of the 136-day query period)."
        )

    def test_cost_with_no_end_date_uses_full_period(self):
        """Open-ended cost (end_date=None) gets the full period —
        unchanged behaviour."""
        from repositories.analytics_repository import _prorate

        range_start = date(2026, 1, 1)
        range_end = date(2026, 5, 16)
        period_days = (range_end - range_start).days + 1  # 136

        result = _prorate(
            108.19, "monthly", period_days,
            cost_start_str="2024-05-01",
            range_start=range_start,
            range_end=range_end,
            cost_end_str=None,  # open-ended
        )
        expected = 108.19 * (136 / 30)
        assert abs(result - expected) < 0.5

    def test_cost_already_ended_before_period_is_zero(self):
        """A cost whose end_date is BEFORE the period start
        contributes nothing."""
        from repositories.analytics_repository import _prorate

        range_start = date(2026, 1, 1)
        range_end = date(2026, 5, 16)
        period_days = (range_end - range_start).days + 1

        # Cost ended 2024-07-21 — well before the 2026 query window
        result = _prorate(
            531.54, "monthly", period_days,
            cost_start_str="2024-05-01",
            range_start=range_start,
            range_end=range_end,
            cost_end_str="2024-07-21",
        )
        assert result == 0.0, (
            f"HOTFIX3 — cost ended in 2024 must contribute 0 to a "
            f"2026 query window. Got {result:.2f}."
        )

    def test_cost_starting_mid_period_is_clamped_to_start_date(self):
        """A cost that begins after the period start is clamped to
        its start_date for proration."""
        from repositories.analytics_repository import _prorate

        range_start = date(2026, 1, 1)
        range_end = date(2026, 5, 16)
        period_days = (range_end - range_start).days + 1

        # Cost starts 2026-03-01 — only April 1-May 16 are active...
        # actually wait, March 1 to May 16 = 77 days.
        result = _prorate(
            500.00, "monthly", period_days,
            cost_start_str="2026-03-01",
            range_start=range_start,
            range_end=range_end,
            cost_end_str=None,
        )
        # Overlap: 2026-03-01 to 2026-05-16 inclusive = 77 days
        expected = 500.00 * (77 / 30)
        assert abs(result - expected) < 0.5, (
            f"HOTFIX3 — cost starting mid-period got {result:.2f}, "
            f"expected ~{expected:.2f}."
        )

    def test_cost_full_period_2025_active(self):
        """The same Finanziament Attività 3 cost, queried for YTD
        2025 (when it was fully active) — full proration."""
        from repositories.analytics_repository import _prorate

        range_start = date(2025, 1, 1)
        range_end = date(2025, 5, 16)
        period_days = (range_end - range_start).days + 1  # 136

        result = _prorate(
            277.70, "monthly", period_days,
            cost_start_str="2024-05-01",
            range_start=range_start,
            range_end=range_end,
            cost_end_str="2026-02-28",
        )
        # Cost was fully active in YTD 2025 → 136 days
        expected = 277.70 * (136 / 30)
        assert abs(result - expected) < 0.5, (
            f"HOTFIX3 — YTD 2025 should see Att.3 fully active. "
            f"Got {result:.2f}, expected ~{expected:.2f}."
        )

    def test_one_off_cost_unchanged(self):
        """one_off behaviour must not change — only when start_date
        lies inside the range, full amount; else 0."""
        from repositories.analytics_repository import _prorate

        range_start = date(2026, 1, 1)
        range_end = date(2026, 5, 16)
        period_days = (range_end - range_start).days + 1

        # one_off WITHIN range
        result = _prorate(
            1500.00, "one_off", period_days,
            cost_start_str="2026-03-10",
            range_start=range_start,
            range_end=range_end,
            cost_end_str=None,
        )
        assert result == 1500.0

        # one_off OUTSIDE range
        result = _prorate(
            1500.00, "one_off", period_days,
            cost_start_str="2026-06-01",
            range_start=range_start,
            range_end=range_end,
            cost_end_str=None,
        )
        assert result == 0.0


# ── Macelleria da Piero exact reproduction (integration shape) ───────────


class TestMacelleriaDaPieroProductionScenario:
    """End-to-end reproduction of the prod scenario the user
    reported on 2026-05-16. Uses the 6 fixed_costs from the live
    Macelleria da Piero account and asserts the YTD 2026 vs 2025
    delta is ~700 EUR (not ~0)."""

    MACELLERIA_FIXED_COSTS = [
        # The exact dataset from prod
        {"amount": 531.54, "frequency": "mensile",
         "start_date": "2024-05-01", "end_date": "2024-07-21",
         "category": "finanziamento", "is_active": True},
        {"amount": 624.42, "frequency": "mensile",
         "start_date": "2024-05-01", "end_date": "2024-07-21",
         "category": "finanziamento", "is_active": True},
        {"amount": 277.70, "frequency": "mensile",
         "start_date": "2024-05-01", "end_date": "2026-02-28",
         "category": "finanziamento", "is_active": True},
        {"amount": 663.64, "frequency": "mensile",
         "start_date": "2024-05-01", "end_date": "2028-02-29",
         "category": "finanziamento", "is_active": True},
        {"amount": 285.00, "frequency": "mensile",
         "start_date": "2024-05-01", "end_date": "2027-03-10",
         "category": "finanziamento", "is_active": True},
        {"amount": 108.19, "frequency": "mensile",
         "start_date": "2024-05-01", "end_date": None,
         "category": "Assicurazione", "is_active": True},
    ]

    @staticmethod
    def _compute_total(fixed_costs, start, end):
        """Mini reimplementation of aggregate_fixed_costs_total
        flow — same _cost_overlaps_period + _prorate sequence."""
        from repositories.analytics_repository import (
            _prorate, _cost_overlaps_period,
        )
        period_days = (end - start).days + 1
        total = 0.0
        for doc in fixed_costs:
            # Note: the prod code uses "monthly" not "mensile" — the
            # _FREQUENCY_DAYS dict has only English keys. "mensile"
            # falls through to the default 30 — same effect.
            if not _cost_overlaps_period(doc, start, end):
                continue
            total += _prorate(
                doc["amount"], doc["frequency"], period_days,
                doc["start_date"], start, end, doc["end_date"],
            )
        return round(total, 2)

    def test_ytd_2026_lower_than_ytd_2025_due_to_att3_termination(self):
        ytd_2026 = self._compute_total(
            self.MACELLERIA_FIXED_COSTS,
            date(2026, 1, 1), date(2026, 5, 16),
        )
        ytd_2025 = self._compute_total(
            self.MACELLERIA_FIXED_COSTS,
            date(2025, 1, 1), date(2025, 5, 16),
        )

        # The delta must reflect that Att.3 (277.70/mo) is
        # active for ~136 days in 2025 but only ~59 days in 2026.
        # Expected delta: 277.70 * (136 - 59) / 30 ≈ 712 EUR
        delta = ytd_2025 - ytd_2026
        assert delta > 500, (
            f"HOTFIX3 regression — Macelleria YTD 2026 fixed_costs "
            f"({ytd_2026:.2f}) is not meaningfully lower than YTD 2025 "
            f"({ytd_2025:.2f}). Delta={delta:.2f}, expected > 500 EUR "
            f"because Finanziament Attività 3 ended Feb 28, 2026. "
            f"Pre-HOTFIX3 the delta was ~0 — proration ignored "
            f"end_date."
        )
        # Sanity ceiling — delta shouldn't be more than ~800 EUR
        # (277.70/mo × ~3 months max)
        assert delta < 900, (
            f"HOTFIX3 — delta {delta:.2f} is suspiciously large. "
            f"Att.3 termination should only remove ~3 months × 278 "
            f"EUR ≈ 712 EUR."
        )


# ── Source-code sentinel ──────────────────────────────────────────────────


class TestProrateSignatureSentinel:
    """The _prorate function must accept cost_end_str. Future
    commits dropping the parameter turn this red."""

    def test_prorate_accepts_cost_end_str(self):
        import inspect
        from repositories.analytics_repository import _prorate
        sig = inspect.signature(_prorate)
        assert "cost_end_str" in sig.parameters, (
            "HOTFIX3 regression — _prorate no longer accepts "
            "cost_end_str. The fix has been reverted."
        )

    def test_both_call_sites_pass_end_date(self):
        """Both aggregate_fixed_costs_total and
        aggregate_fixed_costs_by_category must pass doc.get('end_date')
        as the 7th arg."""
        import inspect
        from repositories import analytics_repository as ar

        src_total = inspect.getsource(ar.aggregate_fixed_costs_total)
        src_cat = inspect.getsource(ar.aggregate_fixed_costs_by_category)

        for name, src in [
            ("aggregate_fixed_costs_total", src_total),
            ("aggregate_fixed_costs_by_category", src_cat),
        ]:
            assert 'doc.get("end_date")' in src or "doc.get('end_date')" in src, (
                f"HOTFIX3 regression — {name} no longer passes "
                f"end_date into _prorate. Costs that ended mid-period "
                f"will be double-counted again."
            )
