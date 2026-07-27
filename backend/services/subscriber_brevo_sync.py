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


def _attributes(doc: dict) -> dict:
    prefs = doc.get("preferences") or {}
    alert = prefs.get("retreat_alert") or {}
    if not alert.get("enabled"):
        alert_val = "off"
    elif alert.get("scope") == "regions" and alert.get("regions"):
        alert_val = ",".join(alert["regions"])
    else:
        alert_val = "italy"
    return {
        "AURYA_STATUS": doc.get("status") or "pending",
        "AURYA_TOPICS": ",".join(prefs.get("topics") or []),
        "AURYA_FORMAT": prefs.get("format") or "all",
        "AURYA_ALERT": alert_val,
        "AURYA_SOURCE": doc.get("source") or "",
        "AURYA_LANG": doc.get("language") or "it",
    }


def _push_to_brevo(email: str, attributes: dict, blacklisted: bool) -> None:
    """Chiamata bloccante (eseguita in thread): upsert contatto."""
    api_key = os.environ.get("BREVO_API_KEY", "")
    if not api_key:
        logger.info("brevo sync [DRY RUN] %s status=%s", email,
                    attributes.get("AURYA_STATUS"))
        return
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


async def sync_subscriber(email: str) -> None:
    """Legge il doc dal DB e lo riflette su Brevo. Mai un raise."""
    try:
        from database import db
        doc = await db.aurya_subscribers.find_one(
            {"email": email},
            {"_id": 0, "status": 1, "preferences": 1, "source": 1,
             "language": 1})
        if not doc:
            return
        await asyncio.to_thread(
            _push_to_brevo, email, _attributes(doc),
            doc.get("status") == "unsubscribed")
    except Exception as exc:                # noqa: BLE001 — best-effort
        logger.warning("brevo sync error: %s", exc)


def sync_subscriber_background(email: str) -> None:
    """Fire-and-forget dal request handler (non allunga la risposta)."""
    try:
        asyncio.get_running_loop().create_task(sync_subscriber(email))
    except RuntimeError:
        # nessun loop (script sync): esegui inline
        asyncio.run(sync_subscriber(email))
