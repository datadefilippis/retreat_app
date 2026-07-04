"""
Track E Step 2.2 — Store embed configuration router.

Endpoint dedicati per merchant per gestire embed setup di OGNI store:
  - GET    /api/stores/{store_id}/embed-info       → snippet + status
  - PATCH  /api/stores/{store_id}/allowed-origins  → manage allowed list

Modular design — NO monolith
============================

Questo router e' separato da:
  - routers/stores.py (CRUD stores generale, troppo affollato per
    aggiungere embed-specific logic)
  - routers/admin.py (4000+ righe legacy, sarebbe carico aggiuntivo)

Single responsibility: embed configuration. Permette di:
  - Test isolated del flow embed config
  - Sentinel pin focused sul contract embed-management
  - Future extension (es. embed analytics endpoints) qui senza
    inflate stores.py o admin.py

Auth contract
=============

Tutti endpoint richiedono require_verified_admin (org admin + email verificata, R8).
Multi-tenant safety:
  - Store deve appartenere a current_user.organization_id
  - 404 se store non esiste OR cross-org access tentato
  - Sentinel pin del check.

Anti-XSS / Anti-injection
=========================

allowed_origins gia' validato dal Pydantic Store model
(models/store.py _validate_allowed_origins):
  - Max 10 entries (cache LRU bounded)
  - Max 200 chars each
  - Must start http:// or https://
  - Rejects "null", "*", empty, duplicates
  - Strip whitespace

Pattern qui: re-validate via stesso helper Pydantic → consistency
tra POST /stores (create) e PATCH /stores/{id}/allowed-origins.

Audit logging
=============

PATCH allowed-origins → audit log action='STORE_EMBED_ORIGINS_UPDATED'
con before/after diff per forensic. Operatore vede chi ha aggiunto
quale dominio quando (GDPR compliance + security forensic post-incident).

Public API
==========

GET /api/stores/{store_id}/embed-info:
    Response: {
      "store_id", "store_slug", "store_name", "is_published",
      "snippet": str (HTML ready per copy),
      "bundle_url": str (canonical CDN URL),
      "hosted_url": str (afianco.ch/s/{slug}),
      "allowed_origins": [str, ...],
      "embed_status": "active" | "no_origins" | "store_unpublished",
    }

PATCH /api/stores/{store_id}/allowed-origins:
    Body: {"allowed_origins": [str, ...]}
    Response: same as GET embed-info post-update.
"""

import logging
from typing import Dict, List

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field, field_validator

from auth import require_verified_admin
from core.embed_distribution import (
    generate_embed_snippet,
    get_embed_bundle_url,
    get_hosted_storefront_url,
)
from core.embed_blocks import compose_alacarte, get_blocks_catalog
from core.embed_preview import mint_preview_token
from core.embed_versioning import apply_api_version
from services.embed_init_service import _aggregate_categories
from models.store import _validate_allowed_origins
from database import stores_collection, audit_logs_collection
from models.common import generate_id, utc_now

logger = logging.getLogger(__name__)

# Mount sotto /stores resource: sub-resource embed-* del singolo store.
# Coerente con REST conventions (stores → storeId → embed sub-resource).
router = APIRouter(prefix="/stores", tags=["Store Embed Configuration"])


# ── Request / response models ──────────────────────────────────────────


class AllowedOriginsUpdate(BaseModel):
    """Body per PATCH /stores/{id}/allowed-origins.

    Validation riusa il helper Pydantic di models/store.py per
    consistency cross-endpoint (create + update vedono stessa logica).
    """

    allowed_origins: List[str] = Field(
        default_factory=list,
        description=(
            "Lista esatta di origin autorizzati. Sostituisce completamente "
            "la lista esistente (semantica REPLACE, non APPEND). Per "
            "rimuovere un origin: GET, modifica array, PATCH."
        ),
    )

    @field_validator("allowed_origins")
    @classmethod
    def _validate(cls, v):
        # Riusa logica canonical da models/store.py — single source of
        # truth per validation rules (max 10, http/https only, no
        # wildcard, max 200 char each, no duplicates, no "null").
        return _validate_allowed_origins(v)


class StoreEmbedInfoResponse(BaseModel):
    """Response per GET /stores/{id}/embed-info.

    Single source of truth per il frontend modal: contiene TUTTO ciò
    che la UX merchant ha bisogno di mostrare per la sezione "Condividi".

    Field stability = CONTRACT (sentinel pinned). Additions OK,
    rimozioni o rinomine richiedono bump version embed-SDK.
    """

    store_id: str
    store_slug: str
    store_name: str
    is_published: bool
    # Distribution
    bundle_url: str = Field(
        description=(
            "URL canonical del JS bundle embed. Configurato via env "
            "EMBED_CDN_BASE_URL (default nginx self-host). Sentinel "
            "verifica che cambio env → cambio URL automatic."
        )
    )
    hosted_url: str = Field(
        description=(
            "URL hosted storefront afianco-side. Funziona sempre, no "
            "setup richiesto. Pattern: https://app.afianco.ch/s/{slug}"
        )
    )
    snippet: str = Field(
        description="HTML snippet completo ready per copy-to-clipboard"
    )
    # Embed configuration
    allowed_origins: List[str]
    embed_status: str = Field(
        description=(
            "Status overall: "
            "'active' = published + has origins, embed funzionante. "
            "'no_origins' = published ma no allowed_origins (solo hosted). "
            "'store_unpublished' = store non pubblicato (hosted + embed off)."
        )
    )
    # Embed à-la-carte (Fase 3) — catalogo blocchi selezionabili per il
    # builder "Componi" nel tab Embed. Data-driven: la UI deriva da qui.
    blocks_catalog: List[dict] = Field(
        default_factory=list,
        description="Blocchi embeddabili selezionabili (id, label, group, needs).",
    )
    # Categorie pubbliche dello store (slug normalizzato = quello che la
    # grid usa via attributo `category`). Per il CategoryPicker del builder.
    categories: List[dict] = Field(
        default_factory=list,
        description="Categorie: {name, slug, count}.",
    )


# ── Embed à-la-carte — compose snippet (Fase 3) ───────────────────────


class EmbedSnippetComposeRequest(BaseModel):
    """Body per POST /stores/{id}/embed-snippet.

    Lo slug NON e' nel body: viene derivato server-side dallo store
    (sicurezza multi-tenant — un admin non puo' generare snippet per un
    altro store). Il client passa solo la SELEZIONE di blocchi + la config.
    """

    blocks: List[str] = Field(
        default_factory=list,
        description="Id dei blocchi selezionati (es. ['cart-button','categories']).",
    )
    config: Dict[str, dict] = Field(
        default_factory=dict,
        description="Config per-blocco: {block_id: {field_key: value}}.",
    )


class StoreEmbedSnippetResponse(BaseModel):
    """Snippet à-la-carte composto, in 3 sezioni guidate + testo unito."""

    head: str = Field(description="<script ...> una-tantum (config di pagina).")
    elements: List[dict] = Field(description="Elementi scelti: {id,label,html}.")
    singletons: List[dict] = Field(description="Singleton da montare 1 volta.")
    snippet: str = Field(description="Tutto unito, pronto da copiare.")


class StoreEmbedPreviewTokenResponse(BaseModel):
    """Token preview read-only per l'anteprima live nella dashboard."""

    token: str
    expires_in: int = Field(description="Validita' in secondi.")
    bundle_url: str
    slug: str


# ── Helper interno ─────────────────────────────────────────────────────


def _compute_embed_status(is_published: bool, allowed_origins: List[str]) -> str:
    """Compute UX status per merchant dashboard indicator."""
    if not is_published:
        return "store_unpublished"
    if not allowed_origins:
        return "no_origins"
    return "active"


async def _load_store_or_404(store_id: str, org_id: str) -> dict:
    """Carica store con multi-tenant scoping. Raise 404 se non trovato
    OR cross-org. Helper riutilizzato cross-endpoint."""
    store = await stores_collection.find_one(
        {"id": store_id, "organization_id": org_id},
        {
            "_id": 0,
            "id": 1,
            "slug": 1,
            "name": 1,
            "is_published": 1,
            "allowed_origins": 1,
            "organization_id": 1,
        },
    )
    if not store:
        # 404 anche su cross-org (anti-enumeration: non distinguere
        # "store esiste in altra org" da "store non esiste").
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Store not found",
        )
    return store


def _build_embed_info_response(
    store: dict, categories: List[dict] | None = None
) -> StoreEmbedInfoResponse:
    """Build response da store doc. Helper testable in isolation.

    ``categories`` e' opzionale: passato dagli endpoint async (che lo
    aggregano dal DB); default [] per i percorsi che non ne hanno bisogno.
    """
    slug = store.get("slug") or ""
    origins = store.get("allowed_origins") or []
    is_pub = bool(store.get("is_published", False))
    return StoreEmbedInfoResponse(
        store_id=store["id"],
        store_slug=slug,
        store_name=store.get("name") or "",
        is_published=is_pub,
        bundle_url=get_embed_bundle_url(),
        hosted_url=get_hosted_storefront_url(slug) if slug else "",
        snippet=generate_embed_snippet(slug) if slug else "",
        allowed_origins=origins,
        embed_status=_compute_embed_status(is_pub, origins),
        blocks_catalog=get_blocks_catalog(),
        categories=categories or [],
    )


async def _store_categories(org_id: str, store_id: str) -> List[dict]:
    """Categorie pubbliche dello store (slug coerente con la grid)."""
    try:
        return await _aggregate_categories(org_id, store_id)
    except Exception as exc:  # soft-fail: il builder funziona anche senza
        logger.warning("embed-info categories aggregation failed: %s", exc)
        return []


# ── Endpoints ──────────────────────────────────────────────────────────


@router.get(
    "/{store_id}/embed-info",
    response_model=StoreEmbedInfoResponse,
    summary="Get embed configuration info for merchant dashboard",
)
async def get_store_embed_info(
    store_id: str,
    current_user: dict = Depends(require_verified_admin),
) -> StoreEmbedInfoResponse:
    """Return tutto cio' che il merchant ha bisogno per:
      - Vedere URL hosted (link condivisibile sempre)
      - Copiare snippet HTML per embed esterno
      - Vedere origin autorizzati
      - Vedere status (active / no_origins / unpublished)

    Multi-tenant: store deve appartenere a current_user.organization_id.
    """
    org_id = current_user["organization_id"]
    store = await _load_store_or_404(store_id, org_id)
    categories = await _store_categories(org_id, store["id"])
    return _build_embed_info_response(store, categories)


@router.post(
    "/{store_id}/embed-snippet",
    response_model=StoreEmbedSnippetResponse,
    summary="Componi uno snippet embed à-la-carte da una selezione di blocchi",
)
async def compose_store_embed_snippet(
    store_id: str,
    body: EmbedSnippetComposeRequest,
    current_user: dict = Depends(require_verified_admin),
) -> StoreEmbedSnippetResponse:
    """Genera lo snippet à-la-carte per il builder "Componi".

    Sicurezza:
      - Multi-tenant: lo store deve appartenere all'org dell'utente.
      - Lo SLUG e' derivato server-side dallo store (mai dal client) → un
        admin non puo' generare snippet per uno store di un'altra org.
      - La composizione e' validata/sanificata in ``compose_alacarte``
        (slug, category slug, product id). Input invalido → 422.
    """
    org_id = current_user["organization_id"]
    store = await _load_store_or_404(store_id, org_id)
    slug = store.get("slug") or ""
    if not slug:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Store has no slug",
        )
    try:
        composed = compose_alacarte(slug, body.blocks, body.config)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        )
    return StoreEmbedSnippetResponse(
        head=composed.head,
        elements=list(composed.elements),
        singletons=list(composed.singletons),
        snippet=composed.snippet,
    )


@router.get(
    "/{store_id}/embed-preview-token",
    response_model=StoreEmbedPreviewTokenResponse,
    summary="Token read-only per l'anteprima live dell'embed nella dashboard",
)
async def get_store_embed_preview_token(
    store_id: str,
    current_user: dict = Depends(require_verified_admin),
) -> StoreEmbedPreviewTokenResponse:
    """Genera un token preview a breve durata per il PROPRIO store.

    Permette l'anteprima live (init/products/categories) dall'origin
    dell'admin senza aggiungerlo agli allowed_origins pubblici. Read-only:
    il middleware accetta il bypass solo per le GET.
    """
    org_id = current_user["organization_id"]
    store = await _load_store_or_404(store_id, org_id)
    slug = store.get("slug") or ""
    if not slug:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Store has no slug"
        )
    token, ttl = mint_preview_token(slug, store["id"], org_id)
    return StoreEmbedPreviewTokenResponse(
        token=token,
        expires_in=ttl,
        bundle_url=get_embed_bundle_url(),
        slug=slug,
    )


@router.patch(
    "/{store_id}/allowed-origins",
    response_model=StoreEmbedInfoResponse,
    summary="Update allowed origins for store embed (replaces full list)",
)
async def update_store_allowed_origins(
    store_id: str,
    body: AllowedOriginsUpdate,
    current_user: dict = Depends(require_verified_admin),
) -> StoreEmbedInfoResponse:
    """Update allowed_origins per store.

    Semantica REPLACE: il body.allowed_origins sostituisce COMPLETAMENTE
    la lista esistente. Per APPEND: client fa GET → modifica array →
    PATCH.

    Validation:
      - Pydantic _validate_allowed_origins (max 10, http/https only,
        no wildcard, max 200 char, no duplicates, no "null")
      - HTTPException 422 su input invalid

    Audit:
      - Action: 'STORE_EMBED_ORIGINS_UPDATED'
      - Records: before + after lists + actor user_id
      - Non-blocking (fail audit non rompe update)
    """
    org_id = current_user["organization_id"]

    # Load store (multi-tenant scoped)
    store = await _load_store_or_404(store_id, org_id)

    previous_origins = list(store.get("allowed_origins") or [])
    new_origins = body.allowed_origins  # gia' validato

    # No-op shortcut: se identico, skip DB write + audit (idempotency).
    if previous_origins == new_origins:
        cats = await _store_categories(org_id, store["id"])
        return _build_embed_info_response(store, cats)

    # Atomic update + return latest doc
    updated = await stores_collection.find_one_and_update(
        {"id": store_id, "organization_id": org_id},
        {"$set": {
            "allowed_origins": new_origins,
            "updated_at": utc_now(),
        }},
        return_document=True,  # ReturnDocument.AFTER
        projection={
            "_id": 0,
            "id": 1, "slug": 1, "name": 1, "is_published": 1,
            "allowed_origins": 1, "organization_id": 1,
        },
    )
    if not updated:
        # Race: store cancellato tra _load_store_or_404 e update.
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Store not found (deleted during update)",
        )

    # Audit log (non-blocking)
    try:
        now_dt = utc_now()
        await audit_logs_collection.insert_one({
            "id": generate_id(),
            "actor_user_id": current_user.get("user_id"),
            "actor_role": current_user.get("role"),
            "organization_id": org_id,
            "action": "STORE_EMBED_ORIGINS_UPDATED",
            "target_type": "store",
            "target_id": store_id,
            "metadata": {
                "store_slug": store.get("slug"),
                "previous_origins": previous_origins,
                "new_origins": new_origins,
                "added": [o for o in new_origins if o not in previous_origins],
                "removed": [o for o in previous_origins if o not in new_origins],
            },
            "created_at": now_dt.isoformat(),
            # Phase 1 Step D3 — BSON Date for TTL index (365 days)
            "expire_at": now_dt,
        })
    except Exception as audit_err:
        # Audit failure NON deve bloccare la response — log + continue.
        logger.warning(
            "store_embed_origins_update audit insert failed (continuing): %s",
            audit_err,
        )

    logger.info(
        "store_embed_origins_updated: store=%s org=%s user=%s "
        "added=%d removed=%d",
        store_id, org_id, current_user.get("user_id"),
        len([o for o in new_origins if o not in previous_origins]),
        len([o for o in previous_origins if o not in new_origins]),
    )

    # R13 — invalida la cache slug→org così la nuova allowed_origins è
    # effettiva subito (no finestra di staleness ≤TTL su un dato CORS-rilevante).
    try:
        from routers.public import _invalidate_resolve_org_cache
        _invalidate_resolve_org_cache(updated.get("slug"))
    except Exception:  # pragma: no cover — best-effort, mai bloccare l'update
        pass

    cats = await _store_categories(org_id, updated["id"])
    return _build_embed_info_response(updated, cats)


__all__ = ["router"]
