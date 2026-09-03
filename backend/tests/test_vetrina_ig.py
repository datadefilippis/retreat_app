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


DASH = FE / "features" / "dashboard"


class TestDashboardIG4:
    """IG4 (3/9/2026) — la home operatore si legge in un colpo, dall'alto:
    numeri del mese, cose da fare, agenda e andamento. Il founder ha
    scartato il saluto «Benvenuta, {nome}» («e se si tratta di un
    uomo?»): la riga di apertura e' la data, uguale per tutti. Le
    tessere sono INSIGHT del nostro sistema, non i numeri del mockup."""

    def test_nessun_saluto_con_genere(self):
        home = (DASH / "OperatorHome.js").read_text()
        assert "Benvenut" not in home and "Bentornat" not in home, \
            "un saluto declinato sbaglia genere: la riga di apertura e' la data"
        assert 'data-testid="home-oggi"' in home

    def test_i_numeri_del_mese_prima_di_tutto(self):
        home = (DASH / "OperatorHome.js").read_text()
        ordine = [home.index(k) for k in (
            'data-testid="home-panoramica"', 'data-testid="home-dafare"',
            'data-testid="home-ritiri"', 'data-testid="home-andamento"')]
        assert ordine == sorted(ordine), \
            "gerarchia: Questo mese → Da fare → Prossimi ritiri → Andamento"
        for tile in ("tile-incassato", "tile-in-arrivo", "tile-prenotazioni", "tile-visite"):
            assert f'testid="{tile}"' in home

    def test_stesse_sei_fonti_nessuna_chiamata_nuova(self):
        home = (DASH / "OperatorHome.js").read_text()
        for ep in ("/event-occurrences/admin/list", "/orders/payments-overview",
                   "/analytics/cashflow", "/reviews",
                   "/organizations/current/onboarding-status", "/analytics/visibility"):
            assert ep in home
        assert home.count("api.get(") == 6, "IG4 e' pelle: nessuna chiamata in piu'"

    def test_visibilita_spenta_niente_zero_finto(self):
        """Il modulo commerce puo' essere spento (403): le tessere del
        mese spariscono, come faceva la vecchia card. Mai uno zero finto."""
        home = (DASH / "OperatorHome.js").read_text()
        assert "visRes.value.data || {}) : false" in home
        assert "visAvailable && (" in home

    def test_il_grafico_non_mostra_il_futuro_a_zero(self):
        home = (DASH / "OperatorHome.js").read_text()
        assert "months.filter((m) => m.month <= ym)" in home, \
            "i 3 secchi futuri del cashflow sembravano un crollo"

    def test_posti_come_barra_e_chiavi_italiane(self):
        import json
        home = (DASH / "OperatorHome.js").read_text()
        assert "reserved_seats" in home and "style={{ width: `${pct}%` }}" in home
        it = json.loads((FE / "locales" / "it" / "dashboard.json").read_text())["home"]
        for k in ("overview_title", "tile_collected", "tile_collected_sub", "tile_expected_sub",
                  "tile_overdue_sub", "delta_same", "delta_vs", "seats", "trend_title", "avg_ticket"):
            assert k in it, f"chiave italiana mancante: {k}"
