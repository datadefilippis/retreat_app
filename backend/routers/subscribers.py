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

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, EmailStr, Field

from core.marketing_unsubscribe_token import (TokenExpiredError,
                                              TokenInvalidError)
from core.subscriber_token import (decode_subscriber_token,
                                   generate_subscriber_token)
from auth import require_system_admin
from routers.auth import limiter

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Newsletter Aurya"])

SUBSCRIBER_FORMATS = ("all", "practices")
ALERT_SCOPES = ("italy", "regions")

# NW1 — interessi ESPERIENZIALI dell'iscritto (per le proposte di
# ritiri/esperienze): vocabolario suo, distinto dai topics editoriali
# del Magazine. "misto" = mi va bene un po' di tutto.
EXPERIENCE_INTERESTS = ("yoga", "meditazione", "breathwork", "reiki",
                        "costellazioni", "cerchi", "suono", "misto")
# NW1 — raggio di viaggio: vicino a casa o ovunque.
TRAVEL_OPTIONS = ("near", "anywhere")

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


def _clean_interests(raw) -> list:
    valid = set(EXPERIENCE_INTERESTS)
    return [i for i in dict.fromkeys(raw or []) if i in valid][:10]


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
    # NW1 — il flag «avvisami anche su esperienze e ritiri» e gli
    # interessi esperienziali del form espanso
    wants_experiences: Optional[bool] = None
    interests: Optional[list[str]] = Field(default=None, max_length=10)
    # BN3 — dal gate di una guida: dopo la conferma si torna li'
    return_to: Optional[str] = Field(default=None, max_length=200)
    consent: bool = False
    # 24/8 — il subscribe arriva da un CANCELLO di sblocco: il
    # gia'-confermato non riceve il magic link (la prova arriva
    # dalla chiamata unlock subito dopo)
    unlock_flow: Optional[bool] = False


class TokenPayload(BaseModel):
    token: str = Field(max_length=2000)


class PreferencesPayload(BaseModel):
    token: str = Field(max_length=2000)
    topics: Optional[list[str]] = Field(default=None, max_length=20)
    format: Optional[str] = Field(default=None, max_length=20)
    retreat_alert: Optional[dict] = None
    # NW1 — l'iscritto puo' vedere e cambiare anche il suo profilo
    # esperienziale (prima si scriveva al subscribe e spariva)
    interests: Optional[list[str]] = Field(default=None, max_length=10)
    city: Optional[str] = Field(default=None, max_length=120)
    travel: Optional[str] = Field(default=None, max_length=40)


def _decode_or_http(token: str) -> str:
    try:
        return decode_subscriber_token(token)["email"]
    except TokenExpiredError:
        raise HTTPException(status_code=410, detail="link scaduto")
    except TokenInvalidError:
        raise HTTPException(status_code=401, detail="link non valido")


# SB3 (20/8) — i cancelli da cui si parte per iscriversi: il link di
# conferma deve saper riportare a CIASCUNO di loro, sbloccato. Prima la
# whitelist conosceva solo il Magazine: chi si iscriveva dalle
# meditazioni riceveva un link che NON tornava li' (il return_to veniva
# scartato in silenzio) e atterrava su una pagina qualunque.
_RETURN_TO_OK = ("/blog/", "/meditazioni", "/frequenze/")


def _safe_return_to(raw: Optional[str]) -> Optional[str]:
    """Solo path interni dei cancelli noti: il next del link di
    conferma non deve mai diventare un open redirect."""
    p = (raw or "").strip()
    if "//" in p or not p.startswith("/"):
        return None
    return p if any(p == r.rstrip("/") or p.startswith(r)
                    for r in _RETURN_TO_OK) else None


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


def _send_access_email(email: str, name: Optional[str], token: str,
                       return_to: Optional[str] = None) -> None:
    """Magic link per l'iscritto GIA' confermato che rimette la email
    (es. da un nuovo dispositivo, davanti a una guida riservata): il
    click ri-salva il token nel browser e sblocca tutte le guide.
    Stesso disegno del double opt-in, copy diverso. Best-effort."""
    try:
        from urllib.parse import quote

        from services.email_service import (_link_block, _wrap_template,
                                            send_email)
        from services.url_builder import build_public_url
        url = build_public_url(f"/newsletter/conferma/{token}")
        if return_to:
            url += f"?next={quote(return_to, safe='')}"
        saluto = f"Ciao {name.strip()}," if (name or "").strip() else "Ciao,"
        dove = ("e tornare alla guida che stavi leggendo"
                if return_to else "su questo dispositivo")
        html = _wrap_template(f"""
            <p>{saluto}</p>
            <p>sei gia' dei nostri: questa email e' iscritta alla
            <strong>lettera di Aurya</strong>. Usa il bottone qui sotto per
            riaprire il tuo accesso {dove}: sblocca le guide riservate e la
            pagina delle preferenze, senza doverti iscrivere di nuovo.</p>
            <p style="text-align: center;">
                <a href="{url}" class="btn">Riapri il mio accesso</a>
            </p>
            {_link_block(url)}
            <p>Se non hai richiesto tu questo link, ignora l'email: nessuno
            puo' usare il tuo accesso senza aprire questo messaggio.</p>
        """)
        send_email(email, "Il tuo accesso alla lettera di Aurya",
                   html, bypass_gate=True)
    except Exception as exc:                # noqa: BLE001
        logger.warning("subscriber access email failed for %s: %s",
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
    # NW1 — il flag esperienze accende/spegne l'alert ritiri anche da
    # solo (il form progressivo non costruisce il dict retreat_alert)
    elif payload.wants_experiences is not None:
        doc_set["preferences.retreat_alert"] = _clean_alert(
            {"enabled": payload.wants_experiences})
    if payload.interests is not None:
        doc_set["profile.interests"] = _clean_interests(payload.interests)
    for field in ("city", "travel", "budget"):
        val = (getattr(payload, field) or "").strip()
        if val:
            if field == "travel" and val not in TRAVEL_OPTIONS:
                continue                     # NW1 — solo near/anywhere
            doc_set[f"profile.{field}"] = val[:120]

    try:
        existing = await db.aurya_subscribers.find_one(
            {"email": email}, {"_id": 0, "status": 1})
        if existing and existing.get("status") == "confirmed":
            await db.aurya_subscribers.update_one(
                {"email": email}, {"$set": doc_set})
            # Gia' confermato che rimette la email. DUE contesti diversi
            # (founder, 24/8): (a) un FORM della Lettera senza seguito →
            # magic link di accesso, come sempre; (b) un CANCELLO di
            # sblocco (guide, meditazioni: unlock_flow dal client) → la
            # prova arriva DALLA CHIAMATA UNLOCK un istante dopo, e
            # l'email era solo un costo con il copy sbagliato («parlava
            # di guide» sotto una meditazione). La risposta resta
            # identica: nessun oracolo di enumerazione.
            if not payload.unlock_flow:
                _send_access_email(email, payload.name,
                                   generate_subscriber_token(email),
                                   _safe_return_to(payload.return_to))
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
    except Exception as exc:                # noqa: BLE001
        # NW1 — un errore di scrittura NON deve svanire in un finto ok:
        # l'iscrizione andrebbe persa in silenzio. Meglio un errore
        # onesto che il form puo' mostrare («riprova tra poco»).
        logger.error("subscriber save failed: %s", exc)
        raise HTTPException(status_code=503,
                            detail="Non riusciamo a salvarti ora, riprova")

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
    from services.subscriber_brevo_sync import sync_subscriber_background
    sync_subscriber_background(email)     # BN6 — riflesso su Brevo
    return {"ok": True, "status": "confirmed"}


class UnlockPayload(BaseModel):
    email: EmailStr


@router.post("/public/newsletter/unlock")
@limiter.limit("10/minute")
async def unlock_for_subscriber(request: Request, payload: UnlockPayload):
    """NL-septies (20/8, founder) — «sono gia' iscritto, perche' devo
    iscrivermi di nuovo?».

    Chi e' gia' iscritto CONFERMATO e apre un contenuto riservato da un
    altro browser (o mesi dopo, con la memoria del browser pulita) non
    deve rifare l'iscrizione: dichiara l'indirizzo e riprende il suo
    lasciapassare. Stesso patto gia' in uso per le meditazioni
    (/frequencies/catalog/unlock): il contenuto e' gratuito e
    l'iscrizione pure, quindi il fattore che conta e' non far ripetere
    un gesto gia' fatto.

    Email non iscritta o non confermata → 404 onesto: la pagina invita
    a iscriversi, che e' esattamente cio' che serve in quel caso.
    """
    from database import db

    email = (payload.email or "").strip().lower()
    doc = await db.aurya_subscribers.find_one(
        {"email": email}, {"_id": 0, "status": 1})
    if not doc or doc.get("status") != "confirmed":
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Questo indirizzo non risulta iscritto e confermato.")
    from core.subscriber_token import generate_subscriber_token
    return {"subscriber_token": generate_subscriber_token(email)}


@router.get("/admin/newsletter-stats")
async def newsletter_stats(
        current_user: dict = Depends(require_system_admin)):
    """BN6 — il polso della lettera per il system admin: iscritti per
    stato/fonte/tema, tasso di conferma, crescita 8 settimane."""
    from datetime import timedelta

    from database import db

    by_status: dict = {}
    async for row in db.aurya_subscribers.aggregate(
            [{"$group": {"_id": "$status", "n": {"$sum": 1}}}]):
        by_status[row["_id"] or "pending"] = row["n"]

    by_source = [
        {"source": r["_id"] or "(sconosciuta)", "n": r["n"]}
        async for r in db.aurya_subscribers.aggregate([
            {"$group": {"_id": "$source", "n": {"$sum": 1}}},
            {"$sort": {"n": -1}}, {"$limit": 15}])]

    by_topic = [
        {"topic": r["_id"], "n": r["n"]}
        async for r in db.aurya_subscribers.aggregate([
            {"$unwind": "$preferences.topics"},
            {"$group": {"_id": "$preferences.topics", "n": {"$sum": 1}}},
            {"$sort": {"n": -1}}])]

    now = datetime.now(timezone.utc)
    weekly = []
    for i in range(7, -1, -1):
        start = now - timedelta(weeks=i + 1)
        end = now - timedelta(weeks=i)
        n = await db.aurya_subscribers.count_documents(
            {"created_at": {"$gte": start, "$lt": end}})
        weekly.append({"week_start": start.date().isoformat(), "n": n})

    total = sum(by_status.values())
    confirmed = by_status.get("confirmed", 0)
    return {
        "total": total,
        "by_status": by_status,
        "confirm_rate": round(confirmed / total, 3) if total else 0.0,
        "by_source": by_source,
        "by_topic": by_topic,
        "weekly_new": weekly,
    }


@router.get("/admin/subscribers")
async def list_subscribers(
        status: Optional[str] = None,
        source: Optional[str] = None,
        q: Optional[str] = None,
        experiences: Optional[str] = None,
        skip: int = 0,
        limit: int = 50,
        current_user: dict = Depends(require_system_admin)):
    """NW3 — la lista iscritti che mancava: ogni riga con FONTE, stato,
    preferenze esperienziali e date. La fonte c'e' sempre: e' il modo
    in cui l'admin sa da dove arriva ogni persona."""
    from database import db

    query: dict = {}
    if status in ("pending", "confirmed", "unsubscribed"):
        query["status"] = status
    if source:
        query["source"] = source[:60]
    if q:
        import re as _re
        query["email"] = {"$regex": _re.escape(q.strip()[:80]), "$options": "i"}
    if experiences == "yes":
        query["preferences.retreat_alert.enabled"] = True

    limit = max(1, min(int(limit or 50), 200))
    skip = max(0, int(skip or 0))
    total = await db.aurya_subscribers.count_documents(query)
    rows = []
    async for d in (db.aurya_subscribers
                    .find(query, {"_id": 0, "email": 1, "name": 1,
                                  "status": 1, "source": 1, "language": 1,
                                  "created_at": 1, "confirmed_at": 1,
                                  "unsubscribed_at": 1, "preferences": 1,
                                  "profile": 1})
                    .sort("created_at", -1).skip(skip).limit(limit)):
        prefs = d.get("preferences") or {}
        profile = d.get("profile") or {}
        rows.append({
            "email": d["email"],
            "name": d.get("name"),
            "status": d.get("status") or "pending",
            "source": d.get("source") or "(sconosciuta)",
            "language": d.get("language"),
            "created_at": d.get("created_at"),
            "confirmed_at": d.get("confirmed_at"),
            "unsubscribed_at": d.get("unsubscribed_at"),
            "wants_experiences": bool(
                (prefs.get("retreat_alert") or {}).get("enabled")),
            "interests": _clean_interests(profile.get("interests")),
            "city": profile.get("city"),
            "travel": profile.get("travel"),
        })
    return {"total": total, "skip": skip, "limit": limit, "rows": rows}


@router.get("/public/newsletter/preferences/{token}")
async def get_preferences(token: str):
    from database import db

    email = _decode_or_http(token)
    doc = await db.aurya_subscribers.find_one(
        {"email": email},
        {"_id": 0, "status": 1, "preferences": 1, "profile": 1}) or {}
    prefs = doc.get("preferences") or {}
    profile = doc.get("profile") or {}
    return {
        "email_masked": _mask_email(email),
        "status": doc.get("status") or "pending",
        "topics": _clean_topics(prefs.get("topics")),
        "format": (prefs.get("format")
                   if prefs.get("format") in SUBSCRIBER_FORMATS else "all"),
        "retreat_alert": _clean_alert(prefs.get("retreat_alert")),
        # NW1 — profilo esperienziale, visibile e modificabile
        "interests": _clean_interests(profile.get("interests")),
        "city": profile.get("city") or "",
        "travel": (profile.get("travel")
                   if profile.get("travel") in TRAVEL_OPTIONS else ""),
        "available_topics": list(subscriber_topics()),
        "available_regions": list(ITALIAN_REGIONS),
        "available_interests": list(EXPERIENCE_INTERESTS),
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
    if payload.interests is not None:
        doc_set["profile.interests"] = _clean_interests(payload.interests)
    if payload.city is not None:
        doc_set["profile.city"] = payload.city.strip()[:120]
    if payload.travel is not None and payload.travel in TRAVEL_OPTIONS:
        doc_set["profile.travel"] = payload.travel
    await db.aurya_subscribers.update_one({"email": email}, {"$set": doc_set})
    from services.subscriber_brevo_sync import sync_subscriber_background
    sync_subscriber_background(email)     # BN6 — attributi aggiornati
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
    from services.subscriber_brevo_sync import sync_subscriber_background
    sync_subscriber_background(email)     # BN6 — blacklist su Brevo
    return {"ok": True, "status": "unsubscribed"}
