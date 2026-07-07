"""Outreach contestuale — il ponte insight→azione (CF2, INSIGHTS_ACTION_PLAN).

Un solo endpoint: componi il messaggio giusto per il contesto giusto
e restituisci il deep-link (mailto: / wa.me) pronto per window.open.
L'invio resta UMANO: nessun automatismo, l'operatore vede il testo,
può modificarlo nel client e decide lui se premere invio.

Regole:
  - contesti transazionali (payment_reminder, pre_retreat,
    post_retreat_review) → sempre disponibili: esiste un rapporto
    contrattuale con il cliente;
  - winback = marketing → SOLO con consenso registrato e non revocato
    (customers.accepted_marketing_at / marketing_revoked_at) → 403
    ``no_marketing_consent`` altrimenti. Serve un customer_id: niente
    winback verso contatti raw;
  - il contatto arriva o da customer_id (lookup org-scoped) o raw
    {name, email, phone} (es. partecipante evento da attendees);
  - variabili contestuali whitelisted e troncate: il template resta
    leggibile anche con contesto parziale (missing → stringa vuota);
  - review_link NON è input del client: lo costruiamo noi dallo slug
    pubblico dell'org (nessuna URL arbitraria nei messaggi).
"""

import logging
from typing import Dict, Optional

from services.module_access import require_module
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from auth import require_admin

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/outreach", tags=["Outreach"],
                   dependencies=[Depends(require_module("outreach"))])

# contesto → template in customer_outreach/templates/library.json
CONTEXT_TEMPLATES = {
    "payment_reminder": "payment_reminder",
    "pre_retreat": "pre_retreat",
    "post_retreat_review": "post_retreat_review",
    "winback": "winback",
    "appointment": "appointment_reminder",
    "generic": "general_check_in",
}

# Variabili contestuali ammesse dal client (troncate a 120 char).
# review_link è ESCLUSO di proposito: server-side only.
_ALLOWED_VARS = {
    "amount", "due_date", "order_number",
    "retreat_name", "start_date", "location",
}
_VAR_MAX = 120


class OutreachBuildRequest(BaseModel):
    context: str = Field(min_length=1, max_length=40)
    channel: str = Field(min_length=1, description="mailto | whatsapp")
    locale: str = Field(default="it", max_length=5)
    # o un cliente CRM…
    customer_id: Optional[str] = Field(default=None, max_length=64)
    # …o un contatto raw (es. partecipante evento)
    contact_name: Optional[str] = Field(default=None, max_length=120)
    contact_email: Optional[str] = Field(default=None, max_length=254)
    contact_phone: Optional[str] = Field(default=None, max_length=40)
    vars: Optional[Dict[str, str]] = None


async def _org_review_link(org_id: str) -> str:
    """Link alla vetrina pubblica (/o/{slug}) dove vive il flusso
    recensioni — dallo store pubblicato dell'org, non dal client."""
    from database import stores_collection, organizations_collection
    from services.url_builder import build_public_url

    store = await stores_collection.find_one(
        {"organization_id": org_id, "is_published": True, "is_active": True},
        {"_id": 0, "slug": 1})
    slug = (store or {}).get("slug")
    if not slug:
        org = await organizations_collection.find_one(
            {"id": org_id}, {"_id": 0, "public_slug": 1})
        slug = (org or {}).get("public_slug")
    return build_public_url(f"/o/{slug}") if slug else build_public_url("")


@router.post("/build")
async def build_contextual_outreach(
    payload: OutreachBuildRequest,
    current_user: dict = Depends(require_admin),
):
    """Compone template contestuale + canale → deep-link + audit."""
    from services.customer_outreach import log_outreach
    from services.customer_outreach.channels.base import CustomerContact

    template_key = CONTEXT_TEMPLATES.get(payload.context)
    if not template_key:
        raise HTTPException(status_code=400, detail={
            "error": "unknown_context",
            "message": f"Contesto sconosciuto: {payload.context!r}",
        })

    org_id = current_user["organization_id"]
    user_id = current_user.get("user_id") or current_user.get("id") or "unknown"

    # ── risoluzione contatto ────────────────────────────────────────────
    customer_doc = None
    if payload.customer_id:
        from database import customers_collection
        customer_doc = await customers_collection.find_one(
            {"id": payload.customer_id, "organization_id": org_id},
            {"_id": 0, "id": 1, "name": 1, "email": 1, "phone": 1,
             "accepted_marketing_at": 1, "marketing_revoked_at": 1})
        if customer_doc is None:
            raise HTTPException(status_code=404, detail="Customer not found")
        contact = CustomerContact(
            id=customer_doc["id"],
            name=customer_doc.get("name") or "",
            email=customer_doc.get("email"),
            phone=customer_doc.get("phone"),
        )
    elif payload.contact_email or payload.contact_phone:
        contact = CustomerContact(
            id="raw-contact",
            name=(payload.contact_name or "").strip(),
            email=payload.contact_email,
            phone=payload.contact_phone,
        )
    else:
        raise HTTPException(status_code=400, detail={
            "error": "no_contact",
            "message": "Serve customer_id oppure contact_email/contact_phone",
        })

    # ── gate GDPR: winback è marketing ──────────────────────────────────
    if payload.context == "winback":
        consented = bool(
            customer_doc
            and customer_doc.get("accepted_marketing_at")
            and not customer_doc.get("marketing_revoked_at")
        )
        if not consented:
            raise HTTPException(status_code=403, detail={
                "error": "no_marketing_consent",
                "message": "Questo cliente non ha dato (o ha revocato) il "
                           "consenso marketing: il ricontatto promozionale "
                           "non è consentito.",
            })

    # ── variabili contestuali ───────────────────────────────────────────
    extra = {k: str(v)[:_VAR_MAX]
             for k, v in (payload.vars or {}).items() if k in _ALLOWED_VARS}
    if payload.context == "post_retreat_review":
        extra["review_link"] = await _org_review_link(org_id)

    from database import organizations_collection
    org = await organizations_collection.find_one(
        {"id": org_id}, {"_id": 0, "name": 1})
    merchant_name = (org or {}).get("name") or ""

    locale = payload.locale if payload.locale in ("it", "en", "de", "fr") else "it"
    try:
        from services.customer_outreach.templates import loader as templates
        rendered = templates.render(
            template_key, locale,
            customer_name=contact.name,
            merchant_name=merchant_name,
            extra=extra,
        )
        if rendered is None:
            raise ValueError(f"Unknown template {template_key!r}")
        from services.customer_outreach.channels.registry import OutreachChannelRegistry
        impl = OutreachChannelRegistry.get_by_name(payload.channel)
        if impl is None:
            raise ValueError(f"Unknown channel {payload.channel!r}")
        if not impl.supports(contact):
            raise HTTPException(status_code=400, detail={
                "error": "channel_unsupported",
                "message": "Il contatto non supporta questo canale "
                           "(email mancante o telefono non valido)",
            })
        link = impl.build_link(contact, subject=rendered["subject"],
                               body=rendered["body"])
    except NotImplementedError as exc:
        raise HTTPException(status_code=501, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    await log_outreach(
        org_id, user_id, contact.id,
        channel=payload.channel, template=f"ctx:{payload.context}",
    )

    return {
        "channel": link.channel,
        "url": link.url,
        "subject": link.subject,
        "body": link.body,
    }
