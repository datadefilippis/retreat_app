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
    """I listing pubblici devono nascondere i sample quando il flag è OFF
    e sbloccarli SOLO in pre-lancio."""
    src = _src("routers/public.py")
    # retreats: i sample bypassano il gate Stripe SOLO in prelaunch
    assert "if prelaunch_mode():" in src
    assert "pay_ready |= sample_orgs" in src
    # operatori: sample saltati se non prelaunch
    assert "if _is_sample and not _prelaunch:" in src
    assert "continue" in src
    # entrambi marcano l'item come sample per il frontend (sfocatura)
    assert '"sample"' in src


def test_resolve_org_404_for_sample_outside_prelaunch():
    """La landing operatore campione non è raggiungibile fuori pre-lancio."""
    src = _src("routers/public.py")
    assert 'org.get("is_sample") and not prelaunch_mode()' in src


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


def test_wipe_and_seed_share_the_same_flag():
    """Seed e wipe devono usare lo STESSO marchio, o il wipe lascerebbe
    residui. Guardia contro divergenze."""
    seed = _src("scripts/seed_prelaunch_samples.py")
    assert "is_sample" in seed
