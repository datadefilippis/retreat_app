"""BN2 — la lettera di Aurya: iscritti con double opt-in e preferenze.

docs/BLOG_NEWSLETTER_STRATEGIA_2026-07.md. Collection `aurya_subscribers`
(nome volutamente DIVERSO da `newsletter_subscriptions`, che e' il
modulo per-org degli operatori: due binari che non si toccano).

Ciclo di vita (status): pending → confirmed → unsubscribed (→ pending
se si re-iscrive). Il double opt-in e' la prova del consenso GDPR:
al subscribe parte l'email di conferma (Brevo) con un link firmato;
solo il click porta a confirmed. Lo STESSO token serve poi la pagina
preferenze e l'unsubscribe a un click (Art. 7(3): revocare facile
quanto dare).

Preferenze strutturate (si raccolgono ora, si usano al flip):
  topics[]        categorie editoriali (ARTICLE_CATEGORIES senza
                  'operatori': il B2B converte alla rete, non qui)
  format          all | practices (solo pratiche ed esercizi)
  retreat_alert   {enabled, scope: italy|regions, regions[]} —
                  DORMIENTE in fase rete: nessun invio finche' il
                  marketplace non apre (onesta' dichiarata nel form).

Risposte volutamente generiche sul subscribe: mai rivelare se una
email e' gia' iscritta (niente oracolo di enumerazione).
"""

import logging
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, EmailStr, Field

from core.marketing_unsubscribe_token import (TokenExpiredError,
                                              TokenInvalidError)
from core.subscriber_token import (decode_subscriber_token,
                                   generate_subscriber_token)
from routers.auth import limiter

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Newsletter Aurya"])

SUBSCRIBER_FORMATS = ("all", "practices")
ALERT_SCOPES = ("italy", "regions")

# Le 20 regioni italiane: le zone dell'alert ritiri (stessa geografia
# della directory). Slug stabili minuscoli, label lato frontend.
ITALIAN_REGIONS = (
    "abruzzo", "basilicata", "calabria", "campania", "emilia-romagna",
    "friuli-venezia-giulia", "lazio", "liguria", "lombardia", "marche",
    "molise", "piemonte", "puglia", "sardegna", "sicilia", "toscana",
    "trentino-alto-adige", "umbria", "valle-d-aosta", "veneto",
)


def subscriber_topics() -> tuple:
    """Categorie iscrivibili: tutte le editoriali tranne 'operatori'."""
    from models.article import ARTICLE_CATEGORIES
    return tuple(k for k in ARTICLE_CATEGORIES if k != "operatori")


def _clean_topics(raw) -> list:
    valid = set(subscriber_topics())
    return [t for t in dict.fromkeys(raw or []) if t in valid][:20]


def _clean_alert(raw: Optional[dict]) -> dict:
    raw = raw or {}
    scope = raw.get("scope") if raw.get("scope") in ALERT_SCOPES else "italy"
    regions = [r for r in dict.fromkeys(raw.get("regions") or [])
               if r in ITALIAN_REGIONS][:20]
    return {"enabled": bool(raw.get("enabled")), "scope": scope,
            "regions": regions}


def _mask_email(email: str) -> str:
    local, _, domain = (email or "").partition("@")
    if len(local) <= 2:
        return f"{local[:1]}***@{domain}"
    return f"{local[0]}***{local[-1]}@{domain}"


class SubscribePayload(BaseModel):
    email: EmailStr
    name: Optional[str] = Field(default=None, max_length=120)
    language: Optional[str] = Field(default=None, max_length=5)
    # sorgente per attribuzione (blog_{categoria}, newsletter, gate...)
    source: Optional[str] = Field(default=None, max_length=60)
    topics: Optional[list[str]] = Field(default=None, max_length=20)
    format: Optional[str] = Field(default=None, max_length=20)
    retreat_alert: Optional[dict] = None
    # profilo facoltativo (dalla landing /newsletter col form pieno)
    city: Optional[str] = Field(default=None, max_length=120)
    travel: Optional[str] = Field(default=None, max_length=40)
    budget: Optional[str] = Field(default=None, max_length=40)
    # BN3 — dal gate di una guida: dopo la conferma si torna li'
    return_to: Optional[str] = Field(default=None, max_length=200)
    consent: bool = False


class TokenPayload(BaseModel):
    token: str = Field(max_length=2000)


class PreferencesPayload(BaseModel):
    token: str = Field(max_length=2000)
    topics: Optional[list[str]] = Field(default=None, max_length=20)
    format: Optional[str] = Field(default=None, max_length=20)
    retreat_alert: Optional[dict] = None


def _decode_or_http(token: str) -> str:
    try:
        return decode_subscriber_token(token)["email"]
    except TokenExpiredError:
        raise HTTPException(status_code=410, detail="link scaduto")
    except TokenInvalidError:
        raise HTTPException(status_code=401, detail="link non valido")


def _safe_return_to(raw: Optional[str]) -> Optional[str]:
    """Solo path interni del Magazine: il next del link di conferma non
    deve mai diventare un open redirect."""
    p = (raw or "").strip()
    return p if p.startswith("/blog/") and "//" not in p else None


def _send_confirm_email(email: str, name: Optional[str], token: str,
                        return_to: Optional[str] = None) -> None:
    """Email di double opt-in, brandizzata col template comune. Best
    effort: un errore email non deve mai rompere il form."""
    try:
        from urllib.parse import quote

        from services.email_service import (_link_block, _wrap_template,
                                            send_email)
        from services.url_builder import build_public_url
        url = build_public_url(f"/newsletter/conferma/{token}")
        if return_to:
            url += f"?next={quote(return_to, safe='')}"
        saluto = f"Ciao {name.strip()}," if (name or "").strip() else "Ciao,"
        html = _wrap_template(f"""
            <p>{saluto}</p>
            <p>manca un solo passo: conferma la tua iscrizione alla
            <strong>lettera di Aurya</strong>. Ogni due settimane una pratica
            raccontata bene e una persona della rete. Niente rumore, mai spam.</p>
            <p style="text-align: center;">
                <a href="{url}" class="btn">Confermo l'iscrizione</a>
            </p>
            {_link_block(url)}
            <p>Se non ti sei iscritto tu, ignora questa email: senza
            conferma non riceverai nulla.</p>
        """)
        send_email(email, "Conferma la tua iscrizione alla lettera di Aurya",
                   html, bypass_gate=True)
    except Exception as exc:                # noqa: BLE001
        logger.warning("subscriber confirm email failed for %s: %s",
                       _mask_email(email), exc)


@router.post("/public/newsletter/subscribe", status_code=201)
@limiter.limit("10/minute")
async def subscribe(request: Request, payload: SubscribePayload):
    """Iscrizione (o aggiornamento) alla lettera. Upsert per email;
    nuovo o non confermato → parte l'email di double opt-in."""
    from database import db

    email = payload.email.lower().strip()
    now = datetime.now(timezone.utc)

    doc_set = {
        "name": (payload.name or "").strip()[:120] or None,
        "language": (payload.language or "")[:5] or None,
        "source": (payload.source or "").strip()[:60] or None,
        "consent": bool(payload.consent),
        "consent_at": now,
        "updated_at": now,
    }
    # preferenze: si scrivono solo se il form le manda (il compact del
    # blog manda solo l'email: non azzeriamo quelle esistenti)
    if payload.topics is not None:
        doc_set["preferences.topics"] = _clean_topics(payload.topics)
    if payload.format in SUBSCRIBER_FORMATS:
        doc_set["preferences.format"] = payload.format
    if payload.retreat_alert is not None:
        doc_set["preferences.retreat_alert"] = _clean_alert(payload.retreat_alert)
    for field in ("city", "travel", "budget"):
        val = (getattr(payload, field) or "").strip()
        if val:
            doc_set[f"profile.{field}"] = val[:120]

    try:
        existing = await db.aurya_subscribers.find_one(
            {"email": email}, {"_id": 0, "status": 1})
        if existing and existing.get("status") == "confirmed":
            await db.aurya_subscribers.update_one(
                {"email": email}, {"$set": doc_set})
            return {"ok": True}
        # nuovo, pending o unsubscribed (re-optin) → (ri)parte la conferma
        doc_set["status"] = "pending"
        set_on_insert = {"email": email, "created_at": now}
        if "preferences.topics" not in doc_set:
            set_on_insert["preferences.topics"] = []
        await db.aurya_subscribers.update_one(
            {"email": email},
            {"$set": doc_set, "$setOnInsert": set_on_insert},
            upsert=True,
        )
    except Exception as exc:                # noqa: BLE001 — mai rompere il form
        logger.warning("subscriber save failed: %s", exc)
        return {"ok": True}

    _send_confirm_email(email, payload.name,
                        generate_subscriber_token(email),
                        _safe_return_to(payload.return_to))
    return {"ok": True}


@router.post("/public/newsletter/confirm")
@limiter.limit("30/minute")
async def confirm(request: Request, payload: TokenPayload):
    """Il click nell'email: pending → confirmed (idempotente). Ritorna
    il token stesso come chiave della pagina preferenze."""
    from database import db

    email = _decode_or_http(payload.token)
    now = datetime.now(timezone.utc)
    await db.aurya_subscribers.update_one(
        {"email": email},
        {"$set": {"status": "confirmed", "confirmed_at": now,
                  "updated_at": now},
         "$setOnInsert": {"email": email, "created_at": now,
                          "consent": True, "consent_at": now,
                          "preferences.topics": []}},
        upsert=True,
    )
    return {"ok": True, "status": "confirmed"}


@router.get("/public/newsletter/preferences/{token}")
async def get_preferences(token: str):
    from database import db

    email = _decode_or_http(token)
    doc = await db.aurya_subscribers.find_one(
        {"email": email}, {"_id": 0, "status": 1, "preferences": 1}) or {}
    prefs = doc.get("preferences") or {}
    return {
        "email_masked": _mask_email(email),
        "status": doc.get("status") or "pending",
        "topics": _clean_topics(prefs.get("topics")),
        "format": (prefs.get("format")
                   if prefs.get("format") in SUBSCRIBER_FORMATS else "all"),
        "retreat_alert": _clean_alert(prefs.get("retreat_alert")),
        "available_topics": list(subscriber_topics()),
        "available_regions": list(ITALIAN_REGIONS),
    }


@router.put("/public/newsletter/preferences")
@limiter.limit("30/minute")
async def update_preferences(request: Request, payload: PreferencesPayload):
    from database import db

    email = _decode_or_http(payload.token)
    now = datetime.now(timezone.utc)
    doc_set = {"updated_at": now}
    if payload.topics is not None:
        doc_set["preferences.topics"] = _clean_topics(payload.topics)
    if payload.format in SUBSCRIBER_FORMATS:
        doc_set["preferences.format"] = payload.format
    if payload.retreat_alert is not None:
        doc_set["preferences.retreat_alert"] = _clean_alert(payload.retreat_alert)
    await db.aurya_subscribers.update_one({"email": email}, {"$set": doc_set})
    return {"ok": True}


@router.post("/public/newsletter/unsubscribe")
@limiter.limit("30/minute")
async def unsubscribe(request: Request, payload: TokenPayload):
    """Un click, mai discussioni (GDPR Art. 7(3)). Idempotente."""
    from database import db

    email = _decode_or_http(payload.token)
    now = datetime.now(timezone.utc)
    await db.aurya_subscribers.update_one(
        {"email": email},
        {"$set": {"status": "unsubscribed", "unsubscribed_at": now,
                  "updated_at": now},
         "$setOnInsert": {"email": email, "created_at": now}},
        upsert=True,
    )
    return {"ok": True, "status": "unsubscribed"}
