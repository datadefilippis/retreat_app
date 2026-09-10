"""La richiesta dell'operatore: «Cerco una struttura per un ritiro» (SR, fase 0).

L'unica cosa che il gestionale del professionista sa delle strutture:
un modulo breve che crea una richiesta. La lista delle strutture non
si vede da qui (e' riservata a voi in fase 0). Tutto il resto vive nel
pannello di sistema.
"""
from typing import Literal, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from auth import require_admin
from repositories import struttura_repository as repo

router = APIRouter(prefix="/strutture", tags=["Strutture (operatori)"])


class RichiestaCrea(BaseModel):
    zona: str = Field(min_length=2, max_length=120)            # regione o zona («Puglia», «Alpi»)
    periodo: str = Field(min_length=2, max_length=120)         # «fine settembre», «primavera 2027»
    persone: int = Field(ge=1, le=500)
    notti: Optional[int] = Field(default=None, ge=1, le=60)
    budget_persona: Optional[float] = Field(default=None, ge=0, le=100000)
    esigenze: Optional[str] = Field(default=None, max_length=2000)
    tipo_ritiro: Optional[str] = Field(default=None, max_length=80)
    # P13 (10/9/2026, piano di business §3.1 A) — la stessa scheda chiede
    # anche la REGIA del ritiro (leggera 290 €, completa 690 € + 40 € a
    # partecipante oltre il sesto). Il tipo distingue la richiesta.
    tipo: Literal["struttura", "regia"] = "struttura"
    formula: Optional[Literal["leggera", "completa", "non_so"]] = None


@router.post("/richieste", status_code=201)
async def crea_richiesta(body: RichiestaCrea, current_user: dict = Depends(require_admin)):
    from database import organizations_collection
    org = await organizations_collection.find_one(
        {"id": current_user["organization_id"]}, {"_id": 0, "name": 1})
    doc = await repo.crea_richiesta(
        current_user["organization_id"], (org or {}).get("name") or "",
        current_user.get("email"), body.model_dump())
    from services.strutture_email import avvisa_piattaforma_richiesta, ricevuta_operatore
    avvisa_piattaforma_richiesta(doc)
    ricevuta_operatore(doc)
    return doc


@router.get("/richieste/mie")
async def mie(current_user: dict = Depends(require_admin)):
    righe = await repo.richieste_di(current_user["organization_id"])
    # all'operatore non si mostrano le note interne
    for r in righe:
        r.pop("nota_interna", None)
    return {"righe": righe}


@router.get("/richieste/{id_}")
async def una(id_: str, current_user: dict = Depends(require_admin)):
    righe = await repo.richieste_di(current_user["organization_id"])
    for r in righe:
        if r["id"] == id_:
            r.pop("nota_interna", None)
            return r
    raise HTTPException(status_code=404, detail="Richiesta non trovata")
