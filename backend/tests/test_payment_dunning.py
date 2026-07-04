"""Fase 2 S3 — planner dunning (puro) + write-ahead (integrazione Mongo)."""

import os, sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-not-for-production")
os.environ.setdefault("MONGO_URL", "mongodb://localhost:27017")
os.environ.setdefault("DB_NAME", "test_db")

import pytest

from services.payment_dunning_service import plan_dunning_actions

NOW = datetime(2026, 8, 1, 12, 0, tzinfo=timezone.utc)


def row(seq, kind, status, due_days_from_now, sent=()):
    return {
        "seq": seq, "kind": kind, "status": status,
        "amount_minor": 56000,
        "due_at": (NOW + timedelta(days=due_days_from_now)).isoformat(),
        "reminders_sent": [{"kind": k, "at": "x"} for k in sent],
    }


def sched(*rows):
    return {"rows": list(rows)}


def types(actions):
    return [a["type"] for a in actions]


class TestPlanner:
    def test_draft_and_cancelled_orders_skipped(self):
        s = sched(row(1, "balance", "pending", -10))
        assert plan_dunning_actions(s, "draft", NOW) == []
        assert plan_dunning_actions(s, "cancelled", NOW) == []
        assert plan_dunning_actions(s, None, NOW) == []

    def test_deposit_rows_never_dunned(self):
        s = sched(row(0, "deposit", "pending", -10))
        assert plan_dunning_actions(s, "confirmed", NOW) == []

    def test_paid_and_terminal_rows_skipped(self):
        s = sched(row(1, "balance", "paid", -10),
                  row(2, "installment", "waived", -10),
                  row(3, "installment", "at_risk", -10))
        assert plan_dunning_actions(s, "confirmed", NOW) == []

    def test_t7_window(self):
        s = sched(row(1, "balance", "pending", 5))
        assert types(plan_dunning_actions(s, "confirmed", NOW)) == ["remind_t7"]
        # oltre 7 giorni: nulla
        s2 = sched(row(1, "balance", "pending", 12))
        assert plan_dunning_actions(s2, "confirmed", NOW) == []
        # già mandato: nulla
        s3 = sched(row(1, "balance", "pending", 5, sent=("t-7",)))
        assert plan_dunning_actions(s3, "confirmed", NOW) == []

    def test_due_today_t0_and_overdue_mark(self):
        s = sched(row(1, "balance", "pending", -0.2, sent=("t-7",)))
        assert types(plan_dunning_actions(s, "confirmed", NOW)) == \
            ["remind_t0", "mark_overdue"]

    def test_overdue_3_days_sollecito(self):
        s = sched(row(1, "balance", "overdue", -4, sent=("t-7", "t-0")))
        assert types(plan_dunning_actions(s, "confirmed", NOW)) == ["sollecito_t3"]

    def test_overdue_7_days_at_risk(self):
        s = sched(row(1, "balance", "overdue", -8, sent=("t-7", "t-0", "t+3")))
        assert types(plan_dunning_actions(s, "confirmed", NOW)) == ["at_risk_t7"]

    def test_full_sequence_from_scratch_when_never_reminded(self):
        # riga mai toccata scoperta a T+8: recupera t-0, overdue, t+3, t+7
        s = sched(row(1, "balance", "pending", -8))
        assert types(plan_dunning_actions(s, "confirmed", NOW)) == \
            ["remind_t0", "mark_overdue", "sollecito_t3", "at_risk_t7"]

    def test_installments_multiple_rows_independent(self):
        s = sched(
            row(1, "installment", "paid", -30),
            row(2, "installment", "pending", 3),
            row(3, "installment", "pending", 40),
        )
        acts = plan_dunning_actions(s, "confirmed", NOW)
        assert types(acts) == ["remind_t7"] and acts[0]["row_seq"] == 2


def _mongo_reachable() -> bool:
    try:
        from pymongo import MongoClient
        MongoClient(os.environ["MONGO_URL"],
                    serverSelectionTimeoutMS=500).admin.command("ping")
        return True
    except Exception:
        return False


@pytest.mark.skipif(not _mongo_reachable(), reason="Mongo non raggiungibile")
class TestWriteAhead:
    @pytest.mark.asyncio
    async def test_mark_reminder_sent_wins_once(self):
        """Il mark write-ahead è atomico: due chiamate → una sola vince."""
        from unittest.mock import patch
        from motor.motor_asyncio import AsyncIOMotorClient
        import services.payment_dunning_service as dun

        client = AsyncIOMotorClient(os.environ["MONGO_URL"])
        coll = client["retreat_scheduler_test"]["payment_schedules"]
        await coll.delete_many({})
        await coll.insert_one({
            "id": "sch_wa", "rows": [
                {"seq": 1, "reminders_sent": []},
            ],
        })

        class FakeDB:
            payment_schedules = coll

        with patch("database.db", FakeDB):
            first = await dun._mark_reminder_sent("sch_wa", 1, "t-7")
            second = await dun._mark_reminder_sent("sch_wa", 1, "t-7")
            other = await dun._mark_reminder_sent("sch_wa", 1, "t-0")
        assert first is True and second is False and other is True
        doc = await coll.find_one({"id": "sch_wa"})
        kinds = [m["kind"] for m in doc["rows"][0]["reminders_sent"]]
        assert kinds == ["t-7", "t-0"]
        await coll.delete_many({})
        client.close()
