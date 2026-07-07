"""AN3 — backfill one-shot: coordinate dei profili operatore.

Geocoda (Nominatim, stessa cache delle occurrence) le org con
public_profile.city ma senza coordinate, e deriva il GeoJSON per
l'indice 2dsphere. Idempotente e rispettoso del rate limit OSM.

Uso:  venv/bin/python scripts/backfill_org_geo.py [--dry-run]
"""

import asyncio
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
os.environ.setdefault("JWT_SECRET_KEY", "backfill")

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

DRY = "--dry-run" in sys.argv


async def main() -> None:
    from database import organizations_collection
    from services.geocoding import geocode, to_geojson

    done = skipped = 0
    async for org in organizations_collection.find(
            {"public_profile.city": {"$nin": [None, ""]},
             "public_profile.latitude": {"$exists": False}},
            {"_id": 0, "id": 1, "name": 1, "public_profile.city": 1,
             "public_profile.region": 1}):
        pp = org.get("public_profile") or {}
        coords = await geocode(pp.get("region"), city=pp["city"],
                               country="Italia")
        if not coords:
            skipped += 1
            print(f"  - {org.get('name')}: geocoding fallito per "
                  f"'{pp['city']}'")
            continue
        if not DRY:
            await organizations_collection.update_one(
                {"id": org["id"]},
                {"$set": {"public_profile.latitude": coords["lat"],
                          "public_profile.longitude": coords["lng"],
                          "public_profile.geo": to_geojson(
                              coords["lat"], coords["lng"])}})
        done += 1
        print(f"  + {org.get('name')}: {pp['city']} → "
              f"({coords['lat']:.4f}, {coords['lng']:.4f})")
        await asyncio.sleep(1.1)   # policy Nominatim: 1 req/s

    mode = "DRY-RUN" if DRY else "APPLICATO"
    print(f"[{mode}] geocodate: {done} | saltate: {skipped}")


if __name__ == "__main__":
    asyncio.run(main())
