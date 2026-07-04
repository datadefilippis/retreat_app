"""Comunicazioni automatiche pre/post ritiro (Fase 4).

Job orario `event-comms-scan` sullo scheduler (lock Mongo + journal):
  T-7  promemoria "ci siamo quasi" (template reminder esistente)
  T-1  info pratiche (template logistics esistente: venue, indirizzo, note)
  T+2  grazie post-ritiro (template followup, Fase 4)

Solo occurrence PUBLISHED (o closed per il T+2 — un ritiro chiuso alle
vendite si è comunque tenuto). Draft e cancelled mai.

IDEMPOTENZA: write-ahead su occurrence.comms_sent (stesso pattern del
dunning): il mark si scrive atomico PRIMA dell'invio — re-run e runner
concorrenti non duplicano mai un broadcast. Il broadcast stesso passa da
broadcast_to_attendees (esclude i biglietti voided, localizza per
destinatario, rispetta l'email gate bounced/blocked/unsubscribed).
"""

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from models.common import utc_now
from services.scheduler_service import register_job

logger = logging.getLogger(__name__)

# (kind, template, quando è "dovuta" rispetto a start/end)
#   t-7 : da 7 giorni prima dell'inizio fino all'inizio
#   t-1 : da 1 giorno prima dell'inizio fino all'inizio
#   t+2 : da 2 giorni dopo la FINE (o inizio se end assente) fino a +7
#         (oltre i 7 giorni un "grazie" tardivo è peggio di niente)
_WINDOWS = [
    ("t-7", "reminder", -7.0, 0.0),
    ("t-1", "logistics", -1.0, 0.0),
    ("t+2", "followup", 2.0, 7.0),
]


def _parse(dt: str) -> Optional[datetime]:
    try:
        d = datetime.fromisoformat(dt)
        return d if d.tzinfo else d.replace(tzinfo=timezone.utc)
    except (ValueError, TypeError):
        return None


def plan_event_comms(occurrence: Dict[str, Any],
                     now: Optional[datetime] = None) -> List[Dict[str, str]]:
    """Quali comunicazioni sono dovute ADESSO per questa occurrence. Puro.

    Ritorna [{"kind", "template"}] escludendo quelle già in comms_sent.
    """
    status = occurrence.get("status")
    if status not in ("published", "closed"):
        return []
    start = _parse(occurrence.get("start_at") or "")
    if not start:
        return []
    end = _parse(occurrence.get("end_at") or "") or start
    now = now or utc_now()
    sent = {m.get("kind") for m in (occurrence.get("comms_sent") or [])}

    due: List[Dict[str, str]] = []
    for kind, template, lo, hi in _WINDOWS:
        if kind in sent:
            continue
        anchor = end if kind == "t+2" else start
        delta_days = (now - anchor).total_seconds() / 86400
        # pre-evento: dovuta quando now è tra (start+lo) e (start+hi)
        if lo <= delta_days <= hi:
            # t-7/t-1 non hanno senso per ritiri già iniziati (delta>0
            # escluso da hi=0); t+2 solo dopo la fine.
            if kind != "t+2" and status != "published":
                continue   # reminder/logistics solo su eventi ancora in vendita
            due.append({"kind": kind, "template": template})
    return due


async def _mark_comms_sent(occurrence_id: str, org_id: str, kind: str) -> bool:
    """Write-ahead atomico su comms_sent: True se il mark è nostro."""
    from database import event_occurrences_collection
    result = await event_occurrences_collection.update_one(
        {"id": occurrence_id, "organization_id": org_id,
         "comms_sent.kind": {"$ne": kind}},
        {"$push": {"comms_sent": {"kind": kind,
                                  "at": utc_now().isoformat()}}},
    )
    return getattr(result, "modified_count", 0) > 0


async def run_event_comms_scan(now: Optional[datetime] = None) -> Dict[str, Any]:
    from database import event_occurrences_collection
    from services.event_email_service import broadcast_to_attendees

    now = now or utc_now()
    summary = {"scanned": 0, "broadcasts": 0, "recipients": 0, "errors": 0}

    # Finestra grezza: eventi che iniziano entro 8 giorni o finiti da meno
    # di 8 — il planner poi decide con precisione.
    cursor = event_occurrences_collection.find(
        {"status": {"$in": ["published", "closed"]}},
        {"_id": 0},
    )
    async for occ in cursor:
        summary["scanned"] += 1
        try:
            for action in plan_event_comms(occ, now):
                if not await _mark_comms_sent(occ["id"], occ["organization_id"],
                                              action["kind"]):
                    continue   # già inviata (re-run / runner concorrente)
                result = await broadcast_to_attendees(
                    org_id=occ["organization_id"],
                    occurrence_id=occ["id"],
                    template_key=action["template"],
                )
                summary["broadcasts"] += 1
                summary["recipients"] += (result or {}).get("sent", 0)
                logger.info(
                    "event_comms: %s (%s) inviata per occ=%s → %s destinatari",
                    action["kind"], action["template"], occ["id"],
                    (result or {}).get("sent", 0),
                )
        except Exception:
            logger.exception("event_comms: occ %s fallita", occ.get("id"))
            summary["errors"] += 1
    return summary


@register_job("event-comms-scan", interval_seconds=3600)
async def event_comms_scan_job() -> Dict[str, Any]:
    return await run_event_comms_scan()
