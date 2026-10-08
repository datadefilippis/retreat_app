"""SN4 (8/10/2026, piano Aurya Sound §5.2) — le porte del Più.

  GET  /platform/me/piu            → lo stato (sempre: dice anche se il Più e' acceso)
  POST /platform/me/piu/checkout   → Stripe Checkout (404 finche' SOUND_PIU_ATTIVO e' spento)
  POST /platform/me/piu/portale    → portale Stripe (carta, fatture, disdetta)
  POST /public/sound/piu/webhook   → gli eventi Stripe del Più (segreto proprio)

Tutto sull'account Aurya (`get_current_platform_account`), mai sull'org.
"""
import logging
import os

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel

from auth import get_current_platform_account
from services import sound_piu

logger = logging.getLogger("aurya.sound_piu")
router = APIRouter(tags=["Aurya Più"])


def _spento_404():
    if not sound_piu.attivo():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Il Più non è ancora acceso.")


def _frontend() -> str:
    from services.url_builder import build_public_url
    return build_public_url("").rstrip("/")


@router.get("/platform/me/piu")
async def stato_piu(account: dict = Depends(get_current_platform_account)):
    return sound_piu.stato_account(account)


class _Ritorno(BaseModel):
    ritorno: str = "/account#meditazioni"


@router.post("/platform/me/piu/checkout")
async def checkout_piu(body: _Ritorno = None, account: dict = Depends(get_current_platform_account)):
    _spento_404()
    st = sound_piu.stato_account(account)
    if st["abbonato"] and st["status"] in sound_piu.STATI_ABBONATO:
        raise HTTPException(status_code=409, detail="Sei già nel Più: gestiscilo dal portale.")
    base = _frontend()
    ritorno = (body.ritorno if body else "/account#meditazioni")
    if not ritorno.startswith("/"):
        ritorno = "/account#meditazioni"
    try:
        return await sound_piu.crea_checkout(
            account, success_url=f"{base}/account?piu=ok#meditazioni", cancel_url=f"{base}/meditazioni/piu?annullato=1")
    except ValueError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    except Exception as exc:  # noqa: BLE001 — Stripe giù: mai un 500 muto
        logger.error("sound_piu checkout: %s", exc)
        raise HTTPException(status_code=502, detail="Stripe non risponde: riprova tra poco.")


@router.post("/platform/me/piu/portale")
async def portale_piu(account: dict = Depends(get_current_platform_account)):
    _spento_404()
    try:
        return await sound_piu.crea_portale(account, return_url=f"{_frontend()}/account#meditazioni")
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    except Exception as exc:  # noqa: BLE001
        logger.error("sound_piu portale: %s", exc)
        raise HTTPException(status_code=502, detail="Stripe non risponde: riprova tra poco.")


@router.post("/public/sound/piu/webhook")
async def webhook_piu(request: Request):
    firma = request.headers.get("stripe-signature", "")
    if not firma:
        raise HTTPException(status_code=400, detail="Missing stripe-signature header")
    payload = await request.body()
    try:
        event = sound_piu.costruisci_evento(payload, firma)
    except ValueError as exc:
        logger.warning("sound_piu webhook: firma non valida: %s", exc)
        raise HTTPException(status_code=400, detail="Invalid webhook signature")
    esito = await sound_piu.applica_evento(event)
    return {"received": True, **{k: v for k, v in esito.items() if k in ("status", "event_type")}}
