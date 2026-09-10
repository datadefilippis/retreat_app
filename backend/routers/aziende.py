"""«Aurya per le aziende» — la richiesta di un team building (P13, 10/9/2026).

Piano di business §3.1 B: il team building alla Masseria e' la riga a
margine piu' alto e piu' veloce, e da' lavoro pagato ai professionisti
della rete. La pagina /aziende e' una landing con un modulo: la
richiesta finisce nelle stesse «richieste» delle strutture (tipo
team_building), Davide e Valentina rispondono con il preventivo, la
prenotazione e' un ordine manuale, la fattura la fa Aurya.

Pubblico, senza account: solo il limite di frequenza (niente esca
anti-bot: l'autofill la riempiva, incidente del 28/8).
"""
from typing import Literal, Optional

from fastapi import APIRouter, Request
from pydantic import BaseModel, EmailStr, Field

from repositories import struttura_repository as repo
from routers.auth import limiter

router = APIRouter(prefix="/public/aziende", tags=["Aziende (pubblico)"])


class RichiestaAzienda(BaseModel):
    azienda: str = Field(min_length=2, max_length=120)
    nome: str = Field(min_length=2, max_length=80)
    email: EmailStr
    telefono: Optional[str] = Field(default=None, max_length=40)
    persone: int = Field(ge=1, le=500)
    periodo: str = Field(min_length=2, max_length=120)
    formato: Literal["giornata", "due_giorni", "su_misura", "non_so"] = "non_so"
    messaggio: Optional[str] = Field(default=None, max_length=2000)


@router.post("/richiesta", status_code=201)
@limiter.limit("5/hour")
async def richiesta_azienda(body: RichiestaAzienda, request: Request):
    dati = body.model_dump()
    dati["email"] = str(body.email)
    dati["tipo"] = "team_building"
    dati["zona"] = "Masseria"
    doc = await repo.crea_richiesta(None, body.azienda.strip(), str(body.email), dati)
    from services.strutture_email import avvisa_piattaforma_richiesta, ricevuta_operatore
    avvisa_piattaforma_richiesta(doc)
    ricevuta_operatore(doc)
    return {"ok": True, "id": doc["id"]}
