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
    """Solleva 409 store_required se l'org non ha un indirizzo pubblico."""
    if not await org_has_public_home(org_id):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT,
                            detail=STORE_REQUIRED_DETAIL)
