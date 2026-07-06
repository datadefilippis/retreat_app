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


class CodeVerify(BaseModel):
    email: str
    code: str


@router.post("/auth/code/verify")
@limiter.limit("10/minute")
async def verify_login_code_ep(body: CodeVerify, request: Request):
    """Login col codice a 6 cifre (stessa email del magic link)."""
    _flag_enabled()
    from services.platform_account_service import verify_login_code
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

    orders = await orders_collection.find(
        {"platform_account_id": account["id"],
         "status": {"$ne": "cancelled"}},
        {"_id": 0, "id": 1, "order_number": 1, "organization_id": 1,
         "status": 1, "total": 1, "currency": 1, "created_at": 1,
         "payment_state": 1,
         "items.product_name": 1, "items.quantity": 1,
         "items.occurrence_start_at": 1, "items.occurrence_location": 1,
         "items.item_type": 1},
    ).sort("created_at", -1).to_list(200)

    if not orders:
        return {"orders": [], "total": 0}

    org_ids = list({o["organization_id"] for o in orders})
    orgs = {o["id"]: o async for o in organizations_collection.find(
        {"id": {"$in": org_ids}}, {"_id": 0, "id": 1, "name": 1})}

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

    out = []
    for o in orders:
        sched = schedules.get(o["id"])
        rows = []
        for r in (sched or {}).get("rows", []):
            row = {"kind": r.get("kind"), "amount_minor": r.get("amount_minor"),
                   "status": r.get("status"), "due_at": r.get("due_at")}
            # pay link SOLO per righe realmente pagabili
            if r.get("status") in PAYABLE_ROW_STATES and r.get("pay_token"):
                row["pay_token"] = r["pay_token"]
            rows.append(row)
        ev = next((it for it in o.get("items", [])
                   if it.get("occurrence_start_at")), None)
        out.append({
            "id": o["id"],
            "order_number": o.get("order_number"),
            "operator_name": orgs.get(o["organization_id"], {}).get("name"),
            "status": o.get("status"),
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
