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
    """PL9/PL14 — l'IDENTITÀ finta non lascia mai il server: nome
    organizzatore, rating, venue e bio dei sample sono redatti nel
    payload (segnaposto sfocati nel frontend). Il TITOLO invece resta
    visibile per scelta founder (PL14): è evocativo e descrittivo,
    comunica il concept senza rivelare chi c'è dietro."""
    src = _src("routers/public.py")
    assert '"title": prod.get("name")' in src            # visibile (PL14)
    assert '"title": "" if _smp' not in src, \
        "regressione: il titolo evocativo tornerebbe oscurato"
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
    for f in ("phone", "city", "interests", "budget", "activity", "message",
              # PL13 — raggio viaggio + dettaglio condizionale operatore
              "travel", "disciplines", "venue_type", "capacity"):
        assert f in fields, f"campo lead mancante: {f}"
        assert not fields[f].is_required(), f"{f} deve restare facoltativo"
    assert fields["email"].is_required()
    # i campi profilati vengono persistiti (non solo accettati)
    src = _src("routers/leads.py")
    for f in ('"phone"', '"city"', '"interests"', '"budget"', '"activity"',
              '"travel"', '"disciplines"', '"venue_type"', '"capacity"'):
        assert f in src


def test_seed_uses_local_photos_and_2027_dates():
    """PL14 — la vetrina di pre-lancio usa foto VERE servite in locale
    (niente picsum/dipendenze esterne) e date tutte nel 2027."""
    seed = _src("scripts/seed_prelaunch_samples.py")
    assert "picsum" not in seed, "foto placeholder esterne tornate nel seed"
    assert "/media/prelaunch/" in seed
    assert seed.count('"2027-') >= 10, "ogni ritiro campione data nel 2027"


def test_seed_samples_translated_in_all_languages():
    """PL18 — OGNI ritiro campione ha name+description in en/de/fr: il
    filtro lingue del marketplace nasconde i prodotti senza traduzione,
    e la vetrina di pre-lancio deve esistere in TUTTE le lingue (in EN
    una directory vuota è peggio di una non tradotta)."""
    seed = _src("scripts/seed_prelaunch_samples.py")
    for lang in ("en", "de", "fr"):
        n = seed.count(f'"{lang}": {{"name"')
        assert n >= 10, f"traduzioni {lang} incomplete nel seed ({n}/10)"
    assert '"translations": translations' in seed


def test_no_stripe_in_public_copy():
    """Scelta founder (10/7): il provider di pagamento non si nomina MAI
    nel copy pubblico — si dice "pagamento diretto online" / "caparra".
    Unica eccezione ammessa: il legal (GDPR impone di nominare i
    sub-responsabili). Guardia sui namespace pubblici ×4 lingue."""
    frontend = Path(__file__).resolve().parent.parent.parent / "frontend" / "src"
    for lang in ("it", "en", "de", "fr"):
        for ns in ("landings", "storefront", "prelaunch"):
            txt = (frontend / "locales" / lang / f"{ns}.json").read_text(
                encoding="utf-8")
            assert "Stripe" not in txt, \
                f"Stripe nel copy pubblico: {lang}/{ns}.json"


def test_prelaunch_directory_noindex_and_honest_preview():
    """PL22 (feedback analista) — in pre-lancio la directory è un'ANTEPRIMA
    onesta, non una finta app funzionante: niente ricerca/filtri su dati
    d'esempio, poche card, CTA verso le landing; e noindex per i motori
    (l'indicizzazione parte al lancio, coi contenuti veri)."""
    src = _src("routers/seo_shell.py")
    assert "prelaunch_mode()" in src
    assert '"noindex": True' in src
    for head in ('"ritiri"', '"operatori"', '"destinazioni"'):
        assert head in src.split("PL22")[1], f"noindex pre-lancio non copre {head}"

    frontend = Path(__file__).resolve().parent.parent.parent / "frontend" / "src"
    cal = (frontend / "features" / "storefront" / "RetreatsCalendarPage.js").read_text(
        encoding="utf-8")
    assert "const { prelaunch } = useSiteConfig();" in cal
    # ricerca hero, categorie e barra filtri spente in pre-lancio
    assert cal.count("!prelaunch &&") >= 3, \
        "regressione: filtri/ricerca tornerebbero visibili sull'anteprima"
    # poche card bastano a raccontare il concept
    assert "items.slice(0, 6)" in cal
    # chiusura onesta: CTA verso le landing lead, non un finto 'mostra altri'
    assert "prelaunchPreviewNote" in cal


def test_operator_landing_transparency_and_direct_contact():
    """PL22 — patti chiari sulla landing operatori: gratis entrare,
    guadagniamo solo su prenotazioni dal calendario pubblico, regole di
    prezzo/cancellazione definite dall'operatore. E un canale diretto
    (mailto info@) accanto ai form, su ENTRAMBE le landing: c'è chi i
    form non li compila, e quel lead vale quanto gli altri."""
    frontend = Path(__file__).resolve().parent.parent.parent / "frontend" / "src"
    op = (frontend / "features" / "prelaunch" / "OperatorLandingPage.js").read_text(
        encoding="utf-8")
    tr = (frontend / "features" / "prelaunch" / "TravelerLandingPage.js").read_text(
        encoding="utf-8")
    assert "mailto:info@aurya.life" in op
    assert "mailto:info@aurya.life" in tr
    assert "pattiTitle" in op
    # i fatti chiave dei patti chiari, tradotti in TUTTE le lingue
    for lang in ("it", "en", "de", "fr"):
        d = (frontend / "locales" / lang / "prelaunch.json").read_text(encoding="utf-8")
        for key in ('"p1q"', '"p2a"', '"p3a"', '"pattiTitle"', '"directT"'):
            assert key in d, f"patti chiari non tradotti: {lang} manca {key}"
    # il fatto centrale (cliente tuo = zero) non deve annacquarsi
    it = (frontend / "locales" / "it" / "prelaunch.json").read_text(encoding="utf-8")
    assert "non paghi nulla" in it


def test_wipe_and_seed_share_the_same_flag():
    """Seed e wipe devono usare lo STESSO marchio, o il wipe lascerebbe
    residui. Guardia contro divergenze."""
    seed = _src("scripts/seed_prelaunch_samples.py")
    assert "is_sample" in seed
