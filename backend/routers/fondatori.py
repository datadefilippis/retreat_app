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

TETTO = 20                         # il badge «Fondatore»: ai primi venti
# AB-R1 (14/9/2026, founder con Valentina): il patto e' «i vantaggi di
# entrare subito» — chi pubblica il profilo entro il 31 dicembre 2026 ha
# gratis l'intervista, i suoi eventi sui social di Aurya e nella Lettera
# del Cerchio (i vantaggi del Pro, senza Sound). Dal 1/1/2027 questi
# servizi sono nel Pro; l'app resta gratuita. Via il «30 giugno 2027» e
# il «prezzo bloccato». Il TETTO resta solo per il badge.
SCADENZA = date(2026, 12, 31)
PIANI_PRO = ("retreat_pro", "retreat_partner")   # chi ha i servizi dal piano


@router.get("")
async def stato_fondatori():
    return await conteggio()


async def ids_fondatori() -> set:
    """RB9 — chi e' fondatore: nella rete (network_member) entro la
    scadenza, nei primi TETTO per data di ingresso. Chi e' entrato prima
    che la data venisse scritta (network_member_since assente) conta per
    primo. La fonte del badge «Fondatore» sul profilo pubblico."""
    righe = await organizations_collection.find(
        {"$or": [{"network_member": True}, {"fondatore_forzato": True}],
         "is_sample": {"$ne": True}, "is_active": {"$ne": False}},
        {"_id": 0, "id": 1, "network_member_since": 1, "fondatore_forzato": 1},
    ).to_list(500)
    # BD (10/9/2026): dal pannello si forza (sempre dentro) o si esclude
    # (mai dentro); gli altri riempiono i posti restanti per data.
    forzati = {r["id"] for r in righe if r.get("fondatore_forzato") is True}
    naturali = [r for r in righe
                if r.get("fondatore_forzato") is None
                and (r.get("network_member_since") or "")[:10] <= SCADENZA.isoformat()]
    naturali.sort(key=lambda r: r.get("network_member_since") or "")
    posti = max(0, TETTO - len(forzati))
    return forzati | {r["id"] for r in naturali[:posti]}


async def entrato_2026(org: dict) -> bool:
    """AB-R1 — il diritto ai vantaggi 2026, CALCOLATO e non assegnato:
    profilo nella rete (network_member) entro la SCADENZA, oppure
    fondatore forzato dal pannello; l'escluso dal pannello no."""
    if not org or org.get("is_sample") or org.get("is_active") is False:
        return False
    if org.get("fondatore_forzato") is True:
        return True
    if org.get("fondatore_forzato") is False:
        return False
    if not org.get("network_member"):
        return False
    return (org.get("network_member_since") or "")[:10] <= SCADENZA.isoformat()


async def vantaggi_pro(org: dict) -> dict:
    """Chi ha diritto ai servizi del Pro (Lettera, social, intervista +
    reel) e da dove: dal piano (Pro/Partner attivo) o dal patto 2026.
    Studio segue SOLO il piano (founder 14/9: «no sound» nel patto)."""
    piano = (org or {}).get("commercial_plan_slug") or "retreat_free"
    stato = (org or {}).get("billing_status") or "none"
    dal_piano = piano in PIANI_PRO and stato in ("active", "trialing", "manual")
    dal_patto = await entrato_2026(org)
    from services.studio_access import studio_attivo   # UNA definizione di «Studio attivo»
    return {"servizi": dal_piano or dal_patto,
            "fonte": "piano" if dal_piano else ("patto_2026" if dal_patto else None),
            "studio": studio_attivo(org), "piano": piano}


async def conteggio() -> dict:
    """Il conteggio vero, riusabile (RB8: la sequenza email lo cita).
    AB-R1: il patto vale per tutti fino alla SCADENZA (niente tetto);
    tetto/presi/rimasti restano per il badge dei primi venti."""
    n = await organizations_collection.count_documents({
        "network_member": True,
        "is_sample": {"$ne": True},
        "is_active": {"$ne": False},
    })
    oggi = date.today()
    return {
        "tetto": TETTO,
        "presi": min(n, TETTO),
        "rimasti": max(0, TETTO - n),
        "scadenza": SCADENZA.isoformat(),
        "giorni_rimasti": max(0, (SCADENZA - oggi).days),
        "aperto": oggi <= SCADENZA,
        "badge_aperto": oggi <= SCADENZA and n < TETTO,
    }
