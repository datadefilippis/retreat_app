"""RF (8/10/2026) — Refinement olistico, founder: anteprima SEMPRE nella
copertina del corso, catalogo del profilo a schede, account come hub con una
sezione per ogni cosa (anche vuota, con l'invito), directory /corsi con le
categorie (famiglie delle discipline) scelte alla creazione."""
import json
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
FRONTEND = BACKEND.parent / "frontend" / "src"


class TestCategoriaEDirectory:
    def test_categoria_sul_corso(self):
        from models.course import Course
        assert "categoria" in Course.model_fields
        acc = (BACKEND / "routers" / "accademia.py").read_text()
        assert "def _categoria_valida(slug: Optional[str]) -> Optional[str]:" in acc
        assert "categoria=_categoria_valida(body.categoria)," in acc              # crea
        assert 'upd["categoria"] = _categoria_valida(body.categoria)' in acc     # modifica ("" = via)
        assert '"categoria_label": _etichetta_categoria(course_doc.get("categoria"))' in acc
        assert '"categorie": famiglie_rosa()' in acc                              # la rosa per il wizard
        wiz = (FRONTEND / "features" / "accademia" / "CorsoWizard.js").read_text()
        assert 'data-testid="corso-categoria"' in wiz and "!!form.categoria" in wiz   # obbligatoria alla creazione
        assert "famiglieVive().map(f => <option" in wiz
        scheda = (FRONTEND / "features" / "accademia" / "CorsoPage.js").read_text()
        assert 'data-testid="corso-categoria"' in scheda and "categoria: form.categoria" in scheda

    def test_directory_pubblica(self):
        pub = (BACKEND / "routers" / "public.py").read_text()
        assert '@router.get("/corsi", response_model=PublicCorsiDirectory)' in pub
        corpo = pub.split("async def directory_corsi(")[1].split("\nasync def ")[0]
        # org campione fuori, pagina online obbligatoria, Accademia spenta → via (passa da _operator_corsi)
        assert '"is_sample": {"$ne": True}' in corpo and "org_has_public_home(oid)" in corpo
        assert "for r in await _operator_corsi(oid):" in corpo
        # i conteggi delle categorie NON seguono il filtro di categoria
        assert corpo.index("conteggi[r[\"categoria\"]]") < corpo.index("if categoria:")
        for f in ('if anteprima:', 'if q and q.strip():', 'if ordina == "prezzo":', 'elif ordina == "durata":'):
            assert f in corpo, f
        shell = (BACKEND / "routers" / "seo_shell.py").read_text()
        assert "async def _meta_corsi(categoria: Optional[str] = None) -> dict:" in shell
        assert 'if head == "corsi":' in shell and '"noindex": quanti == 0' in shell.split("async def _meta_corsi")[1].split("async def _meta_frequenza")[0]
        seo = (BACKEND / "routers" / "seo.py").read_text()
        assert 'urls.append(_url(f"{base}/corsi", priority="0.8"))' in seo
        rotte = json.loads((BACKEND / "config" / "rotte.json").read_text())
        assert "corsi" in rotte["pubblica"] and "corsi" not in rotte["solo_con_slug"]
        assert "corsi" in (BACKEND.parent / "deploy" / "nginx" / "nginx.conf").read_text()

    def test_pagina_directory_e_menu(self):
        p = (FRONTEND / "features" / "storefront" / "CorsiDirectoryPage.js").read_text()
        for t in ("corsi-directory", "corsi-categorie", "corsi-cerca", "corsi-ordina", "corsi-anteprima",
                  "corsi-griglia", "corsi-card", "corsi-vuota", "corsi-nessun-risultato"):
            assert f'data-testid="{t}"' in p, t
        assert "storefrontAPI.getCorsiDirectory(params)" in p and "I primi corsi stanno arrivando." in p
        api = (FRONTEND / "api" / "storefront.js").read_text()
        assert "customerApi.get('/api/public/corsi', { params })" in api
        app = (FRONTEND / "App.js").read_text()
        assert 'path="/corsi" element={<CorsiDirectoryPage />}' in app and 'path="/corsi/:categoria"' in app
        shell = (FRONTEND / "features" / "storefront" / "components" / "MarketplaceShell.jsx").read_text()
        # la voce «Corsi» entra nel menu SOLO allo sblocco dell'Accademia
        assert "...(ACCADEMIA_UI_PRONTA ? [{ to: '/corsi', key: 'marketplace.navCorsi', fallback: 'Corsi' }] : [])" in shell
        assert "const navItems = isNetwork ? NETWORK_NAV_ITEMS : NAV_ITEMS;" in shell


class TestScrollAlCambioPagina:
    def test_in_cima_anche_con_ancora(self):
        """RF-ter (8/10): «clicco Comincia e atterro nel footer» — un link con
        un'ancora che non e' un elemento (#lesson-<id>) lasciava lo scroll
        della pagina vecchia. Al cambio di pagina si torna in cima SEMPRE;
        se cambia solo l'hash sulla stessa pagina non si tocca nulla."""
        app = (FRONTEND / "App.js").read_text()
        blocco = app[app.index("function ScrollToTop()"):]
        blocco = blocco[:blocco.index("return null;")]
        assert "const paginaNuova = ultimoPathname.current !== pathname;" in blocco
        assert "if (paginaNuova) window.scrollTo(0, 0);" in blocco
        assert blocco.index("if (paginaNuova) window.scrollTo(0, 0);") < blocco.index("scrollIntoView")


class TestLandingProfiloAccount:
    def test_anteprima_sempre_nella_copertina(self):
        p = (FRONTEND / "features" / "storefront" / "CorsoLandingPage.js").read_text()
        assert "setAnteprima(cc?.trailer ? 'trailer' : (prima ? prima.id : null));" in p
        assert 'data-testid="corso-anteprima-etichetta"' in p and "'In riproduzione' : (l.tipo === 'video' ? 'Guarda gratis' : 'Ascolta gratis')" in p
        assert "onChiudi" not in p                      # niente piu' «Chiudi»: l'anteprima e' la copertina
        assert 'data-testid="corso-landing-categoria"' in p and "to={`/corsi/${c.categoria}`}" in p

    def test_profilo_a_schede(self):
        p = (FRONTEND / "features" / "storefront" / "OperatorProfilePage.js").read_text()
        assert 'data-testid="profile-catalogo"' in p and 'role="tablist"' in p
        for k in ("listino", "ritiri", "prodotti", "corsi"):
            assert f"classeScheda('{k}')" in p, k
        # con una sola categoria niente barra e niente nascosto
        assert "schede.length > 1 && schedaAttiva !== key ? ' hidden' : ''" in p
        # l'hash sceglie la scheda (deep link da landing e email)
        assert "h.startsWith('servizio-')" in p and "h.startsWith('corso-')" in p and "h.startsWith('prodotto-')" in p
        # le esperienze stanno nel catalogo, prima della galleria; il pin IG5 resta
        assert p.index('<section id="ritiri"') < p.index("<Gallery") and "{hasUpcoming && (" in p

    def test_account_hub(self):
        a = (FRONTEND / "features" / "account" / "AccountPage.js").read_text()
        # l'orientamento e' la barra (le tessere in testa sono state tolte l'8/10 sera)
        assert 'data-testid="account-hub"' not in a
        for t in ("hub-esperienze", "hub-corsi", "hub-file", "hub-guide", "hub-meditazioni", "hub-account"):
            assert f"testid: '{t}'" in a, t
        # ogni sezione ha la sua ancora ed esiste anche vuota, con l'invito
        for sid in ("esperienze", "corsi", "file", "guide", "meditazioni", "impostazioni"):
            assert f'id="{sid}"' in a, sid
        assert 'data-testid="account-corsi-vuoto"' in a and 'to="/corsi"' in a
        assert 'data-testid="account-file-vuoto"' in a and 'to="/operatori"' in a
        assert "Array.isArray(corsi) && corsi.length > 0 &&" not in a
        # RF-bis: la barra fissa in basso su telefono con le stesse voci (una lista sola)
        assert 'data-testid="account-barra"' in a and "const vociHub = [" in a and a.count("vociHub.map(") == 1
        assert "lg:hidden" not in a.split('data-testid="account-barra"')[1][:300]      # ovunque, anche desktop
        fav = (FRONTEND / "features" / "frequenze" / "AccountFavorites.js").read_text()
        assert 'data-testid="account-meditations-vuoto"' in fav and "if (!items.length) return null;" not in fav
