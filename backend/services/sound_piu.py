"""SN4 (8/10/2026, piano Aurya Sound §5.2) — AURYA PIÙ, l'ossatura dell'abbonamento.

L'abbonamento ascoltatore (decisione 5: 39 €/anno, solo annuale) vive
sull'ACCOUNT Aurya (`platform_accounts.piu`), si compra con Stripe
Checkout sul conto di Aurya (non Connect: i soldi sono di Aurya), si
gestisce dal portale Stripe (carta, fattura, disdetta) e si aggiorna dai
webhook. Tutto SCRITTO e PROVATO, ma SPENTO: `SOUND_PIU_ATTIVO` (ambiente)
chiude checkout e portale finche' il founder non accende; il flag si
legge a ogni chiamata, mai in cima al modulo.

Nessun paywall qui: chi e' nel Più si vede (`abbonato`), cosa chiudere al
Più lo decide il player il giorno dell'accensione (docs/SOUND_PIU_ACCENSIONE).
"""
from __future__ import annotations

import asyncio
import logging
import os
from datetime import datetime, timezone
from typing import Any, Dict, Optional

logger = logging.getLogger("aurya.sound_piu")

PREZZO_EUR_ANNO = 39
STATI_ABBONATO = ("active", "trialing", "past_due")   # past_due: Stripe ritenta, l'ascolto non si spegne subito


def attivo() -> bool:
    return (os.getenv("SOUND_PIU_ATTIVO") or "").strip().lower() in ("1", "true", "on", "si", "sì", "yes")


def price_id() -> str:
    return (os.getenv("STRIPE_PIU_PRICE_ID") or "").strip()


def _ts(v) -> Optional[datetime]:
    try:
        return datetime.fromtimestamp(int(v), tz=timezone.utc) if v else None
    except Exception:  # noqa: BLE001
        return None


def _omaggio_valido(piu: dict) -> bool:
    fino = (piu or {}).get("omaggio_until")
    if not fino:
        return False
    if isinstance(fino, str):
        try:
            fino = datetime.fromisoformat(fino.replace("Z", "+00:00"))
        except ValueError:
            return False
    if fino.tzinfo is None:
        fino = fino.replace(tzinfo=timezone.utc)
    return fino > datetime.now(timezone.utc)


def stato_account(account: dict) -> Dict[str, Any]:
    """Lo stato del Più per l'account: cosa mostra la sezione nell'account e
    la regia. `abbonato` = ascolta il Più (abbonamento vivo o omaggio)."""
    piu = account.get("piu") or {}
    status = piu.get("status")
    abbonato = status in STATI_ABBONATO or _omaggio_valido(piu)
    return {
        "attivo": attivo(),
        "prezzo_eur_anno": PREZZO_EUR_ANNO,
        "abbonato": bool(abbonato),
        "status": status,
        "current_period_end": piu.get("current_period_end"),
        "cancel_at_period_end": bool(piu.get("cancel_at_period_end")),
        "omaggio_until": piu.get("omaggio_until"),
        "ha_cliente_stripe": bool(account.get("stripe_customer_id")),
    }


def piu_da_subscription(sub: dict) -> Dict[str, Any]:
    """Pura: dall'oggetto Subscription di Stripe (dict) ai campi dell'account."""
    items = ((sub.get("items") or {}).get("data") or [])
    fine = sub.get("current_period_end")
    if fine is None and items:
        fine = items[0].get("current_period_end")
    return {
        "status": sub.get("status"),
        "stripe_subscription_id": sub.get("id"),
        "current_period_end": _ts(fine),
        "cancel_at_period_end": bool(sub.get("cancel_at_period_end")),
        "updated_at": datetime.now(timezone.utc),
    }


async def _stripe():
    from services.stripe_service import _get_stripe
    return _get_stripe()


async def cliente_stripe(account: dict) -> str:
    """Il cliente Stripe dell'account: quello salvato, altrimenti uno nuovo
    (email e nome dell'account, l'id Aurya nei metadata)."""
    from database import platform_accounts_collection
    stripe = await _stripe()
    cus = account.get("stripe_customer_id")
    if cus:
        return cus
    c = await asyncio.to_thread(
        stripe.Customer.create,
        email=account.get("email"), name=account.get("name") or None,
        metadata={"platform_account_id": account["id"], "aurya": "piu"})
    await platform_accounts_collection.update_one({"id": account["id"]}, {"$set": {"stripe_customer_id": c.id}})
    return c.id


async def crea_checkout(account: dict, success_url: str, cancel_url: str) -> Dict[str, str]:
    """La sessione di Checkout (abbonamento annuale, prezzo da ambiente)."""
    if not price_id():
        raise ValueError("STRIPE_PIU_PRICE_ID mancante: il prezzo del Più non è configurato.")
    stripe = await _stripe()
    cus = await cliente_stripe(account)
    s = await asyncio.to_thread(
        stripe.checkout.Session.create,
        mode="subscription", customer=cus, locale="it",
        line_items=[{"price": price_id(), "quantity": 1}],
        allow_promotion_codes=True,
        success_url=success_url, cancel_url=cancel_url,
        metadata={"platform_account_id": account["id"], "aurya_piu": "1"},
        subscription_data={"metadata": {"platform_account_id": account["id"], "aurya_piu": "1"}},
    )
    return {"url": s.url, "id": s.id}


async def crea_portale(account: dict, return_url: str) -> Dict[str, str]:
    cus = account.get("stripe_customer_id")
    if not cus:
        raise ValueError("Nessun cliente Stripe per questo account.")
    stripe = await _stripe()
    s = await asyncio.to_thread(stripe.billing_portal.Session.create, customer=cus, return_url=return_url)
    return {"url": s.url}


def costruisci_evento(payload: bytes, firma: str) -> dict:
    """Verifica la firma con il segreto del Più (o quello di piattaforma) e
    restituisce l'evento come dict."""
    import json
    from services.stripe_service import _get_stripe
    stripe = _get_stripe()
    segreti = [s for s in (os.getenv("STRIPE_PIU_WEBHOOK_SECRET"), os.getenv("STRIPE_WEBHOOK_SECRET")) if s]
    if not segreti:
        raise ValueError("nessun segreto webhook configurato")
    ultimo = None
    for segreto in segreti:
        try:
            ev = stripe.Webhook.construct_event(payload, firma, segreto)
            return json.loads(json.dumps(ev, default=str)) if not isinstance(ev, dict) else ev
        except Exception as exc:  # noqa: BLE001
            ultimo = exc
    raise ValueError(str(ultimo))


async def _account_per_evento(obj: dict) -> Optional[dict]:
    from database import platform_accounts_collection
    pid = ((obj.get("metadata") or {}).get("platform_account_id"))
    if pid:
        a = await platform_accounts_collection.find_one({"id": pid}, {"_id": 0})
        if a:
            return a
    cus = obj.get("customer")
    if isinstance(cus, dict):
        cus = cus.get("id")
    if cus:
        return await platform_accounts_collection.find_one({"stripe_customer_id": cus}, {"_id": 0})
    return None


async def applica_evento(event: dict) -> Dict[str, Any]:
    """Un evento Stripe → i campi `piu` dell'account. Idempotente: il lucchetto
    per event id e' quello del billing (stessa collezione, stessa regola)."""
    from database import platform_accounts_collection
    from repositories import billing_repository
    etype = event.get("type") or ""
    eid = event.get("id") or ""
    obj = ((event.get("data") or {}).get("object") or {})
    if eid:
        lock = await billing_repository.try_acquire_event_lock(eid, etype)
        if not lock.get("acquired"):
            return {"status": "duplicate", "event_type": etype}
    esito: Dict[str, Any] = {"status": "ignored", "event_type": etype}
    try:
        if etype == "checkout.session.completed":
            if (obj.get("mode") == "subscription" and (obj.get("metadata") or {}).get("aurya_piu") == "1"):
                account = await _account_per_evento(obj)
                if account:
                    stripe = await _stripe()
                    sub_id = obj.get("subscription")
                    sub = await asyncio.to_thread(stripe.Subscription.retrieve, sub_id) if sub_id else None
                    campi = piu_da_subscription(dict(sub)) if sub else {"status": "active", "updated_at": datetime.now(timezone.utc)}
                    await platform_accounts_collection.update_one(
                        {"id": account["id"]},
                        {"$set": {"piu": {**(account.get("piu") or {}), **campi},
                                  "stripe_customer_id": obj.get("customer") or account.get("stripe_customer_id")}})
                    esito = {"status": "ok", "event_type": etype, "account_id": account["id"]}
        elif etype in ("customer.subscription.created", "customer.subscription.updated", "customer.subscription.deleted"):
            if (obj.get("metadata") or {}).get("aurya_piu") == "1" or (obj.get("metadata") or {}).get("platform_account_id"):
                account = await _account_per_evento(obj)
                if account:
                    campi = piu_da_subscription(obj)
                    if etype.endswith("deleted"):
                        campi["status"] = "canceled"
                    await platform_accounts_collection.update_one(
                        {"id": account["id"]}, {"$set": {"piu": {**(account.get("piu") or {}), **campi}}})
                    esito = {"status": "ok", "event_type": etype, "account_id": account["id"]}
        elif etype == "invoice.payment_failed":
            account = await _account_per_evento(obj)
            if account and (account.get("piu") or {}).get("stripe_subscription_id") == obj.get("subscription"):
                await platform_accounts_collection.update_one(
                    {"id": account["id"]}, {"$set": {"piu.status": "past_due", "piu.updated_at": datetime.now(timezone.utc)}})
                esito = {"status": "ok", "event_type": etype, "account_id": account["id"]}
        if eid:
            await billing_repository.mark_event_processed(eid, payload_summary={k: v for k, v in esito.items() if k != "status"})
    except Exception as exc:  # noqa: BLE001
        logger.error("sound_piu: evento %s (%s) fallito: %s", eid, etype, exc)
        if eid:
            try:
                await billing_repository.mark_event_processed(eid, error=str(exc))
            except Exception:  # noqa: BLE001
                pass
        esito = {"status": "error", "event_type": etype, "error": str(exc)}
    return esito
