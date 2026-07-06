"""IndexNow — indicizzazione in ore invece che giorni (S3, SEO_MASTER_PLAN).

Protocollo aperto (Bing, Seznam, Yandex, Naver): al publish/update di
un contenuto si "pinga" l'URL e i motori aderenti lo crawlano subito.
Google non aderisce ma scopre comunque via sitemap (lastmod).

Config:
  INDEXNOW_KEY   chiave esadecimale (openssl rand -hex 16). Se assente,
                 il servizio è NO-OP (dev/staging).

Verifica di proprietà: il motore controlla che
  https://{host}/{INDEXNOW_KEY}.txt
risponda con la chiave — servita da GET /indexnow-key (router seo_shell
non c'entra: route dedicata in server.py, regola proxy in
DEPLOY_CHECKLIST).

Best-effort by design: MAI bloccare un publish per un ping fallito.
"""

import json
import logging
import os
import urllib.request

logger = logging.getLogger(__name__)

_ENDPOINT = "https://api.indexnow.org/indexnow"


def indexnow_key() -> str:
    return (os.environ.get("INDEXNOW_KEY") or "").strip()


def _base_url() -> str:
    return os.environ.get("PUBLIC_APP_URL", "http://localhost:3000").rstrip("/")


def ping_urls(paths: list) -> bool:
    """Invia il batch di path (relativi) a IndexNow. Sync + best-effort:
    i chiamanti async lo lanciano via asyncio.to_thread o in task."""
    key = indexnow_key()
    if not key or not paths:
        return False
    base = _base_url()
    if base.startswith("http://localhost"):
        return False  # mai pingare dal dev
    host = base.split("://", 1)[1]
    body = json.dumps({
        "host": host,
        "key": key,
        "keyLocation": f"{base}/{key}.txt",
        "urlList": [f"{base}{p}" for p in paths[:100]],
    }).encode()
    try:
        req = urllib.request.Request(
            _ENDPOINT, data=body,
            headers={"Content-Type": "application/json; charset=utf-8"},
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            ok = 200 <= resp.status < 300
        logger.info("indexnow: ping %d url → %s", len(paths),
                    "ok" if ok else f"status {resp.status}")
        return ok
    except Exception as exc:  # noqa: BLE001 — best-effort
        logger.warning("indexnow: ping fallito: %s", exc)
        return False


async def ping_urls_async(paths: list) -> None:
    """Fire-and-forget dal codice async (publish di prodotti/occorrenze)."""
    import asyncio
    try:
        await asyncio.to_thread(ping_urls, paths)
    except Exception as exc:  # noqa: BLE001
        logger.debug("indexnow: async ping error: %s", exc)
