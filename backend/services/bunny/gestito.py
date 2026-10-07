"""
Bunny GESTITO da Aurya — AC1 (7/10/2026, docs/PIANO_ACCADEMIA_2026-10-06.md §2).

Un solo account Bunny (chiave in env `BUNNY_ACCOUNT_API_KEY`, mai nel
browser, mai nel documento dell'org), UNA libreria Stream per operatore
creata via API alla prima lezione video, upload DIRETTO dal browser con
credenziali TUS firmate dal server, webhook firmato (HMAC della libreria)
che porta la lezione da «in codifica» a «pronto».

COSTI, le leve (founder 7/10: «minimizzare i costi Bunny senza perdere
qualita' ne' velocita'»):
  - risoluzioni 360p · 720p · 1080p (niente 240p, 1440p, 2160p): ogni
    risoluzione e' una copia in archivio; 1080p e' il massimo che un corso
    registrato con un telefono o una webcam porta davvero;
  - KeepOriginalFiles = False: l'originale caricato (spesso 3-5 GB) sparisce
    dopo la codifica; restano solo le rendition;
  - codifica standard (non premium, niente JIT): gratis;
  - nessuna replica geografica: una regione (Europa) basta;
  - MP4 fallback spento e direct play spento: niente copie extra ne' URL
    non firmati;
  - adattivo HLS: da telefono chi guarda riceve 720p o meno → meno traffico.
  Le quote per piano (video_gb) si contano alla creazione del video e si
  correggono dal webhook con la dimensione reale.

SICUREZZA: token auth sulla libreria (gli URL non firmati non partono),
referrer limitati ai nostri domini, chiave di libreria nel documento org
(come le librerie personali di oggi; cifratura a riposo in un lotto dopo),
chiave di account solo in env; la firma TUS scade in 10 minuti; il webhook
si verifica con HMAC-SHA256 del corpo e la ReadOnlyApiKey della libreria,
confronto a tempo costante.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import logging
import os
import secrets
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

TUS_ENDPOINT = "https://video.bunnycdn.com/tusupload"
TUS_TTL_SECONDS = 600            # la firma dell'upload vale 10 minuti (si rinnova)
RISOLUZIONI = "360p,720p,1080p"  # la leva principale sui costi di archivio
DOMINI_PLAYER = ("aurya.life", "www.aurya.life", "localhost")

# le impostazioni della libreria gestita: costi e sicurezza, in un posto solo
IMPOSTAZIONI_LIBRERIA: Dict[str, Any] = {
    "EnabledResolutions": RISOLUZIONI,
    "KeepOriginalFiles": False,
    "PlayerTokenAuthenticationEnabled": True,
    "AllowDirectPlay": False,
    "EnableMP4Fallback": False,
    "AllowedReferrers": list(DOMINI_PLAYER),
}

# ATTENZIONE: due vocabolari diversi (provato il 7/10 sulla chiave vera).
# Il WEBHOOK manda Status: 0 in coda, 1 elaborazione, 2 codifica, 3 FINITO,
# 4 una risoluzione pronta (riproducibile), 5 errore, 6-8 upload firmato.
STATI_VIDEO = {
    0: "codifica", 1: "codifica", 2: "codifica",
    3: "pronto", 4: "pronto",
    5: "errore",
    6: "caricamento", 7: "codifica", 8: "errore",
}
# L'OGGETTO VIDEO (GET /videos/{guid}) ha `status`: 0 creato, 1 caricato,
# 2 elaborazione, 3 TRANSCODIFICA, 4 FINITO, 5 errore, 6 upload fallito,
# 7-8 JIT. Qui «pronto» e' SOLO 4.
STATI_OGGETTO_VIDEO = {
    0: "caricamento", 1: "codifica", 2: "codifica", 3: "codifica",
    4: "pronto", 5: "errore", 6: "errore", 7: "codifica", 8: "codifica",
}


def chiave_account() -> Optional[str]:
    k = (os.environ.get("BUNNY_ACCOUNT_API_KEY") or "").strip()
    return k or None


def attivo() -> bool:
    """Senza la chiave di account l'upload non parte (locale senza env,
    prod prima che il founder apra l'account): le pagine lo dicono."""
    return chiave_account() is not None


def url_webhook() -> str:
    base = (os.environ.get("BUNNY_WEBHOOK_BASE_URL") or os.environ.get("PUBLIC_APP_URL") or "").rstrip("/")
    return f"{base}/api/webhooks/bunny"


def firma_tus(library_id: str, api_key: str, expire: int, video_id: str) -> str:
    """Documentazione Bunny: SHA256(library_id + api_key + expiration_time + video_id)."""
    return hashlib.sha256(f"{library_id}{api_key}{expire}{video_id}".encode("utf-8")).hexdigest()


def credenziali_tus(lib: Dict[str, Any], video_guid: str, ttl: int = TUS_TTL_SECONDS) -> Dict[str, Any]:
    """Quello che il browser riceve per caricare: endpoint, header, scadenza.
    La chiave API NON viaggia: viaggia la firma, che scade."""
    expire = int(time.time()) + int(ttl)
    return {
        "tus_endpoint": TUS_ENDPOINT,
        "headers": {
            "AuthorizationSignature": firma_tus(str(lib["library_id"]), lib["api_key"], expire, video_guid),
            "AuthorizationExpire": str(expire),
            "VideoId": video_guid,
            "LibraryId": str(lib["library_id"]),
        },
        "expires_at": datetime.fromtimestamp(expire, tz=timezone.utc).isoformat(),
        "video_guid": video_guid,
    }


def firma_webhook_valida(corpo: bytes, firma: Optional[str], read_only_api_key: Optional[str]) -> bool:
    """HMAC-SHA256 del corpo grezzo con la ReadOnlyApiKey della libreria,
    confrontato a tempo costante (documentazione Bunny, header
    X-BunnyStream-Signature)."""
    if not firma or not read_only_api_key:
        return False
    atteso = hmac.new(read_only_api_key.encode("utf-8"), corpo, hashlib.sha256).hexdigest()
    return hmac.compare_digest(atteso.lower(), str(firma).strip().lower())


def libreria_gestita_di(org: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """La libreria creata da Aurya per questa org, se esiste."""
    for lib in ((org or {}).get("integrations") or {}).get("bunny_libraries") or []:
        if lib.get("managed"):
            return lib
    return None


def nome_libreria(org: Dict[str, Any]) -> str:
    slug = (org.get("public_slug") or org.get("id") or "org")[:40]
    return f"aurya-{slug}"


async def assicura_libreria(org_id: str) -> Dict[str, Any]:
    """Get-or-create della libreria gestita dell'org. Crea su Bunny (account
    Aurya), applica le impostazioni di costo e sicurezza, legge l'hostname
    del pull zone, salva nel documento org con managed=True. Idempotente:
    se esiste, la restituisce senza chiamare Bunny."""
    from database import organizations_collection
    org = await organizations_collection.find_one({"id": org_id}, {"_id": 0, "id": 1, "public_slug": 1, "integrations": 1})
    if not org:
        raise LookupError("org non trovata")
    esistente = libreria_gestita_di(org)
    if esistente:
        return esistente
    chiave = chiave_account()
    if not chiave:
        raise RuntimeError("bunny_non_configurato")
    from services.bunny.client import BunnyAccountClient
    async with BunnyAccountClient(chiave) as acc:
        # prima si cerca una libreria con lo stesso nome gia' sull'account
        # (un salvataggio fallito non deve lasciare orfani su Bunny)
        creata = None
        try:
            for esistente_bunny in await acc.list_libraries():
                if esistente_bunny.get("Name") == nome_libreria(org):
                    creata = await acc.get_library(str(esistente_bunny.get("Id")))
                    logger.info("bunny gestito: adotto la libreria %s gia' esistente per org %s", creata.get("Id"), org_id)
                    break
        except Exception as exc:  # noqa: BLE001 — se la lista non risponde, si crea
            logger.warning("bunny gestito: lista librerie non letta: %s", exc)
        if creata is None:
            creata = await acc.create_library(nome_libreria(org))
        library_id = str(creata.get("Id"))
        impostazioni = dict(IMPOSTAZIONI_LIBRERIA)
        wh = url_webhook()
        if wh.startswith("https://"):
            impostazioni["WebhookUrl"] = wh
        try:
            await acc.update_library(library_id, impostazioni)
        except Exception as exc:  # noqa: BLE001 — la libreria esiste: le impostazioni si riprovano
            logger.warning("bunny gestito: impostazioni non applicate alla libreria %s: %s", library_id, exc)
        # i referrer passano dall'endpoint dedicato (il campo nell'update e' ignorato)
        for dominio in DOMINI_PLAYER:
            try:
                await acc.add_allowed_referrer(library_id, dominio)
            except Exception as exc:  # noqa: BLE001
                logger.warning("bunny gestito: referrer %s non aggiunto alla libreria %s: %s", dominio, library_id, exc)
        hostname = None
        zone_key = None
        pull_zone_id = str(creata.get("PullZoneId") or "") or None
        try:
            if pull_zone_id:
                # la PROTEZIONE VERA: token auth sul pull zone (ZoneSecurity). Provato
                # il 7/10: con questo acceso playlist e miniature rispondono 403
                # senza firma anche col referrer giusto; la chiave del pull zone e'
                # la `token_security_key` che firma embed e file CDN.
                await acc.update_pullzone(pull_zone_id, {"ZoneSecurityEnabled": True,
                                                         "ZoneSecurityIncludeHashRemoteIP": False})
                pz = await acc.get_pullzone(pull_zone_id)
                nomi = [h.get("Value") for h in (pz.get("Hostnames") or []) if h.get("Value")]
                hostname = nomi[0] if nomi else None
                zone_key = pz.get("ZoneSecurityKey") or None
        except Exception as exc:  # noqa: BLE001
            logger.warning("bunny gestito: pull zone non configurato: %s", exc)
    librerie = (org.get("integrations") or {}).get("bunny_libraries") or []
    now = datetime.now(timezone.utc).isoformat()
    lib = {
        "id": secrets.token_urlsafe(8),
        "alias": "Aurya",
        "is_default": not any(l.get("is_default") for l in librerie),
        "library_id": library_id,
        "api_key": creata.get("ApiKey") or "",
        "read_only_api_key": creata.get("ReadOnlyApiKey") or None,
        "token_security_key": zone_key,  # la chiave del pull zone: firma embed e file CDN
        "pull_zone_id": pull_zone_id,
        "cdn_hostname": hostname,
        "watermark_enabled": True,
        "managed": True,
        "created_by": "aurya",
        "quota": {"video_bytes": 0, "video_count": 0},
        "library_name": nome_libreria(org),
        "created_at": now, "updated_at": now,
    }
    # `integrations` puo' essere null sulle org nate prima: $push non puo'
    # creare un campo dentro un null → in quel caso si scrive l'oggetto intero
    if isinstance(org.get("integrations"), dict):
        await organizations_collection.update_one(
            {"id": org_id}, {"$push": {"integrations.bunny_libraries": lib}})
    else:
        await organizations_collection.update_one(
            {"id": org_id}, {"$set": {"integrations": {"bunny_libraries": [lib]}}})
    logger.info("bunny gestito: libreria %s pronta per org %s", library_id, org_id)
    return lib


async def org_per_libreria(library_id: str) -> Optional[Dict[str, Any]]:
    """L'org che possiede la libreria Bunny `library_id` (per il webhook)."""
    from database import organizations_collection
    return await organizations_collection.find_one(
        {"integrations.bunny_libraries.library_id": str(library_id)},
        {"_id": 0, "id": 1, "integrations": 1})


def libreria_per_id_bunny(org: Dict[str, Any], library_id: str) -> Optional[Dict[str, Any]]:
    for lib in ((org or {}).get("integrations") or {}).get("bunny_libraries") or []:
        if str(lib.get("library_id")) == str(library_id):
            return lib
    return None


def stato_da_bunny(status: Any) -> str:
    """Dal `Status` del WEBHOOK allo stato della lezione."""
    try:
        return STATI_VIDEO.get(int(status), "codifica")
    except (TypeError, ValueError):
        return "codifica"


def stato_da_oggetto_video(status: Any) -> str:
    """Dal `status` dell'OGGETTO video (GET) allo stato della lezione."""
    try:
        return STATI_OGGETTO_VIDEO.get(int(status), "codifica")
    except (TypeError, ValueError):
        return "codifica"


def url_thumbnail(lib: Dict[str, Any], video: Dict[str, Any]) -> Optional[str]:
    """L'URL NUDO della miniatura (si salva questo); con il token auth della
    libreria si serve solo firmato: vedi `firma_url_cdn` al momento della lettura."""
    host = lib.get("cdn_hostname")
    nome = video.get("thumbnailFileName")
    guid = video.get("guid")
    if host and nome and guid:
        return f"https://{host}/{guid}/{nome}"
    return None


THUMB_TTL_SECONDS = 24 * 3600


def firma_url_cdn(lib: Dict[str, Any], url: Optional[str], video_guid: str = "", ttl: int = THUMB_TTL_SECONDS) -> Optional[str]:
    """Firma di un FILE del CDN (miniatura, playlist) con il token auth del
    pull zone. Provato il 7/10: lo schema e' quello del CDN Bunny —
    token = base64url(sha256_raw(zone_key + path + expires)) — NON quello
    dell'embed (che e' sha256_hex(key + guid + expires)). Senza chiave del
    pull zone l'URL resta nudo (libreria senza ZoneSecurity: protegge il
    referrer). La firma vive 24 ore e si rifa' a ogni lettura."""
    if not url:
        return url
    chiave = lib.get("token_security_key")
    if not chiave:
        return url
    from urllib.parse import urlsplit
    path = urlsplit(url).path or "/"
    expire = int(time.time()) + int(ttl)
    raw = hashlib.sha256(f"{chiave}{path}{expire}".encode("utf-8")).digest()
    token = base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")
    sep = "&" if "?" in url else "?"
    return f"{url}{sep}token={token}&expires={expire}"


async def aggiorna_quota(org_id: str, lib_id: str, delta_bytes: int, delta_count: int) -> None:
    from database import organizations_collection
    await organizations_collection.update_one(
        {"id": org_id, "integrations.bunny_libraries.id": lib_id},
        {"$inc": {"integrations.bunny_libraries.$.quota.video_bytes": int(delta_bytes),
                  "integrations.bunny_libraries.$.quota.video_count": int(delta_count)}})


def gb(n_bytes: Any) -> float:
    try:
        return round(int(n_bytes or 0) / (1024 ** 3), 3)
    except (TypeError, ValueError):
        return 0.0


__all__: List[str] = [
    "TUS_ENDPOINT", "TUS_TTL_SECONDS", "RISOLUZIONI", "IMPOSTAZIONI_LIBRERIA", "STATI_VIDEO",
    "chiave_account", "attivo", "url_webhook", "firma_tus", "credenziali_tus", "firma_webhook_valida",
    "libreria_gestita_di", "assicura_libreria", "org_per_libreria", "libreria_per_id_bunny",
    "stato_da_bunny", "stato_da_oggetto_video", "url_thumbnail", "firma_url_cdn", "THUMB_TTL_SECONDS", "aggiorna_quota", "gb",
]
