"""Suite del denaro — generazione schedule (Fase 2, S1).

INVARIANTE SACRA: la somma delle righe è SEMPRE il totale dell'ordine,
per qualsiasi combinazione di modalità, percentuale e totale. Un centesimo
perso qui è un cliente che discute e un libro mastro che non quadra.
"""

import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-not-for-production")
os.environ.setdefault("MONGO_URL", "mongodb://localhost:27017")
os.environ.setdefault("DB_NAME", "test_db")

import pytest

from models.payment_plan import (
    CancellationTier,
    DepositType,
    PaymentPlan,
    PaymentPlanMode,
)
from models.payment_schedule import RowKind, RowStatus
from services.payment_schedule_service import (
    compute_deposit_minor,
    effective_mode,
    generate_rows,
)

NOW = datetime(2026, 7, 4, 10, 0, tzinfo=timezone.utc)
START_FAR = (NOW + timedelta(days=90)).isoformat()     # ritiro tra 90 giorni
START_NEAR = (NOW + timedelta(days=10)).isoformat()    # tra 10 giorni (< 30)


def plan(mode=PaymentPlanMode.DEPOSIT_BALANCE, **kw) -> PaymentPlan:
    return PaymentPlan(mode=mode, **kw)


# Totali "cattivi" per gli arrotondamenti: dispari, primi, con resto su 3/6.
TRICKY_TOTALS = [100, 999, 9999, 10000, 33333, 50050, 129900, 7, 101, 149999]


class TestSumInvariant:
    @pytest.mark.parametrize("total", TRICKY_TOTALS)
    @pytest.mark.parametrize("mode", list(PaymentPlanMode))
    def test_sum_of_rows_equals_total(self, total, mode):
        p = plan(mode=mode)
        rows, _ = generate_rows(p, total, START_FAR, now=NOW)
        assert sum(r.amount_minor for r in rows) == total

    @pytest.mark.parametrize("total", TRICKY_TOTALS)
    @pytest.mark.parametrize("pct", [10, 30, 33, 50, 90])
    def test_sum_invariant_all_percentages(self, total, pct):
        p = plan(deposit_value=pct)
        rows, _ = generate_rows(p, total, START_FAR, now=NOW)
        assert sum(r.amount_minor for r in rows) == total

    @pytest.mark.parametrize("total", TRICKY_TOTALS)
    @pytest.mark.parametrize("n", [2, 3, 4, 5, 6])
    def test_sum_invariant_installments(self, total, n):
        p = plan(mode=PaymentPlanMode.DEPOSIT_INSTALLMENTS, installments_count=n)
        rows, _ = generate_rows(p, total, START_FAR, now=NOW)
        assert sum(r.amount_minor for r in rows) == total

    def test_no_zero_amount_rows_ever(self):
        # 7 centesimi in 6 rate: il motore non deve MAI produrre righe da 0.
        p = plan(mode=PaymentPlanMode.DEPOSIT_INSTALLMENTS, installments_count=6,
                 deposit_type=DepositType.FIXED, deposit_value=5)
        rows, _ = generate_rows(p, 7, START_FAR, now=NOW)
        assert all(r.amount_minor > 0 for r in rows)
        assert sum(r.amount_minor for r in rows) == 7


class TestDeposit:
    def test_percent_half_up(self):
        # 30% di 99,99€ = 29,997 → 30,00 (half-up)
        assert compute_deposit_minor(plan(), 9999) == 3000

    def test_fixed_deposit(self):
        p = plan(deposit_type=DepositType.FIXED, deposit_value=15000)
        assert compute_deposit_minor(p, 80000) == 15000

    def test_fixed_deposit_cannot_swallow_total(self):
        # caparra fissa 150€ su totale 100€ → clampata a total-1
        p = plan(deposit_type=DepositType.FIXED, deposit_value=15000)
        assert compute_deposit_minor(p, 10000) == 9999

    def test_deposit_row_due_now_balance_at_deadline(self):
        p = plan(balance_due_days_before=30)
        rows, _ = generate_rows(p, 80000, START_FAR, now=NOW)
        assert rows[0].kind == RowKind.DEPOSIT and rows[0].due_at == NOW.isoformat()
        expected_deadline = (NOW + timedelta(days=90) - timedelta(days=30)).isoformat()
        assert rows[1].kind == RowKind.BALANCE and rows[1].due_at == expected_deadline


class TestLastMinuteCollapse:
    def test_collapses_to_full_within_deadline(self):
        rows, collapsed = generate_rows(plan(), 50000, START_NEAR, now=NOW)
        assert collapsed is True
        assert len(rows) == 1 and rows[0].kind == RowKind.FULL
        assert rows[0].amount_minor == 50000

    def test_boundary_exactly_at_deadline_collapses(self):
        start = (NOW + timedelta(days=30)).isoformat()   # deadline == now
        rows, collapsed = generate_rows(plan(balance_due_days_before=30),
                                        50000, start, now=NOW)
        assert collapsed is True and len(rows) == 1

    def test_no_collapse_one_day_before_deadline(self):
        start = (NOW + timedelta(days=31)).isoformat()
        rows, collapsed = generate_rows(plan(balance_due_days_before=30),
                                        50000, start, now=NOW)
        assert collapsed is False and len(rows) == 2

    def test_full_mode_never_flagged_as_collapsed(self):
        rows, collapsed = generate_rows(plan(mode=PaymentPlanMode.FULL),
                                        50000, START_NEAR, now=NOW)
        assert collapsed is False and rows[0].kind == RowKind.FULL


class TestInstallments:
    def test_remainder_goes_to_first_installments(self):
        # saldo 100 centesimi in 3 rate → 34, 33, 33 (resto alle prime)
        p = plan(mode=PaymentPlanMode.DEPOSIT_INSTALLMENTS, installments_count=3,
                 deposit_type=DepositType.FIXED, deposit_value=900)
        rows, _ = generate_rows(p, 1000, START_FAR, now=NOW)
        amounts = [r.amount_minor for r in rows if r.kind == RowKind.INSTALLMENT]
        assert amounts == [34, 33, 33]

    def test_due_dates_ordered_and_within_deadline(self):
        p = plan(mode=PaymentPlanMode.DEPOSIT_INSTALLMENTS, installments_count=4)
        rows, _ = generate_rows(p, 120000, START_FAR, now=NOW)
        installments = [r for r in rows if r.kind == RowKind.INSTALLMENT]
        dues = [r.due_at for r in installments]
        assert dues == sorted(dues)
        deadline = NOW + timedelta(days=60)   # 90 - 30
        assert all(datetime.fromisoformat(d) <= deadline for d in dues)

    def test_labels_are_human(self):
        p = plan(mode=PaymentPlanMode.DEPOSIT_INSTALLMENTS, installments_count=2)
        rows, _ = generate_rows(p, 60000, START_FAR, now=NOW)
        assert [r.label for r in rows] == ["Caparra", "Rata 1 di 2", "Rata 2 di 2"]


class TestPolicy:
    def test_refund_percent_tiers(self):
        p = plan()  # default: 100@60 / 50@30 / 0@0
        assert p.refund_percent_at(61) == 100
        assert p.refund_percent_at(60) == 100
        assert p.refund_percent_at(45) == 50
        assert p.refund_percent_at(30) == 50
        assert p.refund_percent_at(5) == 0
        assert p.refund_percent_at(-1) == 0

    def test_policy_validation_rejects_increasing_refund(self):
        with pytest.raises(ValueError):
            PaymentPlan(cancellation_policy=[
                CancellationTier(days_before=60, refund_percent=50),
                CancellationTier(days_before=30, refund_percent=100),
            ])

    def test_policy_validation_rejects_unsorted_days(self):
        with pytest.raises(ValueError):
            PaymentPlan(cancellation_policy=[
                CancellationTier(days_before=30, refund_percent=100),
                CancellationTier(days_before=60, refund_percent=50),
            ])


class TestInputGuards:
    def test_rejects_non_positive_total(self):
        with pytest.raises(ValueError):
            generate_rows(plan(), 0, START_FAR, now=NOW)

    def test_effective_mode_full_passthrough(self):
        start = datetime.fromisoformat(START_FAR)
        assert effective_mode(plan(mode=PaymentPlanMode.FULL), start, NOW) \
            == PaymentPlanMode.FULL
