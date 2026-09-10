"""
LE SEQUENZE (FV2, 10/9/2026) — un motore solo per due pubblici.

Nato da services/sequenza_operatore.py (RB8: g2/g7/g14/g30, un pubblico
solo, testi dentro il motore). Il founder ha chiesto: «per operatori
creiamo anche un'email se uno si e' registrato ma non ha creato ancora
il profilo, dopo 5, 10, 15 giorni; e tutte le email ben scritte, non
casuali». E il Cerchio, dopo la conferma, non riceveva niente.

Il disegno:
- i PASSI sono dati (PASSI[pubblico]): nome, giorno d'inizio e fine
  della finestra (o «evento» quando non dipende dal giorno), una
  condizione sullo stato, un template in services/email_sequenze.py;
- ogni documento (organizzazione o iscritto) ha un orologio (created_at
  per l'operatore, confirmed_at per il Cerchio) e le marcature
  `sequenza.<passo>`; si marca PRIMA di inviare, mai due volte;
- un passo parte SOLO nella sua finestra: chi si e' registrato mesi fa
  non riceve tre email in un colpo. Le finestre dello stesso ramo non
  si sovrappongono; rami diversi (pagina online / non online) hanno
  condizioni esclusive;
- un template che restituisce None fa saltare il passo (marcato
  «saltato»): niente email vuote «non ci sono ritiri»;
- una sola email per documento a ogni giro; DRY RUN e ANTEPRIMA usano
  lo stesso codice che invia.

Operatore (organizations, orologio created_at):
  g2   giorno 2-4   → ADMIN_EMAIL: «scrivigli su WhatsApp»
  profilo_online (evento, entro 60 giorni) → il link, Telegram, l'IBAN
  np5  5-9, np10 10-14, np15 15-21 → «pagina non ancora online»
  r14  14-20 (online, nessun ritiro) → il primo ritiro
  g30  30-36 → «come va», intervista, fondatori finche' aperti
Cerchio (aurya_subscribers confermati, orologio confirmed_at):
  c1 1-2 «Sei dentro» · c3 3-9 una meditazione · c10 10-16 ritiri o
  professionisti in zona (salta se vuoto) · c30 30-36 «come va»
"""
import logging
import re
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Callable, Dict, List, Optional, Tuple

from services import email_sequenze as T

logger = logging.getLogger(__name__)

_MAX_PER_TICK = 100
EVENTO_ENTRO_GIORNI = 60      # un evento (pagina online) vale solo per chi e' arrivato da poco
_ADMIN = "admin"


@dataclass(frozen=True)
class Passo:
    nome: str
    giorno: Optional[int]                 # None = evento (non dipende dal giorno)
    fine: Optional[int]                   # fine finestra, esclusa
    condizione: str                       # chiave in CONDIZIONI
    template: Callable[[dict], Optional[Tuple[str, str]]]
    a: str = "utente"                     # "utente" | "admin"
    equivalenti: Tuple[str, ...] = ()     # marcature vecchie che valgono come questa

    def nella_finestra(self, giorni: int) -> bool:
        if self.giorno is None:
            return 0 <= giorni < EVENTO_ENTRO_GIORNI
        return self.giorno <= giorni < (self.fine or self.giorno + 7)


CONDIZIONI: Dict[str, Callable[[dict], bool]] = {
    "sempre": lambda s: True,
    "online": lambda s: bool(s.get("online")),
    "non_online": lambda s: not s.get("online"),
    "online_senza_ritiro": lambda s: bool(s.get("online")) and not s.get("ritiro"),
}

PASSI: Dict[str, Tuple[Passo, ...]] = {
    "operatore": (
        Passo("g2", 2, 5, "sempre", T.op_g2_admin, a=_ADMIN),
        Passo("profilo_online", None, None, "online", T.op_profilo_online),
        Passo("np5", 5, 10, "non_online", T.op_np5, equivalenti=("g7",)),
        Passo("np10", 10, 15, "non_online", T.op_np10, equivalenti=("g7",)),
        Passo("np15", 15, 22, "non_online", T.op_np15),
        Passo("r14", 14, 21, "online_senza_ritiro", T.op_r14, equivalenti=("g14",)),
        Passo("g30", 30, 37, "sempre", T.op_g30),
    ),
    "cerchio": (
        Passo("c1", 1, 3, "sempre", T.c1_sei_dentro),
        Passo("c3", 3, 10, "sempre", T.c3_meditazione),
        Passo("c10", 10, 17, "sempre", T.c10_vicino),
        Passo("c30", 30, 37, "sempre", T.c30_come_va),
    ),
}

PUBBLICI = tuple(PASSI)


def passi_dovuti(pubblico: str, giorni: int, stato: dict, marcature: dict) -> List[Passo]:
    """I passi che oggi toccherebbero a questo documento, in ordine.
    Il motore ne manda UNO per giro."""
    out = []
    for p in PASSI[pubblico]:
        if not p.nella_finestra(giorni):
            continue
        if marcature.get(p.nome) or any(marcature.get(e) for e in p.equivalenti):
            continue
        if not CONDIZIONI[p.condizione](stato):
            continue
        out.append(p)
    return out


def passo_dovuto(giorni: int) -> Optional[str]:
    """Compatibilita' con RB8 (solo i passi a giorno, ramo «sempre»)."""
    for p in PASSI["operatore"]:
        if p.giorno is not None and p.condizione == "sempre" and p.nella_finestra(giorni):
            return p.nome
    return None


# ─────────────────────────────────────────────────────────────────────────────
# Orologi e stati
# ─────────────────────────────────────────────────────────────────────────────

def _data(v: Any) -> Optional[datetime]:
    if isinstance(v, datetime):
        return v if v.tzinfo else v.replace(tzinfo=timezone.utc)
    if isinstance(v, str) and v:
        try:
            d = datetime.fromisoformat(v.replace("Z", "+00:00"))
            return d if d.tzinfo else d.replace(tzinfo=timezone.utc)
        except ValueError:
            return None
    return None


async def stato_operatore(org: dict) -> Dict[str, Any]:
    """Gli stessi check di onboarding-status (organizations.py), in breve."""
    from database import products_collection, stores_collection
    org_id = org["id"]
    pp = org.get("public_profile") or {}
    profilo_ok = bool(pp.get("bio")) and bool(
        pp.get("cover_url") or pp.get("instagram") or pp.get("website") or pp.get("facebook"))
    servizio = await products_collection.find_one(
        {"organization_id": org_id, "item_type": "service", "is_published": True}, {"_id": 1})
    ritiro = await products_collection.find_one(
        {"organization_id": org_id, "item_type": "event_ticket", "is_published": True}, {"_id": 1})
    slug = org.get("public_slug")
    if not slug:
        store = await stores_collection.find_one(
            {"organization_id": org_id, "is_active": True}, {"_id": 0, "slug": 1})
        slug = (store or {}).get("slug")
    return {"online": bool(slug) and profilo_ok and bool(servizio),
            "ritiro": bool(ritiro), "slug": slug, "iban": bool(org.get("bank_iban"))}


async def _destinatario_org(org_id: str) -> Tuple[Optional[str], str]:
    from database import users_collection
    u = await users_collection.find_one(
        {"organization_id": org_id, "role": "admin", "is_active": {"$ne": False}},
        {"_id": 0, "email": 1, "name": 1}, sort=[("created_at", 1)])
    if not u or not u.get("email"):
        return None, ""
    return u["email"], (u.get("name") or "").strip()


async def _fondatori() -> Optional[dict]:
    try:
        from routers.fondatori import conteggio
        return await conteggio()
    except Exception:  # noqa: BLE001
        return None


_PROIEZIONE_ORG = {"_id": 0, "id": 1, "name": 1, "created_at": 1, "public_profile": 1,
                   "public_slug": 1, "sequenza": 1, "bank_iban": 1}
_FILTRO_ORG = {"is_sample": {"$ne": True}, "is_active": {"$ne": False},
               "legacy_commerce": {"$ne": True}, "deactivated_at": None}


async def contesto_operatore(org: dict, email: str, nome: str, fondatori: Optional[dict]) -> dict:
    stato = await stato_operatore(org)
    return {"nome": nome, "email": email, "org": org, "stato": stato, "fondatori": fondatori}


# ── Il Cerchio ───────────────────────────────────────────────────────────────

def _slug(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", (s or "").lower()).strip("-")


async def _meditazione_del_momento() -> Optional[dict]:
    """L'ultima meditazione pubblicata e visibile: titolo e link."""
    from database import frequency_tracks_collection
    # la piu' ascoltata fra quelle con un titolo vero; «Senza titolo» in
    # un'email non si manda
    t = await frequency_tracks_collection.find_one(
        {"status": "published", "visibility": {"$ne": "private"},
         "title": {"$nin": [None, "", "Senza titolo"]}},
        {"_id": 0, "slug": 1, "public_slug": 1, "title": 1, "name": 1},
        sort=[("plays_total", -1), ("published_at", -1)])
    if not t:
        return None
    slug = t.get("public_slug") or t.get("slug")
    if not slug:
        return None
    return {"titolo": t.get("title") or t.get("name") or "Una meditazione",
            "url": f"{T.APP_URL}/frequenze/{slug}"}


async def _ritiri_per(sub: dict) -> Tuple[List[dict], bool]:
    """I ritiri futuri pubblicati (online o su richiesta, mai campioni),
    filtrati sulla zona dell'iscritto quando ne ha una e viaggia vicino.
    Ritorna (ritiri, in_zona)."""
    from database import (event_occurrences_collection, organizations_collection,
                          products_collection)
    now_iso = datetime.now(timezone.utc).isoformat()
    occs = await event_occurrences_collection.find(
        {"status": "published", "start_at": {"$gte": now_iso[:16]}},
        {"_id": 0, "product_id": 1, "slug": 1, "start_at": 1, "city": 1, "region": 1},
    ).sort("start_at", 1).to_list(300)
    if not occs:
        return [], False
    prods = {p["id"]: p async for p in products_collection.find(
        {"id": {"$in": [o["product_id"] for o in occs]}, "is_active": True, "is_published": True,
         "item_type": "event_ticket", "transaction_mode": {"$in": ["direct", "request"]}},
        {"_id": 0, "id": 1, "name": 1, "organization_id": 1})}
    orgs = {o["id"]: o async for o in organizations_collection.find(
        {"id": {"$in": list({p["organization_id"] for p in prods.values()})},
         "is_sample": {"$ne": True}, "is_active": {"$ne": False}},
        {"_id": 0, "id": 1, "name": 1, "public_slug": 1})}
    tutti = []
    for o in occs:
        p = prods.get(o["product_id"])
        org = p and orgs.get(p["organization_id"])
        if not p or not org or not org.get("public_slug"):
            continue
        tutti.append({"title": p.get("name"), "start_at": o.get("start_at"), "city": o.get("city"),
                      "region": o.get("region"), "org_name": org.get("name") or "",
                      "url": f"/e/{org['public_slug']}/{o.get('slug')}"})
    profilo = sub.get("profile") or {}
    prefs = sub.get("preferences") or {}
    alert = prefs.get("retreat_alert") or {}
    regioni = {_slug(r) for r in (alert.get("regions") or [])}
    citta = _slug(profilo.get("city") or "")
    ovunque = (profilo.get("travel") in ("anywhere", "italy", "abroad")) or alert.get("scope") == "italy"
    if regioni or citta:
        in_zona = [r for r in tutti
                   if (_slug(r.get("region") or "") in regioni) or (citta and _slug(r.get("city") or "") == citta)]
        if in_zona:
            return in_zona, True
    if ovunque or not (regioni or citta):
        return tutti, False
    return [], False


async def _professionisti_a(citta: str) -> List[dict]:
    """I professionisti della rete con la pagina online nella citta'."""
    from database import organizations_collection
    if not (citta or "").strip():
        return []
    rx = {"$regex": f"^{re.escape(citta.strip())}$", "$options": "i"}
    out = []
    async for o in organizations_collection.find(
            {"public_profile.city": rx, "public_slug": {"$nin": [None, ""]},
             "store_settings.is_storefront_published": True,
             "is_sample": {"$ne": True}, "is_active": {"$ne": False}, "deactivated_at": None,
             "exclude_from_listings": {"$ne": True}},
            {"_id": 0, "name": 1, "public_slug": 1, "public_profile.display_name": 1,
             "public_profile.disciplines": 1}).limit(5):
        pp = o.get("public_profile") or {}
        disc = ", ".join(str(d) for d in (pp.get("disciplines") or [])[:2])
        out.append({"nome": pp.get("display_name") or o.get("name"), "slug": o["public_slug"],
                    "discipline": disc})
    return out


async def contesto_cerchio(sub: dict, passo: Optional[str] = None) -> dict:
    """Il contesto dell'iscritto; le ricerche costose solo per il passo
    che le usa (None = tutte, per l'anteprima)."""
    from core.subscriber_token import generate_subscriber_token   # lo stesso token di /newsletter/preferenze
    profilo = sub.get("profile") or {}
    email = sub["email"]
    ctx = {"nome": (sub.get("name") or "").strip(), "email": email, "sub": sub,
           "token": generate_subscriber_token(email),
           "citta": (profilo.get("city") or "").strip(),
           "interessi": list(profilo.get("interests") or []),
           "meditazione": None, "ritiri": [], "ritiri_in_zona": False, "professionisti": []}
    if passo in (None, "c3"):
        ctx["meditazione"] = await _meditazione_del_momento()
    if passo in (None, "c10"):
        ctx["ritiri"], ctx["ritiri_in_zona"] = await _ritiri_per(sub)
        if not ctx["ritiri"]:
            ctx["professionisti"] = await _professionisti_a(ctx["citta"])
    return ctx


_PROIEZIONE_SUB = {"_id": 0, "email": 1, "name": 1, "confirmed_at": 1, "profile": 1,
                   "preferences": 1, "sequenza": 1}
_FILTRO_SUB = {"status": "confirmed", "consent": True}


# ─────────────────────────────────────────────────────────────────────────────
# Invio
# ─────────────────────────────────────────────────────────────────────────────

def _manda(passo: Passo, ctx: dict, dry_run: bool = False) -> Optional[bool]:
    """True inviata, False errore, None saltata (niente da dire)."""
    from services.email_service import ADMIN_EMAIL, _wrap_template, send_email
    try:
        reso = passo.template(ctx)
    except Exception as exc:  # noqa: BLE001
        logger.warning("sequenze: %s non renderizzato per %s: %s", passo.nome, ctx.get("email", "")[:2] + "***", exc)
        return False
    if not reso:
        return None
    oggetto, corpo = reso
    if dry_run:
        return True
    try:
        if passo.a == _ADMIN:
            return bool(send_email(ADMIN_EMAIL, oggetto, _wrap_template(corpo, "it"), bypass_gate=True))
        return bool(send_email(ctx["email"], oggetto,
                               _wrap_template(corpo, "it", reply_to=ADMIN_EMAIL),
                               reply_to=ADMIN_EMAIL, bypass_gate=True))
    except Exception as exc:  # noqa: BLE001
        logger.warning("sequenze: %s non inviato a %s: %s", passo.nome, ctx.get("email", "")[:2] + "***", exc)
        return False


async def _marca(collezione, chiave: dict, passo: str, valore: str) -> bool:
    r = await collezione.update_one({**chiave, f"sequenza.{passo}": {"$exists": False}},
                                    {"$set": {f"sequenza.{passo}": valore}})
    return r.modified_count == 1


async def _giro_operatore(now: datetime, dry_run: bool, result: dict) -> None:
    from database import organizations_collection
    piu_vecchia = now - timedelta(days=EVENTO_ENTRO_GIORNI)
    fondatori = await _fondatori()
    n = 0
    async for org in organizations_collection.find(_FILTRO_ORG, _PROIEZIONE_ORG).limit(_MAX_PER_TICK * 5):
        creato = _data(org.get("created_at"))
        if not creato or creato < piu_vecchia:
            continue
        giorni = (now - creato).days
        marcature = org.get("sequenza") or {}
        # la finestra prima, lo stato (due query) solo se serve
        se_finestra = [p for p in PASSI["operatore"] if p.nella_finestra(giorni)
                       and not marcature.get(p.nome) and not any(marcature.get(e) for e in p.equivalenti)]
        if not se_finestra:
            continue
        stato = await stato_operatore(org)
        dovuti = passi_dovuti("operatore", giorni, stato, marcature)
        if not dovuti:
            continue
        passo = dovuti[0]
        result["candidati"].append(("operatore", org["id"], passo.nome))
        if dry_run or n >= _MAX_PER_TICK:
            continue
        email, nome = await _destinatario_org(org["id"])
        if not email:
            continue
        if not await _marca(organizations_collection, {"id": org["id"]}, passo.nome, now.isoformat()):
            continue
        n += 1
        try:
            ctx = {"nome": nome, "email": email, "org": org, "stato": stato, "fondatori": fondatori}
            esito = _manda(passo, ctx)
        except Exception as exc:  # noqa: BLE001 — un documento rotto non ferma il giro
            logger.error("sequenze: operatore %s passo %s: %s", org["id"], passo.nome, exc)
            esito = False
        if esito is None:
            await organizations_collection.update_one(
                {"id": org["id"]}, {"$set": {f"sequenza.{passo.nome}": f"saltato {now.isoformat()}"}})
            result["saltati"] += 1
        elif esito:
            result["inviati"] += 1
        else:
            result["errori"] += 1


async def _giro_cerchio(now: datetime, dry_run: bool, result: dict) -> None:
    from database import db
    piu_vecchia = now - timedelta(days=PASSI["cerchio"][-1].fine or 40)
    n = 0
    async for sub in db.aurya_subscribers.find(
            {**_FILTRO_SUB, "$or": [{"confirmed_at": {"$gte": piu_vecchia}},
                                    {"confirmed_at": {"$gte": piu_vecchia.isoformat()}}]},
            _PROIEZIONE_SUB).limit(_MAX_PER_TICK * 5):
        confermato = _data(sub.get("confirmed_at"))
        if not confermato or not sub.get("email"):
            continue
        giorni = (now - confermato).days
        dovuti = passi_dovuti("cerchio", giorni, {}, sub.get("sequenza") or {})
        if not dovuti:
            continue
        passo = dovuti[0]
        result["candidati"].append(("cerchio", sub["email"], passo.nome))
        if dry_run or n >= _MAX_PER_TICK:
            continue
        if not await _marca(db.aurya_subscribers, {"email": sub["email"]}, passo.nome, now.isoformat()):
            continue
        n += 1
        try:
            ctx = await contesto_cerchio(sub, passo.nome)
            esito = _manda(passo, ctx)
        except Exception as exc:  # noqa: BLE001 — un documento rotto non ferma il giro
            logger.error("sequenze: cerchio %s passo %s: %s", sub["email"][:2] + "***", passo.nome, exc)
            esito = False
        if esito is None:
            await db.aurya_subscribers.update_one(
                {"email": sub["email"]}, {"$set": {f"sequenza.{passo.nome}": f"saltato {now.isoformat()}"}})
            result["saltati"] += 1
        elif esito:
            result["inviati"] += 1
        else:
            result["errori"] += 1


async def run_sequenze_sweep(now: datetime = None, dry_run: bool = False,
                             pubblici: Tuple[str, ...] = PUBBLICI) -> Dict[str, Any]:
    """Un giro su tutti i pubblici: per ogni documento nella finestra di
    un passo, quel passo (uno solo)."""
    now = now or datetime.now(timezone.utc)
    result: Dict[str, Any] = {"candidati": [], "inviati": 0, "saltati": 0, "errori": 0}
    if "operatore" in pubblici:
        await _giro_operatore(now, dry_run, result)
    if "cerchio" in pubblici:
        await _giro_cerchio(now, dry_run, result)
    if result["candidati"]:
        logger.info("sequenze: %s", {**result, "candidati": len(result["candidati"])})
    return result


# ─────────────────────────────────────────────────────────────────────────────
# Anteprima (pannello) e conteggi (numeri del lunedi')
# ─────────────────────────────────────────────────────────────────────────────

def elenco_passi() -> Dict[str, List[dict]]:
    out: Dict[str, List[dict]] = {}
    for pubblico, passi in PASSI.items():
        out[pubblico] = [{"nome": p.nome, "giorno": p.giorno, "fine": p.fine,
                          "condizione": p.condizione, "a": p.a,
                          "titolo": (p.template.__doc__ or "").strip().split("\n")[0]}
                         for p in passi]
    return out


def _passo(pubblico: str, nome: str) -> Optional[Passo]:
    return next((p for p in PASSI.get(pubblico, ()) if p.nome == nome), None)


_FITTIZIO_ORG = {"id": "anteprima", "name": "Studio Sole", "public_profile": {"bio": "x", "cover_url": "x"},
                 "public_slug": "studio-sole", "bank_iban": ""}
_FITTIZIO_SUB = {"email": "anteprima@esempio.it", "name": "Giulia",
                 "profile": {"city": "Bari", "interests": ["yoga", "suono"], "travel": "near"},
                 "preferences": {"retreat_alert": {"enabled": True, "regions": ["puglia"]}}}


async def anteprima(pubblico: str, nome: str, email: Optional[str] = None) -> Dict[str, Any]:
    """L'email di un passo per un destinatario vero (per email) o, se
    non c'e', per uno fittizio. Non manda e non marca niente."""
    from services.email_service import ADMIN_EMAIL, _wrap_template
    passo = _passo(pubblico, nome)
    if not passo:
        raise ValueError("passo sconosciuto")
    trovato = False
    if pubblico == "operatore":
        org, dest, nome_dest = None, None, ""
        if email:
            from database import organizations_collection, users_collection
            u = await users_collection.find_one({"email": email.lower().strip()},
                                                {"_id": 0, "organization_id": 1, "name": 1, "email": 1})
            if u and u.get("organization_id"):
                org = await organizations_collection.find_one({"id": u["organization_id"]}, _PROIEZIONE_ORG)
                dest, nome_dest = u["email"], (u.get("name") or "").strip()
        if org:
            trovato = True
            stato = await stato_operatore(org)
        else:
            org, dest, nome_dest = _FITTIZIO_ORG, email or "giulia@esempio.it", "Giulia Serra"
            stato = {"online": passo.condizione != "non_online", "ritiro": False,
                     "slug": "studio-sole", "iban": False}
        ctx = {"nome": nome_dest, "email": dest, "org": org, "stato": stato, "fondatori": await _fondatori()}
    else:
        sub = None
        if email:
            from database import db
            sub = await db.aurya_subscribers.find_one({"email": email.lower().strip()}, _PROIEZIONE_SUB)
        if sub:
            trovato = True
        else:
            sub = {**_FITTIZIO_SUB, "email": email or _FITTIZIO_SUB["email"]}
        ctx = await contesto_cerchio(sub, None)
    reso = passo.template(ctx)
    if not reso:
        return {"pubblico": pubblico, "passo": nome, "trovato": trovato, "destinatario": ctx["email"],
                "oggetto": None, "html": None, "nota": "Per questo destinatario il passo si salta: niente da dire."}
    oggetto, corpo = reso
    html = (_wrap_template(corpo, "it") if passo.a == _ADMIN
            else _wrap_template(corpo, "it", reply_to=ADMIN_EMAIL))
    return {"pubblico": pubblico, "passo": nome, "trovato": trovato,
            "destinatario": ADMIN_EMAIL if passo.a == _ADMIN else ctx["email"],
            "oggetto": oggetto, "html": html}


async def conta_invii(dal: datetime) -> Dict[str, Dict[str, int]]:
    """Quante email di ogni passo sono partite dal giorno dato (le
    marcature sono ISO: il confronto per stringa regge)."""
    from database import db, organizations_collection
    dal_iso = dal.isoformat()
    out: Dict[str, Dict[str, int]] = {}
    for pubblico, coll in (("operatore", organizations_collection), ("cerchio", db.aurya_subscribers)):
        out[pubblico] = {}
        for p in PASSI[pubblico]:
            out[pubblico][p.nome] = await coll.count_documents(
                {f"sequenza.{p.nome}": {"$gte": dal_iso, "$lt": "3"}})   # ISO comincia per «2»: esclude «saltato …»
    return out
