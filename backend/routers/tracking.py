"""VT — POST /api/public/track: il beacon delle visite.

Contratto: fire-and-forget dal frontend (sendBeacon), risponde SEMPRE
204 — anche su input rotto o errore interno. Un tracker che rompe una
pagina pubblica costa più del dato che raccoglie.

Il canale arriva dal client (che sa referrer e ?store=1) ma superficie
e slug vengono RIVALIDATI qui: l'org si risolve dal nostro db, mai dal
payload, quindi non si possono gonfiare i numeri di un'altra org
inventando id.
"""

import logging
from typing import Optional

from fastapi import APIRouter, Request, Response
from pydantic import BaseModel, Field

from routers.auth import limiter
from services.visit_tracking import CHANNELS, SURFACES, record_view

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Tracking"])


class TrackPayload(BaseModel):
    surface: str = Field(max_length=20)
    slug: str = Field(min_length=1, max_length=120)
    channel: str = Field(max_length=20)
    referrer_host: Optional[str] = Field(default=None, max_length=100)
    lang: Optional[str] = Field(default=None, max_length=5)


async def _resolve_org_for(surface: str, slug: str) -> Optional[str]:
    """org_id dalla superficie+slug, con le STESSE regole del pubblico:
    profile/store → store slug o public_slug; event → occurrence slug."""
    from database import (stores_collection, organizations_collection,
                          event_occurrences_collection)
    if surface in ("profile", "store"):
        store = await stores_collection.find_one(
            {"slug": slug, "is_published": True},
            {"_id": 0, "organization_id": 1})
        if store:
            return store["organization_id"]
        org = await organizations_collection.find_one(
            {"public_slug": slug}, {"_id": 0, "id": 1})
        return (org or {}).get("id")
    if surface == "event":
        occ = await event_occurrences_collection.find_one(
            {"slug": slug, "status": "published"},
            {"_id": 0, "organization_id": 1})
        return (occ or {}).get("organization_id")
    return None


@router.post("/public/track", status_code=204)
@limiter.limit("30/minute")
async def track_view(request: Request, payload: TrackPayload) -> Response:
    try:
        if payload.surface in SURFACES and payload.channel in CHANNELS:
            org_id = await _resolve_org_for(payload.surface, payload.slug)
            if org_id:
                await record_view(
                    organization_id=org_id,
                    surface=payload.surface,
                    slug=payload.slug,
                    channel=payload.channel,
                    referrer_host=payload.referrer_host,
                    lang=payload.lang,
                    ip=(request.client.host if request.client else None),
                    user_agent=request.headers.get("user-agent"),
                )
    except Exception as exc:          # noqa: BLE001 — best-effort assoluto
        logger.debug("track skipped: %s", exc)
    return Response(status_code=204)
