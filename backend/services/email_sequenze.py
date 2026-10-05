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
    """Giorno zero (testo del founder, FL3 5/10/2026): un saluto, UN bottone
    che verifica ed entra, dieci minuti per completare. Sostituisce
    «Benvenuto su Aurya — Verifica la tua email»."""
    try:
        from services.email_service import _link_block, _wrap_template, send_email
        url = f"{APP_URL}/verify-email?token={verification_token}&lang={locale or 'it'}"
        html = _wrap_template(f"""
            <p>{_saluto(nome)}</p>
            <p>il tuo spazio su Aurya è aperto.</p>
            <p>Per completarlo bastano circa dieci minuti. Puoi aggiungere le informazioni
            che vuoi mostrare e tornare a modificarle quando vuoi. Un clic sul pulsante
            conferma la tua email e ti porta dentro: non serve rifare il login.</p>
            {_bottone(url, "Apro il mio spazio")}
            {_link_block(url)}
            <p>Per rientrare, quando vuoi: <a href="{APP_URL}/spazio">aurya.life/spazio</a>, con la tua
            email e la password che hai scelto. Se la dimentichi, «Password dimenticata» te ne fa
            scegliere una nuova in un minuto. Non serve registrarsi di nuovo.</p>
            <p>Se hai bisogno di una mano, rispondi a questa email: ci siamo noi.</p>
            {_firma()}
        """, locale or "it", reply_to=risposte_a())
        send_email(email, "Il tuo spazio su Aurya è aperto", html, reply_to=risposte_a())
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
    """EP (19/9) + FL3 (5/10): i canali della rete, nelle parole del founder.
    Ogni canale compare solo se il suo link esiste; senza nessun link
    Telegram si dice come chiedere l'invito, mai un link che non c'e'."""
    bacheca, supporto, ig = telegram_bacheca_url(), telegram_supporto_url(), instagram_url()
    voci = []
    if bacheca:
        voci.append("<p><strong>Bacheca Aurya — Telegram</strong><br>Qui condividiamo novità, richieste "
                    "di eventi e ritiri e cose utili per chi lavora nel benessere."
                    f"{_link_in_chiaro(bacheca)}</p>")
    if supporto:
        voci.append("<p><strong>Supporto — Telegram</strong><br>Se hai una domanda sulla pagina o "
                    f"qualcosa non funziona, scriviamo noi.{_link_in_chiaro(supporto)}</p>")
    if ig:
        voci.append("<p><strong>Instagram</strong><br>Raccontiamo la rete e i professionisti anche "
                    f"qui.{_link_in_chiaro(ig)}</p>")
    if not (bacheca or supporto):
        voci.append("<p>Per entrare nei canali Telegram della rete, rispondi a questa email con il "
                    "tuo nome Telegram e ti mandiamo l'invito.</p>")
    return "".join(voci)

def _blocco_ritiri(iban_presente: bool) -> str:
    """FL3 (5/10/2026): non si usa piu' nel benvenuto della pagina (una cosa
    per email). Resta per compatibilita', vuoto."""
    return ""

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
    """Evento: la pagina e' appena nata. Il link e cosa farci, il listino se
    manca. FL3 (5/10, founder): UNA cosa per email: i canali della rete
    arrivano con op_canali (il giro dopo), i ritiri con op_r14; la consulenza
    a pagamento non sta nel benvenuto."""
    stato = ctx.get("stato") or {}
    url = f"{APP_URL}/o/{stato.get('slug')}"
    return ("La tua pagina è online: ecco il link",
            f"<p>{_saluto(ctx.get('nome'))}</p>"
            f"<p>la tua pagina su Aurya è online:<br><a href=\"{url}\">{url}</a></p>"
            "<p>Puoi metterla nella bio di Instagram o mandarla a chi ti chiede: «Dove ti "
            "trovo?».</p>"
            "<p>Chi la apre vede chi sei, cosa fai e può contattarti per chiederti un posto. "
            "Senza abbonamenti e senza commissioni.</p>"
            + _bottone(url, "Apri la tua pagina")
            + _blocco_listino(stato)
            + "<p>Per tutto il resto puoi rispondere a questa email: la legge Valentina.</p>"
            + _firma())


def op_canali(ctx: dict) -> Tuple[str, str]:
    """FL3 (5/10/2026, founder): i canali della rete, in un'email propria,
    il giro dopo la pagina online. Solo a chi e' online."""
    return ("I canali della rete Aurya",
            f"<p>{_saluto(ctx.get('nome'))}</p>"
            "<p>ora che la tua pagina è online, ecco dove ci si trova.</p>"
            + _blocco_canali()
            + _firma())

def op_np5(ctx: dict) -> Tuple[str, str]:
    """Giorno 5 (testo del founder): con la pagina online ma senza listino,
    «può ancora raccontare qualcosa di te»; senza pagina, «dieci minuti per
    completarla» (PE3: mai dire «non hai la pagina» a chi ce l'ha)."""
    if _pagina_esiste(ctx):
        return ("La tua pagina può ancora raccontare qualcosa di te",
                f"<p>{_saluto(ctx.get('nome'))}</p>"
                "<p>la tua pagina è già online. Se vuoi, puoi aggiungere ancora qualche dettaglio: "
                "una pratica, un servizio con il prezzo, una foto o le informazioni che vuoi far "
                "trovare a chi ti scopre.</p>"
                "<p>Bastano dieci minuti per darle una forma più completa.</p>"
                + _bottone(f"{APP_URL}/listino", "Completo la mia pagina")
                + "<p>Se vuoi un consiglio, rispondi a questa email.</p>"
                + _firma())
    return ("Dieci minuti per completare la tua pagina",
            f"<p>{_saluto(ctx.get('nome'))}</p>"
            "<p>se non hai ancora completato la tua pagina, bastano circa dieci minuti per "
            "aggiungere le informazioni più importanti.</p>"
            "<p>Una pagina completa aiuta chi arriva a capire subito chi sei, cosa fai e come "
            "contattarti.</p>"
            + _bottone(f"{APP_URL}/public-profile", "Completo la mia pagina")
            + "<p>Se è già tutto a posto, non devi fare nulla.</p>"
            + _firma())

def op_np10(ctx: dict) -> Tuple[str, str]:
    """Giorno 10 (testo del founder): le tre cose che fermano una pagina,
    con le risposte corte di sempre dentro (il «contenuto dinamico»)."""
    if _pagina_esiste(ctx):
        return ("Le tre cose che fermano una pagina",
                f"<p>{_saluto(ctx.get('nome'))}</p>"
                "<p>quando una pagina non porta contatti, spesso il problema è molto semplice.</p>"
                "<p>Le tre cose che controlliamo per prime sono:</p>"
                "<ul>"
                "<li><strong>Il prezzo.</strong> «Non so che prezzo mettere»: metti quello che "
                "chiedi già oggi a chi ti contatta. Si cambia in un secondo.</li>"
                "<li><strong>Il servizio.</strong> «Faccio tante cose diverse»: parti da quella che "
                "ti chiedono di più. Le altre le aggiungi dopo, una riga alla volta.</li>"
                "<li><strong>La richiesta.</strong> «Lavoro solo su richiesta»: va bene, il servizio "
                "nasce «su richiesta», chi vuole un posto ti scrive e il prezzo lo concordate.</li>"
                "</ul>"
                "<p>Se una di queste manca, puoi sistemarla direttamente dalla tua pagina.</p>"
                + _bottone(f"{APP_URL}/listino", "Controllo la mia pagina")
                + _firma())
    return ("Le tre cose che fermano una pagina",
            f"<p>{_saluto(ctx.get('nome'))}</p>"
            "<p>prima che qualcuno ti contatti, deve capire in pochi secondi chi sei, cosa "
            "proponi e come trovarti.</p>"
            "<p>Controlla queste tre cose:</p>"
            "<ul>"
            "<li><strong>Chi sei.</strong> Scrivi come parli: chi sei, cosa fai, per chi, cosa può "
            "aspettarsi chi inizia con te. Chi apre la tua pagina vuole conoscerti.</li>"
            "<li><strong>Una foto.</strong> Va bene una foto normale, con la luce del giorno, dove "
            "si vede il tuo viso. Non serve un fotografo.</li>"
            "<li><strong>Un prezzo.</strong> Metti quello che chiedi già oggi a chi ti contatta. "
            "Si cambia in un secondo.</li>"
            "</ul>"
            "<p>Se vuoi, puoi sistemarle ora.</p>"
            + _bottone(f"{APP_URL}/public-profile", "Controllo la mia pagina")
            + _firma())

def op_np15(ctx: dict) -> Tuple[str, str]:
    """Giorno 15 (testo del founder): grazie di essere su Aurya. L'ultima su
    questo passo; lo spazio resta aperto."""
    if _pagina_esiste(ctx):
        return ("Grazie di essere su Aurya",
                f"<p>{_saluto(ctx.get('nome'))}</p>"
                "<p>grazie di essere su Aurya.</p>"
                "<p>La tua pagina è parte della rete di professionisti che stiamo costruendo. "
                "Noi continueremo a lavorare per farla conoscere e per portare nuove persone "
                "alle esperienze presenti sulla piattaforma.</p>"
                "<p>Se vuoi migliorare qualcosa della tua pagina, puoi farlo quando vuoi.</p>"
                + _bottone(f"{APP_URL}/public-profile", "Apro la mia pagina")
                + _firma())
    return ("Grazie di essere su Aurya",
            f"<p>{_saluto(ctx.get('nome'))}</p>"
            "<p>grazie di essere su Aurya.</p>"
            "<p>Se hai già completato la tua pagina, non devi fare altro. Il tuo spazio resta "
            "aperto, gratis, e quando vorrai lo trovi com'era.</p>"
            "<p>Quando vorrai aggiungere qualcosa o raccontarci un'idea, siamo qui: puoi "
            "semplicemente rispondere a questa email.</p>"
            + _bottone(f"{APP_URL}/public-profile", "Completo la mia pagina")
            + _firma())

def op_r14(ctx: dict) -> Optional[Tuple[str, str]]:
    """Giorno 14 con la pagina online e nessun ritiro (testo del founder)."""
    return ("Vuoi pubblicare i tuoi ritiri su Aurya?",
            f"<p>{_saluto(ctx.get('nome'))}</p>"
            "<p>se organizzi ritiri, puoi pubblicarli su Aurya e farli trovare alle persone che "
            "stanno cercando proprio quel tipo di esperienza.</p>"
            "<p>Non serve nessun sistema di pagamento per iniziare: il ritiro nasce «su richiesta», "
            "chi vuole un posto ti scrive e tu confermi.</p>"
            + _bottone(f"{APP_URL}/events/new", "Scopro come funziona")
            + "<p>Se vuoi parlarne con noi, rispondi a questa email.</p>"
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

def _link(email: str, path: str) -> str:
    """C3 (24/9): un link del Cerchio che, al clic, segna l'indirizzo come
    verificato e poi porta a `path` (contratto B3, services/verifica_email).
    Import pigro con ripiego sul link nudo: il modulo nasce in parallelo
    (Lotto B) e queste email devono partire in entrambi gli stati."""
    try:
        from services.verifica_email import link_verificante
        return link_verificante(email, path)
    except Exception:  # noqa: BLE001 — modulo o funzione assenti, o errore: link nudo
        return f"{APP_URL}{path}"


def percorso_preferenze(token: str) -> str:
    return f"/newsletter/preferenze/{token}" if token else "/newsletter"


def url_preferenze_nudo(token: str) -> str:
    """Il link delle preferenze SENZA redirect verificante: e' quello che
    va nell'header List-Unsubscribe (C1), dove Gmail fa una POST diretta."""
    return f"{APP_URL}{percorso_preferenze(token)}"


def _url_preferenze(ctx: dict) -> str:
    """Nel corpo dell'email il link delle preferenze e' verificante (C3)."""
    return _link(ctx.get("email") or "", percorso_preferenze(ctx.get("token") or ""))


def _piede_cerchio(ctx: dict) -> str:
    return (f'<p style="font-size: 13px; color: #6b7280;">Sei nel Cerchio con {ctx.get("email")}. '
            f'Dalle <a href="{_url_preferenze(ctx)}">tue preferenze</a> puoi anche cancellarti con un clic.</p>')

def _dove(ctx: dict) -> str:
    """FL3: «a Bari (zona)», «in Italia», «in Italia o all'estero», o vuoto."""
    citta = (ctx.get("citta") or "").strip()
    travel = ctx.get("travel") or ""
    if travel == "abroad":
        return "in Italia o all'estero"
    if travel in ("italy", "anywhere"):
        return "in Italia"
    if citta:
        return f"a {citta} (zona)"
    return ""

def _meditazioni_riga(ctx: dict) -> str:
    return ("<p>Nel frattempo puoi ascoltare le <strong>meditazioni del Cerchio</strong> dal telefono, "
            "con le cuffie e senza installare nessuna app.</p>"
            + _bottone(_link(ctx.get("email") or "", "/meditazioni"), "Ascolta le meditazioni"))

def benvenuto_cerchio_ritiri(ctx: dict) -> Tuple[str, str]:
    """Chi cerca un ritiro (testo del founder, FL3 5/10/2026): «Sappiamo che ti
    interessano gli eventi e i ritiri di Aurya a {città} (zona)». Mai
    declinato: «ti interessano», non «interessato»."""
    vie = _lista_vie(ctx.get("interessi") or [])
    dove = _dove(ctx)
    cosa = (f"ti interessano {vie} e i ritiri di Aurya" if vie else "ti interessano gli eventi e i ritiri di Aurya")
    if dove:
        cosa += f" {dove}"
    manca = ""
    if not vie or not (ctx.get("citta") or ctx.get("travel")):
        manca = ("<p>Per proporti solo cose adatte a te, dicci cosa ti interessa e dove vivi. "
                 "Ci vuole un minuto e poi possiamo mandarti proposte più vicine a quello che cerchi.</p>"
                 + _bottone(_url_preferenze(ctx), "Le mie preferenze"))
    return ("Sei nel Cerchio di Aurya",
            f"<p>{_saluto(ctx.get('nome'))}</p>"
            "<p>sei nel Cerchio di Aurya.</p>"
            f"<p>Sappiamo che {cosa}.</p>"
            "<p><strong>Come funziona:</strong> quando troviamo un ritiro o un'esperienza che "
            "corrisponde a quello che cerchi, te lo scriviamo. Non vogliamo riempirti la casella "
            "con un elenco di proposte: preferiamo scriverti quando c'è qualcosa che può davvero "
            "interessarti.</p>"
            + manca
            + _meditazioni_riga(ctx)
            + "<p>Se vuoi dirci qualcosa in più su quello che cerchi, rispondi a questa email: "
              "la legge Valentina.</p>"
            + _firma()
            + _piede_cerchio(ctx))

def benvenuto_cerchio_meditazioni(ctx: dict) -> Tuple[str, str]:
    """Dalle meditazioni, senza preferenze sui ritiri (testo del founder)."""
    url = _link(ctx.get("email") or "", "/meditazioni")
    return ("Sei nel Cerchio: le meditazioni sono aperte",
            f"<p>{_saluto(ctx.get('nome'))}</p>"
            "<p>sei nel Cerchio di Aurya e le <strong>meditazioni</strong> sono aperte.</p>"
            "<p>Un tocco sul pulsante e puoi ascoltarle dal telefono, con le cuffie e senza "
            "installare nessuna app.</p>"
            + _bottone(url, "Ascolta le meditazioni")
            + "<p>Per ascoltarle, ti consigliamo le cuffie e dieci minuti in cui nessuno ti cerca. "
              "Puoi semplicemente lasciare il telefono a faccia in giù e iniziare.</p>"
            + "<p>Non c'è niente da fare bene. Se la mente va via, torna.</p>"
            + "<p>Se vuoi dirci com'è stata, rispondi a questa email anche solo con una parola: "
              "le leggiamo tutte.</p>"
            + _firma()
            + _piede_cerchio(ctx))

def benvenuto_cerchio_generico(ctx: dict) -> Tuple[str, str]:
    """Da un'altra porta (home, Magazine, account), senza preferenze (testo del founder)."""
    return ("Sei nel Cerchio di Aurya",
            f"<p>{_saluto(ctx.get('nome'))}</p>"
            "<p>sei nel Cerchio di Aurya. Ecco cosa puoi trovare.</p>"
            "<p><strong>Le meditazioni.</strong><br>Si ascoltano dal telefono, con le cuffie e senza "
            "installare nessuna app.</p>"
            + _bottone(_link(ctx.get("email") or "", "/meditazioni"), "Ascolta le meditazioni")
            + "<p><strong>La Lettera.</strong><br>Quando abbiamo qualcosa che vale la pena condividere: "
              "una pratica raccontata bene, una persona della rete, un'esperienza. Non scriviamo per "
              "riempire una casella.</p>"
            + "<p><strong>I ritiri, se li cerchi.</strong><br>Dicci cosa ti interessa (yoga, respiro, "
              "suono o altro) e dove vivi. Quando troviamo un ritiro adatto, te lo scriviamo.</p>"
            + _bottone(_url_preferenze(ctx), "Le mie preferenze")
            + "<p>Se vuoi dirci cosa cerchi, rispondi a questa email: la legge Valentina.</p>"
            + _firma()
            + _piede_cerchio(ctx))
