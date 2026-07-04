"""Scheduler in-process con lock distribuito su Mongo (Fase 2, S1).

Fondazione per tutti i job automatici della piattaforma (dunning pagamenti,
promemoria pre-ritiro, follow-up). Design:

  · APScheduler (AsyncIOScheduler) DENTRO il processo backend — niente
    Celery/Redis: l'infra è single-VPS per scelta dichiarata (master plan).
  · LOCK A LEASE su Mongo (`scheduler_locks`): ogni tick, il runner prova ad
    acquisire/rinnovare il lease del job. Con più repliche future, una sola
    esegue; se il holder muore, il lease scade e un altro lo riprende.
    Acquisizione ATOMICA via find_one_and_update con predicato
    "libero o scaduto o già mio".
  · JOB JOURNAL (`scheduler_job_runs`): ogni esecuzione registra inizio,
    fine, esito, contatori — osservabilità e post-mortem. Append-only.
  · IDEMPOTENZA: il journal traccia le run; l'idempotenza applicativa vive
    nei job stessi (es. write-ahead `reminders_sent` sulle righe schedule),
    così un job ri-eseguito non produce doppi effetti.

Config env:
  SCHEDULER_ENABLED   — "true"/"false". Default: true, MA forzato false
                        quando ENVIRONMENT=test (i test controllano i job
                        chiamandoli direttamente).
  SCHEDULER_LOCK_TTL_SECONDS — lease del lock (default 120).
"""

import asyncio
import logging
import os
import socket
from datetime import timedelta
from typing import Any, Awaitable, Callable, Dict, List, Optional

from models.common import generate_id, utc_now

logger = logging.getLogger(__name__)

LOCK_TTL_SECONDS = int(os.environ.get("SCHEDULER_LOCK_TTL_SECONDS", "120"))

# Identità del runner: host+pid — leggibile nei lock e nel journal.
RUNNER_ID = f"{socket.gethostname()}:{os.getpid()}"


def scheduler_enabled() -> bool:
    if os.environ.get("ENVIRONMENT", "").lower() == "test":
        return False
    return os.environ.get("SCHEDULER_ENABLED", "true").lower() == "true"


# ── Lock a lease (atomico su Mongo) ─────────────────────────────────────────

async def try_acquire_lock(
    locks_collection,
    lock_name: str,
    *,
    runner_id: str = RUNNER_ID,
    ttl_seconds: int = LOCK_TTL_SECONDS,
    now=None,
) -> bool:
    """Acquisisce o rinnova il lease `lock_name`. True se questo runner lo
    detiene dopo la chiamata.

    Atomico: un solo find_one_and_update con upsert; il predicato accetta
    il lock se (a) scaduto oppure (b) già nostro. Se il documento esiste con
    un holder vivo diverso, l'update non matcha e l'upsert fallisce con
    DuplicateKey → il lock è di qualcun altro.
    """
    now = now or utc_now()
    expires_at = (now + timedelta(seconds=ttl_seconds)).isoformat()
    try:
        await locks_collection.find_one_and_update(
            {
                "_id": lock_name,
                "$or": [
                    {"expires_at": {"$lt": now.isoformat()}},  # scaduto
                    {"holder": runner_id},                       # già mio
                ],
            },
            {"$set": {
                "holder": runner_id,
                "expires_at": expires_at,
                "renewed_at": now.isoformat(),
            }},
            upsert=True,
        )
        return True
    except Exception as exc:
        # DuplicateKeyError atteso quando il lock è detenuto da altri:
        # l'upsert prova a inserire _id già esistente.
        if "duplicate key" in str(exc).lower() or "E11000" in str(exc):
            return False
        raise


async def release_lock(locks_collection, lock_name: str,
                       runner_id: str = RUNNER_ID) -> None:
    """Rilascio esplicito (shutdown pulito). Solo se è nostro."""
    await locks_collection.delete_one({"_id": lock_name, "holder": runner_id})


# ── Journal (append-only) ────────────────────────────────────────────────────

async def journal_start(runs_collection, job_id: str) -> str:
    run_id = generate_id()
    await runs_collection.insert_one({
        "id": run_id,
        "job_id": job_id,
        "runner": RUNNER_ID,
        "started_at": utc_now().isoformat(),
        "status": "running",
    })
    return run_id


async def journal_end(runs_collection, run_id: str, *,
                      status: str, summary: Optional[Dict[str, Any]] = None,
                      error: Optional[str] = None) -> None:
    await runs_collection.update_one(
        {"id": run_id},
        {"$set": {
            "status": status,
            "finished_at": utc_now().isoformat(),
            "summary": summary or {},
            **({"error": error} if error else {}),
        }},
    )


# ── Registry + engine ────────────────────────────────────────────────────────

class ScheduledJob:
    def __init__(self, job_id: str, func: Callable[[], Awaitable[Dict[str, Any]]],
                 interval_seconds: int):
        self.job_id = job_id
        self.func = func
        self.interval_seconds = interval_seconds


_REGISTRY: List[ScheduledJob] = []


def register_job(job_id: str, interval_seconds: int):
    """Decorator: registra un job. La funzione ritorna un dict di summary
    (contatori) che finisce nel journal."""
    def wrap(func: Callable[[], Awaitable[Dict[str, Any]]]):
        _REGISTRY.append(ScheduledJob(job_id, func, interval_seconds))
        return func
    return wrap


def registered_jobs() -> List[ScheduledJob]:
    return list(_REGISTRY)


async def run_job_with_lock(job: ScheduledJob) -> Optional[Dict[str, Any]]:
    """Wrapper eseguito da APScheduler a ogni tick del job:
    lock → journal start → func() → journal end. Errori loggati, mai
    propagati (un job rotto non deve ammazzare il loop)."""
    from database import db
    locks = db.scheduler_locks
    runs = db.scheduler_job_runs

    try:
        if not await try_acquire_lock(locks, f"job:{job.job_id}"):
            return None  # runner concorrente attivo: passo.
    except Exception as exc:
        logger.error("scheduler lock error su %s: %s", job.job_id, exc)
        return None

    run_id = await journal_start(runs, job.job_id)
    try:
        summary = await job.func() or {}
        await journal_end(runs, run_id, status="ok", summary=summary)
        return summary
    except Exception as exc:
        logger.exception("scheduler job %s fallito", job.job_id)
        await journal_end(runs, run_id, status="error", error=str(exc))
        return None


_engine = None


def start_scheduler() -> bool:
    """Avvia AsyncIOScheduler con tutti i job registrati. Chiamato nel
    lifespan di server.py. No-op se disabilitato o già avviato."""
    global _engine
    if not scheduler_enabled():
        logger.info("scheduler disabilitato (env) — nessun job avviato")
        return False
    if _engine is not None:
        return True
    # I moduli che registrano job via @register_job vanno importati PRIMA
    # di avviare l'engine (la registry si popola all'import).
    try:
        from services import payment_dunning_service  # noqa: F401
    except Exception as exc:
        logger.error("scheduler: import job modules failed: %s", exc)
    from apscheduler.schedulers.asyncio import AsyncIOScheduler
    _engine = AsyncIOScheduler(timezone="UTC")
    for job in registered_jobs():
        _engine.add_job(
            run_job_with_lock,
            "interval",
            seconds=job.interval_seconds,
            args=[job],
            id=job.job_id,
            max_instances=1,          # niente overlap dello stesso job
            coalesce=True,            # tick persi (sleep laptop) → 1 run
        )
    _engine.start()
    logger.info("scheduler avviato: %d job (%s)", len(registered_jobs()),
                ", ".join(j.job_id for j in registered_jobs()))
    return True


async def stop_scheduler() -> None:
    global _engine
    if _engine is not None:
        _engine.shutdown(wait=False)
        _engine = None
    # rilascio best-effort dei lock che deteniamo
    try:
        from database import db
        for job in registered_jobs():
            await release_lock(db.scheduler_locks, f"job:{job.job_id}")
    except Exception:
        pass


# ── Job heartbeat (prova di vita della fondazione) ──────────────────────────

@register_job("heartbeat", interval_seconds=300)
async def heartbeat_job() -> Dict[str, Any]:
    """Batte ogni 5 minuti: prova che lock+journal+engine funzionano in prod.
    Il journal di questo job è il primo posto dove guardare se 'i promemoria
    non partono'."""
    return {"alive": True, "runner": RUNNER_ID}
