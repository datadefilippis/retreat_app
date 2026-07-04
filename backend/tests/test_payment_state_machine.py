"""Suite del denaro — macchina a stati + tracciabilità (Fase 2, S1).

Ogni transizione: (1) valida contro ALLOWED_TRANSITIONS, (2) ricalcola i
totali DAI FATTI, (3) appende un PaymentEvent. Le collection Mongo sono
fake in-memory: qui si testa la logica, non il driver.
"""

import os
import sys
from pathlib import Path
from unittest.mock import patch

BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-not-for-production")
os.environ.setdefault("MONGO_URL", "mongodb://localhost:27017")
os.environ.setdefault("DB_NAME", "test_db")

import pytest

from models.payment_plan import PaymentPlan, PaymentPlanMode
from models.payment_schedule import (
    ALLOWED_TRANSITIONS,
    PaymentSchedule,
    RowStatus,
    compute_totals,
    derive_payment_state,
)
from services import payment_schedule_service as svc
from services.payment_schedule_service import (
    InvalidTransition,
    apply_row_transition,
    create_schedule_for_order,
)

NOW_START = "2026-10-01T10:00:00+00:00"


class FakeUpdateResult:
    def __init__(self, modified: int):
        self.modified_count = modified


class FakeCollection:
    """Il minimo indispensabile di Motor per questi test: insert_one +
    update_one con il predicato $elemMatch usato dalla guardia ottimistica."""

    def __init__(self):
        self.docs = []

    async def insert_one(self, doc):
        self.docs.append(dict(doc))

    async def update_one(self, query, update):
        for doc in self.docs:
            if doc.get("id") != query.get("id"):
                continue
            elem = query.get("rows", {}).get("$elemMatch")
            if elem is not None:
                match = any(
                    r.get("seq") == elem["seq"] and r.get("status") == elem["status"]
                    for r in doc.get("rows", [])
                )
                if not match:
                    return FakeUpdateResult(0)
            doc.update(update.get("$set", {}))
            return FakeUpdateResult(1)
        return FakeUpdateResult(0)


@pytest.fixture()
def fake_db():
    schedules, events = FakeCollection(), FakeCollection()
    with patch.object(svc, "_collections", return_value=(schedules, events)):
        yield schedules, events


async def make_schedule(fake_db, mode=PaymentPlanMode.DEPOSIT_BALANCE,
                        total=100000) -> dict:
    schedules, _ = fake_db
    await create_schedule_for_order(
        order_id="ord_1", organization_id="org_1", occurrence_id="occ_1",
        plan=PaymentPlan(mode=mode), total_minor=total, start_at=NOW_START,
    )
    return schedules.docs[0]


class TestCreateSchedule:
    @pytest.mark.asyncio
    async def test_creation_persists_and_logs_event(self, fake_db):
        schedules, events = fake_db
        doc = await make_schedule(fake_db)
        assert doc["totals"]["due_minor"] == 100000
        assert doc["payment_state"] == "none"
        assert len(events.docs) == 1
        ev = events.docs[0]
        assert ev["action"] == "schedule_created"
        assert ev["amount_minor"] == 100000
        assert ev["detail"]["rows"][0]["kind"] == "deposit"

    @pytest.mark.asyncio
    async def test_plan_snapshot_frozen(self, fake_db):
        plan = PaymentPlan()
        schedules, _ = fake_db
        await create_schedule_for_order(
            order_id="o", organization_id="org", occurrence_id=None,
            plan=plan, total_minor=5000, start_at=NOW_START,
        )
        plan.deposit_value = 77   # mutazione POST-prenotazione
        assert schedules.docs[0]["plan_snapshot"]["deposit_value"] == 30


class TestTransitions:
    @pytest.mark.asyncio
    async def test_happy_path_deposit_then_balance(self, fake_db):
        schedules, events = fake_db
        doc = await make_schedule(fake_db)
        doc = await apply_row_transition(
            doc, 0, RowStatus.PAID, actor="webhook:stripe",
            row_updates={"stripe_payment_intent": "pi_123", "fee_minor": 1500},
        )
        assert doc["payment_state"] == "deposit_paid"
        assert doc["totals"]["paid_minor"] == 30000
        assert doc["totals"]["fee_minor"] == 1500
        doc = await apply_row_transition(doc, 1, RowStatus.PAID, actor="webhook:stripe")
        assert doc["payment_state"] == "fully_paid"
        assert doc["totals"]["paid_minor"] == 100000
        # tracciabilità: 1 created + 2 transizioni
        assert [e["action"] for e in events.docs] == \
            ["schedule_created", "row_paid", "row_paid"]
        assert events.docs[1]["from_status"] == "pending"
        assert events.docs[1]["actor"] == "webhook:stripe"

    @pytest.mark.asyncio
    async def test_paid_manual_records_note_and_state(self, fake_db):
        doc = await make_schedule(fake_db)
        doc = await apply_row_transition(
            doc, 0, RowStatus.PAID_MANUAL, actor="operator:user_9",
            row_updates={"manual_note": "bonifico ricevuto 4/7"},
        )
        row = doc["rows"][0]
        assert row["manual_note"] == "bonifico ricevuto 4/7"
        assert row["paid_at"] is not None
        assert doc["payment_state"] == "deposit_paid"

    @pytest.mark.asyncio
    async def test_illegal_transition_rejected(self, fake_db):
        doc = await make_schedule(fake_db)
        doc = await apply_row_transition(doc, 0, RowStatus.PAID, actor="webhook:stripe")
        with pytest.raises(InvalidTransition):
            await apply_row_transition(doc, 0, RowStatus.PENDING, actor="operator:x")

    @pytest.mark.asyncio
    async def test_terminal_states_are_terminal(self):
        assert ALLOWED_TRANSITIONS[RowStatus.REFUNDED] == set()
        assert ALLOWED_TRANSITIONS[RowStatus.CANCELLED] == set()

    @pytest.mark.asyncio
    async def test_concurrency_guard_double_webhook(self, fake_db):
        """Webhook doppio: il secondo apply parte dallo stesso doc stale →
        la guardia $elemMatch non matcha più e la transizione viene rifiutata
        SENZA doppio evento."""
        schedules, events = fake_db
        doc = await make_schedule(fake_db)
        stale_copy = dict(doc)
        await apply_row_transition(doc, 0, RowStatus.PAID, actor="webhook:stripe")
        with pytest.raises(InvalidTransition):
            await apply_row_transition(stale_copy, 0, RowStatus.PAID,
                                       actor="webhook:stripe")
        paid_events = [e for e in events.docs if e["action"] == "row_paid"]
        assert len(paid_events) == 1

    @pytest.mark.asyncio
    async def test_dunning_path_overdue_at_risk_then_recovery(self, fake_db):
        doc = await make_schedule(fake_db)
        doc = await apply_row_transition(doc, 0, RowStatus.PAID, actor="webhook:stripe")
        doc = await apply_row_transition(doc, 1, RowStatus.OVERDUE,
                                         actor="scheduler:payment-schedule-scan")
        doc = await apply_row_transition(doc, 1, RowStatus.AT_RISK,
                                         actor="scheduler:payment-schedule-scan")
        # il partecipante paga comunque dal link: recovery consentito
        doc = await apply_row_transition(doc, 1, RowStatus.PAID, actor="webhook:stripe")
        assert doc["payment_state"] == "fully_paid"

    @pytest.mark.asyncio
    async def test_waived_balance_makes_order_fully_paid(self, fake_db):
        doc = await make_schedule(fake_db)
        doc = await apply_row_transition(doc, 0, RowStatus.PAID, actor="webhook:stripe")
        doc = await apply_row_transition(doc, 1, RowStatus.WAIVED,
                                         actor="operator:user_9",
                                         detail={"reason": "sconto concordato"})
        assert doc["payment_state"] == "fully_paid"
        assert doc["totals"]["paid_minor"] == 30000   # il condono NON è incasso


class TestDerivedState:
    def test_full_mode_single_payment(self):
        plan = PaymentPlan(mode=PaymentPlanMode.FULL)
        from services.payment_schedule_service import generate_rows
        rows, _ = generate_rows(plan, 5000, NOW_START)
        assert derive_payment_state(rows) == "none"
        rows[0].status = RowStatus.PAID
        assert derive_payment_state(rows) == "fully_paid"

    def test_totals_never_negative(self):
        plan = PaymentPlan()
        from services.payment_schedule_service import generate_rows
        rows, _ = generate_rows(plan, 100, NOW_START)
        t = compute_totals(rows)
        assert t.paid_minor == 0 and t.due_minor == 100
