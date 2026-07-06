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
    sulla preferenza dell'account (e' l'email piu' vista dai viaggiatori)."""
    import os
    from services.email_service import send_email, _t

    base = os.environ.get("PUBLIC_APP_URL", "http://localhost:3000")
    link = f"{base}/account/accedi?token={token}"
    greeting = (_t("greeting_name", locale, name=name) if name
                else _t("greeting", locale) + ",")
    code_block = ""
    if code:
        code_block = f"""
    <p>{_t("passport_code_intro", locale, minutes=MAGIC_TOKEN_TTL_MINUTES)}</p>
    <p style="font-size:32px;letter-spacing:8px;font-weight:bold;
    background:#f4f6f4;border-radius:10px;padding:14px 18px;
    display:inline-block">{code}</p>
    <p style="color:#666;font-size:13px">{_t("passport_code_hint", locale)}</p>
    """
    html = f"""
    <p>{greeting}</p>
    {code_block}
    <p>{_t("passport_link_intro", locale, minutes=MAGIC_TOKEN_TTL_MINUTES)}</p>
    <p><a href="{link}" style="display:inline-block;padding:10px 18px;
    background:#376254;color:#fff;border-radius:8px;text-decoration:none">
    {_t("passport_login_cta", locale)}</a></p>
    <p style="color:#666;font-size:13px">{_t("passport_login_ignore", locale)}</p>
    """
    send_email(email, _t("passport_login_subject", locale), html,
               bypass_gate=True)


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
    from services.email_service import send_email, _t

    base = os.environ.get("PUBLIC_APP_URL", "http://localhost:3000")
    link = f"{base}/account/accedi?token={token}"
    greeting = (_t("greeting_name", locale, name=name) if name
                else _t("greeting", locale) + ",")
    html = f"""
    <p>{greeting}</p>
    <p>{_t("passport_claim_body", locale)}</p>
    <p><a href="{link}" style="display:inline-block;padding:10px 18px;
    background:#376254;color:#fff;border-radius:8px;text-decoration:none">
    {_t("passport_claim_cta", locale)}</a></p>
    <p style="color:#666;font-size:13px">{_t("passport_claim_footer", locale,
                                             minutes=MAGIC_TOKEN_TTL_MINUTES)}</p>
    """
    send_email(email, _t("passport_claim_subject", locale), html,
               bypass_gate=True)


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
