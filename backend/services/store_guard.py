"""Store-first guard condivisa (V4, 5/7/2026).

Un prodotto PUBBLICATO deve avere un posto pubblico dove vivere: uno
store attivo o il public_slug legacy (org migrate pre-multistore).
Usata da TUTTE le porte di pubblicazione (wizard ritiri, POST/PATCH
products) — fonte unica, mai criteri che divergono.
"""

from fastapi import HTTPException, status

STORE_REQUIRED_DETAIL = {
    "code": "store_required",
    "message": "Prima di pubblicare crea il tuo store: è l'indirizzo "
               "pubblico delle tue pagine. Puoi salvare come bozza intanto.",
}


async def org_has_public_home(org_id: str) -> bool:
    from database import organizations_collection, stores_collection
    store = await stores_collection.find_one(
        {"organization_id": org_id, "is_active": True}, {"_id": 1},
    )
    if store:
        return True
    org = await organizations_collection.find_one(
        {"id": org_id}, {"_id": 0, "public_slug": 1},
    )
    return bool((org or {}).get("public_slug"))


async def require_public_home(org_id: str) -> None:
    """TW3 (piano Listino) — profile-first: se manca l'indirizzo
    pubblico si AUTO-CREA lo store tecnico invisibile (nome org,
    is_default) invece di fermare l'operatore col 409. Il contratto
    resta identico per il resto del sistema: dopo questa chiamata
    l'org HA un indirizzo pubblico. Il 409 store_required sopravvive
    solo come ultima difesa se la creazione fallisce."""
    if await org_has_public_home(org_id):
        return
    try:
        from routers.stores import _ensure_default_store
        store = await _ensure_default_store(org_id, None)
        if store:
            return
    except Exception:                     # noqa: BLE001 — cade sul 409
        pass
    raise HTTPException(status_code=status.HTTP_409_CONFLICT,
                        detail=STORE_REQUIRED_DETAIL)
