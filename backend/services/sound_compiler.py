"""IL COMPILATORE, lato server — steps → score (Sound Professional P2).

P1 aveva scritto che il compilatore vive in JavaScript «e in un posto
solo». QUELLA FRASE ERA SBAGLIATA, e P2 la corregge per una ragione
che non si aggira: il server deve essere l'autorita' — lo score non
puo' arrivare dal client — e il container backend e' python:3.12-slim,
senza Node. Un compilatore che vive solo nel browser non puo' essere
l'autorita' di niente.

Quindi i compilatori sono DUE, con ruoli diversi e nome diverso:
  - QUESTO e' l'AUTORITA': gira nel CRUD, produce lo score che viene
    salvato ed eseguito;
  - `frontend/src/features/frequenze/pro/compilatore.js` e' lo
    SPECCHIO: serve all'anteprima del Builder (P3), che deve sentire
    il protocollo mentre lo si scrive, senza un giro di rete.

E' il pattern di casa (models/disciplines.py ↔ lib/disciplines.js),
ma la guardia qui e' piu' severa: non confronta costanti, ESEGUE
entrambi i compilatori sulle stesse fixture e pretende lo stesso
output valore per valore, chiave per chiave — inclusi i messaggi
d'errore (test_sound_pro_p2.py). Se divergono, il test
rompe prima che un operatore salvi un protocollo che suona diverso da
come l'ha sentito nell'anteprima.

LA PORTA STRETTA DELL'ARITMETICA: JS arrotonda con Math.round (meta'
verso l'alto), Python con round() (meta' al pari — round(2.5) == 2).
Sono davvero diversi, e su un `start` a 3 decimali basterebbe a far
divergere i gemelli. Qui si arrotonda ALLA MANIERA DI JS, a mano.
"""
import math

# ── i gemelli di pro/compilatore.js (che a sua volta specchia il contratto) ──
from models.frequency_track import (
    BEAT_MAX, BEAT_MIN, CARRIER_MAX, CARRIER_MIN,
    DURATION_MAX, DURATION_MIN, LAYERS_MAX,
)
from models.sound_protocol import (
    GAIN_MAX, GAIN_MIN, PASSO_DURATA_MIN, STEP_METHODS,
)

PASSI_MAX = LAYERS_MAX
BATTITO_NEUTRO = 10.0            # il default che clean_layer scrive
_CON_BATTITO = ("bin", "iso")
_ETICHETTE = {"tone": "tono", "drone": "accordo",
              "bin": "battito", "iso": "ritmo"}


class ErrorePasso(ValueError):
    """Errore di compilazione: porta l'indice del passo colpevole
    (gemello di ErrorePasso in pro/compilatore.js, stesso testo)."""

    def __init__(self, indice, messaggio):
        super().__init__(messaggio if indice is None
                         else f"passo {indice + 1}: {messaggio}")
        self.indice = indice


def _round_js(x: float, decimali: int) -> float:
    """Math.round di JavaScript: la meta' va SEMPRE verso l'alto."""
    m = 10 ** decimali
    return math.floor(x * m + 0.5) / m


def _numero(v) -> bool:
    """Il `typeof v === 'number' && isFinite(v)` di JS.

    I bool in Python sono int: senza l'esclusione, `True` passerebbe
    per una frequenza da 1 Hz."""
    return (isinstance(v, (int, float)) and not isinstance(v, bool)
            and math.isfinite(v))


def _num_fmt(v) -> str:
    """Il valore come lo scriverebbe JS nel messaggio d'errore.

    I gemelli devono dire la STESSA frase, e JS scrive `220` dove
    Python scriverebbe `220.0`, `undefined` dove Python scriverebbe
    `None`. Vince la lingua dello specchio: e' quella che l'operatore
    vede nell'anteprima del Builder.
    (Il messaggio «battito undefined» e' un fondo di sicurezza: dal
     Builder il campo e' obbligatorio. P3 gli dara' una frase italiana
     — in tutti e due i gemelli insieme.)"""
    if v is None:
        return "undefined"
    if isinstance(v, float) and v.is_integer():
        return str(int(v))
    return str(v)


def _valida_passo(p, i):
    if not isinstance(p, dict):
        raise ErrorePasso(i, "non è un passo")
    metodo = p.get("metodo")
    if metodo not in STEP_METHODS:
        raise ErrorePasso(i, f"metodo «{metodo}» non previsto dal sequencer")
    hz = p.get("hz")
    if not _numero(hz) or hz < CARRIER_MIN or hz > CARRIER_MAX:
        raise ErrorePasso(i, f"frequenza {_num_fmt(hz)} fuori da "
                             f"{_num_fmt(CARRIER_MIN)}–{_num_fmt(CARRIER_MAX)} Hz")
    durata = p.get("durata_sec")
    if not _numero(durata) or durata < PASSO_DURATA_MIN:
        raise ErrorePasso(i, f"durata {_num_fmt(durata)}s: il minimo è "
                             f"{_num_fmt(PASSO_DURATA_MIN)}s")
    pausa = p.get("pausa_dopo_sec")
    pausa = 0 if pausa is None else pausa
    if not _numero(pausa) or pausa < 0:
        raise ErrorePasso(i, "pausa negativa")
    gain = p.get("gain")
    if not _numero(gain) or gain < GAIN_MIN or gain > GAIN_MAX:
        raise ErrorePasso(i, f"volume {_num_fmt(gain)} fuori da "
                             f"{_num_fmt(GAIN_MIN)}–{_num_fmt(GAIN_MAX)}")
    con_battito = metodo in _CON_BATTITO
    if con_battito:
        battito = p.get("battito_hz")
        if not _numero(battito) or battito < BEAT_MIN or battito > BEAT_MAX:
            raise ErrorePasso(i, f"battito {_num_fmt(battito)} fuori da "
                                 f"{_num_fmt(BEAT_MIN)}–{_num_fmt(BEAT_MAX)} Hz")
        fine = p.get("battito_fine_hz")
        if fine is not None and (not _numero(fine)
                                 or fine < BEAT_MIN or fine > BEAT_MAX):
            raise ErrorePasso(i, f"battito finale {_num_fmt(fine)} fuori range")
    elif p.get("battito_hz") is not None or p.get("battito_fine_hz") is not None:
        # un campo che il motore ignorerebbe e' una promessa falsa
        raise ErrorePasso(i, f"il metodo «{metodo}» non ha un battito")


def _nome_passo(p, i) -> str:
    base = (f"Passo {i + 1} · {_ETICHETTE[p['metodo']]} "
            f"{_num_fmt(p['hz'])} Hz")
    return base[:60]


def compila(steps) -> dict:
    """steps → score v1. Puro e deterministico.

    Lancia ErrorePasso su input invalido: MAI uno score «quasi
    giusto». Il tempo e' un cursore, le pause sono BUCHI fra le
    finestre — le sovrapposizioni sono impossibili per costruzione.
    """
    if not isinstance(steps, list) or len(steps) == 0:
        raise ErrorePasso(None, "serve almeno un passo")
    if len(steps) > PASSI_MAX:
        raise ErrorePasso(None, f"{len(steps)} passi: il massimo è {PASSI_MAX}")
    for i, p in enumerate(steps):
        _valida_passo(p, i)

    t = 0.0
    layers = []
    for i, p in enumerate(steps):
        inizio = _round_js(t, 3)
        fine = _round_js(t + p["durata_sec"], 3)
        ultimo = i == len(steps) - 1
        pausa = p.get("pausa_dopo_sec")
        t = fine + (0 if ultimo else (0 if pausa is None else pausa))
        con_battito = p["metodo"] in _CON_BATTITO
        f0 = float(p["battito_hz"]) if con_battito else BATTITO_NEUTRO
        if con_battito:
            fine_hz = p.get("battito_fine_hz")
            f1 = float(p["battito_hz"] if fine_hz is None else fine_hz)
        else:
            f1 = BATTITO_NEUTRO
        layers.append({
            # ESATTAMENTE le 13 chiavi di clean_layer, stessi default
            "kind": "neuro",
            "name": _nome_passo(p, i),
            "method": p["metodo"],
            "timbre": "warm",
            "carrier": float(p["hz"]),
            "f0": f0,
            "f1": f1,
            # la transizione e' sempre esponenziale: vedi pro/compilatore.js
            "curve": "exp" if (con_battito and f0 != f1) else "lin",
            "start": float(inizio),
            "end": float(fine),
            "gain": float(p["gain"]),
            "breath": True,
            "mute": False,
        })

    durata = _round_js(t, 1)
    if durata < DURATION_MIN:
        raise ErrorePasso(None, f"il protocollo dura {_num_fmt(durata)}s: "
                                f"il minimo è {_num_fmt(DURATION_MIN)}s (un minuto)")
    if durata > DURATION_MAX:
        raise ErrorePasso(None, f"il protocollo dura {_num_fmt(durata)}s: "
                                f"il massimo è {_num_fmt(DURATION_MAX)}s (trenta minuti)")

    return {
        "score_version": 1,
        "duration_sec": float(durata),
        # espliciti: omessi, il contratto scriverebbe i SUOI default 5/10
        "fade_in_sec": 0.0,
        "fade_out_sec": 0.0,
        "layers": layers,
        "phases": [],
    }
