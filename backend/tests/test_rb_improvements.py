"""Ciclo RB — improvement round (2026-07-07, feedback founder).

RB1: salvare un evento pubblicato senza cambiarne lo stato NON è una
transizione — il form manda sempre lo status corrente e il 400
"published → published" bloccava la modifica di data/luogo.
"""

import os
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-not-for-production")
os.environ.setdefault("MONGO_URL", "mongodb://localhost:27017")
os.environ.setdefault("DB_NAME", "test_db")


class TestOccurrenceEditRb1:

    def test_same_status_is_idempotent_noop(self):
        """status invariato = no-op valido, per OGNI stato (anche
        cancelled: risalvare i campi non è una transizione)."""
        from services.commerce_rules import validate_occurrence_transition
        for status in ("draft", "published", "closed", "cancelled"):
            ok, reason = validate_occurrence_transition(status, status)
            assert ok, f"{status}→{status} deve essere no-op, non errore"

    def test_real_transitions_still_enforced(self):
        from services.commerce_rules import validate_occurrence_transition
        ok, _ = validate_occurrence_transition("published", "draft")
        assert ok
        ok, reason = validate_occurrence_transition("cancelled", "published")
        assert not ok          # cancelled resta terminale
        assert "Transizione" in reason


class TestReviewChannelAgnosticRb2:
    """RB2 — la recensione verificata vale per acquisti da QUALSIASI
    canale (store proprio, directory, manuale, POS): il gate guarda
    solo che esista un ordine reale, mai il sales_channel. E l'email
    non compare mai in pubblico: è solo la chiave OTP (hashata)."""

    def test_gate_has_no_channel_filter(self):
        import inspect
        from services import review_service as rs
        src = inspect.getsource(rs.has_orders_with_org)
        assert "sales_channel" not in src
        assert '"draft", "cancelled"' in src   # esclusi solo i non-ordini

    def test_public_review_never_exposes_email(self):
        """La proiezione pubblica espone author_name/verified, mai
        l'email; nell'OTP store vive solo l'hash."""
        src = (BACKEND_DIR / "services" / "review_service.py").read_text()
        assert "email_hash" in src
        idx = src.index('"author_name"')
        # nella proiezione pubblica non c'è il campo email in chiaro
        assert '"email":' not in src[idx - 500:idx + 500]


FRONTEND_SRC = BACKEND_DIR.parent / "frontend" / "src"
LANGS = ("it", "en", "de", "fr")


class TestCopyRulesRb4:
    """RB4 — le regole del copy (docs/BRAND_AURYA.md): zero trattini
    lunghi nei testi pubblici, nessuna geografia imposta, il motto
    come filo d'oro in font-brand."""

    def test_no_em_dash_in_public_copy(self):
        """Il namespace pubblico (landings) non contiene trattini
        lunghi in NESSUNA lingua."""
        import json as _json
        for lang in LANGS:
            raw = (FRONTEND_SRC / "locales" / lang / "landings.json").read_text()
            assert "—" not in raw, f"{lang}/landings.json: trattino lungo residuo"

    def test_no_geography_branding_in_hero_and_tagline(self):
        import json as _json
        for lang in LANGS:
            data = _json.loads((FRONTEND_SRC / "locales" / lang
                                / "landings.json").read_text())
            hero = data["calendar"]["title"] + data["calendar"]["subtitle"]
            tagline = data["marketplace"]["tagline"]
            for token in ("Itali", "Italy", "Italien", "Italie"):
                assert token not in hero, f"{lang}: geografia nell'hero"
                assert token not in tagline, f"{lang}: geografia nella tagline"

    def test_motto_overline_in_brand_font(self):
        """Connect · Heal · Grow in font-brand (Cinzel, oro) su hero,
        sezioni valore e pagine istituzionali."""
        for rel in ("features/storefront/RetreatsCalendarPage.js",
                    "features/storefront/components/MarketplaceValueSections.jsx",
                    "features/storefront/AboutAuryaPage.js",
                    "features/storefront/HowItWorksPage.js"):
            src = (FRONTEND_SRC / rel).read_text()
            assert "Connect · Heal · Grow" in src, f"{rel}: overline mancante"
            assert "font-brand" in src

    def test_scroll_to_top_on_route_change(self):
        """RB3 — la SPA riparte dall'alto al cambio pagina; i cambi di
        sola query (filtri) non scrollano."""
        app = (FRONTEND_SRC / "App.js").read_text()
        assert "function ScrollToTop" in app
        assert "<ScrollToTop />" in app
        idx = app.index("function ScrollToTop")
        assert "[pathname]" in app[idx:idx + 600]
