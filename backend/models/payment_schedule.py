"""PaymentSchedule — il libro mastro delle scadenze di un ordine (Fase 2, S1).

Un documento per ordine. Ogni riga è una scadenza (caparra/saldo/rata) con
macchina a stati esplicita e transizioni SOLE-ANDATA. Ogni transizione passa
da `apply_row_transition` nel service, che:
  1. valida la transizione contro ALLOWED_TRANSITIONS
  2. aggiorna la riga e ricalcola i totali
  3. appende un PaymentEvent (log append-only) — tracciabilità completa

Importi SEMPRE in minor units. La somma delle righe è SEMPRE il totale
dell'ordine (invariante testata).
"""

from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from models.common import generate_id, utc_now
from models.payment_plan import PaymentPlan


class RowKind(str, Enum):
    FULL = "full"                # pagamento unico (mode=full o collapse)
    DEPOSIT = "deposit"
    BALANCE = "balance"
    INSTALLMENT = "installment"


class RowStatus(str, Enum):
    PENDING = "pending"          # in attesa, non ancora scaduta
    PROCESSING = "processing"    # checkout session generata, esito non noto
    PAID = "paid"                # incassata via Stripe (webhook)
    PAID_MANUAL = "paid_manual"  # segnata pagata dall'operatore (bonifico ecc.)
    OVERDUE = "overdue"          # scaduta, dunning in corso
    AT_RISK = "at_risk"          # dunning esaurito, decide l'operatore
    WAIVED = "waived"            # condonata dall'operatore
    REFUNDED = "refunded"        # rimborsata (totale o parziale)
    CANCELLED = "cancelled"      # annullata (annullo ordine/ritiro)


# Transizioni consentite (sole-andata). Tutto ciò che non è qui è un bug.
ALLOWED_TRANSITIONS: Dict[RowStatus, set] = {
    RowStatus.PENDING: {
        RowStatus.PROCESSING, RowStatus.PAID, RowStatus.PAID_MANUAL,
        RowStatus.OVERDUE, RowStatus.WAIVED, RowStatus.CANCELLED,
    },
    RowStatus.PROCESSING: {
        RowStatus.PAID, RowStatus.PAID_MANUAL,
        # session abbandonata: si torna operativi via overdue/pending-espresso
        RowStatus.PENDING, RowStatus.OVERDUE, RowStatus.CANCELLED,
    },
    RowStatus.OVERDUE: {
        RowStatus.PROCESSING, RowStatus.PAID, RowStatus.PAID_MANUAL,
        RowStatus.AT_RISK, RowStatus.WAIVED, RowStatus.CANCELLED,
    },
    RowStatus.AT_RISK: {
        RowStatus.PROCESSING, RowStatus.PAID, RowStatus.PAID_MANUAL,
        RowStatus.WAIVED, RowStatus.CANCELLED,
    },
    RowStatus.PAID: {RowStatus.REFUNDED},
    RowStatus.PAID_MANUAL: {RowStatus.REFUNDED, RowStatus.CANCELLED},
    RowStatus.WAIVED: {RowStatus.CANCELLED},
    RowStatus.REFUNDED: set(),      # terminale
    RowStatus.CANCELLED: set(),     # terminale
}

# Stati che contano come "incassato" nei totali.
PAID_STATES = {RowStatus.PAID, RowStatus.PAID_MANUAL}


class RowRefund(BaseModel):
    amount_minor: int = Field(ge=0)
    reason: str = ""
    by: str = ""                     # actor id ("operator:<user_id>", "system:cascade")
    at: str = ""                     # ISO datetime


class ReminderMark(BaseModel):
    """Write-ahead: si scrive PRIMA dell'invio email — un job rieseguito
    vede il mark e non duplica il promemoria."""
    kind: str                        # "t-7" | "t-0" | "t+3" | "t+7"
    at: str


class ScheduleRow(BaseModel):
    seq: int = Field(ge=0)
    kind: RowKind
    label: str
    amount_minor: int = Field(gt=0)
    due_at: str                      # ISO datetime UTC
    status: RowStatus = RowStatus.PENDING
    stripe_session_id: Optional[str] = None
    stripe_payment_intent: Optional[str] = None
    paid_at: Optional[str] = None
    fee_minor: int = 0               # application fee registrata all'incasso
    manual_note: Optional[str] = None
    refund: Optional[RowRefund] = None
    reminders_sent: List[ReminderMark] = Field(default_factory=list)


class ScheduleTotals(BaseModel):
    due_minor: int = 0               # totale piano (somma righe non cancelled)
    paid_minor: int = 0              # incassato (paid + paid_manual)
    refunded_minor: int = 0
    fee_minor: int = 0


class PaymentSchedule(BaseModel):
    id: str = Field(default_factory=generate_id)
    order_id: str
    organization_id: str
    occurrence_id: Optional[str] = None
    currency: str = "EUR"
    plan_snapshot: PaymentPlan       # congelato alla prenotazione
    collapsed_last_minute: bool = False
    rows: List[ScheduleRow]
    totals: ScheduleTotals = Field(default_factory=ScheduleTotals)
    payment_state: str = "none"      # none | deposit_paid | fully_paid
    created_at: str = Field(default_factory=lambda: utc_now().isoformat())
    updated_at: str = Field(default_factory=lambda: utc_now().isoformat())


def compute_totals(rows: List[ScheduleRow]) -> ScheduleTotals:
    """Ricalcolo deterministico dai fatti delle righe — mai incrementi sparsi."""
    t = ScheduleTotals()
    for r in rows:
        if r.status != RowStatus.CANCELLED:
            t.due_minor += r.amount_minor
        if r.status in PAID_STATES or (
            r.status == RowStatus.REFUNDED and r.paid_at
        ):
            t.paid_minor += r.amount_minor
        if r.refund:
            t.refunded_minor += r.refund.amount_minor
        t.fee_minor += r.fee_minor
    return t


def derive_payment_state(rows: List[ScheduleRow]) -> str:
    """Stato ordine derivato dalle righe (mai settato a mano)."""
    active = [r for r in rows if r.status != RowStatus.CANCELLED]
    if not active:
        return "none"
    payable = [r for r in active if r.status != RowStatus.WAIVED]
    settled = [
        r for r in payable
        if r.status in PAID_STATES or (r.status == RowStatus.REFUNDED and r.paid_at)
    ]
    if payable and len(settled) == len(payable):
        return "fully_paid"
    if any(r.kind in (RowKind.DEPOSIT, RowKind.FULL) and r.status in PAID_STATES
           for r in active):
        return "deposit_paid"
    return "none"
