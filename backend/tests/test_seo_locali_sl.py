"""SEO-A/B/C/E (14/9/2026 sera) — dall'analisi SEO della piattaforma
(docs/ANALISI_SEO_PIATTAFORMA_2026-09-14.md).

B: pagine locali /operatori/{disciplina}[/{regione}] e /operatori/{regione},
   indicizzabili solo sopra la soglia, una verita' sola (services/pagine_locali)
   per shell e client. A: igiene (/magazine 301, barra finale, sitemap,
   lunghezze). C: profilo (description dalla bio, @id, «Vedi anche»).
   E: Sentry e pagine commerce fuori dal bundle iniziale.
"""
import json
import re
from pathlib import Path

from services import pagine_locali as pl

BACKEND = Path(__file__).resolve().parents[1]
ROOT = BACKEND.parent
FE = ROOT / "frontend" / "src"


class TestRisolutore:
    def test_disciplina_regione_categoria(self):
        assert pl.risolvi("yoga") == {"disciplina": "yoga", "regione": None, "categoria": None, "valida": True}
        assert pl.risolvi("puglia")["regione"] == "Puglia"
        assert pl.risolvi("yoga", "puglia") == {"disciplina": "yoga", "regione": "Puglia", "categoria": None, "valida": True}
        assert pl.risolvi("valle-d-aosta")["regione"] == "Valle d'Aosta"
        assert pl.risolvi("servizi")["categoria"] == "servizi"      # legacy: sottoinsieme, canonico /operatori
        assert pl.risolvi("yoga", "marte")["valida"] is False
        assert pl.risolvi("puglia", "yoga")["valida"] is False
        assert pl.risolvi(None) == {"disciplina": None, "regione": None, "categoria": None, "valida": True}

    def test_percorso_e_briciole(self):
        assert pl.percorso("yoga", "Puglia") == "/operatori/yoga/puglia"
        assert pl.percorso(None, "Friuli-Venezia Giulia") == "/operatori/friuli-venezia-giulia"
        assert pl.percorso(None, None) == "/operatori"
        assert [n for n, _ in pl.briciole("yoga", "Puglia")] == ["Aurya", "Professionisti", "Yoga", "Puglia"]

    def test_nessuna_collisione_fra_discipline_e_regioni(self):
        from models.disciplines import DISCIPLINES
        assert not set(DISCIPLINES) & set(pl.REGIONE_DA_SLUG)


class TestSogliaEMeta:
    PROFILI = [
        {"disciplines": ["yoga", "reiki"], "sedi": [{"citta": "Lecce", "regione": "Puglia"}]},
        {"disciplines": ["yoga"], "sedi": [{"citta": "Bari", "regione": "Puglia"}]},
        {"disciplines": ["yoga"], "city": "Ostuni", "region": "Puglia"},        # non migrato: vale lo stesso
        {"disciplines": ["shiatsu"], "sedi": [{"citta": "Milano", "regione": "Lombardia"}]},
    ]

    def test_conteggi_e_indicizzabili(self):
        c = pl.conteggi(self.PROFILI)
        assert c[("yoga", None)] == 3 and c[("yoga", "Puglia")] == 3 and c[(None, "Puglia")] == 3
        assert c[("reiki", None)] == 1 and c[(None, "Lombardia")] == 1
        assert pl.SOGLIA == 3
        assert pl.indicizzabili(self.PROFILI) == [(None, "Puglia", 3), ("yoga", None, 3), ("yoga", "Puglia", 3)]

    def test_titoli_con_la_preposizione_giusta(self):
        assert pl.meta("yoga", "Puglia", 3)["title"] == "Yoga in Puglia: operatori e professionisti | Aurya"
        assert pl.meta(None, "Lazio", 3)["h1"] == "Operatori olistici nel Lazio"
        assert pl.meta(None, "Marche", 3)["title"].startswith("Operatori olistici nelle Marche")
        assert pl.meta("yoga", None, 3)["h1"] == "Yoga in Italia"
        assert pl.meta(None, None, 9)["title"] == "Operatori olistici e professionisti del benessere in Italia | Aurya"

    def test_sotto_soglia_noindex_e_niente_link_dal_profilo(self):
        assert pl.meta("yoga", "Puglia", 2)["indicizzabile"] is False
        assert pl.meta("yoga", "Puglia", 3)["indicizzabile"] is True
        assert pl.meta(None, None, 0)["indicizzabile"] is False
        c = pl.conteggi(self.PROFILI)
        link = pl.pagine_per_profilo(self.PROFILI[0], c)
        assert [l["path"] for l in link] == ["/operatori/yoga/puglia", "/operatori/yoga", "/operatori/puglia"]
        assert pl.pagine_per_profilo(self.PROFILI[3], c) == []       # Lombardia: 1 solo, mai un link a una noindex

    def test_lunghezze_seo(self):
        for d, r in (("yoga", "Puglia"), ("costellazioni-familiari", "Friuli-Venezia Giulia"), (None, "Trentino-Alto Adige"), ("sound-healing", None)):
            m = pl.meta(d, r, 3)
            assert len(m["title"]) <= 70, m["title"]
            assert 90 <= len(m["description"]) <= 165, m["description"]


class TestDoveVive:
    SHELL = (BACKEND / "routers" / "seo_shell.py").read_text()
    PUB = (BACKEND / "routers" / "public.py").read_text()
    SEO = (BACKEND / "routers" / "seo.py").read_text()

    def test_shell_directory_usa_il_servizio(self):
        corpo = self.SHELL[self.SHELL.index("async def _meta_esplora_operatori("):self.SHELL.index("async def _meta_esperienze(")]
        assert "_pl.risolvi(categoria, sub)" in corpo and 'if not ris["valida"]:\n        return None' in corpo
        assert '"noindex": not pagina["indicizzabile"]' in corpo
        assert "_pl.briciole(disciplina, regione)" in corpo
        assert "if len(parts) > 3:\n            return None" in self.SHELL

    def test_api_directory_regione_e_pagina(self):
        idx = self.PUB[self.PUB.index("async def public_operators_index("):self.PUB.index("async def _operator_listino")]
        assert "regione: str = Query(default=None, max_length=40)" in idx
        assert '"regioni": all_regioni' in idx and '"pagina": (_pl.meta(' in idx
        assert '"pagine_locali": _pl.pagine_per_profilo(pp, await _pl.contatori_locali())' in self.PUB

    def test_sitemap_igiene(self):
        assert '_url(f"{base}/cerca-ritiro", priority="0.8")' in self.SEO
        assert self.SEO.count("_pl.indicizzabili(await _pl.profili_pubblici())") == 2
        assert 'path = f"/esperienze/{cat}"' in self.SEO and 'f"/ritiri/{cat}"' not in self.SEO

    def test_rimandi_e_barra_finale(self):
        reg = json.loads((BACKEND / "config" / "rotte.json").read_text())
        assert reg["rimandi"]["magazine"] == "/blog"
        nginx = (ROOT / "deploy" / "nginx" / "nginx.conf").read_text()
        assert "location ~ ^/magazine/?$ { return 301 /blog; }" in nginx
        assert "location ~ ^/(?!api/|uploads/|static/|media/|__seo/)(.+)/$ { return 301 /$1$is_args$args; }" in nginx
        gen = (BACKEND / "scripts" / "genera_rotte_nginx.py").read_text()
        assert "$is_args$args" in gen

    def test_profilo_description_e_id(self):
        corpo = self.SHELL[self.SHELL.index("async def _meta_operator("):self.SHELL.index("async def _meta_link_page")]
        assert "len(_tag) >= 80" in corpo and '"@id": canonical' in corpo
        assert "_taglia_description(" in corpo, "la description del profilo si ferma a ~155 caratteri"
        from routers.seo_shell import _taglia_description
        assert _taglia_description("a" * 100) == "a" * 100
        lunga = _taglia_description("parola " * 40)
        assert len(lunga) <= 156 and lunga.endswith("…") and not lunga[:-1].endswith(" ")
        assert "_pl.pagine_per_profilo(profile, await _pl.contatori_locali())" in corpo
        assert "Vedi anche: " in corpo

    def test_titoli_e_description_delle_pagine_brand_nella_misura(self):
        blocco = self.SHELL[self.SHELL.index("_BRAND_PAGES = {"):self.SHELL.index("def _meta_brand_page")]
        # senza eseguire codice: si misurano i literal
        for m in re.finditer(r'"title": "([^"]+)"', blocco):
            assert len(m.group(1)) <= 72, m.group(1)   # /entra-nella-rete ha 72: e' il tetto
        for m in re.finditer(r'"description": \(((?:\s*"[^"]*"\s*)+)\)', blocco):
            testo = "".join(re.findall(r'"([^"]*)"', m.group(1)))
            assert len(testo) <= 165, testo[:80]
        assert '"title": "Chi siamo: le persone dietro Aurya | Aurya"' in blocco

    def test_evento_titolo_corto(self):
        assert 'if len(title) > 65 and when:' in self.SHELL


class TestClient:
    def test_directory_legge_la_pagina_dal_backend(self):
        src = (FE / "features" / "storefront" / "OperatorsIndexPage.js").read_text()
        assert "risolviSegmenti(seg1, seg2)" in src and "if (regione) q.regione = regione;" in src
        assert "title: data?.pagina?.title" in src and "canonicalPath: data?.pagina?.path || '/operatori'" in src
        assert 'data-testid="operators-region-filter"' in src
        assert "'Professionisti del benessere in Italia | Aurya'" not in src, "titolo diverso dalla shell (gap G2)"
        lib = (FE / "lib" / "pagineLocali.js").read_text()
        assert "export function risolviSegmenti" in lib and "export function percorsoLocale" in lib
        app = (FE / "App.js").read_text()
        assert '<Route path="/operatori/:categoria/:sub" element={<OperatorsGate />} />' in app

    def test_profilo_vedi_anche_e_description(self):
        src = (FE / "features" / "storefront" / "OperatorProfilePage.js").read_text()
        assert 'data-testid="profile-vedi-anche"' in src and "data.pagine_locali" in src
        assert ".trim().length >= 80 ? data.tagline : (data.bio || data.tagline)" in src

    def test_bundle_iniziale_snello(self):
        app = (FE / "App.js").read_text()
        for nome in ("StorefrontPage", "AccountPage", "ProductLandingPage", "CourseLandingPage", "CustomerCoursePlayerPage"):
            assert f'const {nome} = lazy(' in app, f"{nome} deve essere lazy (SEO-E)"
        oss = (FE / "observability" / "index.js").read_text()
        assert 'import(/* webpackChunkName: "osservabilita" */ "./sentry")' in oss
        assert "requestIdleCallback" in oss
        assert not re.search(r'^import .*@sentry', oss, re.M)
