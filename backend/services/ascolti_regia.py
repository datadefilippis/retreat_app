"""ASCOLTI — l'abitudine di chi ascolta e la regia (lotto CS, 8/10/2026).

docs/PIANO_CASA_CONSIGLI_2026-10-08.md. Gli eventi stanno in `sound_ascolti`
(evento: avvio · q25 · q50 · q75 · fine; secondo; at; slug; account_id).
Qui si RIASSUMONO, non si scrive nulla: `abitudine(account_id)` per il
motore dei consigli (CS2); le viste della regia (CS4) sono sotto.
Le ore si leggono nel fuso di Roma: il pubblico e' italiano e la fascia
(mattina · pausa · sera · notte) e' quella che la persona vive.
"""
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from database import db

ROMA = ZoneInfo("Europe/Rome")
GIORNI_ABITUDINE = 90
GIORNI_STANCHEZZA = 7


def fascia_ora(h: int) -> str:
    if 5 <= h < 11:
        return "mattina"
    if 11 <= h < 17:
        return "pausa"
    if 17 <= h < 22:
        return "sera"
    return "notte"


def _locale(at):
    if at is None:
        return None
    if at.tzinfo is None:
        at = at.replace(tzinfo=timezone.utc)
    return at.astimezone(ROMA)


async def abitudine(account_id: str) -> dict:
    """Quello che il motore dei consigli chiede della persona, dagli eventi:
    fascia abituale, durata media di un ascolto, completamenti recenti,
    ascoltati oggi/ieri, ultimo ascolto per titolo. Mai bloccante."""
    if not account_id:
        return {}
    da = datetime.now(timezone.utc) - timedelta(days=GIORNI_ABITUDINE)
    cur = db.sound_ascolti.find(
        {"account_id": account_id, "at": {"$gte": da}},
        {"_id": 0, "evento": 1, "secondo": 1, "at": 1, "slug": 1},
    ).sort("at", 1)
    fasce = Counter()
    sessioni = defaultdict(int)        # (slug, giorno) -> secondo massimo
    completati = Counter()
    ascoltati_oggi = set()
    ultimo = {}
    adesso = datetime.now(timezone.utc)
    soglia_oggi = adesso - timedelta(hours=36)
    soglia_7 = adesso - timedelta(days=GIORNI_STANCHEZZA)
    async for e in cur:
        at = e.get("at")
        if at is None:
            continue
        at_utc = at if at.tzinfo else at.replace(tzinfo=timezone.utc)
        loc = _locale(at)
        slug = e.get("slug") or ""
        ev = e.get("evento")
        if ev == "avvio":
            fasce[fascia_ora(loc.hour)] += 1
            if at_utc >= soglia_oggi:
                ascoltati_oggi.add(slug)
            ultimo[slug] = int(at_utc.timestamp() * 1000)
        k = (slug, loc.date().isoformat())
        sessioni[k] = max(sessioni[k], int(e.get("secondo") or 0))
        if ev == "fine" and at_utc >= soglia_7:
            completati[slug] += 1
    fascia = fasce.most_common(1)[0][0] if sum(fasce.values()) >= 3 else None
    durate = [v for v in sessioni.values() if v > 0]
    return {
        "fascia": fascia,
        "durata_media_sec": int(sum(durate) / len(durate)) if durate else 0,
        "completati": dict(completati),
        "ascoltati_oggi": sorted(ascoltati_oggi),
        "ultimo_ascolto": ultimo,
        "ascolti_90g": sum(fasce.values()),
    }
