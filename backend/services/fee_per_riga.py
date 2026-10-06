"""P0 (6/10/2026) — LA COMMISSIONE LA DECIDE LA RIGA, NON L'ORGANIZZAZIONE.

Promessa stampata: ritiri e servizi senza commissioni, sempre. Sui
PRODOTTI venduti dal profilo (fisici e digitali) la piattaforma trattiene
una percentuale decisa dal piano: 15% nel Gratis, zero nel Pro (decisione
del founder, 6/10/2026), più i costi Stripe che Stripe applica per conto
suo. Fino a oggi il checkout leggeva UNA percentuale per organizzazione
(`application_fee_percent`, azzerata per tutti dal 10/9): resta come
fallback storico, ma la fee vera nasce qui, riga per riga.

Regole:
  - la percentuale per tipo viene dal piano (`transaction_fee_by_type`),
    propagata sull'org (`application_fee_by_type`) al provisioning; se
    l'org non ce l'ha ancora si rilegge dal piano (orgs nate prima);
  - il tipo della riga e' quello VERO del prodotto oggi (lettura fresca):
    lo snapshot `items[].item_type` ha default «physical» e una riga di
    listino vecchia non deve mai pagare una fee da prodotto;
  - solo `physical` e `digital` hanno una chiave nella mappa: tutto il
    resto (service, event_ticket, rental, booking, course) e' 0;
  - lo sconto coupon si ripartisce in proporzione fra le righe; la
    spedizione non ha fee;
  - caparre, saldi e rate (session parziali) portano una QUOTA della fee
    totale in proporzione all'importo: per i ritiri e' 0 comunque;
  - l'importo passa al provider gia' in centesimi (`application_fee_minor`),
    la percentuale «effettiva» viaggia nel metadata solo per il ledger.
"""
from __future__ import annotations

import json
import logging
from decimal import Decimal, ROUND_HALF_UP
from typing import Dict, Iterable, Optional, Tuple

logger = logging.getLogger(__name__)

# i soli tipi che possono avere una commissione (le chiavi della mappa)
TIPI_CON_FEE = ("physical", "digital", "course")   # AC0 (6/10/2026): + corsi online


def _pct(v) -> Decimal:
    try:
        return Decimal(str(v or 0))
    except Exception:  # noqa: BLE001
        return Decimal("0")


def mappa_pulita(raw) -> Dict[str, float]:
    """Solo i tipi ammessi, percentuali 0..100 come float."""
    if not isinstance(raw, dict):
        return {}
    out: Dict[str, float] = {}
    for k in TIPI_CON_FEE:
        if k in raw:
            p = float(_pct(raw.get(k)))
            out[k] = min(max(p, 0.0), 100.0)
    return out


async def mappa_fee_org(org_doc: Optional[dict]) -> Dict[str, float]:
    """La mappa {tipo: percentuale} per un'org: prima dal campo propagato
    al provisioning, poi dal piano commerciale (org nate prima del campo).
    Niente piano, niente mappa → {} (fee 0 su tutto)."""
    org_doc = org_doc or {}
    if isinstance(org_doc.get("application_fee_by_type"), dict):
        return mappa_pulita(org_doc["application_fee_by_type"])
    slug = org_doc.get("commercial_plan_slug")
    if not slug:
        return {}
    try:
        from repositories import billing_repository
        plan = await billing_repository.get_commercial_plan(slug)
    except Exception as exc:  # noqa: BLE001
        logger.warning("fee_per_riga: piano %s non letto: %s", slug, exc)
        return {}
    return mappa_pulita((plan or {}).get("transaction_fee_by_type"))


async def tipi_prodotti(order: dict) -> Dict[str, str]:
    """{product_id: item_type} letto OGGI dai prodotti dell'ordine."""
    ids = [it.get("product_id") for it in (order.get("items") or []) if it.get("product_id")]
    if not ids:
        return {}
    from database import products_collection
    out: Dict[str, str] = {}
    async for p in products_collection.find({"id": {"$in": ids}}, {"_id": 0, "id": 1, "item_type": 1}):
        if p.get("item_type"):
            out[p["id"]] = p["item_type"]
    return out


def scomponi_fee(order: dict, mappa: Dict[str, float], tipi: Optional[Dict[str, str]] = None,
                 discount_major=None) -> Tuple[int, Dict[str, int]]:
    """(fee totale in centesimi, {tipo: fee in centesimi}) per un ordine.

    Base di ogni riga = line_total (gia' con extras e sconto riga), al
    netto della quota di sconto coupon proporzionale. Arrotondamento
    commerciale per riga. Senza mappa → (0, {})."""
    mappa = mappa_pulita(mappa)
    if not mappa:
        return 0, {}
    tipi = tipi or {}
    items = order.get("items") or []
    righe = []
    for it in items:
        amount = it.get("line_total")
        if amount is None:
            amount = float(it.get("unit_price") or 0) * float(it.get("quantity") or 0)
        righe.append((it, Decimal(str(amount or 0))))
    lordo = sum((a for _, a in righe), Decimal("0"))
    sconto = Decimal(str(discount_major if discount_major is not None else (order.get("discount_total") or 0)))
    if sconto < 0:
        sconto = Decimal("0")
    totale = 0
    per_tipo: Dict[str, int] = {}
    for it, amount in righe:
        tipo = tipi.get(it.get("product_id")) or it.get("item_type") or ""
        pct = Decimal(str(mappa.get(tipo, 0)))
        if pct <= 0 or amount <= 0:
            continue
        netto = amount
        if sconto > 0 and lordo > 0:
            netto = amount - (sconto * amount / lordo)
        if netto <= 0:
            continue
        fee = int((netto * 100 * pct / 100).quantize(Decimal("1"), rounding=ROUND_HALF_UP))
        if fee > 0:
            totale += fee
            per_tipo[tipo] = per_tipo.get(tipo, 0) + fee
    return totale, per_tipo


def quota_fee(fee_totale_minor: int, importo_minor: int, totale_ordine_minor: int) -> int:
    """La parte di fee che spetta a una session parziale (caparra, saldo,
    rata): proporzionale all'importo. Totale ordine 0 → 0."""
    if fee_totale_minor <= 0 or importo_minor <= 0 or totale_ordine_minor <= 0:
        return 0
    q = (Decimal(fee_totale_minor) * Decimal(importo_minor) / Decimal(totale_ordine_minor))
    return min(int(q.quantize(Decimal("1"), rounding=ROUND_HALF_UP)), importo_minor)


def percentuale_effettiva(fee_minor: int, importo_minor: int) -> float:
    """La percentuale «vera» da timbrare nel ledger (4 decimali)."""
    if not importo_minor or importo_minor <= 0 or fee_minor <= 0:
        return 0.0
    return float((Decimal(fee_minor) * 100 / Decimal(importo_minor)).quantize(Decimal("0.0001")))


async def fee_per_ordine(org_doc: Optional[dict], order: dict, discount_major=None) -> Tuple[int, Dict[str, int]]:
    """Tutto insieme: mappa dell'org + tipi freschi + scomposizione."""
    mappa = await mappa_fee_org(org_doc)
    if not mappa or not any(v > 0 for v in mappa.values()):
        return 0, {}
    tipi = await tipi_prodotti(order)
    return scomponi_fee(order, mappa, tipi, discount_major)


def metadata_fee(fee_minor: int, per_tipo: Dict[str, int], importo_minor: Optional[int] = None) -> Dict[str, str]:
    """Le chiavi che viaggiano nella session Stripe (stringhe, come vuole Stripe)."""
    out = {"application_fee_minor": str(int(fee_minor or 0))}
    if per_tipo:
        out["fee_by_type"] = json.dumps({k: int(v) for k, v in per_tipo.items()}, separators=(",", ":"))
    if importo_minor:
        out["application_fee_effective_percent"] = str(percentuale_effettiva(fee_minor, importo_minor))
    return out


def totale_ordine_minor(order: dict) -> int:
    try:
        return int((Decimal(str(order.get("total") or 0)) * 100).quantize(Decimal("1"), rounding=ROUND_HALF_UP))
    except Exception:  # noqa: BLE001
        return 0


def somma_minor(line_items: Iterable, discount_major=None) -> int:
    """Centesimi netti di una lista di CheckoutLineItem (per il provider)."""
    lordo = sum(int(round(float(li.unit_amount) * 100)) * int(li.quantity) for li in line_items)
    sconto = int(round(float(discount_major or 0) * 100))
    return max(0, lordo - sconto)
