"""
LE EMAIL DELLE SEQUENZE (FV, 10/9/2026) — un posto solo, scritte bene.

Regola di casa: ogni email fa UNA cosa, si puo' rispondere (legge
Valentina), niente urgenza finta, niente formule da ufficio, niente
codici. I testi vivono qui e non nei dizionari generici di
email_service, cosi' si leggono per intero e si cambiano insieme.

Chi le manda e quando sta in services/sequenze.py (il motore: passi
come dati, finestre, marcature). Qui ci sono solo le parole.

Ogni funzione «passo» riceve un contesto (dict) e restituisce
(oggetto, corpo_html) oppure None quando non c'e' niente di onesto da
dire: il motore allora salta il passo.

DA CHI PARTONO E DOVE SI RISPONDE (domanda del founder, 10/9 sera):
il mittente e' SMTP_FROM_EMAIL (in prod noreply@aurya.life, «Aurya»);
OGNI email porta il Reply-To = risposte_a() = aurya.life@gmail.com (FV6,
founder; REPLY_TO_EMAIL se impostata). Il
client di posta risponde al Reply-To, non al mittente: la risposta
arriva nella casella vera, e il piede dell'email lo dice.

Contesto operatore: nome, email, org (dict), stato {online, ritiro,
slug, iban}, fondatori (conteggio() o None).
Contesto Cerchio: nome, email, token (preferenze e disiscrizione),
citta, interessi [slug..], travel, porta ('meditazioni' | 'altro'),
vuole_ritiri (bool).
"""
import logging
import os
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

APP_URL = (os.environ.get("FRONTEND_URL") or os.environ.get("PUBLIC_BASE_URL") or "https://aurya.life").rstrip("/")

# Il gruppo Telegram degli operatori Aurya (landing: «entri nel gruppo
# Telegram»). Il link lo mette il founder nell'ambiente; finche' manca,
# l'email dice come chiederlo, senza promettere un bottone che non c'e'.
TELEGRAM_GRUPPO_URL = (os.environ.get("TELEGRAM_GRUPPO_URL") or "").strip()


def risposte_a() -> str:
    """La casella dove arrivano le risposte (Reply-To): aurya.life@gmail.com
    (FV6, founder), o REPLY_TO_EMAIL se impostata."""
    from services.email_service import REPLY_TO_DEFAULT
    return REPLY_TO_DEFAULT


# Le quattordici vie della landing /cerca-ritiro, dette bene
ETICHETTE_VIE: Dict[str, str] = {
    "yoga": "lo yoga", "meditazione": "la meditazione", "breathwork": "il respiro",
    "suono": "il suono", "reiki": "il reiki", "costellazioni": "le costellazioni",
    "astrologia": "l'astrologia", "ayurveda": "l'ayurveda", "tantra": "il tantra",
    "detox": "il detox", "cammini": "i cammini", "cerchi": "i cerchi",
    "crescita": "la crescita personale", "misto": "un po' di tutto",
}


def _saluto(nome: str) -> str:
    nome = (nome or "").strip().split(" ")[0]
    return f"Ciao {nome}," if nome else "Ciao,"


def _bottone(url: str, testo: str) -> str:
    return f'<p style="text-align: center;"><a href="{url}" class="btn">{testo}</a></p>'


def _firma() -> str:
    return "<p>A presto,<br>Valentina e Davide</p>"


def _lista_vie(interessi: List[str]) -> str:
    voci = [ETICHETTE_VIE[i] for i in (interessi or []) if i in ETICHETTE_VIE and i != "misto"]
    if not voci:
        return ""
    if len(voci) == 1:
        return voci[0]
    return ", ".join(voci[:-1]) + " e " + voci[-1]


# ─────────────────────────────────────────────────────────────────────────────
# OPERATORE — giorno zero (dalla registrazione, con il link di verifica)
# ─────────────────────────────────────────────────────────────────────────────

def benvenuto_operatore(email: str, nome: str, verification_token: str, locale: str = "it") -> bool:
    """Giorno zero: un saluto, UN bottone che verifica ed entra, i tre passi,
    cosa succede dopo. Sostituisce «Benvenuto su Aurya — Verifica la tua email»."""
    try:
        from services.email_service import _link_block, _wrap_template, send_email
        url = f"{APP_URL}/verify-email?token={verification_token}&lang={locale or 'it'}"
        html = _wrap_template(f"""
            <p>{_saluto(nome)}</p>
            <p>il tuo spazio su Aurya è aperto. Un clic qui sotto conferma la tua email
            e ti porta dentro: non serve rifare il login.</p>
            {_bottone(url, "Entra nel tuo spazio")}
            {_link_block(url)}
            <p><strong>Cosa trovi dentro, in tre passi.</strong></p>
            <ol>
                <li><strong>La tua pagina.</strong> Una foto, due righe su di te, il primo
                servizio con il prezzo. Dieci minuti, e sei online con un link da mettere
                nella bio.</li>
                <li><strong>I tuoi ritiri ed eventi.</strong> Data, luogo, posti e prezzo:
                le persone chiedono un posto dalla tua pagina e tu confermi. Senza
                commissioni, mai.</li>
                <li><strong>La rete.</strong> Quando il profilo è online entri nel gruppo
                Telegram degli operatori Aurya: le novità, le richieste che arrivano, noi a
                un messaggio di distanza.</li>
            </ol>
            <p>Se qualcosa non torna, rispondi a questa email: la legge Valentina.</p>
            {_firma()}
        """, locale or "it", reply_to=risposte_a())
        send_email(email, "Il tuo spazio su Aurya è aperto: un clic e sei dentro",
                   html, reply_to=risposte_a())
        return True
    except Exception as exc:  # noqa: BLE001 — la registrazione non si blocca mai per un'email
        logger.warning("benvenuto_operatore: email non inviata a %s: %s", email[:2] + "***", exc)
        return False


# ─────────────────────────────────────────────────────────────────────────────
# OPERATORE — i passi della sequenza
# ─────────────────────────────────────────────────────────────────────────────

def op_g2_admin(ctx: dict) -> Tuple[str, str]:
    """Il promemoria a noi: aggiungilo al gruppo Telegram e scrivigli due righe."""
    org = ctx.get("org") or {}
    nome_org = org.get("name") or "Un professionista"
    stato = ctx.get("stato") or {}
    dove = "ha già la pagina online" if stato.get("online") else "non ha ancora la pagina online"
    return (f"Da 2 giorni su Aurya: {nome_org}",
            f"<p><b>{nome_org}</b> si è registrato due giorni fa ({ctx.get('email')}) e {dove}.</p>"
            "<p>Due cose da fare: <strong>aggiungerlo al gruppo Telegram</strong> degli operatori "
            "Aurya, e scrivergli due righe senza copione, per chiedere come va e se serve una "
            "mano con la pagina.</p>"
            + _bottone(f"{APP_URL}/admin", "Apri il pannello"))


def _riga_telegram() -> str:
    if TELEGRAM_GRUPPO_URL:
        return (f'<p><strong>La rete.</strong> Il gruppo Telegram degli operatori Aurya è qui: '
                f'<a href="{TELEGRAM_GRUPPO_URL}">entra nel gruppo</a>. Lì passano le novità, '
                "le richieste che arrivano, e ci siamo noi.</p>")
    return ("<p><strong>La rete.</strong> Ora che la pagina è online ti aggiungiamo al gruppo "
            "Telegram degli operatori Aurya: rispondi a questa email con il tuo numero o il tuo "
            "nome Telegram, e ti mandiamo l'invito.</p>")


def op_profilo_online(ctx: dict) -> Tuple[str, str]:
    """Evento: la pagina e' appena andata online. Il link, cosa farci,
    la rete, e un'avvertenza sull'IBAN (solo se manca)."""
    stato = ctx.get("stato") or {}
    url = f"{APP_URL}/o/{stato.get('slug')}"
    iban = ""
    if not stato.get("iban"):
        iban = ("<p><strong>Una cosa per dopo.</strong> Se pubblicherai un ritiro con la caparra, "
                "le persone la pagano con un bonifico: l'IBAN va nelle Impostazioni, ci vuole un "
                "minuto. Senza, chi chiede un posto legge «chi organizza ti scrive per concordare».</p>")
    return ("La tua pagina è online: ecco il link",
            f"<p>{_saluto(ctx.get('nome'))}</p>"
            f"<p>la tua pagina su Aurya è online. È questa: <a href=\"{url}\">{url}</a></p>"
            "<p>Mettila nella bio di Instagram, mandala a chi ti chiede «dove ti trovo?», "
            "stampala sul biglietto. Chi la apre vede chi sei, cosa fai, e può chiederti un "
            "posto. Senza abbonamenti e senza commissioni.</p>"
            + _bottone(url, "Apri la tua pagina")
            + _riga_telegram()
            + iban
            + "<p>Se vuoi che la guardiamo insieme, rispondi qui: la legge Valentina.</p>"
            + _firma())


def op_np5(ctx: dict) -> Tuple[str, str]:
    """Giorno 5 senza pagina: cosa serve, in concreto."""
    url = f"{APP_URL}/public-profile"
    return ("Ti manca solo la pagina",
            f"<p>{_saluto(ctx.get('nome'))}</p>"
            "<p>il tuo spazio su Aurya è aperto, ma la tua pagina non è ancora online. "
            "Per andarci servono tre cose, e ci si mette dieci minuti:</p>"
            "<ul>"
            "<li><strong>due righe su di te</strong>, come le diresti a chi ti chiede cosa fai;</li>"
            "<li><strong>una foto</strong>, anche dal telefono, o il link al tuo Instagram;</li>"
            "<li><strong>un servizio con il prezzo</strong>: quello che proponi più spesso.</li>"
            "</ul>"
            "<p>Poi la pagina è online, con un link da condividere.</p>"
            + _bottone(url, "Completa la pagina")
            + "<p>Se qualcosa ti blocca, rispondi a questa email: la legge Valentina.</p>"
            + _firma())


def op_np10(ctx: dict) -> Tuple[str, str]:
    """Giorno 10 senza pagina: gli ostacoli veri, e l'offerta di farlo insieme."""
    url = f"{APP_URL}/public-profile"
    return ("Cosa blocca, di solito",
            f"<p>{_saluto(ctx.get('nome'))}</p>"
            "<p>quando una pagina resta a metà, quasi sempre è per una di queste tre cose. "
            "Le diciamo perché a tutte c'è una risposta corta.</p>"
            "<p><strong>«Non so cosa scrivere.»</strong> Scrivi come parli: chi sei, cosa fai, per "
            "chi. Due righe bastano; le lunghe le leggono in pochi.</p>"
            "<p><strong>«Non ho una foto adatta.»</strong> Va bene una foto normale, con la luce del "
            "giorno, dove si vede il tuo viso. Non serve un fotografo.</p>"
            "<p><strong>«Non so che prezzo mettere.»</strong> Metti il prezzo che chiedi già oggi "
            "a chi ti contatta. Si cambia in un secondo.</p>"
            + _bottone(url, "Riprendi la pagina")
            + "<p>Se preferisci farlo insieme, rispondi a questa email con «insieme»: Valentina "
              "ti scrive e in un quarto d'ora la pagina è online.</p>"
            + _firma())


def op_np15(ctx: dict) -> Tuple[str, str]:
    """Giorno 15 senza pagina: l'ultima, onesta. Lo spazio resta aperto."""
    url = f"{APP_URL}/public-profile"
    return ("Un'ultima cosa, poi non insistiamo",
            f"<p>{_saluto(ctx.get('nome'))}</p>"
            "<p>questa è l'ultima email che ti mandiamo sulla pagina. Non perché ci sia una "
            "scadenza: il tuo spazio resta aperto, gratis, e quando vorrai lo trovi com'era.</p>"
            "<p>Solo tre cose, per chiarezza:</p>"
            "<ul>"
            "<li>se non è il momento, rispondi <strong>«più avanti»</strong> e ci risentiamo fra "
            "qualche mese, senza altre email nel mezzo;</li>"
            "<li>se vuoi una mano, rispondi <strong>«chiamami»</strong> con il tuo numero: "
            "Valentina ti chiama e la pagina la fate insieme, in un quarto d'ora;</li>"
            "<li>se ti manca solo il tempo di sederti, il bottone è qui sotto.</li>"
            "</ul>"
            + _bottone(url, "Completa la pagina")
            + "<p>Grazie di esserti iscritto. Se non ci sentiamo, buon lavoro davvero.</p>"
            + _firma())


def op_r14(ctx: dict) -> Optional[Tuple[str, str]]:
    """Giorno 14 con la pagina online e nessun ritiro: il primo."""
    url = f"{APP_URL}/events/new"
    return ("Il primo ritiro, o un'esperienza di un giorno",
            f"<p>{_saluto(ctx.get('nome'))}</p>"
            "<p>la tua pagina è online. Il passo dopo è un ritiro, o anche solo un'esperienza "
            "di un giorno: una data, un posto, un prezzo.</p>"
            "<p>Pubblicarlo su Aurya è gratis e senza commissioni: quello che incassi è tuo. "
            "Non serve Stripe. Il ritiro nasce «su richiesta»: chi vuole un posto ti scrive, "
            "tu confermi, e la caparra arriva con un bonifico.</p>"
            "<p>Ogni ritiro pubblicato compare in «Ritiri ed esperienze», la pagina che chi "
            "cerca un ritiro apre per prima, e arriva alle persone del Cerchio nella tua zona.</p>"
            + _bottone(url, "Pubblica il primo ritiro")
            + "<p>Se hai un'idea ma non sai da dove partire, rispondi qui: la legge Valentina.</p>"
            + _firma())


# ─────────────────────────────────────────────────────────────────────────────
# IL CERCHIO — UN benvenuto, che si adatta a come e da dove ci si iscrive
# (founder 10/9 sera: «un'email che si adatta in base al tipo di
# iscrizione al Cerchio dell'utente, da dove lo fa e come lo fa»).
#   - vuole_ritiri (ha detto le vie o acceso l'avviso ritiri): benvenuto,
#     «appena c'è un ritiro adatto te lo scriviamo», le meditazioni se vuole;
#   - dalle meditazioni, senza preferenze sui ritiri: solo le meditazioni,
#     nessuna parola sui ritiri;
#   - da un'altra porta (home, Magazine, account), senza preferenze: cosa
#     c'è nel Cerchio, e «se cerchi un ritiro dicci le tue vie».
# ─────────────────────────────────────────────────────────────────────────────

def _url_preferenze(ctx: dict) -> str:
    token = ctx.get("token") or ""
    return f"{APP_URL}/newsletter/preferenze/{token}" if token else f"{APP_URL}/newsletter"


def _piede_cerchio(ctx: dict) -> str:
    return (f'<p style="font-size: 13px; color: #6b7280;">Sei nel Cerchio con {ctx.get("email")}. '
            f'<a href="{_url_preferenze(ctx)}">Le tue preferenze</a>, e da lì ti cancelli con un clic.</p>')


def _dove(ctx: dict) -> str:
    citta = (ctx.get("citta") or "").strip()
    travel = ctx.get("travel") or ""
    if travel == "abroad":
        return "in Italia o all'estero"
    if travel in ("italy", "anywhere"):
        return "in Italia"
    if citta:
        return f"vicino a {citta}"
    return ""


def _meditazioni_riga() -> str:
    return ("<p>Nel frattempo, se ti va, ci sono le <strong>meditazioni gratuite</strong> del "
            "Cerchio: si ascoltano dal telefono, con le cuffie, senza nessuna app.</p>"
            + _bottone(f"{APP_URL}/meditazioni", "Ascolta le meditazioni"))


def benvenuto_cerchio_ritiri(ctx: dict) -> Tuple[str, str]:
    """Chi cerca un ritiro: te lo scriviamo appena c'e', sulle tue preferenze."""
    vie = _lista_vie(ctx.get("interessi") or [])
    dove = _dove(ctx)
    if vie and dove:
        cosa = f"ci hai detto che ti chiamano {vie}, e che lo cerchi {dove}"
    elif vie:
        cosa = f"ci hai detto che ti chiamano {vie}"
    elif dove:
        cosa = f"ci hai detto che lo cerchi {dove}"
    else:
        cosa = "ci hai detto che cerchi un ritiro o un'esperienza"
    manca = ""
    if not vie or not (ctx.get("citta") or ctx.get("travel")):
        manca = (f"<p>Per proporti solo cose adatte a te, <a href=\"{_url_preferenze(ctx)}\">dicci le "
                 "tue vie e dove vivi</a>: un minuto, e da lì in poi ricevi solo quello che ti somiglia.</p>")
    return ("Benvenuto nel Cerchio di Aurya",
            f"<p>{_saluto(ctx.get('nome'))}</p>"
            f"<p>sei nel Cerchio di Aurya. Cerchi un ritiro: {cosa}.</p>"
            "<p><strong>Come funziona.</strong> Appena c'è un ritiro o un'esperienza che corrisponde "
            "a quello che ci hai detto, te lo scriviamo. Non un elenco per riempire una email: una "
            "proposta, quando c'è.</p>"
            + manca
            + _meditazioni_riga()
            + "<p>Se vuoi dirci di più su quello che cerchi, rispondi a questa email: la legge Valentina.</p>"
            + _firma()
            + _piede_cerchio(ctx))


def benvenuto_cerchio_meditazioni(ctx: dict) -> Tuple[str, str]:
    """Dalle meditazioni, senza preferenze sui ritiri: solo le meditazioni."""
    url = f"{APP_URL}/meditazioni"
    return ("Benvenuto nel Cerchio: le tue meditazioni",
            f"<p>{_saluto(ctx.get('nome'))}</p>"
            "<p>sei nel Cerchio di Aurya, e le <strong>meditazioni</strong> si sono aperte.</p>"
            + _bottone(url, "Ascolta le meditazioni")
            + "<p>Come ascoltarle: le cuffie, dieci minuti in cui nessuno ti cerca, il telefono "
              "a faccia in giù. Non c'è niente da fare bene; se la mente va via, torna.</p>"
            + "<p>Se le apri da un altro dispositivo e trovi il lucchetto, metti la tua email: "
              "si riapre senza iscriverti di nuovo.</p>"
            + "<p>Se vuoi dirci com'è stata, rispondi a questa email con una parola: le leggiamo tutte.</p>"
            + _firma()
            + _piede_cerchio(ctx))


def benvenuto_cerchio_generico(ctx: dict) -> Tuple[str, str]:
    """Da un'altra porta (home, Magazine, account), senza preferenze."""
    return ("Benvenuto nel Cerchio di Aurya",
            f"<p>{_saluto(ctx.get('nome'))}</p>"
            "<p>sei nel Cerchio di Aurya. Ecco cosa c'è.</p>"
            "<p><strong>Le meditazioni gratuite.</strong> Si ascoltano dal telefono, con le cuffie, "
            "senza nessuna app.</p>"
            + _bottone(f"{APP_URL}/meditazioni", "Ascolta le meditazioni")
            + "<p><strong>La Lettera.</strong> Quando vale la pena: una pratica raccontata bene e una "
              "persona della rete. Mai per riempire una casella.</p>"
            + f"<p><strong>I ritiri, se li cerchi.</strong> <a href=\"{_url_preferenze(ctx)}\">Dicci "
              "le tue vie e dove vivi</a>, e appena c'è un ritiro o un'esperienza adatta te lo scriviamo.</p>"
            + "<p>Se vuoi dirci cosa cerchi, rispondi a questa email: la legge Valentina.</p>"
            + _firma()
            + _piede_cerchio(ctx))
