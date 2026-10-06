"""P1 (6/10/2026) — PRODOTTI: fisici e digitali venduti dal profilo.

Un'entità sola (`Product` con `item_type` digital | physical), pagamento
sempre immediato (transaction_mode=direct, price_mode=fixed), tre
lucchetti alla pubblicazione imposti qui (il frontend li mostra, il
backend li impone):
  1. incassi collegati (Stripe pronto: la stessa regola del checkout),
  2. patto di responsabilità accettato (DPA, come listino e ritiri),
  3. pagina pubblica raggiungibile (store o public_slug),
  + per i digitali: il file caricato.

Riusa le fondamenta: creazione/modifica via routers.products (slug,
quota, tassonomia, sanificazione), upload file via
/products/{id}/digital-file (con il limite del piano), statistiche via
sales-stats. Tutto sotto require_module("prodotti") + interruttore di
regia prodotti_spento (services/module_access.KILL_SWITCH_FLAGS).
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import BaseModel, ConfigDict, Field

from auth import get_verified_user_strict as get_verified_user
from services.module_access import require_module

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/prodotti", tags=["Prodotti"])

TIPI_PRODOTTO = ("digital", "physical")
ETICHETTE_TIPO = {"digital": "Digitale", "physical": "Fisico"}

_gate = require_module("prodotti")


class ProdottoCreate(BaseModel):
    model_config = ConfigDict(extra="ignore")
    item_type: Literal["digital", "physical"]
    name: str = Field(min_length=1, max_length=255)
    description: Optional[str] = Field(default=None, max_length=2000)
    unit_price: float = Field(ge=0)
    image_url: Optional[str] = Field(default=None, max_length=500)
    category: Optional[str] = Field(default=None, max_length=40)
    # fisici
    stock_quantity: Optional[int] = Field(default=None, ge=0)
    # digitali (facoltativi: niente = illimitato / senza scadenza)
    max_downloads_per_delivery: Optional[int] = Field(default=None, ge=1, le=1000)
    access_expiry_days: Optional[int] = Field(default=None, ge=1, le=3650)
    long_description: Optional[str] = Field(default=None, max_length=20000)


class ProdottoUpdate(BaseModel):
    model_config = ConfigDict(extra="ignore")
    name: Optional[str] = Field(default=None, min_length=1, max_length=255)
    description: Optional[str] = Field(default=None, max_length=2000)
    unit_price: Optional[float] = Field(default=None, ge=0)
    image_url: Optional[str] = Field(default=None, max_length=500)
    category: Optional[str] = Field(default=None, max_length=40)
    stock_quantity: Optional[int] = Field(default=None, ge=0)
    max_downloads_per_delivery: Optional[int] = Field(default=None, ge=0, le=1000)   # 0 = illimitato
    access_expiry_days: Optional[int] = Field(default=None, ge=0, le=3650)           # 0 = mai
    long_description: Optional[str] = Field(default=None, max_length=20000)


# ── helpers ──────────────────────────────────────────────────────────────

async def _prerequisiti(org_id: str) -> Dict[str, Any]:
    """I tre lucchetti della pubblicazione, letti dalle stesse fonti del
    checkout e dei ritiri (mai un flag parallelo)."""
    from services.payment_resolution import get_org_checkout_readiness
    from services.dpa_guard import get_dpa_ack
    from services.store_guard import org_has_public_home
    readiness = await get_org_checkout_readiness(org_id)
    stripe_pronto = bool((readiness or {}).get("checkout_available"))
    patto = bool(await get_dpa_ack(org_id))
    pagina = bool(await org_has_public_home(org_id))
    return {
        "stripe_pronto": stripe_pronto,
        "patto": patto,
        "pagina_pubblica": pagina,
        "stripe_motivo": (readiness or {}).get("reason_message") if not stripe_pronto else None,
    }


def _ragioni_pubblicazione(prod: dict, pre: Dict[str, Any]) -> List[str]:
    """Le ragioni (in italiano) per cui un prodotto NON si può pubblicare."""
    ragioni: List[str] = []
    if not pre.get("stripe_pronto"):
        ragioni.append("Collega gli incassi con Stripe: i prodotti si pagano subito, online.")
    if not pre.get("patto"):
        ragioni.append("Accetta il patto di responsabilità (Impostazioni → Condizioni dell'operatore).")
    if not pre.get("pagina_pubblica"):
        ragioni.append("La tua pagina pubblica non è ancora online.")
    if float(prod.get("unit_price") or 0) <= 0:
        ragioni.append("Metti un prezzo maggiore di zero.")
    if prod.get("item_type") == "digital" and not ((prod.get("metadata") or {}).get("download_filename")):
        ragioni.append("Carica il file che il cliente riceverà.")
    return ragioni


async def _venduti_30gg(org_id: str, product_ids: List[str]) -> Dict[str, int]:
    """Pezzi venduti negli ultimi 30 giorni per prodotto (ordini non annullati)."""
    if not product_ids:
        return {}
    from database import orders_collection
    da = (datetime.now(timezone.utc) - timedelta(days=30)).isoformat()
    pipeline = [
        {"$match": {"organization_id": org_id, "created_at": {"$gte": da},
                    "status": {"$nin": ["cancelled", "draft"]},
                    "items.product_id": {"$in": product_ids}}},
        {"$unwind": "$items"},
        {"$match": {"items.product_id": {"$in": product_ids}}},
        {"$group": {"_id": "$items.product_id", "n": {"$sum": {"$ifNull": ["$items.quantity", 1]}}}},
    ]
    out: Dict[str, int] = {}
    try:
        async for r in orders_collection.aggregate(pipeline):
            out[r["_id"]] = int(r.get("n") or 0)
    except Exception as exc:  # noqa: BLE001 — un conteggio non ferma la lista
        logger.warning("prodotti: venduti_30gg fallito org=%s: %s", org_id, exc)
    return out


def _riga(prod: dict, venduti: Dict[str, int], pre: Dict[str, Any]) -> dict:
    meta = prod.get("metadata") or {}
    file_ = None
    if prod.get("item_type") == "digital" and meta.get("download_filename"):
        file_ = {"filename": meta.get("download_filename"),
                 "size_bytes": meta.get("download_size_bytes"),
                 "mime_type": meta.get("download_mime_type")}
    return {
        "id": prod["id"],
        "name": prod.get("name"),
        "slug": prod.get("slug"),
        "item_type": prod.get("item_type"),
        "tipo_etichetta": ETICHETTE_TIPO.get(prod.get("item_type"), prod.get("item_type")),
        "description": prod.get("description"),
        "unit_price": prod.get("unit_price"),
        "currency": prod.get("currency") or "EUR",
        "image_url": prod.get("image_url"),
        "category": prod.get("category"),
        "is_published": bool(prod.get("is_published")),
        "stock_quantity": prod.get("stock_quantity"),
        "file": file_,
        "max_downloads_per_delivery": meta.get("max_downloads_per_delivery"),
        "access_expiry_days": meta.get("access_expiry_days"),
        "long_description": meta.get("long_description"),
        "venduti_30gg": venduti.get(prod["id"], 0),
        "created_at": prod.get("created_at"),
        "updated_at": prod.get("updated_at"),
        "ragioni_pubblicazione": _ragioni_pubblicazione(prod, pre),
    }


async def _mio_prodotto(product_id: str, org_id: str) -> dict:
    from database import products_collection
    prod = await products_collection.find_one(
        {"id": product_id, "organization_id": org_id, "item_type": {"$in": list(TIPI_PRODOTTO)},
         "is_active": {"$ne": False}},
        {"_id": 0})
    if not prod:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Prodotto non trovato")
    return prod


# ── rotte ────────────────────────────────────────────────────────────────

@router.get("")
async def lista_prodotti(current_user: dict = Depends(get_verified_user), _=Depends(_gate)):
    """I prodotti (fisici e digitali) dell'org con venduti a 30 giorni e i
    prerequisiti per vendere (una volta per lista, non per riga)."""
    from database import products_collection
    org_id = current_user["organization_id"]
    rows = await products_collection.find(
        {"organization_id": org_id, "item_type": {"$in": list(TIPI_PRODOTTO)},
         "is_active": {"$ne": False}},
        {"_id": 0}).sort("created_at", -1).to_list(500)
    pre = await _prerequisiti(org_id)
    venduti = await _venduti_30gg(org_id, [r["id"] for r in rows])
    from services.module_access import get_module_entitlements
    ent = await get_module_entitlements(org_id, "prodotti")
    limiti = (ent or {}).get("limits") or {}
    return {
        "prodotti": [_riga(r, venduti, pre) for r in rows],
        "total": len(rows),
        "prerequisiti": pre,
        "limiti": {"products_max": limiti.get("products_max"), "max_file_mb": limiti.get("max_file_mb")},
    }


@router.post("", status_code=status.HTTP_201_CREATED)
async def crea_prodotto(body: ProdottoCreate, current_user: dict = Depends(get_verified_user),
                        _=Depends(_gate)):
    """Nuovo prodotto in BOZZA (mai pubblicato alla creazione): pagamento
    immediato, prezzo fisso. Passa da routers.products.create_product per
    slug, quota a catalogo, tassonomia e patto (409 DPA_REQUIRED)."""
    from database import products_collection
    from models.product import ProductCreate
    from routers.products import create_product
    from services.module_access import enforce_count_quota
    org_id = current_user["organization_id"]

    attuali = await products_collection.count_documents(
        {"organization_id": org_id, "item_type": {"$in": list(TIPI_PRODOTTO)}, "is_active": {"$ne": False}})
    await enforce_count_quota(
        org_id, "prodotti", "products_max", current_count=attuali,
        message_template="Hai raggiunto il limite di {limit} prodotti del tuo piano. Con il Pro ne hai di più.",
        hard_abuse_cap=5000)

    metadata: Dict[str, Any] = {}
    if body.item_type == "digital":
        if body.max_downloads_per_delivery:
            metadata["max_downloads_per_delivery"] = int(body.max_downloads_per_delivery)
        if body.access_expiry_days:
            metadata["access_expiry_days"] = int(body.access_expiry_days)
    if body.long_description:
        metadata["long_description"] = body.long_description

    data = ProductCreate(
        name=body.name.strip(),
        description=(body.description or "").strip() or None,
        category=body.category or None,
        unit_price=float(body.unit_price),
        image_url=body.image_url or None,
        item_type=body.item_type,
        unit_label="file" if body.item_type == "digital" else "pz",
        price_mode="fixed",
        transaction_mode="direct",
        is_published=False,
        stock_quantity=(body.stock_quantity if body.item_type == "physical" else None),
        metadata=metadata,
    )
    created = await create_product(data, Response(), current_user)
    prod = created.model_dump() if hasattr(created, "model_dump") else dict(created)
    pre = await _prerequisiti(org_id)
    logger.info("prodotti: creato %s (%s) org=%s", prod.get("id"), body.item_type, org_id)
    return _riga(prod, {}, pre)


@router.get("/{product_id}")
async def dettaglio_prodotto(product_id: str, current_user: dict = Depends(get_verified_user),
                             _=Depends(_gate)):
    org_id = current_user["organization_id"]
    prod = await _mio_prodotto(product_id, org_id)
    pre = await _prerequisiti(org_id)
    venduti = await _venduti_30gg(org_id, [product_id])
    return _riga(prod, venduti, pre)


@router.patch("/{product_id}")
async def modifica_prodotto(product_id: str, body: ProdottoUpdate,
                            current_user: dict = Depends(get_verified_user), _=Depends(_gate)):
    """Modifica dei campi del prodotto; i metadati del file (filename,
    size, mime) non si toccano da qui: li scrive solo l'upload."""
    from models.product import ProductUpdate
    from routers.products import update_product
    org_id = current_user["organization_id"]
    prod = await _mio_prodotto(product_id, org_id)
    campi: Dict[str, Any] = {}
    for k in ("name", "description", "unit_price", "image_url", "category"):
        v = getattr(body, k)
        if v is not None:
            campi[k] = v.strip() if isinstance(v, str) else v
    if body.stock_quantity is not None and prod.get("item_type") == "physical":
        campi["stock_quantity"] = body.stock_quantity
    meta = dict(prod.get("metadata") or {})
    toccata = False
    if body.max_downloads_per_delivery is not None:
        toccata = True
        if body.max_downloads_per_delivery > 0:
            meta["max_downloads_per_delivery"] = int(body.max_downloads_per_delivery)
        else:
            meta.pop("max_downloads_per_delivery", None)
    if body.access_expiry_days is not None:
        toccata = True
        if body.access_expiry_days > 0:
            meta["access_expiry_days"] = int(body.access_expiry_days)
        else:
            meta.pop("access_expiry_days", None)
    if body.long_description is not None:
        toccata = True
        if body.long_description.strip():
            meta["long_description"] = body.long_description
        else:
            meta.pop("long_description", None)
    if toccata:
        campi["metadata"] = meta
    if not campi:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Niente da modificare")
    await update_product(product_id, ProductUpdate(**campi), Response(), current_user)
    prod = await _mio_prodotto(product_id, org_id)
    pre = await _prerequisiti(org_id)
    return _riga(prod, await _venduti_30gg(org_id, [product_id]), pre)


@router.post("/{product_id}/pubblica")
async def pubblica_prodotto(product_id: str, current_user: dict = Depends(get_verified_user),
                            _=Depends(_gate)):
    """I tre lucchetti (+ il file per i digitali): 409 con le ragioni se
    manca qualcosa, altrimenti il prodotto va online sul profilo."""
    from models.product import ProductUpdate
    from routers.products import update_product
    org_id = current_user["organization_id"]
    prod = await _mio_prodotto(product_id, org_id)
    pre = await _prerequisiti(org_id)
    ragioni = _ragioni_pubblicazione(prod, pre)
    if ragioni:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT,
                            detail={"code": "non_pubblicabile", "ragioni": ragioni})
    await update_product(product_id, ProductUpdate(is_published=True), Response(), current_user)
    prod = await _mio_prodotto(product_id, org_id)
    logger.info("prodotti: pubblicato %s org=%s", product_id, org_id)
    return _riga(prod, await _venduti_30gg(org_id, [product_id]), pre)


@router.post("/{product_id}/ritira")
async def ritira_prodotto(product_id: str, current_user: dict = Depends(get_verified_user),
                          _=Depends(_gate)):
    """Torna in bozza: sparisce dal profilo, i file già comprati restano scaricabili."""
    from models.product import ProductUpdate
    from routers.products import update_product
    org_id = current_user["organization_id"]
    await _mio_prodotto(product_id, org_id)
    await update_product(product_id, ProductUpdate(is_published=False), Response(), current_user)
    prod = await _mio_prodotto(product_id, org_id)
    return _riga(prod, {}, await _prerequisiti(org_id))


@router.delete("/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
async def elimina_prodotto(product_id: str, current_user: dict = Depends(get_verified_user),
                           _=Depends(_gate)):
    """Disattiva (mai cancellazione fisica: gli ordini passati lo citano)."""
    from routers.products import deactivate_product
    org_id = current_user["organization_id"]
    await _mio_prodotto(product_id, org_id)
    await deactivate_product(product_id, current_user)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/{product_id}/vendite")
async def vendite_prodotto(product_id: str, current_user: dict = Depends(get_verified_user),
                           _=Depends(_gate)):
    """Statistiche di vendita: riusa /products/{id}/sales-stats."""
    from routers.products import product_sales_stats
    org_id = current_user["organization_id"]
    await _mio_prodotto(product_id, org_id)
    return await product_sales_stats(product_id, current_user, _module=current_user)
