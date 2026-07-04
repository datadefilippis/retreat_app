"""Fase 4 — planner comunicazioni pre/post ritiro (puro) + write-ahead."""

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

from services.event_comms_service import plan_event_comms

NOW = datetime(2026, 9, 1, 12, 0, tzinfo=timezone.utc)


def occ(status="published", start_days=+5, end_days=None, sent=()):
    o = {
        "status": status,
        "start_at": (NOW + timedelta(days=start_days)).isoformat(),
        "comms_sent": [{"kind": k, "at": "x"} for k in sent],
    }
    if end_days is not None:
        o["end_at"] = (NOW + timedelta(days=end_days)).isoformat()
    return o


def kinds(actions):
    return [a["kind"] for a in actions]


class TestPlanner:
    def test_draft_and_cancelled_never(self):
        assert plan_event_comms(occ(status="draft", start_days=3), NOW) == []
        assert plan_event_comms(occ(status="cancelled", start_days=3), NOW) == []

    def test_t7_window(self):
        assert kinds(plan_event_comms(occ(start_days=5), NOW)) == ["t-7"]
        assert plan_event_comms(occ(start_days=10), NOW) == []
        assert plan_event_comms(occ(start_days=5, sent=("t-7",)), NOW) == []

    def test_t1_and_t7_together_when_late_discovery(self):
        # ritiro scoperto a T-0.5 (mai processato): partono entrambe
        assert kinds(plan_event_comms(occ(start_days=0.5), NOW)) == ["t-7", "t-1"]

    def test_no_pre_event_after_start(self):
        # iniziato ieri, finisce domani: niente t-7/t-1 (finestra chiusa a 0)
        assert plan_event_comms(occ(start_days=-1, end_days=+1), NOW) == []

    def test_followup_after_end(self):
        # finito 3 giorni fa → t+2 dovuta
        acts = plan_event_comms(occ(start_days=-5, end_days=-3), NOW)
        assert kinds(acts) == ["t+2"] and acts[0]["template"] == "followup"

    def test_followup_uses_start_when_no_end(self):
        assert kinds(plan_event_comms(occ(start_days=-3), NOW)) == ["t+2"]

    def test_followup_not_too_late(self):
        # finito 10 giorni fa: un grazie tardivo è peggio di niente
        assert plan_event_comms(occ(start_days=-12, end_days=-10), NOW) == []

    def test_followup_works_for_closed_events(self):
        acts = plan_event_comms(occ(status="closed", start_days=-5, end_days=-3), NOW)
        assert kinds(acts) == ["t+2"]

    def test_closed_events_no_pre_reminders(self):
        # chiuso alle vendite ma non ancora iniziato: niente reminder
        # automatici (potrebbe essere chiuso per motivi organizzativi)
        assert plan_event_comms(occ(status="closed", start_days=5), NOW) == []

    def test_invalid_dates_safe(self):
        assert plan_event_comms({"status": "published", "start_at": "boom"}, NOW) == []


def _mongo_reachable():
    try:
        from pymongo import MongoClient
        MongoClient(os.environ["MONGO_URL"], serverSelectionTimeoutMS=500).admin.command("ping")
        return True
    except Exception:
        return False


@pytest.mark.skipif(not _mongo_reachable(), reason="Mongo non raggiungibile")
class TestWriteAhead:
    @pytest.mark.asyncio
    async def test_mark_comms_sent_wins_once(self):
        from unittest.mock import patch
        from motor.motor_asyncio import AsyncIOMotorClient
        import services.event_comms_service as svc

        client = AsyncIOMotorClient(os.environ["MONGO_URL"])
        coll = client["retreat_scheduler_test"]["event_occurrences"]
        await coll.delete_many({})
        await coll.insert_one({"id": "occ_wa", "organization_id": "org",
                               "comms_sent": []})
        with patch("database.event_occurrences_collection", coll):
            first = await svc._mark_comms_sent("occ_wa", "org", "t-7")
            second = await svc._mark_comms_sent("occ_wa", "org", "t-7")
            other = await svc._mark_comms_sent("occ_wa", "org", "t-1")
        assert first is True and second is False and other is True
        await coll.delete_many({})
        client.close()
