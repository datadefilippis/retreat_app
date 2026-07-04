"""Fase 2 S3 — suite del denaro: rimborsi e cascata (2.11-2.13)."""

import os, sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import AsyncMock, patch

BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-not-for-production")
os.environ.setdefault("MONGO_URL", "mongodb://localhost:27017")
os.environ.setdefault("DB_NAME", "test_db")

import pytest

from services.payment_refund_service import (
    compute_policy_refund,
    plan_refund_distribution,
)

NOW = datetime(2026, 8, 1, 12, 0, tzinfo=timezone.utc)

PLAN = {
    "mode": "deposit_balance", "deposit_type": "percent", "deposit_value": 30,
    "balance_due_days_before": 30, "installments_count": 3,
    "cancellation_policy": [
        {"days_before": 60, "refund_percent": 100},
        {"days_before": 30, "refund_percent": 50},
        {"days_before": 0, "refund_percent": 0},
    ],
}


def sched(rows):
    return {"plan_snapshot": PLAN, "rows": rows}


def paid_row(seq, amount, status="paid", pi=None):
    return {"seq": seq, "amount_minor": amount, "status": status,
            "stripe_payment_intent": pi or f"pi_{seq}"}


class TestPolicyRefund:
    def test_full_refund_far_from_start(self):
        s = sched([paid_row(0, 24000)])
        start = (NOW + timedelta(days=90)).isoformat()
        r = compute_policy_refund(s, start, now=NOW)
        assert r["policy_percent"] == 100 and r["refundable_minor"] == 24000

    def test_half_refund_45_days(self):
        s = sched([paid_row(0, 24000), paid_row(1, 56000)])
        start = (NOW + timedelta(days=45)).isoformat()
        r = compute_policy_refund(s, start, now=NOW)
        assert r["paid_minor"] == 80000
        assert r["policy_percent"] == 50 and r["refundable_minor"] == 40000

    def test_zero_refund_close_to_start(self):
        s = sched([paid_row(0, 24000)])
        start = (NOW + timedelta(days=5)).isoformat()
        r = compute_policy_refund(s, start, now=NOW)
        assert r["policy_percent"] == 0 and r["refundable_minor"] == 0

    def test_unknown_start_worst_tier(self):
        s = sched([paid_row(0, 24000)])
        r = compute_policy_refund(s, None, now=NOW)
        assert r["refundable_minor"] == 0   # serve override esplicito

    def test_unpaid_rows_not_counted(self):
        s = sched([paid_row(0, 24000),
                   {"seq": 1, "amount_minor": 56000, "status": "pending"}])
        start = (NOW + timedelta(days=90)).isoformat()
        assert compute_policy_refund(s, start, now=NOW)["paid_minor"] == 24000


class TestDistribution:
    def test_reverse_order_last_payment_first(self):
        rows = [paid_row(0, 24000), paid_row(1, 56000)]
        dist = plan_refund_distribution(rows, 60000)
        assert [(d["row_seq"], d["amount_minor"]) for d in dist] == \
            [(1, 56000), (0, 4000)]   # saldo intero + caparra parziale

    def test_partial_single_row(self):
        rows = [paid_row(0, 24000), paid_row(1, 56000)]
        dist = plan_refund_distribution(rows, 40000)
        assert [(d["row_seq"], d["amount_minor"]) for d in dist] == [(1, 40000)]

    def test_manual_rows_flagged(self):
        rows = [paid_row(0, 24000),
                paid_row(1, 56000, status="paid_manual", pi=None)]
        dist = plan_refund_distribution(rows, 80000)
        assert dist[0]["channel"] == "manual"      # riga 1 (bonifico)
        assert dist[1]["channel"] == "stripe"

    def test_zero_refund_empty(self):
        assert plan_refund_distribution([paid_row(0, 24000)], 0) == []

    def test_never_exceeds_paid(self):
        rows = [paid_row(0, 24000)]
        dist = plan_refund_distribution(rows, 99999999)
        assert sum(d["amount_minor"] for d in dist) == 24000


class TestRefundOrderOrchestration:
    """refund_order con Stripe e collections fakes: transizioni, eventi,
    canali, cascata annullo righe pendenti."""

    @pytest.mark.asyncio
    async def test_full_cascade_mixed_channels(self):
        from services import payment_refund_service as svc_r
        from services import payment_schedule_service as svc_s
        from tests.test_payment_state_machine import FakeCollection

        schedules, events = FakeCollection(), FakeCollection()
        start = (NOW + timedelta(days=90)).isoformat()
        schedule_doc = {
            "id": "sch_1", "order_id": "ord_1", "organization_id": "org_1",
            "occurrence_id": "occ_1", "currency": "EUR",
            "plan_snapshot": PLAN, "collapsed_last_minute": False,
            "payment_state": "deposit_paid",
            "created_at": "x", "updated_at": "x",
            "totals": {"due_minor": 80000, "paid_minor": 24000,
                       "refunded_minor": 0, "fee_minor": 0},
            "rows": [
                {"seq": 0, "kind": "deposit", "label": "Caparra",
                 "amount_minor": 24000, "due_at": NOW.isoformat(),
                 "status": "paid", "stripe_payment_intent": "pi_dep",
                 "paid_at": "x", "fee_minor": 0, "reminders_sent": [],
                 "pay_token": "tok0"},
                {"seq": 1, "kind": "balance", "label": "Saldo",
                 "amount_minor": 56000, "due_at": start,
                 "status": "pending", "fee_minor": 0, "reminders_sent": [],
                 "pay_token": "tok1"},
            ],
        }
        schedules.docs.append(schedule_doc)

        async def fake_find_one(query, projection=None):
            return dict(schedules.docs[0])
        schedules.find_one = fake_find_one

        stripe_calls = []
        async def fake_stripe_refund(pi, amount, acct, idempotency_key):
            stripe_calls.append((pi, amount, idempotency_key))
            return "re_test"

        class FakeOrders:
            async def find_one(self, q, p=None):
                return {"id": "ord_1", "status": "confirmed"}
            async def update_one(self, q, u):
                class R: modified_count = 1
                return R()
        class FakeOcc:
            async def find_one(self, q, p=None):
                return {"start_at": start}

        cancel_calls = []
        async def fake_cancel(org_id, order_id):
            cancel_calls.append(order_id)
            return {}

        with patch.object(svc_s, "_collections", return_value=(schedules, events)), \
             patch.object(svc_r, "_stripe_refund", fake_stripe_refund), \
             patch.object(svc_r, "_connected_account_for_org",
                          AsyncMock(return_value="acct_x")), \
             patch("database.orders_collection", FakeOrders()), \
             patch("database.event_occurrences_collection", FakeOcc()), \
             patch("services.order_service.cancel_order", fake_cancel):
            result = await svc_r.refund_order(
                "org_1", "ord_1", actor="operator:u1",
                reason="rinuncia partecipante", now=NOW)

        # policy 100% (90 giorni prima): rimborso pieno caparra via Stripe
        assert result["basis"] == "policy"
        assert result["refunded_stripe_minor"] == 24000
        assert stripe_calls == [("pi_dep", 24000, "refund:ord_1:0")]
        # riga 0 refunded, riga 1 (mai pagata) cancelled
        doc = schedules.docs[0]
        assert doc["rows"][0]["status"] == "refunded"
        assert doc["rows"][0]["refund"]["amount_minor"] == 24000
        assert doc["rows"][1]["status"] == "cancelled"
        # ordine annullato con la cascata esistente
        assert cancel_calls == ["ord_1"]
        # tracciabilità
        actions = [e["action"] for e in events.docs]
        assert "row_refunded" in actions and "row_cancelled" in actions

    @pytest.mark.asyncio
    async def test_override_requires_reason(self):
        from services import payment_refund_service as svc_r
        from services import payment_schedule_service as svc_s
        from tests.test_payment_state_machine import FakeCollection
        schedules, events = FakeCollection(), FakeCollection()
        schedules.docs.append({"id": "s", "order_id": "o",
                               "organization_id": "org",
                               "plan_snapshot": PLAN, "rows": [],
                               "occurrence_id": None})
        async def fake_find_one(q, p=None): return dict(schedules.docs[0])
        schedules.find_one = fake_find_one
        class FakeOrders:
            async def find_one(self, q, p=None): return {"id": "o"}
        with patch.object(svc_s, "_collections", return_value=(schedules, events)), \
             patch("database.orders_collection", FakeOrders()), \
             patch("database.event_occurrences_collection", FakeOrders()):
            with pytest.raises(ValueError, match="motivo"):
                await svc_r.refund_order("org", "o", actor="op", reason="",
                                         override_amount_minor=1000)
