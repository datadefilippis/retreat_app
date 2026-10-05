"""Le email delle richieste (SR fase 0, P13): nessuno si perde.

Tre tipi di richiesta, una macchina sola:
- «struttura»: l'operatore cerca una struttura per un ritiro (SR);
- «regia»: l'operatore chiede la regia del ritiro (P13, piano §3.1 A);
- «team_building»: un'azienda chiede un team building o un ritiro
  aziendale su misura dalla pagina /aziende (P13, piano §3.1 B).
Chi chiede riceve una ricevuta e un aggiornamento a ogni cambio di
stato; la piattaforma (CASELLA_AURYA, aurya.life@gmail.com) riceve ogni richiesta nuova con il
link al pannello. Best-effort: un'email che non parte non blocca mai.
"""
import logging
import os

logger = logging.getLogger(__name__)

# FL3 (5/10/2026, founder) [FIX frase rotta]: un'email per stato, con oggetto
# suo; «chiusa» non e' piu' un vicolo cieco. Le chiavi restano quelle del registro.
STATI_TESTO = {
    "nuova": "ricevuta, la stiamo leggendo",
    "in_lavorazione": "cercando fra le strutture che conosciamo",
    "proposta": "una o più proposte",
    "chiusa": "chiusa",
}
STATI_TESTO_SERVIZIO = {
    "nuova": "ricevuta, la stiamo leggendo",
    "in_lavorazione": "preparando la proposta",
    "proposta": "la proposta pronta",
    "chiusa": "chiusa",
}
FORMULE = {"leggera": "Regia leggera (290 €)",
           "completa": "Regia completa (690 € + 40 € a partecipante oltre il sesto)",
           "non_so": "da capire insieme"}
def _base() -> str:
    return (os.environ.get("PUBLIC_BASE_URL") or os.environ.get("FRONTEND_URL")
            or "https://aurya.life").rstrip("/")


def _tipo(r: dict) -> str:
    return r.get("tipo") or "struttura"


# AB-R2 (14/9/2026): i servizi del Pro (e del patto 2026) passano di qui
ETICHETTE_PRO = {   # alla piattaforma (terza persona): «chiede i suoi eventi...»
    "lettera_eventi": "i suoi eventi nella Lettera del Cerchio",
    "social": "la pubblicazione dei suoi eventi sui social di Aurya",
    "intervista_reel": "l'intervista e i reel",
}
# FL3 [FIX]: a chi ha chiesto si da' del tu («i tuoi eventi»), non «i suoi»
ETICHETTE_PRO_TU = {
    "lettera_eventi": "i tuoi eventi nella Lettera del Cerchio",
    "social": "la pubblicazione dei tuoi eventi sui social di Aurya",
    "intervista_reel": "l'intervista e i reel",
}


def _riassunto(r: dict) -> str:
    tipo = _tipo(r)
    righe = []
    if tipo == "team_building":
        righe += [f"Azienda: {r.get('azienda') or r.get('organization_nome')}",
                  f"Referente: {r.get('nome')} — {r.get('email')}"]
        if r.get("telefono"):
            righe.append(f"Telefono: {r['telefono']}")
    elif tipo in ETICHETTE_PRO:
        righe.append(f"Servizio: {ETICHETTE_PRO[tipo]}")
    else:
        righe.append(f"Zona: {r.get('zona')}")
    if tipo not in ETICHETTE_PRO:
        righe += [f"Periodo: {r.get('periodo')}", f"Persone: {r.get('persone')}"]
    if tipo == "regia":
        righe.append(f"Formula: {FORMULE.get(r.get('formula'), 'da capire insieme')}")
    if r.get("notti"):
        righe.append(f"Notti: {r['notti']}")
    if r.get("budget_persona"):
        righe.append(f"Budget a persona: {r['budget_persona']:.0f} €")
    if r.get("tipo_ritiro"):
        righe.append(f"Tipo di ritiro: {r['tipo_ritiro']}")
    if r.get("esigenze"):
        righe.append(f"Esigenze: {r['esigenze']}")
    if r.get("messaggio"):
        righe.append(f"Messaggio: {r['messaggio']}")
    return "".join(f"<li>{riga}</li>" for riga in righe)


def avvisa_piattaforma_richiesta(r: dict) -> None:
    try:
        # FV6 (10/9/2026 sera, founder): i moduli (regia, aziende, strutture)
        # scrivono alla casella di Aurya, aurya.life@gmail.com
        from services.email_service import CASELLA_AURYA, _wrap_template, send_email
        chi = r.get("organization_nome") or "Un professionista"
        tipo = _tipo(r)
        if tipo == "regia":
            testa = f"<p><b>{chi}</b> chiede la regia di un ritiro.</p>"
            oggetto = f"Richiesta di regia da {chi}"
        elif tipo == "team_building":
            testa = f"<p><b>{chi}</b> chiede un team building o un ritiro aziendale su misura.</p>"
            oggetto = f"Richiesta team building da {chi}"
        elif tipo in ETICHETTE_PRO:
            testa = f"<p><b>{chi}</b> chiede {ETICHETTE_PRO[tipo]} ({'Pro' if r.get('fonte') == 'piano' else 'patto 2026'}).</p>"
            oggetto = f"Richiesta Pro ({ETICHETTE_PRO[tipo]}) da {chi}"
        else:
            testa = f"<p><b>{chi}</b> cerca una struttura per un ritiro.</p>"
            oggetto = f"Richiesta struttura da {chi}"
        content = (f"{testa}<ul>{_riassunto(r)}</ul>"
                   f'<p><a href="{_base()}/admin/strutture?vista=richieste" style="display:inline-block;'
                   'background:#2f5e58;color:#fff;padding:10px 18px;border-radius:999px;'
                   'text-decoration:none">Apri le richieste</a></p>')
        send_email(CASELLA_AURYA, oggetto, _wrap_template(content, "it"), bypass_gate=True)
    except Exception:   # noqa: BLE001
        logger.exception("richiesta: email alla piattaforma non inviata")


def _saluto(r: dict) -> str:
    nome = (r.get("nome") or "").strip().split(" ")[0]
    return f"<p>Ciao {nome},</p>" if nome else "<p>Ciao,</p>"


def _firma() -> str:
    return "<p>A presto,<br>Valentina e Davide</p>"


def _dettagli(r: dict) -> str:
    """FL3: i dati della richiesta in una frase, non in un elenco di campi."""
    pezzi = []
    if r.get("zona") and _tipo(r) not in ETICHETTE_PRO and _tipo(r) != "team_building":
        pezzi.append(f"a {r['zona']}")
    if r.get("periodo"):
        pezzi.append(str(r["periodo"]))
    if r.get("persone"):
        pezzi.append(f"per {r['persone']} persone")
    if r.get("notti"):
        pezzi.append(f"{r['notti']} notti")
    if r.get("budget_persona"):
        pezzi.append(f"budget {r['budget_persona']:.0f} € a persona")
    return ", ".join(pezzi)


def ricevuta_operatore(r: dict) -> None:
    if not r.get("email"):
        return
    try:
        from services.email_service import _wrap_template, send_email
        tipo = _tipo(r)
        dett = _dettagli(r)
        extra = "".join(f"<p><strong>{k}:</strong> {r[c]}</p>" for k, c in
                        (("Tipo di ritiro", "tipo_ritiro"), ("Esigenze", "esigenze"), ("Messaggio", "messaggio"))
                        if r.get(c))
        if tipo == "regia":
            formula = FORMULE.get(r.get("formula"), "da capire insieme")
            corpo = (_saluto(r) + f"<p>abbiamo ricevuto la tua richiesta{(' (' + dett + ')') if dett else ''}.</p>"
                     "<p>La leggiamo noi e ti scriviamo entro pochi giorni con una proposta chiara: "
                     f"cosa facciamo noi, cosa resta a te e quanto costa ({formula}).</p>")
            oggetto = "La tua richiesta è arrivata"
        elif tipo in ETICHETTE_PRO:
            corpo = (_saluto(r) + f"<p>abbiamo ricevuto la tua richiesta per {ETICHETTE_PRO_TU[tipo]}.</p>"
                     "<p>Ti scriviamo entro pochi giorni per organizzare insieme cosa fare e quando.</p>")
            oggetto = "La tua richiesta è arrivata"
        elif tipo == "team_building":
            azienda = r.get("azienda") or r.get("organization_nome") or "la vostra azienda"
            corpo = (_saluto(r) + f"<p>abbiamo ricevuto la richiesta di <b>{azienda}</b> per un'esperienza "
                     f"su misura{(': ' + dett) if dett else ''}.</p>"
                     "<p>Vi scriviamo entro due giorni lavorativi.</p>"
                     "<p>Prima ci sarà una chiamata, poi una proposta scritta con programma, chi conduce, "
                     "dove si svolge l'esperienza e il prezzo.</p>")
            oggetto = f"Abbiamo ricevuto la richiesta di {azienda}"
        else:
            corpo = (_saluto(r) + f"<p>abbiamo ricevuto la tua richiesta di una struttura per un ritiro"
                     f"{(' ' + dett) if dett else ''}.</p>"
                     "<p>La leggiamo noi e ti scriviamo entro pochi giorni con le strutture che "
                     "conosciamo e che rispondono a quello che cerchi.</p>")
            oggetto = "La tua richiesta di struttura è arrivata"
        coda = ("" if tipo in ETICHETTE_PRO or tipo == "team_building"
                else "<p>Se intanto cambia qualcosa, rispondi a questa email.</p>")
        content = corpo + extra + coda + _firma()
        send_email(r["email"], oggetto, _wrap_template(content, "it"), bypass_gate=True)
    except Exception:   # noqa: BLE001
        logger.exception("richiesta: ricevuta non inviata")


def avvisa_operatore_stato(r: dict) -> None:
    """FL3 [FIX]: un'email per stato, oggetto proprio, mai una frase spezzata."""
    if not r.get("email"):
        return
    try:
        from services.email_service import _wrap_template, send_email
        tipo = _tipo(r)
        stati = STATI_TESTO if tipo == "struttura" else STATI_TESTO_SERVIZIO
        stato = r.get("stato")
        dove = r.get("azienda") or r.get("zona") or ""
        chi = ", ".join(p for p in (dove, str(r.get("periodo") or ""), f"{r['persone']} persone" if r.get("persone") else "") if p)
        if stato == "in_lavorazione":
            oggetto = f"Ci stiamo lavorando: {chi}" if chi else "Ci stiamo lavorando alla tua richiesta"
            corpo = (f"<p>la tua richiesta{(' (' + chi + ')') if chi else ''} è in lavorazione.</p>"
                     f"<p>Stiamo {stati['in_lavorazione']}.</p>"
                     "<p>Ti scriviamo appena c'è qualcosa di concreto.</p>")
        elif stato == "proposta":
            oggetto = "Abbiamo una proposta per te"
            corpo = (f"<p>per la tua richiesta{(' (' + chi + ')') if chi else ''} abbiamo {stati['proposta']}.</p>"
                     "<p>Ti scriviamo a parte con tutti i dettagli entro oggi.</p>")
        elif stato == "chiusa":
            oggetto = "La tua richiesta è chiusa"
            corpo = (f"<p>abbiamo chiuso la tua richiesta{(' (' + chi + ')') if chi else ''}.</p>"
                     "<p>Se non è quello che ti aspettavi, oppure vuoi riaprirla, rispondi a questa "
                     "email: la legge Valentina.</p>")
        else:
            oggetto = "La tua richiesta è arrivata"
            corpo = f"<p>la tua richiesta{(' (' + chi + ')') if chi else ''} è arrivata e la stiamo leggendo.</p>"
        send_email(r["email"], oggetto, _wrap_template(_saluto(r) + corpo + _firma(), "it"), bypass_gate=True)
    except Exception:   # noqa: BLE001
        logger.exception("richiesta: aggiornamento non inviato")
