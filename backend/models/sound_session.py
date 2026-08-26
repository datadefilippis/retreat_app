"""SoundSession — la sessione professionale (S2, 26/8/2026).

Il prodotto e' il REGISTRO: l'operatore sceglie un protocollo, lo
esegue con una persona, e Aurya ricorda cosa, con chi, e com'e'
andata (docs/SOUND_PROFESSIONAL_PIANO_2026-08.md). La sessione e' la
riga di quel registro.

COSA RICORDA, e perche':
  - IL PROTOCOLLO, in modo che non possa mentire mai:
      * `operatore` → snapshot INTERO dello score eseguito
        (il documento in sound_protocols puo' cambiare domani);
      * `core` → riferimento {id, versione} senza snapshot: il
        catalogo e' versionato in git, il riferimento E' immutabile
        (vedi models/sound_catalog.py).
  - IL VISSUTO: feedback pre/post su scala 1-10. E' un vissuto
    SOGGETTIVO dichiarato dalla persona, non una misura — e resta
    tale anche quando (S7+) accanto ci saranno misure vere, che
    vivranno in una collezione SEPARATA, mai qui dentro.
  - LE NOTE dell'operatore: private, sue, mai negli audit log.

COSA NON RICORDA, di proposito: diagnosi, condizioni, dati sanitari.
Non e' una cartella clinica e non deve poterlo diventare per deriva:
i campi non esistono, non sono «vuoti per ora».

STATI: in_corso → completata | interrotta (scelta dell'operatore) |
persa (il contesto audio e' morto: schermo bloccato, onPerso del
player). La distinzione fra «abbiamo interrotto noi» e «si e'
interrotto da solo» e' informazione professionale, non rumore.

La sessione NON si cancella: e' un registro. Chi sbaglia ad aprirla
la chiude come interrotta.
"""
from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

from .common import generate_id, utc_now

STATI_SESSIONE = ("in_corso", "completata", "interrotta", "persa")
ESITI = ("completata", "interrotta", "persa")
TIPI_PROTOCOLLO = ("core", "operatore")
FEEDBACK_MIN, FEEDBACK_MAX = 1, 10
NOTE_MAX = 4000


class RiferimentoProtocollo(BaseModel):
    model_config = ConfigDict(extra="ignore")

    tipo: Literal["core", "operatore"]
    id: str
    versione: int
    titolo: str


class SoundSession(BaseModel):
    """Il documento in `sound_sessions`."""
    model_config = ConfigDict(extra="ignore")

    id: str = Field(default_factory=generate_id)
    organization_id: str
    operator_user_id: str
    # il legame col gestionale: opzionale (la sessione anonima e'
    # legittima), e sempre della STESSA org — lo verifica il router
    customer_id: Optional[str] = None
    booking_id: Optional[str] = None

    protocollo: RiferimentoProtocollo
    score_snapshot: Optional[dict] = None      # solo tipo=operatore
    durata_prevista_sec: float

    stato: Literal["in_corso", "completata", "interrotta", "persa"] = "in_corso"
    # quanto si e' ascoltato DAVVERO: dichiarato dal client alla
    # chiusura, ma cappato dal server (orologio di muro e durata
    # prevista) — un numero riferito, reso onesto
    ascolto_sec: Optional[float] = None

    feedback_pre: Optional[int] = Field(default=None, ge=FEEDBACK_MIN,
                                        le=FEEDBACK_MAX)
    feedback_post: Optional[int] = Field(default=None, ge=FEEDBACK_MIN,
                                         le=FEEDBACK_MAX)
    note_operative: str = Field(default="", max_length=NOTE_MAX)

    iniziata_il: datetime = Field(default_factory=utc_now)
    terminata_il: Optional[datetime] = None
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)
