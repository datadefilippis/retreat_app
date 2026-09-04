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

    def test_nessun_link_interno_dice_ancora_la_rete_come_destinazione(self):
        """I link a /operatori restano (l'URL e' stabile): cambiano le
        etichette che promettevano «la rete» come pagina-racconto."""
        blog = (STORE / "BlogIndexPage.js").read_text()
        assert "Conosci la rete" not in blog
        interview = (STORE / "OperatorInterviewPage.js").read_text()
        assert "navNetworkMembers" not in interview
