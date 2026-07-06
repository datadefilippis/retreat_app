"""Geocoding gratuito via Nominatim/OSM (G1, docs/GEO_SEARCH_PLAN.md).

Vincolo founder: zero costi. Nominatim e' gratis con policy precise:
  - User-Agent identificativo obbligatorio
  - max 1 richiesta/secondo
  - cache: mai ri-geocodare lo stesso indirizzo

Regole nostre:
  - BEST-EFFORT SEMPRE: il geocoding non blocca mai un salvataggio.
    Timeout corto, ogni eccezione ritorna None.
  - cache su collection `geocode_cache` (chiave = indirizzo normalizzato),
    anche i MISS vengono cachati (found=False) per non martellare
    Nominatim con indirizzi invalidi.
  - il campo `geo` (GeoJSON Point) e' DERIVATO da latitude/longitude:
    lat/lng restano la verita' editabile, geo e' solo l'indice 2dsphere.
"""

import asyncio
import logging
import os
import time
from typing import Any, Dict, Optional

import httpx

logger = logging.getLogger(__name__)

NOMINATIM_URL = os.environ.get(
    "NOMINATIM_URL", "https://nominatim.openstreetmap.org/search")
# Policy OSM: User-Agent che identifica l'applicazione.
USER_AGENT = os.environ.get(
    "GEOCODE_USER_AGENT", "retreat-app-dev/1.0 (geocoding eventi)")
TIMEOUT_S = 4.0

# Rate-limit di processo: 1 req/s (policy Nominatim). Con il geocoding
# solo-al-salvataggio non si raggiunge mai, ma la guardia resta.
_last_call_ts = 0.0
_lock = asyncio.Lock()


def normalize_address(address: Optional[str], city: Optional[str],
                      postal_code: Optional[str], country: Optional[str]) -> str:
    """Chiave di cache stabile: parti presenti, lowercased, separate da virgola."""
    parts = [p.strip().lower() for p in (address, city, postal_code, country) if p and p.strip()]
    return ", ".join(parts)


def to_geojson(latitude: Optional[float], longitude: Optional[float]) -> Optional[Dict[str, Any]]:
    """GeoJSON Point [lng, lat] per l'indice 2dsphere. None se incompleto."""
    if latitude is None or longitude is None:
        return None
    try:
        lat, lng = float(latitude), float(longitude)
    except (TypeError, ValueError):
        return None
    if not (-90 <= lat <= 90 and -180 <= lng <= 180):
        return None
    return {"type": "Point", "coordinates": [lng, lat]}


async def geocode(address: Optional[str], city: Optional[str] = None,
                  postal_code: Optional[str] = None,
                  country: Optional[str] = None) -> Optional[Dict[str, float]]:
    """{lat, lng} dall'indirizzo, o None. Cache-first, best-effort."""
    query = normalize_address(address, city, postal_code, country)
    if not query:
        return None

    from database import db
    cached = await db.geocode_cache.find_one({"query": query}, {"_id": 0})
    if cached is not None:
        if cached.get("found"):
            return {"lat": cached["lat"], "lng": cached["lng"]}
        return None

    global _last_call_ts
    try:
        async with _lock:
            wait = 1.0 - (time.monotonic() - _last_call_ts)
            if wait > 0:
                await asyncio.sleep(wait)
            _last_call_ts = time.monotonic()
            async with httpx.AsyncClient(timeout=TIMEOUT_S) as client:
                resp = await client.get(NOMINATIM_URL, params={
                    "q": query, "format": "json", "limit": 1,
                }, headers={"User-Agent": USER_AGENT})
        resp.raise_for_status()
        results = resp.json()
    except Exception as exc:
        # best-effort: nessun retry qui, nessun blocco del chiamante;
        # il miss NON viene cachato (potrebbe essere un problema di rete)
        logger.warning("geocode fallito per %r: %s", query, exc)
        return None

    doc = {"query": query, "found": False}
    out = None
    if results:
        try:
            lat = float(results[0]["lat"])
            lng = float(results[0]["lon"])
            doc.update({"found": True, "lat": lat, "lng": lng,
                        "display_name": results[0].get("display_name")})
            out = {"lat": lat, "lng": lng}
        except (KeyError, TypeError, ValueError):
            pass
    await db.geocode_cache.update_one(
        {"query": query}, {"$set": doc}, upsert=True)
    return out


async def enrich_occurrence_geo(doc: Dict[str, Any]) -> Dict[str, Any]:
    """Completa lat/lng (geocoding se mancano) e deriva `geo`. Muta e ritorna doc.

    Chiamata dai path di salvataggio occurrence. Mai eccezioni verso l'alto.
    """
    try:
        if doc.get("latitude") is None or doc.get("longitude") is None:
            if doc.get("city") or doc.get("address"):
                hit = await geocode(doc.get("address"), doc.get("city"),
                                    doc.get("postal_code"), doc.get("country"))
                if hit:
                    doc["latitude"] = hit["lat"]
                    doc["longitude"] = hit["lng"]
        geo = to_geojson(doc.get("latitude"), doc.get("longitude"))
        if geo is not None:
            doc["geo"] = geo
        elif "latitude" in doc or "longitude" in doc:
            # coordinate rimosse/invalide → via anche l'indice
            doc["geo"] = None
    except Exception as exc:
        logger.warning("enrich_occurrence_geo: %s", exc)
    return doc
