"""Frequenze by Aurya (ciclo FQ, founder 18/8/2026) — modello traccia.

Il principio (docs/FREQUENZE_PLAN_2026-08.md): una traccia e' la RICETTA,
non l'audio. Lo "score" e' un documento JSON di pochi KB — livelli di
entrainment, fasi, dissolvenze — che il client risintetizza con WebAudio
a ogni ascolto. Niente file audio in Mongo, mai.

`score_version` e' il contratto: il formato puo' evolvere solo aggiungendo
versioni, mai cambiando la semantica della v1 — le tracce salvate oggi
devono suonare identiche tra un anno.
"""

SCORE_VERSION = 1

METHODS = ("bin", "iso", "mono", "bil", "noise", "tone")
TIMBRES = ("pure", "warm")
CURVES = ("lin", "exp", "steps")
INTENTS = ("dormire", "meditare", "rilassare", "concentrare",
           "elaborare", "energizzare")

# limiti fisici/di buon senso: gli stessi del prototipo, arrotondati.
DURATION_MIN, DURATION_MAX = 60, 7200          # 1 min .. 2 h
LAYERS_MAX = 24
PHASES_MAX = 12
BEAT_MIN, BEAT_MAX = 0.2, 60.0                 # Hz del battito
BIL_BEAT_MAX = 3.0                             # alternanza dx/sx tipica 0.5-1.5
CARRIER_MIN, CARRIER_MAX = 20.0, 2000.0        # Hz della portante / tono
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
    return layer


def clean_score(raw):
    """Score v1 validato, o None se il documento non e' uno score.

    Filosofia listino: i valori fuori range si riportano nel range
    (l'operatore non deve combattere col validatore), ma struttura
    sbagliata o vuota = rifiuto netto.
    """
    if not isinstance(raw, dict):
        return None
    if raw.get("score_version") not in (None, SCORE_VERSION):
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
    return {
        "score_version": SCORE_VERSION,
        "duration_sec": round(duration, 1),
        "fade_in_sec": round(_num(raw.get("fade_in_sec"), 0, 120, 10), 1),
        "fade_out_sec": round(_num(raw.get("fade_out_sec"), 0, 120, 20), 1),
        "layers": layers,
        "phases": phases,
    }


def clean_intent(raw):
    return raw if raw in INTENTS else None
