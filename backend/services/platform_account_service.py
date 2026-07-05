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
                             language: str = "it") -> None:
    """Find-or-create account + emette il magic link via email.

    NON ritorna nulla e non solleva per email malformate/duplicate:
    l'endpoint risponde sempre 202 (enumeration-safe). Gli errori interni
    vengono loggati, mai esposti.
    """
    from database import (
        platform_accounts_collection,
        platform_magic_tokens_collection,
    )

    email_n = _normalize_email(email)
    if not email_n or "@" not in email_n:
        return

    account = await platform_accounts_collection.find_one({"email": email_n})
    if not account:
        doc = PlatformAccount(email=email_n, name=name, language=language).model_dump()
        for f in ("created_at", "last_login_at", "sessions_invalidated_at"):
            if isinstance(doc.get(f), datetime):
                doc[f] = _iso(doc[f])
        await platform_accounts_collection.insert_one(doc)
        account = doc

    # token in chiaro SOLO nell'email; a DB va l'hash
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

    _send_magic_link_email(email_n, token, account.get("name"))


def _send_magic_link_email(email: str, token: str, name: Optional[str]) -> None:
    """Email transazionale col link. In dev (niente Brevo) viene loggata."""
    import os
    from services.email_service import send_email

    base = os.environ.get("PUBLIC_APP_URL", "http://localhost:3000")
    link = f"{base}/account/accedi?token={token}"
    greeting = f"Ciao {name}," if name else "Ciao,"
    html = f"""
    <p>{greeting}</p>
    <p>Ecco il tuo link di accesso — vale {MAGIC_TOKEN_TTL_MINUTES} minuti
    e funziona una volta sola:</p>
    <p><a href="{link}" style="display:inline-block;padding:10px 18px;
    background:#376254;color:#fff;border-radius:8px;text-decoration:none">
    Accedi al tuo account</a></p>
    <p style="color:#666;font-size:13px">Se non hai richiesto tu questo
    link, ignora questa email: nessuno puo' accedere senza di essa.</p>
    """
    send_email(email, "Il tuo accesso — un click e sei dentro", html,
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
