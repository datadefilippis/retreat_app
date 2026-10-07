"""
/api/platform/me/corsi — LO STUDENTE segue i suoi corsi con l'account Aurya
(AC2, 7/10/2026; piano docs/PIANO_ACCADEMIA_2026-10-06.md §5 e §7).

Stesso stampo di /platform/me/file: le iscrizioni timbrate con
`platform_account_id` (AC0), su tutti gli operatori. Il player legacy
(/customer/courses, JWT per negozio) resta com'e' e si dismette con AC3.

Sicurezza (come il legacy, che ha questi invarianti giusti):
  - `platform_account_id` e' DENTRO la query Mongo, mai un controllo dopo;
  - revocato → 403 `enrollment_revoked`, scaduto → 403 `enrollment_expired`,
    corso sparito → 410 `course_unavailable`, lezione di un altro corso → 404;
  - il GUID Bunny non esce mai: esce l'URL firmato a 2 ore, col watermark
    dell'email dello studente; rate limit su play-url e progresso;
  - il progresso e' idempotente: watched_seconds monotono, completed_at
    fisso; al 100% il corso si segna `completed_at` una volta sola.
"""
# niente `from __future__ import annotations`: con il decoratore del rate limit
# le annotazioni-stringa non si risolvono e il corpo diventa una query (422)
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, ConfigDict, Field

from auth import get_current_platform_account
from routers.auth import limiter

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/platform/me/corsi", tags=["Accademia"])


class ProgressoBody(BaseModel):
    model_config = ConfigDict(extra="ignore")
    lesson_id: str = Field(min_length=1, max_length=64)
    watched_seconds: int = Field(default=0, ge=0, le=100_000)
    completed: bool = False


def _dt(v: Any) -> Optional[datetime]:
    if v is None:
        return None
    if isinstance(v, datetime):
        return v if v.tzinfo else v.replace(tzinfo=timezone.utc)
    try:
        d = datetime.fromisoformat(str(v).replace("Z", "+00:00"))
        return d if d.tzinfo else d.replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def _scaduta(enr: dict, now: datetime) -> bool:
    e = _dt(enr.get("expires_at"))
    return bool(e and e < now)


def _stato(enr: dict, now: datetime) -> str:
    if enr.get("revoked_at"):
        return "revocato"
    if _scaduta(enr, now):
        return "scaduto"
    if enr.get("completed_at"):
        return "completato"
    return "attivo"


def _lezioni(course_doc: dict) -> List[dict]:
    out = []
    for m in sorted(course_doc.get("modules") or [], key=lambda x: x.get("order", 0)):
        for l in sorted(m.get("lessons") or [], key=lambda x: x.get("order", 0)):
            out.append(l)
    return out


def _video_pronto(l: dict) -> bool:
    v = l.get("video") or {}
    if v:
        return v.get("stato") == "pronto" and bool(v.get("guid"))
    return bool(l.get("bunny_video_guid"))


def _proietta(course_doc: dict, firma=None) -> dict:
    """Il corso per lo studente: MAI il GUID Bunny; `tipo`, `testo`,
    `has_video`, `video_pronto` in piu' rispetto al legacy."""
    moduli = []
    for m in sorted(course_doc.get("modules") or [], key=lambda x: x.get("order", 0)):
        lezioni = []
        for l in sorted(m.get("lessons") or [], key=lambda x: x.get("order", 0)):
            v = l.get("video") or {}
            lezioni.append({
                "id": l.get("id"), "order": int(l.get("order") or 0), "title": l.get("title", ""),
                "description": l.get("description"),
                "tipo": l.get("tipo") or ("video" if (v or l.get("bunny_video_guid")) else "testo"),
                "testo": l.get("testo") if (l.get("tipo") == "testo") else None,
                "duration_seconds": int(l.get("duration_seconds") or v.get("duration_seconds") or 0),
                "is_preview": bool(l.get("is_preview")),
                "has_video": bool(v.get("guid") or l.get("bunny_video_guid")),
                "video_pronto": _video_pronto(l),
                "thumbnail_url": (firma(v) if (firma and v.get("thumbnail_url")) else None),
                "resources": l.get("resources") or [],
            })
        moduli.append({"id": m.get("id"), "order": int(m.get("order") or 0), "title": m.get("title", ""),
                       "description": m.get("description"), "lessons": lezioni})
    return {
        "id": course_doc.get("id"), "title": course_doc.get("title", ""), "description": course_doc.get("description"),
        "long_description": course_doc.get("long_description"), "cover_image_url": course_doc.get("cover_image_url"),
        "instructor_name": course_doc.get("instructor_name"), "instructor_bio": course_doc.get("instructor_bio"),
        "access_policy": course_doc.get("access_policy") or "lifetime",
        "access_expiry_days": course_doc.get("access_expiry_days"), "modules": moduli,
    }


def _stats(course_doc: dict, progress: dict) -> dict:
    lezioni = _lezioni(course_doc)
    ids = {l.get("id") for l in lezioni}
    fatte = sum(1 for k, p in (progress or {}).items() if k in ids and (p or {}).get("completed_at"))
    tot = len(ids)
    return {"lessons_completed": fatte, "total_lessons": tot, "percentage": int(round(100 * fatte / tot)) if tot else 0}


def _iscrizione_out(enr: dict, now: datetime) -> dict:
    return {
        "id": enr.get("id"), "course_id": enr.get("course_id"), "course_title_snapshot": enr.get("course_title_snapshot"),
        "enrolled_at": enr.get("enrolled_at"), "expires_at": enr.get("expires_at"), "revoked_at": enr.get("revoked_at"),
        "revoked_reason": enr.get("revoked_reason"), "last_accessed_at": enr.get("last_accessed_at"),
        "completed_at": enr.get("completed_at"), "source": enr.get("source") or "order", "stato": _stato(enr, now),
        "order_id": enr.get("order_id"),
    }


async def _mia_iscrizione(enrollment_id: str, account_id: str) -> dict:
    from database import issued_course_accesses_collection
    enr = await issued_course_accesses_collection.find_one(
        {"id": enrollment_id, "platform_account_id": account_id}, {"_id": 0})
    if not enr:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Corso non trovato")
    return enr


def _apri_o_403(enr: dict, now: datetime) -> None:
    if enr.get("revoked_at"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail={"error": "enrollment_revoked", "message": "L'accesso a questo corso è stato revocato."})
    if _scaduta(enr, now):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail={"error": "enrollment_expired", "message": "Il tuo accesso a questo corso è scaduto."})


async def _corso_vivo(enr: dict) -> dict:
    from database import courses_collection
    doc = await courses_collection.find_one({"id": enr.get("course_id"), "organization_id": enr.get("organization_id")}, {"_id": 0})
    if not doc:
        raise HTTPException(status_code=status.HTTP_410_GONE,
                            detail={"error": "course_unavailable", "message": "Questo corso non è più disponibile."})
    return doc


async def _firma_org(org_id: str):
    from database import organizations_collection
    from routers.accademia import _firmatore
    org = await organizations_collection.find_one({"id": org_id}, {"_id": 0, "integrations.bunny_libraries": 1})
    return _firmatore(org)


@router.get("")
async def i_miei_corsi(account: dict = Depends(get_current_platform_account)):
    """«I miei corsi»: tutte le iscrizioni dell'account (anche scadute e
    revocate: la card resta, con lo stato), col progresso e chi insegna."""
    from database import issued_course_accesses_collection, courses_collection, organizations_collection
    now = datetime.now(timezone.utc)
    rows = await issued_course_accesses_collection.find(
        {"platform_account_id": account["id"]}, {"_id": 0}).sort("enrolled_at", -1).to_list(500)
    if not rows:
        return {"corsi": [], "total": 0}
    corsi = {c["id"]: c async for c in courses_collection.find(
        {"id": {"$in": list({r["course_id"] for r in rows})}}, {"_id": 0})}
    orgs = {o["id"]: o async for o in organizations_collection.find(
        {"id": {"$in": list({r["organization_id"] for r in rows})}},
        {"_id": 0, "id": 1, "name": 1, "public_slug": 1, "store_settings.display_name": 1})}
    out = []
    for r in rows:
        c = corsi.get(r.get("course_id")) or {}
        o = orgs.get(r.get("organization_id")) or {}
        lezioni = _lezioni(c)
        prog = r.get("progress") or {}
        prossima = next((l for l in lezioni if not (prog.get(l.get("id")) or {}).get("completed_at")), None)
        out.append({
            "iscrizione": _iscrizione_out(r, now),
            "corso": {"id": c.get("id"), "title": c.get("title") or r.get("course_title_snapshot"),
                      "cover_image_url": c.get("cover_image_url"), "instructor_name": c.get("instructor_name"),
                      "lezioni_count": len(lezioni),
                      "durata_totale_seconds": sum(int(l.get("duration_seconds") or 0) for l in lezioni),
                      "disponibile": bool(c)},
            "operatore": {"slug": o.get("public_slug"), "name": (o.get("store_settings") or {}).get("display_name") or o.get("name")},
            "progress_stats": _stats(c, prog),
            "prossima_lezione": ({"id": prossima.get("id"), "title": prossima.get("title")} if prossima else None),
        })
    return {"corsi": out, "total": len(out)}


@router.get("/{enrollment_id}")
async def un_corso(enrollment_id: str, account: dict = Depends(get_current_platform_account)):
    """Il corso da seguire: stesso contratto del legacy ({enrollment, course,
    progress, progress_stats}) cosi' i componenti del player si riusano."""
    now = datetime.now(timezone.utc)
    enr = await _mia_iscrizione(enrollment_id, account["id"])
    _apri_o_403(enr, now)
    doc = await _corso_vivo(enr)
    firma = await _firma_org(enr.get("organization_id"))
    return {"enrollment": _iscrizione_out(enr, now), "course": _proietta(doc, firma),
            "progress": enr.get("progress") or {}, "progress_stats": _stats(doc, enr.get("progress") or {})}


@router.post("/{enrollment_id}/lezioni/{lesson_id}/play-url")
@limiter.limit("60/minute")
async def play_url(request: Request, enrollment_id: str, lesson_id: str,
                   account: dict = Depends(get_current_platform_account)):
    from database import issued_course_accesses_collection, organizations_collection
    from services.bunny import resolve_library_config
    from services.bunny.signer import generate_signed_embed_url, validate_bunny_config
    now = datetime.now(timezone.utc)
    enr = await _mia_iscrizione(enrollment_id, account["id"])
    _apri_o_403(enr, now)
    doc = await _corso_vivo(enr)
    lezione = next((l for l in _lezioni(doc) if l.get("id") == lesson_id), None)
    if not lezione:
        raise HTTPException(status_code=404, detail="Lezione non trovata in questo corso")
    if not _video_pronto(lezione):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT,
                            detail={"error": "video_not_ready", "message": "Il video di questa lezione non è ancora pronto."})
    org = await organizations_collection.find_one({"id": enr.get("organization_id")}, {"_id": 0, "integrations": 1})
    v = lezione.get("video") or {}
    riferimento = {"bunny_library_id": v.get("library_id") or lezione.get("bunny_library_id"),
                   "bunny_video_guid": v.get("guid") or lezione.get("bunny_video_guid")}
    cfg = resolve_library_config(riferimento, org)
    if not validate_bunny_config(cfg):
        raise HTTPException(status_code=503, detail={"error": "bunny_not_configured", "message": "Servizio video non disponibile."})
    firmato = generate_signed_embed_url(cfg, riferimento["bunny_video_guid"], customer_email=account.get("email"))
    try:
        await issued_course_accesses_collection.update_one(
            {"id": enrollment_id, "platform_account_id": account["id"]}, {"$set": {"last_accessed_at": now}})
    except Exception as exc:  # noqa: BLE001
        logger.info("platform_corsi: last_accessed_at non aggiornato: %s", exc)
    return {"play_url": firmato.play_url, "expires_at": firmato.expires_at.isoformat(), "watermark_text": firmato.watermark_text}


@router.post("/{enrollment_id}/progresso")
@limiter.limit("120/minute")
async def progresso(request: Request, enrollment_id: str, body: ProgressoBody,
                    account: dict = Depends(get_current_platform_account)):
    from database import issued_course_accesses_collection
    now = datetime.now(timezone.utc)
    enr = await _mia_iscrizione(enrollment_id, account["id"])
    _apri_o_403(enr, now)
    doc = await _corso_vivo(enr)
    ids = {l.get("id") for l in _lezioni(doc)}
    if body.lesson_id not in ids:
        raise HTTPException(status_code=404, detail="Lezione non trovata in questo corso")
    progress = dict(enr.get("progress") or {})
    cur = progress.get(body.lesson_id) or {}
    nuovo_w = max(int(cur.get("watched_seconds") or 0), int(body.watched_seconds))
    nuovo_c = cur.get("completed_at")
    if body.completed and not nuovo_c:
        nuovo_c = now
    progress[body.lesson_id] = {"watched_seconds": nuovo_w, "completed_at": nuovo_c}
    stats = _stats(doc, progress)
    upd: Dict[str, Any] = {"progress": progress, "last_accessed_at": now, "updated_at": now}
    completato_ora = False
    if stats["total_lessons"] and stats["lessons_completed"] >= stats["total_lessons"] and not enr.get("completed_at"):
        upd["completed_at"] = now          # il percorso e' FINITO: una volta sola
        completato_ora = True
    await issued_course_accesses_collection.update_one(
        {"id": enrollment_id, "platform_account_id": account["id"]}, {"$set": upd})
    c = nuovo_c.isoformat() if hasattr(nuovo_c, "isoformat") else nuovo_c
    return {"lesson_id": body.lesson_id, "watched_seconds": nuovo_w, "completed_at": c,
            "progress_stats": stats, "corso_completato": bool(enr.get("completed_at") or completato_ora),
            "completato_ora": completato_ora}
