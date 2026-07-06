"""Backfill geocoding per le occurrence esistenti (G1, one-off).

Geocoda le occurrence con indirizzo/citta' ma senza lat/lng, e deriva
il campo `geo` per quelle che hanno gia' le coordinate. Idempotente,
rispetta il rate-limit Nominatim (1 req/s, gestito dal service).

Uso:
    ./venv/bin/python -m scripts.backfill_geo          # dry-run
    ./venv/bin/python -m scripts.backfill_geo --apply
"""

import argparse
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


async def main(apply: bool) -> None:
    from database import event_occurrences_collection
    from services.geocoding import enrich_occurrence_geo, to_geojson

    cursor = event_occurrences_collection.find(
        {}, {"_id": 0, "id": 1, "address": 1, "city": 1, "postal_code": 1,
             "country": 1, "latitude": 1, "longitude": 1, "geo": 1})
    scanned = geocoded = derived = skipped = 0
    async for occ in cursor:
        scanned += 1
        has_coords = occ.get("latitude") is not None and occ.get("longitude") is not None
        has_geo = occ.get("geo") is not None
        if has_coords and has_geo:
            skipped += 1
            continue
        if has_coords:
            # solo derivazione geo, niente rete
            geo = to_geojson(occ["latitude"], occ["longitude"])
            if geo and apply:
                await event_occurrences_collection.update_one(
                    {"id": occ["id"]}, {"$set": {"geo": geo}})
            derived += 1
            print(f"  geo derivato: {occ['id']} ({occ.get('city')})")
            continue
        if not (occ.get("city") or occ.get("address")):
            skipped += 1
            continue
        before = dict(occ)
        await enrich_occurrence_geo(occ)
        if occ.get("geo"):
            geocoded += 1
            print(f"  geocodato: {occ['id']} {occ.get('city')} → "
                  f"{occ['latitude']:.4f},{occ['longitude']:.4f}")
            if apply:
                await event_occurrences_collection.update_one(
                    {"id": occ["id"]},
                    {"$set": {"latitude": occ["latitude"],
                              "longitude": occ["longitude"],
                              "geo": occ["geo"]}})
        else:
            skipped += 1
            print(f"  MISS: {occ['id']} ({occ.get('city')})")

    mode = "APPLICATO" if apply else "DRY-RUN (usa --apply)"
    print(f"\n{mode}: scansionate {scanned}, geocodate {geocoded}, "
          f"geo derivati {derived}, saltate {skipped}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    asyncio.run(main(args.apply))
