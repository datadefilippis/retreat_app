"""Newsletter forms — admin CRUD router (F1, modulo Newsletter).

Risorsa **org-scoped** (store opzionale). Pattern coerente con coupons /
store_embed: multi-tenant via ``current_user["organization_id"]``, auth
``require_verified_admin`` (questi endpoint gestiscono anche gli allowed_origins
embed → stesso gate di store_embed, R8).

Endpoints (prefix ``/api/newsletter-forms``):
  GET    ""                         lista form dell'org
  POST   ""                         crea form (slug derivato da name se assente)
  GET    "/{form_id}"               dettaglio
  PATCH  "/{form_id}"               update parziale
  DELETE "/{form_id}"               elimina
  PATCH  "/{form_id}/allowed-origins"  sostituisce gli origins (REPLACE)
  GET    "/{form_id}/submissions"   iscrizioni (filtrabili per sorgente)
"""

import logging
from typing import Optional, List

from fastapi import APIRouter, HTTPException, Depends, Request, Query, status
from pydantic import BaseModel
from pymongo.errors import DuplicateKeyError

from auth import require_verified_admin
from routers.auth import limiter
from models.newsletter import (
    NewsletterForm,
    NewsletterFormCreate,
    NewsletterFormUpdate,
)
from models.event_occurrence import slugify
from models.store import _validate_allowed_origins
from models.common import utc_now

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/newsletter-forms", tags=["Newsletter Forms"])

_MAX_SLUG_ATTEMPTS = 50


async def _unique_slug(org_id: str, base: str) -> str:
    """Genera uno slug unico per l'org a partire da `base` (append -2,-3,…)."""
    from database import newsletter_forms_collection
    root = slugify(base)[:46] or "form"
    candidate = root
    for n in range(1, _MAX_SLUG_ATTEMPTS):
        exists = await newsletter_forms_collection.find_one(
            {"organization_id": org_id, "slug": candidate}, {"_id": 1},
        )
        if not exists:
            return candidate
        candidate = f"{root}-{n + 1}"
    # Fallback estremo: suffisso dall'id generato.
    from models.common import generate_id
    return f"{root}-{generate_id()[:6]}"


async def _load_form_or_404(org_id: str, form_id: str) -> dict:
    from database import newsletter_forms_collection
    form = await newsletter_forms_collection.find_one(
        {"id": form_id, "organization_id": org_id}, {"_id": 0},
    )
    if not form:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Form non trovato")
    return form


@router.get("")
async def list_newsletter_forms(
    store_id: Optional[str] = Query(None),
    current_user: dict = Depends(require_verified_admin),
):
    from database import newsletter_forms_collection
    org_id = current_user["organization_id"]
    query: dict = {"organization_id": org_id}
    if store_id:
        query["store_id"] = store_id
    cursor = newsletter_forms_collection.find(query, {"_id": 0}).sort("created_at", -1).limit(200)
    return await cursor.to_list(200)


@router.post("", status_code=status.HTTP_201_CREATED)
@limiter.limit("20/minute")
async def create_newsletter_form(
    request: Request,
    body: NewsletterFormCreate,
    current_user: dict = Depends(require_verified_admin),
):
    from database import newsletter_forms_collection
    org_id = current_user["organization_id"]

    # store_id opzionale: se fornito, deve appartenere all'org (multi-tenant).
    if body.store_id:
        from database import stores_collection
        store = await stores_collection.find_one(
            {"id": body.store_id, "organization_id": org_id}, {"_id": 1},
        )
        if not store:
            raise HTTPException(status_code=400, detail="Store non valido per questa org")

    slug = body.slug or await _unique_slug(org_id, body.name)

    form = NewsletterForm(
        organization_id=org_id,
        slug=slug,
        name=body.name,
        store_id=body.store_id,
        collect_name=body.collect_name,
        collect_phone=body.collect_phone,
        field_configs=body.field_configs,
        consent_text=body.consent_text,
        privacy_required=body.privacy_required,
        success_message=body.success_message,
        redirect_url=body.redirect_url,
        allowed_origins=body.allowed_origins,
    )
    doc = form.model_dump(mode="json")
    try:
        await newsletter_forms_collection.insert_one(doc.copy())
    except DuplicateKeyError:
        # Race sullo slug: ritenta una volta con slug derivato.
        doc["slug"] = await _unique_slug(org_id, body.name)
        await newsletter_forms_collection.insert_one(doc.copy())
    doc.pop("_id", None)
    return doc


@router.get("/{form_id}")
async def get_newsletter_form(
    form_id: str,
    current_user: dict = Depends(require_verified_admin),
):
    return await _load_form_or_404(current_user["organization_id"], form_id)


@router.patch("/{form_id}")
async def update_newsletter_form(
    form_id: str,
    body: NewsletterFormUpdate,
    current_user: dict = Depends(require_verified_admin),
):
    from database import newsletter_forms_collection
    org_id = current_user["organization_id"]
    await _load_form_or_404(org_id, form_id)

    updates = body.model_dump(exclude_unset=True, mode="json")
    if "store_id" in updates and updates["store_id"]:
        from database import stores_collection
        store = await stores_collection.find_one(
            {"id": updates["store_id"], "organization_id": org_id}, {"_id": 1},
        )
        if not store:
            raise HTTPException(status_code=400, detail="Store non valido per questa org")
    if updates:
        updates["updated_at"] = utc_now().isoformat()
        await newsletter_forms_collection.update_one(
            {"id": form_id, "organization_id": org_id}, {"$set": updates},
        )
    return await _load_form_or_404(org_id, form_id)


@router.delete("/{form_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_newsletter_form(
    form_id: str,
    current_user: dict = Depends(require_verified_admin),
):
    from database import newsletter_forms_collection
    org_id = current_user["organization_id"]
    res = await newsletter_forms_collection.delete_one(
        {"id": form_id, "organization_id": org_id},
    )
    if res.deleted_count == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Form non trovato")
    return None


class _AllowedOriginsBody(BaseModel):
    allowed_origins: List[str] = []


@router.patch("/{form_id}/allowed-origins")
async def update_form_allowed_origins(
    form_id: str,
    body: _AllowedOriginsBody,
    current_user: dict = Depends(require_verified_admin),
):
    from database import newsletter_forms_collection
    org_id = current_user["organization_id"]
    await _load_form_or_404(org_id, form_id)
    origins = _validate_allowed_origins(body.allowed_origins)
    await newsletter_forms_collection.update_one(
        {"id": form_id, "organization_id": org_id},
        {"$set": {"allowed_origins": origins, "updated_at": utc_now().isoformat()}},
    )
    # F2 — invalida la cache CORS così i nuovi origins sono effettivi subito
    # (evita la finestra di staleness ≤TTL su un dato CORS-rilevante).
    try:
        from middleware.dynamic_cors import clear_cache
        clear_cache()
    except Exception:  # pragma: no cover — best-effort
        pass
    return await _load_form_or_404(org_id, form_id)


@router.get("/{form_id}/submissions")
async def list_form_submissions(
    form_id: str,
    source: Optional[str] = Query(None, description="filtro per source_label o source_origin"),
    limit: int = Query(200, ge=1, le=1000),
    current_user: dict = Depends(require_verified_admin),
):
    from database import newsletter_subscriptions_collection
    org_id = current_user["organization_id"]
    await _load_form_or_404(org_id, form_id)
    query: dict = {"organization_id": org_id, "form_id": form_id}
    if source:
        query["$or"] = [{"source_label": source}, {"source_origin": source}]
    cursor = newsletter_subscriptions_collection.find(query, {"_id": 0}).sort(
        "created_at", -1,
    ).limit(limit)
    return await cursor.to_list(limit)
