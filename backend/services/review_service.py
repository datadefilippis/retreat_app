"""Sistema recensioni operatore (PR2, OPERATOR_PROFILE_REVIEWS_PLAN).

Le regole di solidità (decise col founder):
  - recensisce di default SOLO chi ha ≥1 ordine non-draft/non-cancelled
    presso quell'organizzazione (verified); la prova di possesso email
    è un OTP a 6 cifre via email — stesso pattern del Passaporto
    (hash-only a DB, one-shot, max 5 tentativi, TTL 15 min);
  - `org.reviews_open` (opt-in, default False): chi non ha ordini può
    scrivere ma la recensione nasce `pending` (moderazione operatore)
    e non avrà MAI il badge verified;
  - 1 recensione per email per operatore: upsert su
    (organization_id, author_email_hash) — la nuova sostituisce;
  - l'email NON vive mai in chiaro sul documento (solo hash salato);
  - l'operatore risponde e segnala; NON cancella le verified;
  - `organizations.reviews_stats` {avg, count, distribution}
    denormalizzato: il profilo legge un campo, zero aggregation.
"""

import hashlib
import logging
import os
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

from models.common import generate_id, utc_now

logger = logging.getLogger(__name__)

OTP_TTL_MINUTES = 15
OTP_MAX_ATTEMPTS = 5
BODY_MIN, BODY_MAX = 20, 1500
TITLE_MAX, NAME_MAX = 80, 60

# Stati ammessi e transizioni: published ⇄ flagged; pending → published
# (approve) | removed (reject). `removed` resta a DB (audit), mai reso.
STATUSES = ("published", "pending", "flagged", "removed")


def _normalize_email(email: str) -> str:
    return (email or "").strip().lower()


def _email_hash(email: str) -> str:
    """Hash salato: l'email in chiaro non tocca mai il documento review."""
    salt = os.environ.get("REVIEW_HASH_SALT") or os.environ.get(
        "JWT_SECRET_KEY", "dev-salt")
    return hashlib.sha256((salt + _normalize_email(email)).encode()).hexdigest()


def _hash_code(code: str) -> str:
    return hashlib.sha256(code.encode()).hexdigest()


def _iso(dt) -> str:
    return dt.isoformat() if isinstance(dt, datetime) else dt


# ── OTP ──────────────────────────────────────────────────────────────────────

async def request_review_otp(org_slug: str, email: str,
                             locale: str = "it") -> None:
    """Emette l'OTP via email. NON rivela nulla (202 sempre dal router):
    né se l'org esiste né se l'email ha ordini — quello si scopre solo
    al submit, a possesso email dimostrato."""
    from database import review_otps_collection

    email_n = _normalize_email(email)
    if not email_n or "@" not in email_n:
        return

    code = f"{secrets.randbelow(1_000_000):06d}"
    await review_otps_collection.insert_one({
        "id": generate_id(),
        "org_slug": org_slug,
        "email_hash": _email_hash(email_n),
        "code_hash": _hash_code(code),
        "attempts": 0,
        "used_at": None,
        "expires_at": _iso(utc_now() + timedelta(minutes=OTP_TTL_MINUTES)),
        "created_at": _iso(utc_now()),
    })
    _send_review_otp_email(email_n, code, org_slug, locale)


async def _consume_otp(org_slug: str, email: str, code: str) -> bool:
    """Verifica one-shot atomica (find_one_and_update): due submit
    concorrenti con lo stesso codice non passano entrambi; il tentativo
    fallito incrementa il contatore fino al lockout."""
    from database import review_otps_collection

    now_iso = _iso(utc_now())
    base = {
        "org_slug": org_slug,
        "email_hash": _email_hash(email),
        "used_at": None,
        "expires_at": {"$gt": now_iso},
        "attempts": {"$lt": OTP_MAX_ATTEMPTS},
    }
    ok = await review_otps_collection.find_one_and_update(
        {**base, "code_hash": _hash_code(code or "")},
        {"$set": {"used_at": now_iso}},
    )
    if ok:
        return True
    await review_otps_collection.update_many(base, {"$inc": {"attempts": 1}})
    return False


def _send_review_otp_email(email: str, code: str, org_slug: str,
                           locale: str) -> None:
    from services.email_service import send_email, _t, _wrap_template
    content = f"""
    <p>{_t("greeting", locale)},</p>
    <p>{_t("review_otp_body", locale, operator=org_slug)}</p>
    <p style="font-size:32px;letter-spacing:8px;font-weight:bold;
    background:#f1ede3;color:#212c28;border-radius:12px;padding:14px 18px;
    display:inline-block">{code}</p>
    <p style="color:#8a9088;font-size:13px">{_t("review_otp_hint", locale,
                                                minutes=OTP_TTL_MINUTES)}</p>
    """
    send_email(email, _t("review_otp_subject", locale),
               _wrap_template(content, locale), bypass_gate=True)


# ── Verified gate ────────────────────────────────────────────────────────────

async def has_orders_with_org(org_id: str, email: str) -> bool:
    """True se l'email appartiene a ≥1 ordine non-draft/non-cancelled
    dell'organizzazione (il CRM customers è org-scoped: stessa
    risoluzione del claim Passaporto)."""
    from database import customers_collection, orders_collection

    email_n = _normalize_email(email)
    ids = [c["id"] async for c in customers_collection.find(
        {"organization_id": org_id, "email": email_n}, {"_id": 0, "id": 1},
    ).limit(20)]
    if not ids:
        return False
    n = await orders_collection.count_documents({
        "organization_id": org_id,
        "customer_id": {"$in": ids},
        "status": {"$nin": ["draft", "cancelled"]},
    })
    return n > 0


# ── Submit ───────────────────────────────────────────────────────────────────

class ReviewError(Exception):
    def __init__(self, code: str, message: str):
        self.code = code
        self.message = message
        super().__init__(message)


async def submit_review(*, org_slug: str, email: str, code: str,
                        rating: int, body: str, author_name: str,
                        title: Optional[str] = None,
                        lang: str = "it") -> Dict[str, Any]:
    from database import organizations_collection, reviews_collection
    from routers.public import _resolve_org

    if not await _consume_otp(org_slug, email, code):
        raise ReviewError("invalid_code", "Codice non valido o scaduto")

    org = await _resolve_org(org_slug)     # 404 se l'org non è pubblica
    org_id = org["id"]
    verified = await has_orders_with_org(org_id, email)

    if not verified:
        org_doc = await organizations_collection.find_one(
            {"id": org_id}, {"_id": 0, "reviews_open": 1})
        if not (org_doc or {}).get("reviews_open"):
            raise ReviewError(
                "orders_required",
                "Per ora questo operatore accetta recensioni solo da chi "
                "ha già prenotato con lui.")

    rating = int(rating)
    if not 1 <= rating <= 5:
        raise ReviewError("invalid_rating", "La valutazione va da 1 a 5")
    body = (body or "").strip()
    if not BODY_MIN <= len(body) <= BODY_MAX:
        raise ReviewError(
            "invalid_body",
            f"La recensione deve avere tra {BODY_MIN} e {BODY_MAX} caratteri")
    author_name = (author_name or "").strip()[:NAME_MAX]
    if not author_name:
        raise ReviewError("invalid_name", "Serve un nome da mostrare")

    now_iso = _iso(utc_now())
    email_hash = _email_hash(email)
    existing = await reviews_collection.find_one(
        {"organization_id": org_id, "author_email_hash": email_hash},
        {"_id": 0, "id": 1, "created_at": 1})

    status = "published" if verified else "pending"
    doc = {
        "organization_id": org_id,
        "org_slug": org_slug,
        "author_email_hash": email_hash,
        "author_name": author_name,
        "rating": rating,
        "title": (title or "").strip()[:TITLE_MAX] or None,
        "body": body,
        "verified": verified,
        "status": status,
        "reply": None,                    # una nuova versione azzera la reply
        "lang": lang if lang in ("it", "en", "de", "fr") else "it",
        "updated_at": now_iso,
        "edited": bool(existing),
    }
    if existing:
        await reviews_collection.update_one(
            {"id": existing["id"]}, {"$set": doc})
        doc["id"] = existing["id"]
        doc["created_at"] = existing.get("created_at") or now_iso
    else:
        doc["id"] = generate_id()
        doc["created_at"] = now_iso
        await reviews_collection.insert_one({**doc})
    doc.pop("_id", None)

    await recompute_stats(org_id)
    return {k: v for k, v in doc.items() if k != "author_email_hash"}


# ── Stats ────────────────────────────────────────────────────────────────────

async def recompute_stats(org_id: str) -> Dict[str, Any]:
    """Denormalizza media/conteggio/distribuzione su organizations —
    chiamata a OGNI transizione di stato. Solo published contano."""
    from database import reviews_collection, organizations_collection

    dist = {str(i): 0 for i in range(1, 6)}
    total, count = 0, 0
    async for r in reviews_collection.find(
            {"organization_id": org_id, "status": "published"},
            {"_id": 0, "rating": 1}):
        dist[str(r["rating"])] = dist.get(str(r["rating"]), 0) + 1
        total += r["rating"]
        count += 1
    stats = {
        "avg": round(total / count, 2) if count else None,
        "count": count,
        "distribution": dist,
        "updated_at": _iso(utc_now()),
    }
    await organizations_collection.update_one(
        {"id": org_id}, {"$set": {"reviews_stats": stats}})
    return stats


# ── Letture ──────────────────────────────────────────────────────────────────

_PUBLIC_FIELDS = {"_id": 0, "id": 1, "author_name": 1, "rating": 1,
                  "title": 1, "body": 1, "verified": 1, "reply": 1,
                  "created_at": 1, "edited": 1, "lang": 1}


async def list_public(org_id: str, page: int = 1,
                      page_size: int = 10) -> Dict[str, Any]:
    from database import reviews_collection
    page = max(1, page)
    cursor = reviews_collection.find(
        {"organization_id": org_id, "status": "published"}, _PUBLIC_FIELDS,
    ).sort("created_at", -1).skip((page - 1) * page_size).limit(page_size)
    items = await cursor.to_list(page_size)
    total = await reviews_collection.count_documents(
        {"organization_id": org_id, "status": "published"})
    return {"items": items, "total": total, "page": page,
            "page_size": page_size}
