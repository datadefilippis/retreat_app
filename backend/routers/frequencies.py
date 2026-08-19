"""Frequenze by Aurya — router bozze (FQ0, 18/8/2026).

CRUD org-scoped delle tracce vibrazionali in stato bozza: l'operatore
compone a /frequenze, salva la ricetta (score JSON), la riprende.
Nessuna superficie pubblica in FQ0 — publish/slug/player arrivano con FQ1,
insieme alla cittadinanza modulo (chiave `frequencies` in MODULE_OWNERSHIP).

Isolamento: collection dedicata `frequency_tracks`, zero riferimenti a
products/orders/stores. Vedi docs/FREQUENZE_PLAN_2026-08.md.
"""

import logging
import os
import uuid
from pathlib import Path
from typing import Optional

from fastapi import (
    APIRouter, Depends, File, Form, HTTPException, Request, UploadFile, status,
)
from pydantic import BaseModel

from auth import (
    get_current_platform_account, get_current_user, require_system_admin,
)
from models.audio_asset import (
    LICENSE_MAX, MAX_FILE_BYTES, SOUND_CATEGORIES,
    clean_category, safe_extension,
)
from models.audio_asset import TITLE_MAX as SOUND_TITLE_MAX
from models.common import utc_now
from models.frequency_track import (
    DESCRIPTION_MAX, TITLE_MAX, clean_intent, clean_score,
)

# i byte delle basi vivono qui, serviti dallo static mount /uploads
AUDIO_DIR = Path(__file__).resolve().parent.parent / "uploads" / "audio"

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/frequencies", tags=["Frequenze"])

TRACKS_MAX_PER_ORG = 200  # tetto anti-runaway: sono documenti da pochi KB

_LIST_PROJECTION = {
    "_id": 0, "id": 1, "title": 1, "intent": 1, "status": 1,
    "slug": 1, "plays_total": 1,
    "created_at": 1, "updated_at": 1,
    # della ricetta, in lista, serve solo la durata
    "score.duration_sec": 1, "score.layers": 1,
}


class TrackCreate(BaseModel):
    title: str
    score: dict
    description: Optional[str] = None
    intent: Optional[str] = None


class TrackUpdate(BaseModel):
    title: Optional[str] = None
    score: Optional[dict] = None
    description: Optional[str] = None
    intent: Optional[str] = None


def _doc(track: dict) -> dict:
    track.pop("_id", None)
    return track


def _validated_score(raw: dict) -> dict:
    score = clean_score(raw)
    if score is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ricetta non valida: serve almeno un livello.")
    return score


@router.get("/tracks")
async def list_tracks(current_user: dict = Depends(get_current_user)):
    from database import frequency_tracks_collection
    items = await frequency_tracks_collection.find(
        {"organization_id": current_user["organization_id"]},
        _LIST_PROJECTION,
    ).sort("updated_at", -1).to_list(TRACKS_MAX_PER_ORG)
    for it in items:
        score = it.pop("score", None) or {}
        it["duration_sec"] = score.get("duration_sec")
        it["layers_count"] = len(score.get("layers") or [])
    return {"items": items}


@router.post("/tracks", status_code=status.HTTP_201_CREATED)
async def create_track(payload: TrackCreate,
                       current_user: dict = Depends(get_current_user)):
    from database import frequency_tracks_collection
    org_id = current_user["organization_id"]
    count = await frequency_tracks_collection.count_documents(
        {"organization_id": org_id})
    if count >= TRACKS_MAX_PER_ORG:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Limite di {TRACKS_MAX_PER_ORG} tracce raggiunto.")
    title = (payload.title or "").strip()[:TITLE_MAX]
    if not title:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="Serve un titolo.")
    now = utc_now()
    track = {
        "id": str(uuid.uuid4()),
        "organization_id": org_id,
        "title": title,
        "description": (payload.description or "").strip()[:DESCRIPTION_MAX],
        "intent": clean_intent(payload.intent),
        "status": "draft",   # publish arriva con FQ1
        "score": _validated_score(payload.score),
        "created_at": now,
        "updated_at": now,
    }
    await frequency_tracks_collection.insert_one(dict(track))
    return _doc(track)


@router.get("/tracks/{track_id}")
async def get_track(track_id: str,
                    current_user: dict = Depends(get_current_user)):
    from database import frequency_tracks_collection
    track = await frequency_tracks_collection.find_one(
        {"id": track_id,
         "organization_id": current_user["organization_id"]})
    if not track:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="Traccia non trovata.")
    return _doc(track)


@router.patch("/tracks/{track_id}")
async def update_track(track_id: str, payload: TrackUpdate,
                       current_user: dict = Depends(get_current_user)):
    from database import frequency_tracks_collection
    updates = {}
    if payload.title is not None:
        title = payload.title.strip()[:TITLE_MAX]
        if not title:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                                detail="Serve un titolo.")
        updates["title"] = title
    if payload.description is not None:
        updates["description"] = payload.description.strip()[:DESCRIPTION_MAX]
    if payload.intent is not None:
        updates["intent"] = clean_intent(payload.intent)
    if payload.score is not None:
        updates["score"] = _validated_score(payload.score)
    if not updates:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="Nessuna modifica.")
    updates["updated_at"] = utc_now()
    result = await frequency_tracks_collection.find_one_and_update(
        {"id": track_id,
         "organization_id": current_user["organization_id"]},
        {"$set": updates}, return_document=True)
    if not result:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="Traccia non trovata.")
    return _doc(result)


@router.delete("/tracks/{track_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_track(track_id: str,
                       current_user: dict = Depends(get_current_user)):
    from database import frequency_tracks_collection
    result = await frequency_tracks_collection.delete_one(
        {"id": track_id,
         "organization_id": current_user["organization_id"]})
    if result.deleted_count == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="Traccia non trovata.")


# ── FQ1 — pubblicazione e ascolto pubblico ──────────────────────────────────
# La traccia pubblicata resta la RICETTA: il player pubblico la
# risintetizza col motore client. Il cancello d'ascolto (anteprima
# libera, poi Lettera o account Aurya) e' un soft-wall lato client:
# il contenuto e' gratuito, il gate e' cattura contatto, non DRM.

_PUBLIC_PROJECTION = {"_id": 0, "id": 1, "slug": 1, "title": 1,
                      "description": 1, "intent": 1, "score": 1,
                      "plays_total": 1, "organization_id": 1}
_SLUG_ATTEMPTS = 50


async def _unique_track_slug(base: str) -> str:
    from models.event_occurrence import slugify
    from database import frequency_tracks_collection
    root = slugify(base)[:46] or "sessione"
    candidate = root
    for n in range(2, _SLUG_ATTEMPTS + 2):
        clash = await frequency_tracks_collection.find_one(
            {"slug": candidate}, {"_id": 1})
        if not clash:
            return candidate
        candidate = f"{root}-{n}"
    return f"{root}-{uuid.uuid4().hex[:6]}"


@router.post("/tracks/{track_id}/publish")
async def publish_track(track_id: str,
                        current_user: dict = Depends(get_current_user)):
    from database import frequency_tracks_collection
    track = await frequency_tracks_collection.find_one(
        {"id": track_id,
         "organization_id": current_user["organization_id"]})
    if not track:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="Traccia non trovata.")
    slug = track.get("slug") or await _unique_track_slug(track["title"])
    await frequency_tracks_collection.update_one(
        {"id": track_id,
         "organization_id": current_user["organization_id"]},
        {"$set": {"status": "published", "slug": slug,
                  "published_at": utc_now(), "updated_at": utc_now()}})
    return {"id": track_id, "status": "published", "slug": slug}


@router.post("/tracks/{track_id}/unpublish")
async def unpublish_track(track_id: str,
                          current_user: dict = Depends(get_current_user)):
    from database import frequency_tracks_collection
    result = await frequency_tracks_collection.find_one_and_update(
        {"id": track_id,
         "organization_id": current_user["organization_id"]},
        # lo slug resta: ripubblicando, il link gia' condiviso rivive
        {"$set": {"status": "draft", "updated_at": utc_now()}})
    if not result:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="Traccia non trovata.")
    return {"id": track_id, "status": "draft"}


@router.get("/public/{slug}")
async def public_track(slug: str):
    """Payload del player pubblico: ricetta + chi l'ha composta."""
    from database import frequency_tracks_collection, organizations_collection
    track = await frequency_tracks_collection.find_one(
        {"slug": slug, "status": "published"}, _PUBLIC_PROJECTION)
    if not track:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="Traccia non trovata.")
    org = await organizations_collection.find_one(
        {"id": track.pop("organization_id")},
        {"_id": 0, "name": 1, "public_slug": 1,
         "public_profile.display_name": 1})
    profile = (org or {}).get("public_profile") or {}
    track["operator"] = {
        "name": profile.get("display_name") or (org or {}).get("name"),
        # lo slug pubblico vive in cima al doc org (non nel profilo)
        "slug": (org or {}).get("public_slug"),
    }
    track["plays_total"] = track.get("plays_total") or 0
    # FV4 — la ricetta v2 referenzia spezzoni voce per asset_id: il
    # player anonimo non puo' interrogare l'endpoint org-scoped, quindi
    # gli URL viaggiano nel payload (solo id+stream: mai id interni)
    voice_ids = [l.get("asset_id") for l in
                 (track.get("score") or {}).get("layers", [])
                 if l.get("kind") == "voice" and l.get("asset_id")]
    if voice_ids:
        from database import voice_assets_collection
        clips = await voice_assets_collection.find(
            {"id": {"$in": voice_ids}},
            {"_id": 0, "id": 1, "stream_url": 1, "duration_sec": 1},
        ).to_list(len(voice_ids))
        track["voice_assets"] = clips
    return track


@router.post("/public/{slug}/play", status_code=status.HTTP_204_NO_CONTENT)
async def register_play(slug: str):
    from database import frequency_tracks_collection
    await frequency_tracks_collection.update_one(
        {"slug": slug, "status": "published"},
        {"$inc": {"plays_total": 1}})


# ── FQ3 — vetrina /meditazioni: catalogo DIETRO il cancello ────────────────
# La vetrina e' l'incentivo (decisione founder 18/8): senza sblocco il
# catalogo NON si vede. Lo sblocco e' verificato SERVER-SIDE, senza
# toccare i sistemi consolidati:
#   - iscritto Lettera → POST /catalog/unlock verifica l'email in
#     aurya_subscribers e firma un token HMAC (nessuna nuova sessione,
#     nessuna scrittura: solo lettura della collection della Lettera);
#   - account Aurya → Bearer platform gia' esistente (P1).
# I preferiti vivono in una collection dedicata (frequency_favorites),
# agganciata all'account per id: zero campi nuovi su platform_accounts.

import hashlib
import hmac as hmac_mod


def _catalog_token(email: str) -> str:
    from auth import SECRET_KEY
    return hmac_mod.new(SECRET_KEY.encode(),
                        f"fqz-catalog:{email.lower().strip()}".encode(),
                        hashlib.sha256).hexdigest()


async def _subscriber_ok(email: str) -> bool:
    from database import db
    doc = await db.aurya_subscribers.find_one(
        {"email": email.lower().strip()}, {"_id": 0, "status": 1, "consent": 1})
    return bool(doc and doc.get("consent")
                and doc.get("status") != "unsubscribed")


class UnlockPayload(BaseModel):
    email: str


@router.post("/catalog/unlock")
async def catalog_unlock(payload: UnlockPayload):
    """Sblocco per iscritti Lettera: l'email deve esistere davvero tra
    gli iscritti con consenso. Il token e' deterministico (HMAC): si
    revoca solo disiscrivendosi — e' un lucchetto da vetrina, non una
    sessione."""
    email = payload.email.lower().strip()
    if not await _subscriber_ok(email):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Questa email non risulta iscritta alla Lettera.")
    return {"email": email, "token": _catalog_token(email)}


async def _has_catalog_access(request) -> bool:
    """Vero se la richiesta porta uno sblocco valido: header
    X-Fqz-Unlock (email:token HMAC, ri-verificato contro gli iscritti)
    oppure un Bearer platform valido."""
    unlock = request.headers.get("X-Fqz-Unlock", "")
    if ":" in unlock:
        email, token = unlock.split(":", 1)
        if (hmac_mod.compare_digest(token, _catalog_token(email))
                and await _subscriber_ok(email)):
            return True
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        try:
            from auth import decode_token
            payload = decode_token(auth_header[7:])
            if payload.get("type") == "platform" and payload.get("sub"):
                return True
        except Exception:  # token non-platform o scaduto: non sblocca
            pass
    return False


_CATALOG_PROJECTION = {"_id": 0, "slug": 1, "title": 1, "description": 1,
                       "intent": 1, "plays_total": 1, "organization_id": 1,
                       "score.duration_sec": 1, "score.layers": 1,
                       "published_at": 1}


@router.get("/catalog")
async def catalog(request: Request):
    """Tutte le meditazioni pubblicate, di tutti gli operatori — SOLO
    con sblocco. Senza: 403 col conteggio (il teaser dello schermo
    d'invito)."""
    from database import frequency_tracks_collection, organizations_collection
    if not await _has_catalog_access(request):
        count = await frequency_tracks_collection.count_documents(
            {"status": "published"})
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"error": "locked", "tracks_count": count})
    items = await frequency_tracks_collection.find(
        {"status": "published"}, _CATALOG_PROJECTION,
    ).sort("published_at", -1).to_list(500)
    org_ids = {i["organization_id"] for i in items}
    orgs = {o["id"]: o async for o in organizations_collection.find(
        {"id": {"$in": list(org_ids)}},
        {"_id": 0, "id": 1, "name": 1, "public_slug": 1,
         "public_profile.display_name": 1})}
    out = []
    for it in items:
        org = orgs.get(it.pop("organization_id")) or {}
        profile = org.get("public_profile") or {}
        score = it.pop("score", None) or {}
        it["duration_sec"] = score.get("duration_sec")
        it["layers_count"] = len(score.get("layers") or [])
        it["operator"] = {
            "name": profile.get("display_name") or org.get("name"),
            "slug": org.get("public_slug"),
        }
        it["plays_total"] = it.get("plays_total") or 0
        out.append(it)
    return {"items": out}


@router.get("/favorites")
async def list_favorites(account: dict = Depends(get_current_platform_account)):
    from database import db, frequency_tracks_collection
    favs = await db.frequency_favorites.find(
        {"platform_account_id": account["id"]},
        {"_id": 0, "slug": 1}).to_list(500)
    slugs = [f["slug"] for f in favs]
    tracks = await frequency_tracks_collection.find(
        {"slug": {"$in": slugs}, "status": "published"},
        {"_id": 0, "slug": 1, "title": 1, "intent": 1,
         "score.duration_sec": 1}).to_list(500)
    by_slug = {t["slug"]: t for t in tracks}
    items = []
    for slug in slugs:
        t = by_slug.get(slug)
        if t:
            score = t.pop("score", None) or {}
            t["duration_sec"] = score.get("duration_sec")
            items.append(t)
    return {"items": items, "slugs": slugs}


@router.put("/favorites/{slug}", status_code=status.HTTP_204_NO_CONTENT)
async def add_favorite(slug: str,
                       account: dict = Depends(get_current_platform_account)):
    from database import db, frequency_tracks_collection
    track = await frequency_tracks_collection.find_one(
        {"slug": slug, "status": "published"}, {"_id": 1})
    if not track:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="Meditazione non trovata.")
    await db.frequency_favorites.update_one(
        {"platform_account_id": account["id"], "slug": slug},
        {"$setOnInsert": {"created_at": utc_now()}}, upsert=True)


@router.delete("/favorites/{slug}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_favorite(slug: str,
                          account: dict = Depends(get_current_platform_account)):
    from database import db
    await db.frequency_favorites.delete_one(
        {"platform_account_id": account["id"], "slug": slug})


# ── FQ2 — libreria suoni curata ─────────────────────────────────────────────
# GET pubblica (contenuto di piattaforma: la vede anche il player FQ1);
# scrittura SOLO system admin, con licenza annotata.

_SOUND_PROJECTION = {"_id": 0, "id": 1, "title": 1, "category": 1,
                     "duration_sec": 1, "size_bytes": 1, "stream_url": 1}


@router.get("/sounds")
async def list_sounds():
    from database import audio_assets_collection
    items = await audio_assets_collection.find(
        {}, _SOUND_PROJECTION).sort("created_at", -1).to_list(500)
    return {"items": items, "categories": SOUND_CATEGORIES}


@router.post("/sounds", status_code=status.HTTP_201_CREATED)
async def upload_sound(file: UploadFile = File(...),
                       title: str = Form(...),
                       category: str = Form(...),
                       duration_sec: float = Form(0),
                       license_note: str = Form(""),
                       admin: dict = Depends(require_system_admin)):
    cat = clean_category(category)
    if not cat:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="Categoria non valida.")
    ext = safe_extension(file.filename)
    if not ext or not (file.content_type or "").startswith("audio/"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="Formato non supportato (mp3, m4a, ogg, wav).")
    clean_title = title.strip()[:SOUND_TITLE_MAX]
    if not clean_title:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="Serve un titolo.")
    data = await file.read()
    if len(data) > MAX_FILE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File oltre {MAX_FILE_BYTES // (1024 * 1024)}MB.")
    asset_id = str(uuid.uuid4())
    AUDIO_DIR.mkdir(parents=True, exist_ok=True)
    path = AUDIO_DIR / f"{asset_id}.{ext}"
    path.write_bytes(data)
    from database import audio_assets_collection
    asset = {
        "id": asset_id,
        "owner": "platform",
        "title": clean_title,
        "category": cat,
        "duration_sec": round(max(0.0, float(duration_sec or 0)), 1),
        "size_bytes": len(data),
        "mime": file.content_type,
        "stream_url": f"/uploads/audio/{asset_id}.{ext}",
        "license_note": (license_note or "").strip()[:LICENSE_MAX],
        "uploaded_by": admin.get("email"),
        "created_at": utc_now(),
    }
    await audio_assets_collection.insert_one(dict(asset))
    asset.pop("_id", None)
    return asset


@router.delete("/sounds/{asset_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_sound(asset_id: str,
                       admin: dict = Depends(require_system_admin)):
    from database import audio_assets_collection
    asset = await audio_assets_collection.find_one({"id": asset_id})
    if not asset:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="Suono non trovato.")
    await audio_assets_collection.delete_one({"id": asset_id})
    stream = asset.get("stream_url") or ""
    fname = os.path.basename(stream)
    if fname:
        try:
            (AUDIO_DIR / fname).unlink(missing_ok=True)
        except OSError:
            logger.warning("file base %s non rimosso", fname)


# ── FV1 — spezzoni voce dell'operatore ──────────────────────────────────────
# La voce e' PER-ORG e nasce SOLO dalla registrazione in-app (niente
# upload di file arbitrari — decisione founder 18/8). Byte su disco in
# uploads/voice/{org_id}/, metadati in voice_assets. Quota per org.

from models.voice_asset import (          # noqa: E402  (sezione FV1)
    CLIP_MAX_BYTES, CLIP_MAX_SECONDS, CLIPS_MAX_PER_ORG,
    ORG_QUOTA_BYTES, ext_for_mime,
)
from models.voice_asset import TITLE_MAX as VOICE_TITLE_MAX  # noqa: E402

VOICE_DIR = Path(__file__).resolve().parent.parent / "uploads" / "voice"

_VOICE_PROJECTION = {"_id": 0, "id": 1, "title": 1, "duration_sec": 1,
                     "size_bytes": 1, "stream_url": 1, "created_at": 1}


@router.get("/voice")
async def list_voice_clips(current_user: dict = Depends(get_current_user)):
    from database import voice_assets_collection
    org_id = current_user["organization_id"]
    items = await voice_assets_collection.find(
        {"organization_id": org_id}, _VOICE_PROJECTION,
    ).sort("created_at", -1).to_list(CLIPS_MAX_PER_ORG)
    used = sum(i.get("size_bytes") or 0 for i in items)
    return {"items": items, "quota_bytes": ORG_QUOTA_BYTES,
            "used_bytes": used}


@router.post("/voice", status_code=status.HTTP_201_CREATED)
async def record_voice_clip(file: UploadFile = File(...),
                            title: str = Form(...),
                            duration_sec: float = Form(0),
                            current_user: dict = Depends(get_current_user)):
    from database import voice_assets_collection
    org_id = current_user["organization_id"]
    ext = ext_for_mime(file.content_type)
    if not ext:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Formato non riconosciuto: la voce si registra dall'app.")
    duration = max(0.0, float(duration_sec or 0))
    if duration > CLIP_MAX_SECONDS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Spezzone oltre {CLIP_MAX_SECONDS // 60} minuti: "
                   "spezzalo in piu' registrazioni.")
    clean_title = (title or "").strip()[:VOICE_TITLE_MAX] or "Spezzone voce"
    data = await file.read()
    if len(data) > CLIP_MAX_BYTES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Registrazione oltre {CLIP_MAX_BYTES // (1024 * 1024)}MB.")
    existing = await voice_assets_collection.find(
        {"organization_id": org_id}, {"_id": 0, "size_bytes": 1},
    ).to_list(CLIPS_MAX_PER_ORG + 1)
    if len(existing) >= CLIPS_MAX_PER_ORG:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Limite di {CLIPS_MAX_PER_ORG} spezzoni raggiunto: "
                   "elimina quelli che non usi.")
    used = sum(e.get("size_bytes") or 0 for e in existing)
    if used + len(data) > ORG_QUOTA_BYTES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Spazio voce esaurito: elimina spezzoni che non usi.")
    asset_id = str(uuid.uuid4())
    org_dir = VOICE_DIR / org_id
    org_dir.mkdir(parents=True, exist_ok=True)
    (org_dir / f"{asset_id}.{ext}").write_bytes(data)
    asset = {
        "id": asset_id,
        "organization_id": org_id,
        "title": clean_title,
        "duration_sec": round(duration, 1),
        "size_bytes": len(data),
        "mime": (file.content_type or "").split(";")[0],
        "stream_url": f"/uploads/voice/{org_id}/{asset_id}.{ext}",
        "recorded_by": current_user.get("email"),
        "created_at": utc_now(),
    }
    await voice_assets_collection.insert_one(dict(asset))
    asset.pop("_id", None)
    asset.pop("organization_id", None)
    asset.pop("recorded_by", None)
    return asset


class VoiceClipUpdate(BaseModel):
    title: str


@router.patch("/voice/{asset_id}")
async def rename_voice_clip(asset_id: str, payload: VoiceClipUpdate,
                            current_user: dict = Depends(get_current_user)):
    from database import voice_assets_collection
    clean_title = (payload.title or "").strip()[:VOICE_TITLE_MAX]
    if not clean_title:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="Serve un titolo.")
    res = await voice_assets_collection.update_one(
        {"id": asset_id, "organization_id": current_user["organization_id"]},
        {"$set": {"title": clean_title}})
    if not res.matched_count:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="Spezzone non trovato.")
    return {"id": asset_id, "title": clean_title}


@router.delete("/voice/{asset_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_voice_clip(asset_id: str,
                            current_user: dict = Depends(get_current_user)):
    from database import voice_assets_collection
    org_id = current_user["organization_id"]
    asset = await voice_assets_collection.find_one(
        {"id": asset_id, "organization_id": org_id})
    if not asset:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="Spezzone non trovato.")
    await voice_assets_collection.delete_one(
        {"id": asset_id, "organization_id": org_id})
    fname = os.path.basename(asset.get("stream_url") or "")
    if fname:
        try:
            (VOICE_DIR / org_id / fname).unlink(missing_ok=True)
        except OSError:
            logger.warning("file voce %s non rimosso", fname)
