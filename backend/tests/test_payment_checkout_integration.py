"""Fase 2 S1 task 2.4 — l'ordine-ritiro nasce col libro mastro.

Testa l'hook create_schedule_for_new_order chiamato da order_service dopo
l'insert: scoping (solo ordini-evento con totale), fallback su piani
invalidi, e il FORCING S1 a pagamento unico (il ledger riflette ciò che il
checkout fa davvero oggi; le modalità deposit si accendono in S2).
"""

import os, sys
from pathlib import Path
from unittest.mock import patch

BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-not-for-production")
os.environ.setdefault("MONGO_URL", "mongodb://localhost:27017")
os.environ.setdefault("DB_NAME", "test_db")

import pytest

from services import payment_schedule_service as svc
from services.payment_schedule_service import create_schedule_for_new_order
from tests.test_payment_state_machine import FakeCollection

ORDER = {"id": "ord_9", "total": 840.50, "currency": "EUR"}
CTX = {"occurrence_id": "occ_1", "start_at": "2026-10-01T10:00:00+00:00",
       "plan_raw": None}


@pytest.fixture()
def fake_db():
    schedules, events = FakeCollection(), FakeCollection()
    with patch.object(svc, "_collections", return_value=(schedules, events)):
        yield schedules, events


class TestCheckoutHook:
    @pytest.mark.asyncio
    async def test_no_event_ctx_no_schedule(self, fake_db):
        schedules, _ = fake_db
        assert await create_schedule_for_new_order(ORDER, "org_1", None) is None
        assert schedules.docs == []

    @pytest.mark.asyncio
    async def test_zero_total_no_schedule(self, fake_db):
        schedules, _ = fake_db
        order = dict(ORDER, total=0)   # richiesta di contatto
        assert await create_schedule_for_new_order(order, "org_1", CTX) is None
        assert schedules.docs == []

    @pytest.mark.asyncio
    async def test_default_full_single_row_total_in_minor(self, fake_db):
        schedules, events = fake_db
        s = await create_schedule_for_new_order(ORDER, "org_1", CTX)
        assert s is not None
        doc = schedules.docs[0]
        assert len(doc["rows"]) == 1
        assert doc["rows"][0]["amount_minor"] == 84050   # 840,50€ → minor units
        assert doc["organization_id"] == "org_1"
        assert doc["occurrence_id"] == "occ_1"
        assert events.docs[0]["action"] == "schedule_created"
        assert events.docs[0]["actor"] == "system:checkout"

    @pytest.mark.asyncio
    async def test_s2_deposit_plan_generates_real_deposit_rows(self, fake_db):
        """S2: forcing S1 rimosso — il piano caparra produce righe
        caparra+saldo REALI (il checkout addebita solo la caparra)."""
        schedules, _ = fake_db
        ctx = dict(CTX, plan_raw={"mode": "deposit_balance", "deposit_value": 30})
        await create_schedule_for_new_order(ORDER, "org_1", ctx)
        doc = schedules.docs[0]
        assert doc["plan_snapshot"]["mode"] == "deposit_balance"
        assert [r["kind"] for r in doc["rows"]] == ["deposit", "balance"]
        assert sum(r["amount_minor"] for r in doc["rows"]) == 84050

    @pytest.mark.asyncio
    async def test_invalid_plan_falls_back_to_full(self, fake_db):
        schedules, _ = fake_db
        ctx = dict(CTX, plan_raw={"mode": "deposit_balance", "deposit_value": 999})
        await create_schedule_for_new_order(ORDER, "org_1", ctx)
        assert schedules.docs[0]["plan_snapshot"]["mode"] == "full"


class TestS2DepositCheckout:
    """S2 — checkout schedule-aware e webhook idempotente."""

    @pytest.mark.asyncio
    async def test_pending_charge_row_deposit(self, fake_db):
        from services.payment_schedule_service import pending_charge_row
        schedules, _ = fake_db
        ctx = dict(CTX, plan_raw={"mode": "deposit_balance", "deposit_value": 30})
        await create_schedule_for_new_order(ORDER, "org_1", ctx)
        row = pending_charge_row(schedules.docs[0])
        assert row is not None and row["kind"] == "deposit" and row["seq"] == 0

    @pytest.mark.asyncio
    async def test_pending_charge_row_none_for_full_plan(self, fake_db):
        from services.payment_schedule_service import pending_charge_row
        schedules, _ = fake_db
        await create_schedule_for_new_order(ORDER, "org_1", CTX)  # full default
        assert pending_charge_row(schedules.docs[0]) is None
        assert pending_charge_row(None) is None

    @pytest.mark.asyncio
    async def test_webhook_pays_deposit_row_and_is_idempotent(self, fake_db):
        """Doppio webhook sulla stessa caparra: un solo incasso a libro,
        un solo evento row_paid — MAI doppio conteggio."""
        from services.payment_schedule_service import apply_stripe_payment_to_schedule
        schedules, events = fake_db
        ctx = dict(CTX, plan_raw={"mode": "deposit_balance", "deposit_value": 30})
        await create_schedule_for_new_order(ORDER, "org_1", ctx)

        # fake find_one per get_schedule_for_order
        async def find_one(query, projection=None):
            for d in schedules.docs:
                if d.get("order_id") == query.get("order_id"):
                    return d
            return None
        schedules.find_one = find_one

        s1 = await apply_stripe_payment_to_schedule(
            "ord_9", "org_1", 0,
            stripe_payment_intent="pi_test", stripe_session_id="cs_test")
        assert s1["payment_state"] == "deposit_paid"
        assert s1["rows"][0]["status"] == "paid"

        s2 = await apply_stripe_payment_to_schedule(
            "ord_9", "org_1", 0,
            stripe_payment_intent="pi_test", stripe_session_id="cs_test")
        paid_events = [e for e in events.docs if e["action"] == "row_paid"]
        assert len(paid_events) == 1
        assert s2 is not None  # nessuna eccezione, schedule invariato

    def test_below_minimum_deposit_collapses_to_full(self):
        from models.payment_plan import PaymentPlan, PaymentPlanMode
        from services.payment_schedule_service import generate_rows
        # 1% di 10,00€ = 10 cent < 50 → collasso a pagamento unico
        plan = PaymentPlan(mode=PaymentPlanMode.DEPOSIT_BALANCE, deposit_value=1)
        rows, collapsed = generate_rows(plan, 1000, CTX["start_at"])
        assert collapsed is True and len(rows) == 1
        assert rows[0].amount_minor == 1000
