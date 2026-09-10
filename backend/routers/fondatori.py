"""RB2 (10/9/2026) — il contatore VERO dei fondatori.

Il patto: i primi venti operatori olistici che pubblicano il profilo
entro il 31 ottobre 2026 entrano come fondatori. Un'urgenza e' onesta
solo se il numero e' vero: questo endpoint pubblico lo dice.

«Profilo pubblicato» = il profilo sta nella directory /operatori (oggi:
network_member acceso dal pannello quando il profilo e' completo — la
stessa regola della directory, SR1). Chi e' gia' dentro conta: sono i
primi. Chiuso il tetto, la landing toglie la parola.
"""
from datetime import date

from fastapi import APIRouter

from database import organizations_collection

router = APIRouter(prefix="/public/fondatori", tags=["fondatori"])

TETTO = 20
SCADENZA = date(2026, 10, 31)


@router.get("")
async def stato_fondatori():
    return await conteggio()


async def ids_fondatori() -> set:
    """RB9 — chi e' fondatore: nella rete (network_member) entro la
    scadenza, nei primi TETTO per data di ingresso. Chi e' entrato prima
    che la data venisse scritta (network_member_since assente) conta per
    primo. La fonte del badge «Fondatore» sul profilo pubblico."""
    righe = await organizations_collection.find(
        {"network_member": True, "is_sample": {"$ne": True}, "is_active": {"$ne": False}},
        {"_id": 0, "id": 1, "network_member_since": 1},
    ).to_list(500)
    righe = [r for r in righe if (r.get("network_member_since") or "")[:10] <= SCADENZA.isoformat()]
    righe.sort(key=lambda r: r.get("network_member_since") or "")
    return {r["id"] for r in righe[:TETTO]}


async def conteggio() -> dict:
    """Il conteggio vero, riusabile (RB8: la sequenza email lo cita)."""
    n = await organizations_collection.count_documents({
        "network_member": True,
        "is_sample": {"$ne": True},
        "is_active": {"$ne": False},
    })
    aperto = date.today() <= SCADENZA and n < TETTO
    return {
        "tetto": TETTO,
        "presi": min(n, TETTO),
        "rimasti": max(0, TETTO - n),
        "scadenza": SCADENZA.isoformat(),
        "aperto": aperto,
    }
