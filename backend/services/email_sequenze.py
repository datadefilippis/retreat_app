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

# I canali della rete (EP, 19/9/2026, founder): la BACHECA Telegram (tutto
# quello che succede nel mondo Aurya, le richieste che arrivano, le info per
# chi lavora nel benessere), il gruppo di SUPPORTO tecnico e digitale, e
# Instagram. I link degli inviti Telegram sono privati: stanno
# nell'ambiente, mai nel codice. Finche' mancano, l'email dice come chiedere
# l'invito, senza mostrare un link che non c'e'. `TELEGRAM_GRUPPO_URL` (il
# vecchio gruppo unico) vale come bacheca se la variabile nuova manca.
def _env(nome: str, default: str = "") -> str:
    return (os.environ.get(nome) or default).strip()


def telegram_bacheca_url() -> str:
    return _env("TELEGRAM_BACHECA_URL") or _env("TELEGRAM_GRUPPO_URL")


def telegram_supporto_url() -> str:
    return _env("TELEGRAM_SUPPORTO_URL")


def instagram_url() -> str:
    return _env("INSTAGRAM_URL", "https://www.instagram.com/aurya.life")


def consulenza_email() -> str:
    return _env("CONSULENZA_EMAIL", "info@aurya.life")


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
    "detox": "il detox", "cammini": "i cammini", "femminile": "i cerchi e il femminile",
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

# (PE1, 24/9, founder) — il promemoria del giorno 2 a noi non esiste piu':
# era l'email piu' inviata di tutte e la coda di lavoro vive nel pannello
# admin.


def _pagina_esiste(ctx: dict) -> bool:
    """PE3: la pagina c'e' (slug + bio) anche se manca il listino."""
    return bool((ctx.get("stato") or {}).get("pagina"))


def _link_in_chiaro(url: str) -> str:
    """Il link scritto per esteso e cliccabile: si legge anche da chi lo
    inoltra o lo copia (founder: «link visibili»)."""
    return f'<br><a href="{url}">{url}</a>'


def _blocco_canali() -> str:
    """EP (19/9): i canali della rete, tre posti tre usi. Ogni canale compare
    solo se il suo link esiste; senza nessun link Telegram si torna a
    «rispondi con il tuo nome Telegram», cosi' nessuna email promette un
    invito che non puo' dare."""
    bacheca, supporto, ig = telegram_bacheca_url(), telegram_supporto_url(), instagram_url()
    voci = []
    if bacheca:
        voci.append("<p><strong>Bacheca Aurya</strong> — qui condividiamo tutto quello che succede "
                    "nel mondo Aurya: le novità della piattaforma, le richieste di eventi e ritiri "
                    "che ci arrivano, le informazioni utili per chi lavora nel benessere. Entra e "
                    f"resta in ascolto.{_link_in_chiaro(bacheca)}</p>")
    if supporto:
        voci.append("<p><strong>Supporto tecnico e digitale</strong> — per ogni domanda sulla tua "
                    "pagina, sul gestionale o su qualcosa che non funziona. Scrivi lì e rispondiamo "
                    f"noi.{_link_in_chiaro(supporto)}</p>")
    if ig:
        voci.append("<p><strong>Instagram</strong> — se ancora non ci segui, raccontiamo la rete e i "
                    f"professionisti anche qui.{_link_in_chiaro(ig)}</p>")
    if not (bacheca or supporto):
        voci.insert(0, "<p>Ora che la pagina è online ti aggiungiamo ai canali Telegram degli "
                       "operatori Aurya: rispondi a questa email con il tuo nome Telegram, e ti "
                       "mandiamo l'invito.</p>")
    n = len(voci)
    testa = ("<p><strong>I canali della rete.</strong> "
             + {1: "Un posto da conoscere.", 2: "Due posti, due usi diversi."}.get(n, "Tre posti, tre usi diversi.")
             + "</p>")
    return testa + "".join(voci)


def _blocco_ritiri(iban_presente: bool) -> str:
    """EP (19/9): non solo l'IBAN. Come funziona pubblicare un ritiro e le tre
    cose che fanno la differenza; la caparra compare solo a chi l'IBAN non
    l'ha ancora messo."""
    caparra = ""
    if not iban_presente:
        caparra = ("<li><strong>La caparra.</strong> Se la chiedi, le persone la pagano con un "
                   "bonifico: l'IBAN va nelle Impostazioni, ci vuole un minuto. Senza, chi chiede "
                   "un posto legge «chi organizza ti scrive per concordare».</li>")
    quante = "Tre cose" if caparra else "Due cose"
    return ("<p><strong>Se pubblichi un ritiro.</strong> Dalla tua pagina puoi pubblicare ritiri "
            "ed eventi con data, luogo, posti e prezzo. Le persone chiedono un posto da lì e tu "
            f"confermi. {quante} che fanno la differenza:</p>"
            "<ul>"
            "<li><strong>I tempi.</strong> I ritiri si riempiono con mesi di anticipo: chi pubblica "
            "a giugno per settembre arriva tardi. Meglio aprire presto, anche con pochi dettagli, "
            "e completare dopo.</li>"
            + caparra +
            "<li><strong>Il programma.</strong> Chi prenota vuole sapere com'è la giornata, chi "
            "conduce, dove si dorme, cosa è compreso. Più è chiaro, meno domande ricevi e più "
            "posti si riempiono.</li>"
            "</ul>"
            "<p><strong>Se vuoi una mano.</strong> Aurya affianca chi organizza un ritiro, "
            "dall'idea alla partenza: la struttura, il programma, il prezzo, la promozione, la "
            "gestione delle iscrizioni. È una consulenza a pagamento, su misura. Se ti interessa "
            f"scrivici in privato a <a href=\"mailto:{consulenza_email()}\">{consulenza_email()}</a> "
            "e ne parliamo.</p>")


def _blocco_listino(stato: dict) -> str:
    """PE2 (24/9, founder): l'email della pagina parte quando la pagina
    NASCE, quindi spesso il listino ancora non c'e'. Un blocco che dice il
    vero: se manca, e' il prossimo passo (un link, non un secondo bottone:
    l'email fa una cosa sola); se c'e', quanti servizi ci sono."""
    n = int(stato.get("n_servizi") or 0)
    url = f"{APP_URL}/listino"
    if n > 0:
        quanti = "un servizio" if n == 1 else f"{n} servizi"
        return (f"<p><strong>Il tuo listino.</strong> In pagina hai già {quanti}: chi arriva sa cosa "
                f"può prenotare. Quando cambia qualcosa lo aggiorni da <a href=\"{url}\">Il tuo "
                "listino</a>.</p>")
    return ("<p><strong>Il prossimo passo è il listino.</strong> Una riga, un prezzo, una durata: "
            "senza, chi arriva sulla tua pagina vede chi sei ma non sa cosa può prenotare. Per "
            "esempio «Trattamento individuale · 60 min · 60 €». Si scrive in un minuto e si cambia "
            f"quando vuoi: <a href=\"{url}\">aggiungi il primo servizio</a>.</p>")


def op_profilo_online(ctx: dict) -> Tuple[str, str]:
    """Evento: la pagina e' appena nata. Il link e cosa farci, il listino
    se manca, i canali della rete (bacheca, supporto, Instagram), come
    funzionano i ritiri (con la caparra solo se l'IBAN manca), la consulenza."""
    stato = ctx.get("stato") or {}
    url = f"{APP_URL}/o/{stato.get('slug')}"
    return ("La tua pagina è online: ecco il link",
            f"<p>{_saluto(ctx.get('nome'))}</p>"
            f"<p>la tua pagina su Aurya è online. È questa: <a href=\"{url}\">{url}</a></p>"
            "<p>Mettila nella bio di Instagram, mandala a chi ti chiede «dove ti trovo?», "
            "stampala sul biglietto. Chi la apre vede chi sei, cosa fai, e può chiederti un "
            "posto. Senza abbonamenti e senza commissioni.</p>"
            + _bottone(url, "Apri la tua pagina")
            + _blocco_listino(stato)
            + _blocco_canali()
            + _blocco_ritiri(bool(stato.get("iban")))
            + "<p>Per tutto il resto rispondi a questa email: la legge Valentina.</p>"
            + _firma())


def op_np5(ctx: dict) -> Tuple[str, str]:
    """Giorno 5: senza pagina, cosa serve; con la pagina ma senza listino,
    il listino (PE3: mai dire «non hai la pagina» a chi ce l'ha)."""
    if _pagina_esiste(ctx):
        stato = ctx.get("stato") or {}
        pagina = f"{APP_URL}/o/{stato.get('slug')}"
        return ("La tua pagina c'è: manca il listino",
                f"<p>{_saluto(ctx.get('nome'))}</p>"
                f"<p>la tua pagina su Aurya è online (<a href=\"{pagina}\">{pagina}</a>), ma non ha "
                "ancora un servizio con il prezzo. Chi la apre vede chi sei e non sa cosa può "
                "prenotare.</p>"
                "<p>Basta una riga, e ci si mette un minuto:</p>"
                "<ul>"
                "<li><strong>il nome</strong> del servizio che proponi più spesso;</li>"
                "<li><strong>la durata</strong>, anche indicativa;</li>"
                "<li><strong>il prezzo</strong>, quello che chiedi già oggi. Si cambia quando vuoi.</li>"
                "</ul>"
                + _bottone(f"{APP_URL}/listino", "Aggiungi il primo servizio")
                + "<p>Se qualcosa ti blocca, rispondi a questa email: la legge Valentina.</p>"
                + _firma())
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
    """Giorno 10: gli ostacoli veri (della pagina, o del listino se la
    pagina c'e'), e l'offerta di farlo insieme."""
    if _pagina_esiste(ctx):
        url = f"{APP_URL}/listino"
        return ("Il listino, in un minuto",
                f"<p>{_saluto(ctx.get('nome'))}</p>"
                "<p>quando un listino resta vuoto, quasi sempre è per una di queste tre cose. "
                "Le diciamo perché a tutte c'è una risposta corta.</p>"
                "<p><strong>«Non so che prezzo mettere.»</strong> Metti il prezzo che chiedi già oggi "
                "a chi ti contatta. Si cambia in un secondo.</p>"
                "<p><strong>«Faccio tante cose diverse.»</strong> Parti da quella che ti chiedono di "
                "più. Le altre le aggiungi dopo, una riga alla volta.</p>"
                "<p><strong>«Lavoro solo su richiesta.»</strong> Va bene: il servizio nasce «su "
                "richiesta», chi vuole un posto ti scrive e il prezzo lo concordate.</p>"
                + _bottone(url, "Apri il listino")
                + "<p>Se preferisci farlo insieme, rispondi a questa email con «insieme»: Valentina "
                  "ti scrive e in dieci minuti il listino è fatto.</p>"
                + _firma())
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
    """Giorno 15: l'ultima, onesta, su questo passo (pagina o listino).
    Lo spazio resta aperto."""
    if _pagina_esiste(ctx):
        url = f"{APP_URL}/listino"
        return ("Un'ultima cosa sul listino, poi non insistiamo",
                f"<p>{_saluto(ctx.get('nome'))}</p>"
                "<p>questa è l'ultima email che ti mandiamo sul listino. La tua pagina resta online "
                "com'è, e il listino lo aggiungi quando vuoi: un minuto, una riga.</p>"
                "<p>Solo due cose, per chiarezza:</p>"
                "<ul>"
                "<li>se vuoi una mano, rispondi <strong>«insieme»</strong>: Valentina ti scrive e lo "
                "fate in dieci minuti;</li>"
                "<li>se ti manca solo il tempo di sederti, il bottone è qui sotto.</li>"
                "</ul>"
                + _bottone(url, "Aggiungi il primo servizio")
                + "<p>Grazie di essere su Aurya. Buon lavoro davvero.</p>"
                + _firma())
    url = f"{APP_URL}/public-profile"
    return ("Un'ultima cosa, poi non insistiamo",
            f"<p>{_saluto(ctx.get('nome'))}</p>"
            "<p>questa è l'ultima email che ti mandiamo su questo passo, la pagina. Non perché ci "
            "sia una scadenza: il tuo spazio resta aperto, gratis, e quando vorrai lo trovi com'era. "
            "Se poi la pagina va online, ti scriviamo il link: quella sola.</p>"
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
