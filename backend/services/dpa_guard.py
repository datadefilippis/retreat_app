"""PV7 — Il patto di responsabilità (DPA art. 28) come prerequisito di
vendita (docs/PROFILO_VERIFICATO_PIANO_2026-07.md, onda PV7).

Prima di vendere su Aurya l'operatore DEVE aver letto e accettato il suo
accordo di responsabilità (DPA art. 28 GDPR: lui titolare autonomo dei
dati dei suoi clienti, Aurya responsabile del trattamento). La macchina
dell'acknowledgement esiste da CG-7 (GET/POST /api/legal/dpa*): questo
modulo aggiunge SOLO il gate riusabile, senza duplicare testi o endpoint.

Punto di gate scelto: la CREAZIONE dei prodotti vendibili (item_type
``service`` ed ``event_ticket``), NON la pubblicazione. Motivi:
  1. nel mondo snello la creazione E' la pubblicazione: il listino crea
     con is_published=true in un passo (LM1), il wizard ritiri crea e
     pubblica insieme (RS2). Gate alla creazione = gate alla vendita.
  2. le porte di PUBBLICAZIONE sono molte (PUT /products, PATCH status
     occurrence, toggle massivo del listino): gate-arle tutte avrebbe
     bloccato anche i contenuti GIA' esistenti delle org attive — vietato
     (le org esistenti non devono ritrovarsi bloccate su cio' che hanno
     gia' pubblicato). La creazione e' un choke-point unico per
     superficie e la UI non ha altre porte di creazione.
  3. un org esistente con prodotti che ne crea uno NUOVO vede il gate:
     corretto e voluto — la firma copre le nuove vendite da qui in poi.

Fonte di verita' dell'acknowledgement — DUE livelli:
  1. stamp durevole ``merchant_dpa_ack`` sul documento organization,
     scritto da POST /legal/dpa/acknowledge (PV7). NON soggetto a TTL:
     e' lo stato del gate, per sempre.
  2. record immutabile in consent_audit (source
     merchant_dpa_acknowledged, document_type merchant_dpa) — la
     macchina CG-7 esistente, INTATTA. Ha pero' TTL 365 giorni
     (retention audit condivisa): da solo farebbe "scadere" la firma e
     ri-gaterebbe l'org dopo un anno. Per questo il gate legge PRIMA lo
     stamp org; l'audit resta la prova storica/probatoria.
Fallback: org che avesse acked pre-PV7 (solo audit, nessuno stamp) e'
riconosciuta comunque dal livello 2.

Risposta del gate: 409 con detail {"code": "DPA_REQUIRED", ...}. Il
frontend la intercetta e apre il dialog del patto (l'utente normale non
vede mai l'errore: la UI controlla lo status PRIMA di chiamare).
"""

import logging
from typing import Optional

from fastapi import HTTPException, status

logger = logging.getLogger(__name__)

# I tipi di prodotto "vendibili" del mondo snello: righe di listino
# (service) e ritiri (event_ticket). I tipi del commerce legacy restano
# fuori scope PV7 (congelati dietro flag per-org, vedi TW3).
SELLABLE_ITEM_TYPES = ("service", "event_ticket")

DPA_REQUIRED_DETAIL = {
    "code": "DPA_REQUIRED",
    "message": (
        "Prima di vendere leggi e accetta la tua informativa di "
        "responsabilita' (accordo sul trattamento dei dati, art. 28 "
        "GDPR). La trovi anche in Impostazioni → Condizioni "
        "dell'operatore."
    ),
}


async def get_dpa_ack(org_id: str) -> Optional[dict]:
    """Return the org's DPA acknowledgement (normalized dict) or None.

    Livello 1: stamp durevole sul doc org (PV7). Livello 2: record
    consent_audit (CG-7, TTL 365g). La forma restituita e' quella del
    record audit (chiavi accepted_at / user_id / locale / version_tag)
    cosi' /dpa/status e /dpa/acknowledge non cambiano contratto.
    """
    from database import organizations_collection

    org = await organizations_collection.find_one(
        {"id": org_id}, {"_id": 0, "merchant_dpa_ack": 1},
    )
    stamp = (org or {}).get("merchant_dpa_ack")
    if isinstance(stamp, dict) and stamp.get("acknowledged_at"):
        return {
            "accepted_at": stamp.get("acknowledged_at"),
            "user_id": stamp.get("user_id"),
            "locale": stamp.get("locale"),
            "version_tag": stamp.get("version_tag"),
        }

    from repositories import consent_audit_repository as car
    return await car.find_latest_for_org_dpa(org_id)


async def org_has_dpa_ack(org_id: str) -> bool:
    return bool(await get_dpa_ack(org_id))


async def require_dpa_acknowledged(org_id: str) -> None:
    """Gate PV7: 409 DPA_REQUIRED se l'org non ha mai accettato il DPA.

    Applicato dalle porte di CREAZIONE dei prodotti vendibili:
      - POST /api/products (item_type service | event_ticket)
      - POST /api/products/{id}/duplicate (stessi item_type)
      - POST /api/event-occurrences/wizard (crea il product event_ticket)
    """
    if await org_has_dpa_ack(org_id):
        return
    logger.info("dpa_guard: creation blocked, DPA not acknowledged org=%s",
                org_id)
    raise HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail=DPA_REQUIRED_DETAIL,
    )
