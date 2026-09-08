"""Le strutture ricettive dal pannello di sistema (ciclo SR, fase 0).

La porta del system admin sul modello `Struttura`: schema delle liste
chiuse, lista con filtri e conteggi per facet, creazione, salvataggio
per sezione, foto, storia dei contatti, eliminazione. La seconda porta
(l'area della struttura, fase 1) nascera' in routers/struttura.py sullo
stesso repository con `require_struttura`.

Isolamento: solo `require_system_admin`; nessun import dai
professionisti oltre al lettore di immagini (che e' infrastruttura).
"""
import uuid
from typing import List, Optional

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from pydantic import BaseModel, Field

from auth import require_system_admin
from models.struttura import (MODELLI_SEZIONE, SEZIONI, StrutturaCrea, StrutturaPatch,
                              VoceStoria, errori_liste, schema_per_frontend, VISIBILITA)
from repositories import struttura_repository as repo

router = APIRouter(prefix="/admin/strutture", tags=["Strutture (system admin)"])

_FOTO_MAX = 20


@router.get("/schema")
async def schema(_: dict = Depends(require_system_admin)):
    """Le liste chiuse con le etichette: UNA fonte per form e filtri."""
    return schema_per_frontend()


@router.get("")
async def lista(
    q: Optional[str] = Query(default=None, max_length=80),
    regione: Optional[List[str]] = Query(default=None),
    tipo: Optional[List[str]] = Query(default=None),
    stato_pipeline: Optional[List[str]] = Query(default=None),
    visibilita: Optional[str] = Query(default=None),
    posti_letto_min: Optional[int] = Query(default=None, ge=1),
    sala: bool = Query(default=False),
    sala_mq_min: Optional[float] = Query(default=None, ge=1),
    piscina: bool = Query(default=False),
    aria: bool = Query(default=False),
    spazi_esterni: bool = Query(default=False),
    cucina: Optional[List[str]] = Query(default=None),
    regimi: Optional[List[str]] = Query(default=None),
    adatta_a: Optional[List[str]] = Query(default=None),
    contesto: Optional[List[str]] = Query(default=None),
    prezzo_max: Optional[float] = Query(default=None, ge=0),
    uso_esclusivo: bool = Query(default=False),
    ordine: str = Query(default="aggiornato", pattern="^(aggiornato|nome|prezzo|posti)$"),
    pagina: int = Query(default=1, ge=1, le=500),
    _: dict = Depends(require_system_admin),
):
    filtri = {k: v for k, v in dict(
        q=q, regione=regione, tipo=tipo, stato_pipeline=stato_pipeline, visibilita=visibilita,
        posti_letto_min=posti_letto_min, sala=sala, sala_mq_min=sala_mq_min, piscina=piscina,
        aria=aria, spazi_esterni=spazi_esterni, cucina=cucina, regimi=regimi, adatta_a=adatta_a,
        contesto=contesto, prezzo_max=prezzo_max, uso_esclusivo=uso_esclusivo).items()
        if v not in (None, False, [], "")}
    return await repo.cerca(filtri, pagina=pagina, ordine=ordine)


@router.post("", status_code=201)
async def crea(body: StrutturaCrea, current_user: dict = Depends(require_system_admin)):
    errori = errori_liste("luogo", {"regione": body.regione})
    if body.tipo:
        errori += errori_liste("identita", {"tipo": body.tipo})
    if errori:
        raise HTTPException(status_code=400, detail=errori)
    return await repo.crea(body.nome.strip(), body.regione, body.tipo,
                           da_chi=current_user.get("email") or "system_admin")


@router.get("/{id_}")
async def scheda(id_: str, _: dict = Depends(require_system_admin)):
    doc = await repo.trova(id_)
    if not doc:
        raise HTTPException(status_code=404, detail="Struttura non trovata")
    return doc


@router.patch("/{id_}")
async def aggiorna(id_: str, body: StrutturaPatch,
                   current_user: dict = Depends(require_system_admin)):
    """Salva una o piu' sezioni (merge per sezione) e i campi di primo
    livello (visibilita, foto, copertina). Le liste chiuse si validano
    qui: un valore fuori lista e' un 400 con il campo nominato."""
    sezioni, errori = {}, []
    for nome in SEZIONI:
        parte = getattr(body, nome)
        if parte is None:
            continue
        dati = parte.model_dump()
        errori += errori_liste(nome, dati)
        sezioni[nome] = dati
    altri = {}
    if body.visibilita is not None:
        if body.visibilita not in [v for v, _ in VISIBILITA]:
            errori.append("visibilita non ammessa")
        altri["visibilita"] = body.visibilita
    if body.foto is not None:
        altri["foto"] = [f.model_dump() for f in body.foto][:_FOTO_MAX]
    if body.foto_copertina is not None:
        altri["foto_copertina"] = body.foto_copertina or None
    if errori:
        raise HTTPException(status_code=400, detail=errori)
    if not sezioni and not altri:
        raise HTTPException(status_code=400, detail="Niente da salvare")
    doc = await repo.aggiorna_sezioni(id_, sezioni, altri, da_chi=current_user.get("email") or "system_admin")
    if not doc:
        raise HTTPException(status_code=404, detail="Struttura non trovata")
    if altri.get("visibilita") == "pubblica" and not doc.get("pubblicata_il"):
        from models.struttura import adesso
        await repo._coll().update_one({"id": id_}, {"$set": {"pubblicata_il": adesso()}})
        doc["pubblicata_il"] = adesso()
    return doc


@router.post("/{id_}/storia")
async def storia(id_: str, body: VoceStoria, current_user: dict = Depends(require_system_admin)):
    ok = await repo.aggiungi_storia(id_, body.model_dump(), da_chi=current_user.get("email") or "system_admin")
    if not ok:
        raise HTTPException(status_code=404, detail="Struttura non trovata")
    return await repo.trova(id_)


@router.post("/{id_}/foto")
async def foto(id_: str, file: UploadFile = File(...),
               current_user: dict = Depends(require_system_admin)):
    """Una foto per chiamata (stesso motore delle foto del profilo:
    compressione, formati ammessi, cartella propria uploads/strutture)."""
    from routers.organizations import _read_profile_image
    from services.object_storage import content_type_for_ext, save_public_upload
    doc = await repo.trova(id_)
    if not doc:
        raise HTTPException(status_code=404, detail="Struttura non trovata")
    if len(doc.get("foto") or []) >= _FOTO_MAX:
        raise HTTPException(status_code=400, detail=f"Massimo {_FOTO_MAX} foto")
    ext, contents = await _read_profile_image(file)
    url = save_public_upload("strutture", f"{id_}-{uuid.uuid4().hex[:10]}{ext}", contents,
                             content_type=content_type_for_ext(ext))
    foto_ = await repo.aggiungi_foto(id_, url, da_chi=current_user.get("email") or "system_admin")
    return {"foto": foto_}


@router.delete("/{id_}")
async def elimina(id_: str, _: dict = Depends(require_system_admin)):
    esito = await repo.elimina(id_)
    if esito == "assente":
        raise HTTPException(status_code=404, detail="Struttura non trovata")
    return {"esito": esito}


# ── le richieste degli operatori, viste da voi ──────────────────────────────

class RichiestaPatch(BaseModel):
    stato: Optional[str] = Field(default=None, pattern="^(nuova|in_lavorazione|proposta|chiusa)$")
    strutture_proposte: Optional[List[str]] = None
    nota_interna: Optional[str] = Field(default=None, max_length=2000)


@router.get("/richieste/tutte")
async def richieste(stato: Optional[str] = Query(default=None), _: dict = Depends(require_system_admin)):
    return {"righe": await repo.lista_richieste(stato)}


@router.patch("/richieste/{id_}")
async def richiesta_aggiorna(id_: str, body: RichiestaPatch,
                             current_user: dict = Depends(require_system_admin)):
    patch = {k: v for k, v in body.model_dump().items() if v is not None}
    if not patch:
        raise HTTPException(status_code=400, detail="Niente da salvare")
    doc = await repo.aggiorna_richiesta(id_, patch)
    if not doc:
        raise HTTPException(status_code=404, detail="Richiesta non trovata")
    if "stato" in patch and doc.get("email"):
        from services.strutture_email import avvisa_operatore_stato
        avvisa_operatore_stato(doc)
    return doc
