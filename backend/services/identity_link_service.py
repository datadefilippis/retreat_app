"""Il legame dei cappelli — ciclo ID (20/8/2026).

Una persona su Aurya puo' avere due cappelli: operatore (`users`) e
cliente (`platform_accounts`). Le collezioni NON si fondono — questo
modulo mantiene solo il LEGAME fra le due:

    users.platform_account_id  ⇄  platform_accounts.operator_user_id

Piano: docs/IDENTITA_UNICA_PLAN_2026-08.md. Le regole che non si
negoziano (ognuna ha la sua guardia in test_identita_unica_id.py):

1. il link nasce SOLO fra email verificate da ENTRAMBE le parti —
   altrimenti chiunque registri un platform account con l'email di un
   operatore erediterebbe il suo gestionale al primo SSO;
2. idempotente e riparabile: se un crash lascia un puntatore solo, il
   passaggio successivo completa la coppia (lazy repair in /entra);
3. il cambio email su un lato SPEZZA il legame (si ricrea dopo la
   verifica del nuovo indirizzo);
4. cancellare un cappello annulla il puntatore sull'altro lato, e
   nient'altro;
5. il legame e' due FK indicizzate — mai una fusione di dati.
"""

import logging

logger = logging.getLogger(__name__)


def _norm(email):
    return (email or "").strip().lower()


async def link_hats(user_doc: dict, account_doc: dict) -> bool:
    """Scrive il legame nei due sensi. Rifiuta email non combacianti o
    non verificate (regola 1). Ritorna True se il legame e' in piedi."""
    from database import platform_accounts_collection, users_collection

    if _norm(user_doc.get("email")) != _norm(account_doc.get("email")):
        return False
    if not user_doc.get("email_verified") or not account_doc.get("email_verified"):
        return False
    if not user_doc.get("is_active", True) or not account_doc.get("is_active", True):
        return False
    await users_collection.update_one(
        {"id": user_doc["id"]},
        {"$set": {"platform_account_id": account_doc["id"]}})
    await platform_accounts_collection.update_one(
        {"id": account_doc["id"]},
        {"$set": {"operator_user_id": user_doc["id"]}})
    logger.info("identity_link: cappelli collegati user=%s account=%s",
                user_doc["id"], account_doc["id"])
    return True


async def auto_link_by_email(email: str) -> bool:
    """Se la stessa email vive verificata nei due mondi e il legame non
    c'e' (o e' rimasto a meta'), lo mette in piedi. Chiamata dopo ogni
    verifica email e dopo ogni login dalla porta unica: e' anche il
    lazy repair della regola 2. Non crea MAI niente: collega l'esistente."""
    from database import platform_accounts_collection, users_collection

    e = _norm(email)
    if not e:
        return False
    user_doc = await users_collection.find_one({"email": e})
    account_doc = await platform_accounts_collection.find_one({"email": e})
    if not user_doc or not account_doc:
        return False
    if (user_doc.get("platform_account_id") == account_doc["id"]
            and account_doc.get("operator_user_id") == user_doc["id"]):
        return True                                   # gia' in piedi
    return await link_hats(user_doc, account_doc)


async def unlink_for_user(user_id: str) -> None:
    """L'operatore sparisce (o cambia email): il cappello cliente resta,
    ma smette di puntare a lui (regole 3 e 4)."""
    from database import platform_accounts_collection, users_collection
    await platform_accounts_collection.update_one(
        {"operator_user_id": user_id},
        {"$set": {"operator_user_id": None}})
    await users_collection.update_one(
        {"id": user_id}, {"$set": {"platform_account_id": None}})


async def unlink_for_account(account_id: str) -> None:
    """Il cappello cliente sparisce (o cambia email): idem, al contrario."""
    from database import platform_accounts_collection, users_collection
    await users_collection.update_one(
        {"platform_account_id": account_id},
        {"$set": {"platform_account_id": None}})
    await platform_accounts_collection.update_one(
        {"id": account_id}, {"$set": {"operator_user_id": None}})


async def ensure_client_hat_for_operator(user_doc: dict) -> dict:
    """Direzione A del piano: l'operatore chiede il cappello cliente.

    - platform account gia' esistente e verificato → solo il legame;
    - esistente ma NON verificato → si rifiuta (regola 1): quel account
      l'ha creato qualcuno che non ha mai dimostrato di avere la casella;
    - inesistente → nasce DALL'identita' operatore: email gia' verificata
      al signup, quindi `email_verified=True` e NESSUNA password propria
      (magic link e SSO bastano; una password potra' nascere dopo, dal
      flusso reset).

    Ritorna {linked, account_id, created}.
    """
    from database import platform_accounts_collection
    from models.platform_account import PlatformAccount

    if not user_doc.get("email_verified"):
        raise ValueError("OPERATOR_EMAIL_NOT_VERIFIED")
    e = _norm(user_doc["email"])
    account_doc = await platform_accounts_collection.find_one({"email": e})
    if account_doc:
        if not account_doc.get("email_verified"):
            raise ValueError("CLIENT_ACCOUNT_UNVERIFIED")
        ok = await link_hats(user_doc, account_doc)
        return {"linked": ok, "account_id": account_doc["id"], "created": False}

    account = PlatformAccount(
        email=e,
        name=user_doc.get("name"),
        language=user_doc.get("locale", "it"),
        email_verified=True,
        operator_user_id=user_doc["id"],
    )
    doc = account.model_dump()
    await platform_accounts_collection.insert_one(dict(doc))
    from database import users_collection
    await users_collection.update_one(
        {"id": user_doc["id"]},
        {"$set": {"platform_account_id": account.id}})
    logger.info("identity_link: cappello cliente creato dall'operatore user=%s",
                user_doc["id"])
    return {"linked": True, "account_id": account.id, "created": True}
