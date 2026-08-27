"""TR3 — LE CONDIVISIONI: un link per contatto, revocabile a persona
(27/8/2026, piano in docs/CREA_TRACCE_RISERVATE_PLAN_2026-08.md §4).

Il modello di fiducia, dichiarato: ogni contatto riceve il SUO link
(`/ascolta/{token}`) — un invito personale, non in elenco, che conta
i propri ascolti. Revocare Marco non tocca Giulia. Chi ascolta NON
crea un account (fase 1); la verifica email per-share e' la fase 2 e
questo modello la prevede gia'.

Il token e' OPACO (secrets, 128+ bit) e vive in database — non un
JWT: la revoca deve avere effetto SUBITO, non alla scadenza. La rotta
d'ascolto controlla ogni volta: share attivo, traccia riservata e
pubblicata, e STUDIO ATTIVO dell'org proprietaria — deciso dal
founder: se l'operatore smette di pagare, i link si spengono (il
cliente vede un messaggio neutro, mai la colpa dell'operatore).

Sicurezza del suono: il master non ha URL pubblici — la consegna
passa da `_risposta_master` (X-Accel in prod, 206 in dev) DOPO il
controllo dello share, come per la via del cerchio.
"""

import secrets
import uuid

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel

from models.common import utc_now
from routers.frequencies import (
    _risposta_master, require_sound_crea, solo_pubbliche,
)

router = APIRouter(prefix="/frequencies", tags=["Condivisioni"])

SHARES_MAX_PER_TRACK = 200   # anti-runaway: documenti da pochi byte

# Il messaggio NEUTRO del link spento: il cliente finale non deve mai
# leggere la contabilita' del suo operatore (decisione founder, v3).
_SPENTO = "Questo ascolto non è al momento disponibile."


def _mio(current_user: dict, **altro) -> dict:
    """Il filtro di appartenenza: l'unico modo per interrogare la
    collezione (stessa regola e stessa guardia di sound_pro.py)."""
    return {"organization_id": current_user["organization_id"], **altro}


def _doc(share: dict) -> dict:
    share.pop("_id", None)
    return share


class ShareCreate(BaseModel):
    contact_id: str


# ── il lato dell'operatore ─────────────────────────────────────────────────

@router.post("/tracks/{track_id}/condivisioni", status_code=201)
async def crea_condivisione(track_id: str, payload: ShareCreate,
                            current_user: dict = Depends(require_sound_crea)):
    """Un link nuovo per UN contatto. La traccia deve essere
    pubblicata e RISERVATA: le pubbliche hanno gia' il loro slug, un
    token sopra sarebbe una seconda porta da sorvegliare."""
    from database import (
        customers_collection, frequency_tracks_collection,
        sound_shares_collection,
    )
    track = await frequency_tracks_collection.find_one(
        _mio(current_user, id=track_id),
        {"_id": 0, "id": 1, "status": 1, "visibility": 1})
    if not track:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="Traccia non trovata.")
    if track.get("status") != "published" \
            or track.get("visibility") != "private":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Si condividono le tracce pubblicate come riservate.")
    contatto = await customers_collection.find_one(
        _mio(current_user, id=payload.contact_id),
        {"_id": 0, "id": 1, "name": 1})
    if not contatto:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="Contatto non trovato.")
    quanti = await sound_shares_collection.count_documents(
        _mio(current_user, track_id=track_id))
    if quanti >= SHARES_MAX_PER_TRACK:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="Troppi link per questa traccia.")
    share = {
        "id": str(uuid.uuid4()),
        "organization_id": current_user["organization_id"],
        "track_id": track_id,
        "contact_id": contatto["id"],
        # lo snapshot del nome: la lista si legge senza join, come
        # fanno le sessioni del rito
        "contact_name": contatto.get("name") or "",
        "token": secrets.token_urlsafe(24),      # 192 bit
        "stato": "attivo",
        "creato_il": utc_now(),
        "revocato_il": None,
        "accessi": 0,
        "ultimo_accesso": None,
    }
    await sound_shares_collection.insert_one(dict(share))
    return _doc(share)


@router.get("/tracks/{track_id}/condivisioni")
async def lista_condivisioni(track_id: str,
                             current_user: dict = Depends(require_sound_crea)):
    from database import sound_shares_collection
    items = await sound_shares_collection.find(
        _mio(current_user, track_id=track_id), {"_id": 0},
    ).sort("creato_il", -1).to_list(SHARES_MAX_PER_TRACK)
    return {"items": items}


@router.post("/condivisioni/{share_id}/revoca")
async def revoca_condivisione(share_id: str,
                              current_user: dict = Depends(require_sound_crea)):
    """La revoca chirurgica: QUEL contatto smette subito, gli altri
    continuano. Niente cancellazioni: lo storico resta leggibile."""
    from database import sound_shares_collection
    esito = await sound_shares_collection.update_one(
        _mio(current_user, id=share_id, stato="attivo"),
        {"$set": {"stato": "revocato", "revocato_il": utc_now()}})
    if not esito.matched_count:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="Condivisione non trovata o già revocata.")
    return {"id": share_id, "stato": "revocato"}


# ── il lato del cliente (pubblico, senza account) ──────────────────────────

async def _share_vivo(token: str) -> tuple[dict, dict]:
    """Il controllo COMPLETO, ogni volta: share attivo → traccia
    riservata e pubblicata → Studio dell'org proprietaria attivo (il
    founder ha deciso: Pro decaduto = link spenti, subito). Ogni
    fallimento parla col messaggio neutro: al cliente non si
    raccontano ne' i token sbagliati ne' gli abbonamenti altrui."""
    from database import frequency_tracks_collection, sound_shares_collection
    from services.studio_access import org_per_studio, studio_attivo
    share = await sound_shares_collection.find_one(
        {"token": token, "stato": "attivo"}, {"_id": 0})
    if not share:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail=_SPENTO)
    track = await frequency_tracks_collection.find_one(
        {"id": share["track_id"], "status": "published",
         "visibility": "private"},
        {"_id": 0, "id": 1, "title": 1, "description": 1, "intent": 1,
         "score": 1, "organization_id": 1, "master_file": 1,
         "duration_sec": 1})
    if not track:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail=_SPENTO)
    org = await org_per_studio(track["organization_id"])
    if not studio_attivo(org):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail=_SPENTO)
    return share, track


@router.get("/condivise/{token}")
async def ascolta_condivisa(token: str):
    """Il payload del player per chi ha il link: come la pagina
    pubblica, ma la porta e' lo share. Segna l'accesso (i contatori
    sono il termometro dell'operatore: chi inoltra il link, inoltra
    il proprio nome)."""
    from database import organizations_collection, sound_shares_collection
    share, track = await _share_vivo(token)
    await sound_shares_collection.update_one(
        {"id": share["id"]},
        {"$inc": {"accessi": 1}, "$set": {"ultimo_accesso": utc_now()}})
    org = await organizations_collection.find_one(
        {"id": track["organization_id"]}, {"_id": 0, "name": 1})
    return {
        "title": track.get("title"),
        "description": track.get("description"),
        "intent": track.get("intent"),
        "score": track.get("score"),
        "duration_sec": track.get("duration_sec"),
        "operator": {"name": (org or {}).get("name")},
        "master_pronto": bool(track.get("master_file")),
    }


@router.get("/condivise/{token}/master")
async def master_condivisa(token: str, request: Request):
    """I byte del master, DOPO il controllo dello share: stessa
    consegna della via del cerchio (X-Accel in prod, 206 in dev)."""
    _, track = await _share_vivo(token)
    return _risposta_master(track.get("master_file"), request)
