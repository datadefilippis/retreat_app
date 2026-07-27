"""Modalità pre-lancio (soft launch) — interruttore unico.

Con PRELAUNCH_MODE attivo l'app mostra al pubblico una vetrina "in
preparazione": home splash con due strade (operatore / viaggiatore),
due landing di raccolta lead, e la directory popolata da dati CAMPIONE
(is_sample=True) mostrati sfocati e NON prenotabili.

Reversibilità garantita: è tutto dietro questo flag. Al lancio:
  1. python scripts/wipe_prelaunch_samples.py   (cancella i sample)
  2. PRELAUNCH_MODE=false + redeploy
→ l'app torna identica al comportamento normale. Nessun codice da
rimuovere; landing e script restano dormienti nel repo.

Runtime, non build-time: il frontend legge il flag da GET
/api/public/site-config, così accendere/spegnere il lancio è un flip di
variabile d'ambiente + restart, senza rebuild del frontend.
"""

import os

# Marchio comune su TUTTI i documenti campione (org, store, product,
# occurrence): un solo campo, un solo predicato per il wipe.
SAMPLE_FLAG = "is_sample"

# RT1 (piano sito-rete, docs/SITO_RETE_PIANO_2026-07.md) — le fasi del
# sito pubblico. I blocchi si sostituiscono, gli URL mai:
#   network     → sito della rete: manifesto, magazine, operatori
#                 intervistati, newsletter. Marketplace SPENTO.
#   marketplace → lancio: si riaccendono ritiri/prenotazioni/checkout
#                 SOPRA il sito della rete.
SITE_PHASES = ("network", "marketplace")


def site_phase() -> str:
    """Fase corrente del sito pubblico (runtime, env SITE_PHASE).

    SITE_PHASE esplicita vince; senza, si deriva dal flag legacy
    PRELAUNCH_MODE (true → network) così il deploy attuale non cambia
    comportamento finché non si flippa la nuova env."""
    explicit = os.environ.get("SITE_PHASE", "").strip().lower()
    if explicit in SITE_PHASES:
        return explicit
    legacy_on = os.environ.get("PRELAUNCH_MODE", "").strip().lower() in (
        "1", "true", "yes", "on")
    return "network" if legacy_on else "marketplace"


def prelaunch_mode() -> bool:
    """True quando il marketplace NON è pubblico (ogni fase != marketplace).

    Resta il predicato unico letto da tutte le guardie backend (listing,
    noindex, gate GT1b): la semantica "il transazionale è spento" vale
    identica per il vecchio pre-lancio e per la fase rete."""
    return site_phase() != "marketplace"
