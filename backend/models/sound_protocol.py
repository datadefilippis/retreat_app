"""SoundProtocol — il protocollo professionale (P1, 26/8/2026).

Un protocollo e' DUE verita' affiancate:
  - gli `steps`: la verita' EDITORIALE, cio' che l'operatore ha scritto
    (il DSL del sequencer: metodo, frequenza, durata, pausa, volume);
  - lo `score`: la verita' ESECUTIVA, compilata dal compilatore
    (frontend/src/features/frequenze/pro/compilatore.js) e valida
    secondo il contratto v1 — il motore suona QUELLA, e non sa nulla
    del professionista.

DOVE VIVE IL COMPILATORE (corretto in P2, 26/8). P1 aveva scritto
«vive in JavaScript, e in un posto solo». Sbagliato: il server deve
essere l'autorita' — lo score non puo' arrivare dal client — e il
container backend e' python:3.12-slim, senza Node. L'autorita' e'
quindi `services/sound_compiler.py`; `pro/compilatore.js` resta lo
SPECCHIO per l'anteprima del Builder. Una guardia esegue entrambi
sulle stesse fixture e pretende lo stesso risultato (test P2).
Gli step si validano QUI, strutturalmente, con le STESSE costanti del
contratto — importate, mai ricopiate.

VERSIONI: `versione` avanza a ogni salvataggio che CAMBIA GLI STEP
(rinominare non e' una versione nuova); lo score di una versione
salvata e' immutabile, e quello sostituito finisce in
`versioni_precedenti` — il minimo perche' «la versione precedente
resti recuperabile». Non e' la storia completa e non vuole esserlo:
le sessioni (P5) porteranno comunque il proprio snapshot dello score
eseguito, cosi' «ho eseguito il protocollo X versione 3» riproduce
quel suono anche se il protocollo poi cambia.

NIENTE in questo file tocca la salute: e' un partito preso, non una
dimenticanza (vedi discovery, sez. I). `note_operative` e' testo
libero DELL'OPERATORE, attribuito a lui.
"""
from datetime import datetime
from typing import List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

from .common import generate_id, utc_now
from .frequency_track import (
    BEAT_MAX, BEAT_MIN, CARRIER_MAX, CARRIER_MIN,
    DURATION_MAX, DURATION_MIN, LAYERS_MAX,
)

# ── il DSL del sequencer: limiti derivati dal contratto ─────────────────────
STEP_METHODS = ("tone", "drone", "bin", "iso")   # il sottoinsieme del sequencer
_CON_BATTITO = ("bin", "iso")
PASSI_MAX = LAYERS_MAX                            # un passo = un layer
PASSO_DURATA_MIN = 1.0                            # il contratto vuole >= 0.5
GAIN_MIN, GAIN_MAX = 0.05, 1.0                    # lo zero e' muto: fuori
NOME_MAX = 120
DESCRIZIONE_MAX = 2000
NOTE_MAX = 4000

STATI = ("bozza", "attivo", "archiviato")
VISIBILITA = ("org",)                             # V1: solo privati per-org
# quante versioni sostituite si tengono a bordo del documento (le piu'
# recenti). Uno score da 24 passi pesa ~4 KB: dieci stanno larghi nei
# 16 MB di Mongo, e oltre la decima all'indietro nessuno guarda.
VERSIONI_TENUTE = 10


def clean_steps(raw):
    """Gli step validati strutturalmente, o None se non sono step.

    Filosofia DIVERSA da clean_layer: qui NON si riporta nel range —
    si rifiuta. Un protocollo professionale con un valore fuori
    contratto e' un errore da mostrare all'operatore, non da correggere
    in silenzio (correggere cambierebbe cio' che ha progettato).
    La verita' sonora resta clean_score sul compilato: questo filtro
    protegge solo la struttura del documento.
    """
    if not isinstance(raw, list) or not raw or len(raw) > PASSI_MAX:
        return None
    puliti = []
    totale = 0.0
    for i, p in enumerate(raw):
        if not isinstance(p, dict):
            return None
        metodo = p.get("metodo")
        if metodo not in STEP_METHODS:
            return None
        try:
            hz = float(p.get("hz"))
            durata = float(p.get("durata_sec"))
            pausa = float(p.get("pausa_dopo_sec", 0))
            gain = float(p.get("gain"))
        except (TypeError, ValueError):
            return None
        if not (CARRIER_MIN <= hz <= CARRIER_MAX):
            return None
        if durata < PASSO_DURATA_MIN or pausa < 0:
            return None
        if not (GAIN_MIN <= gain <= GAIN_MAX):
            return None
        pulito = {"metodo": metodo, "hz": hz, "durata_sec": durata,
                  "pausa_dopo_sec": pausa, "gain": gain}
        if metodo in _CON_BATTITO:
            try:
                battito = float(p.get("battito_hz"))
            except (TypeError, ValueError):
                return None
            if not (BEAT_MIN <= battito <= BEAT_MAX):
                return None
            pulito["battito_hz"] = battito
            fine = p.get("battito_fine_hz")
            if fine is not None:
                try:
                    fine = float(fine)
                except (TypeError, ValueError):
                    return None
                if not (BEAT_MIN <= fine <= BEAT_MAX):
                    return None
                pulito["battito_fine_hz"] = fine
        elif p.get("battito_hz") is not None or p.get("battito_fine_hz") is not None:
            return None                       # campo che il motore ignorerebbe
        totale += durata + (0 if i == len(raw) - 1 else pausa)
        puliti.append(pulito)
    if not (DURATION_MIN <= round(totale, 1) <= DURATION_MAX):
        return None
    return puliti


class PassoProtocollo(BaseModel):
    metodo: Literal["tone", "drone", "bin", "iso"]
    hz: float = Field(ge=CARRIER_MIN, le=CARRIER_MAX)
    battito_hz: Optional[float] = Field(default=None, ge=BEAT_MIN, le=BEAT_MAX)
    battito_fine_hz: Optional[float] = Field(default=None, ge=BEAT_MIN, le=BEAT_MAX)
    durata_sec: float = Field(ge=PASSO_DURATA_MIN)
    pausa_dopo_sec: float = Field(default=0, ge=0)
    gain: float = Field(ge=GAIN_MIN, le=GAIN_MAX)


class SoundProtocol(BaseModel):
    """Il documento in `sound_protocols` (collezione SEPARATA da
    frequency_tracks per decisione D1: i protocolli sono strumenti
    privati adiacenti ai clienti, le tracce sono contenuto pubblico)."""
    model_config = ConfigDict(extra="ignore")

    id: str = Field(default_factory=generate_id)
    organization_id: str
    created_by: str
    nome: str = Field(min_length=1, max_length=NOME_MAX)
    descrizione: str = Field(default="", max_length=DESCRIZIONE_MAX)
    steps: List[PassoProtocollo]
    score: dict                                # il compilato (clean_score al CRUD)
    durata_sec: float                          # derivata: score.duration_sec
    note_operative: str = Field(default="", max_length=NOTE_MAX)
    stato: Literal["bozza", "attivo", "archiviato"] = "bozza"
    visibilita: Literal["org"] = "org"
    versione: int = 1
    # gli score sostituiti, dal piu' recente: {versione, score,
    # durata_sec, sostituita_il}. Vedi VERSIONI_TENUTE.
    versioni_precedenti: List[dict] = Field(default_factory=list)
    origine: dict = Field(default_factory=lambda: {"tipo": "proprio"})
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)
