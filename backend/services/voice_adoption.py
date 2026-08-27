"""TM8 (27/8/2026) — gli spezzoni seguono la sessione: adozione e scopa.

Gira a ogni avvio, idempotente.

1. L'ADOZIONE: gli spezzoni registrati PRIMA della regola non hanno
   il campo `track_id`. Quelli che uno score referenzia (layer
   kind=voice, asset_id) vengono adottati dalla loro traccia — cosi'
   riappaiono nel leggio riaprendo la bozza giusta, come i livelli.
   Se piu' tracce usano lo stesso spezzone, adotta la prima trovata:
   il legame governa il LEGGIO, mai la risoluzione audio (che resta
   per asset_id, invariata).

2. LA SCOPA: gli spezzoni nati DOPO la regola (campo presente, valore
   null = sessione mai salvata), non referenziati da nessuno score e
   piu' vecchi di 7 giorni, si puliscono — file e documento. I LEGACY
   (campo assente) non si toccano MAI: registrazioni di voce non si
   cancellano senza consenso; restano visibili nel ripiego del leggio
   («Spezzoni senza sessione») finche' l'autore non li usa o elimina.
"""

import logging
from datetime import timedelta
from pathlib import Path

from models.common import utc_now

logger = logging.getLogger(__name__)

GIORNI_ORFANO = 7
VOICE_DIR = Path(__file__).resolve().parent.parent / "uploads" / "voice"


async def adotta_spezzoni() -> dict:
    from database import frequency_tracks_collection, voice_assets_collection

    # gli asset referenziati, traccia per traccia
    riferimenti: dict[str, str] = {}      # asset_id -> track_id (primo)
    async for t in frequency_tracks_collection.find(
            {}, {"_id": 0, "id": 1, "score.layers": 1}):
        for layer in ((t.get("score") or {}).get("layers") or []):
            if layer.get("kind") == "voice" and layer.get("asset_id"):
                riferimenti.setdefault(layer["asset_id"], t["id"])

    adottati = 0
    async for a in voice_assets_collection.find(
            {"track_id": {"$exists": False}}, {"_id": 0, "id": 1}):
        legame = riferimenti.get(a["id"])
        if legame:
            await voice_assets_collection.update_one(
                {"id": a["id"]}, {"$set": {"track_id": legame}})
            adottati += 1

    # la scopa: SOLO i post-regola (null esplicito), non referenziati,
    # vecchi. $type null non prende i legacy (campo assente).
    soglia = utc_now() - timedelta(days=GIORNI_ORFANO)
    spazzati = 0
    async for a in voice_assets_collection.find(
            {"track_id": {"$type": "null"},
             "created_at": {"$lt": soglia}},
            {"_id": 0, "id": 1, "stream_url": 1, "organization_id": 1}):
        if a["id"] in riferimenti:
            continue                      # uno score lo usa: si adotta, non si spazza
        percorso = (a.get("stream_url") or "").removeprefix("/uploads/voice/")
        try:
            if percorso and "/" in percorso and ".." not in percorso:
                f = VOICE_DIR / percorso
                if f.exists():
                    f.unlink()
            await voice_assets_collection.delete_one({"id": a["id"]})
            spazzati += 1
        except Exception as e:            # noqa: BLE001 — mai bloccare l'avvio
            logger.warning("voice_adoption: scopa fallita su %s: %s",
                           a["id"], e)

    if adottati or spazzati:
        logger.info("voice_adoption: %d adottati, %d orfani spazzati",
                    adottati, spazzati)
    return {"adottati": adottati, "spazzati": spazzati}
