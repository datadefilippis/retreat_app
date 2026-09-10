"""Le email delle richieste (SR fase 0, P13): nessuno si perde.

Tre tipi di richiesta, una macchina sola:
- «struttura»: l'operatore cerca una struttura per un ritiro (SR);
- «regia»: l'operatore chiede la regia del ritiro (P13, piano §3.1 A);
- «team_building»: un'azienda chiede una giornata alla Masseria dalla
  pagina /aziende (P13, piano §3.1 B).
Chi chiede riceve una ricevuta e un aggiornamento a ogni cambio di
stato; la piattaforma (ADMIN_EMAIL) riceve ogni richiesta nuova con il
link al pannello. Best-effort: un'email che non parte non blocca mai.
"""
import logging
import os

logger = logging.getLogger(__name__)

STATI_TESTO = {
    "nuova": "ricevuta, la stiamo leggendo",
    "in_lavorazione": "in lavorazione: stiamo cercando fra le strutture che conosciamo",
    "proposta": "abbiamo una o più proposte per te: ti scriviamo a parte con i dettagli",
    "chiusa": "chiusa",
}
STATI_TESTO_SERVIZIO = {
    "nuova": "ricevuta, la stiamo leggendo",
    "in_lavorazione": "in lavorazione: stiamo preparando la proposta",
    "proposta": "la proposta è pronta: ti scriviamo a parte con i dettagli",
    "chiusa": "chiusa",
}
FORMULE = {"leggera": "Regia leggera (290 €)",
           "completa": "Regia completa (690 € + 40 € a partecipante oltre il sesto)",
           "non_so": "da capire insieme"}
FORMATI = {"giornata": "Giornata «Respiro» (6 ore)",
           "due_giorni": "Due giorni «Rientro»",
           "su_misura": "Su misura",
           "non_so": "da capire insieme"}


def _base() -> str:
    return (os.environ.get("PUBLIC_BASE_URL") or os.environ.get("FRONTEND_URL")
            or "https://aurya.life").rstrip("/")


def _tipo(r: dict) -> str:
    return r.get("tipo") or "struttura"


def _riassunto(r: dict) -> str:
    tipo = _tipo(r)
    righe = []
    if tipo == "team_building":
        righe += [f"Azienda: {r.get('azienda') or r.get('organization_nome')}",
                  f"Referente: {r.get('nome')} — {r.get('email')}"]
        if r.get("telefono"):
            righe.append(f"Telefono: {r['telefono']}")
        righe.append(f"Formato: {FORMATI.get(r.get('formato'), r.get('formato') or 'da capire insieme')}")
    else:
        righe.append(f"Zona: {r.get('zona')}")
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
        from services.email_service import ADMIN_EMAIL, _wrap_template, send_email
        chi = r.get("organization_nome") or "Un professionista"
        tipo = _tipo(r)
        if tipo == "regia":
            testa = f"<p><b>{chi}</b> chiede la regia di un ritiro.</p>"
            oggetto = f"Richiesta di regia da {chi}"
        elif tipo == "team_building":
            testa = f"<p><b>{chi}</b> chiede un team building alla Masseria.</p>"
            oggetto = f"Richiesta team building da {chi}"
        else:
            testa = f"<p><b>{chi}</b> cerca una struttura per un ritiro.</p>"
            oggetto = f"Richiesta struttura da {chi}"
        content = (f"{testa}<ul>{_riassunto(r)}</ul>"
                   f'<p><a href="{_base()}/admin/strutture?vista=richieste" style="display:inline-block;'
                   'background:#2f5e58;color:#fff;padding:10px 18px;border-radius:999px;'
                   'text-decoration:none">Apri le richieste</a></p>')
        send_email(ADMIN_EMAIL, oggetto, _wrap_template(content, "it"), bypass_gate=True)
    except Exception:   # noqa: BLE001
        logger.exception("richiesta: email alla piattaforma non inviata")


def ricevuta_operatore(r: dict) -> None:
    if not r.get("email"):
        return
    try:
        from services.email_service import _wrap_template, send_email
        tipo = _tipo(r)
        if tipo == "regia":
            corpo = ("<p>Ciao,</p><p>abbiamo ricevuto la tua richiesta di regia per un ritiro. "
                     "La leggiamo personalmente e ti scriviamo entro pochi giorni con una "
                     "proposta chiara: cosa facciamo noi, cosa resta a te, quanto costa.</p>")
            oggetto = "La tua richiesta di regia è arrivata"
        elif tipo == "team_building":
            corpo = (f"<p>Ciao {r.get('nome') or ''},</p><p>abbiamo ricevuto la richiesta di "
                     f"<b>{r.get('azienda') or r.get('organization_nome')}</b> per una giornata alla Masseria. "
                     "Vi scriviamo entro due giorni lavorativi con un preventivo che dice tutto: "
                     "programma, chi conduce, cosa comprende.</p>")
            oggetto = "La vostra richiesta è arrivata — Aurya per le aziende"
        else:
            corpo = ("<p>Ciao,</p><p>abbiamo ricevuto la tua richiesta di una struttura per un "
                     "ritiro. La leggiamo personalmente e ti scriviamo entro pochi giorni con le "
                     "strutture che conosciamo e che rispondono a quello che cerchi.</p>")
            oggetto = "La tua richiesta di struttura è arrivata"
        content = (f"{corpo}<ul>{_riassunto(r)}</ul>"
                   "<p>Se nel frattempo cambia qualcosa (date, persone, budget), rispondi a "
                   "questa email.</p>")
        send_email(r["email"], oggetto, _wrap_template(content, "it"), bypass_gate=True)
    except Exception:   # noqa: BLE001
        logger.exception("richiesta: ricevuta non inviata")


def avvisa_operatore_stato(r: dict) -> None:
    if not r.get("email"):
        return
    try:
        from services.email_service import _wrap_template, send_email
        tipo = _tipo(r)
        stati = STATI_TESTO if tipo == "struttura" else STATI_TESTO_SERVIZIO
        stato = stati.get(r.get("stato"), r.get("stato"))
        nome = {"regia": "richiesta di regia",
                "team_building": "richiesta di team building"}.get(tipo, "richiesta di struttura per un ritiro")
        dove = r.get("azienda") or r.get("zona")
        content = (f"<p>Ciao,</p><p>la tua {nome} "
                   f"({dove}, {r.get('periodo')}, {r.get('persone')} persone) è {stato}.</p>")
        send_email(r["email"], "Aggiornamento sulla tua richiesta",
                   _wrap_template(content, "it"), bypass_gate=True)
    except Exception:   # noqa: BLE001
        logger.exception("richiesta: aggiornamento non inviato")
