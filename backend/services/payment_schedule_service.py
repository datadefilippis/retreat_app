"""Motore schedule pagamenti (Fase 2, S1).

Responsabilità:
  · generate_rows()          — pura, deterministica, testata: dal piano al
                               libro mastro. INVARIANTE: sum(righe) == totale.
  · create_schedule_for_order() — persiste schedule + evento "schedule_created".
  · apply_row_transition()   — UNICA porta per cambiare stato a una riga:
                               valida la macchina a stati, ricalcola i totali,
                               scrive il PaymentEvent append-only, aggiorna
                               payment_state derivato. Sincronizzazione e
                               tracciabilità vivono qui, non sparse nei caller.

Regole di generazione:
  · mode=full → 1 riga FULL due=now.
  · last-minute collapse: se now >= start - balance_due_days → mode=full
    (flag collapsed_last_minute=True sullo schedule).
  · deposit percent: round half-up sul totale; fixed: min(deposit, total-1)
    così resta sempre un saldo positivo.
  · balance = total - deposit (MAI ricalcolato in percentuale: garantisce
    l'invariante di somma al centesimo).
  · installments: il saldo si divide in N parti; il resto (centesimi) va
    alle PRIME rate (deterministico). Scadenze equispaziate tra prenotazione
    e deadline (start - balance_due_days), granularità giorno.
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from models.payment_event import PaymentEvent
from models.payment_plan import DepositType, PaymentPlan, PaymentPlanMode
from models.payment_schedule import (
    ALLOWED_TRANSITIONS,
    PaymentSchedule,
    RowKind,
    RowStatus,
    ScheduleRow,
    compute_totals,
    derive_payment_state,
)
from models.common import utc_now

logger = logging.getLogger(__name__)


# ── Generazione (pura) ───────────────────────────────────────────────────────

def _parse_dt(value: str) -> datetime:
    dt = datetime.fromisoformat(value)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def _round_half_up(numerator: int, denominator: int) -> int:
    """Divisione intera con arrotondamento half-up (denaro, niente float)."""
    return (numerator * 2 + denominator) // (denominator * 2)


def effective_mode(plan: PaymentPlan, start_at: datetime, now: datetime) -> PaymentPlanMode:
    """Applica la regola last-minute: niente caparra a ridosso dell'inizio."""
    if plan.mode == PaymentPlanMode.FULL:
        return PaymentPlanMode.FULL
    deadline = start_at - timedelta(days=plan.balance_due_days_before)
    if now >= deadline:
        return PaymentPlanMode.FULL
    return plan.mode


def compute_deposit_minor(plan: PaymentPlan, total_minor: int) -> int:
    if plan.deposit_type == DepositType.PERCENT:
        deposit = _round_half_up(total_minor * plan.deposit_value, 100)
    else:
        deposit = plan.deposit_value
    # La caparra non può inghiottire il totale: deve restare saldo positivo.
    return max(1, min(deposit, total_minor - 1))


def generate_rows(
    plan: PaymentPlan,
    total_minor: int,
    start_at: str,
    now: Optional[datetime] = None,
) -> tuple[List[ScheduleRow], bool]:
    """Genera le righe del libro mastro. Ritorna (rows, collapsed_last_minute).

    INVARIANTE (testata): sum(r.amount_minor) == total_minor, sempre.
    """
    if total_minor <= 0:
        raise ValueError("total_minor deve essere positivo")
    now = now or utc_now()
    start = _parse_dt(start_at)
    mode = effective_mode(plan, start, now)
    collapsed = mode == PaymentPlanMode.FULL and plan.mode != PaymentPlanMode.FULL

    if mode == PaymentPlanMode.FULL:
        return ([ScheduleRow(
            seq=0, kind=RowKind.FULL, label="Pagamento",
            amount_minor=total_minor, due_at=now.isoformat(),
        )], collapsed)

    deposit = compute_deposit_minor(plan, total_minor)
    balance_total = total_minor - deposit
    deadline = start - timedelta(days=plan.balance_due_days_before)
    rows = [ScheduleRow(
        seq=0, kind=RowKind.DEPOSIT, label="Caparra",
        amount_minor=deposit, due_at=now.isoformat(),
    )]

    if mode == PaymentPlanMode.DEPOSIT_BALANCE:
        rows.append(ScheduleRow(
            seq=1, kind=RowKind.BALANCE, label="Saldo",
            amount_minor=balance_total, due_at=deadline.isoformat(),
        ))
        return (rows, collapsed)

    # deposit_installments — resto ai primi (deterministico)
    n = plan.installments_count
    base = balance_total // n
    remainder = balance_total - base * n
    if base <= 0:
        # Totale troppo piccolo per N rate: una sola rata (il piano non deve
        # mai produrre righe da 0).
        rows.append(ScheduleRow(
            seq=1, kind=RowKind.INSTALLMENT, label="Rata 1 di 1",
            amount_minor=balance_total, due_at=deadline.isoformat(),
        ))
        return (rows, collapsed)

    window = deadline - now
    for i in range(n):
        amount = base + (1 if i < remainder else 0)
        due = now + window * ((i + 1) / n)
        # granularità giorno, mai oltre la deadline
        due = min(due.replace(hour=12, minute=0, second=0, microsecond=0), deadline)
        rows.append(ScheduleRow(
            seq=i + 1, kind=RowKind.INSTALLMENT,
            label=f"Rata {i + 1} di {n}",
            amount_minor=amount, due_at=due.isoformat(),
        ))
    return (rows, collapsed)


# ── Persistenza & transizioni ────────────────────────────────────────────────

def _collections():
    """Import ritardato: i test unit patchano database.*; il codice prod
    risolve le collection reali."""
    from database import db
    return db.payment_schedules, db.payment_events


async def record_event(event: PaymentEvent) -> None:
    """Append-only: SOLO insert. Nessun path di update/delete esiste."""
    _, events = _collections()
    await events.insert_one(event.model_dump())


async def create_schedule_for_order(
    *,
    order_id: str,
    organization_id: str,
    occurrence_id: Optional[str],
    plan: PaymentPlan,
    total_minor: int,
    start_at: str,
    currency: str = "EUR",
    actor: str = "system:checkout",
    now: Optional[datetime] = None,
) -> PaymentSchedule:
    rows, collapsed = generate_rows(plan, total_minor, start_at, now=now)
    schedule = PaymentSchedule(
        order_id=order_id,
        organization_id=organization_id,
        occurrence_id=occurrence_id,
        currency=currency,
        plan_snapshot=plan,
        collapsed_last_minute=collapsed,
        rows=rows,
        payment_state="none",
    )
    schedule.totals = compute_totals(schedule.rows)
    schedules, _ = _collections()
    await schedules.insert_one(schedule.model_dump())
    await record_event(PaymentEvent(
        organization_id=organization_id,
        order_id=order_id,
        schedule_id=schedule.id,
        action="schedule_created",
        amount_minor=total_minor,
        actor=actor,
        detail={
            "mode": schedule.plan_snapshot.mode.value,
            "collapsed_last_minute": collapsed,
            "rows": [
                {"seq": r.seq, "kind": r.kind.value,
                 "amount_minor": r.amount_minor, "due_at": r.due_at}
                for r in rows
            ],
        },
    ))
    return schedule


async def create_schedule_for_new_order(
    order_doc: Dict[str, Any],
    org_id: str,
    event_ctx: Optional[Dict[str, Any]],
) -> Optional[PaymentSchedule]:
    """Hook di integrazione col checkout esistente (Fase 2, S1 task 2.4).

    Chiamato da order_service.create_order DOPO l'insert dell'ordine, per
    gli ordini che contengono una riga event_ticket con data (= un ritiro).
    Ordini senza eventi o a totale zero (richieste di contatto): nessuno
    schedule, flusso invariato.

    Il piano si legge da product.metadata["payment_plan"] (snapshot passato
    in event_ctx); se assente o invalido → default pagamento unico.

    S1: la modalità è FORZATA a `full` — il checkout oggi incassa l'intero
    totale in una volta, e il libro mastro deve riflettere ciò che accade
    davvero, non ciò che accadrà. S2 (checkout caparra) rimuove il forcing
    e attiva le modalità deposit_*. Consistenza > feature.
    """
    if not event_ctx or not event_ctx.get("start_at"):
        return None
    total = float(order_doc.get("total") or 0)
    if total <= 0:
        return None
    total_minor = int(round(total * 100))

    plan_raw = event_ctx.get("plan_raw")
    plan = None
    if isinstance(plan_raw, dict) and plan_raw:
        try:
            plan = PaymentPlan(**plan_raw)
        except Exception as exc:
            logger.warning(
                "payment_plan invalido su prodotto (order %s): %s — fallback full",
                order_doc.get("id"), exc,
            )
    if plan is None:
        plan = PaymentPlan(mode=PaymentPlanMode.FULL)

    # S1 forcing (vedi docstring). Rimosso in S2 col checkout caparra.
    if plan.mode != PaymentPlanMode.FULL:
        plan = plan.model_copy(update={"mode": PaymentPlanMode.FULL})

    return await create_schedule_for_order(
        order_id=order_doc["id"],
        organization_id=org_id,
        occurrence_id=event_ctx.get("occurrence_id"),
        plan=plan,
        total_minor=total_minor,
        start_at=event_ctx["start_at"],
        currency=order_doc.get("currency") or "EUR",
        actor="system:checkout",
    )


class InvalidTransition(Exception):
    pass


async def apply_row_transition(
    schedule_doc: Dict[str, Any],
    row_seq: int,
    new_status: RowStatus,
    *,
    actor: str,
    action: Optional[str] = None,
    detail: Optional[Dict[str, Any]] = None,
    row_updates: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """L'UNICA porta per cambiare stato a una riga.

    1. valida la transizione (ALLOWED_TRANSITIONS) — tutto il resto è bug
    2. applica gli update alla riga + timestamp
    3. ricalcola totals e payment_state DAI FATTI (mai incrementi)
    4. persiste con guardia ottimistica su (id, rows.seq.status di partenza)
    5. appende il PaymentEvent

    Ritorna lo schedule_doc aggiornato. Solleva InvalidTransition se la
    macchina a stati non consente il passaggio.
    """
    schedule = PaymentSchedule(**schedule_doc)
    row = next((r for r in schedule.rows if r.seq == row_seq), None)
    if row is None:
        raise ValueError(f"riga seq={row_seq} inesistente nello schedule {schedule.id}")
    old_status = row.status
    if new_status not in ALLOWED_TRANSITIONS.get(old_status, set()):
        raise InvalidTransition(
            f"transizione {old_status.value} → {new_status.value} non consentita "
            f"(order {schedule.order_id}, riga {row_seq})"
        )

    row.status = new_status
    if row_updates:
        for key, value in row_updates.items():
            setattr(row, key, value)
    if new_status in (RowStatus.PAID, RowStatus.PAID_MANUAL) and not row.paid_at:
        row.paid_at = utc_now().isoformat()

    schedule.totals = compute_totals(schedule.rows)
    schedule.payment_state = derive_payment_state(schedule.rows)
    schedule.updated_at = utc_now().isoformat()

    schedules, _ = _collections()
    result = await schedules.update_one(
        {
            "id": schedule.id,
            # guardia ottimistica: la riga deve essere ancora nello stato
            # di partenza — concorrenza (webhook doppio, doppio click admin)
            # perde pulita invece di sovrascrivere.
            "rows": {"$elemMatch": {"seq": row_seq, "status": old_status.value}},
        },
        {"$set": {
            "rows": [r.model_dump() for r in schedule.rows],
            "totals": schedule.totals.model_dump(),
            "payment_state": schedule.payment_state,
            "updated_at": schedule.updated_at,
        }},
    )
    if getattr(result, "modified_count", 0) == 0:
        raise InvalidTransition(
            f"guardia concorrenza: riga {row_seq} non più in stato "
            f"{old_status.value} (order {schedule.order_id}) — nessuna modifica"
        )

    await record_event(PaymentEvent(
        organization_id=schedule.organization_id,
        order_id=schedule.order_id,
        schedule_id=schedule.id,
        row_seq=row_seq,
        action=action or f"row_{new_status.value}",
        from_status=old_status.value,
        to_status=new_status.value,
        amount_minor=row.amount_minor,
        actor=actor,
        detail=detail or {},
    ))
    logger.info(
        "payment row transition: order=%s row=%s %s→%s actor=%s",
        schedule.order_id, row_seq, old_status.value, new_status.value, actor,
    )
    return schedule.model_dump()
