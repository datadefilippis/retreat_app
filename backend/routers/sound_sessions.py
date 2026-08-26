"""Sound Professional — le sessioni (S2, 26/8/2026).

Il registro delle sessioni sonore: si apre su un protocollo, si
chiude con un esito, resta per sempre. Stessa ossessione del CRUD dei
protocolli (routers/sound_pro.py): IL SERVER E' L'AUTORITA'.

  - l'organizzazione viene dall'identita', da un punto solo (_mio);
  - lo SNAPSHOT lo decide il server: per un protocollo dell'operatore
    fotografa lo score dal database, per un protocollo core registra
    il riferimento {id, versione} verificato sullo specchio
    (models/sound_catalog.py) — il client manda solo tipo e id,
    MAI uno score;
  - il TEMPO lo decide il server: `ascolto_sec` dichiarato dal client
    viene cappato sull'orologio di muro e sulla durata prevista;
  - la sessione NON si cancella: e' un registro, non un appunto.

PRIVACY, deliberata: negli audit log vanno il tipo e l'id del
protocollo e l'esito — MAI il customer_id, MAI i feedback, MAI le
note. La sessione riguarda una persona: il log di sistema non deve
diventare una seconda copia del registro.
"""
import logging
from typing import Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict, Field

from models.audit import AuditLog
from models.common import generate_id, utc_now
from models.sound_catalog import protocollo_core
from models.sound_session import (
    FEEDBACK_MAX, FEEDBACK_MIN, NOTE_MAX, SoundSession,
)
from repositories import audit_repository
from routers.sound_pro import require_sound_professional

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/sound/pro/sessioni",
                   tags=["Sound Professional"])

# tetto anti-runaway di lettura, come per i protocolli
SESSIONI_LISTA_MAX = 500

# la lista e' il registro sfogliabile: leggera, senza snapshot e
# SENZA note (le note si aprono sulla singola sessione)
_LIST_PROJECTION = {
    "_id": 0, "id": 1, "protocollo": 1, "stato": 1, "customer_id": 1,
    "booking_id": 1, "durata_prevista_sec": 1, "ascolto_sec": 1,
    "feedback_pre": 1, "feedback_post": 1,
    "iniziata_il": 1, "terminata_il": 1,
}


def _mio(current_user: dict, **altro) -> dict:
    """Il filtro di appartenenza: l'unico modo per interrogare la
    collezione (stessa regola, stessa guardia di sound_pro.py)."""
    return {"organization_id": current_user["organization_id"], **altro}


def _doc(sessione: dict) -> dict:
    sessione.pop("_id", None)
    return sessione


# ── richieste: extra="forbid" — il client non decide niente ────────────────
class SessioneApri(BaseModel):
    """Si apre dichiarando COSA si sta per eseguire e con chi. Niente
    score, niente durate, niente appartenenza: quelli sono del server."""
    model_config = ConfigDict(extra="forbid")

    protocollo_tipo: Literal["core", "operatore"]
    protocollo_id: str
    customer_id: Optional[str] = None
    booking_id: Optional[str] = None
    feedback_pre: Optional[int] = Field(default=None, ge=FEEDBACK_MIN,
                                        le=FEEDBACK_MAX)
    note_operative: Optional[str] = None


class SessioneChiudi(BaseModel):
    model_config = ConfigDict(extra="forbid")

    esito: Literal["completata", "interrotta", "persa"]
    ascolto_sec: Optional[float] = Field(default=None, ge=0)
    feedback_post: Optional[int] = Field(default=None, ge=FEEDBACK_MIN,
                                         le=FEEDBACK_MAX)
    note_operative: Optional[str] = None


class SessioneAggiorna(BaseModel):
    """Dopo la chiusura si possono completare SOLO il vissuto e le
    note — il resto della sessione e' un fatto, e i fatti non si
    aggiornano."""
    model_config = ConfigDict(extra="forbid")

    feedback_pre: Optional[int] = Field(default=None, ge=FEEDBACK_MIN,
                                        le=FEEDBACK_MAX)
    feedback_post: Optional[int] = Field(default=None, ge=FEEDBACK_MIN,
                                         le=FEEDBACK_MAX)
    note_operative: Optional[str] = None


async def _audit(current_user: dict, azione: str, sessione_id: str,
                 dettagli: dict) -> None:
    """MAI customer_id, feedback o note nei dettagli: vedi testata."""
    try:
        await audit_repository.create(AuditLog(
            organization_id=current_user["organization_id"],
            user_id=current_user["user_id"],
            action=azione,
            resource_type="sound_session",
            resource_id=sessione_id,
            details=dettagli,
        ))
    except Exception:
        logger.warning("sound_sessions: audit %s fallito", azione,
                       exc_info=True)


async def _verifica_legami(current_user: dict, customer_id, booking_id):
    """Il cliente e l'appuntamento, se dichiarati, devono esistere
    NELLA STESSA org. Un id di un'altra org e' indistinguibile da un
    id inventato: 400, senza dire di piu'."""
    if customer_id:
        from database import customers_collection
        c = await customers_collection.find_one(
            _mio(current_user, id=customer_id), {"_id": 0, "id": 1})
        if not c:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                                detail="Cliente non trovato.")
    if booking_id:
        from database import issued_bookings_collection
        b = await issued_bookings_collection.find_one(
            _mio(current_user, id=booking_id), {"_id": 0, "id": 1})
        if not b:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                                detail="Appuntamento non trovato.")


async def _risolvi_protocollo(current_user: dict, tipo: str,
                              protocollo_id: str):
    """→ (riferimento, score_snapshot, durata_prevista).

    Qui vive la doppia natura del riferimento (vedi
    models/sound_session.py): core = riferimento immutabile senza
    snapshot; operatore = snapshot intero dal database.
    """
    if tipo == "core":
        voce = protocollo_core(protocollo_id)
        if not voce:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                                detail="Protocollo non in catalogo.")
        titolo, versione, durata = voce
        return ({"tipo": "core", "id": protocollo_id,
                 "versione": versione, "titolo": titolo}, None, durata)

    from database import sound_protocols_collection
    doc = await sound_protocols_collection.find_one(
        _mio(current_user, id=protocollo_id))
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="Protocollo non trovato.")
    if doc.get("stato") == "archiviato":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Il protocollo è archiviato: riattivalo per usarlo.")
    riferimento = {"tipo": "operatore", "id": doc["id"],
                   "versione": doc.get("versione", 1),
                   "titolo": doc.get("nome", "")}
    return riferimento, doc.get("score"), doc.get("durata_sec")


@router.post("", status_code=status.HTTP_201_CREATED)
async def apri_sessione(payload: SessioneApri,
                        current_user: dict = Depends(require_sound_professional)):
    from database import sound_sessions_collection
    await _verifica_legami(current_user, payload.customer_id,
                           payload.booking_id)
    riferimento, snapshot, durata = await _risolvi_protocollo(
        current_user, payload.protocollo_tipo, payload.protocollo_id)

    now = utc_now()
    sessione = {
        "id": generate_id(),
        "organization_id": current_user["organization_id"],
        "operator_user_id": current_user["user_id"],
        "customer_id": payload.customer_id,
        "booking_id": payload.booking_id,
        "protocollo": riferimento,
        "score_snapshot": snapshot,
        "durata_prevista_sec": durata,
        "stato": "in_corso",
        "ascolto_sec": None,
        "feedback_pre": payload.feedback_pre,
        "feedback_post": None,
        "note_operative": (payload.note_operative or "").strip()[:NOTE_MAX],
        "iniziata_il": now,
        "terminata_il": None,
        "created_at": now,
        "updated_at": now,
    }
    # il documento che salviamo e' valido secondo il modello — se non
    # lo fosse, meglio un errore qui che un registro corrotto
    SoundSession(**sessione)
    await sound_sessions_collection.insert_one(dict(sessione))
    await _audit(current_user, "sound_session_open", sessione["id"], {
        "protocollo_tipo": riferimento["tipo"],
        "protocollo_id": riferimento["id"],
        "protocollo_versione": riferimento["versione"],
    })
    return _doc(sessione)


@router.post("/{sessione_id}/chiusura")
async def chiudi_sessione(sessione_id: str, payload: SessioneChiudi,
                          current_user: dict = Depends(require_sound_professional)):
    from database import sound_sessions_collection
    aperta = await sound_sessions_collection.find_one(
        _mio(current_user, id=sessione_id, stato="in_corso"))
    if not aperta:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="Nessuna sessione in corso con questo id.")

    now = utc_now()
    # il client Mongo non e' tz_aware: le date tornano naive-UTC, e
    # aware − naive e' un TypeError. Si normalizza qui, una volta.
    inizio = aperta["iniziata_il"]
    if inizio.tzinfo is None:
        from datetime import timezone
        inizio = inizio.replace(tzinfo=timezone.utc)
    muro = max(0.0, (now - inizio).total_seconds())
    # il tempo dichiarato, reso onesto: mai piu' del muro, mai piu'
    # della durata prevista (+ un respiro per gli arrotondamenti)
    dichiarato = payload.ascolto_sec if payload.ascolto_sec is not None else muro
    ascolto = round(min(dichiarato, muro,
                        (aperta.get("durata_prevista_sec") or muro) + 2), 1)

    updates = {
        "stato": payload.esito,
        "ascolto_sec": ascolto,
        "terminata_il": now,
        "updated_at": now,
    }
    if payload.feedback_post is not None:
        updates["feedback_post"] = payload.feedback_post
    if payload.note_operative is not None:
        updates["note_operative"] = payload.note_operative.strip()[:NOTE_MAX]

    dopo = await sound_sessions_collection.find_one_and_update(
        _mio(current_user, id=sessione_id, stato="in_corso"),
        {"$set": updates}, return_document=True)
    if not dopo:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="Nessuna sessione in corso con questo id.")
    await _audit(current_user, "sound_session_close", sessione_id, {
        "esito": payload.esito,
        "protocollo_tipo": dopo["protocollo"]["tipo"],
        "protocollo_id": dopo["protocollo"]["id"],
    })
    return _doc(dopo)


@router.patch("/{sessione_id}")
async def aggiorna_sessione(sessione_id: str, payload: SessioneAggiorna,
                            current_user: dict = Depends(require_sound_professional)):
    from database import sound_sessions_collection
    updates = {}
    if payload.feedback_pre is not None:
        updates["feedback_pre"] = payload.feedback_pre
    if payload.feedback_post is not None:
        updates["feedback_post"] = payload.feedback_post
    if payload.note_operative is not None:
        updates["note_operative"] = payload.note_operative.strip()[:NOTE_MAX]
    if not updates:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="Nessuna modifica.")
    updates["updated_at"] = utc_now()
    dopo = await sound_sessions_collection.find_one_and_update(
        _mio(current_user, id=sessione_id),
        {"$set": updates}, return_document=True)
    if not dopo:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="Sessione non trovata.")
    await _audit(current_user, "sound_session_update", sessione_id,
                 {"campi": sorted(k for k in updates if k != "updated_at")})
    return _doc(dopo)


@router.get("")
async def lista_sessioni(
        stato: Optional[Literal["in_corso", "completata",
                                "interrotta", "persa"]] = Query(None),
        customer_id: Optional[str] = Query(None),
        current_user: dict = Depends(require_sound_professional)):
    from database import sound_sessions_collection
    # i filtri entrano DENTRO _mio: la query si legge intera, e la
    # guardia strutturale puo' vedere l'org a colpo d'occhio
    extra = {}
    if stato:
        extra["stato"] = stato
    if customer_id:
        extra["customer_id"] = customer_id
    items = await sound_sessions_collection.find(
        _mio(current_user, **extra), _LIST_PROJECTION,
    ).sort("iniziata_il", -1).to_list(SESSIONI_LISTA_MAX)
    return {"items": items}


@router.get("/{sessione_id}")
async def leggi_sessione(sessione_id: str,
                         current_user: dict = Depends(require_sound_professional)):
    from database import sound_sessions_collection
    sessione = await sound_sessions_collection.find_one(
        _mio(current_user, id=sessione_id))
    if not sessione:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="Sessione non trovata.")
    return _doc(sessione)
