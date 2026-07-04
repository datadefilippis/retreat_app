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
    async def test_s1_forcing_deposit_plan_becomes_full(self, fake_db):
        """FINCHÉ il checkout incassa tutto subito, il ledger dice 'full'
        anche se il prodotto configura la caparra — consistenza col reale.
        QUESTO TEST SI INVERTE IN S2 (checkout caparra)."""
        schedules, _ = fake_db
        ctx = dict(CTX, plan_raw={"mode": "deposit_balance", "deposit_value": 30})
        await create_schedule_for_new_order(ORDER, "org_1", ctx)
        doc = schedules.docs[0]
        assert doc["plan_snapshot"]["mode"] == "full"
        assert len(doc["rows"]) == 1

    @pytest.mark.asyncio
    async def test_invalid_plan_falls_back_to_full(self, fake_db):
        schedules, _ = fake_db
        ctx = dict(CTX, plan_raw={"mode": "deposit_balance", "deposit_value": 999})
        await create_schedule_for_new_order(ORDER, "org_1", ctx)
        assert schedules.docs[0]["plan_snapshot"]["mode"] == "full"
