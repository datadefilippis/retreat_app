#!/usr/bin/env python3
"""PC1 (24/8/2026) — migrazione del privilegio del comporre.

`organizations.sound_composer` nasce FALSE per tutti; si accende
automaticamente SOLO alle org che hanno già composto (almeno una
traccia in frequency_tracks): chi usava Crea ieri non si sveglia
chiuso fuori — founder e org demo inclusi per costruzione.

Idempotente: si può rilanciare quante volte serve.
Uso: python3 scripts/pc1_sound_composer_migration.py
"""
import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


async def main():
    from database import organizations_collection, frequency_tracks_collection

    compositrici = await frequency_tracks_collection.distinct("organization_id")
    compositrici = [c for c in compositrici if c]
    r1 = await organizations_collection.update_many(
        {"id": {"$in": compositrici}, "sound_composer": {"$ne": True}},
        {"$set": {"sound_composer": True}})
    r2 = await organizations_collection.update_many(
        {"sound_composer": {"$exists": False}},
        {"$set": {"sound_composer": False}})
    print(f"org con tracce: {len(compositrici)} (accese ora: {r1.modified_count})")
    print(f"org senza flag -> false: {r2.modified_count}")


if __name__ == "__main__":
    asyncio.run(main())
