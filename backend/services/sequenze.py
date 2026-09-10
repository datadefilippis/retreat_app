"""
LE SEQUENZE (FV2, 10/9/2026) — un motore solo per due pubblici.

Nato da services/sequenza_operatore.py (RB8: g2/g7/g14/g30, un pubblico
solo, testi dentro il motore). Il founder ha chiesto: «per operatori
creiamo anche un'email se uno si e' registrato ma non ha creato ancora
il profilo, dopo 5, 10, 15 giorni; e tutte le email ben scritte, non
casuali». Poi (FV5, stessa sera): via il «come va» a 30 giorni; per il
Cerchio UNA sola email, il benvenuto, che si adatta a come e da dove ci
si e' iscritti, e parte al momento della conferma.

Il disegno:
- i PASSI sono dati (PASSI[pubblico]): nome, giorno d'inizio e fine
  della finestra (o «evento» quando non dipende dal giorno), una
  condizione sullo stato, un template in services/email_sequenze.py;
- ogni documento (organizzazione o iscritto) ha un orologio (created_at
  per l'operatore, confirmed_at per il Cerchio) e le marcature
  `sequenza.<passo>`; si marca PRIMA di inviare, mai due volte;
- un passo parte SOLO nella sua finestra: chi si e' registrato mesi fa
  non riceve tre email in un colpo. Le finestre dello stesso ramo non
  si sovrappongono; rami diversi hanno condizioni esclusive;
- un template che restituisce None fa saltare il passo (marcato
  «saltato»); una sola email per documento a ogni giro; DRY RUN e
  ANTEPRIMA usano lo stesso codice che invia.

Operatore (organizations, orologio created_at):
  g2   giorno 2-4   → a noi: aggiungilo al gruppo Telegram, scrivigli
  profilo_online (evento, entro 60 giorni) → il link, Telegram, l'IBAN
  np5  5-9, np10 10-14, np15 15-21 → «pagina non ancora online»
  r14  14-20 (online, nessun ritiro) → il primo ritiro
Cerchio (aurya_subscribers confermati, orologio confirmed_at):
  benvenuto, in tre varianti esclusive, subito alla conferma (il giro
  ogni 6h e' la rete di sicurezza, finestra 0-1 giorni):
  ritiri (vuole i ritiri) · meditazioni (dalle meditazioni, senza
  preferenze) · altro (dalle altre porte, senza preferenze)
"""
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Callable, Dict, List, Optional, Tuple

from services import email_sequenze as T

logger = logging.getLogger(__name__)

_MAX_PER_TICK = 100
EVENTO_ENTRO_GIORNI = 60      # un evento (pagina online) vale solo per chi e' arrivato da poco
_ADMIN = "admin"

# Le porte del Cerchio in cui NON si chiede niente sui ritiri (solo
# l'email): da qui non si parla di ritiri finche' l'iscritto non li chiede
PORTE_MEDITAZIONI = ("meditazioni", "gate_meditazione", "cancello:", "frequenze",
                     "sound", "guardia-fq", "invito")


@dataclass(frozen=True)
class Passo:
    nome: str
    giorno: Optional[int]                 # None = evento (non dipende dal giorno)
    fine: Optional[int]                   # fine finestra, esclusa
    condizione: str                       # chiave in CONDIZIONI
    template: Callable[[dict], Optional[Tuple[str, str]]]
    a: str = "utente"                     # "utente" | "admin"
    equivalenti: Tuple[str, ...] = ()     # marcature (vecchie o sorelle) che valgono come questa

    def nella_finestra(self, giorni: int) -> bool:
        if self.giorno is None:
            return 0 <= giorni < EVENTO_ENTRO_GIORNI
        return self.giorno <= giorni < (self.fine or self.giorno + 7)


CONDIZIONI: Dict[str, Callable[[dict], bool]] = {
    "sempre": lambda s: True,
    "online": lambda s: bool(s.get("online")),
    "non_online": lambda s: not s.get("online"),
    "online_senza_ritiro": lambda s: bool(s.get("online")) and not s.get("ritiro"),
    "cerchio_ritiri": lambda s: bool(s.get("vuole_ritiri")),
    "cerchio_meditazioni": lambda s: not s.get("vuole_ritiri") and s.get("porta") == "meditazioni",
    "cerchio_altro": lambda s: not s.get("vuole_ritiri") and s.get("porta") != "meditazioni",
}

_BENVENUTI = ("benvenuto_ritiri", "benvenuto_meditazioni", "benvenuto_altro")

PASSI: Dict[str, Tuple[Passo, ...]] = {
    "operatore": (
        Passo("g2", 2, 5, "sempre", T.op_g2_admin, a=_ADMIN),
        Passo("profilo_online", None, None, "online", T.op_profilo_online),
        Passo("np5", 5, 10, "non_online", T.op_np5, equivalenti=("g7",)),
        Passo("np10", 10, 15, "non_online", T.op_np10, equivalenti=("g7",)),
        Passo("np15", 15, 22, "non_online", T.op_np15),
        Passo("r14", 14, 21, "online_senza_ritiro", T.op_r14, equivalenti=("g14",)),
    ),
    "cerchio": tuple(
        Passo(nome, 0, 2, cond, tpl, equivalenti=tuple(b for b in _BENVENUTI if b != nome) + ("c1",))
        for nome, cond, tpl in (
            ("benvenuto_ritiri", "cerchio_ritiri", T.benvenuto_cerchio_ritiri),
            ("benvenuto_meditazioni", "cerchio_meditazioni", T.benvenuto_cerchio_meditazioni),
            ("benvenuto_altro", "cerchio_altro", T.benvenuto_cerchio_generico),
        )
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


# ── Il Cerchio ───────────────────────────────────────────────────────────────

def porta_cerchio(source: Optional[str]) -> str:
    """Da dove si e' iscritto: 'meditazioni' (solo email, mai chiesto
    dei ritiri) oppure 'altro'."""
    s = (source or "").lower()
    return "meditazioni" if any(s.startswith(p) for p in PORTE_MEDITAZIONI) else "altro"


def stato_cerchio(sub: dict) -> Dict[str, Any]:
    """Come si e' iscritto: ha DETTO qualcosa sui ritiri (le vie, o
    l'avviso acceso in un form che lo chiedeva)? Da quale porta?"""
    profilo = sub.get("profile") or {}
    alert = (sub.get("preferences") or {}).get("retreat_alert") or {}
    interessi = [i for i in (profilo.get("interests") or []) if i]
    return {"vuole_ritiri": bool(alert.get("enabled")) or bool(interessi),
            "porta": porta_cerchio(sub.get("source"))}


def contesto_cerchio(sub: dict) -> dict:
    from core.subscriber_token import generate_subscriber_token   # lo stesso token di /newsletter/preferenze
    profilo = sub.get("profile") or {}
    email = sub["email"]
    stato = stato_cerchio(sub)
    return {"nome": (sub.get("name") or "").strip(), "email": email,
            "token": generate_subscriber_token(email),
            "citta": (profilo.get("city") or "").strip(),
            "interessi": list(profilo.get("interests") or []),
            "travel": profilo.get("travel") or "",
            "porta": stato["porta"], "vuole_ritiri": stato["vuole_ritiri"]}


_PROIEZIONE_SUB = {"_id": 0, "email": 1, "name": 1, "confirmed_at": 1, "profile": 1,
                   "preferences": 1, "sequenza": 1, "source": 1}
_FILTRO_SUB = {"status": "confirmed", "consent": True}


# ─────────────────────────────────────────────────────────────────────────────
# Invio
# ─────────────────────────────────────────────────────────────────────────────

def _manda(passo: Passo, ctx: dict, dry_run: bool = False) -> Optional[bool]:
    """True inviata, False errore, None saltata (niente da dire)."""
    from services.email_service import CASELLA_AURYA, _wrap_template, send_email
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
            # FV6 — «a noi» = la casella di Aurya
            return bool(send_email(CASELLA_AURYA, oggetto, _wrap_template(corpo, "it"), bypass_gate=True))
        risposte = T.risposte_a()
        return bool(send_email(ctx["email"], oggetto,
                               _wrap_template(corpo, "it", reply_to=risposte),
                               reply_to=risposte, bypass_gate=True))
    except Exception as exc:  # noqa: BLE001
        logger.warning("sequenze: %s non inviato a %s: %s", passo.nome, ctx.get("email", "")[:2] + "***", exc)
        return False


async def _marca(collezione, chiave: dict, passo: str, valore: str) -> bool:
    r = await collezione.update_one({**chiave, f"sequenza.{passo}": {"$exists": False}},
                                    {"$set": {f"sequenza.{passo}": valore}})
    return r.modified_count == 1


async def _esegui(collezione, chiave: dict, passo: Passo, costruisci_ctx, now: datetime, result: dict) -> None:
    """Marca, costruisce il contesto, manda, conta. Un documento rotto
    non ferma il giro."""
    if not await _marca(collezione, chiave, passo.nome, now.isoformat()):
        return
    try:
        ctx = await costruisci_ctx() if callable(costruisci_ctx) else costruisci_ctx
        esito = _manda(passo, ctx)
    except Exception as exc:  # noqa: BLE001
        logger.error("sequenze: %s passo %s: %s", chiave, passo.nome, exc)
        esito = False
    if esito is None:
        await collezione.update_one(chiave, {"$set": {f"sequenza.{passo.nome}": f"saltato {now.isoformat()}"}})
        result["saltati"] += 1
    elif esito:
        result["inviati"] += 1
    else:
        result["errori"] += 1


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
        n += 1
        ctx = {"nome": nome, "email": email, "org": org, "stato": stato, "fondatori": fondatori}
        await _esegui(organizations_collection, {"id": org["id"]}, passo, ctx, now, result)


async def _giro_cerchio(now: datetime, dry_run: bool, result: dict) -> None:
    """La rete di sicurezza del benvenuto: chi e' confermato da meno di
    due giorni e non l'ha ricevuto (es. errore al momento della conferma)."""
    from database import db
    piu_vecchia = now - timedelta(days=PASSI["cerchio"][-1].fine or 2)
    n = 0
    async for sub in db.aurya_subscribers.find(
            {**_FILTRO_SUB, "$or": [{"confirmed_at": {"$gte": piu_vecchia}},
                                    {"confirmed_at": {"$gte": piu_vecchia.isoformat()}}]},
            _PROIEZIONE_SUB).limit(_MAX_PER_TICK * 5):
        confermato = _data(sub.get("confirmed_at"))
        if not confermato or not sub.get("email"):
            continue
        giorni = (now - confermato).days
        dovuti = passi_dovuti("cerchio", giorni, stato_cerchio(sub), sub.get("sequenza") or {})
        if not dovuti:
            continue
        passo = dovuti[0]
        result["candidati"].append(("cerchio", sub["email"], passo.nome))
        if dry_run or n >= _MAX_PER_TICK:
            continue
        n += 1
        await _esegui(db.aurya_subscribers, {"email": sub["email"]}, passo,
                      contesto_cerchio(sub), now, result)


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


async def invia_subito(pubblico: str, email: str) -> Optional[str]:
    """Il passo dovuto ADESSO a un documento (giorno zero), fuori dal
    giro: il benvenuto del Cerchio al momento della conferma. Ritorna il
    nome del passo mandato, o None."""
    if pubblico != "cerchio":
        raise ValueError("solo il Cerchio ha un passo immediato")
    from database import db
    sub = await db.aurya_subscribers.find_one({"email": email, **_FILTRO_SUB}, _PROIEZIONE_SUB)
    if not sub:
        return None
    dovuti = passi_dovuti("cerchio", 0, stato_cerchio(sub), sub.get("sequenza") or {})
    if not dovuti:
        return None
    now = datetime.now(timezone.utc)
    result: Dict[str, Any] = {"inviati": 0, "saltati": 0, "errori": 0}
    await _esegui(db.aurya_subscribers, {"email": email}, dovuti[0], contesto_cerchio(sub), now, result)
    return dovuti[0].nome


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
_FITTIZI_SUB = {
    "benvenuto_ritiri": {"email": "anteprima@esempio.it", "name": "Giulia", "source": "cerca-ritiro",
                         "profile": {"city": "Bari", "interests": ["yoga", "suono"], "travel": "near"},
                         "preferences": {"retreat_alert": {"enabled": True, "scope": "italy", "regions": []}}},
    "benvenuto_meditazioni": {"email": "anteprima@esempio.it", "name": "Giulia", "source": "meditazioni",
                              "profile": {}, "preferences": {}},
    "benvenuto_altro": {"email": "anteprima@esempio.it", "name": "Giulia", "source": "home_letter",
                        "profile": {}, "preferences": {}},
}


async def anteprima(pubblico: str, nome: str, email: Optional[str] = None) -> Dict[str, Any]:
    """L'email di un passo per un destinatario vero (per email) o, se
    non c'e', per uno fittizio. Non manda e non marca niente."""
    from services.email_service import CASELLA_AURYA, _wrap_template
    passo = _passo(pubblico, nome)
    if not passo:
        raise ValueError("passo sconosciuto")
    trovato = False
    nota = None
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
            dovuti = passi_dovuti("cerchio", 0, stato_cerchio(sub), {})
            if dovuti and dovuti[0].nome != nome:
                nota = f"A questa persona partirebbe la variante «{dovuti[0].nome}», non «{nome}»."
        else:
            sub = {**_FITTIZI_SUB.get(nome, _FITTIZI_SUB["benvenuto_altro"]), "email": email or "anteprima@esempio.it"}
        ctx = contesto_cerchio(sub)
    reso = passo.template(ctx)
    if not reso:
        return {"pubblico": pubblico, "passo": nome, "trovato": trovato, "destinatario": ctx["email"],
                "oggetto": None, "html": None, "nota": "Per questo destinatario il passo si salta: niente da dire."}
    oggetto, corpo = reso
    html = (_wrap_template(corpo, "it") if passo.a == _ADMIN
            else _wrap_template(corpo, "it", reply_to=T.risposte_a()))
    return {"pubblico": pubblico, "passo": nome, "trovato": trovato,
            "destinatario": CASELLA_AURYA if passo.a == _ADMIN else ctx["email"],
            "oggetto": oggetto, "html": html, "nota": nota}


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
