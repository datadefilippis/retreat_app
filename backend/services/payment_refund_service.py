"""Rimborsi & cascata annullo ritiro (Fase 2 S3 — task 2.11/2.12).

Regole (FASE2 §4, decise a tavolino):
  · Rinuncia del partecipante → percentuale dalla POLICY SNAPSHOT
    dell'ordine (mai quella corrente del prodotto), calcolata sul TOTALE
    PAGATO, rimborsata A RITROSO (prima l'ultimo pagamento).
  · Override manuale possibile, sempre tracciato con motivo nel log.
  · Annullo ritiro → rimborso 100% a tutti, indipendente dalla policy
    (l'inadempienza è dell'organizzatore).
  · Righe paid_manual (bonifici): Stripe non c'entra — vengono marcate
    rimborsate a libro e segnalate all'operatore come "rimborso fuori
    piattaforma a tuo carico".
  · Idempotenza: REFUNDED è terminale; Stripe Refund con idempotency key
    per-riga; un secondo tentativo non trova righe rimborsabili.

Le funzioni di calcolo sono PURE (testate a tavolino); l'orchestratore
fa I/O e passa ogni cambio di stato dall'unica porta apply_row_transition.
"""

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from models.common import utc_now
from models.payment_plan import PaymentPlan
from models.payment_schedule import PAID_STATES, RowRefund, RowStatus
from services.payment_schedule_service import (
    InvalidTransition,
    apply_row_transition,
    get_schedule_for_order,
)

logger = logging.getLogger(__name__)

# Stati non-terminali che una cascata di annullo porta a CANCELLED.
_CANCELLABLE = {RowStatus.PENDING.value, RowStatus.PROCESSING.value,
                RowStatus.OVERDUE.value, RowStatus.AT_RISK.value}


# ── Calcoli puri ─────────────────────────────────────────────────────────────

def _parse(dt: str) -> datetime:
    d = datetime.fromisoformat(dt)
    return d if d.tzinfo else d.replace(tzinfo=timezone.utc)


def compute_policy_refund(
    schedule_doc: Dict[str, Any],
    occurrence_start_at: Optional[str],
    now: Optional[datetime] = None,
) -> Dict[str, Any]:
    """Quanto spetta di rimborso per una rinuncia ADESSO, dalla policy
    fotografata sull'ordine. Puro."""
    now = now or utc_now()
    plan = PaymentPlan(**schedule_doc["plan_snapshot"])
    paid_minor = sum(
        r["amount_minor"] for r in schedule_doc.get("rows", [])
        if r.get("status") in {s.value for s in PAID_STATES}
    )
    if occurrence_start_at:
        days_before = int((_parse(occurrence_start_at) - now).total_seconds() // 86400)
    else:
        days_before = -1   # data ignota: fascia peggiore, serve override
    percent = plan.refund_percent_at(days_before)
    refundable = (paid_minor * percent) // 100
    return {
        "paid_minor": paid_minor,
        "days_before_start": days_before,
        "policy_percent": percent,
        "refundable_minor": refundable,
    }


def plan_refund_distribution(
    rows: List[Dict[str, Any]], refund_minor: int,
) -> List[Dict[str, Any]]:
    """Distribuisce il rimborso A RITROSO sulle righe pagate.

    Ritorna [{row_seq, amount_minor, channel: stripe|manual,
              payment_intent}] — l'ultima riga toccata può essere parziale.
    Puro, testato."""
    remaining = max(0, refund_minor)
    out: List[Dict[str, Any]] = []
    paid_rows = [r for r in rows
                 if r.get("status") in {s.value for s in PAID_STATES}]
    for row in sorted(paid_rows, key=lambda r: r["seq"], reverse=True):
        if remaining <= 0:
            break
        share = min(remaining, row["amount_minor"])
        out.append({
            "row_seq": row["seq"],
            "amount_minor": share,
            "channel": "manual" if row.get("status") == RowStatus.PAID_MANUAL.value
                       else "stripe",
            "payment_intent": row.get("stripe_payment_intent"),
        })
        remaining -= share
    return out


# ── I/O Stripe (isolato per i test) ─────────────────────────────────────────

async def _stripe_refund(payment_intent: str, amount_minor: int,
                         connected_account: Optional[str],
                         idempotency_key: str) -> str:
    """Via provider registry — il linter di isolamento Stripe vieta gli
    import diretti del SDK fuori da payment_providers (giustamente)."""
    from payment_providers import PaymentProviderRegistry
    from services.payment_checkout_service import _resolve_org_doc_for_provider
    # provider di default stripe: il refund vive sul connected account
    provider = PaymentProviderRegistry.get_for_org(None)
    return await provider.create_refund(
        payment_intent=payment_intent,
        amount_minor=amount_minor,
        connected_account=connected_account,
        idempotency_key=idempotency_key,
    )


async def _connected_account_for_org(org_id: str) -> Optional[str]:
    from services.payment_checkout_service import _get_connected_account_id
    return await _get_connected_account_id(org_id)


# ── Orchestratore: rimborso ordine ──────────────────────────────────────────

async def refund_order(
    org_id: str,
    order_id: str,
    *,
    actor: str,
    reason: str,
    override_amount_minor: Optional[int] = None,
    force_full: bool = False,
    cancel_the_order: bool = True,
    now: Optional[datetime] = None,
) -> Dict[str, Any]:
    """Rimborsa un ordine secondo policy (o override/full) e — di default —
    lo annulla con la cascata esistente (posti liberati, biglietti void,
    email al cliente).

    force_full=True → 100% del pagato (cascata annullo ritiro).
    override_amount_minor → importo esplicito (tracciato col motivo).
    """
    from database import event_occurrences_collection, orders_collection

    schedule_doc = await get_schedule_for_order(order_id, org_id)
    if not schedule_doc:
        raise ValueError("Nessun piano pagamenti per questo ordine")
    order = await orders_collection.find_one(
        {"id": order_id, "organization_id": org_id}, {"_id": 0})
    if not order:
        raise ValueError("Ordine non trovato")

    occ_start = None
    if schedule_doc.get("occurrence_id"):
        occ = await event_occurrences_collection.find_one(
            {"id": schedule_doc["occurrence_id"], "organization_id": org_id},
            {"_id": 0, "start_at": 1})
        occ_start = (occ or {}).get("start_at")

    policy = compute_policy_refund(schedule_doc, occ_start, now=now)
    if force_full:
        refund_minor = policy["paid_minor"]
        basis = "full_cancellation"
    elif override_amount_minor is not None:
        if not reason.strip():
            raise ValueError("Il motivo è obbligatorio per un rimborso in override")
        refund_minor = min(int(override_amount_minor), policy["paid_minor"])
        basis = "override"
    else:
        refund_minor = policy["refundable_minor"]
        basis = "policy"

    distribution = plan_refund_distribution(schedule_doc["rows"], refund_minor)
    connected = await _connected_account_for_org(org_id) if any(
        d["channel"] == "stripe" for d in distribution) else None

    refunded_stripe = 0
    refunded_manual = 0
    now_iso = utc_now().isoformat()
    for item in distribution:
        seq = item["row_seq"]
        refund_kwargs = dict(
            amount_minor=item["amount_minor"], reason=reason or basis,
            by=actor, at=now_iso,
        )
        if item["channel"] == "stripe" and item["payment_intent"]:
            refund_id = await _stripe_refund(
                item["payment_intent"], item["amount_minor"], connected,
                idempotency_key=f"refund:{order_id}:{seq}",
            )
            refund_kwargs["stripe_refund_id"] = refund_id
            refunded_stripe += item["amount_minor"]
        else:
            refund_kwargs["out_of_platform"] = True
            refunded_manual += item["amount_minor"]
        refund_info = RowRefund(**refund_kwargs)
        try:
            schedule_doc = await apply_row_transition(
                schedule_doc, seq, RowStatus.REFUNDED,
                actor=actor, action="row_refunded",
                row_updates={"refund": refund_info},
                detail={"basis": basis, "policy": policy,
                        "channel": item["channel"]},
            )
        except InvalidTransition as exc:
            logger.warning("refund: transizione riga %s saltata: %s", seq, exc)

    # righe non pagate → cancelled (il piano muore con l'ordine)
    if cancel_the_order:
        for row in list(schedule_doc["rows"]):
            if row.get("status") in _CANCELLABLE:
                try:
                    schedule_doc = await apply_row_transition(
                        schedule_doc, row["seq"], RowStatus.CANCELLED,
                        actor=actor, action="row_cancelled",
                        detail={"basis": basis},
                    )
                except InvalidTransition:
                    pass

    await orders_collection.update_one(
        {"id": order_id, "organization_id": org_id},
        {"$set": {"payment_state": schedule_doc.get("payment_state")}},
    )

    if cancel_the_order:
        from services.order_service import cancel_order
        try:
            await cancel_order(org_id, order_id)
        except Exception as exc:
            logger.error("refund: cancel_order fallito per %s: %s", order_id, exc)

    return {
        "order_id": order_id,
        "basis": basis,
        "policy": policy,
        "refunded_stripe_minor": refunded_stripe,
        "refunded_manual_minor": refunded_manual,   # a carico operatore
        "rows_refunded": [d["row_seq"] for d in distribution],
    }


# ── Cascata annullo ritiro ───────────────────────────────────────────────────

async def cancel_occurrence_cascade(
    org_id: str,
    occurrence_id: str,
    *,
    actor: str,
) -> Dict[str, Any]:
    """Annulla un ritiro: occurrence → cancelled, rimborso 100% a tutti gli
    ordini attivi, biglietti void (via cancel_order), broadcast di avviso
    (template 'cancellation' esistente). Da ore di lavoro a una chiamata."""
    from database import db, event_occurrences_collection, orders_collection

    occ = await event_occurrences_collection.find_one(
        {"id": occurrence_id, "organization_id": org_id}, {"_id": 0})
    if not occ:
        raise ValueError("Ritiro non trovato")

    await event_occurrences_collection.update_one(
        {"id": occurrence_id, "organization_id": org_id},
        {"$set": {"status": "cancelled", "updated_at": utc_now().isoformat()}},
    )

    schedules = await db.payment_schedules.find(
        {"organization_id": org_id, "occurrence_id": occurrence_id},
        {"_id": 0},
    ).to_list(1000)

    summary = {"occurrence_id": occurrence_id, "orders_processed": 0,
               "refunded_stripe_minor": 0, "refunded_manual_minor": 0,
               "skipped": 0, "errors": []}
    for schedule_doc in schedules:
        order_id = schedule_doc["order_id"]
        order = await orders_collection.find_one(
            {"id": order_id, "organization_id": org_id},
            {"_id": 0, "status": 1})
        if not order or order.get("status") == "cancelled":
            summary["skipped"] += 1
            continue
        try:
            result = await refund_order(
                org_id, order_id,
                actor=actor,
                reason="Ritiro annullato dall'organizzatore",
                force_full=True,
            )
            summary["orders_processed"] += 1
            summary["refunded_stripe_minor"] += result["refunded_stripe_minor"]
            summary["refunded_manual_minor"] += result["refunded_manual_minor"]
        except Exception as exc:
            logger.exception("cascade: ordine %s fallito", order_id)
            summary["errors"].append({"order_id": order_id, "error": str(exc)})

    # broadcast ai partecipanti (template esistente E4) — best-effort
    try:
        from services.event_email_service import broadcast_to_attendees
        await broadcast_to_attendees(
            org_id=org_id, occurrence_id=occurrence_id,
            template_key="cancellation",
            include_voided=True,   # i biglietti sono appena stati annullati
        )
        summary["broadcast"] = "sent"
    except Exception as exc:
        logger.warning("cascade: broadcast fallito: %s", exc)
        summary["broadcast"] = f"failed: {exc}"

    return summary
