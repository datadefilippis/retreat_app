"""MP3 (5/10/2026) — Meta Conversions API, lato server.

Piano: docs/PIANO_META_PIXEL_2026-10-05.md §2.2. Il pixel nel browser
(frontend/src/lib/meta.js) manda a Meta gli eventi che contano con un
`eventID`; lo stesso identificativo arriva qui dentro il blocco
`provenienza.tracciamento` del documento (iscritto, organizzazione,
account). Da qui parte la stessa cosa verso la Conversions API: Meta vede
due copie con lo stesso (event_name, event_id) e ne conta UNA. Il valore
e' doppio: gli eventi arrivano anche quando il browser blocca il pixel
(iOS, adblock), e la corrispondenza e' migliore grazie all'email hashata.

Regole della casa:
 - Si manda SOLO se `tracciamento.marketing` e' True (la persona ha
   accettato il marketing nel banner): senza, questo modulo non fa nulla.
 - L'email viaggia solo come SHA-256 (normalizzata); mai in chiaro, mai
   nei log. Il token vive solo nell'env (META_CAPI_TOKEN) e nel corpo
   della POST, mai in URL, log o risposta.
 - Mai bloccante: la spedizione e' un task in background con timeout 5s
   e 3 tentativi (solo su errori di rete/5xx/429); qualunque eccezione
   finisce in un warning. Un errore qui non puo' fermare un'iscrizione.
 - Ogni spedizione lascia una riga nel registro `tracciamento_eventi`
   (TTL 90 giorni) per la regia (MP4): quanti partiti, quanti accettati.
 - META_TEST_EVENT_CODE (facoltativo): gli eventi compaiono in «Testa gli
   eventi» di Gestione eventi senza contare nelle campagne. Si toglie a
   prova finita.
"""
from __future__ import annotations

import asyncio
import hashlib
import logging
import os
import re
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

logger = logging.getLogger(__name__)

API_VERSIONE = "v21.0"
TIMEOUT_S = 5.0
TENTATIVI = 3
TTL_REGISTRO_GIORNI = 90
EVENTI_STANDARD = ("Lead", "CompleteRegistration", "Contact", "Purchase", "PageView")

_TASK: set = set()
_INDICI_PRONTI = False
_RE_EVENT_ID = re.compile(r"^[A-Za-z0-9_\-]{8,64}$")


# ── configurazione ──────────────────────────────────────────────────────────

def pixel_id() -> Optional[str]:
    return (os.environ.get("META_PIXEL_ID") or "").strip() or None


def _token() -> Optional[str]:
    return (os.environ.get("META_CAPI_TOKEN") or "").strip() or None


def test_event_code() -> Optional[str]:
    return (os.environ.get("META_TEST_EVENT_CODE") or "").strip() or None


def configurato() -> bool:
    """Pixel e token presenti: solo allora si parla con Meta."""
    return bool(pixel_id() and _token())


# ── costruzione dell'evento ─────────────────────────────────────────────────

def hash_email(email: Optional[str]) -> Optional[str]:
    """SHA-256 dell'email normalizzata (minuscola, senza spazi), come vuole
    Meta. None se vuota."""
    e = (email or "").strip().lower()
    if not e or "@" not in e:
        return None
    return hashlib.sha256(e.encode("utf-8")).hexdigest()


def dati_utente(*, email: Optional[str] = None, fbp: Optional[str] = None, fbc: Optional[str] = None,
                ip: Optional[str] = None, user_agent: Optional[str] = None) -> dict:
    """Il blocco `user_data`: solo quello che c'e', mai l'email in chiaro."""
    out: dict[str, Any] = {}
    em = hash_email(email)
    if em:
        out["em"] = [em]
    if fbp:
        out["fbp"] = str(fbp)[:160]
    if fbc:
        out["fbc"] = str(fbc)[:160]
    if ip and ip not in ("127.0.0.1", "::1", "testclient"):
        out["client_ip_address"] = str(ip)[:64]
    if user_agent:
        out["client_user_agent"] = str(user_agent)[:300]
    return out


def costruisci_evento(nome: str, event_id: str, *, email: Optional[str] = None,
                      fbp: Optional[str] = None, fbc: Optional[str] = None,
                      ip: Optional[str] = None, user_agent: Optional[str] = None,
                      url: Optional[str] = None, custom_data: Optional[dict] = None,
                      quando: Optional[datetime] = None) -> dict:
    """Un evento nel formato della Conversions API (action_source website)."""
    quando = quando or datetime.now(timezone.utc)
    ev: dict[str, Any] = {
        "event_name": str(nome)[:64],
        "event_time": int(quando.timestamp()),
        "event_id": str(event_id)[:64],
        "action_source": "website",
        "user_data": dati_utente(email=email, fbp=fbp, fbc=fbc, ip=ip, user_agent=user_agent),
    }
    if url:
        ev["event_source_url"] = str(url)[:500]
    if custom_data:
        pulito = {k: v for k, v in custom_data.items() if v not in (None, "")}
        if pulito:
            ev["custom_data"] = pulito
    return ev


# ── spedizione ──────────────────────────────────────────────────────────────

def _messaggio_errore(risposta) -> str:
    """Il messaggio di Meta, corto e senza segreti (mai il token, mai email)."""
    try:
        err = (risposta.json() or {}).get("error") or {}
        msg = err.get("message") or ""
        return f"{err.get('code', '')} {msg}".strip()[:200]
    except Exception:  # noqa: BLE001
        return (risposta.text or "")[:120]


async def invia_eventi(eventi: list[dict], *, codice_test: Optional[str] = None) -> dict:
    """POST /{pixel}/events. Ritorna {ok, accettati, tentativi, errore}.
    Nuovo tentativo solo su rete, 5xx e 429; un 4xx e' definitivo."""
    if not configurato():
        return {"ok": False, "accettati": 0, "tentativi": 0, "errore": "non configurato"}
    if not eventi:
        return {"ok": True, "accettati": 0, "tentativi": 0, "errore": None}
    import httpx
    corpo: dict[str, Any] = {"data": eventi, "access_token": _token()}
    if codice_test:
        corpo["test_event_code"] = codice_test
    url = f"https://graph.facebook.com/{API_VERSIONE}/{pixel_id()}/events"
    errore = None
    for tentativo in range(1, TENTATIVI + 1):
        try:
            async with httpx.AsyncClient(timeout=TIMEOUT_S) as client:
                r = await client.post(url, json=corpo)
            if r.status_code == 200:
                ricevuti = 0
                try:
                    ricevuti = int((r.json() or {}).get("events_received") or 0)
                except Exception:  # noqa: BLE001
                    ricevuti = len(eventi)
                return {"ok": True, "accettati": ricevuti, "tentativi": tentativo, "errore": None}
            errore = f"http {r.status_code}: {_messaggio_errore(r)}"
            if 400 <= r.status_code < 500 and r.status_code != 429:
                return {"ok": False, "accettati": 0, "tentativi": tentativo, "errore": errore}
        except Exception as exc:  # noqa: BLE001 — rete, timeout, json
            errore = f"{type(exc).__name__}"
        if tentativo < TENTATIVI:
            await asyncio.sleep(0.5 * (2 ** (tentativo - 1)))
    return {"ok": False, "accettati": 0, "tentativi": TENTATIVI, "errore": errore}


# ── registro ────────────────────────────────────────────────────────────────

async def _registro():
    global _INDICI_PRONTI
    from database import db
    coll = db.tracciamento_eventi
    if not _INDICI_PRONTI:
        await coll.create_index("created_at", expireAfterSeconds=TTL_REGISTRO_GIORNI * 24 * 3600,
                                name="tracciamento_eventi_ttl")
        await coll.create_index([("event_id", 1), ("nome", 1)], name="tracciamento_eventi_evento")
        _INDICI_PRONTI = True
    return coll


async def _invia_e_registra(evento: dict, contesto: Optional[str]) -> None:
    """Il task in background: manda e annota. Mai un'eccezione verso l'alto."""
    try:
        codice = test_event_code()
        esito = await invia_eventi([evento], codice_test=codice)
        try:
            coll = await _registro()
            now = datetime.now(timezone.utc)
            await coll.insert_one({
                "event_id": evento.get("event_id"), "nome": evento.get("event_name"),
                "contesto": (contesto or "")[:60] or None,
                "stato": "accettato" if esito["ok"] and esito["accettati"] else ("inviato" if esito["ok"] else "fallito"),
                "accettati": int(esito.get("accettati") or 0), "tentativi": int(esito.get("tentativi") or 0),
                "errore": esito.get("errore"), "test": bool(codice),
                "con_email": "em" in (evento.get("user_data") or {}),
                "con_cookie": bool((evento.get("user_data") or {}).get("fbp") or (evento.get("user_data") or {}).get("fbc")),
                "created_at": now,
            })
        except Exception:  # noqa: BLE001 — il registro e' un di piu'
            logger.debug("meta_capi: registro non scritto", exc_info=True)
        if not esito["ok"]:
            logger.warning("meta_capi: evento %s (%s) non accettato: %s",
                           evento.get("event_name"), contesto, esito.get("errore"))
    except Exception:  # noqa: BLE001
        logger.warning("meta_capi: spedizione fallita", exc_info=True)


def invia_in_background(evento: dict, contesto: Optional[str] = None) -> bool:
    """Accoda la spedizione sul loop in corso. False se non c'e' un loop
    (chiamata sincrona fuori da FastAPI) o non siamo configurati."""
    if not configurato():
        return False
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        return False
    task = loop.create_task(_invia_e_registra(evento, contesto))
    _TASK.add(task)
    task.add_done_callback(_TASK.discard)
    return True


# ── la porta per gli agganci ────────────────────────────────────────────────

def evento_da_provenienza(nome: str, provenienza: Optional[dict], *, email: Optional[str] = None,
                          request=None, ip: Optional[str] = None, user_agent: Optional[str] = None,
                          custom_data: Optional[dict] = None, event_id: Optional[str] = None,
                          contesto: Optional[str] = None) -> bool:
    """L'unico ingresso usato dagli agganci (iscrizione, registrazioni,
    contatti, verifica). Legge `provenienza.tracciamento` (gia' pulito da
    services/provenienza.pulisci_tracciamento): senza consenso marketing
    o senza event_id NON parte nulla. Ritorna True se accodato."""
    try:
        if not configurato():
            return False
        prov = provenienza if isinstance(provenienza, dict) else {}
        tracc = prov.get("tracciamento") if isinstance(prov.get("tracciamento"), dict) else {}
        if tracc.get("marketing") is not True:
            return False
        eid = (event_id or tracc.get("event_id") or "").strip()
        if not _RE_EVENT_ID.match(eid):
            return False
        if request is not None:
            if not ip:
                try:
                    from core.rate_limiting import get_real_ip
                    ip = get_real_ip(request)
                except Exception:  # noqa: BLE001
                    ip = None
            if not user_agent:
                try:
                    user_agent = (request.headers.get("user-agent") or "")[:300] or None
                except Exception:  # noqa: BLE001
                    user_agent = None
        evento = costruisci_evento(
            nome, eid, email=email, fbp=tracc.get("fbp"), fbc=tracc.get("fbc"),
            ip=ip, user_agent=user_agent, url=prov.get("url"), custom_data=custom_data)
        return invia_in_background(evento, contesto or prov.get("porta") or prov.get("source"))
    except Exception:  # noqa: BLE001 — mai un'eccezione verso chi registra
        logger.warning("meta_capi: evento %s non accodato", nome, exc_info=True)
        return False


def id_derivato(prefisso: str, chiave: str) -> str:
    """Un event_id deterministico (es. la conferma di un iscritto): lo
    stesso gesto ripetuto produce lo stesso id, e Meta non lo conta due
    volte. Mai l'email in chiaro: un hash corto."""
    h = hashlib.sha256((chiave or "").strip().lower().encode("utf-8")).hexdigest()[:24]
    return f"{prefisso}_{h}"[:64]


# ── regia (MP4) ─────────────────────────────────────────────────────────────

async def riepilogo(ore: int = 24) -> dict:
    """Per i numeri della regia: eventi inviati/accettati/falliti nelle
    ultime `ore`, per nome. {configurato, test, ore, totale, accettati,
    falliti, per_nome: {Lead: {inviati, accettati}}}"""
    out = {"configurato": configurato(), "test": bool(test_event_code()), "ore": ore,
           "totale": 0, "accettati": 0, "falliti": 0, "per_nome": {}}
    try:
        from database import db
        da = datetime.now(timezone.utc) - timedelta(hours=ore)
        cur = db.tracciamento_eventi.aggregate([
            {"$match": {"created_at": {"$gte": da}}},
            {"$group": {"_id": {"nome": "$nome", "stato": "$stato"}, "n": {"$sum": 1}}},
        ])
        async for r in cur:
            nome = (r["_id"] or {}).get("nome") or "?"
            stato = (r["_id"] or {}).get("stato") or "?"
            n = int(r.get("n") or 0)
            voce = out["per_nome"].setdefault(nome, {"inviati": 0, "accettati": 0, "falliti": 0})
            voce["inviati"] += n
            out["totale"] += n
            if stato == "accettato":
                voce["accettati"] += n
                out["accettati"] += n
            elif stato == "fallito":
                voce["falliti"] += n
                out["falliti"] += n
    except Exception:  # noqa: BLE001
        logger.debug("meta_capi: riepilogo non disponibile", exc_info=True)
    return out
