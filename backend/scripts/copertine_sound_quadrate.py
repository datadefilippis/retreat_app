"""MR1 (8/10/2026) — LE COPERTINE DI SOUND, UN FORMATO SOLO.

Per le meditazioni e le playlist PUBBLICATE:
  - chi ha una foto: la foto si rilegge dal disco, si ritaglia al centro in
    quadrato (1200, WebP) e si risalva; il documento punta alla nuova;
  - chi non ce l'ha: si genera la copertina (tono + titolo) e si salva.

A secco di default (dice cosa farebbe); `--applica` scrive. Idempotente:
una copertina gia' quadrata e WebP (nome con `.q.` o `.gen.`) non si rifa'.

  cd backend && venv/bin/python scripts/copertine_sound_quadrate.py
  cd backend && venv/bin/python scripts/copertine_sound_quadrate.py --applica
"""
import argparse
import asyncio
import io
import os
import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


def _file_locale(url: str):
    """Da /uploads/frequenze/x.webp al file su disco (storage locale)."""
    from services import object_storage
    radice = getattr(object_storage, "_UPLOADS_ROOT", None)
    if not radice or not url or "/uploads/" not in url:
        return None
    rel = url.split("/uploads/", 1)[1]
    p = Path(str(radice)) / rel
    return p if p.exists() else None


async def main(applica: bool) -> int:
    from database import frequency_tracks_collection, sound_playlists_collection
    from services.copertine_sound import quadra, salva_fallback_traccia, salva_fallback_playlist
    from services.object_storage import save_public_upload
    fatte = 0
    async for t in frequency_tracks_collection.find(
            {"status": "published", "visibility": {"$ne": "private"}},
            {"_id": 0, "id": 1, "title": 1, "intent": 1, "cover_url": 1, "score.duration_sec": 1, "duration_sec": 1}):
        cu = t.get("cover_url") or ""
        if ".q." in cu or ".gen." in cu:
            continue
        if not cu:
            print(f"[traccia] {t['id'][:8]} «{t.get('title')}»: senza foto → copertina generata")
            if applica:
                url = salva_fallback_traccia(t)
                if url:
                    await frequency_tracks_collection.update_one({"id": t["id"]}, {"$set": {"cover_url": url}})
                    fatte += 1
            continue
        f = _file_locale(cu)
        if not f:
            print(f"[traccia] {t['id'][:8]} «{t.get('title')}»: foto non trovata su disco ({cu}), salto")
            continue
        print(f"[traccia] {t['id'][:8]} «{t.get('title')}»: foto → quadrata")
        if applica:
            data, ext = quadra(f.read_bytes())
            url = save_public_upload("frequenze", f"{t['id']}.{uuid.uuid4().hex[:8]}.q.{ext}", data, content_type="image/webp")
            await frequency_tracks_collection.update_one({"id": t["id"]}, {"$set": {"cover_url": url}})
            fatte += 1
    async for p in sound_playlists_collection.find({"status": "published"}, {"_id": 0, "id": 1, "title": 1, "cover_url": 1, "tracce": 1}):
        cu = p.get("cover_url") or ""
        if ".q." in cu or ".gen." in cu:
            continue
        if not cu:
            print(f"[playlist] {p['id'][:8]} «{p.get('title')}»: senza foto → copertina generata")
            if applica:
                url = salva_fallback_playlist(p, len(p.get("tracce") or []))
                if url:
                    await sound_playlists_collection.update_one({"id": p["id"]}, {"$set": {"cover_url": url}})
                    fatte += 1
            continue
        f = _file_locale(cu)
        if not f:
            print(f"[playlist] {p['id'][:8]} «{p.get('title')}»: foto non trovata su disco ({cu}), salto")
            continue
        print(f"[playlist] {p['id'][:8]} «{p.get('title')}»: foto → quadrata")
        if applica:
            data, ext = quadra(f.read_bytes())
            url = save_public_upload("playlists", f"{p['id']}.{uuid.uuid4().hex[:8]}.q.{ext}", data, content_type="image/webp")
            await sound_playlists_collection.update_one({"id": p["id"]}, {"$set": {"cover_url": url}})
            fatte += 1
    print(f"{'scritte' if applica else 'a secco: da fare'}: {fatte if applica else '(vedi sopra)'}")
    return 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--applica", action="store_true")
    a = ap.parse_args()
    sys.exit(asyncio.run(main(a.applica)))
