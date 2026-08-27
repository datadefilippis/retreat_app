"""PC3 (24/8/2026) — /admin/sound: chi può COMPORRE in Aurya Sound.

Decisione founder: la creazione delle meditazioni non è più di tutti
gli operatori — è un privilegio (`organizations.sound_composer`) che
il system admin concede da una PAGINA dedicata (non un tab: richiesta
esplicita). Le superfici pubbliche (frequenze, tutorial, meditazioni
pubblicate) non c'entrano: il privilegio governa il comporre, non
l'esistere di ciò che è già stato composto.

- GET  /admin/sound/composers            → elenco org con conteggi
- POST /admin/sound/composers/{org_id}   → {enabled} + audit trail

Modellato su admin_feature_flags (require_system_admin + AuditLog).
"""

import logging

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from auth import require_system_admin
from models import AuditLog
from repositories import audit_repository

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin/sound", tags=["Admin Aurya Sound"])


class ComposerToggle(BaseModel):
    enabled: bool


@router.get("/composers")
async def list_composers(current_user: dict = Depends(require_system_admin)):
    """Tutte le org con lo stato del privilegio e i numeri del loro
    comporre (tracce totali/pubblicate, ultima attività): il contesto
    per decidere, non una lista nuda di interruttori.

    Con l'EMAIL di chi guida l'org (24/8, founder: «per identificare
    subito l'utente»): il nome dell'organizzazione non basta a
    riconoscere una persona — l'email si': e' quella con cui scrive,
    accede e a cui si risponde. Si prende l'admin dell'org (il piu'
    vecchio: chi l'ha aperta), o un membro qualunque se manca.
    """
    from database import (organizations_collection, frequency_tracks_collection,
                          users_collection)

    # una sola passata sugli utenti: l'admin piu' vecchio per org
    # (niente una query per riga — la lista cresce con la piattaforma)
    referenti = {}
    async for u in users_collection.find(
            {"organization_id": {"$ne": None}},
            {"_id": 0, "organization_id": 1, "email": 1, "role": 1,
             "created_at": 1}).sort("created_at", 1):
        org_id = u.get("organization_id")
        gia = referenti.get(org_id)
        # il primo admin vince; un 'user' tiene il posto finche' non
        # compare un admin (org senza admin: meglio un'email che nulla)
        if gia is None or (gia.get("role") != "admin" and u.get("role") == "admin"):
            referenti[org_id] = {"email": u.get("email"), "role": u.get("role")}

    conteggi = {}
    pipeline = [
        {"$group": {
            "_id": "$organization_id",
            "totali": {"$sum": 1},
            "pubblicate": {"$sum": {"$cond": [
                {"$eq": ["$status", "published"]}, 1, 0]}},
            "ultima": {"$max": "$updated_at"},
        }},
    ]
    async for r in frequency_tracks_collection.aggregate(pipeline):
        conteggi[r["_id"]] = r

    out = []
    from services.studio_access import studio_attivo
    async for org in organizations_collection.find(
            {}, {"_id": 0, "id": 1, "name": 1, "public_slug": 1,
                 "sound_composer": 1, "sound_studio_override": 1,
                 "plan": 1, "billing_status": 1}):
        c = conteggi.get(org["id"], {})
        out.append({
            "id": org["id"],
            "name": org.get("name"),
            "slug": org.get("public_slug"),
            "sound_composer": bool(org.get("sound_composer")),
            # TR1 — la CHIAVE 2, in sola lettura: si accende col Pro,
            # il pannello la MOSTRA (regia completa in un posto solo)
            "studio_attivo": studio_attivo(org),
            "studio_override": org.get("sound_studio_override"),
            "plan": org.get("plan"),
            "billing_status": org.get("billing_status"),
            "email": (referenti.get(org["id"]) or {}).get("email"),
            "tracks_total": c.get("totali", 0),
            "tracks_published": c.get("pubblicate", 0),
            "last_track_at": c.get("ultima"),
        })
    # prima chi compone, poi chi ha materiale, poi l'alfabeto
    out.sort(key=lambda o: (not o["sound_composer"],
                            -o["tracks_total"], o["name"] or ""))
    return {"items": out}


@router.post("/composers/{org_id}")
async def set_composer(org_id: str, body: ComposerToggle,
                       current_user: dict = Depends(require_system_admin)):
    from database import organizations_collection

    org = await organizations_collection.find_one(
        {"id": org_id}, {"_id": 0, "id": 1, "name": 1, "sound_composer": 1})
    if not org:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="Organizzazione non trovata.")
    prima = bool(org.get("sound_composer"))
    await organizations_collection.update_one(
        {"id": org_id}, {"$set": {"sound_composer": bool(body.enabled)}})

    await audit_repository.create(AuditLog(
        organization_id=None,
        user_id=current_user["user_id"],
        action="admin_set_sound_composer",
        resource_type="organization",
        resource_id=org_id,
        details={
            "previous_value": prima,
            "new_value": bool(body.enabled),
            "org_name": org.get("name"),
        },
    ))
    return {"id": org_id, "sound_composer": bool(body.enabled)}


class StudioOverride(BaseModel):
    """TR1 — l'interruttore d'emergenza della chiave 2: "on" accende
    Studio a mano (partnership, senza abbonamento), "off" lo spegne a
    una specifica org anche se paga, None torna alla vita normale
    (decide l'abbonamento)."""
    override: str | None = None          # "on" | "off" | None


@router.post("/studio/{org_id}")
async def set_studio_override(org_id: str, body: StudioOverride,
                              current_user: dict = Depends(require_system_admin)):
    if body.override not in (None, "on", "off"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="Override sconosciuto.")
    from database import organizations_collection
    org = await organizations_collection.find_one(
        {"id": org_id}, {"_id": 0, "id": 1, "name": 1,
                         "sound_studio_override": 1})
    if not org:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="Organizzazione non trovata.")
    prima = org.get("sound_studio_override")
    if body.override is None:
        await organizations_collection.update_one(
            {"id": org_id}, {"$unset": {"sound_studio_override": ""}})
    else:
        await organizations_collection.update_one(
            {"id": org_id},
            {"$set": {"sound_studio_override": body.override}})
    await audit_repository.create(AuditLog(
        organization_id=None,
        user_id=current_user["user_id"],
        action="admin_set_sound_studio_override",
        resource_type="organization",
        resource_id=org_id,
        details={"previous_value": prima, "new_value": body.override,
                 "org_name": org.get("name")},
    ))
    return {"id": org_id, "studio_override": body.override}
