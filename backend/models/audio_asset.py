"""Frequenze by Aurya — basi sonore curate (FQ2, 18/8/2026).

La libreria e' DELLA PIATTAFORMA: carica solo il system admin, con
licenza annotata (CC0 o licenziata — mai materiale di terzi senza
diritti). L'operatore le sceglie, non ne carica di sue (decisione
founder 18/8). I byte vivono su disco in uploads/audio/, mai in Mongo.
"""

# SL (20/8): l'ordine e' quello dei tab in Esplora → Suoni, dal letto
# piu' comune al dettaglio piu' raro. `corpo` e' la serie dalla radice
# alla testa; `transizioni` sono i passaggi brevi tra due momenti.
# Il frontend tiene la stessa lista (guardia di parita' nei test).
# CI (22/9/2026, founder): tre categorie in piu' per le ESPERIENZE —
# `melodie` (brani con un tema: archi, piano, flauto, orchestra; prima
# finivano in ambient, che era un contenitore da 104 suoni), `danza`
# (brani ritmici che portano il corpo, con un tempo) e `respiro` (le
# guide del respiro registrate: conteggi, respiro vero, campane di
# svolta). L'ordine resta «dal letto al dettaglio».
SOUND_CATEGORIES = {
    "ambient": "Ambient",
    "melodie": "Melodie",
    "natura": "Natura",
    "droni": "Droni",
    "corpo": "Corpo",
    "campane": "Campane",
    "ritmi": "Ritmi",
    "danza": "Danza",
    "voce": "Voce",
    "respiro": "Respiro",
    "transizioni": "Transizioni",
}

# ── I MOMENTI (24/8/2026) — il secondo asse della libreria ──────────
# La CATEGORIA dice com'e' fatto un suono (timbro); il MOMENTO dice a
# che punto del viaggio serve. Sono ortogonali: un drone puo' stare
# nell'Arrivo o nella Catarsi, e nella Catarsi convivono percussioni
# tribali e sussurri. Il founder organizza cosi' il suo materiale, ed
# e' il modo in cui si compone davvero una meditazione.
#
# L'ORDINE NON E' ALFABETICO ed e' quello del founder: si arriva, ci
# si attiva, si ATTRAVERSA la catarsi, poi si sale, poi si rientra.
# Chi lo cambia cambia la drammaturgia, non una lista.
SOUND_MOMENTS = {
    "arrivo": "Arrivo",
    "attivazione": "Attivazione",
    "catarsi": "Catarsi",
    "ascesa": "Ascesa",
    "rientro": "Rientro",
}

ALLOWED_EXTENSIONS = {"mp3", "m4a", "ogg", "wav"}
ALLOWED_MIME_PREFIXES = ("audio/",)
MAX_FILE_BYTES = 60 * 1024 * 1024   # 60MB: una base da ~30 min in mp3
TITLE_MAX = 80
LICENSE_MAX = 300


def clean_category(raw):
    return raw if raw in SOUND_CATEGORIES else None


def clean_moment(raw):
    """Il momento del viaggio, o None: un suono puo' non averlo (tutta
    la libreria di prima non ce l'ha, e resta valida)."""
    v = (raw or "").strip().lower()
    return v if v in SOUND_MOMENTS else None


# ── CI (22/9/2026) — i campi che servono alle ESPERIENZE MODELLO ─────
# Tutti facoltativi (la libreria di prima non li ha e resta valida):
# `bpm` il tempo del brano quando c'e' (danza, ritmi), `energia` 1-5
# (quanto spinge: 1 quiete, 5 picco), `tags` parole libere («tribale»,
# «flauto», «coro»). Servono a scegliere i suoni giusti per momento ed
# energia senza sfogliare duecento schede.
BPM_MIN, BPM_MAX = 30, 220
ENERGIA_MIN, ENERGIA_MAX = 1, 5
TAGS_MAX, TAG_LEN_MAX = 12, 32


def clean_bpm(raw):
    try:
        v = int(round(float(raw)))
    except (TypeError, ValueError):
        return None
    return v if BPM_MIN <= v <= BPM_MAX else None


def clean_energia(raw):
    try:
        v = int(raw)
    except (TypeError, ValueError):
        return None
    return v if ENERGIA_MIN <= v <= ENERGIA_MAX else None


def clean_tags(raw):
    """Lista pulita di parole (o None): da lista o da stringa «a, b, c»."""
    if raw is None:
        return None
    parti = raw if isinstance(raw, (list, tuple)) else str(raw).split(",")
    puliti = []
    for p in parti:
        t = str(p).strip().lower()[:TAG_LEN_MAX]
        if t and t not in puliti:
            puliti.append(t)
    return puliti[:TAGS_MAX] or None


# ── CI-F1 (22/9/2026) — LA GUIDA DEL RESPIRO ───────────────────────────
# I clip registrati dal founder (categoria `respiro`) portano due campi:
# `guida` dice COSA sono per il motore — `ciclo` (un respiro intero da
# ripetere: «inspira 1 2 3 4, espira 1 2 3 4»), `inspira`/`espira` (la
# parola sola, per le svolte delle ritenzioni), `conta` (i numeri una
# volta), `soffio_in`/`soffio_out` (il respiro vero, senza parole);
# `ciclo_sec` vale solo per i `ciclo`: ogni quanti secondi ricomincia.
# Il tempo e' quello della registrazione, non un numero da inventare:
# lo misura prepara_respiro.py sulla forma d'onda. engine/guida.js e'
# il gemello (guardia di parita').
GUIDA_TIPI = ("ciclo", "inspira", "espira", "conta", "soffio_in", "soffio_out")
CICLO_MIN, CICLO_MAX = 2.0, 60.0


def clean_guida(raw):
    v = (raw or "").strip().lower() if isinstance(raw, str) else ""
    return v if v in GUIDA_TIPI else None


def clean_ciclo_sec(raw):
    try:
        v = round(float(raw), 2)
    except (TypeError, ValueError):
        return None
    return v if CICLO_MIN <= v <= CICLO_MAX else None


def safe_extension(filename: str):
    """Estensione consentita del file, o None."""
    ext = (filename or "").rsplit(".", 1)[-1].lower()
    return ext if ext in ALLOWED_EXTENSIONS else None
