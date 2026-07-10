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


def prelaunch_mode() -> bool:
    """True se la modalità pre-lancio è attiva (env PRELAUNCH_MODE)."""
    return os.environ.get("PRELAUNCH_MODE", "").strip().lower() in (
        "1", "true", "yes", "on")
