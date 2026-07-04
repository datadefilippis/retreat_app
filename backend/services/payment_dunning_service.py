"""Dunning pagamenti — il pilota automatico del saldo (Fase 2 S3).

Job schedulato `payment-schedule-scan` (ogni ora, lock Mongo, journal):
per ogni riga saldo/rata non pagata di ordini confermati applica la
sequenza decisa nel piano (FASE2 §3.3):

  T-7   promemoria gentile con link /pay/{token}
  T-0   "scade oggi" con link
  T+..  transizione → OVERDUE (alla prima scansione post-scadenza)
  T+3   sollecito con link
  T+7   transizione → AT_RISK + notifica all'OPERATORE (decide lui:
        MAI cancellazione automatica del posto — piano, regola fissa)

IDEMPOTENZA (write-ahead): il mark in `reminders_sent` si scrive PRIMA
dell'invio email — un job ri-eseguito (crash, riavvio, doppio tick) vede
il mark e non duplica. Le transizioni passano da apply_row_transition
(macchina a stati + evento append-only): un re-run perde pulito.

Il planner è una funzione PURA (testata a tavolino); l'executor fa I/O.
"""

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from models.payment_schedule import RowKind, RowStatus
from models.common import utc_now
from services.scheduler_service import register_job

logger = logging.getLogger(__name__)

# Righe soggette a dunning: mai la caparra (una caparra non pagata è un
# checkout abbandonato, non un credito da sollecitare).
DUNNABLE_KINDS = {RowKind.BALANCE.value, RowKind.INSTALLMENT.value}
ACTIVE_STATES = {RowStatus.PENDING.value, RowStatus.PROCESSING.value,
                 RowStatus.OVERDUE.value}


def _parse(dt: str) -> datetime:
    d = datetime.fromisoformat(dt)
    return d if d.tzinfo else d.replace(tzinfo=timezone.utc)


def plan_dunning_actions(
    schedule_doc: Dict[str, Any],
    order_status: Optional[str],
    now: Optional[datetime] = None,
) -> List[Dict[str, Any]]:
    """Decide le azioni per uno schedule. Pura: nessun I/O.

    Ritorna [{"type": remind_t7|remind_t0|mark_overdue|sollecito_t3|at_risk_t7,
              "row_seq": int}] in ordine di applicazione.
    """
    if order_status in (None, "draft", "cancelled"):
        return []
    now = now or utc_now()
    actions: List[Dict[str, Any]] = []
    for row in schedule_doc.get("rows") or []:
        if row.get("kind") not in DUNNABLE_KINDS:
            continue
        if row.get("status") not in ACTIVE_STATES:
            continue
        due = _parse(row["due_at"])
        sent = {m.get("kind") for m in (row.get("reminders_sent") or [])}
        seq = row["seq"]
        days_to_due = (due - now).total_seconds() / 86400

        if 0 < days_to_due <= 7 and "t-7" not in sent:
            actions.append({"type": "remind_t7", "row_seq": seq})
        if days_to_due <= 0:
            if "t-0" not in sent:
                actions.append({"type": "remind_t0", "row_seq": seq})
            if row.get("status") in (RowStatus.PENDING.value,
                                     RowStatus.PROCESSING.value):
                actions.append({"type": "mark_overdue", "row_seq": seq})
            overdue_days = -days_to_due
            if overdue_days >= 3 and "t+3" not in sent:
                actions.append({"type": "sollecito_t3", "row_seq": seq})
            if overdue_days >= 7 and "t+7" not in sent:
                actions.append({"type": "at_risk_t7", "row_seq": seq})
    return actions


async def _mark_reminder_sent(schedule_id: str, row_seq: int, kind: str) -> bool:
    """Write-ahead atomico: True se il mark è NOSTRO (non c'era già).
    Doppio runner / re-run → il secondo trova il mark e salta l'invio."""
    from database import db
    result = await db.payment_schedules.update_one(
        {"id": schedule_id,
         "rows": {"$elemMatch": {"seq": row_seq,
                                 "reminders_sent.kind": {"$ne": kind}}}},
        {"$push": {"rows.$.reminders_sent": {
            "kind": kind, "at": utc_now().isoformat()}}},
    )
    return getattr(result, "modified_count", 0) > 0


async def run_dunning_scan(now: Optional[datetime] = None) -> Dict[str, Any]:
    """Executor: scandisce gli schedule attivi e applica il planner."""
    from database import db, orders_collection
    from services.payment_schedule_service import (
        InvalidTransition, apply_row_transition, ensure_row_pay_tokens,
    )
    from services import payment_email_service as mail

    now = now or utc_now()
    summary = {"scanned": 0, "reminders": 0, "overdue": 0,
               "at_risk": 0, "errors": 0}

    cursor = db.payment_schedules.find(
        {"rows": {"$elemMatch": {
            "kind": {"$in": list(DUNNABLE_KINDS)},
            "status": {"$in": list(ACTIVE_STATES)},
        }}},
        {"_id": 0},
    )
    async for schedule_doc in cursor:
        summary["scanned"] += 1
        try:
            order = await orders_collection.find_one(
                {"id": schedule_doc["order_id"],
                 "organization_id": schedule_doc["organization_id"]},
                {"_id": 0},
            )
            actions = plan_dunning_actions(
                schedule_doc, (order or {}).get("status"), now)
            if not actions:
                continue
            schedule_doc = await ensure_row_pay_tokens(schedule_doc)

            for action in actions:
                seq = action["row_seq"]
                row = next(r for r in schedule_doc["rows"] if r["seq"] == seq)
                kind_map = {"remind_t7": "t-7", "remind_t0": "t-0",
                            "sollecito_t3": "t+3", "at_risk_t7": "t+7"}

                if action["type"] == "mark_overdue":
                    try:
                        schedule_doc = await apply_row_transition(
                            schedule_doc, seq, RowStatus.OVERDUE,
                            actor="scheduler:payment-schedule-scan",
                        )
                        summary["overdue"] += 1
                    except InvalidTransition:
                        pass
                    continue

                mark = kind_map[action["type"]]
                if not await _mark_reminder_sent(schedule_doc["id"], seq, mark):
                    continue  # già inviato (re-run / runner concorrente)

                if action["type"] in ("remind_t7", "remind_t0", "sollecito_t3"):
                    await mail.send_payment_reminder(
                        order, schedule_doc, row, phase=action["type"])
                    summary["reminders"] += 1
                elif action["type"] == "at_risk_t7":
                    try:
                        schedule_doc = await apply_row_transition(
                            schedule_doc, seq, RowStatus.AT_RISK,
                            actor="scheduler:payment-schedule-scan",
                            detail={"reason": "dunning esaurito (T+7)"},
                        )
                    except InvalidTransition:
                        pass
                    await mail.send_at_risk_to_operator(order, schedule_doc, row)
                    summary["at_risk"] += 1

            # mirror payment_state sull'ordine (fonte: schedule)
            await orders_collection.update_one(
                {"id": schedule_doc["order_id"],
                 "organization_id": schedule_doc["organization_id"]},
                {"$set": {"payment_state": schedule_doc.get("payment_state")}},
            )
        except Exception:
            logger.exception("dunning: schedule %s fallito", schedule_doc.get("id"))
            summary["errors"] += 1
    return summary


@register_job("payment-schedule-scan", interval_seconds=3600)
async def payment_schedule_scan_job() -> Dict[str, Any]:
    return await run_dunning_scan()
