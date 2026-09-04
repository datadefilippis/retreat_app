"""
SITO IMMEDIATO (3/9/2026, docs/SITO_IMMEDIATO_PIANO_2026-09.md) —
«meno parole, piu' persone». Il founder: un'operatrice ha trovato il
sito bello ma con troppe informazioni; la diagnosi misurata e'
RIDONDANZA (il perche' ripetuto in cinque pagine). Queste guardie
fissano le decisioni delle onde man mano che entrano.

SR1 — La Rete diventa la directory: /operatori rende la pagina esplora
in ogni fase, /esplora-operatori rimanda, il menu dice
«Professionisti», la copertina nomina la rete senza ripetere il
Manifesto. Regola di visibilita' scelta dal founder (3/9): profili
PUBBLICATI e non esclusi (regola esplora), «Verificato» come segno
della cura; network_member non e' un cancello.
SR3 — header a quattro voci: Professionisti · Magazine · Sound · Chi
siamo (+ pill Per i professionisti); Meditazioni dentro Sound,
Manifesto dentro Chi siamo e nel footer.
"""
import json
from pathlib import Path

FE = Path(__file__).resolve().parents[1].parent / "frontend" / "src"
BACKEND = Path(__file__).resolve().parents[1]
STORE = FE / "features" / "storefront"


class TestSr1Directory:
    def test_operatori_e_la_directory_in_ogni_fase(self):
        app = (FE / "App.js").read_text()
        i = app.index("function OperatorsGate()")
        gate = app[i:app.index("\n}\n", i)]
        assert "NetworkOperatorsPage" not in gate, \
            "il gate rende ancora il racconto della rete"
        assert "<OperatorsIndexPage />" in gate
        assert "sitePhase === 'network'" not in gate

    def test_esplora_operatori_rimanda_a_operatori(self):
        app = (FE / "App.js").read_text()
        assert 'path="/esplora-operatori" element={<EsploraOperatoriRedirect />}' in app
        assert 'path="/esplora-operatori/:categoria" element={<EsploraOperatoriRedirect />}' in app
        i = app.index("function EsploraOperatoriRedirect()")
        assert "`/operatori/${categoria}`" in app[i:i + 400]

    def test_la_pagina_vive_su_operatori_con_dati_veri(self):
        page = (STORE / "OperatorsIndexPage.js").read_text()
        assert "const basePath = '/operatori'" in page
        assert "q.preview = 1;" in page, "lo specchio di fase svuoterebbe la directory"
        assert "isPreview" not in page
        assert "PrelaunchBanner" not in page.split("const OperatorsMapView")[0].replace("import", ""), \
            "niente banner «d'esempio»: i dati sono veri"
        assert "canonicalPath: categoria ? `/operatori/${categoria}` : '/operatori'" in page

    def test_la_copertina_nomina_la_rete_una_volta_sola(self):
        page = (STORE / "OperatorsIndexPage.js").read_text()
        it = json.loads((FE / "locales" / "it" / "landings.json").read_text())["operators"]
        assert it["pageTitle"] == "I professionisti della rete Aurya"
        assert "una per una" in it["subtitle"]
        assert "stiamo costruendo" not in it["subtitle"].lower(), \
            "il «stiamo costruendo» vive nel Manifesto, non qui"
        assert 'data-testid="operators-how-born"' in page and 'to="/manifesto"' in page
        assert "<BrandPayoff" in page, "il payoff di brand resta sopra ogni hero (regola RB)"

    def test_il_menu_dice_professionisti_non_la_rete(self):
        shell = (STORE / "components" / "MarketplaceShell.jsx").read_text()
        i = shell.index("const NETWORK_NAV_ITEMS")
        blocco = shell[i:shell.index("];", i)]
        voci = [l for l in blocco.splitlines() if l.strip().startswith("{ to:")]
        assert [v.split("'")[1] for v in voci] == ["/operatori", "/blog", "/sound", "/chi-siamo"], \
            "SR3: quattro voci, Professionisti per prima"
        assert "navNetwork'" not in shell and "'La Rete'" not in shell
        assert "footer-nw-operatori" in shell
        j = shell.index('data-testid="footer-nw-operatori"')
        assert "marketplace.navOperators" in shell[j:j + 200]

    def test_la_shell_seo_serve_la_directory_su_operatori(self):
        src = (BACKEND / "routers" / "seo_shell.py").read_text()
        i = src.index("async def _meta_operators_index")
        corpo = src[i:src.index("async def _meta_esplora_operatori")]
        assert "return await _meta_esplora_operatori(category)" in corpo
        assert "network_member" not in corpo, "la shell non filtra piu' per membri della rete"
        j = src.index("async def _meta_esplora_operatori")
        assert 'canonical = f"{base}/operatori"' in src[j:j + 1500]
        assert 'href="/esplora-operatori"' not in src

    def test_sr2_home_la_porta_di_casa_e_la_directory(self):
        """SR2 — hero: la primaria porta ai professionisti; la card
        Professionisti non dice piu' «stiamo costruendo» (vive nel
        Manifesto); il perche' e' l'antitesi in due righe + la porta;
        la sezione professionisti chiude con l'invito e UNA porta."""
        home = (FE / "features" / "network" / "NetworkHomePage.js").read_text()
        i = home.index('data-testid="hp-hero-cta"')
        assert "NETWORK_PATH" in home[i - 200:i]
        assert "stiamo costruendo" not in home[home.index("id: 'professionisti'"):home.index("id: 'esperienze'")].lower()
        why = home[home.index('data-testid="hp-why"'):home.index('data-testid="hp-why-cta"')]
        for k in ("whyP1", "whyP4", "whyP5", "whyP6"):
            assert f"nwHome.{k}" not in why, f"il perche' per esteso ({k}) vive nel Manifesto"
        pros = home[home.index('data-testid="hp-pros"'):home.index('data-testid="hp-letter"')]
        assert "nwHome.prosP4" not in pros and "hp-pros-cta-alt" not in pros
        it = json.loads((FE / "locales" / "it" / "landings.json").read_text())["nwHome"]
        assert it["heroCta"] == "Scopri i professionisti"
        assert "stiamo costruendo" not in it["pillarProText"].lower()
        # la shell SSR dice quello che dice la pagina
        shell = (BACKEND / "routers" / "seo_shell.py").read_text()
        assert "Stiamo costruendo una rete di professionisti" not in shell
        assert "c['whyP4']" not in shell and "c['prosP4']" not in shell

    def test_sr5_faq_della_landing_si_aprono_una_alla_volta(self):
        landing = (FE / "features" / "prelaunch" / "OperatorLandingPage.js").read_text()
        blocco = landing[landing.index('data-testid="ol-faq"'):landing.index('data-testid="ol-who"')]
        assert "<details" in blocco and "<summary" in blocco, \
            "le FAQ restano nel DOM ma si aprono una alla volta"
        assert "{f.a}" in blocco, "la risposta deve restare nel DOM per i crawler"

    def test_nessun_link_interno_dice_ancora_la_rete_come_destinazione(self):
        """I link a /operatori restano (l'URL e' stabile): cambiano le
        etichette che promettevano «la rete» come pagina-racconto."""
        blog = (STORE / "BlogIndexPage.js").read_text()
        assert "Conosci la rete" not in blog
        interview = (STORE / "OperatorInterviewPage.js").read_text()
        assert "navNetworkMembers" not in interview
