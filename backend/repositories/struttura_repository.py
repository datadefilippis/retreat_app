"""Il repository delle strutture (ciclo SR, fase 0).

Qui vive la logica di persistenza e di ricerca, perche' in fase 1 la
stessa collezione avra' DUE porte (pannello di sistema e area della
struttura): i router restano porte, la sostanza sta qui.
"""
from typing import Any, Dict, List, Optional

from models.common import generate_id
from models.struttura import adesso, calcola_derivati, slugify

PAGINA = 20
_ORDINI = {
    "aggiornato": [("aggiornato_il", -1)],
    "nome": [("identita.nome", 1)],
    "prezzo": [("derivati.prezzo_da", 1)],
    "posti": [("derivati.posti_letto_totali", -1)],
}
_RIGA = {"_id": 0, "id": 1, "slug": 1, "visibilita": 1, "origine": 1, "foto_copertina": 1,
         "identita.nome": 1, "identita.tipo": 1, "luogo.comune": 1, "luogo.regione": 1,
         "derivati": 1, "aggiornato_il": 1, "redazione.stato_pipeline": 1,
         "redazione.giudizio": 1}


def _coll():
    from database import strutture_collection
    return strutture_collection


async def slug_libero(nome: str, escludi_id: Optional[str] = None) -> str:
    base = slugify(nome)
    slug, n = base, 2
    while await _coll().find_one({"slug": slug, "id": {"$ne": escludi_id}}, {"_id": 1}):
        slug = f"{base}-{n}"
        n += 1
    return slug


async def crea(nome: str, regione: str, tipo: Optional[str], da_chi: str) -> Dict[str, Any]:
    ora = adesso()
    doc = {
        "id": generate_id(),
        "slug": await slug_libero(nome),
        "organization_id": None,           # fase 1: la struttura che adotta la scheda
        "origine": "redazione",
        "visibilita": "riservata",
        "identita": {"nome": nome, "tipo": tipo},
        "luogo": {"regione": regione},
        "redazione": {"stato_pipeline": "da_contattare"},
        "storia": [],
        "foto": [],
        "foto_copertina": None,
        "creato_da": da_chi, "creato_il": ora,
        "aggiornato_da": da_chi, "aggiornato_il": ora,
    }
    doc["derivati"] = calcola_derivati(doc)
    await _coll().insert_one({**doc})
    doc.pop("_id", None)
    return doc


async def trova(id_o_slug: str) -> Optional[Dict[str, Any]]:
    return await _coll().find_one({"$or": [{"id": id_o_slug}, {"slug": id_o_slug}]}, {"_id": 0})


async def aggiorna_sezioni(id_: str, sezioni: Dict[str, Any], altri: Dict[str, Any],
                           da_chi: str) -> Optional[Dict[str, Any]]:
    """Merge per sezione: la sezione inviata sostituisce la sua, le altre
    restano. `altri` = campi di primo livello (visibilita, foto...)."""
    attuale = await _coll().find_one({"id": id_}, {"_id": 0})
    if not attuale:
        return None
    nuovo = {**attuale, **{k: v for k, v in sezioni.items()}, **altri}
    if "identita" in sezioni and sezioni["identita"].get("nome") \
            and sezioni["identita"]["nome"] != (attuale.get("identita") or {}).get("nome") \
            and nuovo.get("visibilita") != "pubblica":
        # lo slug segue il nome finche' la scheda non e' pubblica
        nuovo["slug"] = await slug_libero(sezioni["identita"]["nome"], escludi_id=id_)
    nuovo["derivati"] = calcola_derivati(nuovo)
    nuovo["aggiornato_da"] = da_chi
    nuovo["aggiornato_il"] = adesso()
    await _coll().replace_one({"id": id_}, nuovo)
    return nuovo


async def aggiungi_storia(id_: str, voce: Dict[str, Any], da_chi: str) -> bool:
    voce = {**voce, "quando": voce.get("quando") or adesso()[:10], "chi": voce.get("chi") or da_chi}
    res = await _coll().update_one(
        {"id": id_}, {"$push": {"storia": {"$each": [voce], "$position": 0}},
                      "$set": {"aggiornato_il": adesso(), "aggiornato_da": da_chi}})
    return res.matched_count > 0


async def aggiungi_foto(id_: str, url: str, da_chi: str) -> Optional[List[Dict]]:
    doc = await _coll().find_one({"id": id_}, {"_id": 0, "foto": 1, "foto_copertina": 1})
    if doc is None:
        return None
    foto = (doc.get("foto") or []) + [{"url": url, "alt": None}]
    upd = {"foto": foto, "aggiornato_il": adesso(), "aggiornato_da": da_chi}
    if not doc.get("foto_copertina"):
        upd["foto_copertina"] = url
    await _coll().update_one({"id": id_}, {"$set": upd})
    return foto


async def elimina(id_: str) -> str:
    """Mai pubblicata → via; pubblicata → sospesa e riservata (audit)."""
    doc = await _coll().find_one({"id": id_}, {"_id": 0, "visibilita": 1, "pubblicata_il": 1})
    if not doc:
        return "assente"
    if doc.get("pubblicata_il"):
        await _coll().update_one({"id": id_}, {"$set": {
            "visibilita": "riservata", "redazione.stato_pipeline": "sospesa",
            "derivati.stato_pipeline": "sospesa", "aggiornato_il": adesso()}})
        return "sospesa"
    await _coll().delete_one({"id": id_})
    return "eliminata"


def _filtro(f: Dict[str, Any]) -> Dict[str, Any]:
    q: Dict[str, Any] = {}
    if f.get("q"):
        q["$text"] = {"$search": f["q"]}
    if f.get("regione"):
        q["derivati.regione"] = {"$in": f["regione"]}
    if f.get("tipo"):
        q["derivati.tipo"] = {"$in": f["tipo"]}
    if f.get("stato_pipeline"):
        q["derivati.stato_pipeline"] = {"$in": f["stato_pipeline"]}
    if f.get("visibilita"):
        q["visibilita"] = f["visibilita"]
    if f.get("posti_letto_min"):
        q["derivati.posti_letto_totali"] = {"$gte": int(f["posti_letto_min"])}
    if f.get("sala"):
        q["derivati.ha_sala"] = True
    if f.get("sala_mq_min"):
        q["derivati.sala_mq_max"] = {"$gte": float(f["sala_mq_min"])}
    if f.get("piscina"):
        q["derivati.ha_piscina"] = True
    if f.get("aria"):
        q["derivati.ha_aria"] = True
    if f.get("spazi_esterni"):
        q["derivati.ha_spazi_esterni"] = True
    if f.get("cucina"):
        q["cucina.cucina"] = {"$in": f["cucina"]}
    if f.get("regimi"):
        q["cucina.regimi"] = {"$all": f["regimi"]}
    if f.get("adatta_a"):
        q["derivati.adatta_a"] = {"$all": f["adatta_a"]}
    if f.get("contesto"):
        q["luogo.contesto"] = {"$in": f["contesto"]}
    if f.get("prezzo_max") is not None:
        q["derivati.prezzo_da"] = {"$lte": float(f["prezzo_max"])}
    if f.get("uso_esclusivo"):
        q["ricettivita.uso_esclusivo_possibile"] = True
    return q


async def cerca(filtri: Dict[str, Any], pagina: int = 1, ordine: str = "aggiornato") -> Dict[str, Any]:
    q = _filtro(filtri)
    pagina = max(1, pagina)
    sort = _ORDINI.get(ordine, _ORDINI["aggiornato"])
    cursor = _coll().find(q, _RIGA).sort(sort).skip((pagina - 1) * PAGINA).limit(PAGINA)
    righe = await cursor.to_list(PAGINA)
    totale = await _coll().count_documents(q)
    # i conteggi per facet, sulla ricerca SENZA il filtro della facet stessa
    facet = {}
    for chiave, campo in (("regione", "$derivati.regione"), ("tipo", "$derivati.tipo"),
                          ("stato_pipeline", "$derivati.stato_pipeline")):
        q_senza = _filtro({k: v for k, v in filtri.items() if k != chiave})
        pipeline = [{"$match": q_senza}, {"$group": {"_id": campo, "n": {"$sum": 1}}},
                    {"$sort": {"n": -1}}]
        facet[chiave] = [{"valore": d["_id"], "n": d["n"]}
                         async for d in _coll().aggregate(pipeline) if d["_id"]]
    return {"righe": righe, "totale": totale, "pagina": pagina, "per_pagina": PAGINA, "facet": facet}


# ── le richieste degli operatori ────────────────────────────────────────────

def _richieste():
    from database import richieste_struttura_collection
    return richieste_struttura_collection


async def crea_richiesta(org_id: str, org_nome: str, email: Optional[str], dati: Dict[str, Any]) -> Dict[str, Any]:
    ora = adesso()
    doc = {"id": generate_id(), "organization_id": org_id, "organization_nome": org_nome,
           "email": email, **dati, "stato": "nuova", "strutture_proposte": [],
           "creato_il": ora, "aggiornato_il": ora}
    await _richieste().insert_one({**doc})
    doc.pop("_id", None)
    return doc


async def lista_richieste(stato: Optional[str] = None) -> List[Dict[str, Any]]:
    q = {"stato": stato} if stato else {}
    return await _richieste().find(q, {"_id": 0}).sort("creato_il", -1).to_list(200)


async def richieste_di(org_id: str) -> List[Dict[str, Any]]:
    return await _richieste().find({"organization_id": org_id}, {"_id": 0}).sort("creato_il", -1).to_list(50)


async def aggiorna_richiesta(id_: str, patch: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    res = await _richieste().find_one_and_update(
        {"id": id_}, {"$set": {**patch, "aggiornato_il": adesso()}}, projection={"_id": 0},
        return_document=True)
    return res
