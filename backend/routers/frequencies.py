"""Frequenze by Aurya — router bozze (FQ0, 18/8/2026).

CRUD org-scoped delle tracce vibrazionali in stato bozza: l'operatore
compone a /frequenze, salva la ricetta (score JSON), la riprende.
Nessuna superficie pubblica in FQ0 — publish/slug/player arrivano con FQ1,
insieme alla cittadinanza modulo (chiave `frequencies` in MODULE_OWNERSHIP).

Isolamento: collection dedicata `frequency_tracks`, zero riferimenti a
products/orders/stores. Vedi docs/FREQUENZE_PLAN_2026-08.md.
"""

import logging
import os
import uuid
from pathlib import Path
from typing import Optional

from fastapi import (
    APIRouter, Depends, File, Form, HTTPException, UploadFile, status,
)
from pydantic import BaseModel

from auth import get_current_user, require_system_admin
from models.audio_asset import (
    LICENSE_MAX, MAX_FILE_BYTES, SOUND_CATEGORIES,
    clean_category, safe_extension,
)
from models.audio_asset import TITLE_MAX as SOUND_TITLE_MAX
from models.common import utc_now
from models.frequency_track import (
    DESCRIPTION_MAX, TITLE_MAX, clean_intent, clean_score,
)

# i byte delle basi vivono qui, serviti dallo static mount /uploads
AUDIO_DIR = Path(__file__).resolve().parent.parent / "uploads" / "audio"

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/frequencies", tags=["Frequenze"])

TRACKS_MAX_PER_ORG = 200  # tetto anti-runaway: sono documenti da pochi KB

_LIST_PROJECTION = {
    "_id": 0, "id": 1, "title": 1, "intent": 1, "status": 1,
    "created_at": 1, "updated_at": 1,
    # della ricetta, in lista, serve solo la durata
    "score.duration_sec": 1, "score.layers": 1,
}


class TrackCreate(BaseModel):
    title: str
    score: dict
    description: Optional[str] = None
    intent: Optional[str] = None


class TrackUpdate(BaseModel):
    title: Optional[str] = None
    score: Optional[dict] = None
    description: Optional[str] = None
    intent: Optional[str] = None


def _doc(track: dict) -> dict:
    track.pop("_id", None)
    return track


def _validated_score(raw: dict) -> dict:
    score = clean_score(raw)
    if score is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ricetta non valida: serve almeno un livello.")
    return score


@router.get("/tracks")
async def list_tracks(current_user: dict = Depends(get_current_user)):
    from database import frequency_tracks_collection
    items = await frequency_tracks_collection.find(
        {"organization_id": current_user["organization_id"]},
        _LIST_PROJECTION,
    ).sort("updated_at", -1).to_list(TRACKS_MAX_PER_ORG)
    for it in items:
        score = it.pop("score", None) or {}
        it["duration_sec"] = score.get("duration_sec")
        it["layers_count"] = len(score.get("layers") or [])
    return {"items": items}


@router.post("/tracks", status_code=status.HTTP_201_CREATED)
async def create_track(payload: TrackCreate,
                       current_user: dict = Depends(get_current_user)):
    from database import frequency_tracks_collection
    org_id = current_user["organization_id"]
    count = await frequency_tracks_collection.count_documents(
        {"organization_id": org_id})
    if count >= TRACKS_MAX_PER_ORG:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Limite di {TRACKS_MAX_PER_ORG} tracce raggiunto.")
    title = (payload.title or "").strip()[:TITLE_MAX]
    if not title:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="Serve un titolo.")
    now = utc_now()
    track = {
        "id": str(uuid.uuid4()),
        "organization_id": org_id,
        "title": title,
        "description": (payload.description or "").strip()[:DESCRIPTION_MAX],
        "intent": clean_intent(payload.intent),
        "status": "draft",   # publish arriva con FQ1
        "score": _validated_score(payload.score),
        "created_at": now,
        "updated_at": now,
    }
    await frequency_tracks_collection.insert_one(dict(track))
    return _doc(track)


@router.get("/tracks/{track_id}")
async def get_track(track_id: str,
                    current_user: dict = Depends(get_current_user)):
    from database import frequency_tracks_collection
    track = await frequency_tracks_collection.find_one(
        {"id": track_id,
         "organization_id": current_user["organization_id"]})
    if not track:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="Traccia non trovata.")
    return _doc(track)


@router.patch("/tracks/{track_id}")
async def update_track(track_id: str, payload: TrackUpdate,
                       current_user: dict = Depends(get_current_user)):
    from database import frequency_tracks_collection
    updates = {}
    if payload.title is not None:
        title = payload.title.strip()[:TITLE_MAX]
        if not title:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                                detail="Serve un titolo.")
        updates["title"] = title
    if payload.description is not None:
        updates["description"] = payload.description.strip()[:DESCRIPTION_MAX]
    if payload.intent is not None:
        updates["intent"] = clean_intent(payload.intent)
    if payload.score is not None:
        updates["score"] = _validated_score(payload.score)
    if not updates:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="Nessuna modifica.")
    updates["updated_at"] = utc_now()
    result = await frequency_tracks_collection.find_one_and_update(
        {"id": track_id,
         "organization_id": current_user["organization_id"]},
        {"$set": updates}, return_document=True)
    if not result:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="Traccia non trovata.")
    return _doc(result)


@router.delete("/tracks/{track_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_track(track_id: str,
                       current_user: dict = Depends(get_current_user)):
    from database import frequency_tracks_collection
    result = await frequency_tracks_collection.delete_one(
        {"id": track_id,
         "organization_id": current_user["organization_id"]})
    if result.deleted_count == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="Traccia non trovata.")


# ── FQ1 — pubblicazione e ascolto pubblico ──────────────────────────────────
# La traccia pubblicata resta la RICETTA: il player pubblico la
# risintetizza col motore client. Il cancello d'ascolto (anteprima
# libera, poi Lettera o account Aurya) e' un soft-wall lato client:
# il contenuto e' gratuito, il gate e' cattura contatto, non DRM.

_PUBLIC_PROJECTION = {"_id": 0, "id": 1, "slug": 1, "title": 1,
                      "description": 1, "intent": 1, "score": 1,
                      "plays_total": 1, "organization_id": 1}
_SLUG_ATTEMPTS = 50


async def _unique_track_slug(base: str) -> str:
    from models.event_occurrence import slugify
    from database import frequency_tracks_collection
    root = slugify(base)[:46] or "sessione"
    candidate = root
    for n in range(2, _SLUG_ATTEMPTS + 2):
        clash = await frequency_tracks_collection.find_one(
            {"slug": candidate}, {"_id": 1})
        if not clash:
            return candidate
        candidate = f"{root}-{n}"
    return f"{root}-{uuid.uuid4().hex[:6]}"


@router.post("/tracks/{track_id}/publish")
async def publish_track(track_id: str,
                        current_user: dict = Depends(get_current_user)):
    from database import frequency_tracks_collection
    track = await frequency_tracks_collection.find_one(
        {"id": track_id,
         "organization_id": current_user["organization_id"]})
    if not track:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="Traccia non trovata.")
    slug = track.get("slug") or await _unique_track_slug(track["title"])
    await frequency_tracks_collection.update_one(
        {"id": track_id,
         "organization_id": current_user["organization_id"]},
        {"$set": {"status": "published", "slug": slug,
                  "published_at": utc_now(), "updated_at": utc_now()}})
    return {"id": track_id, "status": "published", "slug": slug}


@router.post("/tracks/{track_id}/unpublish")
async def unpublish_track(track_id: str,
                          current_user: dict = Depends(get_current_user)):
    from database import frequency_tracks_collection
    result = await frequency_tracks_collection.find_one_and_update(
        {"id": track_id,
         "organization_id": current_user["organization_id"]},
        # lo slug resta: ripubblicando, il link gia' condiviso rivive
        {"$set": {"status": "draft", "updated_at": utc_now()}})
    if not result:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="Traccia non trovata.")
    return {"id": track_id, "status": "draft"}


@router.get("/public/{slug}")
async def public_track(slug: str):
    """Payload del player pubblico: ricetta + chi l'ha composta."""
    from database import frequency_tracks_collection, organizations_collection
    track = await frequency_tracks_collection.find_one(
        {"slug": slug, "status": "published"}, _PUBLIC_PROJECTION)
    if not track:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="Traccia non trovata.")
    org = await organizations_collection.find_one(
        {"id": track.pop("organization_id")},
        {"_id": 0, "name": 1, "public_slug": 1,
         "public_profile.display_name": 1})
    profile = (org or {}).get("public_profile") or {}
    track["operator"] = {
        "name": profile.get("display_name") or (org or {}).get("name"),
        # lo slug pubblico vive in cima al doc org (non nel profilo)
        "slug": (org or {}).get("public_slug"),
    }
    track["plays_total"] = track.get("plays_total") or 0
    return track


@router.post("/public/{slug}/play", status_code=status.HTTP_204_NO_CONTENT)
async def register_play(slug: str):
    from database import frequency_tracks_collection
    await frequency_tracks_collection.update_one(
        {"slug": slug, "status": "published"},
        {"$inc": {"plays_total": 1}})


# ── FQ2 — libreria suoni curata ─────────────────────────────────────────────
# GET pubblica (contenuto di piattaforma: la vede anche il player FQ1);
# scrittura SOLO system admin, con licenza annotata.

_SOUND_PROJECTION = {"_id": 0, "id": 1, "title": 1, "category": 1,
                     "duration_sec": 1, "size_bytes": 1, "stream_url": 1}


@router.get("/sounds")
async def list_sounds():
    from database import audio_assets_collection
    items = await audio_assets_collection.find(
        {}, _SOUND_PROJECTION).sort("created_at", -1).to_list(500)
    return {"items": items, "categories": SOUND_CATEGORIES}


@router.post("/sounds", status_code=status.HTTP_201_CREATED)
async def upload_sound(file: UploadFile = File(...),
                       title: str = Form(...),
                       category: str = Form(...),
                       duration_sec: float = Form(0),
                       license_note: str = Form(""),
                       admin: dict = Depends(require_system_admin)):
    cat = clean_category(category)
    if not cat:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="Categoria non valida.")
    ext = safe_extension(file.filename)
    if not ext or not (file.content_type or "").startswith("audio/"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="Formato non supportato (mp3, m4a, ogg, wav).")
    clean_title = title.strip()[:SOUND_TITLE_MAX]
    if not clean_title:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="Serve un titolo.")
    data = await file.read()
    if len(data) > MAX_FILE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File oltre {MAX_FILE_BYTES // (1024 * 1024)}MB.")
    asset_id = str(uuid.uuid4())
    AUDIO_DIR.mkdir(parents=True, exist_ok=True)
    path = AUDIO_DIR / f"{asset_id}.{ext}"
    path.write_bytes(data)
    from database import audio_assets_collection
    asset = {
        "id": asset_id,
        "owner": "platform",
        "title": clean_title,
        "category": cat,
        "duration_sec": round(max(0.0, float(duration_sec or 0)), 1),
        "size_bytes": len(data),
        "mime": file.content_type,
        "stream_url": f"/uploads/audio/{asset_id}.{ext}",
        "license_note": (license_note or "").strip()[:LICENSE_MAX],
        "uploaded_by": admin.get("email"),
        "created_at": utc_now(),
    }
    await audio_assets_collection.insert_one(dict(asset))
    asset.pop("_id", None)
    return asset


@router.delete("/sounds/{asset_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_sound(asset_id: str,
                       admin: dict = Depends(require_system_admin)):
    from database import audio_assets_collection
    asset = await audio_assets_collection.find_one({"id": asset_id})
    if not asset:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="Suono non trovato.")
    await audio_assets_collection.delete_one({"id": asset_id})
    stream = asset.get("stream_url") or ""
    fname = os.path.basename(stream)
    if fname:
        try:
            (AUDIO_DIR / fname).unlink(missing_ok=True)
        except OSError:
            logger.warning("file base %s non rimosso", fname)
