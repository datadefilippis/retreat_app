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
    language: str = Field("it", max_length=5)


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
    try:
        await _req(body.email, name=body.name, language=body.language)
    except Exception:
        # mai esporre errori interni su questo endpoint
        import logging
        logging.getLogger(__name__).exception("magic-link request fallita")
    return {"status": "accepted"}


@router.post("/auth/magic-link/verify")
@limiter.limit("10/minute")
async def verify_magic_link(body: MagicLinkVerify, request: Request):
    """Consuma il token one-shot e ritorna il JWT piattaforma (30gg)."""
    _flag_enabled()
    from services.platform_account_service import consume_magic_link
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
    }


@router.get("/me")
async def get_me(account: dict = Depends(get_current_platform_account)):
    _flag_enabled()
    return {k: account.get(k) for k in
            ("id", "email", "name", "phone", "language",
             "email_verified", "created_at", "last_login_at")}


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
