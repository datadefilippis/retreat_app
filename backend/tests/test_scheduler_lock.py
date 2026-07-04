"""Scheduler — lock a lease su Mongo (Fase 2, S1).

Integrazione con Mongo REALE (localhost): il predicato atomico di
find_one_and_update è il cuore dell'esclusività e va provato sul driver
vero, non su un fake. In CI (nessun Mongo service) questi test skippano
con motivazione — girano in locale e sono richiesti per la DoD S1.
"""

import asyncio
import os
import sys
from datetime import timedelta
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-not-for-production")
os.environ.setdefault("MONGO_URL", "mongodb://localhost:27017")
os.environ.setdefault("DB_NAME", "test_db")

import pytest

from models.common import utc_now
from services.scheduler_service import (
    journal_end,
    journal_start,
    release_lock,
    try_acquire_lock,
)

LOCK = "job:test-lock"


def _mongo_reachable() -> bool:
    try:
        from pymongo import MongoClient
        MongoClient(os.environ["MONGO_URL"],
                    serverSelectionTimeoutMS=500).admin.command("ping")
        return True
    except Exception:
        return False


pytestmark = pytest.mark.skipif(
    not _mongo_reachable(),
    reason="Mongo non raggiungibile (CI senza service) — test lock solo in locale",
)


import pytest_asyncio


@pytest_asyncio.fixture()
async def locks():
    """Collection lock su un DB di test dedicato, pulita prima e dopo.
    Fixture async: il client Motor deve vivere sul loop del test."""
    from motor.motor_asyncio import AsyncIOMotorClient
    client = AsyncIOMotorClient(os.environ["MONGO_URL"])
    coll = client["retreat_scheduler_test"]["scheduler_locks"]
    await coll.delete_many({})
    yield coll
    await coll.delete_many({})
    client.close()


class TestLeaseLock:
    @pytest.mark.asyncio
    async def test_first_acquirer_wins_second_loses(self, locks):
        assert await try_acquire_lock(locks, LOCK, runner_id="runner-A") is True
        assert await try_acquire_lock(locks, LOCK, runner_id="runner-B") is False

    @pytest.mark.asyncio
    async def test_holder_can_renew_own_lease(self, locks):
        assert await try_acquire_lock(locks, LOCK, runner_id="runner-A") is True
        assert await try_acquire_lock(locks, LOCK, runner_id="runner-A") is True

    @pytest.mark.asyncio
    async def test_expired_lease_is_stolen(self, locks):
        past = utc_now() - timedelta(seconds=300)
        # runner-A acquisisce con orologio nel passato → lease già scaduto
        assert await try_acquire_lock(locks, LOCK, runner_id="runner-A",
                                      ttl_seconds=60, now=past) is True
        assert await try_acquire_lock(locks, LOCK, runner_id="runner-B") is True
        doc = await locks.find_one({"_id": LOCK})
        assert doc["holder"] == "runner-B"

    @pytest.mark.asyncio
    async def test_release_only_own_lock(self, locks):
        await try_acquire_lock(locks, LOCK, runner_id="runner-A")
        await release_lock(locks, LOCK, runner_id="runner-B")   # non suo: no-op
        assert await locks.find_one({"_id": LOCK}) is not None
        await release_lock(locks, LOCK, runner_id="runner-A")
        assert await locks.find_one({"_id": LOCK}) is None

    @pytest.mark.asyncio
    async def test_concurrent_burst_single_winner(self, locks):
        """10 acquisizioni simultanee sullo stesso lock: UNA vince."""
        results = await asyncio.gather(*[
            try_acquire_lock(locks, LOCK, runner_id=f"runner-{i}")
            for i in range(10)
        ])
        assert sum(1 for r in results if r) == 1


class TestJournal:
    @pytest.mark.asyncio
    async def test_start_end_roundtrip(self, locks):
        runs = locks.database["scheduler_job_runs"]
        await runs.delete_many({})
        run_id = await journal_start(runs, "heartbeat")
        await journal_end(runs, run_id, status="ok", summary={"alive": True})
        doc = await runs.find_one({"id": run_id})
        assert doc["status"] == "ok"
        assert doc["summary"] == {"alive": True}
        assert doc["started_at"] and doc["finished_at"]
        await runs.delete_many({})
