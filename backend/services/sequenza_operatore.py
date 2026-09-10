"""
LA SEQUENZA DOPO LA REGISTRAZIONE (RB8, 10/9/2026, piano di rebranding
onda 2, piano di business §5.2 «i cinque inneschi»).

Un professionista si registra, riceve il benvenuto (g0, send_welcome)
e poi... niente. In produzione i profili restano a meta'. Quattro
momenti, UNA azione ciascuno, mai un'urgenza:
  g2  — promemoria a Valentina (ADMIN_EMAIL): «scrivigli su WhatsApp»
  g7  — il profilo pubblico (se non e' online) / condividilo (se lo e')
  g14 — il primo ritiro o esperienza (gratis, senza commissioni, su
        richiesta con la caparra via bonifico)
  g30 — «come va?»: si risponde all'email, Valentina legge; l'intervista
        (gratis per i primi 50) e i fondatori finche' sono aperti
Ogni passo parte SOLO nella sua finestra (gN .. gN+7 giorni): chi si e'
registrato mesi fa non riceve tre email in un colpo. Si marca PRIMA di
inviare (sequenza.gN sull'organizzazione): mai due volte. I campioni,
le org spente e il commerce legacy restano fuori.
"""
import logging
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

PASSI: Tuple[Tuple[str, int], ...] = (("g2", 2), ("g7", 7), ("g14", 14), ("g30", 30))
FINESTRA_GIORNI = 7          # ogni passo ha sette giorni per partire, poi si lascia stare
_MAX_PER_TICK = 100


def passo_dovuto(giorni: int) -> Optional[str]:
    """Il passo la cui finestra contiene «giorni dalla registrazione».
    Le finestre non si sovrappongono: quella di un passo finisce dove
    comincia il successivo (g2 vale dal 2° al 6° giorno, g7 dal 7°)."""
    for i, (nome, g) in enumerate(PASSI):
        fine = g + FINESTRA_GIORNI
        if i + 1 < len(PASSI):
            fine = min(fine, PASSI[i + 1][1])
        if g <= giorni < fine:
            return nome
    return None


def _creato_il(org: dict) -> Optional[datetime]:
    v = org.get("created_at")
    if isinstance(v, datetime):
        return v if v.tzinfo else v.replace(tzinfo=timezone.utc)
    if isinstance(v, str) and v:
        try:
            d = datetime.fromisoformat(v.replace("Z", "+00:00"))
            return d if d.tzinfo else d.replace(tzinfo=timezone.utc)
        except ValueError:
            return None
    return None


async def _stato(org: dict) -> Dict[str, object]:
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
            "ritiro": bool(ritiro), "slug": slug}


async def _destinatario(org_id: str) -> Tuple[Optional[str], str]:
    from database import users_collection
    u = await users_collection.find_one(
        {"organization_id": org_id, "role": "admin", "is_active": {"$ne": False}},
        {"_id": 0, "email": 1, "name": 1}, sort=[("created_at", 1)])
    if not u or not u.get("email"):
        return None, ""
    return u["email"], (u.get("name") or "").strip()


def _saluto(nome: str) -> str:
    return f"Ciao {nome.split()[0]}," if nome else "Ciao,"


def _bottone(url: str, testo: str) -> str:
    return (f'<p style="text-align: center;"><a href="{url}" class="btn">{testo}</a></p>')


def _contenuto(passo: str, nome: str, org: dict, stato: dict, fondatori: Optional[dict]) -> Tuple[str, str]:
    """Oggetto e corpo (HTML dentro il template) per il passo."""
    from services.url_builder import build_app_url, build_public_url
    if passo == "g7":
        if stato["online"] and stato["slug"]:
            url = build_public_url(f"/o/{stato['slug']}")
            return ("Il tuo profilo è online: condividilo",
                    f"<p>{_saluto(nome)}</p>"
                    "<p>il tuo profilo su Aurya è online. Chi lo apre vede chi sei, cosa fai e "
                    "come prenotare. Mettilo nella bio di Instagram e mandalo a chi te lo chiede: "
                    "è la tua pagina, senza abbonamenti e senza commissioni.</p>"
                    + _bottone(url, "Apri il tuo profilo"))
        url = build_app_url("/public-profile")
        return ("Il tuo profilo, in dieci minuti",
                f"<p>{_saluto(nome)}</p>"
                "<p>il tuo spazio su Aurya è aperto ma la pagina non è ancora online. Servono "
                "tre cose: due righe su di te, una foto o un link social, un servizio con il "
                "prezzo. Dieci minuti, e chi ti cerca ti trova.</p>"
                + _bottone(url, "Completa il profilo"))
    if passo == "g14":
        if stato["ritiro"]:
            url = build_public_url("/esperienze")
            return ("Il tuo ritiro è in Ritiri ed esperienze",
                    f"<p>{_saluto(nome)}</p>"
                    "<p>il tuo ritiro è pubblicato e compare in «Ritiri ed esperienze», la pagina "
                    "che chi cerca un ritiro apre per prima. Le richieste ti arrivano via email; "
                    "la caparra la chiedi con un bonifico, se hai messo l'IBAN nelle Impostazioni.</p>"
                    + _bottone(url, "Vedi la pagina"))
        url = build_app_url("/events/new")
        return ("Il primo ritiro, o un'esperienza di un giorno",
                f"<p>{_saluto(nome)}</p>"
                "<p>pubblicare un ritiro su Aurya è gratis e senza commissioni: quello che incassi "
                "è tuo. Non serve Stripe: il ritiro nasce «su richiesta», chi vuole un posto ti "
                "scrive e la caparra arriva con un bonifico. Basta una data, un posto e un prezzo. "
                "Se un ritiro è troppo, va bene anche un'esperienza di un giorno.</p>"
                + _bottone(url, "Pubblica il primo ritiro"))
    # g30
    righe = [f"<p>{_saluto(nome)}</p>",
             "<p>è un mese che sei su Aurya. Come va? Cosa ti manca, cosa non torna, cosa "
             "vorresti che facessimo? Rispondi a questa email: la legge Valentina, e risponde lei.</p>",
             "<p>Due cose che forse non sai. L'intervista: per i primi cinquanta professionisti "
             "della rete è gratuita, per sempre; è il modo in cui Aurya ti racconta a chi cerca. "
             "Se la vuoi, rispondi «intervista».</p>"]
    if fondatori and fondatori.get("aperto"):
        try:
            d = datetime.fromisoformat(fondatori["scadenza"])
            data = d.strftime("%d/%m/%Y")
        except Exception:  # noqa: BLE001
            data = fondatori.get("scadenza", "")
        righe.append(f"<p>E i fondatori: i primi {fondatori['tetto']} profili pubblicati entro il "
                     f"{data} hanno il Club regalato per tutto il 2027. Ne restano "
                     f"{fondatori['rimasti']}.</p>")
    righe.append("<p>Grazie di esserci. Valentina e Davide</p>")
    return ("Come va, dopo un mese?", "".join(righe))


def _manda(passo: str, org: dict, email: str, nome: str, stato: dict, fondatori: Optional[dict]) -> bool:
    try:
        from services.email_service import ADMIN_EMAIL, _wrap_template, send_email
        from services.url_builder import build_app_url
        if passo == "g2":
            # il promemoria a Valentina: un messaggio vero, da persona a persona
            content = (f"<p><b>{org.get('name') or 'Un professionista'}</b> si è registrato due giorni "
                       f"fa ({email}). È il momento del WhatsApp: due righe, senza copione, per "
                       "chiedere come va e se serve una mano col profilo.</p>"
                       f'<p><a href="{build_app_url("/admin")}" class="btn">Apri il pannello</a></p>')
            return bool(send_email(ADMIN_EMAIL, f"Da 2 giorni su Aurya: {org.get('name') or email}",
                                   _wrap_template(content, "it"), bypass_gate=True))
        oggetto, corpo = _contenuto(passo, nome, org, stato, fondatori)
        return bool(send_email(email, oggetto, _wrap_template(corpo, "it"),
                               reply_to=ADMIN_EMAIL, bypass_gate=True))
    except Exception as exc:  # noqa: BLE001
        logger.warning("sequenza_operatore: %s non inviato a %s: %s", passo, email[:2] + "***", exc)
        return False


async def run_sequenza_sweep(now: datetime = None, dry_run: bool = False) -> Dict[str, object]:
    """Un giro: per ogni organizzazione nella finestra di un passo, quel passo."""
    from database import organizations_collection
    now = now or datetime.now(timezone.utc)
    piu_vecchia = now - timedelta(days=PASSI[-1][1] + FINESTRA_GIORNI)
    result: Dict[str, object] = {"candidati": [], "inviati": 0, "errori": 0}
    fondatori = None
    try:
        from routers.fondatori import conteggio
        fondatori = await conteggio()
    except Exception:  # noqa: BLE001
        fondatori = None
    cursor = organizations_collection.find(
        {"is_sample": {"$ne": True}, "is_active": {"$ne": False},
         "legacy_commerce": {"$ne": True}, "deactivated_at": None},
        {"_id": 0, "id": 1, "name": 1, "created_at": 1, "public_profile": 1,
         "public_slug": 1, "sequenza": 1},
    ).limit(_MAX_PER_TICK * 5)
    n = 0
    async for org in cursor:
        creato = _creato_il(org)
        if not creato or creato < piu_vecchia:
            continue
        giorni = (now - creato).days
        passo = passo_dovuto(giorni)
        if not passo or (org.get("sequenza") or {}).get(passo):
            continue
        result["candidati"].append((org["id"], passo))
        if dry_run or n >= _MAX_PER_TICK:
            continue
        email, nome = await _destinatario(org["id"])
        if not email:
            continue
        # si marca PRIMA di inviare: mai due volte
        marked = await organizations_collection.update_one(
            {"id": org["id"], f"sequenza.{passo}": {"$exists": False}},
            {"$set": {f"sequenza.{passo}": now.isoformat()}})
        if marked.modified_count != 1:
            continue
        n += 1
        stato = await _stato(org)
        if _manda(passo, org, email, nome, stato, fondatori):
            result["inviati"] += 1
        else:
            result["errori"] += 1
    if result["candidati"]:
        logger.info("sequenza_operatore: %s", {**result, "candidati": len(result["candidati"])})
    return result
