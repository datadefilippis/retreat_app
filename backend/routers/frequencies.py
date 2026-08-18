"""Frequenze by Aurya — router bozze (FQ0, 18/8/2026).

CRUD org-scoped delle tracce vibrazionali in stato bozza: l'operatore
compone a /frequenze, salva la ricetta (score JSON), la riprende.
Nessuna superficie pubblica in FQ0 — publish/slug/player arrivano con FQ1,
insieme alla cittadinanza modulo (chiave `frequencies` in MODULE_OWNERSHIP).

Isolamento: collection dedicata `frequency_tracks`, zero riferimenti a
products/orders/stores. Vedi docs/FREQUENZE_PLAN_2026-08.md.
"""

import logging
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from auth import get_current_user
from models.common import utc_now
from models.frequency_track import (
    DESCRIPTION_MAX, TITLE_MAX, clean_intent, clean_score,
)

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
