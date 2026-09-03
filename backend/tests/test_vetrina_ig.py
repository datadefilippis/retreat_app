"""
CICLO IG (3/9/2026) — il profilo mobile da vetrina (per il carosello
Instagram del founder). SOLO PELLE: nessuna logica, nessuna API,
nessun campo nuovo. Piano in docs/VETRINA_MOBILE_PLAN_2026-09.md.

Vincolo del founder: ogni operatore carica foto di dimensioni
diverse e devono vedersi bene per TUTTI — quindi mai un layout
guidato dalla proporzione della foto.
"""
from pathlib import Path

FE = Path(__file__).resolve().parents[1].parent / "frontend" / "src"
STORE = FE / "features" / "storefront"


class TestFotoRobuste:
    def test_l_avatar_e_sempre_tondo_e_ritagliato(self):
        """Qualunque proporzione la foto abbia: cerchio + object-cover
        col fuoco alto (le teste dei ritratti verticali restano)."""
        src = (STORE / "components" / "OperatorIdentityHeader.jsx").read_text()
        assert "rounded-full" in src and "object-cover" in src
        assert "object-[center_25%]" in src, \
            "senza il fuoco alto le foto verticali tagliano il volto"

    def test_la_cover_e_una_banda_ad_altezza_fissa(self):
        src = (STORE / "components" / "OperatorIdentityHeader.jsx").read_text()
        assert "h-44" in src and "object-cover" in src, \
            "la cover deve avere altezza fissa: mai il layout che balla"
        assert "identity-card" in src, "manca la card d'identita'"

    def test_via_la_fotona_a_grandezza_naturale(self):
        """Il ritratto non vive piu' nell'aside a dimensione naturale
        (era il difetto: uno screenshot = una foto). Entra in galleria."""
        src = (STORE / "OperatorProfilePage.js").read_text()
        assert "w-full h-auto max-h-96 object-contain" not in src, \
            "la fotona a proporzione naturale e' tornata nell'aside"


class TestVetrinaMockup:
    def test_la_cta_prenota_e_lo_sticky(self):
        src = (STORE / "OperatorProfilePage.js").read_text()
        assert 'data-testid="profile-cta-prenota"' in src
        assert 'data-testid="profile-cta-sticky"' in src
        assert "bookSession" in src and "#listino" in src

    def test_il_prezzo_e_in_evidenza(self):
        src = (STORE / "OperatorProfilePage.js").read_text()
        assert "text-base font-bold text-[#376254]" in src, \
            "il prezzo deve risaltare come nei mockup"

    def test_il_calendario_vive_sui_dati_esistenti(self):
        cal = (STORE / "components" / "MiniCalendario.jsx").read_text()
        assert "upcoming" in cal, "il calendario usa i dati che il profilo GIA' riceve"
        assert "if (!quadro) return null" in cal, \
            "agenda vuota = niente calendario (mai una griglia vuota)"
        # zero chiamate: e' solo disegno
        assert "fetch(" not in cal and "api." not in cal.lower()
        pagina = (STORE / "OperatorProfilePage.js").read_text()
        assert "<MiniCalendario" in pagina
