"""SA1 — libro mastro delle fee di piattaforma (docs/SYSTEM_ADMIN_360_PIANO).

Ogni incasso ONLINE (Stripe) scrive una riga: quanto è transitato
sull'operatore e quanto ne trattiene la piattaforma. È la fonte di
verità per "quanto guadagno da ogni operatore" (SA2/SA4): niente
stime a posteriori, l'importo e la percentuale vengono timbrati al
momento del webhook, quando sono certi.

Regole:
  - scrivono qui SOLO i flussi Stripe (checkout, saldi/rate, rimborsi);
    il mark-paid manuale e la pagina Dati non generano fee (=0) e non
    compaiono;
  - idempotente: una riga per session_id / refund id (upsert), così i
    retry del webhook non raddoppiano mai;
  - i rimborsi Stripe scrivono una riga NEGATIVA (kind='refund'): gli
    aggregati restano onesti anche dopo uno storno.

Documento (collection ``platform_fee_ledger``):
  entry_key      chiave idempotente (session_id o refund:<id>)
  organization_id, order_id
  kind           checkout | schedule_row | refund
  row_seq        riga schedule pagata (solo schedule_row)
  amount_minor   transato (negativo sui refund)
  fee_percent    percentuale applicata al momento dell'incasso
  fee_minor      fee piattaforma in minor units (negativa sui refund)
  currency, collected_at
"""

import logging
from decimal import Decimal, ROUND_HALF_UP
from typing import Optional

logger = logging.getLogger(__name__)


def compute_fee_minor(amount_minor: int, fee_percent: float) -> int:
    """Fee in minor units, arrotondamento commerciale (HALF_UP)."""
    return int((Decimal(amount_minor) * Decimal(str(fee_percent)) / 100)
               .quantize(Decimal("1"), rounding=ROUND_HALF_UP))


async def resolve_fee_percent(session: dict, org_id: str) -> float:
    """La percentuale VERA dell'incasso: prima dal metadata della
    session (timbrata alla creazione del checkout — sopravvive ai
    cambi piano avvenuti nel frattempo), poi dall'org come fallback
    per le session create prima di SA1."""
    meta = session.get("metadata") or {}
    raw = meta.get("application_fee_percent")
    if raw not in (None, ""):
        try:
            return float(raw)
        except (TypeError, ValueError):
            pass
    from database import organizations_collection
    org = await organizations_collection.find_one(
        {"id": org_id}, {"_id": 0, "application_fee_percent": 1}) or {}
    return float(org.get("application_fee_percent") or 0)


async def record_platform_fee(
    *,
    entry_key: str,
    organization_id: str,
    order_id: Optional[str],
    kind: str,
    amount_minor: int,
    fee_percent: float,
    currency: Optional[str],
    row_seq: Optional[int] = None,
    collected_at: Optional[str] = None,
) -> None:
    """Upsert idempotente di una riga del ledger. Best-effort: un
    errore qui NON deve mai bloccare il flusso di pagamento — si
    logga e si va avanti (il backfill può ricostruire)."""
    from database import db
    from models.common import utc_now

    try:
        await db.platform_fee_ledger.update_one(
            {"entry_key": entry_key},
            {"$setOnInsert": {
                "entry_key": entry_key,
                "organization_id": organization_id,
                "order_id": order_id,
                "kind": kind,
                "row_seq": row_seq,
                "amount_minor": int(amount_minor),
                "fee_percent": float(fee_percent),
                "fee_minor": compute_fee_minor(int(amount_minor), fee_percent)
                             if amount_minor >= 0
                             else -compute_fee_minor(-int(amount_minor), fee_percent),
                "currency": (currency or "eur").lower(),
                "collected_at": collected_at or utc_now().isoformat(),
            }},
            upsert=True,
        )
    except Exception as exc:  # mai bloccare il pagamento per il ledger
        logger.error("platform_fee_ledger: write failed (%s, %s): %s",
                     entry_key, organization_id, exc)


async def record_from_session(
    session: dict,
    *,
    organization_id: str,
    order_id: str,
    kind: str,
    row_seq: Optional[int] = None,
) -> None:
    """Riga ledger da una checkout session Stripe riconciliata."""
    amount = session.get("amount_total")
    if not amount or int(amount) <= 0:
        return
    fee_percent = await resolve_fee_percent(session, organization_id)
    await record_platform_fee(
        entry_key=str(session.get("id") or f"order:{order_id}:{kind}:{row_seq}"),
        organization_id=organization_id,
        order_id=order_id,
        kind=kind,
        amount_minor=int(amount),
        fee_percent=fee_percent,
        currency=session.get("currency"),
        row_seq=row_seq,
    )
