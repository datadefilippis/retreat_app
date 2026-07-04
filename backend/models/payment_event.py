"""PaymentEvent — log APPEND-ONLY di ogni movimento di denaro (Fase 2, S1).

Requisito del founder: tracciabilità completa delle transazioni. Ogni
cambiamento di stato di una riga di PaymentSchedule produce UN evento qui,
scritto NEL MOMENTO in cui accade, con attore esplicito. Nessun update,
nessuna delete: la collection payment_events è la storia, il PaymentSchedule
è lo stato corrente. Quando i due divergono, vince la storia.

Attori:
  webhook:stripe        — conferme/refund arrivati da Stripe
  scheduler:<job_id>    — azioni dei job automatici (dunning, session saldo)
  operator:<user_id>    — azioni manuali dall'admin (mark-paid, waive, refund)
  system:<flow>         — cascate interne (annullo ordine/ritiro, checkout)
"""

from typing import Any, Dict, Optional

from pydantic import BaseModel, Field

from models.common import generate_id, utc_now


class PaymentEvent(BaseModel):
    id: str = Field(default_factory=generate_id)
    organization_id: str
    order_id: str
    schedule_id: str
    row_seq: Optional[int] = None        # None per eventi a livello schedule
    action: str                          # es. "schedule_created", "row_paid",
                                         # "row_overdue", "row_refunded", ...
    from_status: Optional[str] = None
    to_status: Optional[str] = None
    amount_minor: Optional[int] = None
    actor: str                           # vedi docstring
    detail: Dict[str, Any] = Field(default_factory=dict)  # payload contestuale
    at: str = Field(default_factory=lambda: utc_now().isoformat())
