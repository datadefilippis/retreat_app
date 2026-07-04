"""PaymentPlan — come l'organizzatore incassa un ritiro (Fase 2, S1).

Configurato per-prodotto nel wizard; viene SNAPSHOTTATO sull'ordine alla
prenotazione (pattern consensi/attendee): cambiare il piano di un ritiro
non tocca mai gli ordini già presi.

Tre modalità:
  full                 — pagamento unico al checkout (comportamento storico)
  deposit_balance      — caparra al checkout + saldo entro X giorni dall'inizio
  deposit_installments — caparra al checkout + N rate, l'ultima entro X giorni

Regola last-minute (applicata alla GENERAZIONE dello schedule, non qui):
se alla prenotazione mancano meno di `balance_due_days_before` giorni
all'inizio, il piano collassa in `full`.

Tutti gli importi in MINOR UNITS (centesimi). Mai float sul denaro.
"""

from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field, model_validator


class PaymentPlanMode(str, Enum):
    FULL = "full"
    DEPOSIT_BALANCE = "deposit_balance"
    DEPOSIT_INSTALLMENTS = "deposit_installments"


class DepositType(str, Enum):
    PERCENT = "percent"
    FIXED = "fixed"          # minor units


class CancellationTier(BaseModel):
    """Scaglione policy: 'rimborso refund_percent% fino a days_before giorni
    dall'inizio'. Gli scaglioni si valutano dal più lontano al più vicino."""
    days_before: int = Field(ge=0, le=365)
    refund_percent: int = Field(ge=0, le=100)


DEFAULT_CANCELLATION_POLICY: List[CancellationTier] = [
    CancellationTier(days_before=60, refund_percent=100),
    CancellationTier(days_before=30, refund_percent=50),
    CancellationTier(days_before=0, refund_percent=0),
]


class PaymentPlan(BaseModel):
    mode: PaymentPlanMode = PaymentPlanMode.FULL
    deposit_type: DepositType = DepositType.PERCENT
    # percent: 1-90 · fixed: minor units > 0
    deposit_value: int = Field(default=30, gt=0)
    balance_due_days_before: int = Field(default=30, ge=1, le=180)
    installments_count: int = Field(default=3, ge=2, le=6)
    cancellation_policy: List[CancellationTier] = Field(
        default_factory=lambda: [t.model_copy() for t in DEFAULT_CANCELLATION_POLICY]
    )

    @model_validator(mode="after")
    def _validate(self) -> "PaymentPlan":
        if self.deposit_type == DepositType.PERCENT and not (1 <= self.deposit_value <= 90):
            raise ValueError("deposit_value percent deve essere 1-90")
        # Policy: ordinata dal più lontano al più vicino, senza duplicati,
        # con percentuali non crescenti (più ti avvicini, meno rimborso).
        tiers = self.cancellation_policy
        if not tiers:
            raise ValueError("cancellation_policy non può essere vuota")
        days = [t.days_before for t in tiers]
        if days != sorted(days, reverse=True) or len(set(days)) != len(days):
            raise ValueError("scaglioni policy in ordine decrescente di days_before, senza duplicati")
        pcts = [t.refund_percent for t in tiers]
        if pcts != sorted(pcts, reverse=True):
            raise ValueError("refund_percent non può crescere avvicinandosi all'evento")
        return self

    def refund_percent_at(self, days_before_start: int) -> int:
        """Percentuale di rimborso per una rinuncia a `days_before_start`
        giorni dall'inizio. Scaglione: il primo (dal più lontano) il cui
        days_before è <= ai giorni rimanenti."""
        if days_before_start < 0:
            return 0
        for tier in self.cancellation_policy:
            if days_before_start >= tier.days_before:
                return tier.refund_percent
        return 0
