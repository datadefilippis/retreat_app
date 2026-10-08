"""MR4 (8/10/2026) — Regia → Sound → Categorie delle meditazioni.

  GET   /admin/sound/categorie          → tutte (anche spente) + quante meditazioni per categoria
  POST  /admin/sound/categorie          → nuova (slug dal titolo, immutabile)
  PATCH /admin/sound/categorie/{slug}   → label, descrizione, tono, ordine, attiva (mai cancellare)
Solo system admin. Ogni scrittura ricarica il registro: la scelta in Crea
e i filtri della casa la vedono subito, senza deploy.
"""
from fastapi import APIRouter, Body, Depends, HTTPException

from auth import require_system_admin
from services import categorie_sound as C

router = APIRouter(prefix="/admin/sound/categorie", tags=["Admin Sound"])


@router.get("")
async def elenco(_: dict = Depends(require_system_admin)) -> dict:
    from database import frequency_tracks_collection
    voci = await C.elenco(solo_attive=False)
    conteggi = {}
    async for r in frequency_tracks_collection.aggregate([
            {"$match": {"status": "published", "visibility": {"$ne": "private"}}},
            {"$group": {"_id": "$categoria", "n": {"$sum": 1}}}]):
        conteggi[r["_id"] or ""] = r["n"]
    return {"categorie": [{**c, "meditazioni": conteggi.get(c["slug"], 0)} for c in voci],
            "senza_categoria": conteggi.get("", 0), "toni": list(C.TONI)}


@router.post("", status_code=201)
async def crea(body: dict = Body(...), _: dict = Depends(require_system_admin)) -> dict:
    from database import db
    from models.common import utc_now
    try:
        doc = C.valida_nuova(body)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    if await db.sound_categorie.find_one({"slug": doc["slug"]}, {"_id": 1}):
        raise HTTPException(status_code=409, detail=f"«{doc['slug']}» esiste già.")
    await db.sound_categorie.insert_one({**doc, "created_at": utc_now(), "updated_at": utc_now()})
    await C.ricarica()
    return {"categoria": doc}


@router.patch("/{slug}")
async def modifica(slug: str, body: dict = Body(...), _: dict = Depends(require_system_admin)) -> dict:
    from database import db
    from models.common import utc_now
    if not await db.sound_categorie.find_one({"slug": slug}, {"_id": 1}):
        raise HTTPException(status_code=404, detail="Categoria non trovata.")
    try:
        upd = C.valida_modifica(body)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    if not upd:
        raise HTTPException(status_code=400, detail="Nessuna modifica.")
    await db.sound_categorie.update_one({"slug": slug}, {"$set": {**upd, "updated_at": utc_now()}})
    await C.ricarica()
    doc = await db.sound_categorie.find_one({"slug": slug}, {"_id": 0})
    return {"categoria": doc}
