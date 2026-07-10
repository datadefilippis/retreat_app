"""Lead pre-lancio — raccolta contatti dalle due landing (PL2).

POST /api/public/leads   pubblico, rate-limited: salva il lead in
                         `prelaunch_leads` (dedup per email+tipo) e manda
                         una notifica a info@aurya.life. Best-effort:
                         un errore email non fa fallire la raccolta.
GET  /api/admin/leads    system admin: lista + conteggi, esportabile.

Al lancio i lead restano (sono contatti veri): non vengono toccati dal
wipe dei sample. Se vuoi ripartire puliti, si svuota la collection a mano.
"""

import logging
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, EmailStr, Field

from routers.auth import limiter
from auth import require_system_admin

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Leads"])

_TYPES = ("operator", "traveler")


class LeadPayload(BaseModel):
    email: EmailStr
    type: str = Field(max_length=20)
    name: Optional[str] = Field(default=None, max_length=120)
    message: Optional[str] = Field(default=None, max_length=1000)
    language: Optional[str] = Field(default=None, max_length=5)
    # GDPR: consenso esplicito richiesto (il form lo impone)
    consent: bool = False


@router.post("/public/leads", status_code=201)
@limiter.limit("10/minute")
async def create_lead(request: Request, payload: LeadPayload):
    """Registra un lead dalle landing di pre-lancio. Idempotente per
    (email, tipo): un secondo invio aggiorna, non duplica."""
    from database import db

    lead_type = payload.type if payload.type in _TYPES else "traveler"
    email = payload.email.lower().strip()
    now = datetime.now(timezone.utc)

    doc_set = {
        "name": (payload.name or "").strip()[:120] or None,
        "message": (payload.message or "").strip()[:1000] or None,
        "language": (payload.language or "")[:5] or None,
        "consent": bool(payload.consent),
        "updated_at": now,
    }
    try:
        res = await db.prelaunch_leads.update_one(
            {"email": email, "type": lead_type},
            {"$set": doc_set,
             "$setOnInsert": {"email": email, "type": lead_type,
                              "created_at": now}},
            upsert=True,
        )
        is_new = res.upserted_id is not None
    except Exception as exc:               # noqa: BLE001 — mai rompere il form
        logger.warning("lead save failed: %s", exc)
        # rispondiamo comunque ok: il lead non deve vedere errori
        return {"ok": True}

    # notifica best-effort a info@ (solo per i lead nuovi, niente spam)
    if is_new:
        try:
            from services.email_service import send_email
            label = "operatore" if lead_type == "operator" else "viaggiatore"
            html = (
                f"<h2>Nuovo lead pre-lancio Aurya</h2>"
                f"<p><b>Tipo:</b> {label}</p>"
                f"<p><b>Email:</b> {email}</p>"
                f"<p><b>Nome:</b> {doc_set['name'] or '—'}</p>"
                f"<p><b>Messaggio:</b> {doc_set['message'] or '—'}</p>"
            )
            send_email("info@aurya.life",
                       f"Nuovo lead {label}: {email}", html,
                       reply_to=email)
        except Exception as exc:           # noqa: BLE001
            logger.debug("lead notify skipped: %s", exc)

    return {"ok": True}


@router.get("/admin/leads")
async def list_leads(
    limit: int = 500,
    current_user: dict = Depends(require_system_admin),
):
    """Lista lead + conteggi per tipo (system admin). Esportabile al
    lancio per contattare chi si è iscritto."""
    from database import db
    rows = await db.prelaunch_leads.find(
        {}, {"_id": 0}).sort("created_at", -1).to_list(min(limit, 2000))
    counts = {"operator": 0, "traveler": 0}
    for r in rows:
        counts[r.get("type", "traveler")] = \
            counts.get(r.get("type", "traveler"), 0) + 1
    return {"items": rows, "total": len(rows), "counts": counts}
