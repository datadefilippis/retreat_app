"""Platform account service — magic-link auth per il marketplace (P1).

Piano: docs/PLATFORM_ACCOUNT_PLAN.md. Regole di sicurezza:
  - enumeration-safe: request_magic_link risponde SEMPRE allo stesso modo
    (l'endpoint restituisce 202), che l'email esista o no
  - token magic: 32 byte urlsafe, salvato SOLO hashed (sha256), TTL 15',
    one-shot (used_at marcato ATOMICAMENTE con $eq None — due click sullo
    stesso link non emettono due sessioni)
  - il consumo del token verifica l'email (email_verified=True): il
    magic link E' la verifica
  - find-or-create dell'account alla richiesta: l'account "nasce" pending
    e diventa reale solo quando il link viene usato
"""

import hashlib
import logging
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

from models.common import utc_now
from models.platform_account import MagicLinkToken, PlatformAccount

logger = logging.getLogger(__name__)

MAGIC_TOKEN_TTL_MINUTES = 15


def _normalize_email(email: str) -> str:
    return (email or "").strip().lower()


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _iso(dt: datetime) -> str:
    return dt.isoformat()


async def find_account_by_email(email: str) -> Optional[Dict[str, Any]]:
    from database import platform_accounts_collection
    return await platform_accounts_collection.find_one(
        {"email": _normalize_email(email)}, {"_id": 0},
    )


async def get_account(account_id: str) -> Optional[Dict[str, Any]]:
    from database import platform_accounts_collection
    return await platform_accounts_collection.find_one(
        {"id": account_id}, {"_id": 0},
    )


async def request_magic_link(email: str, *, name: Optional[str] = None,
                             language: Optional[str] = None) -> None:
    """Find-or-create account + emette il magic link via email.

    NON ritorna nulla e non solleva per email malformate/duplicate:
    l'endpoint risponde sempre 202 (enumeration-safe). Gli errori interni
    vengono loggati, mai esposti.

    R2a — ``language`` e' la lingua UI del frontend al momento della
    richiesta (None = client legacy che non la manda). Quando valida:
    viene salvata come preferenza dell'account (il viaggiatore che cambia
    lingua nel marketplace cambia anche la lingua delle sue email) e
    l'email OTP parte in quella lingua. Altrimenti si usa la lingua gia'
    sull'account, con fallback it.
    """
    from database import (
        platform_accounts_collection,
        platform_magic_tokens_collection,
    )

    email_n = _normalize_email(email)
    if not email_n or "@" not in email_n:
        return

    lang_n = language if language in ("it", "en", "de", "fr") else None

    account = await platform_accounts_collection.find_one({"email": email_n})
    if not account:
        doc = PlatformAccount(email=email_n, name=name,
                              language=lang_n or "it").model_dump()
        for f in ("created_at", "last_login_at", "sessions_invalidated_at"):
            if isinstance(doc.get(f), datetime):
                doc[f] = _iso(doc[f])
        await platform_accounts_collection.insert_one(doc)
        account = doc
    elif lang_n and account.get("language") != lang_n:
        await platform_accounts_collection.update_one(
            {"id": account["id"]}, {"$set": {"language": lang_n}},
        )
        account["language"] = lang_n

    # token in chiaro SOLO nell'email; a DB va l'hash. Stessa email,
    # DUE strade: codice a 6 cifre (immediato, si digita sul posto) e
    # link (fallback classico).
    token = secrets.token_urlsafe(32)
    code = f"{secrets.randbelow(1_000_000):06d}"
    t = MagicLinkToken(
        account_id=account["id"],
        token_hash=_hash_token(token),
        code_hash=_hash_token(code),
        expires_at=utc_now() + timedelta(minutes=MAGIC_TOKEN_TTL_MINUTES),
    )
    tdoc = t.model_dump()
    for f in ("expires_at", "used_at", "created_at"):
        if isinstance(tdoc.get(f), datetime):
            tdoc[f] = _iso(tdoc[f])
    await platform_magic_tokens_collection.insert_one(tdoc)

    _send_magic_link_email(email_n, token, account.get("name"), code=code,
                           locale=account.get("language") or "it")


def _send_magic_link_email(email: str, token: str, name: Optional[str],
                           code: Optional[str] = None,
                           locale: str = "it") -> None:
    """Email transazionale: CODICE a 6 cifre in evidenza + link fallback.
    In dev (niente Brevo) viene loggata. R2a: localizzata in 4 lingue
    sulla preferenza dell'account (e' l'email piu' vista dai viaggiatori).
    R2b: dentro il template comune (header Aurya + footer marketplace)."""
    import os
    from services.email_service import send_email, _t, _wrap_template

    base = os.environ.get("PUBLIC_APP_URL", "http://localhost:3000")
    link = f"{base}/account/accedi?token={token}"
    greeting = (_t("greeting_name", locale, name=name) if name
                else _t("greeting", locale) + ",")
    code_block = ""
    if code:
        code_block = f"""
    <p>{_t("passport_code_intro", locale, minutes=MAGIC_TOKEN_TTL_MINUTES)}</p>
    <p style="font-size:32px;letter-spacing:8px;font-weight:bold;
    background:#f1ede3;color:#212c28;border-radius:12px;padding:14px 18px;
    display:inline-block">{code}</p>
    <p style="color:#8a9088;font-size:13px">{_t("passport_code_hint", locale)}</p>
    """
    content = f"""
    <p>{greeting}</p>
    {code_block}
    <p>{_t("passport_link_intro", locale, minutes=MAGIC_TOKEN_TTL_MINUTES)}</p>
    <p><a href="{link}" class="btn">{_t("passport_login_cta", locale)}</a></p>
    <p style="color:#8a9088;font-size:13px">{_t("passport_login_ignore", locale)}</p>
    """
    send_email(email, _t("passport_login_subject", locale),
               _wrap_template(content, locale), bypass_gate=True)


async def consume_magic_link(token: str) -> Optional[Dict[str, Any]]:
    """Consuma il token (one-shot atomico) e ritorna l'account, o None.

    L'update con used_at=None nel filtro garantisce che due richieste
    concorrenti sullo stesso token non emettano due sessioni.
    """
    from database import (
        platform_accounts_collection,
        platform_magic_tokens_collection,
    )

    if not token:
        return None
    now = utc_now()
    result = await platform_magic_tokens_collection.find_one_and_update(
        {"token_hash": _hash_token(token),
         "used_at": None,
         "expires_at": {"$gt": _iso(now)}},
        {"$set": {"used_at": _iso(now)}},
    )
    if not result:
        return None

    await platform_accounts_collection.update_one(
        {"id": result["account_id"]},
        {"$set": {"email_verified": True, "last_login_at": _iso(now)}},
    )
    account = await platform_accounts_collection.find_one(
        {"id": result["account_id"], "is_active": True}, {"_id": 0},
    )
    if account:
        logger.info("platform_account: login magic-link per %s", account["id"])
        # P4 — claim retroattivo: l'email e' APPENA stata verificata, e'
        # il momento sicuro per agganciare account org e ordini passati.
        # Best-effort: un errore qui non blocca mai il login.
        try:
            await retroactive_claim(account)
        except Exception:
            logger.exception("claim retroattivo fallito per %s", account["id"])
    return account


async def verify_login_code(email: str, code: str) -> Optional[Dict[str, Any]]:
    """Verifica il codice a 6 cifre per l'email. One-shot, max 5 tentativi.

    Il tentativo fallito INCREMENTA il contatore sul token piu' recente
    (superati i 5, il token muore anche se il codice era giusto): il
    brute-force sul codice corto e' chiuso da tentativi+TTL+rate-limit.
    """
    from database import (
        platform_accounts_collection,
        platform_magic_tokens_collection,
    )

    email_n = _normalize_email(email)
    code = (code or "").strip()
    if not email_n or not code.isdigit() or len(code) != 6:
        return None
    account = await platform_accounts_collection.find_one(
        {"email": email_n, "is_active": True}, {"_id": 0})
    if not account:
        return None

    now = utc_now()
    # match atomico: codice giusto + non usato + non scaduto + tentativi ok
    result = await platform_magic_tokens_collection.find_one_and_update(
        {"account_id": account["id"],
         "code_hash": _hash_token(code),
         "used_at": None,
         "code_attempts": {"$lt": 5},
         "expires_at": {"$gt": _iso(now)}},
        {"$set": {"used_at": _iso(now)}},
    )
    if not result:
        # tentativo fallito: brucia un tentativo sull'ultimo token vivo
        await platform_magic_tokens_collection.update_one(
            {"account_id": account["id"], "used_at": None,
             "expires_at": {"$gt": _iso(now)}},
            {"$inc": {"code_attempts": 1}},
        )
        return None

    await platform_accounts_collection.update_one(
        {"id": account["id"]},
        {"$set": {"email_verified": True, "last_login_at": _iso(now)}},
    )
    account = await platform_accounts_collection.find_one(
        {"id": account["id"], "is_active": True}, {"_id": 0})
    if account:
        logger.info("platform_account: login via codice per %s", account["id"])
        try:
            await retroactive_claim(account)
        except Exception:
            logger.exception("claim retroattivo fallito per %s", account["id"])
    return account


async def ensure_indexes() -> None:
    """Indici: email unica case-normalized, token hash, TTL cleanup."""
    from database import (
        platform_accounts_collection,
        platform_magic_tokens_collection,
    )
    await platform_accounts_collection.create_index("email", unique=True)
    await platform_accounts_collection.create_index("id", unique=True)
    await platform_magic_tokens_collection.create_index("token_hash")
    await platform_magic_tokens_collection.create_index("expires_at")


# ── AP2 — ponte newsletter (hub /account) ────────────────────────────────────

async def newsletter_status(email: str, *,
                            with_token: bool = True) -> Dict[str, Any]:
    """Lookup aurya_subscribers per l'email del Passaporto (AP2).

    Se l'email risulta iscritta CONFERMATA alla lettera di Aurya ritorna
    ``{"newsletter_subscriber": True, "subscriber_token": <jwt>}`` — lo
    stesso token (core/subscriber_token) che il blog BN3 usa per
    sbloccare le guide riservate. In ogni altro caso (non iscritta,
    pending, unsubscribed) SOLO ``{"newsletter_subscriber": False}``:
    nessun token viene mai emesso per chi non ha confermato.

    ``with_token=False`` (es. GET /platform/me) evita di firmare un JWT
    quando serve solo il booleano per il render.
    """
    from database import db

    email_n = _normalize_email(email)
    out: Dict[str, Any] = {"newsletter_subscriber": False}
    if not email_n:
        return out
    doc = await db.aurya_subscribers.find_one(
        {"email": email_n}, {"_id": 0, "status": 1})
    if doc and doc.get("status") == "confirmed":
        out["newsletter_subscriber"] = True
        if with_token:
            from core.subscriber_token import generate_subscriber_token
            out["subscriber_token"] = generate_subscriber_token(email_n)
    return out


# ── AP1b — email + password sull'account Aurya ──────────────────────────────
# Stessa macchina collaudata di customer_auth_service, portata a livello
# piattaforma: bcrypt, verifica email con token one-shot (sha256 a DB),
# reset password che vale ANCHE come "imposta password" per gli account
# nati passwordless (claim acquisto), lockout con le stesse soglie.

VERIFY_TOKEN_TTL_HOURS = 24
RESET_TOKEN_TTL_MINUTES = 60

# Anti-enumeration timing-costante (stesso pattern Track S 2.1 dei
# customer): quando l'email non esiste o non ha password bruciamo comunque
# un giro bcrypt, cosi' la latenza non rivela se l'account c'e'.
from auth import get_password_hash, verify_password, validate_password_strength  # noqa: E402

_BCRYPT_DUMMY_HASH = get_password_hash("anti-enumeration-dummy-never-matches")


async def password_signup(*, name: Optional[str], email: str, password: str,
                          language: Optional[str] = None) -> Dict[str, Any]:
    """Signup email+password: crea (o adotta) l'account e invia l'email
    di verifica. L'account NON e' loggabile con password finche' l'email
    non e' verificata.

    Email gia' registrata → ValueError("EMAIL_EXISTS") (il router la
    traduce in un 409 onesto). Eccezione VOLUTA: un account "guscio"
    nato passwordless da un acquisto guest (mai verificato, mai loggato,
    senza password) viene ADOTTATO dal signup — dire "email gia'
    registrata" per un account che l'utente non ha mai creato sarebbe
    solo confusione; la proprieta' dell'email resta provata dal link di
    verifica.
    """
    from database import platform_accounts_collection

    email_n = _normalize_email(email)
    if not email_n or "@" not in email_n:
        raise ValueError("INVALID_EMAIL")

    validate_password_strength(password)
    from core.password_breach import validate_password_not_breached
    validate_password_not_breached(password)

    lang_n = language if language in ("it", "en", "de", "fr") else None

    account = await platform_accounts_collection.find_one({"email": email_n})
    if account and (account.get("email_verified") or account.get("password_hash")):
        raise ValueError("EMAIL_EXISTS")

    token = secrets.token_urlsafe(32)
    now = utc_now()
    verify_fields = {
        "password_hash": get_password_hash(password),
        "verification_token_hash": _hash_token(token),
        "verification_token_expires": _iso(
            now + timedelta(hours=VERIFY_TOKEN_TTL_HOURS)),
    }

    if account:
        # guscio passwordless pending: si adotta (vedi docstring)
        updates = dict(verify_fields)
        if name and not account.get("name"):
            updates["name"] = name.strip()
        if lang_n:
            updates["language"] = lang_n
        await platform_accounts_collection.update_one(
            {"id": account["id"]}, {"$set": updates})
        account = {**account, **updates}
    else:
        doc = PlatformAccount(email=email_n,
                              name=(name or "").strip() or None,
                              language=lang_n or "it").model_dump()
        for f in ("created_at", "last_login_at", "sessions_invalidated_at",
                  "claim_last_sent_at", "locked_until"):
            if isinstance(doc.get(f), datetime):
                doc[f] = _iso(doc[f])
        doc.update(verify_fields)
        await platform_accounts_collection.insert_one(doc)
        account = doc

    _send_verify_email(email_n, token, account.get("name"),
                       locale=account.get("language") or "it")
    logger.info("platform_account: signup password per %s (verifica inviata)",
                account["id"])
    return {"status": "verification_required"}


def _send_verify_email(email: str, token: str, name: Optional[str],
                       locale: str = "it") -> None:
    """Email di verifica account (AP1b): stesso template grafico delle
    altre transazionali Aurya, 4 lingue. In dev (niente Brevo) loggata."""
    import os
    from services.email_service import send_email, _t, _wrap_template

    base = os.environ.get("PUBLIC_APP_URL", "http://localhost:3000")
    link = f"{base}/account/verifica?token={token}"
    greeting = (_t("greeting_name", locale, name=name) if name
                else _t("greeting", locale) + ",")
    content = f"""
    <p>{greeting}</p>
    <p>{_t("aurya_verify_body", locale)}</p>
    <p><a href="{link}" class="btn">{_t("aurya_verify_cta", locale)}</a></p>
    <p style="color:#8a9088;font-size:13px">{_t("aurya_verify_footer", locale,
                                                hours=VERIFY_TOKEN_TTL_HOURS)}</p>
    """
    send_email(email, _t("aurya_verify_subject", locale),
               _wrap_template(content, locale), bypass_gate=True)


async def verify_signup_email(token: str) -> Dict[str, Any]:
    """Consuma il token di verifica (one-shot: al successo l'hash viene
    azzerato). Token invalido/scaduto → ValueError("INVALID_TOKEN")."""
    from database import platform_accounts_collection

    if not token:
        raise ValueError("INVALID_TOKEN")
    account = await platform_accounts_collection.find_one(
        {"verification_token_hash": _hash_token(token)}, {"_id": 0})
    if not account:
        raise ValueError("INVALID_TOKEN")

    expires = account.get("verification_token_expires")
    if expires:
        exp_dt = datetime.fromisoformat(expires)
        if exp_dt.tzinfo is None:
            exp_dt = exp_dt.replace(tzinfo=timezone.utc)
        if utc_now() > exp_dt:
            raise ValueError("INVALID_TOKEN")

    await platform_accounts_collection.update_one(
        {"id": account["id"]},
        {"$set": {"email_verified": True,
                  "verification_token_hash": None,
                  "verification_token_expires": None}},
    )
    logger.info("platform_account: email verificata per %s", account["id"])
    # email appena verificata: momento sicuro per il claim retroattivo
    # (stesso aggancio del magic link). Best-effort, mai bloccante.
    try:
        await retroactive_claim(account)
    except Exception:
        logger.exception("claim retroattivo fallito per %s", account["id"])
    return {"status": "verified"}


async def _handle_failed_password_login(account: Dict[str, Any]) -> None:
    """Contatore tentativi falliti + lockout esponenziale, stessa
    matematica dei customer (core/lockout_helpers)."""
    from core.lockout_helpers import compute_lockout_duration_minutes
    from core.security_config import LOCKOUT_THRESHOLD
    from database import platform_accounts_collection

    now = utc_now()
    new_attempts = int(account.get("failed_login_attempts", 0) or 0) + 1
    if new_attempts >= LOCKOUT_THRESHOLD:
        prior = int(account.get("lockout_count_today", 0) or 0)
        duration_min = compute_lockout_duration_minutes(prior)
        locked_until = now + timedelta(minutes=duration_min)
        await platform_accounts_collection.update_one(
            {"id": account["id"]},
            {"$set": {"failed_login_attempts": 0,
                      "locked_until": _iso(locked_until),
                      "lockout_count_today": prior + 1,
                      "last_failed_login_at": _iso(now)}},
        )
        logger.warning("platform_account.lockout: id=%s attempts=%d "
                       "duration_min=%d", account.get("id"), new_attempts,
                       duration_min)
    else:
        await platform_accounts_collection.update_one(
            {"id": account["id"]},
            {"$set": {"failed_login_attempts": new_attempts,
                      "last_failed_login_at": _iso(now)}},
        )


async def password_login(email: str, password: str) -> Dict[str, Any]:
    """Login email+password. Ordine anti-enumeration (Track S 2.1):

      1. rate limit per-email → 401 generico (bcrypt dummy comunque)
      2. account inesistente o senza password → bcrypt dummy + 401 generico
      3. password sbagliata → contatore fallimenti (lockout) + 401 generico
      4. da qui il chiamante HA la password: gli errori di stato sono
         sicuri → lockout 423, ACCOUNT_DISABLED, EMAIL_NOT_VERIFIED
      5. successo: azzera i contatori, timbra last_login_at, claim
         retroattivo best-effort. Ritorna l'account fresco.
    """
    from core.lockout_helpers import is_account_locked
    from core.rate_limiting import check_email_rate
    from core.security_config import LOCKOUT_ERROR_CODE
    from database import platform_accounts_collection

    email_n = _normalize_email(email)
    if not check_email_rate(email_n, "platform_login", max_per_hour=20):
        verify_password(password or "", _BCRYPT_DUMMY_HASH)
        raise ValueError("INVALID_CREDENTIALS")

    account = await platform_accounts_collection.find_one(
        {"email": email_n}, {"_id": 0})
    if not account or not account.get("password_hash"):
        verify_password(password or "", _BCRYPT_DUMMY_HASH)
        raise ValueError("INVALID_CREDENTIALS")

    if not verify_password(password, account["password_hash"]):
        await _handle_failed_password_login(account)
        raise ValueError("INVALID_CREDENTIALS")

    now = utc_now()
    locked_until_iso = is_account_locked(account, now)
    if locked_until_iso:
        raise ValueError(f"{LOCKOUT_ERROR_CODE}:{locked_until_iso}")

    if not account.get("is_active", True):
        raise ValueError("ACCOUNT_DISABLED")
    if not account.get("email_verified", False):
        raise ValueError("EMAIL_NOT_VERIFIED")

    await platform_accounts_collection.update_one(
        {"id": account["id"]},
        {"$set": {"last_login_at": _iso(now),
                  "failed_login_attempts": 0,
                  "locked_until": None,
                  "lockout_count_today": 0}},
    )
    account = await platform_accounts_collection.find_one(
        {"id": account["id"]}, {"_id": 0})
    logger.info("platform_account: login password per %s", account["id"])
    try:
        await retroactive_claim(account)
    except Exception:
        logger.exception("claim retroattivo fallito per %s", account["id"])
    return account


async def request_password_reset(email: str,
                                 language: Optional[str] = None) -> None:
    """Richiesta reset: il router risponde SEMPRE 200 neutro; l'email col
    token parte solo se l'account esiste. Vale anche per gli account nati
    passwordless (claim acquisto): e' la strada per IMPOSTARE la password
    la prima volta."""
    from database import platform_accounts_collection

    email_n = _normalize_email(email)
    if not email_n or "@" not in email_n:
        return
    account = await platform_accounts_collection.find_one({"email": email_n})
    if not account:
        return

    token = secrets.token_urlsafe(32)
    await platform_accounts_collection.update_one(
        {"id": account["id"]},
        {"$set": {"reset_token_hash": _hash_token(token),
                  "reset_token_expires": _iso(
                      utc_now() + timedelta(minutes=RESET_TOKEN_TTL_MINUTES))}},
    )
    locale = language if language in ("it", "en", "de", "fr") else (
        account.get("language") if account.get("language") in
        ("it", "en", "de", "fr") else "it")
    _send_reset_email(email_n, token, account.get("name"), locale=locale)


def _send_reset_email(email: str, token: str, name: Optional[str],
                      locale: str = "it") -> None:
    import os
    from services.email_service import send_email, _t, _wrap_template

    base = os.environ.get("PUBLIC_APP_URL", "http://localhost:3000")
    link = f"{base}/account/nuova-password?token={token}"
    greeting = (_t("greeting_name", locale, name=name) if name
                else _t("greeting", locale) + ",")
    content = f"""
    <p>{greeting}</p>
    <p>{_t("aurya_reset_body", locale)}</p>
    <p><a href="{link}" class="btn">{_t("aurya_reset_cta", locale)}</a></p>
    <p style="color:#8a9088;font-size:13px">{_t("aurya_reset_footer", locale,
                                                minutes=RESET_TOKEN_TTL_MINUTES)}</p>
    """
    send_email(email, _t("aurya_reset_subject", locale),
               _wrap_template(content, locale), bypass_gate=True)


async def confirm_password_reset(token: str, new_password: str) -> Dict[str, Any]:
    """Consuma il token di reset (one-shot) e imposta la nuova password.

    Per gli account passwordless e' la PRIMA password: il flusso e'
    identico (password_hash None → viene semplicemente scritto). Il
    click sul link prova il controllo della casella → email_verified
    diventa True e i contatori anti-bruteforce si azzerano (stessa
    regola Onda 29 dei customer)."""
    from database import platform_accounts_collection

    if not token:
        raise ValueError("INVALID_TOKEN")
    account = await platform_accounts_collection.find_one(
        {"reset_token_hash": _hash_token(token)}, {"_id": 0})
    if not account:
        raise ValueError("INVALID_TOKEN")

    expires = account.get("reset_token_expires")
    if expires:
        exp_dt = datetime.fromisoformat(expires)
        if exp_dt.tzinfo is None:
            exp_dt = exp_dt.replace(tzinfo=timezone.utc)
        if utc_now() > exp_dt:
            raise ValueError("INVALID_TOKEN")

    validate_password_strength(new_password)
    from core.password_breach import validate_password_not_breached
    validate_password_not_breached(new_password)

    was_unverified = not account.get("email_verified")
    now = utc_now()
    await platform_accounts_collection.update_one(
        {"id": account["id"]},
        {"$set": {"password_hash": get_password_hash(new_password),
                  "reset_token_hash": None,
                  "reset_token_expires": None,
                  "password_changed_at": _iso(now),
                  "email_verified": True,
                  "failed_login_attempts": 0,
                  "locked_until": None,
                  "lockout_count_today": 0}},
    )
    logger.info("platform_account: password impostata via reset per %s",
                account["id"])
    if was_unverified:
        # prima verifica di fatto (link email usato): claim retroattivo
        try:
            await retroactive_claim(account)
        except Exception:
            logger.exception("claim retroattivo fallito per %s", account["id"])
    return {"status": "ok"}


# ── P2 — aggancio acquisto ───────────────────────────────────────────────────
# Chiamate SEMPRE best-effort dai flussi ordine/pagamento (try/except nel
# chiamante): il Passaporto non deve MAI bloccare un ordine o un incasso.

CLAIM_EMAIL_COOLDOWN_HOURS = 24


async def link_order_to_platform_account(order: Dict[str, Any],
                                         org_id: str) -> Optional[str]:
    """Stamp additivo post-creazione ordine (percorso storefront).

    1. find-or-create del platform account (pending, email_verified=False
       finche' il magic link non viene usato) sulla email dell'ordine
    2. stamp orders.platform_account_id (denormalizzato per /account)
    3. link dei customer_accounts org ESISTENTI con la stessa email
       (set platform_account_id se assente — mai sovrascritto)

    Non tocca nulla della pipeline ordini/pagamenti: solo campi additivi.
    """
    from database import (
        customer_accounts_collection,
        orders_collection,
        platform_accounts_collection,
    )

    email_n = _normalize_email(order.get("customer_email") or "")
    if not email_n or "@" not in email_n:
        return None

    account = await platform_accounts_collection.find_one({"email": email_n})
    if not account:
        doc = PlatformAccount(email=email_n,
                              name=order.get("customer_name")).model_dump()
        for f in ("created_at", "last_login_at", "sessions_invalidated_at",
                  "claim_last_sent_at"):
            if isinstance(doc.get(f), datetime):
                doc[f] = _iso(doc[f])
        await platform_accounts_collection.insert_one(doc)
        account = doc

    await orders_collection.update_one(
        {"id": order["id"], "organization_id": org_id,
         "platform_account_id": {"$exists": False}},
        {"$set": {"platform_account_id": account["id"]}},
    )
    # link account org con stessa email (solo se non gia' linkati)
    await customer_accounts_collection.update_many(
        {"email": email_n, "platform_account_id": {"$exists": False}},
        {"$set": {"platform_account_id": account["id"]}},
    )
    return account["id"]


async def send_claim_email_if_needed(order: Dict[str, Any]) -> bool:
    """Email "Gestisci le tue prenotazioni" col magic link, al primo
    pagamento riuscito. Solo se l'account non e' ancora verificato,
    con cooldown 24h (acquisti multipli → una sola email)."""
    from database import (
        platform_accounts_collection,
        platform_magic_tokens_collection,
    )

    email_n = _normalize_email(order.get("customer_email") or "")
    if not email_n:
        # l'ordine non porta l'email: risolvo dal CRM (customers) via
        # customer_id — e' il percorso normale per gli ordini storefront
        cust_id = order.get("customer_id")
        if cust_id:
            from database import customers_collection
            cust = await customers_collection.find_one(
                {"id": cust_id}, {"_id": 0, "email": 1},
            )
            email_n = _normalize_email((cust or {}).get("email") or "")
    if not email_n:
        return False
    account = await platform_accounts_collection.find_one({"email": email_n})
    if not account or account.get("email_verified"):
        return False

    last = account.get("claim_last_sent_at")
    if last:
        last_dt = datetime.fromisoformat(last) if isinstance(last, str) else last
        if last_dt.tzinfo is None:
            last_dt = last_dt.replace(tzinfo=timezone.utc)
        if utc_now() - last_dt < timedelta(hours=CLAIM_EMAIL_COOLDOWN_HOURS):
            return False

    token = secrets.token_urlsafe(32)
    t = MagicLinkToken(
        account_id=account["id"],
        token_hash=_hash_token(token),
        expires_at=utc_now() + timedelta(minutes=MAGIC_TOKEN_TTL_MINUTES),
    )
    tdoc = t.model_dump()
    for f in ("expires_at", "used_at", "created_at"):
        if isinstance(tdoc.get(f), datetime):
            tdoc[f] = _iso(tdoc[f])
    await platform_magic_tokens_collection.insert_one(tdoc)

    # R2a — lingua: la lingua UI con cui l'utente ha COMPRATO (order.locale)
    # e' il segnale piu' fresco; fallback sulla preferenza account, poi it.
    _claim_locale = order.get("locale")
    if _claim_locale not in ("it", "en", "de", "fr"):
        _claim_locale = account.get("language") if account.get("language") in (
            "it", "en", "de", "fr") else "it"

    _send_claim_email(email_n, token, account.get("name"), locale=_claim_locale)
    await platform_accounts_collection.update_one(
        {"id": account["id"]},
        {"$set": {"claim_last_sent_at": _iso(utc_now())}},
    )
    return True


def _send_claim_email(email: str, token: str, name: Optional[str],
                      locale: str = "it") -> None:
    import os
    from services.email_service import send_email, _t, _wrap_template

    base = os.environ.get("PUBLIC_APP_URL", "http://localhost:3000")
    link = f"{base}/account/accedi?token={token}"
    greeting = (_t("greeting_name", locale, name=name) if name
                else _t("greeting", locale) + ",")
    content = f"""
    <p>{greeting}</p>
    <p>{_t("passport_claim_body", locale)}</p>
    <p><a href="{link}" class="btn">{_t("passport_claim_cta", locale)}</a></p>
    <p style="color:#8a9088;font-size:13px">{_t("passport_claim_footer", locale,
                                                minutes=MAGIC_TOKEN_TTL_MINUTES)}</p>
    """
    send_email(email, _t("passport_claim_subject", locale),
               _wrap_template(content, locale), bypass_gate=True)


# ── P4 — claim retroattivo + GDPR ────────────────────────────────────────────

async def retroactive_claim(account: Dict[str, Any]) -> Dict[str, int]:
    """Al login (email APPENA verificata dal magic link): aggancia tutto
    cio' che esiste gia' per questa email.

    1. customer_accounts org con stessa email → platform_account_id
    2. ordini passati: via CRM customers (l'ordine non porta l'email) —
       stamp platform_account_id dove assente

    Idempotente e additivo: $exists False → mai sovrascritture. Chiamata
    best-effort dal consume (mai bloccare un login).
    """
    from database import (
        customer_accounts_collection,
        customers_collection,
        orders_collection,
    )

    email_n = _normalize_email(account.get("email") or "")
    if not email_n:
        return {"customer_accounts": 0, "orders": 0}

    r1 = await customer_accounts_collection.update_many(
        {"email": email_n, "platform_account_id": {"$exists": False}},
        {"$set": {"platform_account_id": account["id"]}},
    )

    crm_ids = [c["id"] async for c in customers_collection.find(
        {"email": email_n}, {"_id": 0, "id": 1})]
    r2_count = 0
    if crm_ids:
        r2 = await orders_collection.update_many(
            {"customer_id": {"$in": crm_ids},
             "platform_account_id": {"$exists": False}},
            {"$set": {"platform_account_id": account["id"]}},
        )
        r2_count = getattr(r2, "modified_count", 0)

    claimed = {"customer_accounts": getattr(r1, "modified_count", 0),
               "orders": r2_count}
    if claimed["customer_accounts"] or claimed["orders"]:
        logger.info("platform_account %s: claim retroattivo %s",
                    account["id"], claimed)
    return claimed


async def export_account_data(account: Dict[str, Any]) -> Dict[str, Any]:
    """GDPR export: i dati dell'IDENTITA' piattaforma + la vista cliente
    delle prenotazioni (stessi campi safe dell'area personale). I dati
    interni degli operatori (loro CRM, costi, note) NON sono dell'utente
    e non escono da qui."""
    from database import orders_collection

    orders = await orders_collection.find(
        {"platform_account_id": account["id"]},
        {"_id": 0, "id": 1, "order_number": 1, "status": 1, "total": 1,
         "currency": 1, "created_at": 1,
         "items.product_name": 1, "items.quantity": 1,
         "items.occurrence_start_at": 1},
    ).sort("created_at", -1).to_list(500)

    return {
        "account": {k: account.get(k) for k in
                    ("id", "email", "name", "phone", "language",
                     "email_verified", "created_at", "last_login_at")},
        "orders": orders,
        "exported_at": utc_now().isoformat(),
    }


async def delete_account(account: Dict[str, Any]) -> Dict[str, int]:
    """GDPR cancellazione a DUE livelli (docs/PLATFORM_ACCOUNT_PLAN.md §3):

    CANCELLA l'identita' piattaforma (account + token magic) e SCOLLEGA
    gli stamp (unset platform_account_id da ordini e customer_accounts).
    NON tocca i dati degli operatori: ordini, CRM e documenti fiscali
    restano — sono obblighi di legge LORO, titolarita' loro.
    """
    from database import (
        customer_accounts_collection,
        orders_collection,
        platform_accounts_collection,
        platform_magic_tokens_collection,
    )

    aid = account["id"]
    r_ord = await orders_collection.update_many(
        {"platform_account_id": aid},
        {"$unset": {"platform_account_id": ""}},
    )
    r_cust = await customer_accounts_collection.update_many(
        {"platform_account_id": aid},
        {"$unset": {"platform_account_id": ""}},
    )
    await platform_magic_tokens_collection.delete_many({"account_id": aid})
    await platform_accounts_collection.delete_one({"id": aid})

    result = {"orders_unlinked": getattr(r_ord, "modified_count", 0),
              "customer_accounts_unlinked": getattr(r_cust, "modified_count", 0)}
    logger.info("platform_account %s CANCELLATO (GDPR): %s", aid, result)
    return result
