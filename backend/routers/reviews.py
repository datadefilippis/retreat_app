"""Recensioni operatore — endpoints pubblici e admin (PR2).

Pubblici (/public/reviews/*): OTP + submit + lista. Enumeration-safe
sull'OTP (202 sempre); rate limit stretti; honeypot sul submit.
Admin (/reviews/*): lista con filtri, reply, moderazione dei pending
(solo unverified), flag abuse, toggle reviews_open.
"""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, EmailStr, Field

from auth import require_admin
from services.module_access import require_module
from routers.auth import limiter

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Reviews"])


# ── Pubblico ─────────────────────────────────────────────────────────────────

class ReviewOtpRequest(BaseModel):
    org_slug: str = Field(min_length=3, max_length=50)
    email: EmailStr
    language: Optional[str] = Field(default=None, max_length=5)


class ReviewSubmit(BaseModel):
    org_slug: str = Field(min_length=3, max_length=50)
    email: EmailStr
    code: str = Field(min_length=6, max_length=6)
    rating: int = Field(ge=1, le=5)
    body: str = Field(min_length=1, max_length=2000)
    author_name: str = Field(min_length=1, max_length=80)
    title: Optional[str] = Field(default=None, max_length=120)
    language: Optional[str] = Field(default=None, max_length=5)
    # honeypot: i bot compilano tutto; gli umani non lo vedono (campo
    # nascosto via CSS). Valorizzato → 202 finto, niente scrittura.
    website: Optional[str] = Field(default=None, max_length=200)


@router.post("/public/reviews/request-otp", status_code=202)
@limiter.limit("5/minute")
async def review_request_otp(body: ReviewOtpRequest, request: Request):
    """202 SEMPRE: né l'esistenza dell'org né lo stato dell'email
    trapelano da qui."""
    from services.review_service import request_review_otp
    try:
        lang = body.language if body.language in ("it", "en", "de", "fr") else "it"
        await request_review_otp(body.org_slug, body.email, lang)
    except Exception:
        logger.exception("review otp request fallita")
    return {"status": "accepted"}


@router.post("/public/reviews/submit")
@limiter.limit("5/minute")
async def review_submit(body: ReviewSubmit, request: Request):
    from services.review_service import submit_review, ReviewError
    if body.website:                      # honeypot
        return {"status": "accepted"}
    try:
        review = await submit_review(
            org_slug=body.org_slug, email=body.email, code=body.code,
            rating=body.rating, body=body.body,
            author_name=body.author_name, title=body.title,
            lang=(body.language or "it")[:2],
        )
    except ReviewError as exc:
        raise HTTPException(status_code=400, detail={
            "error": exc.code, "message": exc.message})
    return {"status": review["status"], "verified": review["verified"],
            "id": review["id"]}


@router.get("/public/reviews/{org_slug}")
@limiter.limit("30/minute")
async def review_list_public(org_slug: str, request: Request,
                             page: int = Query(default=1, ge=1, le=500)):
    from routers.public import _resolve_org
    from services.review_service import list_public
    org = await _resolve_org(org_slug)
    return await list_public(org["id"], page=page)


# ── Admin ────────────────────────────────────────────────────────────────────

class ReplyBody(BaseModel):
    body: str = Field(min_length=1, max_length=1000)


class ModerateBody(BaseModel):
    action: str = Field(pattern="^(approve|reject)$")


class ReviewSettings(BaseModel):
    reviews_open: bool


@router.get("/reviews")
async def admin_list_reviews(
    status: Optional[str] = Query(default=None, max_length=20),
    page: int = Query(default=1, ge=1, le=500),
    current_user: dict = Depends(require_admin),
    _module: dict = Depends(require_module("reviews")),
):
    from database import reviews_collection, organizations_collection
    org_id = current_user["organization_id"]
    q = {"organization_id": org_id}
    q["status"] = status if status in ("published", "pending", "flagged") \
        else {"$ne": "removed"}
    page_size = 20
    items = await reviews_collection.find(
        q, {"_id": 0, "author_email_hash": 0},
    ).sort("created_at", -1).skip((page - 1) * page_size).limit(page_size) \
        .to_list(page_size)
    total = await reviews_collection.count_documents(q)
    org = await organizations_collection.find_one(
        {"id": org_id}, {"_id": 0, "reviews_stats": 1, "reviews_open": 1})
    pending = await reviews_collection.count_documents(
        {"organization_id": org_id, "status": "pending"})
    return {"items": items, "total": total, "page": page,
            "stats": (org or {}).get("reviews_stats"),
            "reviews_open": bool((org or {}).get("reviews_open")),
            "pending_count": pending}


@router.post("/reviews/{review_id}/reply")
async def admin_reply(review_id: str, body: ReplyBody,
                      current_user: dict = Depends(require_admin),
                      _module: dict = Depends(require_module("reviews"))):
    from database import reviews_collection
    from models.common import utc_now
    res = await reviews_collection.update_one(
        {"id": review_id, "organization_id": current_user["organization_id"],
         "status": {"$in": ["published", "pending"]}},
        {"$set": {"reply": {"body": body.body.strip(),
                            "at": utc_now().isoformat()}}},
    )
    if res.matched_count == 0:
        raise HTTPException(status_code=404, detail="Recensione non trovata")
    return {"ok": True}


@router.patch("/reviews/{review_id}/moderate")
async def admin_moderate(review_id: str, body: ModerateBody,
                         current_user: dict = Depends(require_admin),
                      _module: dict = Depends(require_module("reviews"))):
    """Moderazione SOLO dei pending unverified (le verified pubblicano
    da sole e l'operatore non le governa — credibilità marketplace)."""
    from database import reviews_collection
    from services.review_service import recompute_stats
    org_id = current_user["organization_id"]
    new_status = "published" if body.action == "approve" else "removed"
    res = await reviews_collection.update_one(
        {"id": review_id, "organization_id": org_id,
         "status": "pending", "verified": False},
        {"$set": {"status": new_status}},
    )
    if res.matched_count == 0:
        raise HTTPException(
            status_code=404,
            detail="Recensione non trovata o non moderabile")
    await recompute_stats(org_id)
    return {"ok": True, "status": new_status}


@router.post("/reviews/{review_id}/flag")
async def admin_flag(review_id: str,
                     current_user: dict = Depends(require_admin),
                      _module: dict = Depends(require_module("reviews"))):
    """Segnala un abuso: la recensione sparisce dal pubblico in attesa
    della revisione della piattaforma (notifica interna)."""
    from database import reviews_collection
    from services.review_service import recompute_stats
    org_id = current_user["organization_id"]
    res = await reviews_collection.update_one(
        {"id": review_id, "organization_id": org_id,
         "status": "published"},
        {"$set": {"status": "flagged"}},
    )
    if res.matched_count == 0:
        raise HTTPException(status_code=404, detail="Recensione non trovata")
    await recompute_stats(org_id)
    logger.warning("review flagged per revisione piattaforma: %s (org=%s)",
                   review_id, org_id)
    return {"ok": True}


@router.patch("/reviews/settings")
async def admin_review_settings(body: ReviewSettings,
                                current_user: dict = Depends(require_admin),
                      _module: dict = Depends(require_module("reviews"))):
    from database import organizations_collection
    await organizations_collection.update_one(
        {"id": current_user["organization_id"]},
        {"$set": {"reviews_open": bool(body.reviews_open)}},
    )
    return {"reviews_open": bool(body.reviews_open)}
