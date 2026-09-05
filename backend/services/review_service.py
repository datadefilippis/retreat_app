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

    # RV3 (founder, 5/9/2026): «se l'operatore ha disabilitato le
    # recensioni da chi non ha ordinato, chi non ha ordinato non deve
    # nemmeno ricevere l'email». La porta si chiude QUI, prima del
    # codice: se l'organizzazione accetta solo clienti e questa email
    # non ha prenotazioni, niente codice — arriva una riga di cortesia
    # che dice la cura (usa l'email della prenotazione). La risposta
    # HTTP resta 202 per tutti: verso l'esterno non trapela nulla, la
    # verita' la legge solo il proprietario della casella.
    try:
        from routers.public import _resolve_org
        org = await _resolve_org(org_slug)
    except Exception:
        return                                   # org non pubblica: silenzio
    if not await _org_accetta(org, email_n):
        _send_review_closed_email(email_n, org, locale)
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


def _otp_base(org_slug: str, email: str) -> Dict[str, Any]:
    return {
        "org_slug": org_slug,
        "email_hash": _email_hash(email),
        "used_at": None,
        "expires_at": {"$gt": _iso(utc_now())},
        "attempts": {"$lt": OTP_MAX_ATTEMPTS},
    }


async def _peek_otp(org_slug: str, email: str, code: str) -> bool:
    """IG5 (3/9/2026) — verifica SENZA consumare: il codice si brucia
    solo a recensione accettata. Prima si consumava subito e chi
    inciampava in una regola successiva («solo chi ha prenotato», testo
    troppo corto) doveva chiedere un codice nuovo. Il tentativo
    sbagliato conta comunque verso il lockout."""
    from database import review_otps_collection

    ok = await review_otps_collection.find_one(
        {**_otp_base(org_slug, email), "code_hash": _hash_code(code or "")},
        {"_id": 1})
    if ok:
        return True
    await review_otps_collection.update_many(
        _otp_base(org_slug, email), {"$inc": {"attempts": 1}})
    return False


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


async def _org_accetta(org: Dict[str, Any], email_n: str) -> bool:
    """Vero se questa email puo' recensire l'organizzazione: ha un
    ordine, oppure l'organizzazione accetta anche chi non ha prenotato."""
    from database import organizations_collection
    if await has_orders_with_org(org["id"], email_n):
        return True
    org_doc = await organizations_collection.find_one(
        {"id": org["id"]}, {"_id": 0, "reviews_open": 1})
    return bool((org_doc or {}).get("reviews_open"))


def _nome_org(org: Dict[str, Any]) -> str:
    return (org.get("name") or org.get("public_slug") or org.get("slug")
            or "questo professionista")


def _send_review_closed_email(email: str, org: Dict[str, Any],
                              locale: str) -> None:
    """La riga di cortesia al posto del codice (RV3): nessuna
    prenotazione con questa email, le recensioni sono riservate a chi
    ha prenotato."""
    from services.email_service import send_email, _wrap_template
    nome = _nome_org(org)
    content = f"""
    <p>Ciao,</p>
    <p>hai chiesto di recensire <b>{nome}</b> su Aurya, ma con questa
    email non risulta nessuna prenotazione: le recensioni di questo
    professionista sono riservate a chi ha prenotato con lui.</p>
    <p>Se hai prenotato con un&rsquo;altra email, riprova con quella:
    il codice arriva l&igrave;.</p>
    """
    try:
        send_email(email, f"Recensione per {nome}: serve l’email della prenotazione",
                   _wrap_template(content, locale), bypass_gate=True)
    except Exception:
        logger.exception("email di cortesia recensione non inviata")


def _base_url() -> str:
    return (os.environ.get("PUBLIC_BASE_URL") or os.environ.get("FRONTEND_URL")
            or "https://aurya.life").rstrip("/")


async def _operator_recipient(org_id: str) -> Optional[str]:
    """Chi riceve le email del professionista: notification_email dello
    store, poi il primo admin attivo (stessa risoluzione delle email
    di quota). Proiezione a lista: la guardia RB2 vieta il letterale
    `"email":` vicino alla proiezione pubblica, e ha ragione."""
    from database import organizations_collection, users_collection
    org_doc = await organizations_collection.find_one(
        {"id": org_id}, {"_id": 0, "store_settings": 1}) or {}
    to = (org_doc.get("store_settings") or {}).get("notification_email")
    if not to:
        admin = await users_collection.find_one(
            {"organization_id": org_id, "role": {"$in": ["admin"]},
             "is_active": True},
            ["email"], sort=[("created_at", 1)])
        to = (admin or {}).get("email")
    return to


def _bottone(link: str, testo: str) -> str:
    return (f'<p><a href="{link}" style="display:inline-block;background:#2f5e58;'
            f'color:#fff;padding:10px 18px;border-radius:999px;text-decoration:none">'
            f'{testo}</a></p>')


def _send_reviewer_receipt(email: str, org: Dict[str, Any],
                           review: Dict[str, Any], locale: str = "it") -> None:
    """RV (5/9): chi scrive non si perde. L'email in chiaro esiste solo
    ADESSO, al submit (a DB resta l'hash): e' l'unico momento in cui si
    puo' dire «grazie, e' pubblica» o «e' in attesa del professionista».
    Le tappe successive (approvazione, risposta) non possono
    raggiungerlo senza un consenso a conservare l'email (RV6, decisione
    del founder)."""
    from services.email_service import send_email, _wrap_template
    nome = _nome_org(org)
    slug = org.get("public_slug") or org.get("slug") or review.get("org_slug")
    link = f"{_base_url()}/o/{slug}#recensioni"
    if review.get("verified"):
        subject = f"La tua recensione per {nome} è pubblica"
        content = f"""
        <p>Grazie: la tua recensione per <b>{nome}</b> &egrave; gi&agrave;
        visibile sul suo profilo, con il badge «Cliente verificato».
        Se il professionista risponde, la risposta comparir&agrave;
        sotto la tua recensione.</p>
        {_bottone(link, 'Vedi la tua recensione')}
        """
    else:
        subject = f"Recensione per {nome} ricevuta: in attesa di approvazione"
        content = f"""
        <p>Grazie: la tua recensione per <b>{nome}</b> &egrave; arrivata.
        Con questa email non risulta una prenotazione, quindi la
        legger&agrave; prima il professionista: se la approva, comparir&agrave;
        sul suo profilo senza il badge «Cliente verificato».</p>
        {_bottone(link, 'Vai al profilo')}
        """
    try:
        send_email(email, subject, _wrap_template(content, locale), bypass_gate=True)
    except Exception:
        logger.exception("ricevuta recensione non inviata")


async def _notify_operator_new_review(org_id: str, review: Dict[str, Any]) -> None:
    """RV2 (5/9/2026): il professionista lo viene a sapere. Una email
    per recensione all'admin dell'organizzazione. Verificata → e' gia'
    pubblica, «rispondi»; non verificata → «aspetta la tua
    approvazione». Best-effort: un fallimento qui non tocca la
    recensione."""
    from services.email_service import send_email, _wrap_template
    try:
        to = await _operator_recipient(org_id)
        if not to:
            logger.warning("review notify: nessun destinatario per org=%s", org_id)
            return
        base = _base_url()
        stelle = "★" * int(review.get("rating") or 0)
        autore = review.get("author_name") or "Un cliente"
        estratto = (review.get("body") or "")[:240]
        if review.get("verified"):
            subject = f"Nuova recensione da {autore} ({stelle})"
            testa = ("Una persona che ha prenotato con te ha lasciato una "
                     "recensione: &egrave; gi&agrave; pubblica sul tuo profilo. "
                     "Puoi rispondere dal gestionale.")
            link = f"{base}/reviews"
        else:
            subject = f"Una recensione aspetta la tua approvazione ({stelle})"
            testa = ("Una persona che non risulta fra le tue prenotazioni ha "
                     "scritto una recensione: resta in attesa finch&eacute; "
                     "non la approvi o la rifiuti.")
            link = f"{base}/reviews?status=pending"
        content = f"""
        <p>Ciao,</p>
        <p>{testa}</p>
        <p style="margin:14px 0 4px"><b>{autore}</b> · {stelle}</p>
        <p style="color:#3b4440;border-left:3px solid #c9b37e;padding-left:12px">{estratto}</p>
        <p><a href="{link}" style="display:inline-block;background:#2f5e58;color:#fff;
        padding:10px 18px;border-radius:999px;text-decoration:none">Vai alle recensioni</a></p>
        """
        send_email(to, subject, _wrap_template(content, "it"), bypass_gate=True)
    except Exception:
        logger.exception("review notify: email al professionista non inviata")


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

    # IG5 — prima si GUARDA il codice (prova di possesso dell'email: da
    # qui in poi si puo' dire se quell'email ha prenotato), lo si
    # CONSUMA solo a recensione accettata, in fondo.
    if not await _peek_otp(org_slug, email, code):
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

    # tutto valido: ORA il codice si brucia (atomico: due submit
    # concorrenti con lo stesso codice non passano entrambi)
    if not await _consume_otp(org_slug, email, code):
        raise ReviewError("invalid_code", "Codice non valido o scaduto")

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
    await _notify_operator_new_review(org_id, doc)      # RV2, best-effort
    _send_reviewer_receipt(email, org, doc, lang)       # chi scrive sa dov'e'
    return {k: v for k, v in doc.items() if k != "author_email_hash"}


# ── Segnalazioni: operatore → piattaforma → operatore (RV5) ──────────────────

async def flag_review(org_id: str, review_id: str, reason: Optional[str],
                      by_email: Optional[str] = None) -> bool:
    """L'operatore segnala: la recensione esce dal pubblico e va nella
    CODA della piattaforma (system admin), che decide. Prima (PR3) era
    un log e basta: nessuno la rileggeva. Chi la revisiona lo sa via
    email (ADMIN_EMAIL), l'operatore vede «in revisione» nella sua tab."""
    from database import reviews_collection, organizations_collection
    from services.email_service import send_email, _wrap_template, ADMIN_EMAIL
    now_iso = _iso(utc_now())
    res = await reviews_collection.update_one(
        {"id": review_id, "organization_id": org_id, "status": "published"},
        {"$set": {"status": "flagged", "flagged_at": now_iso,
                  "flag_reason": (reason or "").strip()[:500] or None,
                  "flagged_by": by_email, "resolution": None}},
    )
    if res.matched_count == 0:
        return False
    await recompute_stats(org_id)
    try:
        org = await organizations_collection.find_one(
            {"id": org_id}, {"_id": 0, "name": 1, "public_slug": 1, "slug": 1}) or {}
        r = await reviews_collection.find_one(
            {"id": review_id}, {"_id": 0, "author_email_hash": 0}) or {}
        content = f"""
        <p><b>{_nome_org(org)}</b> ha segnalato una recensione come abuso.</p>
        <p><b>{r.get('author_name')}</b> · {'★' * int(r.get('rating') or 0)}</p>
        <p style="color:#3b4440;border-left:3px solid #c9b37e;padding-left:12px">{(r.get('body') or '')[:600]}</p>
        <p>Motivo: {r.get('flag_reason') or 'non indicato'}</p>
        {_bottone(_base_url() + '/admin?tab=reviews', 'Apri la coda delle segnalazioni')}
        """
        send_email(ADMIN_EMAIL, f"Recensione segnalata da {_nome_org(org)}",
                   _wrap_template(content, "it"), bypass_gate=True)
    except Exception:
        logger.exception("segnalazione: email alla piattaforma non inviata")
    return True


async def list_flagged() -> Dict[str, Any]:
    """La coda del system admin: tutte le segnalate, con il nome
    dell'organizzazione, dalla piu' vecchia."""
    from database import reviews_collection, organizations_collection
    items = await reviews_collection.find(
        {"status": "flagged"}, {"_id": 0, "author_email_hash": 0},
    ).sort("flagged_at", 1).to_list(200)
    org_ids = list({r["organization_id"] for r in items})
    nomi = {}
    async for o in organizations_collection.find(
            {"id": {"$in": org_ids}}, {"_id": 0, "id": 1, "name": 1, "public_slug": 1}):
        nomi[o["id"]] = o
    for r in items:
        o = nomi.get(r["organization_id"], {})
        r["org_name"] = o.get("name")
        r["org_public_slug"] = o.get("public_slug")
    return {"items": items, "total": len(items)}


async def resolve_flag(review_id: str, action: str, note: Optional[str],
                       by_email: Optional[str]) -> Optional[str]:
    """La piattaforma decide: `restore` la ripubblica, `remove` la
    toglie per sempre (resta a DB per l'audit). In entrambi i casi il
    professionista riceve l'esito via email: nessuna segnalazione
    finisce nel vuoto."""
    from database import reviews_collection
    from services.email_service import send_email, _wrap_template
    if action not in ("restore", "remove"):
        return None
    new_status = "published" if action == "restore" else "removed"
    now_iso = _iso(utc_now())
    r = await reviews_collection.find_one_and_update(
        {"id": review_id, "status": "flagged"},
        {"$set": {"status": new_status,
                  "resolution": {"action": action, "note": (note or "").strip()[:500] or None,
                                 "at": now_iso, "by": by_email}}},
    )
    if not r:
        return None
    org_id = r["organization_id"]
    await recompute_stats(org_id)
    try:
        to = await _operator_recipient(org_id)
        if to:
            if action == "restore":
                subject = "Segnalazione esaminata: la recensione torna pubblica"
                testa = ("Abbiamo esaminato la recensione che avevi segnalato e non "
                         "abbiamo trovato una violazione: torna visibile sul tuo "
                         "profilo. Puoi sempre risponderle pubblicamente.")
            else:
                subject = "Segnalazione accolta: la recensione è stata rimossa"
                testa = ("Abbiamo esaminato la recensione che avevi segnalato e "
                         "l'abbiamo rimossa dal tuo profilo.")
            nota = f"<p>Nota di Aurya: {r['resolution']['note']}</p>" if note else ""
            content = f"""
            <p>Ciao,</p><p>{testa}</p>
            <p><b>{r.get('author_name')}</b> · {'★' * int(r.get('rating') or 0)}</p>
            <p style="color:#3b4440;border-left:3px solid #c9b37e;padding-left:12px">{(r.get('body') or '')[:240]}</p>
            {nota}
            {_bottone(_base_url() + '/reviews', 'Vai alle recensioni')}
            """
            send_email(to, subject, _wrap_template(content, "it"), bypass_gate=True)
    except Exception:
        logger.exception("esito segnalazione: email al professionista non inviata")
    return new_status


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
