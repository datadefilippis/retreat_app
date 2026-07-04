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


# Sotto questa soglia Stripe rifiuta l'addebito (minimo EUR ~0,50€).
# Una caparra sotto soglia fa collassare il piano in pagamento unico.
MIN_CHARGE_MINOR = 50


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
    # Caparra o saldo sotto il minimo addebitabile Stripe → pagamento unico
    # (una riga da 30 centesimi non è incassabile: meglio un piano onesto).
    if deposit < MIN_CHARGE_MINOR or (total_minor - deposit) < MIN_CHARGE_MINOR:
        return ([ScheduleRow(
            seq=0, kind=RowKind.FULL, label="Pagamento",
            amount_minor=total_minor, due_at=now.isoformat(),
        )], True)
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

    S2: le modalità deposit_* sono ATTIVE — il checkout addebita la sola
    riga caparra (create_checkout_session è schedule-aware) e il webhook
    fa la transizione della riga. Il forcing S1 è stato rimosso qui e il
    test marcato è stato invertito insieme (consistenza ledger↔realtà).
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


def aggregate_schedules(schedule_docs: List[Dict[str, Any]], now_iso: Optional[str] = None) -> Dict[str, Any]:
    """Aggregato dashboard incassi per un ritiro (funzione PURA, testata).

    incassato  = righe paid/paid_manual
    in_arrivo  = righe pending con scadenza futura
    in_ritardo = righe pending scadute (il job dunning le porterà a overdue,
                 ma la dashboard non deve aspettare il job) + overdue
    a_rischio  = righe at_risk
    """
    now_iso = now_iso or utc_now().isoformat()
    agg = {
        "orders_count": len(schedule_docs),
        "incassato_minor": 0,
        "in_arrivo_minor": 0,
        "in_ritardo_minor": 0,
        "a_rischio_minor": 0,
        "rimborsato_minor": 0,
        "fully_paid_orders": 0,
        "deposit_paid_orders": 0,
    }
    for doc in schedule_docs:
        state = doc.get("payment_state")
        if state == "fully_paid":
            agg["fully_paid_orders"] += 1
        elif state == "deposit_paid":
            agg["deposit_paid_orders"] += 1
        for row in doc.get("rows") or []:
            status = row.get("status")
            amount = row.get("amount_minor", 0)
            if status in ("paid", "paid_manual"):
                agg["incassato_minor"] += amount
            elif status == "pending":
                if (row.get("due_at") or "") < now_iso:
                    agg["in_ritardo_minor"] += amount
                else:
                    agg["in_arrivo_minor"] += amount
            elif status in ("overdue", "processing"):
                agg["in_ritardo_minor"] += amount if status == "overdue" else 0
                if status == "processing":
                    # session emessa non conclusa: è denaro atteso
                    if (row.get("due_at") or "") < now_iso:
                        agg["in_ritardo_minor"] += amount
                    else:
                        agg["in_arrivo_minor"] += amount
            elif status == "at_risk":
                agg["a_rischio_minor"] += amount
            if row.get("refund"):
                agg["rimborsato_minor"] += (row["refund"] or {}).get("amount_minor", 0)
    return agg


async def get_schedule_for_order(order_id: str, organization_id: str) -> Optional[Dict[str, Any]]:
    """Schedule corrente di un ordine (None se assente — ordini non-ritiro)."""
    schedules, _ = _collections()
    return await schedules.find_one(
        {"order_id": order_id, "organization_id": organization_id}, {"_id": 0},
    )


def pending_charge_row(schedule_doc: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """La riga da addebitare ADESSO al checkout, se il piano lo prevede.

    Ritorna la prima riga (seq 0) quando è una caparra in stato addebitabile
    (pending o processing — processing = session precedente abbandonata,
    l'idempotency key Stripe collassa i duplicati). Per piani `full` ritorna
    None: il checkout classico addebita l'intero totale, zero deviazioni.
    """
    if not schedule_doc:
        return None
    rows = schedule_doc.get("rows") or []
    if not rows:
        return None
    first = rows[0]
    if first.get("kind") != RowKind.DEPOSIT.value:
        return None
    if first.get("status") not in (RowStatus.PENDING.value, RowStatus.PROCESSING.value):
        return None
    return first


async def apply_stripe_payment_to_schedule(
    order_id: str,
    organization_id: str,
    row_seq: int,
    *,
    stripe_payment_intent: Optional[str],
    stripe_session_id: Optional[str],
) -> Optional[Dict[str, Any]]:
    """Transizione riga → PAID dal webhook Stripe. Idempotente: se la riga
    non è più in uno stato pagabile (webhook doppio), logga e ritorna lo
    schedule invariato — MAI un doppio incasso a libro."""
    schedule_doc = await get_schedule_for_order(order_id, organization_id)
    if not schedule_doc:
        return None
    rows = schedule_doc.get("rows") or []
    row = next((r for r in rows if r.get("seq") == row_seq), None)
    if row is None:
        logger.error("apply_stripe_payment: riga %s inesistente (order %s)",
                     row_seq, order_id)
        return schedule_doc
    try:
        return await apply_row_transition(
            schedule_doc, row_seq, RowStatus.PAID,
            actor="webhook:stripe",
            row_updates={
                "stripe_payment_intent": stripe_payment_intent,
                "stripe_session_id": stripe_session_id,
            },
        )
    except InvalidTransition as exc:
        logger.info("apply_stripe_payment: transizione ignorata (%s)", exc)
        return schedule_doc


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
