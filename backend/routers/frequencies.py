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
    APIRouter, Depends, File, Form, HTTPException, Query, Request, Response,
    UploadFile, status,
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
# IL MASTER (23/8) — il mix renderizzato ALLA PUBBLICAZIONE dal browser
# dell'operatore: chi ascolta riceve UN file in streaming (~37 MB per
# 27 min) invece di risintetizzare 12 basi (~700 MB di RAM). La
# directory vive nel volume uploads ma NON e' servita staticamente:
# nginx la marca `internal` e la consegna solo via X-Accel-Redirect,
# dopo che il portiere qui sotto ha verificato lo sblocco — un file
# statico pubblico sarebbe il cancello demolito da un'altra porta.
MASTERS_DIR = Path(__file__).resolve().parent.parent / "uploads" / "masters"
MASTER_MAX_BYTES = 64 * 1024 * 1024      # 30 min a 192 kbps ~ 41 MB + margine
MASTER_PASS_TTL_SEC = 6 * 3600
# VP (24/8) — i tre modi della pulizia voce. Il gemello nel client:
# engine/voicefx.js (cleanVoiceBuffer). Assente sul documento = i take
# di prima del 24/8: valgono «pulita», il suono non cambia da solo.
VOICE_CLEAN_MODES = ("naturale", "pulita", "grezza")
# L'ANTEPRIMA (M3, 24/8): i 90 secondi del cancello, come FILE
# pubblico (~2 MB). Prima i non-sbloccati — cioe' CHIUNQUE riceva un
# link condiviso — sintetizzavano l'anteprima col percorso pesante, e
# sul telefono il tab moriva di RAM (founder: «in Safari va in
# errore»). Si RITAGLIA dal master a colpi di byte: i frame MP3 sono
# indipendenti, un taglio netto suona — niente encoder nel server.
ANTEPRIME_DIR = Path(__file__).resolve().parent.parent / "uploads" / "anteprime"
ANTEPRIMA_SEC = 92                       # 90 del cancello + respiro


async def require_sound_composer(
        current_user: dict = Depends(get_current_user)) -> dict:
    """PC1 (24/8, decisione founder) — comporre e' un PRIVILEGIO: non
    tutti gli operatori, solo quelli a cui il system admin lo concede
    (organizations.sound_composer, pagina /admin/sound). Le superfici
    pubbliche (frequenze, tutorial, meditazioni pubblicate, /sounds in
    lettura) non passano di qui: il privilegio governa il COMPORRE,
    non l'esistere di cio' che e' gia' stato composto."""
    from database import organizations_collection
    org = await organizations_collection.find_one(
        {"id": current_user["organization_id"]},
        {"_id": 0, "sound_composer": 1})
    if not (org or {}).get("sound_composer"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="La composizione di Aurya Sound e' su invito: "
                   "scrivici e ne parliamo.")
    return current_user


def _ritaglia_anteprima(master_bytes: bytes) -> bytes:
    # 192 kbps CBR: byte al secondo = 24000. Un margine di 4 KB copre
    # header/tag in testa. Se il master fosse piu' corto, resta tutto.
    quota = 24000 * ANTEPRIMA_SEC + 4096
    return master_bytes[:quota]

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
async def list_tracks(current_user: dict = Depends(require_sound_composer)):
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
                       current_user: dict = Depends(require_sound_composer)):
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
                    current_user: dict = Depends(require_sound_composer)):
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
                       current_user: dict = Depends(require_sound_composer)):
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
                       current_user: dict = Depends(require_sound_composer)):
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
                      "plays_total": 1, "organization_id": 1,
                      "master_file": 1, "master_bytes": 1,
                      "anteprima_url": 1}
_SLUG_ATTEMPTS = 50


async def _unique_track_slug(base: str, escludi_id: str = None) -> str:
    from models.event_occurrence import slugify
    from database import frequency_tracks_collection
    root = slugify(base)[:46] or "sessione"
    candidate = root
    for n in range(2, _SLUG_ATTEMPTS + 2):
        filtro = {"$or": [{"slug": candidate},
                          {"slug_precedenti": candidate}]}
        if escludi_id:
            filtro["id"] = {"$ne": escludi_id}
        clash = await frequency_tracks_collection.find_one(filtro, {"_id": 1})
        if not clash:
            return candidate
        candidate = f"{root}-{n}"
    return f"{root}-{uuid.uuid4().hex[:6]}"


async def _trova_pubblicata(slug: str, projection: dict):
    """La traccia pubblicata per slug — anche coi LINK DI IERI: lo
    slug segue il titolo a ogni pubblicazione (founder, 24/8: la sua
    «Rinascita» era /senza-titolo perche' pubblicata col titolo ancora
    vuoto), ma i vecchi slug restano in slug_precedenti e i link gia'
    condivisi continuano a rispondere."""
    from database import frequency_tracks_collection
    return await frequency_tracks_collection.find_one(
        {"$or": [{"slug": slug}, {"slug_precedenti": slug}],
         "status": "published"}, projection)


@router.post("/tracks/{track_id}/publish")
async def publish_track(track_id: str,
                        current_user: dict = Depends(require_sound_composer)):
    from database import frequency_tracks_collection
    track = await frequency_tracks_collection.find_one(
        {"id": track_id,
         "organization_id": current_user["organization_id"]})
    if not track:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="Traccia non trovata.")
    # lo slug SEGUE IL TITOLO: se il titolo di oggi produce una radice
    # diversa (es. la traccia fu pubblicata da «Senza titolo»), se ne
    # genera uno nuovo e il vecchio scende in slug_precedenti — i link
    # gia' in giro non muoiono. La deduplica (-2, -3…) ignora se stessa.
    from models.event_occurrence import slugify
    slug = track.get("slug")
    root = slugify(track["title"])[:46] or "sessione"
    precedenti = list(track.get("slug_precedenti") or [])
    if not slug or not (slug == root or slug.startswith(root + "-")):
        if slug:
            precedenti = list(dict.fromkeys(precedenti + [slug]))
        slug = await _unique_track_slug(track["title"], escludi_id=track_id)
    # ES4 (21/8) — i numeri da vetrina si MATERIALIZZANO qui, una volta:
    # prima il catalogo trasportava l'intero array dei livelli di ogni
    # traccia solo per contarli. Si paga alla pubblicazione (rara), non
    # a ogni apertura della vetrina.
    score = track.get("score") or {}
    await frequency_tracks_collection.update_one(
        {"id": track_id,
         "organization_id": current_user["organization_id"]},
        {"$set": {"status": "published", "slug": slug,
                  "slug_precedenti": precedenti,
                  "published_at": utc_now(), "updated_at": utc_now(),
                  "layers_count": len(score.get("layers") or []),
                  "duration_sec": score.get("duration_sec")}})
    return {"id": track_id, "status": "published", "slug": slug}


@router.post("/tracks/{track_id}/master")
async def upload_master(track_id: str,
                        file: UploadFile = File(...),
                        current_user: dict = Depends(require_sound_composer)):
    """Riceve il master renderizzato dal client dell'operatore.
    Nome content-addressed ({id}.{epoch}.mp3): il re-publish carica un
    file nuovo e spazza i precedenti — un master per traccia, mai
    orfani. Il server non renderizza mai (zero CPU): custodisce."""
    from database import frequency_tracks_collection
    track = await frequency_tracks_collection.find_one(
        {"id": track_id,
         "organization_id": current_user["organization_id"]},
        {"_id": 0, "id": 1})
    if not track:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="Traccia non trovata.")
    data = await file.read()
    if len(data) > MASTER_MAX_BYTES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Master oltre {MASTER_MAX_BYTES // (1024 * 1024)}MB.")
    if len(data) < 100_000:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="Master sospettosamente piccolo.")
    MASTERS_DIR.mkdir(parents=True, exist_ok=True)
    ANTEPRIME_DIR.mkdir(parents=True, exist_ok=True)
    import time as _time
    epoca = int(_time.time())
    nome = f"{track_id}.{epoca}.mp3"
    (MASTERS_DIR / nome).write_bytes(data)
    # l'anteprima nasce dal master, qui, senza encoder: taglio di byte
    nome_ant = f"{track_id}.{epoca}.mp3"
    (ANTEPRIME_DIR / nome_ant).write_bytes(_ritaglia_anteprima(data))
    for vecchio in MASTERS_DIR.glob(f"{track_id}.*.mp3"):
        if vecchio.name != nome:
            vecchio.unlink(missing_ok=True)
    for vecchio in ANTEPRIME_DIR.glob(f"{track_id}.*.mp3"):
        if vecchio.name != nome_ant:
            vecchio.unlink(missing_ok=True)
    await frequency_tracks_collection.update_one(
        {"id": track_id,
         "organization_id": current_user["organization_id"]},
        {"$set": {"master_file": nome, "master_bytes": len(data),
                  "anteprima_url": f"/uploads/anteprime/{nome_ant}",
                  "master_at": utc_now(), "updated_at": utc_now()}})
    return {"id": track_id, "master_bytes": len(data)}


def _firma_master_pass(slug: str) -> str:
    """Pass effimero per l'<audio>: un elemento non sa mandare header,
    e mettere la prova del cerchio in query la regalerebbe ai log. Il
    pass e' scoped alla traccia e muore in ore."""
    import time as _time
    import jwt as _jwt
    return _jwt.encode(
        {"scope": "fqz_master", "slug": slug,
         "exp": int(_time.time()) + MASTER_PASS_TTL_SEC},
        os.environ["JWT_SECRET_KEY"], algorithm="HS256")


def _verifica_master_pass(token: str, slug: str) -> bool:
    try:
        import jwt as _jwt
        payload = _jwt.decode(token, os.environ["JWT_SECRET_KEY"],
                              algorithms=["HS256"])
        return (payload.get("scope") == "fqz_master"
                and payload.get("slug") == slug)
    except Exception:
        return False


@router.get("/public/{slug}/master-pass")
async def master_pass(slug: str, request: Request):
    """Il portiere di giorno: la prova del cerchio (header) si scambia
    con un pass che l'<audio> puo' portare in query."""
    if not await _has_catalog_access(request):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                            detail="Serve lo sblocco del cerchio.")
    track = await _trova_pubblicata(slug, {"_id": 0, "master_file": 1})
    if not track or not track.get("master_file"):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="Master non disponibile.")
    return {"pass": _firma_master_pass(slug)}


@router.get("/public/{slug}/master")
async def serve_master(slug: str, request: Request,
                       secondo: Optional[str] = Query(default=None, alias="pass")):
    """Il portiere di notte: verifica il pass (o lo sblocco diretto) e
    consegna via X-Accel-Redirect — nginx serve i byte (sendfile,
    Range nativo per il seek), il backend non li tocca mai. In dev,
    senza nginx davanti, ripiega su FileResponse."""
    if not (secondo and _verifica_master_pass(secondo, slug)):
        if not await _has_catalog_access(request):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                                detail="Serve lo sblocco del cerchio.")
    track = await _trova_pubblicata(slug, {"_id": 0, "master_file": 1})
    nome = (track or {}).get("master_file")
    if not nome or "/" in nome or ".." in nome:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="Master non disponibile.")
    if os.environ.get("ENVIRONMENT", "development").lower() == "production":
        return Response(status_code=200, headers={
            "X-Accel-Redirect": f"/uploads/masters/{nome}",
            "Content-Type": "audio/mpeg",
            "Cache-Control": "private, max-age=3600",
        })
    from fastapi.responses import FileResponse
    percorso = MASTERS_DIR / nome
    if not percorso.exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="File master assente.")
    return FileResponse(percorso, media_type="audio/mpeg")


@router.post("/tracks/{track_id}/unpublish")
async def unpublish_track(track_id: str,
                          current_user: dict = Depends(require_sound_composer)):
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
    track = await _trova_pubblicata(slug, _PUBLIC_PROJECTION)
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
    # IL MASTER: il player lo preferisce; senza, percorso synth di sempre
    track["master_pronto"] = bool(track.pop("master_file", None))
    # l'anteprima pubblica dei 90s viaggia nel payload (e' statica)
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
            {"_id": 0, "id": 1, "stream_url": 1, "tappeto_url": 1, "duration_sec": 1},
        ).to_list(len(voice_ids))
        track["voice_assets"] = clips
    return track


@router.post("/public/{slug}/play", status_code=status.HTTP_204_NO_CONTENT)
async def register_play(slug: str):
    from database import frequency_tracks_collection
    await frequency_tracks_collection.update_one(
        {"$or": [{"slug": slug}, {"slug_precedenti": slug}],
         "status": "published"},
        {"$inc": {"plays_total": 1}})


# ── FQ3 — vetrina /meditazioni: catalogo DIETRO il cancello ────────────────
# La vetrina e' l'incentivo (decisione founder 18/8): senza sblocco il
# catalogo NON si vede. Lo sblocco e' verificato SERVER-SIDE, senza
# toccare i sistemi consolidati:
#   - iscritto Lettera → la PROVA UNICA del cerchio (SB1, 20/8): il JWT
#     `newsletter_subscriber` di core.subscriber_token — lo stesso che
#     sblocca le guide del Magazine. Prima qui viveva un token HMAC
#     separato, e sbloccare le guide lasciava chiuse le meditazioni (e
#     viceversa): due prove per lo stesso diritto. L'email nel JWT viene
#     comunque RIVERIFICATA contro gli iscritti confermati a ogni
#     richiesta, come faceva l'HMAC.
#   - account Aurya → Bearer platform gia' esistente (P1).
# I preferiti vivono in una collection dedicata (frequency_favorites),
# agganciata all'account per id: zero campi nuovi su platform_accounts.


async def _subscriber_ok(email: str) -> bool:
    """NL-septies (20/8, founder) — serve l'iscrizione CONFERMATA.

    Prima bastava `status != unsubscribed`, cioe' anche un'iscrizione
    mai confermata: chiunque digitasse un indirizzo qualsiasi apriva le
    meditazioni al primo colpo, mentre le guide del Magazine
    pretendevano il clic nell'email. Due cancelli con due regole, e il
    piu' debole rendeva decorativo il doppio opt-in. Ora la regola e'
    una sola su tutti i contenuti riservati: il clic prova che quella
    casella e' tua.
    """
    from database import db
    doc = await db.aurya_subscribers.find_one(
        {"email": email.lower().strip()}, {"_id": 0, "status": 1, "consent": 1})
    return bool(doc and doc.get("consent")
                and doc.get("status") == "confirmed")


class UnlockPayload(BaseModel):
    email: str


@router.post("/catalog/unlock")
async def catalog_unlock(payload: UnlockPayload):
    """SB1 — sblocco per iscritti Lettera: l'email deve risultare
    CONFERMATA. Ritorna la prova unica del cerchio (lo stesso JWT di
    /public/newsletter/unlock): un lucchetto da vetrina, non una
    sessione — si revoca solo disiscrivendosi, perche' l'email viene
    riverificata a ogni richiesta."""
    email = payload.email.lower().strip()
    if not await _subscriber_ok(email):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Questa email non risulta iscritta alla Lettera.")
    from core.subscriber_token import generate_subscriber_token
    return {"email": email, "token": generate_subscriber_token(email)}


async def _has_catalog_access(request) -> bool:
    """Vero se la richiesta porta uno sblocco valido: header
    X-Fqz-Unlock con la prova unica (JWT newsletter_subscriber,
    ri-verificato contro gli iscritti confermati) oppure un Bearer
    platform valido."""
    unlock = request.headers.get("X-Fqz-Unlock", "")
    if unlock:
        try:
            from core.subscriber_token import decode_subscriber_token
            email = decode_subscriber_token(unlock)["email"]
            if email and await _subscriber_ok(email):
                return True
        except Exception:  # scaduto, contraffatto o vecchio HMAC: chiuso
            pass
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        try:
            from auth import decode_token
            payload = decode_token(auth_header[7:])
            # platform (account Aurya) O operatore loggato: un account
            # e' PIU' del cerchio — e il client attacca il Bearer org a
            # ogni chiamata (24/8: l'operatore che ascoltava la SUA
            # meditazione prendeva 401 e il client lo sbatteva al login)
            if payload.get("sub") and (payload.get("type") == "platform"
                                       or payload.get("org_id")):
                return True
        except Exception:  # token scaduto o estraneo: non sblocca
            pass
    return False


# ES4 — niente `score.layers` nella proiezione: i numeri da vetrina
# sono materializzati alla pubblicazione (con fallback sul solo
# duration_sec dello score per le tracce pubblicate prima).
_CATALOG_PROJECTION = {"_id": 0, "slug": 1, "title": 1, "description": 1,
                       "intent": 1, "plays_total": 1, "organization_id": 1,
                       "score.duration_sec": 1, "layers_count": 1,
                       "duration_sec": 1, "published_at": 1}

CATALOG_PAGE_MAX = 100


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
    # ES4 — paginazione a cursore: prima era `to_list(500)`, che alla
    # traccia numero 501 avrebbe fatto SPARIRE le piu' vecchie dalla
    # vetrina senza che nessuno se ne accorgesse. Il cursore e'
    # `published_at` (l'ordine della vetrina): `?before=` riprende da
    # dove l'ultima pagina e' finita.
    try:
        limit = min(CATALOG_PAGE_MAX, max(1, int(
            request.query_params.get("limit", CATALOG_PAGE_MAX))))
    except ValueError:
        limit = CATALOG_PAGE_MAX
    filtro = {"status": "published"}
    before = request.query_params.get("before")
    if before:
        # published_at in Mongo e' un datetime: la stringa ISO del
        # client va riportata a datetime, o il $lt confronterebbe tipi
        # BSON diversi e non troverebbe MAI niente (vetrina vuota a
        # pagina due, senza errori).
        from datetime import datetime
        try:
            filtro["published_at"] = {
                "$lt": datetime.fromisoformat(before.replace("Z", "+00:00"))}
        except ValueError:
            pass   # cursore malformato: prima pagina, non un errore
    items = await frequency_tracks_collection.find(
        filtro, _CATALOG_PROJECTION,
    ).sort("published_at", -1).to_list(limit)
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
        # materializzati alla pubblicazione; il fallback copre le
        # tracce pubblicate prima di ES4
        it["duration_sec"] = it.get("duration_sec") or score.get("duration_sec")
        it["layers_count"] = it.get("layers_count") or 0
        it["operator"] = {
            "name": profile.get("display_name") or org.get("name"),
            "slug": org.get("public_slug"),
        }
        it["plays_total"] = it.get("plays_total") or 0
        out.append(it)
    # il cursore per la pagina dopo: assente = la vetrina e' finita
    next_before = out[-1]["published_at"] if len(out) == limit else None
    return {"items": out, "next_before": next_before}


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
                     "duration_sec": 1, "size_bytes": 1, "stream_url": 1, "tappeto_url": 1}


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
    # NOTA TAPPETI (23/8): una base oltre i ~4 minuti merita il suo
    # {nome}.tappeto.m4a (scripts/prepara_tappeti.py, gira sul mac) —
    # senza, su iPhone l'anello ripiega sul file intero. La fabbrica
    # e' idempotente: si rilancia dopo gli upload e si ricarica.
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
    ORG_QUOTA_BYTES, clamp_trim, ext_for_mime,
)
from models.voice_asset import TITLE_MAX as VOICE_TITLE_MAX  # noqa: E402

VOICE_DIR = Path(__file__).resolve().parent.parent / "uploads" / "voice"

_VOICE_PROJECTION = {"_id": 0, "id": 1, "title": 1, "duration_sec": 1,
                     "size_bytes": 1, "stream_url": 1, "tappeto_url": 1, "created_at": 1,
                     "trim_start": 1, "trim_end": 1, "clean_mode": 1}


@router.get("/voice")
async def list_voice_clips(current_user: dict = Depends(require_sound_composer)):
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
                            current_user: dict = Depends(require_sound_composer)):
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
        # FV6 — nasce intera: il taglio si decide dopo, sullo spezzone
        "trim_start": 0.0,
        "trim_end": 0.0,
        # VP (24/8, founder: «la voce inizia bassa e poi si alza») —
        # era il GATE anti-fruscio della pulizia: un attacco morbido
        # finiva sotto soglia e usciva a -18dB, poi risaliva. Ora
        # l'autore sceglie: i take NUOVI nascono «naturale» (volume e
        # bordi, nessun gate); i take gia' esistenti, senza campo,
        # valgono «pulita» — cioe' suonano ESATTAMENTE come oggi.
        "clean_mode": "naturale",
    }
    await voice_assets_collection.insert_one(dict(asset))
    asset.pop("_id", None)
    asset.pop("organization_id", None)
    asset.pop("recorded_by", None)
    return asset


class VoiceClipUpdate(BaseModel):
    """Titolo e/o taglio dello spezzone. Ogni campo e' facoltativo:
    si rinomina senza toccare il taglio e si taglia senza rinominare."""
    title: Optional[str] = None
    trim_start: Optional[float] = None
    trim_end: Optional[float] = None
    clean_mode: Optional[str] = None       # naturale | pulita | grezza


@router.patch("/voice/{asset_id}")
async def update_voice_clip(asset_id: str, payload: VoiceClipUpdate,
                            current_user: dict = Depends(require_sound_composer)):
    from database import voice_assets_collection
    asset = await voice_assets_collection.find_one(
        {"id": asset_id, "organization_id": current_user["organization_id"]},
        _VOICE_PROJECTION)
    if not asset:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="Spezzone non trovato.")
    changes = {}
    if payload.title is not None:
        clean_title = (payload.title or "").strip()[:VOICE_TITLE_MAX]
        if not clean_title:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                                detail="Serve un titolo.")
        changes["title"] = clean_title
    if payload.trim_start is not None or payload.trim_end is not None:
        start, end = clamp_trim(
            payload.trim_start if payload.trim_start is not None
            else asset.get("trim_start"),
            payload.trim_end if payload.trim_end is not None
            else asset.get("trim_end"),
            asset.get("duration_sec"))
        changes["trim_start"] = start
        changes["trim_end"] = end
    if payload.clean_mode is not None:
        if payload.clean_mode not in VOICE_CLEAN_MODES:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                                detail="Modo di pulizia sconosciuto.")
        changes["clean_mode"] = payload.clean_mode
    if changes:
        await voice_assets_collection.update_one(
            {"id": asset_id,
             "organization_id": current_user["organization_id"]},
            {"$set": changes})
    return {**{k: asset.get(k) for k in ("id", "title", "duration_sec")},
            "trim_start": changes.get("trim_start", asset.get("trim_start") or 0),
            "trim_end": changes.get("trim_end", asset.get("trim_end") or 0),
            **({"title": changes["title"]} if "title" in changes else {})}


@router.delete("/voice/{asset_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_voice_clip(asset_id: str,
                            current_user: dict = Depends(require_sound_composer)):
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
