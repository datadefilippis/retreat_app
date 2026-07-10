"""Guardie modalità pre-lancio (PL1-PL7).

Il pre-lancio è tutto dietro un unico interruttore runtime
(PRELAUNCH_MODE). La proprietà di sicurezza fondamentale è:
    flag OFF  →  comportamento IDENTICO a oggi.
    flag ON   →  sample visibili (sfocati, non prenotabili) + landing.

Questi test bloccano regressioni su:
  1. il parsing del flag (prelaunch_mode);
  2. il gate dei sample nei listing pubblici (nascosti se flag OFF);
  3. il blocco checkout sui ritiri campione;
  4. il 404 sui sample fuori pre-lancio (_resolve_org);
  5. il wipe (un solo predicato, quattro collection).

Sono guardie di sorgente/pure-function: non richiedono un DB attivo.
"""

import os
import inspect
from pathlib import Path

import core.prelaunch as prelaunch


# ── 1. Flag runtime ──────────────────────────────────────────────────────────

def _set_flag(value):
    if value is None:
        os.environ.pop("PRELAUNCH_MODE", None)
    else:
        os.environ["PRELAUNCH_MODE"] = value


def test_prelaunch_mode_off_by_default():
    """Assente/vuoto/qualsiasi rumore → OFF (default sicuro = oggi)."""
    old = os.environ.get("PRELAUNCH_MODE")
    try:
        for v in (None, "", "  ", "0", "false", "no", "off", "maybe", "2"):
            _set_flag(v)
            assert prelaunch.prelaunch_mode() is False, f"{v!r} dovrebbe essere OFF"
    finally:
        _set_flag(old)


def test_prelaunch_mode_on_values():
    """Solo un set esplicito di valori accende il pre-lancio."""
    old = os.environ.get("PRELAUNCH_MODE")
    try:
        for v in ("1", "true", "TRUE", " yes ", "On", "on"):
            _set_flag(v)
            assert prelaunch.prelaunch_mode() is True, f"{v!r} dovrebbe essere ON"
    finally:
        _set_flag(old)


def test_sample_flag_constant():
    """Un solo campo marchia tutti i documenti campione."""
    assert prelaunch.SAMPLE_FLAG == "is_sample"


# ── 2/3/4. Guardie di sorgente ───────────────────────────────────────────────

def _src(module_relpath: str) -> str:
    root = Path(__file__).resolve().parent.parent
    return (root / module_relpath).read_text(encoding="utf-8")


def test_public_listings_gate_samples_behind_flag():
    """PL8 — specchio esatto: flag OFF = solo contenuti VERI (sample
    nascosti); flag ON = SOLO campioni (i veri non compaiono)."""
    src = _src("routers/public.py")
    # retreats: in prelaunch il gate diventa SOLO sample (niente |=)
    assert "if prelaunch_mode():" in src
    assert "pay_ready = set(sample_orgs)" in src
    assert "pay_ready |= sample_orgs" not in src, \
        "regressione: i ritiri veri comparirebbero in pre-lancio"
    # operatori: specchio sample <=> prelaunch
    assert "if _is_sample != _prelaunch:" in src
    # destinazioni ed esperienze: stessi confini
    assert "allowed_orgs = public_orgs & pay_ready" in src
    # entrambi marcano l'item come sample per il frontend (sfocatura)
    assert '"sample"' in src


def test_resolve_org_404_for_sample_always():
    """PL9 — un'org campione non ha MAI una pagina propria: 404 sempre
    (profilo, landing, store), anche in pre-lancio. Le card in vetrina
    non sono cliccabili, quindi nessun percorso legittimo ci arriva."""
    src = _src("routers/public.py")
    assert 'if org.get("is_sample"):' in src
    assert 'org.get("is_sample") and not prelaunch_mode()' not in src, \
        "regressione: la landing campione tornerebbe raggiungibile"


def test_sample_identity_redacted_server_side():
    """PL9 — l'identità finta non lascia mai il server: titolo, nome
    organizzatore, rating e bio dei sample sono redatti nel payload
    (il frontend mostra segnaposto sfocati)."""
    src = _src("routers/public.py")
    assert '"title": "" if _smp else prod.get("name")' in src
    assert '"org_name": "" if _smp else' in src
    assert '"org_rating": None if _smp else' in src
    assert '"venue_name": None if _smp else' in src
    assert '"name": "" if _is_sample else' in src
    assert '"bio": None if _is_sample else' in src


def test_samples_never_in_sitemap():
    """PL9 — le pagine campione rispondono 404: mai offrirle ai crawler."""
    src = _src("routers/seo.py")
    assert '"is_sample": {"$ne": True}' in src


def test_checkout_blocks_sample_retreats():
    """Un ritiro campione non è mai prenotabile (403), flag o non flag."""
    src = _src("services/order_creation_service.py")
    assert 'is_sample' in src
    assert '403' in src


# ── 5. Wipe reversibile ──────────────────────────────────────────────────────

def test_wipe_covers_all_sample_collections():
    """Il wipe usa un solo predicato (is_sample) sulle quattro collection
    che i sample popolano — così il lancio pulisce senza residui."""
    import scripts.wipe_prelaunch_samples as wipe
    src = inspect.getsource(wipe)
    for coll in ("organizations", "stores", "products", "event_occurrences"):
        assert coll in src, f"wipe non copre {coll}"
    # un solo predicato, marchio condiviso
    assert "SAMPLE_FLAG" in src
    assert "delete_many" in src


def test_lead_payload_profiling_fields():
    """PL10 — il form arricchito raccoglie profilazione: viaggiatore
    (città, interessi, budget) e operatore (telefono, località,
    attività, descrizione). Tutti facoltativi: solo email+consenso
    sono obbligatori, il form resta gentile."""
    from routers.leads import LeadPayload
    fields = LeadPayload.model_fields
    for f in ("phone", "city", "interests", "budget", "activity", "message"):
        assert f in fields, f"campo lead mancante: {f}"
        assert not fields[f].is_required(), f"{f} deve restare facoltativo"
    assert fields["email"].is_required()
    # i campi profilati vengono persistiti (non solo accettati)
    src = _src("routers/leads.py")
    for f in ('"phone"', '"city"', '"interests"', '"budget"', '"activity"'):
        assert f in src


def test_wipe_and_seed_share_the_same_flag():
    """Seed e wipe devono usare lo STESSO marchio, o il wipe lascerebbe
    residui. Guardia contro divergenze."""
    seed = _src("scripts/seed_prelaunch_samples.py")
    assert "is_sample" in seed
