"""WS-1.1 consolidamento — settle_order_manual (caso bonifico esterno)."""

import os, sys
from pathlib import Path
from unittest.mock import AsyncMock, patch

BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-not-for-production")
os.environ.setdefault("MONGO_URL", "mongodb://localhost:27017")
os.environ.setdefault("DB_NAME", "test_db")

import pytest

from services.commerce_rules import get_order_actions


class TestActionRules:
    def test_draft_storefront_bonifico_has_exit(self):
        """Il caso limbo: draft con pagamento richiesto → settle_manual
        DEVE essere disponibile (prima non c'era via d'uscita)."""
        actions = get_order_actions({"status": "draft",
                                     "payment_intent": "required"})
        assert actions["settle_manual"]["allowed"] is True
        assert actions["confirm"]["allowed"] is False   # invariato

    def test_manual_draft_has_settle_too(self):
        actions = get_order_actions({"status": "draft",
                                     "payment_intent": "none"})
        assert actions["settle_manual"]["allowed"] is True

    def test_confirmed_order_no_settle_button(self):
        # sugli ordini confermati si usano mark_paid / le azioni per-riga
        actions = get_order_actions({"status": "confirmed",
                                     "payment_intent": "collected",
                                     "payment_status": "pending"})
        assert actions["settle_manual"]["allowed"] is False


class TestSettleOrchestration:
    @pytest.mark.asyncio
    async def test_full_settle_confirms_and_pays_everything(self):
        from services import order_service as osvc
        from services import payment_schedule_service as psvc
        from tests.test_payment_state_machine import FakeCollection

        order_doc = {"id": "o1", "status": "draft",
                     "payment_intent": "required", "payment_status": "pending"}
        updates_log = []

        async def fake_find(order_id, org_id):
            return dict(order_doc)
        async def fake_update(order_id, org_id, updates):
            updates_log.append(updates); order_doc.update(updates); return True
        confirm_calls = []
        async def fake_confirm(org_id, order_id, skip_payment_check=False):
            confirm_calls.append(skip_payment_check)
            order_doc["status"] = "confirmed"
            return dict(order_doc)
        sync_calls = []
        async def fake_sync(org_id, order_id, status):
            sync_calls.append(status)

        schedules, events = FakeCollection(), FakeCollection()
        schedule_doc = {
            "id": "s1", "order_id": "o1", "organization_id": "org",
            "occurrence_id": "occ", "currency": "EUR",
            "plan_snapshot": {"mode": "deposit_balance", "deposit_type": "percent",
                              "deposit_value": 30, "balance_due_days_before": 30,
                              "installments_count": 3,
                              "cancellation_policy": [
                                  {"days_before": 0, "refund_percent": 0}]},
            "collapsed_last_minute": False, "payment_state": "none",
            "created_at": "x", "updated_at": "x",
            "totals": {"due_minor": 80000, "paid_minor": 0,
                       "refunded_minor": 0, "fee_minor": 0},
            "rows": [
                {"seq": 0, "kind": "deposit", "label": "Caparra",
                 "amount_minor": 24000, "due_at": "2026-07-04T00:00:00+00:00",
                 "status": "processing", "fee_minor": 0, "reminders_sent": [],
                 "pay_token": "t0"},
                {"seq": 1, "kind": "balance", "label": "Saldo",
                 "amount_minor": 56000, "due_at": "2026-09-02T00:00:00+00:00",
                 "status": "pending", "fee_minor": 0, "reminders_sent": [],
                 "pay_token": "t1"},
            ],
        }
        schedules.docs.append(schedule_doc)
        async def fake_sched_find(order_id, org_id):
            return dict(schedules.docs[0])

        with patch("repositories.order_repository.find_one", fake_find), \
             patch("repositories.order_repository.update", fake_update), \
             patch.object(osvc, "confirm_order", fake_confirm), \
             patch("services.payment_sync.sync_payment_to_sales", fake_sync), \
             patch.object(psvc, "_collections", return_value=(schedules, events)), \
             patch.object(psvc, "get_schedule_for_order", fake_sched_find):
            result = await osvc.settle_order_manual(
                "org", "o1", actor="operator:u1",
                note="bonifico ricevuto", scope="full")

        assert confirm_calls == [True]                 # confermato senza pagamento
        assert order_doc["payment_intent"] == "collected"
        assert order_doc["payment_status"] == "paid"
        assert sync_calls == ["paid"]
        doc = schedules.docs[0]
        assert [r["status"] for r in doc["rows"]] == ["paid_manual", "paid_manual"]
        assert doc["payment_state"] == "fully_paid"
        assert result["_settled_rows"] == [0, 1]

    @pytest.mark.asyncio
    async def test_deposit_scope_settles_only_first_row(self):
        from services import order_service as osvc
        from services import payment_schedule_service as psvc
        from tests.test_payment_state_machine import FakeCollection

        order_doc = {"id": "o2", "status": "draft",
                     "payment_intent": "required", "payment_status": "pending"}
        async def fake_find(order_id, org_id): return dict(order_doc)
        async def fake_update(order_id, org_id, updates):
            order_doc.update(updates); return True
        async def fake_confirm(org_id, order_id, skip_payment_check=False):
            order_doc["status"] = "confirmed"; return dict(order_doc)

        schedules, events = FakeCollection(), FakeCollection()
        schedules.docs.append({
            "id": "s2", "order_id": "o2", "organization_id": "org",
            "occurrence_id": "occ", "currency": "EUR",
            "plan_snapshot": {"mode": "deposit_balance", "deposit_type": "percent",
                              "deposit_value": 30, "balance_due_days_before": 30,
                              "installments_count": 3,
                              "cancellation_policy": [
                                  {"days_before": 0, "refund_percent": 0}]},
            "collapsed_last_minute": False, "payment_state": "none",
            "created_at": "x", "updated_at": "x",
            "totals": {"due_minor": 80000, "paid_minor": 0,
                       "refunded_minor": 0, "fee_minor": 0},
            "rows": [
                {"seq": 0, "kind": "deposit", "label": "Caparra",
                 "amount_minor": 24000, "due_at": "2026-07-04T00:00:00+00:00",
                 "status": "pending", "fee_minor": 0, "reminders_sent": [],
                 "pay_token": "t0"},
                {"seq": 1, "kind": "balance", "label": "Saldo",
                 "amount_minor": 56000, "due_at": "2026-09-02T00:00:00+00:00",
                 "status": "pending", "fee_minor": 0, "reminders_sent": [],
                 "pay_token": "t1"},
            ],
        })
        async def fake_sched_find(order_id, org_id):
            return dict(schedules.docs[0])

        with patch("repositories.order_repository.find_one", fake_find), \
             patch("repositories.order_repository.update", fake_update), \
             patch.object(osvc, "confirm_order", fake_confirm), \
             patch.object(psvc, "_collections", return_value=(schedules, events)), \
             patch.object(psvc, "get_schedule_for_order", fake_sched_find):
            result = await osvc.settle_order_manual(
                "org", "o2", actor="operator:u1",
                note="bonifico caparra", scope="deposit")

        doc = schedules.docs[0]
        assert doc["rows"][0]["status"] == "paid_manual"
        assert doc["rows"][1]["status"] == "pending"     # saldo → dunning normale
        assert doc["payment_state"] == "deposit_paid"
        assert order_doc.get("payment_status") != "paid"  # non tutto saldato
        assert result["_settled_rows"] == [0]

    @pytest.mark.asyncio
    async def test_note_required_and_cancelled_rejected(self):
        from services import order_service as osvc
        async def fake_find(order_id, org_id):
            return {"id": "o3", "status": "cancelled"}
        with patch("repositories.order_repository.find_one", fake_find):
            with pytest.raises(ValueError, match="nota"):
                await osvc.settle_order_manual("org", "o3", actor="a",
                                               note="  ", scope="full")
            with pytest.raises(ValueError, match="annullato"):
                await osvc.settle_order_manual("org", "o3", actor="a",
                                               note="x", scope="full")


class TestMarkPaidCoherence:
    """WS-1.4 — mark_paid/unpaid coerenti col libro mastro."""

    @pytest.mark.asyncio
    async def test_mark_paid_settles_open_schedule_rows(self):
        from services import order_service as osvc
        from services import payment_schedule_service as psvc
        from tests.test_payment_state_machine import FakeCollection

        order_doc = {"id": "o4", "status": "confirmed",
                     "payment_status": "pending"}
        async def fake_find(order_id, org_id): return dict(order_doc)
        async def fake_update(order_id, org_id, updates):
            order_doc.update(updates); return True
        async def fake_sync(org_id, order_id, status): pass

        schedules, events = FakeCollection(), FakeCollection()
        schedules.docs.append({
            "id": "s4", "order_id": "o4", "organization_id": "org",
            "occurrence_id": "occ", "currency": "EUR",
            "plan_snapshot": {"mode": "deposit_balance", "deposit_type": "percent",
                              "deposit_value": 30, "balance_due_days_before": 30,
                              "installments_count": 3,
                              "cancellation_policy": [
                                  {"days_before": 0, "refund_percent": 0}]},
            "collapsed_last_minute": False, "payment_state": "deposit_paid",
            "created_at": "x", "updated_at": "x",
            "totals": {"due_minor": 80000, "paid_minor": 24000,
                       "refunded_minor": 0, "fee_minor": 0},
            "rows": [
                {"seq": 0, "kind": "deposit", "label": "Caparra",
                 "amount_minor": 24000, "due_at": "2026-07-01T00:00:00+00:00",
                 "status": "paid", "paid_at": "x", "fee_minor": 0,
                 "reminders_sent": [], "pay_token": "t0"},
                {"seq": 1, "kind": "balance", "label": "Saldo",
                 "amount_minor": 56000, "due_at": "2026-09-02T00:00:00+00:00",
                 "status": "pending", "fee_minor": 0, "reminders_sent": [],
                 "pay_token": "t1"},
            ],
        })
        async def fake_sched_find(order_id, org_id):
            return dict(schedules.docs[0])

        with patch("repositories.order_repository.find_one", fake_find), \
             patch("repositories.order_repository.update", fake_update), \
             patch("services.payment_sync.sync_payment_to_sales", fake_sync), \
             patch.object(psvc, "_collections", return_value=(schedules, events)), \
             patch.object(psvc, "get_schedule_for_order", fake_sched_find):
            await osvc.mark_order_paid("org", "o4")

        doc = schedules.docs[0]
        assert doc["rows"][1]["status"] == "paid_manual"   # saldo chiuso
        assert doc["payment_state"] == "fully_paid"
        assert order_doc["payment_status"] == "paid"

    @pytest.mark.asyncio
    async def test_mark_unpaid_blocked_when_ledger_has_income(self):
        from services import order_service as osvc
        from services import payment_schedule_service as psvc

        order_doc = {"id": "o5", "status": "confirmed",
                     "payment_status": "paid"}
        async def fake_find(order_id, org_id): return dict(order_doc)
        async def fake_sched_find(order_id, org_id):
            return {"rows": [{"seq": 0, "status": "paid"}]}

        with patch("repositories.order_repository.find_one", fake_find), \
             patch.object(psvc, "get_schedule_for_order", fake_sched_find):
            with pytest.raises(ValueError, match="incassi registrati"):
                await osvc.mark_order_unpaid("org", "o5")
