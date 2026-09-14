"""La richiesta dell'operatore: «Cerco una struttura per un ritiro» (SR, fase 0).

L'unica cosa che il gestionale del professionista sa delle strutture:
un modulo breve che crea una richiesta. La lista delle strutture non
si vede da qui (e' riservata a voi in fase 0). Tutto il resto vive nel
pannello di sistema.
"""
from typing import Literal, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, model_validator

from auth import require_admin
from repositories import struttura_repository as repo

router = APIRouter(prefix="/strutture", tags=["Strutture (operatori)"])


class RichiestaCrea(BaseModel):
    # AB-R2 (14/9/2026): per i servizi del Pro (lettera_eventi, social,
    # intervista_reel) zona/periodo/persone non hanno senso: sono
    # facoltativi, e obbligatori solo per struttura e regia (validator).
    zona: Optional[str] = Field(default=None, max_length=120)     # regione o zona («Puglia», «Alpi»)
    periodo: Optional[str] = Field(default=None, max_length=120)  # «fine settembre», «primavera 2027»
    persone: Optional[int] = Field(default=None, ge=1, le=500)
    messaggio: Optional[str] = Field(default=None, max_length=2000)   # cosa vuoi che raccontiamo / quale evento
    notti: Optional[int] = Field(default=None, ge=1, le=60)
    budget_persona: Optional[float] = Field(default=None, ge=0, le=100000)
    esigenze: Optional[str] = Field(default=None, max_length=2000)
    tipo_ritiro: Optional[str] = Field(default=None, max_length=80)
    # P13 (10/9/2026, piano di business §3.1 A) — la stessa scheda chiede
    # anche la REGIA del ritiro (leggera 290 €, completa 690 € + 40 € a
    # partecipante oltre il sesto). Il tipo distingue la richiesta.
    tipo: Literal["struttura", "regia", "lettera_eventi", "social", "intervista_reel"] = "struttura"
    formula: Optional[Literal["leggera", "completa", "non_so"]] = None

    @model_validator(mode="after")
    def _campi_per_tipo(self):
        if self.tipo in ("struttura", "regia"):
            if not (self.zona and len(self.zona.strip()) >= 2):
                raise ValueError("zona obbligatoria")
            if not (self.periodo and len(self.periodo.strip()) >= 2):
                raise ValueError("periodo obbligatorio")
            if not self.persone:
                raise ValueError("persone obbligatorio")
        return self


# AB-R2 (14/9/2026): i servizi del Pro (e del patto 2026) sono richieste
# come la regia: stessa collezione, stesso pannello, stessa email a noi.
# Il diritto lo dice routers.fondatori.vantaggi_pro; senza, 403 e il
# messaggio che porta a Piani e costi.
TIPI_PRO = ("lettera_eventi", "social", "intervista_reel")


@router.post("/richieste", status_code=201)
async def crea_richiesta(body: RichiestaCrea, current_user: dict = Depends(require_admin)):
    from database import organizations_collection
    org = await organizations_collection.find_one(
        {"id": current_user["organization_id"]},
        {"_id": 0, "name": 1, "commercial_plan_slug": 1, "billing_status": 1,
         "network_member": 1, "network_member_since": 1, "fondatore_forzato": 1,
         "is_sample": 1, "is_active": 1, "sound_composer": 1, "sound_studio_override": 1})
    campi = body.model_dump()
    if body.tipo in TIPI_PRO:
        from routers.fondatori import vantaggi_pro
        diritto = await vantaggi_pro(org or {})
        if not diritto["servizi"]:
            raise HTTPException(status_code=403, detail="È incluso nel Pro: attivalo da Piani e costi.")
        campi["fonte"] = diritto["fonte"]          # «piano» o «patto_2026», lo dice l'email a noi
    doc = await repo.crea_richiesta(
        current_user["organization_id"], (org or {}).get("name") or "",
        current_user.get("email"), campi)
    from services.strutture_email import avvisa_piattaforma_richiesta, ricevuta_operatore
    avvisa_piattaforma_richiesta(doc)
    ricevuta_operatore(doc)
    return doc


@router.get("/vantaggi-pro")
async def vantaggi_pro_correnti(current_user: dict = Depends(require_admin)):
    """AB-R4 (14/9/2026): cosa ha diritto a chiedere l'organizzazione —
    i servizi del Pro (Lettera, social, intervista + reel) dal piano o dal
    patto 2026, Studio dal piano — e le richieste gia' fatte. La regola
    vive in routers.fondatori.vantaggi_pro (una sola). Sta qui e non in
    organizations.py: il mondo delle richieste resta isolato (SR)."""
    from database import organizations_collection
    from routers.fondatori import vantaggi_pro, conteggio
    org = await organizations_collection.find_one(
        {"id": current_user["organization_id"]},
        {"_id": 0, "commercial_plan_slug": 1, "billing_status": 1, "network_member": 1,
         "network_member_since": 1, "fondatore_forzato": 1, "is_sample": 1, "is_active": 1,
         "sound_composer": 1, "sound_studio_override": 1}) or {}
    diritto = await vantaggi_pro(org)
    righe = await repo.richieste_di(current_user["organization_id"])
    richieste = [{"id": r["id"], "tipo": r.get("tipo"), "stato": r.get("stato"), "created_at": r.get("created_at")}
                 for r in righe if r.get("tipo") in TIPI_PRO]
    return {**diritto, "richieste": richieste, "patto": await conteggio()}


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
