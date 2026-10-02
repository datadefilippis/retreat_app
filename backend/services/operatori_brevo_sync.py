"""OP2 (2/10/2026 sera) — gli OPERATORI in Brevo, distinti dagli iscritti al
Cerchio ma sullo STESSO contatto (Brevo identifica per email: un operatore
che e' anche nel Cerchio e' un contatto solo, con le due facce).

Base giuridica (OP1, informativa 1-bis e Termini 19.4, v2.10): l'operatore
e' cliente, riceve comunicazioni di servizio e aggiornamenti sulla
Piattaforma per contratto e legittimo interesse, e puo' opporsi: niente
casella di consenso, niente marketing di terzi.

Tre chiavi per non sbagliare pubblico in Brevo:
  AURYA_TIPO             cerchio | operatore | operatore+cerchio
  AURYA_INVIABILE        (del Cerchio) true solo se confermato col consenso
  AURYA_OP_COMUNICAZIONI true finche' l'operatore non si oppone (webhook
                         Brevo «unsubscribed» → users.comunicazioni_opposizione_at)

Quando si allinea: al salvataggio del profilo (dopo_salvataggio), una
volta al giorno per tutti (scheduler «brevo_operatori»), e a mano con
scripts/brevo_segmentazione.py --operatori. Solo API contatti: mai email.
"""
from __future__ import annotations

import asyncio
import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

ATTRIBUTI_BREVO_OP = {
    "AURYA_TIPO": "text",               # cerchio | operatore | operatore+cerchio (lo scrivono ENTRAMBE le sync)
    "AURYA_OP": "boolean",              # e' un operatore (account attivo)
    "AURYA_OP_COMUNICAZIONI": "boolean",  # LA chiave: true finche' non si oppone
    "AURYA_OP_STATO": "text",           # account | bozza | online
    "AURYA_OP_ATTIVITA": "text",        # nome dell'organizzazione
    "AURYA_OP_PAGINA": "text",          # URL della pagina pubblica, se online
    "AURYA_OP_DIRECTORY": "boolean",    # online E non escluso dalla directory
    "AURYA_OP_DISCIPLINE": "text",      # csv slug dichiarati
    "AURYA_OP_REGIONE": "text",
    "AURYA_OP_CITTA": "text",
    "AURYA_OP_PIANO": "text",           # free | pro | founding | partner
    "AURYA_OP_LISTINO": "boolean",      # almeno un prodotto pubblicato
    "AURYA_OP_STRIPE": "boolean",       # incassi online collegati
    "AURYA_OP_SOUND": "boolean",        # compone in Aurya Sound
    "AURYA_OP_REGISTRATO_IL": "date",   # YYYY-MM-DD
    "AURYA_OP_ULTIMO_ACCESSO": "date",  # YYYY-MM-DD (assente se mai entrato)
    "AURYA_OP_VERIFICATO": "boolean",   # email dell'account verificata
}

_PROIEZIONE_ORG = {"_id": 0, "id": 1, "name": 1, "plan": 1, "public_profile": 1, "public_slug": 1,
                   "store_settings": 1, "sound_composer": 1, "is_active": 1, "deactivated_at": 1,
                   "exclude_from_listings": 1, "created_at": 1, "is_sample": 1, "is_demo": 1}
_PROIEZIONE_USER = {"_id": 0, "email": 1, "role": 1, "organization_id": 1, "email_verified": 1,
                    "created_at": 1, "last_login_at": 1, "is_active": 1,
                    "comunicazioni_opposizione_at": 1}


def _titolare(utenti: List[dict]) -> Optional[dict]:
    """Il primo admin vince, un membro qualsiasi fa da riserva (SA2)."""
    admin = [u for u in utenti if u.get("role") == "admin" and u.get("email")]
    return admin[0] if admin else next((u for u in utenti if u.get("email")), None)


async def tipo_contatto(email: str) -> str:
    """cerchio | operatore | operatore+cerchio — per ENTRAMBE le sync."""
    from database import db
    e = (email or "").strip().lower()
    op = await db.users.count_documents({"email": e, "role": {"$ne": "system_admin"}}, limit=1)
    sub = await db.aurya_subscribers.count_documents({"email": e}, limit=1)
    if op and sub:
        return "operatore+cerchio"
    return "operatore" if op else "cerchio"


async def fatti_operatore(org_id: str) -> Optional[Dict[str, Any]]:
    """Tutto cio' che Brevo deve sapere di un operatore, letto dal DB.
    None se l'organizzazione non c'e', e' un campione, o non ha un titolare
    con email."""
    from database import db
    org = await db.organizations.find_one({"id": org_id}, _PROIEZIONE_ORG)
    if not org or org.get("is_sample") or org.get("is_demo"):
        return None
    utenti = [u async for u in db.users.find({"organization_id": org_id}, _PROIEZIONE_USER)]
    tit = _titolare(utenti)
    if not tit:
        return None
    email = tit["email"].strip().lower()
    # pagina online: lo STESSO criterio della regia e della directory
    store = await db.stores.find_one(
        {"organization_id": org_id, "is_published": True, "is_active": True,
         "visibility": "public", "slug": {"$nin": [None, ""]}}, {"_id": 0, "slug": 1})
    slug = (store or {}).get("slug")
    if not slug and org.get("public_slug") and (org.get("store_settings") or {}).get("is_storefront_published"):
        slug = org["public_slug"]
    pp = org.get("public_profile") or {}
    attivo = org.get("is_active", True) is not False and not org.get("deactivated_at") \
        and tit.get("is_active", True) is not False
    listino = await db.products.count_documents({"organization_id": org_id, "is_published": True}, limit=1) > 0
    stripe = await db.payment_connections.count_documents(
        {"organization_id": org_id, "runtime_status": "ready"}, limit=1) > 0
    sub = await db.aurya_subscribers.find_one({"email": email}, {"_id": 0, "status": 1})
    return {
        "email": email, "org_id": org_id, "attivo": attivo,
        "attivita": org.get("name") or "",
        "slug": slug, "bozza": bool((pp.get("bio") or "").strip() or pp.get("disciplines")),
        "directory": bool(slug) and not org.get("exclude_from_listings"),
        "discipline": [d for d in (pp.get("disciplines") or []) if d],
        "regione": pp.get("region") or "", "citta": pp.get("city") or "",
        "piano": str(org.get("plan") or "free").lower(),
        "listino": listino, "stripe": stripe, "sound": bool(org.get("sound_composer")),
        "registrato_il": tit.get("created_at") or org.get("created_at"),
        "ultimo_accesso": tit.get("last_login_at"),
        "verificato": bool(tit.get("email_verified")),
        "opposizione": bool(tit.get("comunicazioni_opposizione_at")),
        "cerchio": (sub or {}).get("status"),
    }


def attributi_operatore(f: Dict[str, Any]) -> Dict[str, Any]:
    from services.subscriber_brevo_sync import _data
    base_url = _url_pubblico()
    out = {
        "AURYA_TIPO": "operatore+cerchio" if f.get("cerchio") else "operatore",
        "AURYA_OP": bool(f.get("attivo")),
        # la chiave: cliente attivo che non si e' opposto
        "AURYA_OP_COMUNICAZIONI": bool(f.get("attivo")) and not f.get("opposizione"),
        "AURYA_OP_STATO": "online" if f.get("slug") else ("bozza" if f.get("bozza") else "account"),
        "AURYA_OP_ATTIVITA": " ".join(str(f.get("attivita") or "").split())[:120],
        "AURYA_OP_PAGINA": f"{base_url}/o/{f['slug']}" if f.get("slug") else "",
        "AURYA_OP_DIRECTORY": bool(f.get("directory")),
        "AURYA_OP_DISCIPLINE": ",".join(f.get("discipline") or []),
        "AURYA_OP_REGIONE": str(f.get("regione") or "")[:60],
        "AURYA_OP_CITTA": str(f.get("citta") or "")[:80],
        "AURYA_OP_PIANO": f.get("piano") or "free",
        "AURYA_OP_LISTINO": bool(f.get("listino")),
        "AURYA_OP_STRIPE": bool(f.get("stripe")),
        "AURYA_OP_SOUND": bool(f.get("sound")),
        "AURYA_OP_REGISTRATO_IL": _data(f.get("registrato_il")),
        "AURYA_OP_ULTIMO_ACCESSO": _data(f.get("ultimo_accesso")),
        "AURYA_OP_VERIFICATO": bool(f.get("verificato")),
    }
    # date vuote omesse (Brevo rifiuterebbe l'intero upsert)
    return {k: v for k, v in out.items() if not (ATTRIBUTI_BREVO_OP.get(k) == "date" and not v)}


def _url_pubblico() -> str:
    import os
    return (os.environ.get("PUBLIC_APP_URL") or os.environ.get("APP_URL") or "https://aurya.life").rstrip("/")


def _in_blacklist(f: Dict[str, Any]) -> bool:
    """Opposto alle comunicazioni, o disiscritto dal Cerchio: Brevo non gli
    manda nulla. L'operatore NON riaccende mai da solo un contatto che il
    Cerchio ha messo in blacklist."""
    return bool(f.get("opposizione")) or f.get("cerchio") == "unsubscribed"


async def sync_operatore(org_id: str) -> bool:
    """Riflette un operatore su Brevo. Mai un raise (best-effort)."""
    try:
        f = await fatti_operatore(org_id)
        if not f:
            return False
        from services.subscriber_brevo_sync import _push_to_brevo
        return await asyncio.to_thread(_push_to_brevo, f["email"], attributi_operatore(f), _in_blacklist(f))
    except Exception as exc:  # noqa: BLE001
        logger.warning("brevo sync operatore %s: %s", org_id, exc)
        return False


def sync_operatore_background(org_id: str) -> None:
    try:
        asyncio.get_running_loop().create_task(sync_operatore(org_id))
    except RuntimeError:
        asyncio.run(sync_operatore(org_id))


async def sync_tutti(pausa: float = 0.15) -> Dict[str, int]:
    """Tutti gli operatori, in ordine di registrazione: per il job
    giornaliero e per lo script. Ritorna i conteggi."""
    from database import db
    esito = {"allineati": 0, "falliti": 0, "saltati": 0, "comunicazioni": 0}
    async for org in db.organizations.find({}, {"_id": 0, "id": 1}).sort("created_at", 1):
        f = await fatti_operatore(org["id"])
        if not f:
            esito["saltati"] += 1
            continue
        from services.subscriber_brevo_sync import _push_to_brevo
        attr = attributi_operatore(f)
        esito["comunicazioni"] += 1 if attr["AURYA_OP_COMUNICAZIONI"] else 0
        ok = await asyncio.to_thread(_push_to_brevo, f["email"], attr, _in_blacklist(f))
        esito["allineati" if ok else "falliti"] += 1
        await asyncio.sleep(pausa)
    return esito
