"""Lotto B3 (24/9/2026) — la verifica «per uso», non «per rito».

Qualsiasi clic su qualsiasi link di qualsiasi email che mandiamo
dimostra che l'indirizzo e' di chi lo legge. Qui c'e' l'unica funzione
che lo annota, per i due mondi (iscritti del Cerchio e utenti con
account), e il link firmato che le email usano per farlo.

Contratto (lo importa il Lotto C nelle email delle sequenze):

    async def segna_verificato(email, tipo, dettaglio="") -> dict
    def link_verificante(email, path) -> str

Effetti di segna_verificato (idempotente):
  aurya_subscribers → verificato_at, verificato_da{tipo, dettaglio}
                      (solo la PRIMA prova: le successive non la
                      riscrivono); se status == "pending" → confirmed +
                      confirmed_at, cioe' la conferma implicita: i sei
                      cancelli restano legati a status == "confirmed" e
                      parte invia_subito("cerchio") come oggi alla
                      conferma; consenso.modalita → doppio (manuale se
                      lo fa l'admin); riga in consent_audit.
  users (stessa email) → email_verified True se era falso.

docs/ANALISI_SYSTEM_ADMIN_2026-09-24.md §6.2.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Optional
from urllib.parse import quote

logger = logging.getLogger(__name__)

TIPI = ("conferma", "clic", "otp", "admin")


def _mask(email: str) -> str:
    local, _, domain = (email or "").partition("@")
    return f"{local[:1]}***@{domain}"


def link_verificante(email: str, path: str) -> str:
    """URL assoluto che al clic verifica l'indirizzo e porta a `path`
    (solo percorsi interni: la rotta scarta il resto)."""
    from core.subscriber_token import generate_subscriber_token
    from services.url_builder import build_public_url
    token = generate_subscriber_token(email)
    dove = percorso_interno(path)
    return build_public_url(f"/api/public/newsletter/v/{token}") + f"?to={quote(dove, safe='/')}"


def percorso_interno(raw: Optional[str]) -> str:
    """Mai un open redirect: solo un percorso che comincia con «/»."""
    p = (raw or "").strip()
    if not p.startswith("/") or p.startswith("//") or "\\" in p or "\n" in p or "\r" in p:
        return "/"
    return p[:500]


async def registra_consenso_audit(email: str, source: str, sub: Optional[dict] = None,
                                  ip: Optional[str] = None, user_agent: Optional[str] = None) -> None:
    """Riga in consent_audit per un evento del Cerchio (subscribe,
    confirm, unsubscribe, admin_confirm): version_tag e hash del testo
    dal registro sull'iscritto. Best effort, mai un raise."""
    try:
        from database import db
        from repositories.consent_audit_repository import (hash_document_text,
                                                           record_consent)
        from services.testi_consenso import VERSIONE_CORRENTE, testo
        if sub is None:
            sub = await db.aurya_subscribers.find_one(
                {"email": email}, {"_id": 0, "consenso": 1, "language": 1}) or {}
        cons = sub.get("consenso") or {}
        versione = cons.get("versione") or VERSIONE_CORRENTE
        txt = cons.get("testo") or testo(versione)
        await record_consent(
            user_id=None, customer_email=email,
            locale=(sub.get("language") or "it")[:2] or "it",
            version_tag=versione, version_hash=hash_document_text(txt),
            ip_address=ip, user_agent=user_agent,
            source=source, document_type="aurya_newsletter")
    except Exception as exc:                # noqa: BLE001
        logger.warning("consent_audit %s non scritta per %s: %s", source, _mask(email), exc)


async def segna_verificato(email: str, tipo: str, dettaglio: str = "") -> dict:
    """Annota la prova che l'indirizzo e' suo. Ritorna cosa e' successo:
    {email, iscritto, era_verificato, verificato_at, confermato_ora, status}."""
    from database import db, users_collection

    email = (email or "").strip().lower()
    tipo = tipo if tipo in TIPI else "clic"
    dettaglio = (dettaglio or "").strip()[:300]
    now = datetime.now(timezone.utc)
    esito = {"email": email, "iscritto": False, "era_verificato": False,
             "verificato_at": None, "confermato_ora": False, "status": None}
    if not email:
        return esito

    sub = await db.aurya_subscribers.find_one(
        {"email": email},
        {"_id": 0, "status": 1, "verificato_at": 1, "consenso": 1, "language": 1})
    if sub:
        esito["iscritto"] = True
        esito["era_verificato"] = bool(sub.get("verificato_at"))
        esito["verificato_at"] = sub.get("verificato_at") or now
        esito["status"] = sub.get("status") or "pending"
        set_: dict = {"updated_at": now}
        if not sub.get("verificato_at"):
            set_["verificato_at"] = now
            set_["verificato_da"] = {"tipo": tipo, "dettaglio": dettaglio, "at": now}
        modalita_nuova = "manuale" if tipo == "admin" else "doppio"
        cons = sub.get("consenso") or {}
        if cons and cons.get("modalita") not in ("doppio", "manuale", "prelancio"):
            set_["consenso.modalita"] = modalita_nuova
        confermato_ora = sub.get("status") == "pending"
        if confermato_ora:
            set_["status"] = "confirmed"
            set_["confirmed_at"] = now
            if not cons:
                # iscritto senza registro (prima del 24/9): la conferma
                # e' comunque una prova, la si annota
                set_["consenso.modalita"] = modalita_nuova
        await db.aurya_subscribers.update_one({"email": email}, {"$set": set_})
        esito["status"] = "confirmed" if confermato_ora else esito["status"]
        esito["confermato_ora"] = confermato_ora
        if confermato_ora:
            await registra_consenso_audit(
                email, "newsletter_admin_confirm" if tipo == "admin" else "newsletter_confirm", sub)
            try:
                from services.subscriber_brevo_sync import sync_subscriber_background
                sync_subscriber_background(email)
            except Exception as exc:        # noqa: BLE001
                logger.warning("brevo sync dopo verifica fallito per %s: %s", _mask(email), exc)
            try:
                from services.sequenze import invia_subito
                await invia_subito("cerchio", email)
            except Exception as exc:        # noqa: BLE001 — la verifica non si rompe per un'email
                logger.warning("benvenuto Cerchio non inviato a %s: %s", _mask(email), exc)

    # l'account con la stessa email (operatore o cliente della piattaforma)
    try:
        r = await users_collection.update_one(
            {"email": email, "email_verified": {"$ne": True}},
            {"$set": {"email_verified": True,
                      "email_verified_da": {"tipo": tipo, "dettaglio": dettaglio, "at": now},
                      "updated_at": now.isoformat()}})
        esito["account_verificato_ora"] = r.modified_count == 1
    except Exception as exc:                # noqa: BLE001
        logger.warning("email_verified non aggiornato per %s: %s", _mask(email), exc)
        esito["account_verificato_ora"] = False
    # E6: la pagina dell'operatore, pronta ma ferma in attesa della
    # verifica, esce al primo clic verificante. Best-effort.
    if esito.get("account_verificato_ora"):
        try:
            u = await users_collection.find_one({"email": email}, {"_id": 0, "organization_id": 1})
            if u and u.get("organization_id"):
                from routers.organizations import _ensure_public_surface
                await _ensure_public_surface(u["organization_id"])
        except Exception as exc:            # noqa: BLE001
            logger.warning("pagina dopo verifica non aggiornata per %s: %s", _mask(email), exc)
    return esito
