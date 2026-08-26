"""Sound Professional — CRUD dei protocolli (P2, 26/8/2026).

Il professionista progetta protocolli, il compilatore li traduce, il
motore li suona — e il motore non sa nulla del professionista. Questo
router e' l'unico posto dove i protocolli entrano ed escono, e ha una
sola ossessione: IL SERVER E' L'AUTORITA'.

Cosa vuol dire, in concreto:
  - l'ORGANIZZAZIONE viene dall'identita' autenticata, mai dal corpo
    della richiesta. Ogni query — lista, lettura, modifica, archivio,
    e persino il conteggio del tetto — porta l'org nel filtro: non
    esiste un lookup per solo `id` da cui possa uscire il documento di
    un'altra organizzazione;
  - lo SCORE lo produce il server (services/sound_compiler.py). Se il
    client ne manda uno, la richiesta viene RIFIUTATA, non ripulita:
    i modelli di richiesta hanno extra="forbid", cosi' `score`,
    `organization_id`, `created_by`, `versione`, `durata_sec` fanno
    422 invece di essere ignorati in silenzio;
  - la VERSIONE la decide il server: cambiano gli step → versione
    nuova, e quella vecchia resta recuperabile.

LA CATENA DI VALIDAZIONE, che non ammette scorciatoie:
    steps → clean_steps → compila → clean_score → identico?
Se clean_score CORREGGE anche un solo valore, la risposta e' 500 e non
400: l'operatore ha mandato passi validi, e' il compilatore ad aver
mentito. Salvare uno score «poi ripulito dal validatore» e' esattamente
cio' che P1 ha costruito per rendere impossibile.

FUORI DA P2 di proposito: nessun `customer_id` (il legame protocollo →
sessione → cliente arriva in P5/P6), nessun billing, nessuna libreria
pubblica, nessuna condivisione, nessuna anteprima.
"""
import logging
import uuid
from typing import List, Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict

from auth import get_current_user
from models.audit import AuditLog
from models.common import utc_now
from models.frequency_track import clean_score
from models.sound_protocol import (
    DESCRIZIONE_MAX, NOME_MAX, NOTE_MAX, VERSIONI_TENUTE, clean_steps,
)
from repositories import audit_repository
from services.sound_compiler import ErrorePasso, compila

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/sound/pro", tags=["Sound Professional"])

# tetto anti-runaway, come TRACKS_MAX_PER_ORG: sono documenti da pochi
# KB. Conta i NON archiviati — l'archivio non deve consumare il tetto,
# altrimenti archiviare diventa un modo per restare bloccati.
PROTOCOLLI_MAX_PER_ORG = 200

# la lista non porta lo score (24 layer per riga): porta la durata e
# quanti passi sono, che e' cio' che si legge in un elenco.
_LIST_PROJECTION = {
    "_id": 0, "id": 1, "nome": 1, "descrizione": 1, "stato": 1,
    "versione": 1, "durata_sec": 1, "steps": 1,
    "created_at": 1, "updated_at": 1,
}


async def require_sound_professional(
        current_user: dict = Depends(get_current_user)) -> dict:
    """Il portiere del Professional, ricalcato su require_sound_composer
    (routers/frequencies.py): il privilegio e' un flag per-org concesso
    a mano (`organizations.sound_professional`), non un abbonamento —
    il billing vero verra' dopo, e quando verra' bastera' cambiare
    QUESTA funzione."""
    from database import organizations_collection
    org = await organizations_collection.find_one(
        {"id": current_user["organization_id"]},
        {"_id": 0, "sound_professional": 1})
    if not (org or {}).get("sound_professional"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Aurya Sound Professional è su invito: "
                   "scrivici e ne parliamo.")
    return current_user


# ── richieste: extra="forbid", cosi' il client non prova nemmeno ────────────
class ProtocolloCreate(BaseModel):
    """Il client manda SOLO cio' che gli appartiene: il progetto.
    Appartenenza, score, versione e durata sono del server, e
    `extra="forbid"` li rifiuta esplicitamente invece di ignorarli."""
    model_config = ConfigDict(extra="forbid")

    nome: str
    steps: List[dict]
    descrizione: Optional[str] = None
    note_operative: Optional[str] = None
    stato: Optional[Literal["bozza", "attivo"]] = None


class ProtocolloUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    nome: Optional[str] = None
    steps: Optional[List[dict]] = None
    descrizione: Optional[str] = None
    note_operative: Optional[str] = None
    stato: Optional[Literal["bozza", "attivo"]] = None


def _mio(current_user: dict, **altro) -> dict:
    """Il filtro di appartenenza, e l'unico modo per interrogare la
    collezione. L'organizzazione entra da qui e da nessun'altra parte:
    scordarsela smette di essere una svista possibile, e diventa una
    query che non esiste nel file."""
    return {"organization_id": current_user["organization_id"], **altro}


def _doc(protocollo: dict) -> dict:
    protocollo.pop("_id", None)
    return protocollo


def _riga(item: dict) -> dict:
    """La riga di lista: gli step diventano un numero."""
    item["passi"] = len(item.pop("steps", None) or [])
    return item


def _nome(raw: Optional[str]) -> str:
    nome = (raw or "").strip()[:NOME_MAX]
    if not nome:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="Serve un nome.")
    return nome


def _progetta(raw_steps) -> tuple:
    """La catena intera: steps → (steps puliti, score, durata).

    Ogni uscita da qui e' o un errore parlante o uno score che il
    contratto accetta SENZA CORREZIONI. Non esiste una terza via.
    """
    puliti = clean_steps(raw_steps)
    try:
        # il compilatore da' il messaggio parlante («passo 3: ...»);
        # se clean_steps ha gia' rifiutato, gli si passa comunque il
        # grezzo per ottenere QUELLA frase invece di un muto «non valido»
        score = compila(puliti if puliti is not None else raw_steps)
    except ErrorePasso as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail=str(e))
    if puliti is None:
        # i due validatori non concordano: nel dubbio si RIFIUTA
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="Passi non validi.")

    pulito = clean_score(score)
    if pulito is None or pulito != score:
        # non e' colpa di chi ha scritto i passi: e' il compilatore che
        # produce uno score che il contratto deve correggere. Va visto.
        logger.error("sound_pro: lo score compilato non e' stabile "
                     "sotto clean_score (passi: %d)", len(puliti))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Errore interno di compilazione del protocollo.")
    return puliti, score, score["duration_sec"]


async def _audit(current_user: dict, azione: str, protocollo_id: str,
                 dettagli: dict) -> None:
    """Traccia l'azione. NIENTE step e NIENTE note operative nei
    dettagli: sono il lavoro dell'operatore, non materiale da log."""
    try:
        await audit_repository.create(AuditLog(
            organization_id=current_user["organization_id"],
            user_id=current_user["user_id"],
            action=azione,
            resource_type="sound_protocol",
            resource_id=protocollo_id,
            details=dettagli,
        ))
    except Exception:                       # l'audit non rompe l'azione
        logger.warning("sound_pro: audit %s fallito", azione, exc_info=True)


@router.get("/protocolli")
async def list_protocolli(
        stato: Optional[Literal["bozza", "attivo", "archiviato"]] = Query(None),
        current_user: dict = Depends(require_sound_professional)):
    """I protocolli dell'organizzazione corrente. E basta.

    Senza filtro, gli archiviati NON compaiono: la lista e' il tavolo
    di lavoro, l'archivio si chiede."""
    from database import sound_protocols_collection
    items = await sound_protocols_collection.find(
        _mio(current_user, stato=stato if stato else {"$ne": "archiviato"}),
        _LIST_PROJECTION,
    ).sort("updated_at", -1).to_list(PROTOCOLLI_MAX_PER_ORG)
    return {"items": [_riga(it) for it in items]}


@router.post("/protocolli", status_code=status.HTTP_201_CREATED)
async def create_protocollo(
        payload: ProtocolloCreate,
        current_user: dict = Depends(require_sound_professional)):
    from database import sound_protocols_collection
    org_id = current_user["organization_id"]
    quanti = await sound_protocols_collection.count_documents(
        _mio(current_user, stato={"$ne": "archiviato"}))
    if quanti >= PROTOCOLLI_MAX_PER_ORG:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Limite di {PROTOCOLLI_MAX_PER_ORG} protocolli raggiunto.")

    nome = _nome(payload.nome)
    steps, score, durata = _progetta(payload.steps)
    now = utc_now()
    protocollo = {
        "id": str(uuid.uuid4()),
        "organization_id": org_id,                  # dall'identita', mai dal client
        "created_by": current_user["user_id"],      # idem
        "nome": nome,
        "descrizione": (payload.descrizione or "").strip()[:DESCRIZIONE_MAX],
        "steps": steps,
        "score": score,
        "durata_sec": durata,
        "note_operative": (payload.note_operative or "").strip()[:NOTE_MAX],
        "stato": payload.stato or "bozza",
        "visibilita": "org",
        "versione": 1,
        "versioni_precedenti": [],
        "origine": {"tipo": "proprio"},
        "created_at": now,
        "updated_at": now,
    }
    await sound_protocols_collection.insert_one(dict(protocollo))
    await _audit(current_user, "sound_pro_create", protocollo["id"],
                 {"nome": nome, "passi": len(steps), "durata_sec": durata})
    return _doc(protocollo)


@router.get("/protocolli/{protocollo_id}")
async def get_protocollo(
        protocollo_id: str,
        current_user: dict = Depends(require_sound_professional)):
    from database import sound_protocols_collection
    protocollo = await sound_protocols_collection.find_one(
        _mio(current_user, id=protocollo_id))
    if not protocollo:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="Protocollo non trovato.")
    return _doc(protocollo)


@router.patch("/protocolli/{protocollo_id}")
async def update_protocollo(
        protocollo_id: str, payload: ProtocolloUpdate,
        current_user: dict = Depends(require_sound_professional)):
    """Cambiare i passi e' una VERSIONE NUOVA; rinominare non lo e'.

    Lo score precedente non viene sovrascritto in silenzio: scende in
    `versioni_precedenti`, e chi domani vorra' sapere cosa suonava la
    versione 1 potra' leggerlo."""
    from database import sound_protocols_collection
    prima = await sound_protocols_collection.find_one(
        _mio(current_user, id=protocollo_id))
    if not prima:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="Protocollo non trovato.")

    # «non hai mandato niente» e «cio' che hai mandato non cambia
    # niente» sono due cose diverse: la prima e' un errore, la seconda
    # e' un salvataggio senza modifiche — il Builder rimanda tutto il
    # modulo a ogni salva, e non deve prendersi un 400 per questo.
    if not payload.model_dump(exclude_unset=True):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="Nessuna modifica.")

    updates = {}
    if payload.nome is not None:
        updates["nome"] = _nome(payload.nome)
    if payload.descrizione is not None:
        updates["descrizione"] = payload.descrizione.strip()[:DESCRIZIONE_MAX]
    if payload.note_operative is not None:
        updates["note_operative"] = payload.note_operative.strip()[:NOTE_MAX]
    if payload.stato is not None:
        updates["stato"] = payload.stato

    nuova_versione = False
    if payload.steps is not None:
        steps, score, durata = _progetta(payload.steps)
        if steps != prima.get("steps"):
            nuova_versione = True
            snapshot = {
                "versione": prima.get("versione", 1),
                "score": prima.get("score"),
                "durata_sec": prima.get("durata_sec"),
                "sostituita_il": utc_now(),
            }
            storia = [snapshot] + list(prima.get("versioni_precedenti") or [])
            updates["versioni_precedenti"] = storia[:VERSIONI_TENUTE]
            updates["versione"] = prima.get("versione", 1) + 1
            updates["steps"] = steps
            updates["score"] = score
            updates["durata_sec"] = durata

    updates["updated_at"] = utc_now()
    dopo = await sound_protocols_collection.find_one_and_update(
        _mio(current_user, id=protocollo_id),
        {"$set": updates}, return_document=True)
    if not dopo:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="Protocollo non trovato.")
    await _audit(current_user, "sound_pro_update", protocollo_id, {
        "campi": sorted(k for k in updates if k != "updated_at"),
        "versione_prima": prima.get("versione", 1),
        "versione_dopo": dopo.get("versione", 1),
        "nuova_versione": nuova_versione,
    })
    return _doc(dopo)


@router.delete("/protocolli/{protocollo_id}",
               status_code=status.HTTP_204_NO_CONTENT)
async def archive_protocollo(
        protocollo_id: str,
        current_user: dict = Depends(require_sound_professional)):
    """ARCHIVIA, non cancella. Il modello prevede gia' lo stato, e un
    protocollo che domani potrebbe risultare eseguito in una sessione
    (P5) non deve poter sparire dal database sotto quel riferimento."""
    from database import sound_protocols_collection
    dopo = await sound_protocols_collection.find_one_and_update(
        _mio(current_user, id=protocollo_id, stato={"$ne": "archiviato"}),
        {"$set": {"stato": "archiviato", "updated_at": utc_now()}},
        return_document=True)
    if not dopo:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="Protocollo non trovato.")
    await _audit(current_user, "sound_pro_archive", protocollo_id,
                 {"nome": dopo.get("nome"),
                  "versione": dopo.get("versione", 1)})
