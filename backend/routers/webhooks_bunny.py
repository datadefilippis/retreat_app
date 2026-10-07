"""
Webhook Bunny Stream — AC1 (7/10/2026). POST /api/webhooks/bunny

Bunny chiama a ogni cambio di stato di un video: {VideoLibraryId, VideoGuid,
Status}. Si verifica la firma (HMAC-SHA256 del corpo con la ReadOnlyApiKey
della libreria, header X-BunnyStream-Signature), si trova la lezione che
porta quel video e si aggiorna lo stato; quando e' pronto si leggono da
Bunny durata, dimensione e miniatura. Idempotente: lo stesso evento due
volte scrive gli stessi valori. Non fa mai fede per i pagamenti.

Risposte: 200 sempre quando la firma e' valida (anche se il video non e'
nostro: Bunny non deve ritentare), 401 con firma assente o sbagliata, 404
con libreria sconosciuta.
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Request, status

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/webhooks/bunny", tags=["Accademia"])


async def applica_evento(org_id: str, lib: dict, video_guid: str, stato: str) -> dict:
    """Trova la lezione con quel video e scrive lo stato (+ durata, dimensione,
    miniatura quando e' pronto). Restituisce cosa ha fatto."""
    from database import courses_collection
    from services.bunny import gestito
    corso = await courses_collection.find_one(
        {"organization_id": org_id, "$or": [{"modules.lessons.video.guid": video_guid}, {"trailer.guid": video_guid}]},
        {"_id": 0, "id": 1, "modules": 1, "trailer": 1})
    if not corso:
        return {"esito": "video_non_nostro"}
    dettagli = {}
    if stato == "pronto":
        try:
            from services.bunny.client import BunnyClient
            async with BunnyClient(lib["api_key"]) as c:
                v = await c.get_video(str(lib["library_id"]), video_guid)
            dettagli = {
                "duration_seconds": int(v.get("length") or 0),
                "size_bytes": int(v.get("storageSize") or 0),
                "thumbnail_url": gestito.url_thumbnail(lib, v),
            }
        except Exception as exc:  # noqa: BLE001 — pronto resta pronto, i dettagli si rileggono dopo
            logger.warning("webhook bunny: dettagli video %s non letti: %s", video_guid, exc)
    now = datetime.now(timezone.utc).isoformat()
    toccata = None
    delta_bytes = 0
    # AC3 — il trailer del corso
    tr = corso.get("trailer") or {}
    if tr.get("guid") == video_guid:
        prima = int(tr.get("size_bytes") or 0)
        tr["stato"] = stato
        tr["updated_at"] = now
        if dettagli:
            tr.update({k: v for k, v in dettagli.items() if v is not None})
            delta_bytes = int(tr.get("size_bytes") or 0) - prima
        await courses_collection.update_one({"id": corso["id"], "organization_id": org_id},
                                            {"$set": {"trailer": tr, "updated_at": now}})
        if delta_bytes:
            await gestito.aggiorna_quota(org_id, lib.get("id"), delta_bytes, 0)
        return {"esito": "aggiornata", "trailer": True, "stato": stato}
    for m in corso.get("modules") or []:
        for l in m.get("lessons") or []:
            vid = l.get("video") or {}
            if vid.get("guid") != video_guid:
                continue
            prima = int(vid.get("size_bytes") or 0)
            vid["stato"] = stato
            vid["updated_at"] = now
            if dettagli:
                vid.update({k: v for k, v in dettagli.items() if v is not None})
                if dettagli.get("duration_seconds"):
                    l["duration_seconds"] = dettagli["duration_seconds"]
                delta_bytes = int(vid.get("size_bytes") or 0) - prima
                # il player legacy e il firmatario leggono questi due campi
                l["bunny_video_guid"] = video_guid
                l["bunny_library_id"] = lib.get("id")
            l["video"] = vid
            toccata = l["id"]
    if not toccata:
        return {"esito": "lezione_non_trovata"}
    await courses_collection.update_one(
        {"id": corso["id"], "organization_id": org_id},
        {"$set": {"modules": corso["modules"], "updated_at": now}})
    if delta_bytes:
        await gestito.aggiorna_quota(org_id, lib.get("id"), delta_bytes, 0)
    return {"esito": "aggiornata", "lezione_id": toccata, "stato": stato}


@router.post("")
async def webhook_bunny(request: Request):
    from services.bunny import gestito
    corpo = await request.body()
    try:
        dati = json.loads(corpo or b"{}")
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="corpo non valido")
    library_id = str(dati.get("VideoLibraryId") or "")
    video_guid = str(dati.get("VideoGuid") or "")
    if not library_id or not video_guid:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="campi mancanti")
    org = await gestito.org_per_libreria(library_id)
    lib = gestito.libreria_per_id_bunny(org, library_id) if org else None
    if not org or not lib:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="libreria sconosciuta")
    firma = request.headers.get("X-BunnyStream-Signature")
    if not gestito.firma_webhook_valida(corpo, firma, lib.get("read_only_api_key")):
        logger.warning("webhook bunny: firma non valida per libreria %s", library_id)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="firma non valida")
    stato = gestito.stato_da_bunny(dati.get("Status"))
    esito = await applica_evento(org["id"], lib, video_guid, stato)
    return {"ok": True, **esito}
