"""Le email delle richieste di struttura (SR, fase 0): nessuno si perde.

- l'operatore riceve una ricevuta quando manda la richiesta e un
  aggiornamento a ogni cambio di stato;
- la piattaforma (ADMIN_EMAIL) riceve ogni richiesta nuova con il link
  al pannello.
Best-effort: un'email che non parte non blocca mai la richiesta.
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


def _base() -> str:
    return (os.environ.get("PUBLIC_BASE_URL") or os.environ.get("FRONTEND_URL")
            or "https://aurya.life").rstrip("/")


def _riassunto(r: dict) -> str:
    righe = [f"Zona: {r.get('zona')}", f"Periodo: {r.get('periodo')}",
             f"Persone: {r.get('persone')}"]
    if r.get("notti"):
        righe.append(f"Notti: {r['notti']}")
    if r.get("budget_persona"):
        righe.append(f"Budget a persona: {r['budget_persona']:.0f} €")
    if r.get("tipo_ritiro"):
        righe.append(f"Tipo di ritiro: {r['tipo_ritiro']}")
    if r.get("esigenze"):
        righe.append(f"Esigenze: {r['esigenze']}")
    return "".join(f"<li>{riga}</li>" for riga in righe)


def avvisa_piattaforma_richiesta(r: dict) -> None:
    try:
        from services.email_service import ADMIN_EMAIL, _wrap_template, send_email
        content = (f"<p><b>{r.get('organization_nome') or 'Un professionista'}</b> cerca una "
                   f"struttura per un ritiro.</p><ul>{_riassunto(r)}</ul>"
                   f'<p><a href="{_base()}/admin/strutture" style="display:inline-block;'
                   'background:#2f5e58;color:#fff;padding:10px 18px;border-radius:999px;'
                   'text-decoration:none">Apri le richieste</a></p>')
        send_email(ADMIN_EMAIL, f"Richiesta struttura da {r.get('organization_nome') or 'un professionista'}",
                   _wrap_template(content, "it"), bypass_gate=True)
    except Exception:   # noqa: BLE001
        logger.exception("richiesta struttura: email alla piattaforma non inviata")


def ricevuta_operatore(r: dict) -> None:
    if not r.get("email"):
        return
    try:
        from services.email_service import _wrap_template, send_email
        content = ("<p>Ciao,</p><p>abbiamo ricevuto la tua richiesta di una struttura per un "
                   "ritiro. La leggiamo personalmente e ti scriviamo entro pochi giorni con le "
                   f"strutture che conosciamo e che rispondono a quello che cerchi.</p><ul>{_riassunto(r)}</ul>"
                   "<p>Se nel frattempo cambia qualcosa (date, persone, budget), rispondi a "
                   "questa email.</p>")
        send_email(r["email"], "La tua richiesta di struttura è arrivata",
                   _wrap_template(content, "it"), bypass_gate=True)
    except Exception:   # noqa: BLE001
        logger.exception("richiesta struttura: ricevuta non inviata")


def avvisa_operatore_stato(r: dict) -> None:
    if not r.get("email"):
        return
    try:
        from services.email_service import _wrap_template, send_email
        stato = STATI_TESTO.get(r.get("stato"), r.get("stato"))
        content = (f"<p>Ciao,</p><p>la tua richiesta di struttura per un ritiro "
                   f"({r.get('zona')}, {r.get('periodo')}, {r.get('persone')} persone) è {stato}.</p>")
        send_email(r["email"], "Aggiornamento sulla tua richiesta di struttura",
                   _wrap_template(content, "it"), bypass_gate=True)
    except Exception:   # noqa: BLE001
        logger.exception("richiesta struttura: aggiornamento non inviato")
