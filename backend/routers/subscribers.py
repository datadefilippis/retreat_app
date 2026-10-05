"""BN2 — la lettera di Aurya: iscritti con double opt-in e preferenze.

docs/BLOG_NEWSLETTER_STRATEGIA_2026-07.md. Collection `aurya_subscribers`
(nome volutamente DIVERSO da `newsletter_subscriptions`, che e' il
modulo per-org degli operatori: due binari che non si toccano).

Ciclo di vita (status): pending → confirmed → unsubscribed (→ pending
se si re-iscrive). Il double opt-in e' la prova del consenso GDPR:
al subscribe parte l'email di conferma (Brevo) con un link firmato;
solo il click porta a confirmed. Lo STESSO token serve poi la pagina
preferenze e l'unsubscribe a un click (Art. 7(3): revocare facile
quanto dare).

Preferenze strutturate (si raccolgono ora, si usano al flip):
  topics[]        categorie editoriali (ARTICLE_CATEGORIES senza
                  'operatori': il B2B converte alla rete, non qui)
  format          all | practices (solo pratiche ed esercizi)
  retreat_alert   {enabled, scope: italy|regions, regions[]} —
                  DORMIENTE in fase rete: nessun invio finche' il
                  marketplace non apre (onesta' dichiarata nel form).

Risposte volutamente generiche sul subscribe: mai rivelare se una
email e' gia' iscritta (niente oracolo di enumerazione).
"""

import asyncio
import logging
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, EmailStr, Field

from core.marketing_unsubscribe_token import (TokenExpiredError,
                                              TokenInvalidError)
from core.subscriber_token import (decode_subscriber_token,
                                   generate_subscriber_token)
from auth import require_system_admin
from routers.auth import limiter

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Newsletter Aurya"])

SUBSCRIBER_FORMATS = ("all", "practices")
ALERT_SCOPES = ("italy", "regions")

# NW1 — interessi ESPERIENZIALI dell'iscritto (per le proposte di
# ritiri/esperienze): vocabolario suo, distinto dai topics editoriali
# del Magazine. "misto" = mi va bene un po' di tutto.
# founder 10/9 sera: quattordici vie, le stesse della landing /cerca-ritiro
# TX (10/9/2026): le vie SONO le categorie dei ritiri (retreat_taxonomy)
# piu' «misto»; «cerchi» e' diventata «femminile» (migrazione
# migrate_vie_femminile_v1) cosi' la via di chi cerca e la categoria di
# chi pubblica hanno la stessa chiave.
EXPERIENCE_INTERESTS = ("yoga", "meditazione", "breathwork", "suono", "reiki",
                        "costellazioni", "astrologia", "ayurveda", "tantra",
                        "detox", "cammini", "femminile", "crescita", "misto")
# NW1 — raggio di viaggio: vicino a casa o ovunque.
# near = nella mia zona; anywhere/italy = ovunque in Italia; abroad = anche
# all'estero (la landing di luglio mandava italy/abroad e venivano scartati)
TRAVEL_OPTIONS = ("near", "anywhere", "italy", "abroad")
# ET1 (2/10/2026) — la fascia d'eta', facoltativa, dal modulo di
# /cerca-ritiro: una rosa chiusa, tutto il resto si scarta. Mai l'eta'
# esatta, mai una fascia sotto i 18 (la regola 18+ resta su account e
# prenotazioni). Piano: docs/PIANO_ETA_CERCHIO_2026-10-02.md
ETA_FASCE = ("18-29", "30-44", "45-59", "60+")


def _eta_valida(raw) -> Optional[str]:
    v = str(raw or "").strip()
    return v if v in ETA_FASCE else None

# Le 20 regioni italiane: le zone dell'alert ritiri (stessa geografia
# della directory). Slug stabili minuscoli, label lato frontend.
ITALIAN_REGIONS = (
    "abruzzo", "basilicata", "calabria", "campania", "emilia-romagna",
    "friuli-venezia-giulia", "lazio", "liguria", "lombardia", "marche",
    "molise", "piemonte", "puglia", "sardegna", "sicilia", "toscana",
    "trentino-alto-adige", "umbria", "valle-d-aosta", "veneto",
)


def subscriber_topics() -> tuple:
    """Categorie iscrivibili: tutte le editoriali tranne 'operatori'."""
    from models.article import ARTICLE_CATEGORIES
    return tuple(k for k in ARTICLE_CATEGORIES if k != "operatori")


def _clean_topics(raw) -> list:
    valid = set(subscriber_topics())
    return [t for t in dict.fromkeys(raw or []) if t in valid][:20]


def _clean_interests(raw) -> list:
    valid = set(EXPERIENCE_INTERESTS)
    return [i for i in dict.fromkeys(raw or []) if i in valid][:10]


def _clean_alert(raw: Optional[dict]) -> dict:
    raw = raw or {}
    scope = raw.get("scope") if raw.get("scope") in ALERT_SCOPES else "italy"
    regions = [r for r in dict.fromkeys(raw.get("regions") or [])
               if r in ITALIAN_REGIONS][:20]
    return {"enabled": bool(raw.get("enabled")), "scope": scope,
            "regions": regions}


def _mask_email(email: str) -> str:
    local, _, domain = (email or "").partition("@")
    if len(local) <= 2:
        return f"{local[:1]}***@{domain}"
    return f"{local[0]}***{local[-1]}@{domain}"


class SubscribePayload(BaseModel):
    email: EmailStr
    name: Optional[str] = Field(default=None, max_length=120)
    language: Optional[str] = Field(default=None, max_length=5)
    # sorgente per attribuzione (blog_{categoria}, newsletter, gate...)
    source: Optional[str] = Field(default=None, max_length=60)
    topics: Optional[list[str]] = Field(default=None, max_length=20)
    format: Optional[str] = Field(default=None, max_length=20)
    retreat_alert: Optional[dict] = None
    # profilo facoltativo (dalla landing /newsletter col form pieno)
    city: Optional[str] = Field(default=None, max_length=120)
    travel: Optional[str] = Field(default=None, max_length=40)
    budget: Optional[str] = Field(default=None, max_length=40)
    eta: Optional[str] = Field(default=None, max_length=10)     # ET1 — fascia, facoltativa
    # NW1 — il flag «avvisami anche su esperienze e ritiri» e gli
    # interessi esperienziali del form espanso
    wants_experiences: Optional[bool] = None
    interests: Optional[list[str]] = Field(default=None, max_length=10)
    # BN3 — dal gate di una guida: dopo la conferma si torna li'
    return_to: Optional[str] = Field(default=None, max_length=200)
    consent: bool = False
    # 24/8 — il subscribe arriva da un CANCELLO di sblocco: il
    # gia'-confermato non riceve il magic link (la prova arriva
    # dalla chiamata unlock subito dopo)
    unlock_flow: Optional[bool] = False
    # Lotto B1/B2 (24/9/2026) — la provenienza scritta all'iscrizione
    # (non piu' derivata) e la versione del testo di consenso letto
    url: Optional[str] = Field(default=None, max_length=500)
    referrer: Optional[str] = Field(default=None, max_length=500)
    utm: Optional[dict] = None
    consenso_versione: Optional[str] = Field(default=None, max_length=30)
    # MP0 (5/10/2026) — identificativi di clic (fbclid, gclid) e il blocco di
    # tracciamento per Meta: {event_id, fbp, fbc, marketing}. Facoltativi:
    # un bundle vecchio non li manda e tutto resta com'e'.
    click_ids: Optional[dict] = None
    tracciamento: Optional[dict] = None


class TokenPayload(BaseModel):
    token: str = Field(max_length=2000)


class PreferencesPayload(BaseModel):
    token: str = Field(max_length=2000)
    topics: Optional[list[str]] = Field(default=None, max_length=20)
    format: Optional[str] = Field(default=None, max_length=20)
    retreat_alert: Optional[dict] = None
    # NW1 — l'iscritto puo' vedere e cambiare anche il suo profilo
    # esperienziale (prima si scriveva al subscribe e spariva)
    interests: Optional[list[str]] = Field(default=None, max_length=10)
    city: Optional[str] = Field(default=None, max_length=120)
    travel: Optional[str] = Field(default=None, max_length=40)
    # US (10/9/2026 notte) — il budget come ovunque (stesso blocco)
    budget: Optional[str] = Field(default=None, max_length=40)
    eta: Optional[str] = Field(default=None, max_length=10)     # ET1 — "" = togli


def _decode_or_http(token: str) -> str:
    try:
        return decode_subscriber_token(token)["email"]
    except TokenExpiredError:
        raise HTTPException(status_code=410, detail="link scaduto")
    except TokenInvalidError:
        raise HTTPException(status_code=401, detail="link non valido")


# SB3 (20/8) — i cancelli da cui si parte per iscriversi: il link di
# conferma deve saper riportare a CIASCUNO di loro, sbloccato. Prima la
# whitelist conosceva solo il Magazine: chi si iscriveva dalle
# meditazioni riceveva un link che NON tornava li' (il return_to veniva
# scartato in silenzio) e atterrava su una pagina qualunque.
_RETURN_TO_OK = ("/blog/", "/meditazioni", "/frequenze/")


def _safe_return_to(raw: Optional[str]) -> Optional[str]:
    """Solo path interni dei cancelli noti: il next del link di
    conferma non deve mai diventare un open redirect."""
    p = (raw or "").strip()
    if "//" in p or not p.startswith("/"):
        return None
    return p if any(p == r.rstrip("/") or p.startswith(r)
                    for r in _RETURN_TO_OK) else None


def _send_confirm_email(email: str, name: Optional[str], token: str,
                        return_to: Optional[str] = None) -> None:
    """Email di double opt-in, brandizzata col template comune. Best
    effort: un errore email non deve mai rompere il form."""
    try:
        from urllib.parse import quote

        from services.email_service import (_link_block, _wrap_template,
                                            send_email)
        from services.url_builder import build_public_url
        url = build_public_url(f"/newsletter/conferma/{token}")
        if return_to:
            url += f"?next={quote(return_to, safe='')}"
        saluto = f"Ciao {name.strip()}," if (name or "").strip() else "Ciao,"
        # CN2 (3/9/2026, piano IL CERCHIO) — il doppio opt-in VENDE, non
        # chiede: in prod 6 iscritti su 9 non confermavano mai, e l'email
        # parlava solo «della lettera». Ora dice cosa si sblocca col clic.
        html = _wrap_template(f"""
            <p>{saluto}</p>
            <p>un clic e sei nel <strong>Cerchio di Aurya</strong>. Da subito:</p>
            <ul>
                <li>le <strong>meditazioni riservate</strong>, gratis;</li>
                <li>i <strong>ritiri e le esperienze in anteprima</strong>, prima che siano pieni;</li>
                <li>la <strong>Lettera</strong>: una pratica raccontata bene e una persona della rete, quando vale la pena.</li>
            </ul>
            <p style="text-align: center;">
                <a href="{url}" class="btn">Entro nel Cerchio</a>
            </p>
            {_link_block(url)}
            <p>Se non ti sei iscritto tu, ignora questa email: senza
            conferma non riceverai nulla.</p>
        """)
        # FV3 (10/9 sera): «Benvenuto» in testa, la promessa e' la stessa
        # PE8 (24/9): oggetto diverso dal benvenuto che arriva al clic
        send_email(email, "Un clic per entrare nel Cerchio di Aurya",
                   html, bypass_gate=True)
    except Exception as exc:                # noqa: BLE001
        logger.warning("subscriber confirm email failed for %s: %s",
                       _mask_email(email), exc)


def _send_access_email(email: str, name: Optional[str], token: str,
                       return_to: Optional[str] = None) -> None:
    """Magic link per l'iscritto GIA' confermato che rimette la email
    (es. da un nuovo dispositivo, davanti a una guida riservata): il
    click ri-salva il token nel browser e sblocca tutte le guide.
    Stesso disegno del double opt-in, copy diverso. Best-effort."""
    try:
        from urllib.parse import quote

        from services.email_service import (_link_block, _wrap_template,
                                            send_email)
        from services.url_builder import build_public_url
        url = build_public_url(f"/newsletter/conferma/{token}")
        if return_to:
            url += f"?next={quote(return_to, safe='')}"
        saluto = f"Ciao {name.strip()}," if (name or "").strip() else "Ciao,"
        dove = ("e tornare alla guida che stavi leggendo"
                if return_to else "su questo dispositivo")
        html = _wrap_template(f"""
            <p>{saluto}</p>
            <p>sei gia' nel <strong>Cerchio di Aurya</strong> con questa
            email. Usa il bottone qui sotto per riaprire il tuo accesso
            {dove}: meditazioni riservate, guide e preferenze, senza doverti
            iscrivere di nuovo.</p>
            <p style="text-align: center;">
                <a href="{url}" class="btn">Riapri il mio accesso</a>
            </p>
            {_link_block(url)}
            <p>Se non hai richiesto tu questo link, ignora l'email: nessuno
            puo' usare il tuo accesso senza aprire questo messaggio.</p>
        """)
        send_email(email, "Il tuo accesso al Cerchio di Aurya",
                   html, bypass_gate=True)
    except Exception as exc:                # noqa: BLE001
        logger.warning("subscriber access email failed for %s: %s",
                       _mask_email(email), exc)


@router.post("/public/newsletter/subscribe", status_code=201)
@limiter.limit("10/minute")
async def subscribe(request: Request, payload: SubscribePayload):
    """Iscrizione (o aggiornamento) alla lettera. Upsert per email;
    nuovo o non confermato → parte l'email di double opt-in.

    Lotto E (24/9/2026) — la route e' un involucro sottile (rate limit)
    intorno a `iscrivi`: le porte interne (checkout, link «entra» delle
    email, account) chiamano quella, senza passare da HTTP."""
    return await iscrivi(payload, request)


def richiesta_sintetica(ip: Optional[str], user_agent: Optional[str]) -> Request:
    """Lotto E1 — una Request minima per chi chiama `iscrivi` senza
    averne una viva (il servizio ordini riceve solo ip e user-agent):
    `_consenso_da_payload` legge da qui l'ip e lo user-agent della prova."""
    headers = []
    if user_agent:
        headers.append((b"user-agent", str(user_agent)[:300].encode("utf-8", "ignore")))
    scope = {"type": "http", "method": "POST", "path": "/public/newsletter/subscribe",
             "query_string": b"", "headers": headers,
             "client": (ip, 0) if ip else None, "server": None, "scheme": "https"}
    return Request(scope)


async def iscrivi(payload: SubscribePayload, request: Request, *,
                  gia_verificato: bool = False) -> dict:
    """Il corpo dell'iscrizione al Cerchio, riusabile dalle porte interne.
    Stesso comportamento della route: upsert, registro del consenso,
    503 onesto se non si salva, benvenuto/conferma come sempre.

    `gia_verificato` (solo chiamate interne, E3): il gesto che iscrive e'
    GIA' la prova dell'indirizzo (clic nel link firmato di un'email), il
    chiamante conferma subito con `segna_verificato`, che manda il
    benvenuto: qui non parte nessuna email di conferma."""
    from database import db

    email = payload.email.lower().strip()
    now = datetime.now(timezone.utc)

    doc_set = {
        "name": (payload.name or "").strip()[:120] or None,
        "language": (payload.language or "")[:5] or None,
        "source": (payload.source or "").strip()[:60] or None,
        "consent": bool(payload.consent),
        "consent_at": now,
        "updated_at": now,
    }
    # Lotto B1 (24/9) — la provenienza si scrive ADESSO, a tre livelli,
    # con URL, referrer, UTM e dispositivo: `source` resta com'e' (le
    # sequenze e i test la leggono), questa e' la sua traduzione leggibile
    user_agent = (request.headers.get("user-agent") or "")[:300]
    doc_set["provenienza"] = _provenienza_da_payload(payload, user_agent)
    # Lotto B2 (24/9) — il registro del consenso: quale testo, quando, da
    # dove, con quale prova. Solo se la casella e' spuntata (senza, non
    # c'e' un consenso da registrare). `modalita` parte da «singolo» e
    # diventa «doppio» alla conferma (segna_verificato).
    consenso = _consenso_da_payload(payload, request, user_agent, now) if payload.consent else None
    if consenso:
        doc_set["consenso"] = consenso
    # preferenze: si scrivono solo se il form le manda (il compact del
    # blog manda solo l'email: non azzeriamo quelle esistenti)
    if payload.topics is not None:
        doc_set["preferences.topics"] = _clean_topics(payload.topics)
    if payload.format in SUBSCRIBER_FORMATS:
        doc_set["preferences.format"] = payload.format
    if payload.retreat_alert is not None:
        doc_set["preferences.retreat_alert"] = _clean_alert(payload.retreat_alert)
    # NW1 — il flag esperienze accende/spegne l'alert ritiri anche da
    # solo (il form progressivo non costruisce il dict retreat_alert)
    elif payload.wants_experiences is not None:
        doc_set["preferences.retreat_alert"] = _clean_alert(
            {"enabled": payload.wants_experiences})
    if payload.interests is not None:
        doc_set["profile.interests"] = _clean_interests(payload.interests)
    for field in ("city", "travel", "budget", "eta"):
        val = (getattr(payload, field) or "").strip()
        if val:
            if field == "travel" and val not in TRAVEL_OPTIONS:
                continue                     # NW1 — solo near/anywhere
            if field == "eta" and val not in ETA_FASCE:
                continue                     # ET1 — solo la rosa; vuoto = non scritto
            doc_set[f"profile.{field}"] = val[:120]

    try:
        existing = await db.aurya_subscribers.find_one(
            {"email": email}, {"_id": 0, "status": 1})
        if existing and existing.get("status") == "confirmed":
            # B2: chi e' gia' confermato ha gia' dato la prova doppia, un
            # nuovo consenso non la abbassa a «singolo»
            if consenso:
                doc_set["consenso"] = {**consenso, "modalita": "doppio"}
            await db.aurya_subscribers.update_one(
                {"email": email}, {"$set": doc_set})
            if consenso:
                await _audit_consenso_subscribe(email, doc_set["consenso"], payload.language)
            # Gia' confermato che rimette la email. DUE contesti diversi
            # (founder, 24/8): (a) un FORM della Lettera senza seguito →
            # magic link di accesso, come sempre; (b) un CANCELLO di
            # sblocco (guide, meditazioni: unlock_flow dal client) → la
            # prova arriva DALLA CHIAMATA UNLOCK un istante dopo, e
            # l'email era solo un costo con il copy sbagliato («parlava
            # di guide» sotto una meditazione). La risposta resta
            # identica: nessun oracolo di enumerazione.
            if not payload.unlock_flow:
                _send_access_email(email, payload.name,
                                   generate_subscriber_token(email),
                                   _safe_return_to(payload.return_to))
            return {"ok": True, "modalita": _modalita_risposta()}
        # nuovo, pending o unsubscribed (re-optin) → (ri)parte la conferma
        doc_set["status"] = "pending"
        set_on_insert = {"email": email, "created_at": now}
        if "preferences.topics" not in doc_set:
            set_on_insert["preferences.topics"] = []
        await db.aurya_subscribers.update_one(
            {"email": email},
            {"$set": doc_set, "$setOnInsert": set_on_insert,
             # FV8 (10/9/2026 sera) — chi si era cancellato e torna riparte
             # da zero: via le marcature delle sequenze (il benvenuto
             # arriva di nuovo alla conferma) e la traccia della
             # disiscrizione. Il promemoria 48h resta «una volta sola».
             "$unset": {"sequenza": "", "unsubscribed_at": "", "unsubscribed_by": ""}},
            upsert=True,
        )
    except Exception as exc:                # noqa: BLE001
        # NW1 — un errore di scrittura NON deve svanire in un finto ok:
        # l'iscrizione andrebbe persa in silenzio. Meglio un errore
        # onesto che il form puo' mostrare («riprova tra poco»).
        logger.error("subscriber save failed: %s", exc)
        raise HTTPException(status_code=503,
                            detail="Non riusciamo a salvarti ora, riprova")

    if consenso:
        await _audit_consenso_subscribe(email, consenso, payload.language)
    if gia_verificato:
        return {"ok": True}                  # E3: la conferma (e il benvenuto) arrivano dal chiamante
    # C4/B (24/9): con CERCHIO_SINGOLO_OPTIN acceso la prima email e' il
    # BENVENUTO (i suoi link sono verificanti: il clic conferma), non
    # l'email di conferma. Se il benvenuto non parte (gia' ricevuto in
    # passato) si ripiega sulla conferma di sempre. Spento: come oggi.
    # Consolidamento (24/9 sera): l'email parte in un TASK, non dentro la
    # richiesta. Brevo puo' metterci secondi (timeout 10s + 3 retry): il
    # form deve rispondere subito, l'email arriva un istante dopo. Il
    # riferimento al task resta in _TASK_EMAIL finche' non finisce (il
    # loop non lo raccoglie a meta').
    task = asyncio.create_task(_dopo_iscrizione(
        email, payload.name, _safe_return_to(payload.return_to)))
    _TASK_EMAIL.add(task)
    task.add_done_callback(_TASK_EMAIL.discard)
    return {"ok": True, "modalita": _modalita_risposta()}


_TASK_EMAIL: set = set()


async def _dopo_iscrizione(email: str, name: Optional[str], return_to: Optional[str]) -> None:
    """La prima email dell'iscritto, fuori dalla richiesta. Mai un'eccezione
    verso l'alto: il documento e' gia' salvato, l'email e' best-effort."""
    try:
        from services.sequenze import invia_subito_se_singolo, singolo_optin
        inviato = await invia_subito_se_singolo(email) if singolo_optin() else None
        if not inviato:
            await asyncio.to_thread(_send_confirm_email, email, name,
                                    generate_subscriber_token(email), return_to)
            await _registra_email_inviata(email, "conferma")   # il benvenuto lo segna gia' la sequenza
    except Exception as exc:                # noqa: BLE001
        logger.warning("email dopo iscrizione non partita per %s: %s", _mask_email(email), exc)


def _modalita_risposta() -> str:
    """Cosa dire nel «grazie»: dipende SOLO dall'interruttore, mai dallo
    stato dell'iscritto (la risposta resta identica per nuovo, pending e
    gia' confermato: nessun oracolo di enumerazione). «benvenuto» = la
    prima Lettera arriva subito e un suo clic conferma; «conferma» =
    l'email di conferma di sempre."""
    from services.sequenze import singolo_optin
    return "benvenuto" if singolo_optin() else "conferma"


def _provenienza_da_payload(payload: "SubscribePayload", user_agent: str) -> dict:
    """B1 — il blocco `provenienza` dell'iscritto, dalla fonte e da quello
    che il form ci manda in piu' (url, referrer, utm)."""
    from services.provenienza import (classifica, dispositivo, pulisci_click_ids,
                                      pulisci_tracciamento, pulisci_utm)
    url = (payload.url or "").strip()[:500] or None
    referrer = (payload.referrer or "").strip()[:500] or None
    utm = pulisci_utm(payload.utm)
    base = classifica(payload.source, None, url)
    if not base.get("porta") and utm and utm.get("source"):
        # senza ?porta= la porta e' l'utm_source (traffico esterno)
        base["porta"] = utm["source"][:20].lower()
    out = {**base, "url": url, "referrer": referrer, "utm": utm,
           "dispositivo": dispositivo(user_agent)}
    # MP0 — clic pubblicitari e blocco di tracciamento (solo se il client li manda)
    click = pulisci_click_ids(payload.click_ids)
    if click:
        out["click_ids"] = click
    tracc = pulisci_tracciamento(payload.tracciamento)
    if tracc:
        out["tracciamento"] = tracc
    return out


def _consenso_da_payload(payload: "SubscribePayload", request: Request,
                         user_agent: str, now: datetime) -> dict:
    """B2 — il registro del consenso: testo letto (per versione), quando,
    ip, user-agent, pagina e modalita' iniziale «singolo»."""
    from urllib.parse import urlsplit

    from core.rate_limiting import get_real_ip
    from services.testi_consenso import testo, versione_valida
    versione = versione_valida(payload.consenso_versione)
    pagina = None
    if payload.url:
        try:
            pagina = urlsplit(payload.url.strip()).path[:200] or None
        except ValueError:
            pagina = None
    try:
        ip = get_real_ip(request)
    except Exception:                        # noqa: BLE001
        ip = None
    return {"at": now, "testo": testo(versione), "versione": versione,
            "ip": ip, "user_agent": user_agent or None,
            "pagina": pagina or (payload.source or "").strip()[:60] or None,
            "modalita": "singolo"}


async def _audit_consenso_subscribe(email: str, consenso: dict, language: Optional[str]) -> None:
    """B2 — riga in consent_audit all'iscrizione (best effort)."""
    from services.verifica_email import registra_consenso_audit
    await registra_consenso_audit(
        email, "newsletter_subscribe",
        {"consenso": consenso, "language": language},
        ip=consenso.get("ip"), user_agent=consenso.get("user_agent"))


@router.post("/public/newsletter/confirm")
@limiter.limit("30/minute")
async def confirm(request: Request, payload: TokenPayload):
    """Il click nell'email: pending → confirmed (idempotente). Ritorna
    il token stesso come chiave della pagina preferenze."""
    from database import db

    from pymongo import ReturnDocument

    email = _decode_or_http(payload.token)
    now = datetime.now(timezone.utc)
    prima = await db.aurya_subscribers.find_one_and_update(
        {"email": email},
        {"$set": {"status": "confirmed", "confirmed_at": now,
                  "updated_at": now},
         "$setOnInsert": {"email": email, "created_at": now,
                          "consent": True, "consent_at": now,
                          "preferences.topics": []}},
        upsert=True, return_document=ReturnDocument.BEFORE,
        projection={"_id": 0, "status": 1},
    )
    from services.subscriber_brevo_sync import sync_subscriber_background
    sync_subscriber_background(email)     # BN6 — riflesso su Brevo
    # FV5 (10/9/2026 sera) — UN benvenuto, al momento della conferma, che
    # si adatta a come e da dove ci si e' iscritti (services/sequenze.py).
    # Solo alla PRIMA conferma: il clic ripetuto non rimanda niente.
    if not prima or prima.get("status") != "confirmed":
        try:
            from services.sequenze import invia_subito
            await invia_subito("cerchio", email)
        except Exception as exc:            # noqa: BLE001 — la conferma non si rompe per un'email
            logger.warning("benvenuto Cerchio non inviato a %s: %s", _mask_email(email), exc)
    # Lotto B3 (24/9) — il clic e' anche la prova che l'indirizzo e' suo:
    # verificato_at, consenso.modalita → doppio, email_verified sull'account
    # con la stessa email. Lo status e' gia' confirmed qui sopra, quindi
    # segna_verificato NON rimanda il benvenuto.
    try:
        from services.verifica_email import registra_consenso_audit, segna_verificato
        await segna_verificato(email, "conferma", "email di conferma")
        if not prima or prima.get("status") != "confirmed":
            await registra_consenso_audit(email, "newsletter_confirm")
    except Exception as exc:                # noqa: BLE001
        logger.warning("verifica alla conferma non annotata per %s: %s", _mask_email(email), exc)
    return {"ok": True, "status": "confirmed"}


@router.get("/public/newsletter/v/{token}")
@limiter.limit("30/minute")
async def verifica_e_vai(request: Request, token: str, to: Optional[str] = None):
    """Lotto B3 (24/9) — il link «verificante» delle email del Cerchio:
    un clic qualunque (Lettera, promemoria, benvenuto) dimostra che
    l'indirizzo e' suo, e porta dove voleva andare. Solo percorsi
    interni; un token rotto non blocca la lettura (si va lo stesso a
    `to`, senza annotare niente)."""
    from fastapi.responses import RedirectResponse

    from services.verifica_email import percorso_interno, segna_verificato
    dove = percorso_interno(to)
    try:
        email = decode_subscriber_token(token)["email"]
    except (TokenExpiredError, TokenInvalidError):
        email = None
    if email:
        try:
            await segna_verificato(email, "clic", dove)
        except Exception as exc:            # noqa: BLE001 — il clic porta comunque alla pagina
            logger.warning("verifica al clic fallita per %s: %s", _mask_email(email), exc)
    from services.url_builder import build_public_url
    return RedirectResponse(url=build_public_url(dove), status_code=302)


@router.get("/public/newsletter/entra/{token}")
@limiter.limit("30/minute")
async def entra_con_un_clic(request: Request, token: str,
                            to: Optional[str] = None, da: Optional[str] = None):
    """Lotto E3 (24/9/2026) — la riga «Vuoi la Lettera del Cerchio? Un
    clic» nelle email transazionali (conferma ordine, codice recensione).
    Il clic e' insieme il consenso (testo corrente, ip e user-agent della
    richiesta) e la prova che l'indirizzo e' suo: iscrive con la fonte
    dell'email (`da`: email-ordine | email-recensione), annota la
    verifica e porta a `to` (solo percorsi interni; senza, alla pagina
    «Sei nel Cerchio» che salva anche la prova nel browser). Un token
    rotto non iscrive nessuno: si va alla landing del Cerchio."""
    from fastapi.responses import RedirectResponse

    from services.porte_cerchio import SUPERFICI_EMAIL
    from services.testi_consenso import VERSIONE_CORRENTE
    from services.url_builder import build_public_url
    from services.verifica_email import percorso_interno, segna_verificato

    try:
        email = decode_subscriber_token(token)["email"]
    except (TokenExpiredError, TokenInvalidError):
        return RedirectResponse(url=build_public_url("/newsletter"), status_code=302)
    fonte = da if da in SUPERFICI_EMAIL else "email-ordine"
    dove = percorso_interno(to) if to else f"/newsletter/conferma/{token}"
    try:
        await iscrivi(SubscribePayload(
            email=email, source=fonte, consent=True, unlock_flow=True,
            consenso_versione=VERSIONE_CORRENTE, language="it",
            # la «pagina» del consenso e' l'email da cui si e' cliccato,
            # non l'URL col token (che nel registro non deve finire)
            url=build_public_url(f"/email/{fonte}")), request, gia_verificato=True)
        await segna_verificato(email, "clic", "entra")
    except Exception as exc:                # noqa: BLE001 — il clic porta comunque alla pagina
        logger.warning("entra con un clic fallito per %s: %s", _mask_email(email), exc)
    return RedirectResponse(url=build_public_url(dove), status_code=302)


class UnlockPayload(BaseModel):
    email: EmailStr


@router.post("/public/newsletter/unlock")
@limiter.limit("10/minute")
async def unlock_for_subscriber(request: Request, payload: UnlockPayload):
    """NL-septies (20/8, founder) — «sono gia' iscritto, perche' devo
    iscrivermi di nuovo?».

    Chi e' gia' iscritto CONFERMATO e apre un contenuto riservato da un
    altro browser (o mesi dopo, con la memoria del browser pulita) non
    deve rifare l'iscrizione: dichiara l'indirizzo e riprende il suo
    lasciapassare. Stesso patto gia' in uso per le meditazioni
    (/frequencies/catalog/unlock): il contenuto e' gratuito e
    l'iscrizione pure, quindi il fattore che conta e' non far ripetere
    un gesto gia' fatto.

    Email non iscritta o non confermata → 404 onesto: la pagina invita
    a iscriversi, che e' esattamente cio' che serve in quel caso.
    """
    from database import db

    email = (payload.email or "").strip().lower()
    doc = await db.aurya_subscribers.find_one(
        {"email": email}, {"_id": 0, "status": 1})
    if not doc or doc.get("status") != "confirmed":
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Questo indirizzo non risulta iscritto e confermato.")
    from core.subscriber_token import generate_subscriber_token
    return {"subscriber_token": generate_subscriber_token(email)}


@router.get("/admin/newsletter-stats")
async def newsletter_stats(
        current_user: dict = Depends(require_system_admin)):
    """BN6 — il polso della lettera per il system admin: iscritti per
    stato/fonte/tema, tasso di conferma, crescita 8 settimane."""
    from datetime import timedelta

    from database import db

    by_status: dict = {}
    async for row in db.aurya_subscribers.aggregate(
            [{"$group": {"_id": "$status", "n": {"$sum": 1}}}]):
        by_status[row["_id"] or "pending"] = row["n"]

    by_source = [
        {"source": r["_id"] or "(sconosciuta)", "n": r["n"]}
        async for r in db.aurya_subscribers.aggregate([
            {"$group": {"_id": "$source", "n": {"$sum": 1}}},
            {"$sort": {"n": -1}}, {"$limit": 15}])]

    by_topic = [
        {"topic": r["_id"], "n": r["n"]}
        async for r in db.aurya_subscribers.aggregate([
            {"$unwind": "$preferences.topics"},
            {"$group": {"_id": "$preferences.topics", "n": {"$sum": 1}}},
            {"$sort": {"n": -1}}])]

    now = datetime.now(timezone.utc)
    weekly = []
    for i in range(7, -1, -1):
        start = now - timedelta(weeks=i + 1)
        end = now - timedelta(weeks=i)
        n = await db.aurya_subscribers.count_documents(
            {"created_at": {"$gte": start, "$lt": end}})
        weekly.append({"week_start": start.date().isoformat(), "n": n})

    # Lotto B4 (24/9) — le ripartizioni cliccabili della pagina Iscritti:
    # budget, dove, canale (con etichetta), regione dell'avviso, verificati
    async def _conta(campo: str, unwind: bool = False, limite: int = 20) -> list:
        pipeline = [{"$unwind": f"${campo}"}] if unwind else []
        pipeline += [{"$group": {"_id": f"${campo}", "n": {"$sum": 1}}},
                     {"$sort": {"n": -1}}, {"$limit": limite}]
        return [{"valore": r["_id"], "n": r["n"]}
                async for r in db.aurya_subscribers.aggregate(pipeline) if r["_id"]]

    from services.provenienza import ETICHETTE
    by_budget = [{"budget": r["valore"], "n": r["n"]} for r in await _conta("profile.budget")]
    by_travel = [{"travel": r["valore"], "n": r["n"]} for r in await _conta("profile.travel")]
    # ET1 — la fascia d'eta', nell'ordine delle fasce (non per numero)
    conta_eta = {r["valore"]: r["n"] for r in await _conta("profile.eta")}
    by_eta = [{"eta": f, "n": conta_eta[f]} for f in ETA_FASCE if conta_eta.get(f)]
    by_canale =[{"canale": r["valore"], "label": ETICHETTE.get(r["valore"], r["valore"]), "n": r["n"]}
                 for r in await _conta("provenienza.canale")]
    by_regione = [{"regione": r["valore"], "n": r["n"]}
                  for r in await _conta("preferences.retreat_alert.regions", unwind=True, limite=25)]
    verificati = await db.aurya_subscribers.count_documents({"verificato_at": {"$exists": True}})

    total = sum(by_status.values())
    confirmed = by_status.get("confirmed", 0)
    return {
        "total": total,
        "by_status": by_status,
        "confirm_rate": round(confirmed / total, 3) if total else 0.0,
        "by_source": by_source,
        "by_topic": by_topic,
        "weekly_new": weekly,
        "by_budget": by_budget,
        "by_travel": by_travel,
        "by_eta": by_eta,
        "by_canale": by_canale,
        "by_regione": by_regione,
        "verificati": verificati,
    }


def _riga_iscritto(d: dict) -> dict:
    """SA-R (10/9/2026 sera) — TUTTO quello che sappiamo di una persona,
    per il pannello «Iscritti al Cerchio»: stato e date, porta e fonte,
    le vie, la citta', il raggio, il budget, l'avviso ritiri, i temi, le
    email delle sequenze ricevute."""
    from services.provenienza import classifica
    from services.sequenze import porta_cerchio
    prefs = d.get("preferences") or {}
    profile = d.get("profile") or {}
    # B4 (24/9) — provenienza a tre livelli (se il documento non l'ha
    # ancora, la si legge al volo dalla fonte: lo script la scrive), il
    # registro del consenso SENZA ip in lista, la prova di verifica, la
    # salute dell'indirizzo, quante email ha ricevuto, tag e note.
    provenienza = d.get("provenienza") or {**classifica(d.get("source")), "url": None,
                                           "referrer": None, "utm": None, "dispositivo": None}
    consenso = {k: v for k, v in (d.get("consenso") or {}).items() if k != "ip"} or None
    n_email, ultima, email_dettaglio = _conta_email(d)
    return {
        "email": d["email"],
        "name": d.get("name"),
        "status": d.get("status") or "pending",
        "source": d.get("source") or "(sconosciuta)",
        "porta": porta_cerchio(d.get("source")),
        "language": d.get("language"),
        "created_at": d.get("created_at"),
        "confirmed_at": d.get("confirmed_at"),
        "unsubscribed_at": d.get("unsubscribed_at"),
        "unsubscribed_by": d.get("unsubscribed_by"),
        "reminder_sent_at": d.get("reminder_sent_at"),
        "topics": _clean_topics(prefs.get("topics")),
        "format": prefs.get("format") if prefs.get("format") in SUBSCRIBER_FORMATS else "all",
        "retreat_alert": _clean_alert(prefs.get("retreat_alert")),
        "interests": _clean_interests(profile.get("interests")),
        "city": profile.get("city"),
        "travel": profile.get("travel") if profile.get("travel") in TRAVEL_OPTIONS else None,
        "budget": profile.get("budget"),
        "eta": _eta_valida(profile.get("eta")),          # ET1
        "sequenza": [k for k, v in (d.get("sequenza") or {}).items() if v and not str(v).startswith("saltato")],
        "provenienza": provenienza,
        "consenso": consenso,
        "verificato_at": d.get("verificato_at"),
        "verificato_da": d.get("verificato_da"),
        "email_status": d.get("email_status"),
        "n_email": n_email,
        "ultima_email_at": ultima,
        "email_dettaglio": email_dettaglio,
        "tag": list(d.get("tag") or []),
        "n_note": len(d.get("note_admin") or []),
    }


def _iso_o_str(v) -> str:
    return v.isoformat() if hasattr(v, "isoformat") else (str(v) if v else "")


def _conta_email(d: dict):
    """Le email AUTOMATICHE che il sistema ha mandato a questo indirizzo:
    la conferma (o il benvenuto) all'iscrizione, il promemoria, i passi
    delle sequenze inviati (non quelli «saltato»). Ritorna
    (quante, quando l'ultima, dettaglio). Non sappiamo se le hanno APERTE
    (Brevo non ce lo dice): sappiamo se hanno CLICCATO (verificato_at).

    Le conferme si registrano in `email_inviate` dal 24/9 sera; prima
    partivano sempre all'iscrizione senza lasciare traccia: per il
    pregresso se ne conta una, alla data di iscrizione (tranne chi e'
    entrato dal link a un clic dell'email d'ordine, che non la riceve)."""
    voci: list = []
    for k, v in (d.get("sequenza") or {}).items():
        if v and not str(v).startswith("saltato"):
            voci.append({"tipo": k, "at": str(v)})
    if d.get("reminder_sent_at"):
        voci.append({"tipo": "promemoria", "at": _iso_o_str(d["reminder_sent_at"])})
    inviate = [e for e in (d.get("email_inviate") or []) if isinstance(e, dict) and e.get("at")]
    for e in inviate:
        voci.append({"tipo": e.get("tipo") or "conferma", "at": _iso_o_str(e["at"])})
    if not inviate and (d.get("verificato_da") or {}).get("dettaglio") != "entra":
        voci.append({"tipo": "conferma", "at": _iso_o_str(d.get("created_at"))})
    voci.sort(key=lambda x: x["at"])
    when = [x["at"] for x in voci if x["at"]]
    return len(voci), (max(when) if when else None), voci


async def _registra_email_inviata(email: str, tipo: str) -> None:
    """Traccia sul documento un'email automatica mandata (conferma,
    reinvio): e' quello che l'admin conta nella colonna «Email inviate»."""
    try:
        # 25/9 sera: in prod usciva «name 'db' is not defined» a ogni
        # conferma — il modulo non importa `db` a livello di file
        from database import db
        await db.aurya_subscribers.update_one(
            {"email": email},
            {"$push": {"email_inviate": {"tipo": tipo, "at": datetime.now(timezone.utc)}}})
    except Exception as exc:                # noqa: BLE001
        logger.warning("email_inviate non registrata per %s: %s", _mask_email(email), exc)


async def _audit_iscritto(current_user: dict, action: str, email: str, metadata: dict) -> None:
    """La riga di audit (forma canonica di admin.py:3201, target
    «subscriber»). Ogni scrittura da admin sugli iscritti la chiama."""
    try:
        from database import audit_logs_collection
        from models.common import generate_id, utc_now
        now_dt = utc_now()
        await audit_logs_collection.insert_one({
            "id": generate_id(),
            "actor_user_id": current_user.get("user_id"),
            "actor_role": "system_admin",
            "organization_id": None,
            "action": action,
            "target_type": "subscriber",
            "target_id": email,
            "metadata": {**(metadata or {}), "attore": current_user.get("email")},
            "created_at": now_dt.isoformat(),
            "expire_at": now_dt,      # TTL 365 giorni, come gli altri
        })
    except Exception as exc:                # noqa: BLE001 — l'audit non rompe il gesto
        logger.warning("audit %s non scritto per %s: %s", action, _mask_email(email), exc)


_PORTE_MEDITAZIONI_RX = r"^(meditazioni|gate_meditazione|cancello:|frequenze|sound|guardia-fq|invito)"


def _data_filtro(raw: Optional[str], fine: bool = False) -> Optional[datetime]:
    """«2026-09-01» → datetime UTC (a fine giornata se `fine`)."""
    s = (raw or "").strip()[:25]
    if not s:
        return None
    try:
        dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    if fine and len(s) <= 10:
        dt = dt.replace(hour=23, minute=59, second=59)
    return dt


def _query_iscritti(status: Optional[str], source: Optional[str], q: Optional[str],
                    experiences: Optional[str], region: Optional[str], interest: Optional[str],
                    porta: Optional[str],
                    canale: Optional[str] = None, superficie: Optional[str] = None,
                    budget: Optional[str] = None, travel: Optional[str] = None,
                    dal: Optional[str] = None, al: Optional[str] = None,
                    verificato: Optional[str] = None, tag: Optional[str] = None,
                    eta: Optional[str] = None) -> dict:
    import re as _re
    query: dict = {}
    if _eta_valida(eta):                                   # ET1
        query["profile.eta"] = _eta_valida(eta)
    if status in ("pending", "confirmed", "unsubscribed"):
        query["status"] = status
    if source:
        query["source"] = source[:60]
    if q:
        query["email"] = {"$regex": _re.escape(q.strip()[:80]), "$options": "i"}
    # B4 (24/9) — i filtri nuovi: canale › superficie (dalla provenienza
    # scritta o migrata), budget, dove, periodo, verificato, tag
    if canale:
        query["provenienza.canale"] = canale.strip()[:30]
    if superficie:
        query["provenienza.superficie"] = superficie.strip()[:30]
    if budget:
        query["profile.budget"] = budget.strip()[:40]
    if travel in TRAVEL_OPTIONS:
        query["profile.travel"] = travel
    periodo: dict = {}
    if _data_filtro(dal):
        periodo["$gte"] = _data_filtro(dal)
    if _data_filtro(al, fine=True):
        periodo["$lte"] = _data_filtro(al, fine=True)
    if periodo:
        query["created_at"] = periodo
    if verificato == "si":
        query["verificato_at"] = {"$exists": True}
    elif verificato == "no":
        query["verificato_at"] = {"$exists": False}
    if tag:
        query["tag"] = tag.strip().lower()[:30]
    if experiences == "yes":
        query["preferences.retreat_alert.enabled"] = True
    elif experiences == "no":
        query["preferences.retreat_alert.enabled"] = {"$ne": True}
    if region in ITALIAN_REGIONS:
        query["preferences.retreat_alert.regions"] = region
    if interest in EXPERIENCE_INTERESTS:
        query["profile.interests"] = interest
    if porta == "meditazioni":
        query["source"] = {"$regex": _PORTE_MEDITAZIONI_RX, "$options": "i"}
    elif porta == "altro":
        query["$or"] = [{"source": {"$not": _re.compile(_PORTE_MEDITAZIONI_RX, _re.I)}}, {"source": None}]
    return query


_PROIEZIONE_ISCRITTO = {"_id": 0, "email": 1, "name": 1, "status": 1, "source": 1, "language": 1,
                        "created_at": 1, "confirmed_at": 1, "unsubscribed_at": 1, "unsubscribed_by": 1,
                        "reminder_sent_at": 1, "preferences": 1, "profile": 1, "sequenza": 1,
                        "email_inviate": 1,   # 24/9 sera: il registro delle automatiche mandate
                        # B4 (24/9)
                        "provenienza": 1, "consenso": 1, "verificato_at": 1, "verificato_da": 1,
                        "email_status": 1, "email_status_at": 1, "tag": 1, "note_admin": 1}


@router.get("/admin/subscribers")
async def list_subscribers(
        status: Optional[str] = None,
        source: Optional[str] = None,
        q: Optional[str] = None,
        experiences: Optional[str] = None,
        region: Optional[str] = None,
        interest: Optional[str] = None,
        porta: Optional[str] = None,
        canale: Optional[str] = None,
        superficie: Optional[str] = None,
        budget: Optional[str] = None,
        travel: Optional[str] = None,
        dal: Optional[str] = None,
        al: Optional[str] = None,
        verificato: Optional[str] = None,
        tag: Optional[str] = None,
        eta: Optional[str] = None,
        skip: int = 0,
        limit: int = 50,
        current_user: dict = Depends(require_system_admin)):
    """NW3 — la lista iscritti con FONTE, stato, preferenze e date.
    SA-R (10/9 sera): tutti i campi, i filtri per porta / regione / via /
    «vuole i ritiri», e le fonti distinte per il filtro.
    B4 (24/9): filtri canale › superficie, budget, dove, periodo,
    verificato, tag; la tassonomia dei canali con le etichette."""
    from database import db
    from services.provenienza import canali_per_admin
    query = _query_iscritti(status, source, q, experiences, region, interest, porta,
                            canale, superficie, budget, travel, dal, al, verificato, tag, eta)
    limit = max(1, min(int(limit or 50), 200))
    skip = max(0, int(skip or 0))
    total = await db.aurya_subscribers.count_documents(query)
    rows = [_riga_iscritto(d) async for d in (db.aurya_subscribers
                                               .find(query, _PROIEZIONE_ISCRITTO)
                                               .sort("created_at", -1).skip(skip).limit(limit))]
    fonti = sorted(f for f in await db.aurya_subscribers.distinct("source") if f)
    return {"total": total, "items": rows, "skip": skip, "limit": limit, "sources": fonti,
            "canali": canali_per_admin()}


@router.get("/admin/subscribers/export.csv")
async def export_subscribers(
        status: Optional[str] = None, source: Optional[str] = None, q: Optional[str] = None,
        experiences: Optional[str] = None, region: Optional[str] = None,
        interest: Optional[str] = None, porta: Optional[str] = None,
        canale: Optional[str] = None, superficie: Optional[str] = None,
        budget: Optional[str] = None, travel: Optional[str] = None,
        dal: Optional[str] = None, al: Optional[str] = None,
        verificato: Optional[str] = None, tag: Optional[str] = None,
        eta: Optional[str] = None,
        current_user: dict = Depends(require_system_admin)):
    """SA-R — lo stesso elenco, in CSV (max 5000 righe), con gli stessi filtri."""
    import csv, io
    from fastapi.responses import Response
    from database import db
    query = _query_iscritti(status, source, q, experiences, region, interest, porta,
                            canale, superficie, budget, travel, dal, al, verificato, tag, eta)
    buf = io.StringIO()
    w = csv.writer(buf, delimiter=";")
    w.writerow(["email", "nome", "stato", "porta", "fonte", "iscritto_il", "confermato_il", "disiscritto_il",
                "vie", "citta", "dove", "budget", "avviso_ritiri", "regioni", "temi", "email_ricevute",
                # B4 (24/9) — le colonne nuove in coda (le vecchie restano dove sono)
                "canale", "superficie", "porta_arrivo", "consenso_modalita", "consenso_versione",
                "verificato_at", "n_email",
                "eta"])                                    # ET1 (2/10) — in coda
    async for d in db.aurya_subscribers.find(query, _PROIEZIONE_ISCRITTO).sort("created_at", -1).limit(5000):
        r = _riga_iscritto(d)
        a = r["retreat_alert"]
        p = r["provenienza"] or {}
        c = r["consenso"] or {}
        w.writerow([r["email"], r["name"] or "", r["status"], r["porta"], r["source"],
                    r["created_at"] or "", r["confirmed_at"] or "", r["unsubscribed_at"] or "",
                    " ".join(r["interests"]), r["city"] or "", r["travel"] or "", r["budget"] or "",
                    "si" if a.get("enabled") else "no", " ".join(a.get("regions") or []),
                    " ".join(r["topics"]), " ".join(r["sequenza"]),
                    p.get("canale") or "", p.get("superficie") or "", p.get("porta") or "",
                    c.get("modalita") or "", c.get("versione") or "",
                    r["verificato_at"] or "", r["n_email"],
                    r["eta"] or ""])
    return Response(content="\ufeff" + buf.getvalue(), media_type="text/csv; charset=utf-8",
                    headers={"Content-Disposition": 'attachment; filename="iscritti-cerchio.csv"'})


class DisiscriviPayload(BaseModel):
    email: EmailStr


@router.post("/admin/subscribers/disiscrivi")
async def disiscrivi_da_admin(payload: DisiscriviPayload,
                              current_user: dict = Depends(require_system_admin)):
    """SA-R — la disiscrizione fatta da noi (richiesta a voce o via email):
    stesso effetto del link nelle email, con la traccia di chi l'ha fatta."""
    from database import db
    email = payload.email.lower().strip()
    now = datetime.now(timezone.utc)
    r = await db.aurya_subscribers.find_one_and_update(
        {"email": email},
        {"$set": {"status": "unsubscribed", "unsubscribed_at": now, "unsubscribed_by": "admin",
                  "updated_at": now}},
        projection=_PROIEZIONE_ISCRITTO, return_document=True)
    if not r:
        raise HTTPException(status_code=404, detail="Questo indirizzo non e' fra gli iscritti.")
    from services.subscriber_brevo_sync import sync_subscriber_background
    sync_subscriber_background(email)
    from services.verifica_email import registra_consenso_audit
    await registra_consenso_audit(email, "newsletter_unsubscribe", r)
    await _audit_iscritto(current_user, "SUBSCRIBER_UNSUBSCRIBED", email, {})
    return _riga_iscritto(r)


# ── B4 (24/9/2026) — le azioni dell'admin sugli iscritti ─────────────────────
# ATTENZIONE all'ordine: le rotte con percorso fisso (/export.csv,
# /disiscrivi, /reinvia-conferma, /conferma) stanno PRIMA di
# /admin/subscribers/{email}, altrimenti «conferma» diventa un'email.

class EmailPayload(BaseModel):
    email: EmailStr


class ConfermaPayload(BaseModel):
    email: EmailStr
    motivo: str = Field(min_length=3, max_length=300)


class MotivoPayload(BaseModel):
    motivo: str = Field(min_length=3, max_length=300)


class NotaPayload(BaseModel):
    testo: str = Field(min_length=1, max_length=2000)


class TagPayload(BaseModel):
    tag: list[str] = Field(default_factory=list, max_length=20)


class PreferenzeAdminPayload(BaseModel):
    """Gli stessi campi di PUT /public/newsletter/preferences, senza token."""
    topics: Optional[list[str]] = Field(default=None, max_length=20)
    format: Optional[str] = Field(default=None, max_length=20)
    retreat_alert: Optional[dict] = None
    interests: Optional[list[str]] = Field(default=None, max_length=10)
    city: Optional[str] = Field(default=None, max_length=120)
    travel: Optional[str] = Field(default=None, max_length=40)
    budget: Optional[str] = Field(default=None, max_length=40)
    eta: Optional[str] = Field(default=None, max_length=10)     # ET1 — "" = togli
    name: Optional[str] = Field(default=None, max_length=120)


def _set_eta(doc_set: dict, doc_unset: dict, raw: Optional[str]) -> None:
    """ET1 — fascia nella rosa → scritta; vuota → tolta; altro → ignorato."""
    if raw is None:
        return
    if _eta_valida(raw):
        doc_set["profile.eta"] = _eta_valida(raw)
    elif not str(raw).strip():
        doc_unset["profile.eta"] = ""


async def _iscritto_o_404(email: str) -> dict:
    from database import db
    d = await db.aurya_subscribers.find_one({"email": email}, _PROIEZIONE_ISCRITTO)
    if not d:
        raise HTTPException(status_code=404, detail="Questo indirizzo non e' fra gli iscritti.")
    return d


@router.post("/admin/subscribers/reinvia-conferma")
async def reinvia_conferma(payload: EmailPayload,
                           current_user: dict = Depends(require_system_admin)):
    """Rimanda l'email di doppio opt-in a chi e' ancora in attesa. A chi e'
    confermato non serve; a chi si e' cancellato non si scrive."""
    email = payload.email.lower().strip()
    d = await _iscritto_o_404(email)
    if d.get("status") != "pending":
        raise HTTPException(status_code=409, detail=f"L'iscritto e' «{d.get('status')}»: niente da riconfermare.")
    _send_confirm_email(email, d.get("name"), generate_subscriber_token(email))
    await _registra_email_inviata(email, "conferma (reinvio)")
    await _audit_iscritto(current_user, "SUBSCRIBER_CONFIRM_RESENT", email, {})
    return {"ok": True, "email": email}


@router.post("/admin/subscribers/conferma")
async def conferma_da_admin(payload: ConfermaPayload,
                            current_user: dict = Depends(require_system_admin)):
    """La conferma a mano (iscrizione a voce, via WhatsApp): con motivo,
    passa da segna_verificato(admin) → status confirmed, modalita
    «manuale», benvenuto come alla conferma dal link."""
    email = payload.email.lower().strip()
    d = await _iscritto_o_404(email)
    from services.verifica_email import segna_verificato
    esito = await segna_verificato(email, "admin", payload.motivo)
    await _audit_iscritto(current_user, "SUBSCRIBER_ADMIN_CONFIRMED", email,
                          {"motivo": payload.motivo, "stato_prima": d.get("status"),
                           "confermato_ora": esito.get("confermato_ora")})
    return {"ok": True, **esito, "item": _riga_iscritto(await _iscritto_o_404(email))}


@router.get("/admin/subscribers/{email}")
async def scheda_iscritto(email: str, current_user: dict = Depends(require_system_admin)):
    """La scheda completa: i sei blocchi (identita', consenso col suo ip,
    provenienza, interessi, ritiri, ciclo di vita), i legami (account,
    lead, organizzazione), le note, e la cronologia in ordine di tempo."""
    from database import db
    email = email.lower().strip()
    d = await _iscritto_o_404(email)
    riga = _riga_iscritto(d)
    riga["consenso"] = d.get("consenso")          # nella scheda l'ip si vede
    riga["note"] = list(d.get("note_admin") or [])
    riga["email_status_at"] = d.get("email_status_at")
    riga["sequenza_dettaglio"] = d.get("sequenza") or {}

    # legami: lo stesso essere umano nelle altre liste
    utente = await db.users.find_one({"email": email}, {"_id": 0, "id": 1, "role": 1,
                                                        "organization_id": 1, "email_verified": 1})
    lead = await db.prelaunch_leads.find_one({"email": email}, {"_id": 0, "type": 1, "created_at": 1,
                                                                "phone": 1, "activity": 1})
    riga["legami"] = {
        "account": utente,
        "lead": lead,
        "organizzazione_id": (utente or {}).get("organization_id") if (utente or {}).get("role") == "admin" else None,
    }

    def _iso(v):
        return v.isoformat() if hasattr(v, "isoformat") else (str(v) if v else None)

    cron = []
    if d.get("created_at"):
        cron.append({"at": _iso(d["created_at"]), "tipo": "iscritto",
                     "testo": f"Iscritto da {riga['provenienza'].get('canale')} › {riga['provenienza'].get('superficie')}"})
    c = d.get("consenso") or {}
    if c.get("at"):
        cron.append({"at": _iso(c["at"]), "tipo": "consenso",
                     "testo": f"Consenso {c.get('versione')} ({c.get('modalita')})"})
    if d.get("reminder_sent_at"):
        cron.append({"at": _iso(d["reminder_sent_at"]), "tipo": "promemoria", "testo": "Promemoria di conferma"})
    for e in (d.get("email_inviate") or []):
        if isinstance(e, dict) and e.get("at"):
            cron.append({"at": _iso(e["at"]), "tipo": "email", "testo": f"Email inviata: {e.get('tipo') or 'conferma'}"})
    if d.get("confirmed_at"):
        cron.append({"at": _iso(d["confirmed_at"]), "tipo": "confermato", "testo": "Confermato"})
    if d.get("verificato_at"):
        vd = d.get("verificato_da") or {}
        cron.append({"at": _iso(d["verificato_at"]), "tipo": "verificato",
                     "testo": f"Indirizzo verificato ({vd.get('tipo') or '?'})", "dettaglio": vd.get("dettaglio")})
    for passo, v in (d.get("sequenza") or {}).items():
        sv = str(v or "")
        saltato = sv.startswith("saltato")
        cron.append({"at": sv.replace("saltato ", "", 1) if saltato else sv,
                     "tipo": "sequenza", "testo": f"{'Saltato' if saltato else 'Inviato'}: {passo}"})
    if d.get("unsubscribed_at"):
        cron.append({"at": _iso(d["unsubscribed_at"]), "tipo": "disiscritto",
                     "testo": f"Disiscritto ({d.get('unsubscribed_by') or 'link'})"})
    if d.get("email_status_at"):
        cron.append({"at": _iso(d["email_status_at"]), "tipo": "email_status",
                     "testo": f"Indirizzo: {d.get('email_status')}"})
    for n in (d.get("note_admin") or []):
        cron.append({"at": _iso(n.get("at")), "tipo": "nota", "testo": n.get("testo"), "dettaglio": n.get("da")})
    try:
        async for a in db.audit_logs.find({"target_type": "subscriber", "target_id": email},
                                          {"_id": 0, "action": 1, "created_at": 1, "metadata": 1}).sort("created_at", -1).limit(50):
            cron.append({"at": _iso(a.get("created_at")), "tipo": "audit", "testo": a.get("action"),
                         "dettaglio": (a.get("metadata") or {}).get("motivo") or (a.get("metadata") or {}).get("attore")})
        async for a in db.consent_audit.find({"customer_email": email, "document_type": "aurya_newsletter"},
                                             {"_id": 0, "source": 1, "accepted_at": 1, "version_tag": 1}).sort("accepted_at", -1).limit(50):
            cron.append({"at": _iso(a.get("accepted_at")), "tipo": "consent_audit",
                         "testo": f"{a.get('source')} · {a.get('version_tag')}"})
    except Exception as exc:                # noqa: BLE001
        logger.warning("cronologia audit non letta per %s: %s", _mask_email(email), exc)
    riga["cronologia"] = sorted(cron, key=lambda x: x.get("at") or "")
    return riga


@router.patch("/admin/subscribers/{email}/preferenze")
async def preferenze_da_admin(email: str, payload: PreferenzeAdminPayload,
                              current_user: dict = Depends(require_system_admin)):
    """Le preferenze cambiate da noi (stessi campi della pagina pubblica)."""
    from database import db
    email = email.lower().strip()
    prima = await _iscritto_o_404(email)
    now = datetime.now(timezone.utc)
    doc_set: dict = {"updated_at": now}
    if payload.topics is not None:
        doc_set["preferences.topics"] = _clean_topics(payload.topics)
    if payload.format in SUBSCRIBER_FORMATS:
        doc_set["preferences.format"] = payload.format
    if payload.retreat_alert is not None:
        doc_set["preferences.retreat_alert"] = _clean_alert(payload.retreat_alert)
    if payload.interests is not None:
        doc_set["profile.interests"] = _clean_interests(payload.interests)
    if payload.city is not None:
        doc_set["profile.city"] = payload.city.strip()[:120]
    if payload.travel is not None and payload.travel in TRAVEL_OPTIONS:
        doc_set["profile.travel"] = payload.travel
    if payload.budget is not None:
        doc_set["profile.budget"] = payload.budget.strip()[:40]
    if payload.name is not None:
        doc_set["name"] = payload.name.strip()[:120] or None
    doc_unset: dict = {}
    _set_eta(doc_set, doc_unset, payload.eta)              # ET1
    await db.aurya_subscribers.update_one(
        {"email": email}, {"$set": doc_set, **({"$unset": doc_unset} if doc_unset else {})})
    from services.subscriber_brevo_sync import sync_subscriber_background
    sync_subscriber_background(email)
    riga_prima = _riga_iscritto(prima)
    dopo = _riga_iscritto(await _iscritto_o_404(email))
    campi = [k for k in ("topics", "format", "retreat_alert", "interests", "city", "travel", "budget", "eta", "name")
             if riga_prima.get(k) != dopo.get(k)]
    await _audit_iscritto(current_user, "SUBSCRIBER_PREFERENCES_EDITED", email,
                          {"campi": campi,
                           "prima": {k: str(riga_prima.get(k))[:120] for k in campi},
                           "dopo": {k: str(dopo.get(k))[:120] for k in campi}})
    return dopo


@router.post("/admin/subscribers/{email}/note")
async def nota_da_admin(email: str, payload: NotaPayload,
                        current_user: dict = Depends(require_system_admin)):
    """Una nota del founder sull'iscritto (note_admin[])."""
    from database import db
    from models.common import generate_id
    email = email.lower().strip()
    await _iscritto_o_404(email)
    now = datetime.now(timezone.utc)
    nota = {"id": generate_id(), "testo": payload.testo.strip()[:2000], "at": now,
            "da": current_user.get("email")}
    await db.aurya_subscribers.update_one({"email": email},
                                          {"$push": {"note_admin": nota}, "$set": {"updated_at": now}})
    await _audit_iscritto(current_user, "SUBSCRIBER_NOTE_ADDED", email, {"nota_id": nota["id"]})
    return {"ok": True, "nota": nota, "item": _riga_iscritto(await _iscritto_o_404(email))}


def _pulisci_tag(raw) -> list:
    out = []
    for t in raw or []:
        s = str(t or "").strip().lower()[:30]
        if s and s not in out:
            out.append(s)
    return out[:20]


@router.put("/admin/subscribers/{email}/tag")
async def tag_da_admin(email: str, payload: TagPayload,
                       current_user: dict = Depends(require_system_admin)):
    """I tag dell'iscritto, sostituiti in blocco (minuscoli, senza doppioni)."""
    from database import db
    email = email.lower().strip()
    prima = await _iscritto_o_404(email)
    tag = _pulisci_tag(payload.tag)
    await db.aurya_subscribers.update_one({"email": email},
                                          {"$set": {"tag": tag, "updated_at": datetime.now(timezone.utc)}})
    await _audit_iscritto(current_user, "SUBSCRIBER_TAGS_SET", email,
                          {"prima": list(prima.get("tag") or []), "dopo": tag})
    return {"ok": True, "tag": tag, "item": _riga_iscritto(await _iscritto_o_404(email))}


@router.delete("/admin/subscribers/{email}")
async def elimina_iscritto(email: str, payload: MotivoPayload,
                           current_user: dict = Depends(require_system_admin)):
    """Cancellazione GDPR su richiesta (art. 17): il documento sparisce,
    Brevo lo mette in blacklist, resta la riga di audit col motivo."""
    from database import db
    email = email.lower().strip()
    d = await _iscritto_o_404(email)
    res = await db.aurya_subscribers.delete_one({"email": email})
    from services.subscriber_brevo_sync import blacklist_subscriber_background
    blacklist_subscriber_background(email)
    creato = d.get("created_at")
    await _audit_iscritto(current_user, "SUBSCRIBER_DELETED", email,
                          {"motivo": payload.motivo, "stato": d.get("status"),
                           "iscritto_il": creato.isoformat() if hasattr(creato, "isoformat") else None,
                           "cancellati": res.deleted_count})
    return {"ok": True, "email": email, "cancellati": res.deleted_count}


@router.get("/public/newsletter/preferences/{token}")
async def get_preferences(token: str):
    from database import db

    email = _decode_or_http(token)
    doc = await db.aurya_subscribers.find_one(
        {"email": email},
        {"_id": 0, "status": 1, "preferences": 1, "profile": 1}) or {}
    prefs = doc.get("preferences") or {}
    profile = doc.get("profile") or {}
    return {
        "email_masked": _mask_email(email),
        "status": doc.get("status") or "pending",
        "topics": _clean_topics(prefs.get("topics")),
        "format": (prefs.get("format")
                   if prefs.get("format") in SUBSCRIBER_FORMATS else "all"),
        "retreat_alert": _clean_alert(prefs.get("retreat_alert")),
        # NW1 — profilo esperienziale, visibile e modificabile
        "interests": _clean_interests(profile.get("interests")),
        "city": profile.get("city") or "",
        "travel": (profile.get("travel")
                   if profile.get("travel") in TRAVEL_OPTIONS else ""),
        "budget": profile.get("budget") or "",
        "eta": _eta_valida(profile.get("eta")) or "",        # ET1
        "available_topics": list(subscriber_topics()),
        "available_regions": list(ITALIAN_REGIONS),
        "available_interests": list(EXPERIENCE_INTERESTS),
    }


@router.put("/public/newsletter/preferences")
@limiter.limit("30/minute")
async def update_preferences(request: Request, payload: PreferencesPayload):
    from database import db

    email = _decode_or_http(payload.token)
    now = datetime.now(timezone.utc)
    doc_set = {"updated_at": now}
    if payload.topics is not None:
        doc_set["preferences.topics"] = _clean_topics(payload.topics)
    if payload.format in SUBSCRIBER_FORMATS:
        doc_set["preferences.format"] = payload.format
    if payload.retreat_alert is not None:
        doc_set["preferences.retreat_alert"] = _clean_alert(payload.retreat_alert)
    if payload.interests is not None:
        doc_set["profile.interests"] = _clean_interests(payload.interests)
    if payload.city is not None:
        doc_set["profile.city"] = payload.city.strip()[:120]
    if payload.travel is not None and payload.travel in TRAVEL_OPTIONS:
        doc_set["profile.travel"] = payload.travel
    if payload.budget is not None:
        doc_set["profile.budget"] = payload.budget.strip()[:40]
    doc_unset: dict = {}
    _set_eta(doc_set, doc_unset, payload.eta)              # ET1
    await db.aurya_subscribers.update_one(
        {"email": email}, {"$set": doc_set, **({"$unset": doc_unset} if doc_unset else {})})
    from services.subscriber_brevo_sync import sync_subscriber_background
    sync_subscriber_background(email)     # BN6 — attributi aggiornati
    return {"ok": True}


@router.post("/public/newsletter/unsubscribe")
@limiter.limit("30/minute")
async def unsubscribe(request: Request, payload: TokenPayload):
    """Un click, mai discussioni (GDPR Art. 7(3)). Idempotente."""
    from database import db

    email = _decode_or_http(payload.token)
    now = datetime.now(timezone.utc)
    await db.aurya_subscribers.update_one(
        {"email": email},
        {"$set": {"status": "unsubscribed", "unsubscribed_at": now,
                  "updated_at": now},
         "$setOnInsert": {"email": email, "created_at": now}},
        upsert=True,
    )
    from services.subscriber_brevo_sync import sync_subscriber_background
    sync_subscriber_background(email)     # BN6 — blacklist su Brevo
    # B2 — la revoca lascia la sua riga nel registro, come l'accettazione
    from services.verifica_email import registra_consenso_audit
    await registra_consenso_audit(email, "newsletter_unsubscribe")
    return {"ok": True, "status": "unsubscribed"}
