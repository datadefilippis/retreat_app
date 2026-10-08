"""LE PLAYLIST di Aurya Sound — SN0 (8/10/2026, piano Aurya Sound).

Una playlist e' una raccolta CURATA di meditazioni pubblicate, con copertina,
racconto e ordine. Vive in `sound_playlists`, additiva: le tracce non
cambiano, la playlist tiene solo i loro id in ordine.

Regole (decisioni del founder, 8/10):
- la crea chi ha Crea Studio (`require_sound_crea`), SOLO con tracce proprie,
  pubblicate e NON riservate (stessa guardia di `_traccia_mia` dei corsi);
- la pubblicazione e' della chiave 1 (`sound_composer`): come per le
  meditazioni pubbliche. Senza chiave 1 resta bozza (403 al publish);
- `accesso`: «cerchio» (default, gratis per chi e' nel Cerchio) o «piu»
  (abbonati, quando il Piu' si accendera': fino ad allora e' un'etichetta);
- in pubblico si vedono SOLO le playlist pubblicate con almeno una traccia
  ancora pubblicata; la lettura pubblica passa dallo STESSO cancello del
  catalogo (`_has_catalog_access`): senza sblocco 403 `locked`.
"""
from __future__ import annotations

import logging
import uuid
from typing import List, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, Query, Request, UploadFile, status
from pydantic import BaseModel, Field

from models.common import utc_now
from models.frequency_track import ACCESSI, clean_accesso
from routers.frequencies import (
    _has_catalog_access, require_sound_crea, solo_pubbliche,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/frequencies/playlists", tags=["Frequenze"])

TITLE_MAX = 120
DESCRIPTION_MAX = 2000
TRACCE_MAX = 60
PLAYLISTS_MAX_PER_ORG = 100
COVER_MAX_BYTES = 5 * 1024 * 1024
COVER_EXT = {"jpg": "image/jpeg", "jpeg": "image/jpeg", "png": "image/png", "webp": "image/webp"}

_PROIEZIONE = {"_id": 0}


class PlaylistCreate(BaseModel):
    title: str = Field(min_length=1, max_length=TITLE_MAX)
    description: Optional[str] = Field(default=None, max_length=DESCRIPTION_MAX)
    accesso: Optional[str] = None
    tracce: Optional[List[str]] = None       # id delle tracce, in ordine


class PlaylistUpdate(BaseModel):
    title: Optional[str] = Field(default=None, min_length=1, max_length=TITLE_MAX)
    description: Optional[str] = Field(default=None, max_length=DESCRIPTION_MAX)
    accesso: Optional[str] = None
    in_vetrina: Optional[bool] = None
    tracce: Optional[List[str]] = None


def _doc(p: dict) -> dict:
    p.pop("_id", None)
    return p


async def _mia(playlist_id: str, org_id: str) -> dict:
    from database import sound_playlists_collection
    p = await sound_playlists_collection.find_one({"id": playlist_id, "organization_id": org_id}, _PROIEZIONE)
    if not p:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Playlist non trovata.")
    return p


async def _tracce_mie_pubbliche(org_id: str, ids: List[str]) -> List[str]:
    """Gli id, nell'ordine dato, SOLO se tracce dell'org, pubblicate e non
    riservate; gli altri cadono (mai un errore silenzioso: si rispondono gli
    scartati)."""
    from database import frequency_tracks_collection
    puliti = list(dict.fromkeys(str(i) for i in ids if i))[:TRACCE_MAX]
    if not puliti:
        return []
    valide = {t["id"] async for t in frequency_tracks_collection.find(
        solo_pubbliche({"id": {"$in": puliti}, "organization_id": org_id, "status": "published"}),
        {"_id": 0, "id": 1})}
    return [i for i in puliti if i in valide]


async def _riga(p: dict) -> dict:
    """La playlist con le sue tracce (titolo, durata, slug, copertina,
    accesso), nell'ordine; le tracce ritirate nel frattempo non compaiono."""
    from database import frequency_tracks_collection
    ids = p.get("tracce") or []
    docs = {t["id"]: t async for t in frequency_tracks_collection.find(
        solo_pubbliche({"id": {"$in": ids}, "status": "published"}),
        {"_id": 0, "id": 1, "slug": 1, "title": 1, "intent": 1, "duration_sec": 1, "score.duration_sec": 1,
         "cover_url": 1, "accesso": 1, "has_voce": 1, "plays_total": 1})}
    tracce = []
    for i in ids:
        t = docs.get(i)
        if not t:
            continue
        tracce.append({"id": t["id"], "slug": t.get("slug"), "title": t.get("title"), "intent": t.get("intent"),
                       "duration_sec": t.get("duration_sec") or (t.get("score") or {}).get("duration_sec"),
                       "cover_url": t.get("cover_url"), "accesso": t.get("accesso") or "cerchio",
                       "has_voce": bool(t.get("has_voce")), "plays_total": t.get("plays_total") or 0})
    out = {k: p.get(k) for k in ("id", "slug", "title", "description", "cover_url", "accesso", "in_vetrina",
                                 "status", "published_at", "plays_total", "created_at", "updated_at", "annuncio")}
    out["accesso"] = out.get("accesso") or "cerchio"
    out["tracce"] = tracce
    out["tracce_count"] = len(tracce)
    out["duration_sec"] = sum(int(t.get("duration_sec") or 0) for t in tracce)
    return out


# ── il gestionale (Crea → Playlist) ──────────────────────────────────────

@router.get("/mine")
async def mie(current_user: dict = Depends(require_sound_crea)):
    from database import sound_playlists_collection
    items = []
    async for p in sound_playlists_collection.find(
            {"organization_id": current_user["organization_id"]}, _PROIEZIONE).sort("updated_at", -1).limit(PLAYLISTS_MAX_PER_ORG):
        items.append(await _riga(p))
    return {"items": items, "sound_composer": bool(current_user.get("_sound_composer"))}


@router.post("", status_code=status.HTTP_201_CREATED)
async def crea(payload: PlaylistCreate, current_user: dict = Depends(require_sound_crea)):
    from database import sound_playlists_collection
    org_id = current_user["organization_id"]
    if await sound_playlists_collection.count_documents({"organization_id": org_id}) >= PLAYLISTS_MAX_PER_ORG:
        raise HTTPException(status_code=400, detail=f"Limite di {PLAYLISTS_MAX_PER_ORG} playlist raggiunto.")
    now = utc_now()
    p = {"id": str(uuid.uuid4()), "organization_id": org_id, "title": payload.title.strip(),
         "description": (payload.description or "").strip()[:DESCRIPTION_MAX],
         "accesso": clean_accesso(payload.accesso), "in_vetrina": False, "status": "draft",
         "slug": None, "slug_precedenti": [], "cover_url": None, "plays_total": 0,
         "tracce": await _tracce_mie_pubbliche(org_id, payload.tracce or []),
         "created_at": now, "updated_at": now}
    await sound_playlists_collection.insert_one(dict(p))
    return await _riga(p)


@router.get("/mine/{playlist_id}")
async def una_mia(playlist_id: str, current_user: dict = Depends(require_sound_crea)):
    return await _riga(await _mia(playlist_id, current_user["organization_id"]))


@router.patch("/{playlist_id}")
async def modifica(playlist_id: str, payload: PlaylistUpdate, current_user: dict = Depends(require_sound_crea)):
    from database import sound_playlists_collection
    org_id = current_user["organization_id"]
    await _mia(playlist_id, org_id)
    upd = {}
    if payload.title is not None:
        upd["title"] = payload.title.strip()
    if payload.description is not None:
        upd["description"] = payload.description.strip()[:DESCRIPTION_MAX]
    if payload.accesso is not None:
        upd["accesso"] = clean_accesso(payload.accesso)
    if payload.in_vetrina is not None:
        upd["in_vetrina"] = bool(payload.in_vetrina)
    if payload.tracce is not None:
        upd["tracce"] = await _tracce_mie_pubbliche(org_id, payload.tracce)
    if not upd:
        raise HTTPException(status_code=400, detail="Nessuna modifica.")
    upd["updated_at"] = utc_now()
    p = await sound_playlists_collection.find_one_and_update(
        {"id": playlist_id, "organization_id": org_id}, {"$set": upd}, return_document=True)
    return await _riga(_doc(p))


@router.post("/{playlist_id}/copertina")
async def copertina(playlist_id: str, file: UploadFile = File(...), current_user: dict = Depends(require_sound_crea)):
    from database import sound_playlists_collection
    from services.object_storage import save_public_upload
    org_id = current_user["organization_id"]
    await _mia(playlist_id, org_id)
    ext = (file.filename or "").rsplit(".", 1)[-1].lower() if "." in (file.filename or "") else ""
    if ext not in COVER_EXT:
        raise HTTPException(status_code=400, detail="Formato non ammesso: jpg, png o webp.")
    data = await file.read()
    if not data or len(data) > COVER_MAX_BYTES:
        raise HTTPException(status_code=400, detail="Immagine vuota o oltre 5 MB.")
    url = save_public_upload("playlists", f"{playlist_id}.{uuid.uuid4().hex[:8]}.{ext}", data, content_type=COVER_EXT[ext])
    await sound_playlists_collection.update_one({"id": playlist_id, "organization_id": org_id},
                                                {"$set": {"cover_url": url, "updated_at": utc_now()}})
    return {"cover_url": url}


async def _slug_libero(base: str, escludi_id: Optional[str] = None) -> str:
    from models.event_occurrence import slugify
    from database import sound_playlists_collection
    root = slugify(base)[:46] or "playlist"
    cand = root
    for n in range(2, 60):
        filtro = {"$or": [{"slug": cand}, {"slug_precedenti": cand}]}
        if escludi_id:
            filtro["id"] = {"$ne": escludi_id}
        if not await sound_playlists_collection.find_one(filtro, {"_id": 1}):
            return cand
        cand = f"{root}-{n}"
    return f"{root}-{uuid.uuid4().hex[:6]}"


@router.post("/{playlist_id}/publish")
async def pubblica(playlist_id: str, current_user: dict = Depends(require_sound_crea)):
    """Solo la chiave 1 pubblica (come le meditazioni pubbliche); serve
    almeno una traccia valida. Lo slug segue il titolo, i vecchi restano."""
    from database import sound_playlists_collection
    from models.event_occurrence import slugify
    org_id = current_user["organization_id"]
    if not current_user.get("_sound_composer"):
        raise HTTPException(status_code=403, detail="Le playlist pubbliche sono su invito, come le Meditazioni di Aurya.")
    p = await _mia(playlist_id, org_id)
    tracce = await _tracce_mie_pubbliche(org_id, p.get("tracce") or [])
    if not tracce:
        raise HTTPException(status_code=400, detail="Serve almeno una meditazione pubblicata nella playlist.")
    slug = p.get("slug")
    root = slugify(p["title"])[:46] or "playlist"
    precedenti = list(p.get("slug_precedenti") or [])
    if not slug or not (slug == root or slug.startswith(root + "-")):
        if slug:
            precedenti = list(dict.fromkeys(precedenti + [slug]))
        slug = await _slug_libero(p["title"], escludi_id=playlist_id)
    now = utc_now()
    await sound_playlists_collection.update_one(
        {"id": playlist_id, "organization_id": org_id},
        {"$set": {"status": "published", "slug": slug, "slug_precedenti": precedenti, "tracce": tracce,
                  "published_at": p.get("published_at") or now, "updated_at": now}})
    return await _riga(await _mia(playlist_id, org_id))


@router.post("/{playlist_id}/annuncia")
async def annuncia(playlist_id: str, sfondo: BackgroundTasks, a_secco: bool = Query(False),
                   current_user: dict = Depends(require_sound_crea)):
    """SN2 — l'annuncio al Cerchio: «nuova playlist», con il link diretto.
    Solo la chiave 1, solo pubblicata, una volta sola; `a_secco=1` conta e
    mostra l'anteprima senza spedire."""
    from database import sound_playlists_collection
    from services import annunci_sound
    if not annunci_sound.attivo():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Gli annunci al Cerchio sono spenti.")
    org_id = current_user["organization_id"]
    if not current_user.get("_sound_composer"):
        raise HTTPException(status_code=403, detail="L'annuncio al Cerchio è su invito, come le Meditazioni di Aurya.")
    p = await _riga(await _mia(playlist_id, org_id))
    if p.get("status") != "published" or not p.get("slug") or not p.get("tracce"):
        raise HTTPException(status_code=409, detail="Si annuncia solo una playlist pubblicata con almeno una meditazione.")
    testo = annunci_sound.testo_annuncio("playlist", p)
    lista = await annunci_sound.destinatari()
    esito = {"destinatari": len(lista), "oggetto": testo["oggetto"], "anteprima": testo["corpo"],
             "gia_annunciata": (p.get("annuncio") or {}).get("at")}
    if a_secco:
        return esito
    if p.get("annuncio"):
        raise HTTPException(status_code=409, detail="Questa playlist è già stata annunciata al Cerchio.")
    if not lista:
        raise HTTPException(status_code=409, detail="Nessun destinatario nel Cerchio.")
    if not await annunci_sound.prenota(sound_playlists_collection, playlist_id, len(lista)):
        raise HTTPException(status_code=409, detail="Questa playlist è già stata annunciata al Cerchio.")
    sfondo.add_task(annunci_sound.spedisci, "playlist", sound_playlists_collection, playlist_id,
                    testo["oggetto"], testo["corpo"], testo["percorso"], lista)
    return {**esito, "avviato": True}


@router.post("/{playlist_id}/unpublish")
async def ritira(playlist_id: str, current_user: dict = Depends(require_sound_crea)):
    from database import sound_playlists_collection
    org_id = current_user["organization_id"]
    await _mia(playlist_id, org_id)
    await sound_playlists_collection.update_one({"id": playlist_id, "organization_id": org_id},
                                                {"$set": {"status": "draft", "in_vetrina": False, "updated_at": utc_now()}})
    return await _riga(await _mia(playlist_id, org_id))


@router.delete("/{playlist_id}", status_code=status.HTTP_204_NO_CONTENT)
async def elimina(playlist_id: str, current_user: dict = Depends(require_sound_crea)):
    from database import sound_playlists_collection
    r = await sound_playlists_collection.delete_one({"id": playlist_id, "organization_id": current_user["organization_id"]})
    if r.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Playlist non trovata.")


# ── il pubblico (dietro lo stesso cancello del catalogo) ─────────────────

async def _pubblicate() -> List[dict]:
    from database import sound_playlists_collection
    out = []
    async for p in sound_playlists_collection.find({"status": "published"}, _PROIEZIONE).sort("published_at", -1).limit(200):
        r = await _riga(p)
        if r["tracce_count"]:
            out.append(r)
    return out


@router.get("")
async def lista_pubblica(request: Request):
    if not await _has_catalog_access(request):
        from database import sound_playlists_collection
        n = await sound_playlists_collection.count_documents({"status": "published"})
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail={"error": "locked", "playlists_count": n})
    return {"items": await _pubblicate()}


@router.get("/{slug}")
async def una_pubblica(slug: str, request: Request):
    if not await _has_catalog_access(request):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail={"error": "locked"})
    from database import sound_playlists_collection
    p = await sound_playlists_collection.find_one(
        {"status": "published", "$or": [{"slug": slug}, {"slug_precedenti": slug}]}, _PROIEZIONE)
    if not p:
        raise HTTPException(status_code=404, detail="Playlist non trovata.")
    return await _riga(p)


@router.post("/{slug}/play", status_code=status.HTTP_204_NO_CONTENT)
async def conta_play(slug: str):
    from database import sound_playlists_collection
    await sound_playlists_collection.update_one(
        {"status": "published", "$or": [{"slug": slug}, {"slug_precedenti": slug}]}, {"$inc": {"plays_total": 1}})


__all__ = ["router", "ACCESSI"]
