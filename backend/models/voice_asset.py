"""Frequenze by Aurya — spezzoni voce dell'operatore (FV1, 19/8/2026).

La voce e' l'ECCEZIONE DICHIARATA alla regola «ricetta non audio»
(docs/FREQUENZE_VOCE_PLAN_2026-08.md): le frequenze restano sintesi, la
voce e' per forza un file — ma piccolo (parlato compresso ~0.25 MB/min).

Tre paletti architetturali:
- SOLO registrazione in-app (MediaRecorder): niente upload di file
  arbitrari, coerente con la decisione founder del 18/8;
- asset PER-ORG (non libreria di piattaforma): la voce e' dell'operatore;
- byte su disco in uploads/voice/{org_id}/, MAI in Mongo (solo metadati).
"""

# MediaRecorder produce webm/opus (Chrome, Firefox) o mp4/aac (Safari).
# ogg per compatibilita' con vecchi Firefox.
ALLOWED_MIME_PREFIXES = ("audio/webm", "audio/mp4", "audio/ogg",
                         "audio/mpeg", "audio/aac", "video/webm")
MIME_TO_EXT = {
    "audio/webm": "webm", "video/webm": "webm",
    "audio/mp4": "m4a", "audio/aac": "m4a",
    "audio/ogg": "ogg", "audio/mpeg": "mp3",
}

CLIP_MAX_SECONDS = 600            # uno spezzone: fino a 10 minuti
CLIP_MAX_BYTES = 30 * 1024 * 1024  # 10 min aac 128k stereo con margine
ORG_QUOTA_BYTES = 100 * 1024 * 1024  # tetto complessivo per organizzazione
CLIPS_MAX_PER_ORG = 100
TITLE_MAX = 80

# FV6 — il taglio vive sulla REGISTRAZIONE, non sul livello in sessione
# (feedback founder 19/8: nella timeline la voce deve avere lo stesso
# specchietto degli altri suoni). Non e' distruttivo: il file resta
# intero, questi sono i secondi che la sessione salta ai due capi.
CLIP_MIN_USEFUL = 1.0             # dopo il taglio deve restare un secondo


def ext_for_mime(content_type):
    """Estensione per il MIME registrato, o None se fuori famiglia."""
    base = (content_type or "").split(";")[0].strip().lower()
    if not base.startswith(ALLOWED_MIME_PREFIXES):
        return None
    return MIME_TO_EXT.get(base, "webm")


def clamp_trim(trim_start, trim_end, duration_sec):
    """Taglio (inizio, fine) in secondi, sempre dentro la registrazione.

    Il vincolo e' uno solo: cio' che resta non scende mai sotto
    CLIP_MIN_USEFUL. Se la durata non e' nota si applica solo il tetto
    del clip, cosi' un metadato mancante non blocca la modifica.
    """
    dur = max(0.0, float(duration_sec or 0))
    start = max(0.0, min(float(trim_start or 0), CLIP_MAX_SECONDS))
    end = max(0.0, min(float(trim_end or 0), CLIP_MAX_SECONDS))
    if dur:
        start = min(start, max(0.0, dur - CLIP_MIN_USEFUL))
        end = min(end, max(0.0, dur - start - CLIP_MIN_USEFUL))
    return round(start, 2), round(end, 2)
