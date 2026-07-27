"""BN2 — migra i lead pre-lancio (type=traveler) in aurya_subscribers.

Idempotente e NON distruttivo: i prelaunch_leads restano dove sono
(archivio del funnel pre-lancio); qui si crea/aggiorna l'iscritto in
stato PENDING. Niente email di massa da questo script: la conferma
(double opt-in) partira' con la prima campagna ("conferma per
continuare a ricevere la lettera"), decisione founder in BN6.

Mappa interests (chip del LeadForm) → topics (categorie editoriali):
  yoga→yoga, meditation→meditazione, breathwork→breathwork,
  sound→suono, detox→detox, nature→cammini, women→femminile,
  mixed→(nessun topic: significa "tutto")

Uso: python scripts/bn2_migrate_leads_to_subscribers.py
"""

import asyncio
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

INTEREST_TO_TOPIC = {
    "yoga": "yoga", "meditation": "meditazione",
    "breathwork": "breathwork", "sound": "suono", "detox": "detox",
    "nature": "cammini", "women": "femminile",
}


async def main() -> None:
    from database import db
    from routers.subscribers import _clean_topics

    now = datetime.now(timezone.utc)
    migrated = skipped = 0
    async for lead in db.prelaunch_leads.find({"type": "traveler"}):
        email = (lead.get("email") or "").lower().strip()
        if not email:
            continue
        existing = await db.aurya_subscribers.find_one(
            {"email": email}, {"_id": 0, "status": 1})
        if existing:
            skipped += 1     # mai degradare un confirmed/unsubscribed
            continue
        topics = _clean_topics([INTEREST_TO_TOPIC.get(i)
                                for i in (lead.get("interests") or [])])
        await db.aurya_subscribers.insert_one({
            "email": email,
            "status": "pending",
            "name": lead.get("name"),
            "language": lead.get("language"),
            "source": "prelaunch_lead",
            "consent": bool(lead.get("consent")),
            "consent_at": lead.get("created_at") or now,
            "preferences": {"topics": topics, "format": "all",
                            "retreat_alert": {"enabled": True,
                                              "scope": "italy",
                                              "regions": []}},
            "profile": {k: lead.get(k) for k in ("city", "travel", "budget")
                        if lead.get(k)},
            "created_at": lead.get("created_at") or now,
            "updated_at": now,
        })
        migrated += 1
    print(f"migrati: {migrated}, gia' presenti: {skipped}")


if __name__ == "__main__":
    asyncio.run(main())
