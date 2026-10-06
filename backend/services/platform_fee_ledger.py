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
    # P0 (6/10/2026) — la fee per riga timbra la percentuale EFFETTIVA
    # (importo/transato): e' quella vera anche su ordini misti
    eff = meta.get("application_fee_effective_percent")
    if eff not in (None, ""):
        try:
            return float(eff)
        except (TypeError, ValueError):
            pass
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
    fee_minor: Optional[int] = None,
    fee_by_type: Optional[dict] = None,
) -> None:
    """Upsert idempotente di una riga del ledger. Best-effort: un
    errore qui NON deve mai bloccare il flusso di pagamento — si
    logga e si va avanti (il backfill può ricostruire).

    P0 (6/10/2026): `fee_minor` esplicito (la fee per riga, esatta al
    centesimo) vince sul calcolo dalla percentuale; `fee_by_type` e' la
    scomposizione per tipo di riga, informativa."""
    from database import db
    from models.common import utc_now

    if fee_minor is None:
        fee_minor = (compute_fee_minor(int(amount_minor), fee_percent)
                     if amount_minor >= 0
                     else -compute_fee_minor(-int(amount_minor), fee_percent))
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
                "fee_minor": int(fee_minor),
                "fee_by_type": fee_by_type or None,
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
    # P0 — l'importo esatto timbrato alla creazione (fee per riga)
    meta = session.get("metadata") or {}
    fee_minor = None
    fee_by_type = None
    raw_minor = meta.get("application_fee_minor")
    if raw_minor not in (None, ""):
        try:
            fee_minor = int(raw_minor)
        except (TypeError, ValueError):
            fee_minor = None
    raw_types = meta.get("fee_by_type")
    if raw_types:
        try:
            import json as _json
            fee_by_type = _json.loads(raw_types)
        except Exception:  # noqa: BLE001
            fee_by_type = None
    await record_platform_fee(
        entry_key=str(session.get("id") or f"order:{order_id}:{kind}:{row_seq}"),
        organization_id=organization_id,
        order_id=order_id,
        kind=kind,
        amount_minor=int(amount),
        fee_percent=fee_percent,
        currency=session.get("currency"),
        row_seq=row_seq,
        fee_minor=fee_minor,
        fee_by_type=fee_by_type,
    )


async def resolve_fee_percent_for_order(order_id: str, org_id: str) -> float:
    """P0 — per i RIMBORSI: la percentuale effettiva con cui l'ordine e'
    stato incassato (ultima riga positiva del ledger), cosi' lo storno
    pro-quota e' coerente con l'incasso anche su ordini misti. Fallback:
    l'org (storico)."""
    from database import db
    try:
        riga = await db.platform_fee_ledger.find_one(
            {"order_id": order_id, "organization_id": org_id, "amount_minor": {"$gt": 0}},
            {"_id": 0, "fee_percent": 1}, sort=[("collected_at", -1)])
        if riga and riga.get("fee_percent") is not None:
            return float(riga["fee_percent"])
    except Exception as exc:  # noqa: BLE001
        logger.warning("platform_fee_ledger: lettura fee ordine %s fallita: %s", order_id, exc)
    return await resolve_fee_percent({}, org_id)
