"""La porta unica /accedi — ciclo ID (20/8/2026).

POST /api/auth/entra: una email, una password, e il server decide il
mondo — l'archivio di appartenenza e' un dettaglio NOSTRO, non una
domanda da fare all'utente. La password e' il selettore:

  - combacia su `users`            → cappello operatore;
  - combacia su `platform_accounts`→ cappello cliente;
  - combacia su entrambi           → operatore (il contesto di lavoro),
                                     e col legame arriva anche l'altro;
  - non combacia da nessuna parte  → UN solo errore generico.

SSO (decisione founder 20/8): se le identita' sono COLLEGATE
(identity_link_service, email verificata da entrambe le parti), un
login qualsiasi rilascia entrambi i token. Le chiavi e i formati dei
token NON cambiano: `token` (operatore) e `platform_token` (cliente)
restano quelli di sempre, cosi' nessuna sessione viva si invalida.

Anti-abuso: rate-limit IP 10/min (come le due porte di prima), piu' il
contatore per-email TRASVERSALE — prima ogni mondo contava per conto
suo e si poteva martellare una porta mentre l'altra dormiva.

POST /api/auth/recupero: il «password dimenticata» della porta unica —
inoltra il reset a OGNI mondo in cui l'email esiste, risposta sempre
identica (anti-enumeration).

POST /api/auth/hats/client: direzione A del piano — l'operatore chiede
il cappello cliente con un clic, zero credenziali nuove.
"""

import logging
from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field

from auth import create_platform_token, get_current_user
from core.security_config import LOCKOUT_ERROR_CODE
from routers.auth import limiter
from services import auth_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["unified-auth"])

_GENERIC_401 = "Email o password non corretti."
_PLATFORM_SESSION_DAYS = 30      # identico a routers/platform_accounts.py


class EntraRequest(BaseModel):
    email: str = Field(..., max_length=254)
    password: str = Field(..., max_length=256)


class RecuperoRequest(BaseModel):
    email: str = Field(..., max_length=254)


def _client_world(account: dict) -> dict:
    """Il cappello cliente nel formato che il frontend gia' conosce
    (stesso shape di _login_response in routers/platform_accounts.py)."""
    token = create_platform_token(
        {"sub": account["id"], "email": account["email"]},
        expires_delta=timedelta(days=_PLATFORM_SESSION_DAYS),
    )
    return {
        "type": "client",
        "access_token": token,
        "account": {"id": account["id"], "email": account["email"],
                    "name": account.get("name"),
                    "language": account.get("language", "it")},
    }


def _operator_world(token_response) -> dict:
    """Il cappello operatore, dal TokenResponse del servizio esistente."""
    return {
        "type": "operator",
        "access_token": token_response.access_token,
        "user": token_response.user.model_dump(mode="json"),
    }


async def _sso_client_for_operator(user_id: str):
    """SSO: l'operatore e' entrato — se il legame c'e', anche il
    cappello cliente entra. Solo legami veri (verificati, attivi)."""
    from database import platform_accounts_collection
    account = await platform_accounts_collection.find_one(
        {"operator_user_id": user_id, "is_active": True,
         "email_verified": True})
    return _client_world(account) if account else None


async def _sso_operator_for_client(account: dict):
    """SSO nell'altro verso: il cliente e' entrato, il legame porta
    anche il gestionale. Il token operatore e' identico a quello del
    login classico (stessi claim)."""
    from auth import create_access_token
    from database import users_collection
    op_id = account.get("operator_user_id")
    if not op_id:
        return None
    user_doc = await users_collection.find_one(
        {"id": op_id, "is_active": True, "email_verified": True})
    if not user_doc:
        return None
    token = create_access_token({
        "sub": user_doc["id"],
        "org_id": user_doc.get("organization_id"),
        "role": user_doc["role"],
        "email": user_doc["email"],
    })
    return {
        "type": "operator",
        "access_token": token,
        "user": {"id": user_doc["id"], "email": user_doc["email"],
                 "name": user_doc.get("name", ""),
                 "role": user_doc["role"],
                 "organization_id": user_doc.get("organization_id")},
    }


@router.post("/entra")
@limiter.limit("10/minute")
async def entra(request: Request, body: EntraRequest):
    from core.rate_limiting import check_email_rate
    from services.identity_link_service import auto_link_by_email
    from services.platform_account_service import (newsletter_status,
                                                   password_login)

    email = (body.email or "").strip().lower()

    # contatore TRASVERSALE per email: la porta e' una, il conto e' uno.
    # Risposta identica al fallimento normale (anti-enumeration).
    if not check_email_rate(email, "unified_login", max_per_hour=20):
        logger.info("entra: per-email rate limit. email_redacted=%s***",
                    email[:3])
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                            detail=_GENERIC_401)

    # lazy repair del legame (regola 2): costa due find indicizzate
    await auto_link_by_email(email)

    worlds = []
    operator_not_verified = False

    # ── primo tentativo: mondo operatore ────────────────────────────
    try:
        token_response = await auth_service.login(email, body.password)
        worlds.append(_operator_world(token_response))
        sso = await _sso_client_for_operator(token_response.user.id)
        if sso:
            worlds.append({**sso, **await newsletter_status(email)})
    except ValueError as e:
        msg = str(e)
        if msg.startswith(LOCKOUT_ERROR_CODE):
            # il lockout operatore si dice subito, come su /login: e'
            # post-credenziale, niente enumeration (Track S 2.1)
            unlock_at = msg.split(":", 1)[1]
            raise HTTPException(
                status_code=423,
                detail={"code": "ACCOUNT_LOCKED",
                        "message": "Account temporaneamente bloccato per troppi tentativi falliti.",
                        "unlock_at": unlock_at})
        if msg.startswith("Account deactivated"):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                                detail="Account deactivated")
        if "not verified" in msg.lower():
            # non si svela ancora: forse il cappello cliente combacia
            operator_not_verified = True
        # credenziali sbagliate → si prova l'altro mondo

    # ── secondo tentativo: mondo cliente ────────────────────────────
    if not worlds:
        try:
            account = await password_login(email, body.password)
            worlds.append({**_client_world(account),
                           **await newsletter_status(email)})
            sso = await _sso_operator_for_client(account)
            if sso:
                worlds.insert(0, sso)      # operatore sempre per primo
        except ValueError as e:
            msg = str(e)
            if msg.startswith(LOCKOUT_ERROR_CODE):
                raise HTTPException(status_code=423, detail=msg)
            if msg in ("EMAIL_NOT_VERIFIED", "ACCOUNT_DISABLED"):
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                                    detail=msg)
            # niente da nessuna parte: se il mondo operatore aveva
            # riconosciuto le credenziali ma l'email non e' verificata,
            # ORA e' giusto dirlo (parita' con /login di ieri)
            if operator_not_verified:
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                                    detail="Email not verified")
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                                detail=_GENERIC_401)

    return {"worlds": worlds}


@router.post("/recupero", status_code=200)
@limiter.limit("5/minute;20/hour")
async def recupero(request: Request, body: RecuperoRequest):
    """Password dimenticata dalla porta unica: il reset parte per OGNI
    mondo in cui l'email esiste, riusando i flussi collaudati di
    ciascuno (token, scadenze e pagine di reset INVARIATI). Risposta
    sempre identica: chi chiede non scopre dove esiste l'email."""
    from core.rate_limiting import check_email_rate

    email = (body.email or "").strip().lower()
    generic = {"message": "Se l'email esiste, riceverai le istruzioni per reimpostare la password."}
    if not email or not check_email_rate(email, "unified_forgot",
                                         max_per_hour=10):
        return generic

    # mondo operatore: riusa ESATTAMENTE la route esistente (limiti
    # per-email suoi inclusi) — zero logica di reset duplicata
    try:
        from models import ForgotPasswordRequest
        from routers.auth import forgot_password
        await forgot_password(request, ForgotPasswordRequest(email=email))
    except Exception:
        logger.warning("recupero: ramo operatore fallito", exc_info=True)

    # mondo cliente: idem, via il servizio della piattaforma
    try:
        from services.platform_account_service import request_password_reset
        await request_password_reset(email)
    except Exception:
        logger.warning("recupero: ramo cliente fallito", exc_info=True)

    return generic


@router.post("/hats/client")
@limiter.limit("10/hour")
async def request_client_hat(request: Request,
                             current_user: dict = Depends(get_current_user)):
    """«Usa Aurya come cliente» — un clic, zero credenziali nuove.
    Il cappello nasce (o si collega) dall'identita' operatore gia'
    verificata; dal login successivo la porta unica rilascia entrambi
    i token. Mai automatico: solo su questo gesto esplicito."""
    from database import users_collection
    from services.identity_link_service import ensure_client_hat_for_operator
    # get_current_user ritorna un contesto ({user_id, ...}), non il
    # documento: il cappello nasce dal documento autoritativo del DB
    user_doc = await users_collection.find_one({"id": current_user["user_id"]})
    if not user_doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="Utente non trovato.")
    try:
        result = await ensure_client_hat_for_operator(user_doc)
        # ID-quinquies (20/8) — il cappello si indossa SUBITO: la
        # risposta porta anche il token cliente, cosi' chi ha chiesto
        # «usa Aurya come cliente» entra senza un secondo accesso.
        # Legittimo: chi chiede e' gia' autenticato, e il cappello e'
        # suo (stessa email verificata).
        from database import platform_accounts_collection
        account = await platform_accounts_collection.find_one(
            {"id": result["account_id"]}, {"_id": 0})
        if account:
            result = {**result, **_client_world(account)}
    except ValueError as e:
        msg = str(e)
        if msg == "OPERATOR_EMAIL_NOT_VERIFIED":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Prima verifica l'email del tuo account operatore.")
        if msg == "CLIENT_ACCOUNT_UNVERIFIED":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Esiste già un account cliente con questa email, ma non è mai stato verificato. Verificalo (o recupera la password) e il collegamento nascerà da solo.")
        raise
    return result
