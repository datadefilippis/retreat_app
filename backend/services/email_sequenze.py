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
dire (es. nessun ritiro in zona): il motore allora salta il passo.

Contesto operatore: nome, email, org (dict), stato {online, ritiro,
slug, iban}, fondatori (conteggio() o None).
Contesto Cerchio: nome, email, sub (dict), token (per preferenze e
disiscrizione), meditazione {titolo, url} o None, ritiri [..],
ritiri_in_zona (bool), professionisti [..], citta, interessi [slug..].
"""
import logging
import os
from datetime import datetime
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

APP_URL = (os.environ.get("FRONTEND_URL") or os.environ.get("PUBLIC_BASE_URL") or "https://aurya.life").rstrip("/")

# Il gruppo Telegram degli operatori Aurya (landing: «entri nel gruppo
# Telegram»). Il link lo mette il founder nell'ambiente; finche' manca,
# l'email dice come chiederlo, senza promettere un bottone che non c'e'.
TELEGRAM_GRUPPO_URL = (os.environ.get("TELEGRAM_GRUPPO_URL") or "").strip()

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


def _data_it(iso: Optional[str]) -> str:
    if not iso:
        return ""
    try:
        d = datetime.fromisoformat(str(iso).replace("Z", "+00:00"))
        mesi = ["gennaio", "febbraio", "marzo", "aprile", "maggio", "giugno", "luglio",
                "agosto", "settembre", "ottobre", "novembre", "dicembre"]
        return f"{d.day} {mesi[d.month - 1]}"
    except (ValueError, IndexError):
        return str(iso)[:10]


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
        from services.email_service import _link_block, _wrap_template, send_email, ADMIN_EMAIL
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
        """, locale or "it", reply_to=ADMIN_EMAIL)
        send_email(email, "Il tuo spazio su Aurya è aperto: un clic e sei dentro",
                   html, reply_to=ADMIN_EMAIL)
        return True
    except Exception as exc:  # noqa: BLE001 — la registrazione non si blocca mai per un'email
        logger.warning("benvenuto_operatore: email non inviata a %s: %s", email[:2] + "***", exc)
        return False


# ─────────────────────────────────────────────────────────────────────────────
# OPERATORE — i passi della sequenza
# ─────────────────────────────────────────────────────────────────────────────

def op_g2_admin(ctx: dict) -> Tuple[str, str]:
    """Il promemoria a Valentina: un messaggio vero, da persona a persona."""
    org = ctx.get("org") or {}
    nome_org = org.get("name") or "Un professionista"
    stato = ctx.get("stato") or {}
    dove = "ha già la pagina online" if stato.get("online") else "non ha ancora la pagina online"
    return (f"Da 2 giorni su Aurya: {nome_org}",
            f"<p><b>{nome_org}</b> si è registrato due giorni fa ({ctx.get('email')}) e {dove}. "
            "È il momento del WhatsApp: due righe, senza copione, per chiedere come va e se "
            "serve una mano.</p>"
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


def op_g30(ctx: dict) -> Tuple[str, str]:
    """Giorno 30: come va. Si risponde. L'intervista, e i fondatori finche' sono aperti."""
    fondatori = ctx.get("fondatori") or {}
    righe = [f"<p>{_saluto(ctx.get('nome'))}</p>",
             "<p>è un mese che sei su Aurya. Come va? Cosa ti manca, cosa non torna, cosa "
             "vorresti che facessimo? Rispondi a questa email: la legge Valentina, e risponde lei.</p>",
             "<p>Due cose che forse non sai. L'intervista: per i primi cinquanta professionisti "
             "della rete è gratuita, per sempre; è il modo in cui Aurya ti racconta a chi cerca. "
             "Se la vuoi, rispondi «intervista».</p>"]
    if fondatori.get("aperto"):
        try:
            data = datetime.fromisoformat(fondatori["scadenza"]).strftime("%d/%m/%Y")
        except Exception:  # noqa: BLE001
            data = str(fondatori.get("scadenza", ""))
        righe.append(f"<p>E i fondatori: i primi {fondatori['tetto']} profili pubblicati entro il "
                     f"{data} hanno il Club regalato fino al 30 giugno 2027. Ne restano "
                     f"{fondatori['rimasti']}.</p>")
    righe.append("<p>Grazie di esserci.</p>")
    righe.append(_firma())
    return ("Come va, dopo un mese?", "".join(righe))


# ─────────────────────────────────────────────────────────────────────────────
# IL CERCHIO — i passi dopo la conferma
# ─────────────────────────────────────────────────────────────────────────────

def _url_preferenze(ctx: dict) -> str:
    token = ctx.get("token") or ""
    return f"{APP_URL}/newsletter/preferenze/{token}" if token else f"{APP_URL}/newsletter"


def _piede_cerchio(ctx: dict) -> str:
    return (f'<p style="font-size: 13px; color: #6b7280;">Sei nel Cerchio con {ctx.get("email")}. '
            f'<a href="{_url_preferenze(ctx)}">Le tue preferenze</a>, e da lì ti cancelli con un clic.</p>')


def c1_sei_dentro(ctx: dict) -> Tuple[str, str]:
    """Il giorno dopo la conferma: cosa c'e' da subito, cosa arriva, e
    una domanda sola (la citta') se manca."""
    interessi = _lista_vie(ctx.get("interessi") or [])
    citta = (ctx.get("citta") or "").strip()
    url_med = f"{APP_URL}/meditazioni"
    personale = ""
    if interessi and citta:
        personale = (f"<p>Ci hai detto che ti interessano {interessi}, e che sei a {citta}: "
                     "i ritiri e le esperienze che ti manderemo partono da lì.</p>")
    elif interessi:
        personale = (f"<p>Ci hai detto che ti interessano {interessi}: i ritiri e le esperienze "
                     "che ti manderemo partono da lì.</p>")
    elif citta:
        personale = f"<p>Ci hai detto che sei a {citta}: quello che ti manderemo parte da lì.</p>"
    manca = ""
    if not citta:
        manca = (f"<p>Una cosa sola ci manca: <a href=\"{_url_preferenze(ctx)}\">la tua città</a>. "
                 "Serve per dirti cosa c'è vicino a te, e per niente altro.</p>")
    return ("Sei dentro. Ecco cosa c'è da subito",
            f"<p>{_saluto(ctx.get('nome'))}</p>"
            "<p>sei nel Cerchio di Aurya. Da subito hai le <strong>meditazioni riservate</strong>: "
            "si ascoltano dal telefono, con le cuffie, e non serve nessuna app.</p>"
            + _bottone(url_med, "Ascolta le meditazioni")
            + "<p>Se le apri da un altro dispositivo e trovi il lucchetto, metti la tua email: "
              "si riapre senza iscriverti di nuovo.</p>"
            + personale
            + "<p><strong>Cosa arriva, e quando.</strong> Fra qualche giorno una meditazione "
              "scelta per te. Poi i ritiri e le esperienze vicino a te, quando ce ne sono: mai "
              "un elenco per riempire una email. E la Lettera, quando vale la pena: una pratica "
              "raccontata bene e una persona della rete.</p>"
            + manca
            + "<p>Se vuoi dirci cosa cerchi, rispondi a questa email: la legge Valentina.</p>"
            + _firma()
            + _piede_cerchio(ctx))


def c3_meditazione(ctx: dict) -> Optional[Tuple[str, str]]:
    """Giorno 3: UNA meditazione, e come ascoltarla. Senza una traccia
    pubblicata non si manda niente."""
    med = ctx.get("meditazione") or {}
    if not med.get("url"):
        return None
    titolo = med.get("titolo") or "Una meditazione"
    return (f"Una meditazione per questa settimana: {titolo}",
            f"<p>{_saluto(ctx.get('nome'))}</p>"
            f"<p>ti proponiamo una meditazione sola, per questa settimana: "
            f"<strong>{titolo}</strong>.</p>"
            "<p>Come ascoltarla: le cuffie, dieci minuti in cui nessuno ti cerca, il telefono "
            "a faccia in giù. Non c'è niente da fare bene; se la mente va via, torna.</p>"
            + _bottone(med["url"], "Ascolta")
            + "<p>Quando l'hai ascoltata, se ti va, rispondi con una parola: com'è stata. "
              "Le leggiamo tutte.</p>"
            + _firma()
            + _piede_cerchio(ctx))


def _riga_ritiro(r: dict) -> str:
    dove = ", ".join(x for x in (r.get("city"), r.get("region")) if x)
    quando = _data_it(r.get("start_at"))
    con = f" · con {r['org_name']}" if r.get("org_name") else ""
    testo = " · ".join(x for x in (quando, dove) if x)
    return (f'<li><a href="{APP_URL}{r["url"]}"><strong>{r.get("title")}</strong></a>'
            f'{" · " + testo if testo else ""}{con}</li>')


def c10_vicino(ctx: dict) -> Optional[Tuple[str, str]]:
    """Giorno 10: i ritiri in programma per te (zona o ovunque), oppure i
    professionisti nella tua citta'. Se non c'e' niente di vero, niente."""
    ritiri = ctx.get("ritiri") or []
    prof = ctx.get("professionisti") or []
    citta = (ctx.get("citta") or "").strip()
    if ritiri:
        dove = f"vicino a {citta}" if citta and ctx.get("ritiri_in_zona") else "in programma"
        return (f"I ritiri {dove}, oggi",
                f"<p>{_saluto(ctx.get('nome'))}</p>"
                f"<p>questi sono i ritiri e le esperienze {dove} pubblicati dai professionisti della "
                "rete. Ogni scheda dice chi conduce, dove, quando, il prezzo e come si prenota.</p>"
                "<ul>" + "".join(_riga_ritiro(r) for r in ritiri[:5]) + "</ul>"
                + _bottone(f"{APP_URL}/esperienze", "Tutti i ritiri, per data")
                + "<p>Se cerchi qualcosa di diverso, rispondi qui e dicci cosa: la legge Valentina.</p>"
                + _firma()
                + _piede_cerchio(ctx))
    if prof and citta:
        righe = "".join(
            f'<li><a href="{APP_URL}/o/{p["slug"]}"><strong>{p["nome"]}</strong></a>'
            f'{" · " + p["discipline"] if p.get("discipline") else ""}</li>' for p in prof[:5])
        return (f"Chi c'è a {citta}, nella rete",
                f"<p>{_saluto(ctx.get('nome'))}</p>"
                f"<p>di ritiri vicino a te per ora non ce ne sono in programma. Ma a {citta} ci sono "
                "professionisti della rete Aurya, con la loro pagina e i loro servizi:</p>"
                f"<ul>{righe}</ul>"
                + _bottone(f"{APP_URL}/operatori", "Tutti i professionisti")
                + "<p>Appena c'è un ritiro nella tua zona, te lo scriviamo.</p>"
                + _firma()
                + _piede_cerchio(ctx))
    return None


def c30_come_va(ctx: dict) -> Tuple[str, str]:
    """Giorno 30: come va, cosa cerchi. La citta' se manca."""
    citta = (ctx.get("citta") or "").strip()
    manca = ""
    if not citta:
        manca = (f"<p>E se ci dici <a href=\"{_url_preferenze(ctx)}\">la tua città</a>, quello che "
                 "ti mandiamo diventa più preciso.</p>")
    return ("Come va, dopo un mese nel Cerchio?",
            f"<p>{_saluto(ctx.get('nome'))}</p>"
            "<p>è un mese che sei nel Cerchio. Ti chiediamo una cosa sola: cosa stai cercando, "
            "adesso? Un ritiro, una persona con cui lavorare, una pratica da imparare, o solo "
            "un momento tuo ogni tanto.</p>"
            "<p>Rispondi a questa email con due righe: la legge Valentina, e se nella rete c'è la "
            "persona giusta te la presenta lei.</p>"
            + manca
            + _firma()
            + _piede_cerchio(ctx))
