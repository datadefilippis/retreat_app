"""
/api/accademia — L'OPERATORE crea i suoi corsi online (AC1, 7/10/2026).
Piano: docs/PIANO_ACCADEMIA_2026-10-06.md §4 e §7.

Tre gesti: il corso (titolo, due righe, prezzo, copertina, durata
dell'accesso) → le lezioni (video caricato dal browser sulla libreria
GESTITA da Aurya, oppure testo; moduli facoltativi; anteprime) → pubblica
(lucchetti in chiaro). Il prodotto gemello `item_type=course` nasce con il
corso (riusa `_ensure_linked_product` del legacy) e porta prezzo e
pubblicazione: fonte unica, come per i prodotti.

Isolamento: tutto dietro require_module("accademia") (+ interruttore
`accademia_spento`); i modelli Course/Module/Lesson sono quelli del
legacy (additivi: tipo, testo, video); il legacy /api/courses resta com'e'.

Sicurezza: la chiave API Bunny non lascia mai il server (il browser riceve
una firma TUS a scadenza); quota video per piano controllata PRIMA di
creare il video; ogni rotta e' scoped sull'org dell'utente.
"""
from __future__ import annotations

import logging
import os
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from pydantic import BaseModel, ConfigDict, Field

from auth import get_verified_user_strict as get_verified_user
from services.module_access import require_module

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/accademia", tags=["Accademia"])
_gate = require_module("accademia")

ETICHETTE_ACCESSO = {"lifetime": "Per sempre", "expiring": "A tempo"}
STATI_VIDEO_PRONTI = ("pronto",)
MODULO_DEFAULT = "Lezioni"
MAX_VIDEO_BYTES = 5 * 1024 ** 3


# ── modelli di ingresso ──────────────────────────────────────────────────

class CorsoCreate(BaseModel):
    model_config = ConfigDict(extra="ignore")
    title: str = Field(min_length=1, max_length=255)
    description: Optional[str] = Field(default=None, max_length=2000)
    long_description: Optional[str] = Field(default=None, max_length=20000)
    instructor_name: Optional[str] = Field(default=None, max_length=255)
    unit_price: Optional[float] = Field(default=None, ge=0)
    access_policy: str = Field(default="lifetime", pattern="^(lifetime|expiring)$")
    access_expiry_days: Optional[int] = Field(default=None, ge=1, le=3650)


class CorsoUpdate(BaseModel):
    model_config = ConfigDict(extra="ignore")
    title: Optional[str] = Field(default=None, min_length=1, max_length=255)
    description: Optional[str] = Field(default=None, max_length=2000)
    long_description: Optional[str] = Field(default=None, max_length=20000)
    instructor_name: Optional[str] = Field(default=None, max_length=255)
    instructor_bio: Optional[str] = Field(default=None, max_length=4000)
    unit_price: Optional[float] = Field(default=None, ge=0)
    access_policy: Optional[str] = Field(default=None, pattern="^(lifetime|expiring)$")
    access_expiry_days: Optional[int] = Field(default=None, ge=0, le=3650)   # 0 = via


class ModuloBody(BaseModel):
    model_config = ConfigDict(extra="ignore")
    title: str = Field(min_length=1, max_length=255)
    description: Optional[str] = Field(default=None, max_length=2000)


class LezioneCreate(BaseModel):
    model_config = ConfigDict(extra="ignore")
    title: str = Field(min_length=1, max_length=255)
    description: Optional[str] = Field(default=None, max_length=2000)
    tipo: str = Field(default="video", pattern="^(video|testo)$")
    testo: Optional[str] = Field(default=None, max_length=20000)
    module_id: Optional[str] = None
    is_preview: bool = False


class LezioneUpdate(BaseModel):
    model_config = ConfigDict(extra="ignore")
    title: Optional[str] = Field(default=None, min_length=1, max_length=255)
    description: Optional[str] = Field(default=None, max_length=2000)
    tipo: Optional[str] = Field(default=None, pattern="^(video|testo)$")
    testo: Optional[str] = Field(default=None, max_length=20000)
    module_id: Optional[str] = None
    is_preview: Optional[bool] = None


class OrdineBody(BaseModel):
    """L'ordine nuovo: i moduli nell'ordine voluto, ognuno con le sue lezioni."""
    model_config = ConfigDict(extra="ignore")
    moduli: List[Dict[str, Any]]


class VideoBody(BaseModel):
    model_config = ConfigDict(extra="ignore")
    filename: str = Field(min_length=1, max_length=255)
    size_bytes: int = Field(ge=1, le=MAX_VIDEO_BYTES)


class RevocaBody(BaseModel):
    model_config = ConfigDict(extra="ignore")
    motivo: str = Field(min_length=2, max_length=500)


# ── helpers ──────────────────────────────────────────────────────────────

def _slugify(titolo: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", (titolo or "").lower()).strip("-")
    return (s or "corso")[:100]


async def _slug_libero(org_id: str, base: str) -> str:
    from repositories.course_repository import check_slug_available
    slug = base
    n = 2
    while not await check_slug_available(org_id, slug):
        slug = f"{base}-{n}"[:120]
        n += 1
    return slug


async def _mio_corso(course_id: str, org_id: str) -> dict:
    from database import courses_collection
    doc = await courses_collection.find_one(
        {"id": course_id, "organization_id": org_id, "is_active": {"$ne": False}}, {"_id": 0})
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Corso non trovato")
    return doc


async def _prodotto_di(course_doc: dict, org_id: str) -> dict:
    """Il prodotto gemello (fonte di prezzo e pubblicazione), creato se manca."""
    from routers.courses import _ensure_linked_product
    from models.course import Course
    return await _ensure_linked_product(org_id, Course(**course_doc))


async def _limiti(org_id: str) -> Dict[str, Any]:
    from services.module_access import get_module_entitlements
    ent = await get_module_entitlements(org_id, "accademia")
    lim = (ent or {}).get("limits") or {}
    return {"corsi_max": lim.get("corsi_max"), "lezioni_max": lim.get("lezioni_max"), "video_gb": lim.get("video_gb")}


async def _quota_video(org_id: str) -> Dict[str, Any]:
    from database import organizations_collection
    from services.bunny import gestito
    org = await organizations_collection.find_one({"id": org_id}, {"_id": 0, "integrations": 1})
    lib = gestito.libreria_gestita_di(org)
    usati = int(((lib or {}).get("quota") or {}).get("video_bytes") or 0)
    lim = await _limiti(org_id)
    max_gb = lim.get("video_gb")
    return {"usati_bytes": usati, "usati_gb": gestito.gb(usati), "max_gb": max_gb,
            "max_bytes": int(max_gb * 1024 ** 3) if max_gb else None}


def _lezioni(course_doc: dict) -> List[dict]:
    return [l for m in (course_doc.get("modules") or []) for l in (m.get("lessons") or [])]


def _lezione_pronta(l: dict) -> bool:
    if l.get("tipo") == "testo":
        return bool((l.get("testo") or "").strip())
    v = l.get("video") or {}
    return v.get("stato") in STATI_VIDEO_PRONTI or bool(l.get("bunny_video_guid") and not v)


def _ragioni_pubblicazione(course_doc: dict, prodotto: dict, pre: Dict[str, Any]) -> List[str]:
    ragioni: List[str] = []
    if not pre.get("stripe_pronto"):
        ragioni.append("Collega gli incassi con Stripe: i corsi si pagano subito, online.")
    if not pre.get("patto"):
        ragioni.append("Accetta il patto di responsabilità (Impostazioni → Condizioni dell'operatore).")
    if not pre.get("pagina_pubblica"):
        ragioni.append("La tua pagina pubblica non è ancora online.")
    if float((prodotto or {}).get("unit_price") or 0) <= 0:
        ragioni.append("Metti un prezzo maggiore di zero.")
    lezioni = _lezioni(course_doc)
    pronte = [l for l in lezioni if _lezione_pronta(l)]
    if not pronte:
        ragioni.append("Serve almeno una lezione pronta (un video codificato o un testo).")
    in_corso = [l for l in lezioni if l.get("tipo", "video") == "video" and (l.get("video") or {}).get("stato") in ("caricamento", "codifica")]
    if in_corso:
        ragioni.append(f"{len(in_corso)} lezion{'e' if len(in_corso) == 1 else 'i'} con il video ancora in lavorazione: aspetta che sia pronto o toglilo.")
    errori = [l for l in lezioni if (l.get("video") or {}).get("stato") == "errore"]
    if errori:
        ragioni.append(f"{len(errori)} lezion{'e' if len(errori) == 1 else 'i'} con un video in errore: ricaricalo.")
    vuote = [l for l in lezioni if not _lezione_pronta(l) and not (l.get("video") or {}).get("stato")]
    if vuote:
        ragioni.append(f"{len(vuote)} lezion{'e' if len(vuote) == 1 else 'i'} senza contenuto: carica il video, scrivi il testo o toglila.")
    return ragioni


def _riga_lezione(l: dict) -> dict:
    v = l.get("video") or {}
    return {
        "id": l["id"], "order": l.get("order", 0), "title": l.get("title"), "description": l.get("description"),
        "tipo": l.get("tipo") or ("video" if (v or l.get("bunny_video_guid")) else "testo"),
        "testo": l.get("testo"), "is_preview": bool(l.get("is_preview")),
        "duration_seconds": int(l.get("duration_seconds") or v.get("duration_seconds") or 0),
        "pronta": _lezione_pronta(l),
        "video": ({"guid": v.get("guid"), "stato": v.get("stato"), "size_bytes": v.get("size_bytes"),
                   "thumbnail_url": v.get("thumbnail_url"), "duration_seconds": v.get("duration_seconds"),
                   "uploaded_at": v.get("uploaded_at")} if v else None),
        "resources": l.get("resources") or [],
    }


async def _riga(course_doc: dict, prodotto: dict, pre: Dict[str, Any], studenti: int, public_slug: Optional[str]) -> dict:
    lezioni = _lezioni(course_doc)
    from services.bunny import gestito
    return {
        "id": course_doc["id"], "title": course_doc.get("title"), "slug": course_doc.get("slug"),
        "description": course_doc.get("description"), "long_description": course_doc.get("long_description"),
        "cover_image_url": course_doc.get("cover_image_url"),
        "instructor_name": course_doc.get("instructor_name"), "instructor_bio": course_doc.get("instructor_bio"),
        "access_policy": course_doc.get("access_policy") or "lifetime",
        "access_expiry_days": course_doc.get("access_expiry_days"),
        "access_etichetta": ETICHETTE_ACCESSO.get(course_doc.get("access_policy") or "lifetime"),
        "product_id": prodotto.get("id"), "unit_price": prodotto.get("unit_price"),
        "is_published": bool(prodotto.get("is_published")),
        "lezioni_count": len(lezioni), "lezioni_pronte": sum(1 for l in lezioni if _lezione_pronta(l)),
        "durata_totale_seconds": sum(int(l.get("duration_seconds") or 0) for l in lezioni),
        "moduli": [{"id": m["id"], "order": m.get("order", 0), "title": m.get("title"), "description": m.get("description"),
                    "lezioni": [_riga_lezione(l) for l in sorted(m.get("lessons") or [], key=lambda x: x.get("order", 0))]}
                   for m in sorted(course_doc.get("modules") or [], key=lambda x: x.get("order", 0))],
        "studenti": studenti,
        "ragioni_pubblicazione": _ragioni_pubblicazione(course_doc, prodotto, pre),
        "public_slug": public_slug,
        "bunny_attivo": gestito.attivo(),
        "created_at": course_doc.get("created_at"), "updated_at": course_doc.get("updated_at"),
    }


async def _studenti_per_corso(org_id: str, course_ids: List[str]) -> Dict[str, int]:
    from database import issued_course_accesses_collection
    out: Dict[str, int] = {}
    if not course_ids:
        return out
    async for r in issued_course_accesses_collection.aggregate([
            {"$match": {"organization_id": org_id, "course_id": {"$in": course_ids}, "revoked_at": None}},
            {"$group": {"_id": "$course_id", "n": {"$sum": 1}}}]):
        out[r["_id"]] = int(r["n"])
    return out


async def _commissione_corsi(org_id: str) -> Dict[str, Any]:
    """La percentuale sui corsi dal piano dell'org (fee per riga, chiave course)."""
    from database import organizations_collection
    from services.fee_per_riga import mappa_fee_org
    org = await organizations_collection.find_one({"id": org_id}, {"_id": 0, "commercial_plan_slug": 1, "application_fee_by_type": 1})
    mappa = await mappa_fee_org(org)
    return {"course": float(mappa.get("course") or 0), "piano": (org or {}).get("commercial_plan_slug")}


async def _public_slug(org_id: str) -> Optional[str]:
    from database import organizations_collection
    org = await organizations_collection.find_one({"id": org_id}, {"_id": 0, "public_slug": 1})
    return (org or {}).get("public_slug")


def _trova_lezione(course_doc: dict, lesson_id: str):
    for m in course_doc.get("modules") or []:
        for l in m.get("lessons") or []:
            if l.get("id") == lesson_id:
                return m, l
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lezione non trovata")


async def _salva_moduli(course_doc: dict, org_id: str) -> dict:
    from repositories.course_repository import update_modules
    # ri-numera: 0..N-1 per modulo e per lezione
    for i, m in enumerate(sorted(course_doc.get("modules") or [], key=lambda x: x.get("order", 0))):
        m["order"] = i
        for j, l in enumerate(sorted(m.get("lessons") or [], key=lambda x: x.get("order", 0))):
            l["order"] = j
        m["lessons"] = sorted(m.get("lessons") or [], key=lambda x: x["order"])
    course_doc["modules"] = sorted(course_doc.get("modules") or [], key=lambda x: x["order"])
    await update_modules(course_doc["id"], org_id, course_doc["modules"])
    return await _mio_corso(course_doc["id"], org_id)


async def _risposta(course_doc: dict, org_id: str) -> dict:
    from routers.prodotti import _prerequisiti
    pre = await _prerequisiti(org_id)
    prodotto = await _prodotto_di(course_doc, org_id)
    studenti = await _studenti_per_corso(org_id, [course_doc["id"]])
    return await _riga(course_doc, prodotto, pre, studenti.get(course_doc["id"], 0), pre.get("public_slug"))


# ── il corso ─────────────────────────────────────────────────────────────

@router.get("")
async def lista_corsi(current_user: dict = Depends(get_verified_user), _=Depends(_gate)):
    from database import courses_collection, products_collection
    from routers.prodotti import _prerequisiti, _commissione
    from services.bunny import gestito
    org_id = current_user["organization_id"]
    corsi = await courses_collection.find(
        {"organization_id": org_id, "is_active": {"$ne": False}}, {"_id": 0}).sort("created_at", -1).to_list(500)
    pre = await _prerequisiti(org_id)
    prodotti = {p["metadata"]["course_id"]: p async for p in products_collection.find(
        {"organization_id": org_id, "item_type": "course", "is_active": {"$ne": False},
         "metadata.course_id": {"$in": [c["id"] for c in corsi]}}, {"_id": 0})}
    studenti = await _studenti_per_corso(org_id, [c["id"] for c in corsi])
    righe = []
    for c in corsi:
        prodotto = prodotti.get(c["id"]) or await _prodotto_di(c, org_id)
        righe.append(await _riga(c, prodotto, pre, studenti.get(c["id"], 0), pre.get("public_slug")))
    return {
        "corsi": righe, "total": len(righe),
        "prerequisiti": pre, "public_slug": pre.get("public_slug"),
        "limiti": await _limiti(org_id),
        "quota_video": await _quota_video(org_id),
        "commissione": await _commissione_corsi(org_id),
        "bunny_attivo": gestito.attivo(),
    }


@router.post("", status_code=status.HTTP_201_CREATED)
async def crea_corso(body: CorsoCreate, current_user: dict = Depends(get_verified_user), _=Depends(_gate)):
    from database import courses_collection, products_collection
    from services.dpa_guard import require_dpa_acknowledged
    from services.module_access import enforce_count_quota
    from repositories.course_repository import create
    from models.course import CourseCreate
    from models.common import generate_id
    org_id = current_user["organization_id"]
    await require_dpa_acknowledged(org_id)
    n = await courses_collection.count_documents({"organization_id": org_id, "is_active": {"$ne": False}})
    await enforce_count_quota(org_id, "accademia", "corsi_max", current_count=n,
                              message_template="Hai raggiunto il limite di {limit} corsi del tuo piano.",
                              hard_abuse_cap=1000)
    slug = await _slug_libero(org_id, _slugify(body.title))
    if body.access_policy == "expiring" and not body.access_expiry_days:
        raise HTTPException(status_code=400, detail="Con l'accesso a tempo serve il numero di giorni.")
    dati = CourseCreate(
        title=body.title.strip(), slug=slug, description=(body.description or None),
        long_description=(body.long_description or None), instructor_name=(body.instructor_name or None),
        access_policy=body.access_policy,
        access_expiry_days=body.access_expiry_days if body.access_policy == "expiring" else None,
    )
    corso = await create(org_id, dati)
    # il modulo di default: l'operatore non deve pensare ai moduli se non vuole
    now = datetime.now(timezone.utc).isoformat()
    await courses_collection.update_one(
        {"id": corso.id, "organization_id": org_id},
        {"$set": {"modules": [{"id": generate_id(), "order": 0, "title": MODULO_DEFAULT, "description": None, "lessons": []}],
                  "updated_at": now}})
    doc = await _mio_corso(corso.id, org_id)
    prodotto = await _prodotto_di(doc, org_id)
    if body.unit_price is not None:
        await products_collection.update_one({"id": prodotto["id"], "organization_id": org_id},
                                             {"$set": {"unit_price": float(body.unit_price), "updated_at": now}})
    return await _risposta(doc, org_id)


@router.get("/{course_id}")
async def un_corso(course_id: str, current_user: dict = Depends(get_verified_user), _=Depends(_gate)):
    org_id = current_user["organization_id"]
    return await _risposta(await _mio_corso(course_id, org_id), org_id)


@router.patch("/{course_id}")
async def modifica_corso(course_id: str, body: CorsoUpdate, current_user: dict = Depends(get_verified_user),
                         _=Depends(_gate)):
    from database import products_collection
    from repositories.course_repository import update
    org_id = current_user["organization_id"]
    doc = await _mio_corso(course_id, org_id)
    upd: Dict[str, Any] = {}
    for k in ("title", "description", "long_description", "instructor_name", "instructor_bio", "access_policy"):
        v = getattr(body, k)
        if v is not None:
            upd[k] = v.strip() if isinstance(v, str) and k == "title" else v
    if body.access_expiry_days is not None:
        upd["access_expiry_days"] = body.access_expiry_days or None
    if (upd.get("access_policy") or doc.get("access_policy")) == "expiring" and not (
            upd.get("access_expiry_days") if "access_expiry_days" in upd else doc.get("access_expiry_days")):
        raise HTTPException(status_code=400, detail="Con l'accesso a tempo serve il numero di giorni.")
    if upd:
        await update(course_id, org_id, upd)
    prodotto = await _prodotto_di(doc, org_id)
    pupd: Dict[str, Any] = {"updated_at": datetime.now(timezone.utc).isoformat()}
    if "title" in upd:
        pupd["name"] = upd["title"]
    if "description" in upd:
        pupd["description"] = upd["description"]
    if "long_description" in upd:
        pupd["metadata.long_description"] = upd["long_description"]
    if body.unit_price is not None:
        pupd["unit_price"] = float(body.unit_price)
    await products_collection.update_one({"id": prodotto["id"], "organization_id": org_id}, {"$set": pupd})
    return await _risposta(await _mio_corso(course_id, org_id), org_id)


@router.post("/{course_id}/copertina")
async def copertina(course_id: str, file: UploadFile = File(...), current_user: dict = Depends(get_verified_user),
                    _=Depends(_gate)):
    from database import products_collection
    from repositories.course_repository import update
    from services.object_storage import content_type_for_ext, save_public_upload
    org_id = current_user["organization_id"]
    doc = await _mio_corso(course_id, org_id)
    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext not in (".jpg", ".jpeg", ".png", ".webp", ".heic", ".heif"):
        raise HTTPException(status_code=400, detail="Formato non supportato: usa JPG, PNG o WebP.")
    contents = await file.read()
    if len(contents) > 5 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="Immagine troppo grande: massimo 5 MB.")
    url = save_public_upload("courses", f"{course_id}{ext}", contents, content_type=content_type_for_ext(ext))
    await update(course_id, org_id, {"cover_image_url": url})
    prodotto = await _prodotto_di(doc, org_id)
    await products_collection.update_one({"id": prodotto["id"], "organization_id": org_id},
                                         {"$set": {"image_url": url, "metadata.cover_image_url": url}})
    return {"cover_image_url": url}


@router.post("/{course_id}/pubblica")
async def pubblica(course_id: str, current_user: dict = Depends(get_verified_user), _=Depends(_gate)):
    from database import products_collection
    from routers.prodotti import _prerequisiti
    org_id = current_user["organization_id"]
    doc = await _mio_corso(course_id, org_id)
    prodotto = await _prodotto_di(doc, org_id)
    ragioni = _ragioni_pubblicazione(doc, prodotto, await _prerequisiti(org_id))
    if ragioni:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT,
                            detail={"code": "non_pubblicabile", "ragioni": ragioni})
    await products_collection.update_one({"id": prodotto["id"], "organization_id": org_id},
                                         {"$set": {"is_published": True, "updated_at": datetime.now(timezone.utc).isoformat()}})
    return await _risposta(doc, org_id)


@router.post("/{course_id}/ritira")
async def ritira(course_id: str, current_user: dict = Depends(get_verified_user), _=Depends(_gate)):
    from database import products_collection
    org_id = current_user["organization_id"]
    doc = await _mio_corso(course_id, org_id)
    prodotto = await _prodotto_di(doc, org_id)
    await products_collection.update_one({"id": prodotto["id"], "organization_id": org_id},
                                         {"$set": {"is_published": False, "updated_at": datetime.now(timezone.utc).isoformat()}})
    return await _risposta(doc, org_id)


@router.delete("/{course_id}")
async def elimina_corso(course_id: str, current_user: dict = Depends(get_verified_user), _=Depends(_gate)):
    """Toglie il corso dal catalogo (disattiva corso e prodotto gemello).
    Gli studenti gia' iscritti continuano a seguirlo: il contenuto resta."""
    from database import products_collection, courses_collection
    org_id = current_user["organization_id"]
    doc = await _mio_corso(course_id, org_id)
    now = datetime.now(timezone.utc).isoformat()
    await products_collection.update_many({"organization_id": org_id, "item_type": "course", "metadata.course_id": course_id},
                                          {"$set": {"is_published": False, "is_active": False, "updated_at": now}})
    await courses_collection.update_one({"id": course_id, "organization_id": org_id},
                                        {"$set": {"is_active": False, "updated_at": now}})
    return {"ok": True, "id": course_id}


# ── moduli ───────────────────────────────────────────────────────────────

@router.post("/{course_id}/moduli", status_code=status.HTTP_201_CREATED)
async def crea_modulo(course_id: str, body: ModuloBody, current_user: dict = Depends(get_verified_user),
                      _=Depends(_gate)):
    from models.common import generate_id
    org_id = current_user["organization_id"]
    doc = await _mio_corso(course_id, org_id)
    doc.setdefault("modules", []).append({"id": generate_id(), "order": len(doc["modules"]),
                                         "title": body.title.strip(), "description": body.description, "lessons": []})
    return await _risposta(await _salva_moduli(doc, org_id), org_id)


@router.patch("/{course_id}/moduli/{module_id}")
async def modifica_modulo(course_id: str, module_id: str, body: ModuloBody,
                          current_user: dict = Depends(get_verified_user), _=Depends(_gate)):
    org_id = current_user["organization_id"]
    doc = await _mio_corso(course_id, org_id)
    m = next((m for m in doc.get("modules") or [] if m.get("id") == module_id), None)
    if not m:
        raise HTTPException(status_code=404, detail="Modulo non trovato")
    m["title"] = body.title.strip()
    m["description"] = body.description
    return await _risposta(await _salva_moduli(doc, org_id), org_id)


@router.delete("/{course_id}/moduli/{module_id}")
async def elimina_modulo(course_id: str, module_id: str, current_user: dict = Depends(get_verified_user),
                         _=Depends(_gate)):
    """Le lezioni del modulo tolto passano al modulo precedente (o al primo):
    non si perde mai una lezione cancellando un separatore."""
    org_id = current_user["organization_id"]
    doc = await _mio_corso(course_id, org_id)
    moduli = sorted(doc.get("modules") or [], key=lambda x: x.get("order", 0))
    idx = next((i for i, m in enumerate(moduli) if m.get("id") == module_id), None)
    if idx is None:
        raise HTTPException(status_code=404, detail="Modulo non trovato")
    if len(moduli) == 1:
        raise HTTPException(status_code=409, detail="Un corso ha almeno un modulo: rinominalo invece di toglierlo.")
    orfane = moduli[idx].get("lessons") or []
    dest = moduli[idx - 1] if idx > 0 else moduli[1]
    base = len(dest.get("lessons") or [])
    for j, l in enumerate(orfane):
        l["order"] = base + j
    dest.setdefault("lessons", []).extend(orfane)
    doc["modules"] = [m for m in moduli if m.get("id") != module_id]
    return await _risposta(await _salva_moduli(doc, org_id), org_id)


# ── lezioni ──────────────────────────────────────────────────────────────

@router.post("/{course_id}/lezioni", status_code=status.HTTP_201_CREATED)
async def crea_lezione(course_id: str, body: LezioneCreate, current_user: dict = Depends(get_verified_user),
                       _=Depends(_gate)):
    from models.common import generate_id
    from services.module_access import enforce_count_quota
    org_id = current_user["organization_id"]
    doc = await _mio_corso(course_id, org_id)
    await enforce_count_quota(org_id, "accademia", "lezioni_max", current_count=len(_lezioni(doc)),
                              message_template="Hai raggiunto il limite di {limit} lezioni per corso del tuo piano.",
                              hard_abuse_cap=5000)
    moduli = sorted(doc.get("modules") or [], key=lambda x: x.get("order", 0))
    if not moduli:
        moduli = [{"id": generate_id(), "order": 0, "title": MODULO_DEFAULT, "description": None, "lessons": []}]
        doc["modules"] = moduli
    m = next((m for m in moduli if m.get("id") == body.module_id), None) if body.module_id else moduli[-1]
    if not m:
        raise HTTPException(status_code=404, detail="Modulo non trovato")
    lezione = {"id": generate_id(), "order": len(m.get("lessons") or []), "title": body.title.strip(),
               "description": body.description, "tipo": body.tipo, "testo": body.testo if body.tipo == "testo" else None,
               "video": None, "duration_seconds": 0, "bunny_video_guid": None, "bunny_library_id": None,
               "resources": [], "is_preview": bool(body.is_preview)}
    m.setdefault("lessons", []).append(lezione)
    salvato = await _salva_moduli(doc, org_id)
    return {**(await _risposta(salvato, org_id)), "lezione_id": lezione["id"]}


@router.patch("/{course_id}/lezioni/{lesson_id}")
async def modifica_lezione(course_id: str, lesson_id: str, body: LezioneUpdate,
                           current_user: dict = Depends(get_verified_user), _=Depends(_gate)):
    org_id = current_user["organization_id"]
    doc = await _mio_corso(course_id, org_id)
    m, l = _trova_lezione(doc, lesson_id)
    if body.title is not None:
        l["title"] = body.title.strip()
    if body.description is not None:
        l["description"] = body.description
    if body.tipo is not None:
        l["tipo"] = body.tipo
    if body.testo is not None:
        l["testo"] = body.testo
    if body.is_preview is not None:
        l["is_preview"] = bool(body.is_preview)
    if body.module_id and body.module_id != m.get("id"):
        dest = next((x for x in doc.get("modules") or [] if x.get("id") == body.module_id), None)
        if not dest:
            raise HTTPException(status_code=404, detail="Modulo non trovato")
        m["lessons"] = [x for x in m.get("lessons") or [] if x.get("id") != lesson_id]
        l["order"] = len(dest.get("lessons") or [])
        dest.setdefault("lessons", []).append(l)
    return await _risposta(await _salva_moduli(doc, org_id), org_id)


@router.delete("/{course_id}/lezioni/{lesson_id}")
async def elimina_lezione(course_id: str, lesson_id: str, current_user: dict = Depends(get_verified_user),
                          _=Depends(_gate)):
    org_id = current_user["organization_id"]
    doc = await _mio_corso(course_id, org_id)
    m, l = _trova_lezione(doc, lesson_id)
    await _cancella_video_bunny(org_id, l)
    m["lessons"] = [x for x in m.get("lessons") or [] if x.get("id") != lesson_id]
    return await _risposta(await _salva_moduli(doc, org_id), org_id)


@router.put("/{course_id}/ordine")
async def riordina(course_id: str, body: OrdineBody, current_user: dict = Depends(get_verified_user),
                   _=Depends(_gate)):
    """L'ordine nuovo, come lista: [{id: modulo, lezioni: [id...]}, ...].
    Ogni modulo e ogni lezione del corso devono comparire una volta."""
    org_id = current_user["organization_id"]
    doc = await _mio_corso(course_id, org_id)
    moduli = {m["id"]: m for m in doc.get("modules") or []}
    lezioni = {l["id"]: l for l in _lezioni(doc)}
    visti_m, visti_l = [], []
    nuovi = []
    for i, blocco in enumerate(body.moduli):
        m = moduli.get(str(blocco.get("id")))
        if not m or m["id"] in visti_m:
            raise HTTPException(status_code=400, detail="Ordine non valido: modulo sconosciuto o ripetuto.")
        visti_m.append(m["id"])
        nuove = []
        for j, lid in enumerate(blocco.get("lezioni") or []):
            l = lezioni.get(str(lid))
            if not l or l["id"] in visti_l:
                raise HTTPException(status_code=400, detail="Ordine non valido: lezione sconosciuta o ripetuta.")
            visti_l.append(l["id"])
            l["order"] = j
            nuove.append(l)
        m["order"] = i
        m["lessons"] = nuove
        nuovi.append(m)
    if len(visti_m) != len(moduli) or len(visti_l) != len(lezioni):
        raise HTTPException(status_code=400, detail="Ordine non valido: manca un modulo o una lezione.")
    doc["modules"] = nuovi
    return await _risposta(await _salva_moduli(doc, org_id), org_id)


# ── il video di una lezione ──────────────────────────────────────────────

async def _cancella_video_bunny(org_id: str, l: dict) -> None:
    """Best-effort: cancella il video su Bunny e scala la quota. Mai blocca."""
    v = l.get("video") or {}
    if not v.get("guid"):
        return
    from database import organizations_collection
    from services.bunny import gestito
    from services.bunny.client import BunnyClient
    org = await organizations_collection.find_one({"id": org_id}, {"_id": 0, "integrations": 1})
    lib = next((x for x in ((org or {}).get("integrations") or {}).get("bunny_libraries") or []
                if x.get("id") == v.get("library_id")), None)
    if lib and gestito.attivo():
        try:
            async with BunnyClient(lib["api_key"]) as c:
                await c.delete_video(str(lib["library_id"]), v["guid"])
        except Exception as exc:  # noqa: BLE001
            logger.warning("accademia: video %s non cancellato su Bunny: %s", v.get("guid"), exc)
    if lib:
        await gestito.aggiorna_quota(org_id, lib["id"], -int(v.get("size_bytes") or 0), -1)
    l["video"] = None
    l["bunny_video_guid"] = None
    l["duration_seconds"] = 0


@router.post("/{course_id}/lezioni/{lesson_id}/video")
async def nuovo_video(course_id: str, lesson_id: str, body: VideoBody,
                      current_user: dict = Depends(get_verified_user), _=Depends(_gate)):
    """Prepara l'upload: quota, libreria gestita (creata se manca), video su
    Bunny, credenziali TUS firmate. Il file NON passa dal server."""
    from services.bunny import gestito
    from services.bunny.client import BunnyClient
    org_id = current_user["organization_id"]
    if not gestito.attivo():
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                            detail={"code": "bunny_non_configurato",
                                    "message": "Il caricamento video non è ancora attivo su questo ambiente."})
    doc = await _mio_corso(course_id, org_id)
    m, l = _trova_lezione(doc, lesson_id)
    quota = await _quota_video(org_id)
    gia = int(((l.get("video") or {}).get("size_bytes")) or 0)
    if quota.get("max_bytes") and quota["usati_bytes"] - gia + body.size_bytes > quota["max_bytes"]:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT,
                            detail={"code": "quota_video",
                                    "message": f"Il tuo piano comprende {quota['max_gb']} GB di video: con questo file li superi "
                                               f"(usati {quota['usati_gb']} GB). Togli un video o passa al Pro."})
    try:
        lib = await gestito.assicura_libreria(org_id)
    except RuntimeError:
        raise HTTPException(status_code=503, detail={"code": "bunny_non_configurato", "message": "Caricamento video non attivo."})
    await _cancella_video_bunny(org_id, l)    # un video per lezione: il nuovo sostituisce il vecchio
    async with BunnyClient(lib["api_key"]) as c:
        creato = await c.create_video(str(lib["library_id"]), f"{doc.get('title', '')} — {l.get('title', '')}")
    guid = creato.get("guid")
    if not guid:
        raise HTTPException(status_code=502, detail="Bunny non ha creato il video.")
    now = datetime.now(timezone.utc).isoformat()
    l["tipo"] = "video"
    l["video"] = {"guid": guid, "library_id": lib["id"], "bunny_library_id": str(lib["library_id"]),
                  "stato": "caricamento", "duration_seconds": 0, "size_bytes": int(body.size_bytes),
                  "thumbnail_url": None, "uploaded_at": now, "updated_at": now}
    await _salva_moduli(doc, org_id)
    await gestito.aggiorna_quota(org_id, lib["id"], int(body.size_bytes), 1)
    return gestito.credenziali_tus(lib, guid)


@router.get("/{course_id}/lezioni/{lesson_id}/video")
async def stato_video(course_id: str, lesson_id: str, current_user: dict = Depends(get_verified_user),
                      _=Depends(_gate)):
    """Lo stato del video; se e' ancora in lavorazione e Bunny risponde,
    lo rilegge (il webhook potrebbe non essere arrivato)."""
    from database import organizations_collection
    from services.bunny import gestito
    from services.bunny.client import BunnyClient
    from routers.webhooks_bunny import applica_evento
    org_id = current_user["organization_id"]
    doc = await _mio_corso(course_id, org_id)
    m, l = _trova_lezione(doc, lesson_id)
    v = l.get("video") or {}
    if v.get("guid") and v.get("stato") in ("caricamento", "codifica") and gestito.attivo():
        org = await organizations_collection.find_one({"id": org_id}, {"_id": 0, "integrations": 1})
        lib = next((x for x in ((org or {}).get("integrations") or {}).get("bunny_libraries") or []
                    if x.get("id") == v.get("library_id")), None)
        if lib:
            try:
                async with BunnyClient(lib["api_key"]) as c:
                    remoto = await c.get_video(str(lib["library_id"]), v["guid"])
                stato = gestito.stato_da_bunny(remoto.get("status"))
                if stato != v.get("stato"):
                    await applica_evento(org_id, lib, v["guid"], stato)
                    doc = await _mio_corso(course_id, org_id)
                    m, l = _trova_lezione(doc, lesson_id)
            except Exception as exc:  # noqa: BLE001
                logger.info("accademia: stato video %s non riletto: %s", v.get("guid"), exc)
    return _riga_lezione(l)


@router.delete("/{course_id}/lezioni/{lesson_id}/video")
async def togli_video(course_id: str, lesson_id: str, current_user: dict = Depends(get_verified_user),
                      _=Depends(_gate)):
    org_id = current_user["organization_id"]
    doc = await _mio_corso(course_id, org_id)
    m, l = _trova_lezione(doc, lesson_id)
    await _cancella_video_bunny(org_id, l)
    return await _risposta(await _salva_moduli(doc, org_id), org_id)


# ── gli studenti ─────────────────────────────────────────────────────────

@router.get("/{course_id}/studenti")
async def studenti(course_id: str, current_user: dict = Depends(get_verified_user), _=Depends(_gate)):
    from database import db, issued_course_accesses_collection
    org_id = current_user["organization_id"]
    doc = await _mio_corso(course_id, org_id)
    n_lezioni = len(_lezioni(doc)) or 1
    rows = await issued_course_accesses_collection.find(
        {"organization_id": org_id, "course_id": course_id},
        {"_id": 0, "id": 1, "order_id": 1, "platform_account_id": 1, "customer_account_id": 1, "enrolled_at": 1,
         "expires_at": 1, "revoked_at": 1, "revoked_reason": 1, "progress": 1, "last_accessed_at": 1,
         "completed_at": 1, "source": 1}).sort("enrolled_at", -1).to_list(500)
    ids = [r["platform_account_id"] for r in rows if r.get("platform_account_id")]
    account = {a["id"]: a async for a in db.platform_accounts.find({"id": {"$in": ids}}, {"_id": 0, "id": 1, "email": 1, "name": 1})}
    now = datetime.now(timezone.utc)
    out = []
    for r in rows:
        a = account.get(r.get("platform_account_id")) or {}
        prog = r.get("progress") or {}
        fatte = sum(1 for p in prog.values() if (p or {}).get("completed_at"))
        exp = r.get("expires_at")
        scaduto = False
        if exp:
            try:
                e = datetime.fromisoformat(str(exp).replace("Z", "+00:00")) if isinstance(exp, str) else exp
                scaduto = e.replace(tzinfo=e.tzinfo or timezone.utc) < now
            except ValueError:
                scaduto = False
        stato = "revocato" if r.get("revoked_at") else ("scaduto" if scaduto else ("completato" if r.get("completed_at") else "attivo"))
        out.append({"id": r["id"], "nome": a.get("name"), "email": a.get("email"), "stato": stato,
                    "lezioni_fatte": fatte, "lezioni_totali": n_lezioni, "percentuale": int(round(100 * fatte / n_lezioni)),
                    "iscritto_il": r.get("enrolled_at"), "ultimo_accesso": r.get("last_accessed_at"),
                    "scade_il": exp, "revocato_il": r.get("revoked_at"), "motivo": r.get("revoked_reason"),
                    "source": r.get("source") or "order"})
    return {"studenti": out, "total": len(out)}


@router.post("/{course_id}/studenti/{enrollment_id}/revoca")
async def revoca(course_id: str, enrollment_id: str, body: RevocaBody,
                 current_user: dict = Depends(get_verified_user), _=Depends(_gate)):
    from database import issued_course_accesses_collection
    org_id = current_user["organization_id"]
    await _mio_corso(course_id, org_id)
    enr = await issued_course_accesses_collection.find_one(
        {"id": enrollment_id, "organization_id": org_id, "course_id": course_id}, {"_id": 0, "id": 1, "revoked_at": 1})
    if not enr:
        raise HTTPException(status_code=404, detail="Iscrizione non trovata")
    if enr.get("revoked_at"):
        return {"id": enrollment_id, "gia_revocata": True}
    now = datetime.now(timezone.utc)
    await issued_course_accesses_collection.update_one(
        {"id": enrollment_id, "organization_id": org_id},
        {"$set": {"revoked_at": now, "revoked_reason": body.motivo.strip(), "updated_at": now}})
    logger.info("accademia: iscrizione %s revocata da %s: %r", enrollment_id, current_user.get("user_id"), body.motivo)
    return {"id": enrollment_id, "gia_revocata": False, "revocato_il": now.isoformat()}
