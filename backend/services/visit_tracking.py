"""VT — Visibilità operatore: motore di misurazione first-party.

Privacy by design (il cookie banner promette 'nessuna analytics
esterna' e resta VERO): niente cookie, niente IP salvati, visitor_hash
con salt che ruota ogni giorno (mai ricostruibile un percorso tra
giorni), referrer solo hostname. Anti-bot: filtro User-Agent qui +
il ping parte solo dal JS (i crawler senza JS non arrivano proprio).

Due collection:
- page_views: un doc per (visitor, superficie, slug, giorno) con
  contatore hits → uniques = count(docs), views = sum(hits).
  TTL 13 mesi sui grezzi.
- visibility_stats: aggregati day-level (per ora: impression dai
  listing, VT3) → vive per sempre, è ciò che la dashboard legge
  per lo storico lungo.

Best-effort ASSOLUTO: nessuna funzione qui può far fallire la
richiesta che la ospita.
"""

import asyncio
import hashlib
import logging
import os
import time
from datetime import datetime, timezone
from typing import Dict, Iterable, Optional, Tuple

logger = logging.getLogger(__name__)

SURFACES = ("profile", "event", "store")
CHANNELS = ("directory", "store", "search", "social", "direct")

# UA di bot/crawler/tool: mai contati (né visite né impression).
_BOT_MARKERS = (
    "bot", "crawler", "spider", "slurp", "curl", "wget", "python-requests",
    "httpx", "aiohttp", "java/", "go-http-client", "headless", "phantomjs",
    "lighthouse", "pagespeed", "pingdom", "uptimerobot", "facebookexternalhit",
    "whatsapp", "telegrambot", "skypeuripreview", "preview", "scrapy",
    "ahrefs", "semrush", "mj12", "dotbot", "petalbot", "bytespider", "gptbot",
    "claude-web", "ccbot", "dataforseo",
)


def is_bot(user_agent: Optional[str]) -> bool:
    """True se lo User-Agent è (quasi certamente) un bot. UA vuoto =
    bot: i browser veri lo mandano sempre."""
    if not user_agent:
        return True
    ua = user_agent.lower()
    return any(marker in ua for marker in _BOT_MARKERS)


def _today() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def visitor_hash(ip: Optional[str], user_agent: Optional[str],
                 day: Optional[str] = None) -> str:
    """Impronta ANONIMA del visitatore, valida un giorno solo.

    salt = sha256(secret + giorno): ruota a mezzanotte UTC → lo stesso
    visitatore domani ha un hash diverso, nessun percorso ricostruibile.
    L'IP entra nell'hash ma NON viene mai salvato da nessuna parte.
    """
    day = day or _today()
    secret = os.environ.get("JWT_SECRET_KEY", "dev")
    salt = hashlib.sha256(f"{secret}:{day}".encode()).hexdigest()
    raw = f"{salt}:{ip or ''}:{user_agent or ''}"
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


async def record_view(*, organization_id: str, surface: str, slug: str,
                      channel: str, referrer_host: Optional[str],
                      lang: Optional[str], ip: Optional[str],
                      user_agent: Optional[str]) -> None:
    """Registra una vista. Dedup naturale: un doc per (visitor,
    superficie, slug, giorno), i refresh incrementano hits ma uniques
    resta 1. Mai raise."""
    try:
        if surface not in SURFACES or channel not in CHANNELS:
            return
        if is_bot(user_agent):
            return
        from database import db
        day = _today()
        vh = visitor_hash(ip, user_agent, day)
        await db.page_views.update_one(
            {"visitor_hash": vh, "surface": surface, "slug": slug[:120],
             "day": day},
            {"$inc": {"hits": 1},
             "$setOnInsert": {
                 "organization_id": organization_id,
                 "channel": channel,
                 "referrer_host": (referrer_host or "")[:100] or None,
                 "lang": (lang or "")[:2] or None,
                 "created_at": datetime.now(timezone.utc),
             }},
            upsert=True,
        )
    except Exception as exc:          # noqa: BLE001 — mai rompere la pagina
        logger.debug("record_view skipped: %s", exc)


# ─── Impression (VT3): batch in memoria, flush pigro ────────────────────
# I listing (/public/retreats, /public/operators) chiamano
# bump_impressions([org_ids]) per ogni risposta: accumuliamo in un dict
# e scriviamo su Mongo al massimo ogni _FLUSH_EVERY secondi. Niente
# background task da gestire: il flush parte dal bump successivo
# (lazy), quindi zero setup e zero rischio di task orfani.

_pending: Dict[Tuple[str, str], int] = {}
_last_flush = 0.0
_FLUSH_EVERY = 20.0
_flush_lock = asyncio.Lock()


def bump_impressions(org_ids: Iterable[str],
                     user_agent: Optional[str] = None) -> None:
    """+1 impression per ogni org apparsa in un listing. Sincrona e
    O(n) su un dict: costo invisibile nel percorso caldo. Il flush su
    Mongo è schedulato fire-and-forget quando è passato abbastanza
    tempo. I bot non contano."""
    global _last_flush
    try:
        if is_bot(user_agent):
            return
        day = _today()
        for oid in org_ids:
            if oid:
                key = (oid, day)
                _pending[key] = _pending.get(key, 0) + 1
        now = time.monotonic()
        if now - _last_flush >= _FLUSH_EVERY and _pending:
            _last_flush = now
            asyncio.get_running_loop().create_task(_flush())
    except Exception as exc:          # noqa: BLE001
        logger.debug("bump_impressions skipped: %s", exc)


async def _flush() -> None:
    """Scarica il batch su visibility_stats (day-level, $inc)."""
    async with _flush_lock:
        if not _pending:
            return
        batch = dict(_pending)
        _pending.clear()
        try:
            from database import db
            for (oid, day), count in batch.items():
                await db.visibility_stats.update_one(
                    {"organization_id": oid, "day": day,
                     "metric": "impressions"},
                    {"$inc": {"count": count}},
                    upsert=True,
                )
        except Exception as exc:      # noqa: BLE001 — perdere un batch di
            logger.debug("impressions flush skipped: %s", exc)  # imp. è ok


async def flush_now() -> None:
    """Per i test: forza il flush del batch pendente."""
    global _last_flush
    _last_flush = time.monotonic()
    await _flush()
