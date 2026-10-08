"""MR4 (8/10/2026) — pianta il seme «Meditazioni guidate» e assegna la
categoria alle meditazioni che non ce l'hanno. A secco di default.

  cd backend && venv/bin/python scripts/categorie_sound_seme.py
  cd backend && venv/bin/python scripts/categorie_sound_seme.py --applica
"""
import argparse
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


async def main(applica: bool) -> int:
    from database import frequency_tracks_collection, sound_playlists_collection
    from services import categorie_sound as C
    voci = await C.elenco(solo_attive=False)   # pianta il seme se manca
    print("registro:", [f"{c['slug']} ({'attiva' if c.get('attiva', True) else 'spenta'})" for c in voci])
    seme = C.SEME["slug"]
    q = {"categoria": {"$in": [None, ""]}}
    n = await frequency_tracks_collection.count_documents(q)
    print(f"meditazioni senza categoria: {n} → «{seme}»")
    if applica and n:
        r = await frequency_tracks_collection.update_many(q, {"$set": {"categoria": seme}})
        print("aggiornate:", r.modified_count)
    np = await sound_playlists_collection.count_documents(q)
    print(f"playlist senza categoria: {np} (facoltativa: restano cosi')")
    return 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--applica", action="store_true")
    sys.exit(asyncio.run(main(ap.parse_args().applica)))
