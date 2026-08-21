"""Frequenze by Aurya (ciclo FQ, founder 18/8/2026) — modello traccia.

Il principio (docs/FREQUENZE_PLAN_2026-08.md): una traccia e' la RICETTA,
non l'audio. Lo "score" e' un documento JSON di pochi KB — livelli di
entrainment, fasi, dissolvenze — che il client risintetizza con WebAudio
a ogni ascolto. Niente file audio in Mongo, mai.

`score_version` e' il contratto: il formato puo' evolvere solo aggiungendo
versioni, mai cambiando la semantica della v1 — le tracce salvate oggi
devono suonare identiche tra un anno.

v2 (FV1, 19/8): aggiunge il layer `kind:'voice'` (spezzone registrato
dall'operatore, con effetto selezionabile) e il flag `voice_duck` (le
basi si abbassano sotto la voce). Una ricetta si salva v2 SOLO se usa
la voce: tutto il pregresso resta v1, byte per byte.

v3 (ONDA 2, 21/8): aggiunge la curva `wave` e il campo `period` — il
battito non va piu' solo da f0 a f1, puo' andare e TORNARE all'infinito
(una marea). Stessa regola: una ricetta sale a v3 SOLO se una marea
c'e' davvero. Le tre curve monotone restano identiche, e una ricetta
salvata ieri suona oggi byte per byte com'era.
"""

SCORE_VERSION = 1
SCORE_VERSION_VOICE = 2
SCORE_VERSION_WAVE = 3
ACCEPTED_VERSIONS = (None, SCORE_VERSION, SCORE_VERSION_VOICE,
                     SCORE_VERSION_WAVE)

# preset effetto voce (engine/voicefx.js e' il gemello: tenerli allineati)
VOICE_FX = ("natural", "dream", "temple", "whisper")

METHODS = ("bin", "iso", "mono", "bil", "noise", "tone")
TIMBRES = ("pure", "warm")
CURVES = ("lin", "exp", "steps", "wave")
INTENTS = ("dormire", "meditare", "rilassare", "concentrare",
           "elaborare", "energizzare")

# limiti fisici/di buon senso: gli stessi del prototipo, arrotondati.
DURATION_MIN, DURATION_MAX = 60, 7200          # 1 min .. 2 h
LAYERS_MAX = 24
PHASES_MAX = 12
BEAT_MIN, BEAT_MAX = 0.2, 60.0                 # Hz del battito
BIL_BEAT_MAX = 3.0                             # alternanza dx/sx tipica 0.5-1.5
CARRIER_MIN, CARRIER_MAX = 20.0, 2000.0        # Hz della portante / tono
# ONDA 2 — il periodo della marea: sotto i 2 s non e' piu' un movimento
# ma un vibrato; sopra i 10 min il ritorno non si percepirebbe.
PERIOD_MIN, PERIOD_MAX, PERIOD_DEFAULT = 2.0, 600.0, 40.0
TITLE_MAX = 120
DESCRIPTION_MAX = 2000


def _num(value, lo, hi, default):
    """Numero nel range [lo, hi], o default se non interpretabile."""
    try:
        v = float(value)
    except (TypeError, ValueError):
        return default
    if v != v:  # NaN
        return default
    return max(lo, min(hi, v))


def clean_layer(raw, duration):
    """Un livello valido (neuro o base audio), o None se irrecuperabile.

    FQ2: un layer audio referenzia una base della libreria per
    `asset_id` — MAI byte audio nel documento (il campo `buffer` del
    client non passa di qui).
    """
    if not isinstance(raw, dict):
        return None
    if raw.get("kind") == "audio":
        asset_id = raw.get("asset_id")
        if not isinstance(asset_id, str) or not (1 <= len(asset_id) <= 64):
            return None
        start = _num(raw.get("start"), 0, duration, 0)
        end = _num(raw.get("end"), 0, duration, duration)
        if end - start < 0.5:
            end = min(duration, start + 0.5)
        return {
            "kind": "audio",
            "asset_id": asset_id,
            "name": str(raw.get("name") or "Base")[:60],
            "start": round(start, 3),
            "end": round(end, 3),
            "gain": _num(raw.get("gain"), 0.0, 1.0, 0.7),
            "loop": bool(raw.get("loop", True)),
            "mute": bool(raw.get("mute", False)),
        }
    if raw.get("kind") == "voice":
        asset_id = raw.get("asset_id")
        if not isinstance(asset_id, str) or not (1 <= len(asset_id) <= 64):
            return None
        start = _num(raw.get("start"), 0, duration, 0)
        end = _num(raw.get("end"), 0, duration, duration)
        if end - start < 0.5:
            end = min(duration, start + 0.5)
        return {
            "kind": "voice",
            "asset_id": asset_id,
            "name": str(raw.get("name") or "Voce")[:60],
            "start": round(start, 3),
            "end": round(end, 3),
            "gain": _num(raw.get("gain"), 0.0, 1.0, 0.9),
            "fx": raw.get("fx") if raw.get("fx") in VOICE_FX else "dream",
            "fx_amount": _num(raw.get("fx_amount"), 0.0, 1.0, 0.6),
            # FV5 — taglio non distruttivo: salta i primi N secondi del
            # clip (il file resta intatto, il taglio vive nella ricetta)
            "clip_in": round(_num(raw.get("clip_in"), 0.0, 3600.0, 0.0), 2),
            "mute": bool(raw.get("mute", False)),
        }
    method = raw.get("method")
    if method not in METHODS:
        return None
    start = _num(raw.get("start"), 0, duration, 0)
    end = _num(raw.get("end"), 0, duration, duration)
    if end - start < 0.5:
        end = min(duration, start + 0.5)
    beat_hi = BIL_BEAT_MAX if method == "bil" else BEAT_MAX
    layer = {
        "kind": "neuro",
        "name": str(raw.get("name") or "Livello")[:60],
        "method": method,
        "timbre": raw.get("timbre") if raw.get("timbre") in TIMBRES else "warm",
        "carrier": _num(raw.get("carrier"), CARRIER_MIN, CARRIER_MAX, 180.0),
        "f0": _num(raw.get("f0"), BEAT_MIN, beat_hi, min(10.0, beat_hi)),
        "f1": _num(raw.get("f1"), BEAT_MIN, beat_hi, min(10.0, beat_hi)),
        "curve": raw.get("curve") if raw.get("curve") in CURVES else "lin",
        "start": round(start, 3),
        "end": round(end, 3),
        "gain": _num(raw.get("gain"), 0.0, 1.0, 0.25),
        "breath": bool(raw.get("breath", True)),
        "mute": bool(raw.get("mute", False)),
    }
    # ONDA 2 — il periodo esiste solo per la marea: sugli altri livelli
    # sarebbe un campo muto che confonde chi legge il documento
    if layer["curve"] == "wave":
        layer["period"] = round(
            _num(raw.get("period"), PERIOD_MIN, PERIOD_MAX, PERIOD_DEFAULT), 2)
    return layer


def clean_score(raw):
    """Score v1 validato, o None se il documento non e' uno score.

    Filosofia listino: i valori fuori range si riportano nel range
    (l'operatore non deve combattere col validatore), ma struttura
    sbagliata o vuota = rifiuto netto.
    """
    if not isinstance(raw, dict):
        return None
    if raw.get("score_version") not in ACCEPTED_VERSIONS:
        return None  # versioni future: mai degradarle in silenzio
    duration = _num(raw.get("duration_sec"), DURATION_MIN, DURATION_MAX, 1200)
    layers_raw = raw.get("layers")
    if not isinstance(layers_raw, list) or not layers_raw:
        return None
    layers = []
    for item in layers_raw[:LAYERS_MAX]:
        cl = clean_layer(item, duration)
        if cl:
            layers.append(cl)
    if not layers:
        return None
    phases = []
    for p in (raw.get("phases") or [])[:PHASES_MAX]:
        if isinstance(p, dict):
            phases.append({
                "t": round(_num(p.get("t"), 0, duration, 0), 3),
                "name": str(p.get("name") or "fase")[:40],
            })
    phases.sort(key=lambda p: p["t"])
    voice_duck = bool(raw.get("voice_duck", False))
    has_voice = any(l.get("kind") == "voice" for l in layers)
    has_wave = any(l.get("curve") == "wave" for l in layers)
    score = {
        # la versione sale SOLO dove serve: il pregresso resta identico.
        # v3 (marea) ha la precedenza su v2 perche' la include.
        "score_version": SCORE_VERSION_WAVE if has_wave
                         else SCORE_VERSION_VOICE if (has_voice or voice_duck)
                         else SCORE_VERSION,
        "duration_sec": round(duration, 1),
        "fade_in_sec": round(_num(raw.get("fade_in_sec"), 0, 120, 10), 1),
        "fade_out_sec": round(_num(raw.get("fade_out_sec"), 0, 120, 20), 1),
        "layers": layers,
        "phases": phases,
    }
    if has_voice or voice_duck:
        score["voice_duck"] = voice_duck
    return score


def clean_intent(raw):
    return raw if raw in INTENTS else None
