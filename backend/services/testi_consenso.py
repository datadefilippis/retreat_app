"""Lotto B2 (24/9/2026) — i testi della casella di consenso, versionati.

Il registro del consenso (`consenso` sull'iscritto + riga in
consent_audit) cita una VERSIONE e ne conserva il testo: la versione
non puo' essere inventata, quindi i testi vivono qui, uno per
versione, e non si modificano mai (si aggiunge una versione nuova).
Specchio frontend: lib/testiConsenso.js (guardia di parita' in Lotto D).

Le storiche sono i testi che le caselle mostravano DAVVERO prima del
24/9 (frontend, prelaunch.json e componenti): servono alla migrazione
per dire con onesta' cosa ha letto chi si e' iscritto allora.
"""
from __future__ import annotations

from typing import Optional

TESTI = {
    # la casella della landing del Cerchio, della home e delle meditazioni
    "cerchio-v1": "Acconsento a ricevere le email del Cerchio di Aurya.",
    # la variante dei cancelli Sound (CancelloLettera)
    "cerchio-v2": ("Acconsento a ricevere le email del Cerchio di Aurya "
                   "(meditazioni, anteprime, la Lettera). Confermerai dall'email "
                   "che ti arriva; ti cancelli con un clic."),
    # dal 24/9: un testo solo, su tutte le porte
    "cerchio-v3": ("Sì, mandami la Lettera del Cerchio di Aurya "
                   "(meditazioni, guide, ritiri). Ti cancelli con un clic."),
    # cerca-ritiro (TravelerLandingPage): la promessa dei ritiri su misura
    "cerchio-ritiri-v1": ("Acconsento a ricevere le email del Cerchio di Aurya, "
                          "con ritiri ed esperienze selezionati in base alle mie preferenze."),
    # i CTA del Magazine e i cancelli delle guide
    "lettera-v1": "Acconsento a ricevere la lettera di Aurya via email.",
    # InvitoSound (esplora, lab)
    "sound-v1": "Acconsento a ricevere la newsletter; disiscrizione in un click.",
    # i lead viaggiatori del prelancio (poi migrati con bn2)
    "lancio-v1": "Acconsento a essere contattato via email sul lancio di Aurya.",
}

VERSIONE_CORRENTE = "cerchio-v3"

# Chi si iscrive senza dichiarare la versione (i form di prima del Lotto
# D) ha letto il testo v1: e' quello che la landing e la home mostrano.
VERSIONE_SENZA_DICHIARAZIONE = "cerchio-v1"

# modalita' del consenso registrate sull'iscritto
MODALITA = ("singolo", "doppio", "manuale", "prelancio", "singolo-senza-prova")


def versione_valida(v: Optional[str]) -> str:
    """La versione dichiarata dal client se la conosciamo, altrimenti
    quella dei form che non la dichiarano."""
    v = (v or "").strip()
    return v if v in TESTI else VERSIONE_SENZA_DICHIARAZIONE


def testo(versione: Optional[str] = None) -> str:
    return TESTI[versione_valida(versione or VERSIONE_CORRENTE)]


def versione_storica(source: Optional[str]) -> str:
    """Per la migrazione: quale casella ha letto chi si e' iscritto
    prima del registro, a giudicare dalla fonte."""
    s = (source or "").lower()
    if s.startswith("prelaunch"):
        return "lancio-v1"
    if s.startswith("cerca-ritiro") or s.startswith("hero"):
        return "cerchio-ritiri-v1"
    if s.startswith("blog") or (s.startswith("gate_") and not s.startswith("gate_meditazione")):
        return "lettera-v1"
    if s.startswith("cancello:"):
        return "cerchio-v2"
    if s.startswith("sound"):
        return "sound-v1"
    return "cerchio-v1"
