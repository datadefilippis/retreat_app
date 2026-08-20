"""Platform accounts router — auth marketplace (P1).

Piano: docs/PLATFORM_ACCOUNT_PLAN.md. Endpoints:

  POST /platform/auth/magic-link         → 202 SEMPRE (enumeration-safe)
  POST /platform/auth/magic-link/verify  → {access_token} o 401
  GET  /platform/me                      → profilo (token piattaforma)
  PATCH /platform/me                     → nome/telefono/lingua
  POST /platform/auth/logout-all         → invalida tutte le sessioni

Feature flag: PLATFORM_ACCOUNTS_ENABLED (default on; off → 404 su tutto,
l'app funziona come prima del modulo).
"""

import os
from datetime import timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field

from auth import create_platform_token, get_current_platform_account
from routers.auth import limiter
from models.common import utc_now

router = APIRouter(prefix="/platform", tags=["Platform Accounts"])

PLATFORM_SESSION_DAYS = 30


def _flag_enabled() -> None:
    if os.environ.get("PLATFORM_ACCOUNTS_ENABLED", "true").lower() in ("0", "false", "off"):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="Not found")


class MagicLinkRequest(BaseModel):
    email: str = Field(..., max_length=254)
    name: Optional[str] = Field(None, max_length=120)
    # R2a: lingua UI del frontend alla richiesta. None = client legacy →
    # il service usa la lingua gia' salvata sull'account (fallback it).
    # Quando presente e valida aggiorna la preferenza dell'account.
    language: Optional[str] = Field(None, max_length=5)
    # NL1 (20/8) — la registrazione leggera passa da qui: col consenso
    # l'account nasce senza password; senza consenso l'endpoint e'
    # find-only (nessun account senza timbro legale, AP-L).
    accepted_terms: bool = False
    # NL2 — consenso marketing SEPARATO, mai preselezionato lato UI
    wants_newsletter: bool = False


class MagicLinkVerify(BaseModel):
    token: str = Field(..., max_length=128)


class ProfileUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=120)
    phone: Optional[str] = Field(None, max_length=40)
    language: Optional[str] = Field(None, max_length=5)


@router.post("/auth/magic-link", status_code=202)
@limiter.limit("5/minute")
async def request_magic_link(body: MagicLinkRequest, request: Request):
    """Richiede un magic link. Risponde 202 SEMPRE — che l'email esista,
    non esista o sia malformata: nessuna enumerazione possibile."""
    _flag_enabled()
    from services.platform_account_service import request_magic_link as _req
    _req_ip = None
    try:
        from core.rate_limiting import get_real_ip
        _req_ip = get_real_ip(request)
    except Exception:
        pass
    try:
        await _req(body.email, name=body.name, language=body.language,
                   accepted_terms=body.accepted_terms, request_ip=_req_ip,
                   user_agent=request.headers.get("user-agent") if request else None)
        # NL2 — la Lettera e' un consenso a parte: si chiede insieme ma
        # viaggia sul suo flusso (double opt-in immutato)
        if body.accepted_terms and body.wants_newsletter:
            await _subscribe_to_letter(request, body.email, body.name,
                                       body.language)
    except Exception:
        # mai esporre errori interni su questo endpoint
        import logging
        logging.getLogger(__name__).exception("magic-link request fallita")
    return {"status": "accepted"}


async def _subscribe_to_letter(request: Request, email: str, name,
                               language) -> None:
    """NL2 — iscrizione alla Lettera chiesta durante la creazione
    dell'account. Riusa la ROUTE pubblica (double opt-in, consenso
    marketing, sorgente tracciata): nessuna scorciatoia e nessuna
    logica duplicata; un errore qui non fa mai fallire l'account."""
    import logging
    try:
        from routers.subscribers import SubscribePayload, subscribe
        await subscribe(request, SubscribePayload(
            email=email, name=name, consent=True,
            language=language or "it", source="account_signup"))
    except Exception:
        logging.getLogger(__name__).warning(
            "NL2: iscrizione Lettera dal signup fallita", exc_info=True)


@router.post("/auth/magic-link/verify")
@limiter.limit("10/minute")
async def verify_magic_link(body: MagicLinkVerify, request: Request):
    """Consuma il token one-shot e ritorna il JWT piattaforma (30gg)."""
    _flag_enabled()
    from services.platform_account_service import (consume_magic_link,
                                                   newsletter_status)
    account = await consume_magic_link(body.token)
    if not account:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Link non valido o scaduto. Richiedine uno nuovo.",
        )
    token = create_platform_token(
        {"sub": account["id"], "email": account["email"]},
        expires_delta=timedelta(days=PLATFORM_SESSION_DAYS),
    )
    return {
        "access_token": token,
        "token_type": "bearer",
        "account": {"id": account["id"], "email": account["email"],
                    "name": account.get("name"),
                    "language": account.get("language", "it")},
        # AP2 — se l'email e' iscritta CONFERMATA alla lettera di Aurya,
        # il login porta anche il subscriber_token che sblocca le guide
        # (newsletter_subscriber: False e nessun token altrimenti).
        **await newsletter_status(account["email"]),
    }


class CodeVerify(BaseModel):
    email: str
    code: str


@router.post("/auth/code/verify")
@limiter.limit("10/minute")
async def verify_login_code_ep(body: CodeVerify, request: Request):
    """Login col codice a 6 cifre (stessa email del magic link)."""
    _flag_enabled()
    from services.platform_account_service import (newsletter_status,
                                                   verify_login_code)
    account = await verify_login_code(body.email, body.code)
    if not account:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Codice non valido o scaduto. Richiedine uno nuovo.",
        )
    token = create_platform_token(
        {"sub": account["id"], "email": account["email"]},
        expires_delta=timedelta(days=PLATFORM_SESSION_DAYS),
    )
    return {
        "access_token": token,
        "token_type": "bearer",
        "account": {"id": account["id"], "email": account["email"],
                    "name": account.get("name"),
                    "language": account.get("language", "it")},
        # AP2 — stessa regola del magic link: token guide SOLO se l'email
        # e' un'iscrizione confermata alla lettera di Aurya.
        **await newsletter_status(account["email"]),
    }


# ── AP1b — email + password sull'account Aurya ──────────────────────────────
# Stesso router, stesso flag. Il passwordless (magic link + OTP) resta
# identico come alternativa e recovery. Risposta di login IDENTICA alle
# altre strade (access_token + account + newsletter_status AP2).


class PasswordSignup(BaseModel):
    name: Optional[str] = Field(None, max_length=120)
    email: str = Field(..., max_length=254)
    password: str = Field(..., max_length=128)
    language: Optional[str] = Field(None, max_length=5)
    # AP-L — consenso a Termini + Privacy di Aurya: obbligatorio alla
    # creazione account (checkbox nel form). Default False: i client
    # legacy ricevono un 400 onesto, non un errore di schema.
    accepted_terms: bool = False
    # NL2 — consenso marketing SEPARATO (mai preselezionato lato UI):
    # vale per entrambe le strade di registrazione, con e senza password
    wants_newsletter: bool = False


class VerifyEmailBody(BaseModel):
    token: str = Field(..., max_length=128)


class PasswordLogin(BaseModel):
    email: str = Field(..., max_length=254)
    password: str = Field(..., max_length=128)


class PasswordResetRequest(BaseModel):
    email: str = Field(..., max_length=254)
    language: Optional[str] = Field(None, max_length=5)


class PasswordResetConfirm(BaseModel):
    token: str = Field(..., max_length=128)
    new_password: str = Field(..., max_length=128)


def _login_response(account: dict) -> dict:
    """Shape unico per TUTTE le strade di login (magic link, OTP,
    password): il frontend salva il token e, se presente, il
    subscriber_token con lo stesso codice."""
    token = create_platform_token(
        {"sub": account["id"], "email": account["email"]},
        expires_delta=timedelta(days=PLATFORM_SESSION_DAYS),
    )
    return {
        "access_token": token,
        "token_type": "bearer",
        "account": {"id": account["id"], "email": account["email"],
                    "name": account.get("name"),
                    "language": account.get("language", "it")},
    }


@router.post("/auth/signup", status_code=202)
@limiter.limit("5/minute")
async def password_signup_ep(body: PasswordSignup, request: Request):
    """Signup email+password. Email di verifica con token one-shot:
    l'account non e' loggabile con password finche' non e' verificata.
    Email gia' registrata → 409 onesto (chi ha un account deve accedere,
    non ricrearlo)."""
    _flag_enabled()
    from services.platform_account_service import password_signup

    # AP-L — senza consenso ai documenti Aurya l'account non si crea
    if not body.accepted_terms:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Per creare l'account devi accettare i Termini e la "
                   "Privacy di Aurya.",
        )
    # IP + User-Agent per l'audit immutabile del consenso (best-effort)
    _req_ip = None
    try:
        from core.rate_limiting import get_real_ip
        _req_ip = get_real_ip(request)
    except Exception:
        pass
    _ua = request.headers.get("user-agent") if request else None

    try:
        out = await password_signup(name=body.name, email=body.email,
                                    password=body.password,
                                    language=body.language,
                                    accepted_terms=True,
                                    request_ip=_req_ip, user_agent=_ua)
        # NL2 — la Lettera viaggia sul suo flusso (double opt-in), mai
        # come effetto collaterale silenzioso della creazione account
        if body.wants_newsletter:
            await _subscribe_to_letter(request, body.email, body.name,
                                       body.language)
        return out
    except ValueError as e:
        msg = str(e)
        if msg == "EMAIL_EXISTS":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Questa email ha già un account Aurya. "
                       "Accedi oppure usa Password dimenticata.",
            )
        if msg == "INVALID_EMAIL":
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                                detail="Inserisci un'email valida.")
        # policy password: il messaggio del validator e' gia' onesto
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail=msg)


@router.post("/auth/verify-email")
@limiter.limit("10/minute")
async def verify_email_ep(body: VerifyEmailBody, request: Request):
    """Consuma il token di verifica del signup (one-shot)."""
    _flag_enabled()
    from services.platform_account_service import verify_signup_email
    try:
        return await verify_signup_email(body.token)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Link non valido o scaduto. Richiedine uno nuovo.",
        )


@router.post("/auth/login")
@limiter.limit("10/minute")
async def password_login_ep(body: PasswordLogin, request: Request):
    """Login email+password. Errori: 401 generico (anti-enumeration),
    423 lockout (stesse soglie dei customer), 403 email non verificata.
    Risposta identica alle altre strade di login (newsletter_status AP2
    incluso: le guide si sbloccano anche da qui)."""
    _flag_enabled()
    from core.security_config import LOCKOUT_ERROR_CODE
    from services.platform_account_service import (newsletter_status,
                                                   password_login)
    try:
        account = await password_login(body.email, body.password)
    except ValueError as e:
        msg = str(e)
        if msg.startswith(LOCKOUT_ERROR_CODE):
            raise HTTPException(status_code=status.HTTP_423_LOCKED,
                                detail=msg)
        if msg in ("EMAIL_NOT_VERIFIED", "ACCOUNT_DISABLED"):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                                detail=msg)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                            detail="Email o password non corretti.")
    return {
        **_login_response(account),
        # AP2 — stessa regola delle altre strade: token guide SOLO se
        # l'email e' un'iscrizione confermata alla lettera di Aurya.
        **await newsletter_status(account["email"]),
    }


@router.post("/auth/password-reset", status_code=200)
@limiter.limit("5/minute")
async def password_reset_request_ep(body: PasswordResetRequest,
                                    request: Request):
    """Richiesta reset: 200 SEMPRE neutro (enumeration-safe), l'email col
    token parte solo se l'account esiste. Serve anche agli account nati
    passwordless per IMPOSTARE la password la prima volta."""
    _flag_enabled()
    from services.platform_account_service import request_password_reset
    try:
        await request_password_reset(body.email, language=body.language)
    except Exception:
        import logging
        logging.getLogger(__name__).exception("password-reset request fallita")
    return {"status": "accepted"}


@router.post("/auth/password-reset/confirm")
@limiter.limit("10/minute")
async def password_reset_confirm_ep(body: PasswordResetConfirm,
                                    request: Request):
    """Consuma il token di reset (one-shot) e imposta la nuova password."""
    _flag_enabled()
    from services.platform_account_service import confirm_password_reset
    try:
        return await confirm_password_reset(body.token, body.new_password)
    except ValueError as e:
        msg = str(e)
        if msg == "INVALID_TOKEN":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Link non valido o scaduto. Richiedine uno nuovo.",
            )
        # policy password
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail=msg)


@router.get("/me")
async def get_me(account: dict = Depends(get_current_platform_account)):
    _flag_enabled()
    out = {k: account.get(k) for k in
           ("id", "email", "name", "phone", "language",
            "email_verified", "created_at", "last_login_at")}
    # TA5 — la UI "imposta password" deve sapere se chiedere l'attuale
    out["has_password"] = bool(account.get("password_hash"))
    # AP2 — booleano per il render della sezione Guide in /account
    # (niente token qui: quello viaggia solo nella risposta di login).
    from services.platform_account_service import newsletter_status
    nl = await newsletter_status(account.get("email") or "", with_token=False)
    out["newsletter_subscriber"] = nl["newsletter_subscriber"]
    # CP1 — none | pending | confirmed | unsubscribed: il pending
    # smette di essere invisibile
    out["newsletter_state"] = nl.get("newsletter_state", "none")
    # ID-bis (20/8) — /account mostra il cappello professionista se il
    # legame c'e': solo un booleano, mai dati dell'altro mondo.
    out["operator_linked"] = bool(account.get("operator_user_id"))
    return out


@router.patch("/me")
async def update_me(body: ProfileUpdate,
                    account: dict = Depends(get_current_platform_account)):
    _flag_enabled()
    from database import platform_accounts_collection
    updates = {k: v for k, v in body.model_dump().items() if v is not None}
    if updates:
        await platform_accounts_collection.update_one(
            {"id": account["id"]}, {"$set": updates},
        )
    fresh = {**account, **updates}
    return {k: fresh.get(k) for k in
            ("id", "email", "name", "phone", "language")}


class _PasswordChange(BaseModel):
    new_password: str
    current_password: Optional[str] = None


@router.post("/me/password", status_code=200)
async def set_my_password(body: _PasswordChange,
                          account: dict = Depends(get_current_platform_account)):
    """TA5 — imposta (o cambia) la password dall'hub /account.

    L'email di claim promette "una volta dentro puoi impostare una
    password", ma non esisteva nessuna superficie: l'unica strada era
    ripassare da "password dimenticata". Se l'account ha gia' una
    password serve quella attuale; se e' nato passwordless (acquisto
    guest) basta la sessione — l'email e' gia' provata dal login.
    """
    _flag_enabled()
    from database import platform_accounts_collection
    from auth import (get_password_hash, verify_password,
                      validate_password_strength)

    if account.get("password_hash"):
        if not body.current_password or not verify_password(
                body.current_password, account["password_hash"]):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                                detail="Password attuale non corretta")
    try:
        validate_password_strength(body.new_password)
        from core.password_breach import validate_password_not_breached
        validate_password_not_breached(body.new_password)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail=str(e))
    await platform_accounts_collection.update_one(
        {"id": account["id"]},
        {"$set": {"password_hash": get_password_hash(body.new_password)}},
    )
    return {"status": "ok"}


@router.post("/auth/logout-all", status_code=200)
async def logout_all(account: dict = Depends(get_current_platform_account)):
    """Invalida TUTTE le sessioni (i token gia' emessi vengono rifiutati)."""
    _flag_enabled()
    from database import platform_accounts_collection
    await platform_accounts_collection.update_one(
        {"id": account["id"]},
        {"$set": {"sessions_invalidated_at": utc_now().isoformat()}},
    )
    return {"status": "ok"}


# Stessa fonte di verita' del motore /pay: una riga con session gia'
# emessa (processing) resta pagabile — il /pay genera una session fresca.
from services.payment_schedule_service import PAYABLE_STATES as PAYABLE_ROW_STATES  # noqa: E402


@router.get("/me/orders")
async def get_my_orders(account: dict = Depends(get_current_platform_account)):
    """P3 — le prenotazioni dell'utente su TUTTI gli operatori.

    Aggregazione via orders.platform_account_id (stamp di P2). Espone
    SOLO dati lato-cliente: niente costi interni, note operatore, fee o
    dati di altri clienti. Le righe pagamento aperte portano il
    pay_token (link /pay eterno) — un solo posto per pagare tutto.
    """
    _flag_enabled()
    from database import (
        db,
        issued_tickets_collection,
        orders_collection,
        organizations_collection,
    )

    # AP2 — anche i cancellati: l'utente deve VEDERE che una richiesta
    # e' stata annullata (badge 'Annullato'), non trovarla sparita.
    orders = await orders_collection.find(
        {"platform_account_id": account["id"]},
        {"_id": 0, "id": 1, "order_number": 1, "organization_id": 1,
         "status": 1, "total": 1, "currency": 1, "created_at": 1,
         "payment_state": 1,
         "items.product_name": 1, "items.quantity": 1,
         "items.occurrence_start_at": 1, "items.occurrence_location": 1,
         "items.item_type": 1, "items.transaction_mode": 1,
         "items.booking_date": 1, "items.booking_start_time": 1,
         "items.booking_end_time": 1},
    ).sort("created_at", -1).to_list(200)

    if not orders:
        return {"orders": [], "total": 0}

    org_ids = list({o["organization_id"] for o in orders})
    # Il nome PUBBLICO dell'operatore e' quello dello store (display
    # name), non org.name (interno/legacy: la simulazione E2E 9/7 ha
    # mostrato 'Demo Restaurant' al posto di 'Masseria Montanari Demo').
    orgs = {o["id"]: o async for o in organizations_collection.find(
        {"id": {"$in": org_ids}},
        {"_id": 0, "id": 1, "name": 1, "store_settings.display_name": 1})}
    from database import stores_collection
    async for s in stores_collection.find(
            {"organization_id": {"$in": org_ids}, "is_published": True},
            {"_id": 0, "organization_id": 1, "name": 1}):
        if s.get("name") and s["organization_id"] in orgs:
            orgs[s["organization_id"]]["public_name"] = s["name"]

    order_ids = [o["id"] for o in orders]
    schedules = {s["order_id"]: s async for s in db.payment_schedules.find(
        {"order_id": {"$in": order_ids}},
        {"_id": 0, "order_id": 1, "payment_state": 1,
         "rows.kind": 1, "rows.amount_minor": 1, "rows.status": 1,
         "rows.due_at": 1, "rows.pay_token": 1, "rows.seq": 1})}

    tickets_by_order: dict = {}
    async for tk in issued_tickets_collection.find(
            {"order_id": {"$in": order_ids}, "status": {"$ne": "voided"}},
            {"_id": 0, "order_id": 1, "access_token": 1, "code": 1}):
        tickets_by_order.setdefault(tk["order_id"], []).append(
            {"access_token": tk.get("access_token"), "code": tk.get("code")})

    # TA2 — anche le prenotazioni servizio sono cittadine del Passaporto:
    # prima il link /b/{token} viveva solo nell'email di conferma (persa
    # l'email, perso l'appuntamento). Stessa proiezione minima dei ticket.
    from database import issued_bookings_collection
    bookings_by_order: dict = {}
    async for bk in issued_bookings_collection.find(
            {"order_id": {"$in": order_ids}, "status": {"$ne": "cancelled"}},
            {"_id": 0, "order_id": 1, "access_token": 1, "code": 1}):
        bookings_by_order.setdefault(bk["order_id"], []).append(
            {"access_token": bk.get("access_token"), "code": bk.get("code")})

    out = []
    for o in orders:
        sched = schedules.get(o["id"])
        rows = []
        for r in (sched or {}).get("rows", []):
            row = {"kind": r.get("kind"), "amount_minor": r.get("amount_minor"),
                   "status": r.get("status"), "due_at": r.get("due_at")}
            # pay link SOLO per righe realmente pagabili — e MAI su un
            # ordine annullato (AP2: gli annullati ora sono visibili qui)
            if (r.get("status") in PAYABLE_ROW_STATES and r.get("pay_token")
                    and o.get("status") != "cancelled"):
                row["pay_token"] = r["pay_token"]
            rows.append(row)
        ev = next((it for it in o.get("items", [])
                   if it.get("occurrence_start_at")), None)
        # AP2 — modo dominante dell'ordine, stessa regola del checkout
        # (order_creation_service): un solo modo → quello, misto → request.
        modes = {it.get("transaction_mode") or "request"
                 for it in o.get("items", [])}
        # AP2 — appuntamento scelto al checkout servizi (snapshot
        # booking_* sulla riga): la prima riga con uno slot.
        slot_line = next((it for it in o.get("items", [])
                          if it.get("booking_date")), None)
        out.append({
            "id": o["id"],
            "order_number": o.get("order_number"),
            "operator_name": (lambda og: og.get("public_name")
                              or (og.get("store_settings") or {}).get("display_name")
                              or og.get("name"))(orgs.get(o["organization_id"], {})),
            "status": o.get("status"),
            "transaction_mode": (modes.pop() if len(modes) == 1
                                 else "request"),
            "service_slot": ({"date": slot_line["booking_date"],
                              "start_time": slot_line.get("booking_start_time"),
                              "end_time": slot_line.get("booking_end_time")}
                             if slot_line else None),
            "total": o.get("total"),
            "currency": o.get("currency", "EUR"),
            "created_at": o.get("created_at"),
            "payment_state": (sched or {}).get("payment_state") or o.get("payment_state"),
            "retreat_title": (ev or (o.get("items") or [{}])[0]).get("product_name"),
            "start_at": (ev or {}).get("occurrence_start_at"),
            "location": (ev or {}).get("occurrence_location"),
            "seats": (ev or {}).get("quantity"),
            "payment_rows": rows,
            "tickets": tickets_by_order.get(o["id"], []),
            "bookings": bookings_by_order.get(o["id"], []),
        })
    return {"orders": out, "total": len(out)}


@router.get("/me/export")
async def export_my_data(account: dict = Depends(get_current_platform_account)):
    """GDPR — export JSON dei dati dell'identita' piattaforma + vista
    cliente delle prenotazioni. I dati interni degli operatori non
    escono da qui (titolarita' loro)."""
    _flag_enabled()
    from services.platform_account_service import export_account_data
    return await export_account_data(account)


@router.delete("/me", status_code=200)
async def delete_my_account(account: dict = Depends(get_current_platform_account)):
    """GDPR — cancella l'identita' piattaforma e scollega gli stamp.
    Ordini e documenti fiscali degli operatori restano (obblighi di
    legge loro): cancellazione a due livelli, vedi piano §3."""
    _flag_enabled()
    from services.platform_account_service import delete_account
    result = await delete_account(account)
    return {"status": "deleted", **result}
