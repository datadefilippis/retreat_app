"""BN6 — sync iscritti lettera → contatti Brevo (best-effort).

Il nostro DB (aurya_subscribers) resta la FONTE DI VERITA'; Brevo e'
il braccio d'invio: le campagne si scrivono e spediscono dalla
dashboard Brevo segmentando sugli attributi che sincronizziamo qui.
Niente campaign engine in casa (scelta S5 della strategia).

Attributi sincronizzati (da creare una volta in Brevo, tipo testo):
  AURYA_STATUS   pending | confirmed | unsubscribed
  AURYA_TOPICS   csv dei temi scelti (vuoto = tutto)
  AURYA_FORMAT   all | practices
  AURYA_ALERT    off | italy | csv regioni
  AURYA_SOURCE   sorgente di iscrizione (blog_yoga, newsletter, gate_...)
  AURYA_LANG     lingua dichiarata

Unsubscribed → emailBlacklisted=true su Brevo: la piattaforma smette
di spedirgli QUALSIASI campagna anche se un segmento lo includesse per
errore. Best-effort assoluto: un errore di rete non deve mai rompere
il flusso utente (il DB e' gia' aggiornato; il sync si riallinea al
prossimo evento).

Env:
  BREVO_API_KEY   gia' usata dal transazionale (senza: solo log)
  BREVO_LIST_ID   opzionale: id lista Brevo a cui agganciare i contatti
"""

import asyncio
import logging
import os

logger = logging.getLogger(__name__)

_CONTACTS_URL = "https://api.brevo.com/v3/contacts"


# BS (2/10/2026, founder: «segmentiamo gli utenti in Brevo in maniera solida,
# con le vie e tutte le info di valore») — IL REGISTRO degli attributi che la
# sync scrive: nome → tipo Brevo. Lo script scripts/brevo_segmentazione.py
# li crea in Brevo (idempotente) e la guardia pretende che _attributes()
# produca ESATTAMENTE queste chiavi. Scoperta del 2/10: fino a oggi nessun
# attributo AURYA_* esisteva in Brevo e i valori venivano scartati in silenzio.
ATTRIBUTI_BREVO = {
    "NOME": "text",                    # il nome, per il «Ciao {{ contact.NOME }}» (attributo gia' in Brevo)
    "AURYA_STATUS": "text",            # pending | confirmed | unsubscribed | deleted
    "AURYA_INVIABILE": "boolean",      # LA chiave dei segmenti: true solo se confermato e col consenso
    "AURYA_TOPICS": "text",            # csv temi Magazine
    "AURYA_FORMAT": "text",            # all | practices
    "AURYA_ALERT": "text",             # off | italy | csv regioni
    "AURYA_SOURCE": "text",            # fonte grezza di iscrizione
    "AURYA_CANALE": "text",            # provenienza.canale (sito, sound, account, magazine...)
    "AURYA_SUPERFICIE": "text",        # provenienza.superficie (cerca-ritiro, cancello, signup-pro...)
    "AURYA_PORTA": "text",             # meditazioni | altro
    "AURYA_LANG": "text",
    "AURYA_INTERESTS": "text",         # LE VIE, csv (yoga, meditazione, suono...)
    "AURYA_CITY": "text",
    "AURYA_TRAVEL": "text",            # near | italy | anywhere | abroad
    "AURYA_BUDGET": "text",            # under500 | 500to1000 | over1000 | flexible
    "AURYA_ETA": "text",               # 18-29 | 30-44 | 45-59 | 60+
    "AURYA_ISCRITTO_IL": "date",       # YYYY-MM-DD
    "AURYA_CONFERMATO_IL": "date",     # YYYY-MM-DD (assente finche' pending)
    "AURYA_VERIFICATO": "boolean",     # indirizzo provato (clic / account / admin)
    "AURYA_CONSENSO_VERSIONE": "text", # versione del testo della casella accettata
}
_PROIEZIONE_SYNC = {"_id": 0, "status": 1, "preferences": 1, "source": 1, "language": 1,
                    "profile": 1, "provenienza": 1,
                    # BS: le info di valore in piu'
                    "name": 1, "created_at": 1, "confirmed_at": 1, "verificato_at": 1,
                    "consent": 1, "consenso": 1}


def _data(v) -> str:
    """datetime o iso → «YYYY-MM-DD» (il formato delle date di Brevo); vuoto se manca."""
    if not v:
        return ""
    if hasattr(v, "strftime"):
        return v.strftime("%Y-%m-%d")
    return str(v)[:10]


def _attributes(doc: dict) -> dict:
    prefs = doc.get("preferences") or {}
    alert = prefs.get("retreat_alert") or {}
    if not alert.get("enabled"):
        alert_val = "off"
    elif alert.get("scope") == "regions" and alert.get("regions"):
        alert_val = ",".join(alert["regions"])
    else:
        alert_val = "italy"
    profile = doc.get("profile") or {}
    prov = doc.get("provenienza") or {}
    from services.sequenze import porta_cerchio      # lazy: niente cicli d'import
    out = {
        "NOME": " ".join(str(doc.get("name") or "").split())[:80],
        # BS — la chiave dei segmenti: la stessa regola con cui il Cerchio
        # scrive (status confermato + consenso), cosi' una campagna fatta
        # «a tutti» per sbaglio non raggiunge chi non ha confermato
        "AURYA_INVIABILE": doc.get("status") == "confirmed" and doc.get("consent") is True,
        "AURYA_SUPERFICIE": prov.get("superficie") or "",
        "AURYA_PORTA": porta_cerchio(doc.get("source")),
        "AURYA_ISCRITTO_IL": _data(doc.get("created_at")),
        "AURYA_CONFERMATO_IL": _data(doc.get("confirmed_at")),
        "AURYA_VERIFICATO": bool(doc.get("verificato_at")),
        "AURYA_CONSENSO_VERSIONE": (doc.get("consenso") or {}).get("versione") or "",
        "AURYA_STATUS": doc.get("status") or "pending",
        "AURYA_TOPICS": ",".join(prefs.get("topics") or []),
        "AURYA_FORMAT": prefs.get("format") or "all",
        "AURYA_ALERT": alert_val,
        "AURYA_SOURCE": doc.get("source") or "",
        "AURYA_LANG": doc.get("language") or "it",
        # NW1 — profilo esperienziale per la segmentazione delle
        # proposte ritiri (vuoti se l'iscritto non ha acceso il flag)
        "AURYA_INTERESTS": ",".join(profile.get("interests") or []),
        "AURYA_CITY": profile.get("city") or "",
        "AURYA_TRAVEL": profile.get("travel") or "",
        # Lotto B4 (24/9/2026) — gli stessi assi della lista iscritti,
        # cosi' le liste Brevo si segmentano per budget e per canale
        "AURYA_BUDGET": profile.get("budget") or "",
        "AURYA_CANALE": (doc.get("provenienza") or {}).get("canale") or "",
        # ET1 (2/10/2026) — la fascia d'eta' (attributo da creare in Brevo)
        "AURYA_ETA": profile.get("eta") or "",
    }
    # una data vuota farebbe rifiutare l'INTERO upsert da Brevo: si omette
    # (le date non si cancellano mai, al massimo arrivano dopo)
    return {k: v for k, v in out.items() if not (ATTRIBUTI_BREVO.get(k) == "date" and not v)}


def _push_to_brevo(email: str, attributes: dict, blacklisted: bool) -> bool:
    """Chiamata bloccante (eseguita in thread): upsert contatto.
    Ritorna True se Brevo ha accettato (per il backfill); mai un raise
    sull'esito, solo il warning di sempre."""
    api_key = os.environ.get("BREVO_API_KEY", "")
    if not api_key:
        logger.info("brevo sync [DRY RUN] %s status=%s", email,
                    attributes.get("AURYA_STATUS"))
        return True
    import requests
    payload = {
        "email": email,
        "attributes": attributes,
        "emailBlacklisted": blacklisted,
        "updateEnabled": True,
    }
    list_id = os.environ.get("BREVO_LIST_ID", "").strip()
    if list_id.isdigit():
        payload["listIds"] = [int(list_id)]
    resp = requests.post(
        _CONTACTS_URL, json=payload,
        headers={"api-key": api_key, "Content-Type": "application/json"},
        timeout=10)
    if resp.status_code not in (200, 201, 204):
        logger.warning("brevo sync failed for contact (%s): %s",
                       resp.status_code, resp.text[:200])
        return False
    return True


async def sync_subscriber(email: str) -> None:
    """Legge il doc dal DB e lo riflette su Brevo. Mai un raise."""
    try:
        from database import db
        # B4 (24/9): la proiezione non portava `profile`, quindi
        # AURYA_INTERESTS/CITY/TRAVEL arrivavano sempre vuoti; BS (2/10):
        # un'unica proiezione, la stessa del backfill
        doc = await db.aurya_subscribers.find_one({"email": email}, _PROIEZIONE_SYNC)
        if not doc:
            return
        await asyncio.to_thread(
            _push_to_brevo, email, _attributes(doc),
            doc.get("status") == "unsubscribed")
    except Exception as exc:                # noqa: BLE001 — best-effort
        logger.warning("brevo sync error: %s", exc)


async def blacklist_subscriber(email: str) -> None:
    """B4 — dopo una cancellazione GDPR il documento non c'e' piu':
    Brevo va messo in blacklist a mano, senza attributi. Mai un raise."""
    try:
        await asyncio.to_thread(
            _push_to_brevo, email, {"AURYA_STATUS": "deleted"}, True)
    except Exception as exc:                # noqa: BLE001
        logger.warning("brevo blacklist error: %s", exc)


def blacklist_subscriber_background(email: str) -> None:
    try:
        asyncio.get_running_loop().create_task(blacklist_subscriber(email))
    except RuntimeError:
        asyncio.run(blacklist_subscriber(email))


def sync_subscriber_background(email: str) -> None:
    """Fire-and-forget dal request handler (non allunga la risposta)."""
    try:
        asyncio.get_running_loop().create_task(sync_subscriber(email))
    except RuntimeError:
        # nessun loop (script sync): esegui inline
        asyncio.run(sync_subscriber(email))
