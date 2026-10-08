"""Lotto ES (8/10/2026 sera) — AURYA SOUND / ESPLORA, semplice e immediato.

docs/PIANO_ESPLORA_SOUND_2026-10-08.md. Decisioni del founder: un suono alla
volta per il pubblico; famiglie prima e schede dopo; fondamenta a capitoli;
niente «meditazioni che usano questa frequenza». Le pagine nuove vivono
accanto al compositore (FrequenzePage intatta, dietro SOUND_ESPLORA_NUOVA).
"""
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
FRONTEND = BACKEND.parent / "frontend" / "src"
FQ = FRONTEND / "features" / "frequenze"
ES = FQ / "esplora"


class TestMappa:
    def test_pagine_proprie_dietro_flag(self):
        assert "export const SOUND_ESPLORA_NUOVA = true;" in (FQ / "stato.js").read_text()
        app = (FRONTEND / "App.js").read_text()
        assert '{SOUND_ESPLORA_NUOVA && <Route path="/sound/esplora" element={<BibliotecaPage />} />}' in app
        assert '{SOUND_ESPLORA_NUOVA && <Route path="/sound/impara" element={<FondamentaPage />} />}' in app
        assert '{SOUND_ESPLORA_NUOVA && <Route path="/sound/impara/glossario" element={<FondamentaPage />} />}' in app
        # le pagine nuove stanno PRIMA del catch-all del compositore, che resta
        assert app.index('path="/sound/esplora" element={<BibliotecaPage />}') < app.index('path="/sound/*"')
        assert 'path="/sound/*" element={<FrequenzePage />}' in app

    def test_un_selettore_a_tre(self):
        sel = (ES / "SelettoreTre.jsx").read_text()
        for porta in ("['frequenze', 'Frequenze', '/sound/esplora']", "['fondamenta', 'Fondamenta', '/sound/impara']", "['lab', 'Lab', '/sound/lab']"):
            assert porta in sel, porta
        for f in ("BibliotecaPage.jsx", "FondamentaPage.jsx"):
            assert "<SelettoreTre attiva=" in (ES / f).read_text(), f
        assert '<SelettoreTre attiva="frequenze" />' in (FQ / "SchedaBibliotecaPage.jsx").read_text()
        lab = (FQ / "lab" / "LabSala.jsx").read_text()
        assert '{SOUND_ESPLORA_NUOVA ? <SelettoreTre attiva="lab" /> : <StanzeSound attiva="lab" />}' in lab
        # niente stanze, niente «Le mie tracce», niente basi, niente trigger nel pubblico nuovo
        bib = (ES / "BibliotecaPage.jsx").read_text()
        for vietato in ("StanzeSound", "TriggerStudio", "worldswitch", "Le mie tracce", "+ Sessione", "Controindicazioni"):
            assert vietato not in bib, vietato

    def test_una_fonte_per_i_testi(self):
        testi = (FQ / "content" / "biblioteca_testi.js").read_text()
        for v in ("export const FAMIGLIE", "export const CAT_INTRO", "export const HOWTO_BODY", "export const GRADI", "export const METODI_CHIAVE"):
            assert v in testi, v
        fp = (FQ / "FrequenzePage.js").read_text()
        assert "import { CAT_HINT, CAT_INTRO, HOWTO_BODY } from './content/biblioteca_testi';" in fp
        assert "const CAT_INTRO = {" not in fp and "const HOWTO_BODY = " not in fp


class TestBiblioteca:
    def test_famiglie_prima_schede_dopo(self):
        bib = (ES / "BibliotecaPage.jsx").read_text()
        assert 'data-testid="esp-famiglie"' in bib and 'data-testid={`esp-famiglia-${f.slug}`}' in bib
        assert "famigliaDaSlug(params.get('famiglia'))" in bib and 'data-testid="esp-torna"' in bib
        assert 'data-testid="esp-scheda"' in bib and 'data-testid="esp-play"' in bib
        # le informazioni al posto giusto: la legenda nel foglio ⓘ, la chiave dei metodi solo in Metodi
        assert 'data-testid="esp-info-foglio"' in bib and "famiglia.slug === 'metodi'" in bib
        # la scheda si apre dal titolo e porta con se' la famiglia (il «←» sa tornare)
        assert "`/sound/esplora/${slug}${famiglia ? `?famiglia=${famiglia.slug}` : ''}`" in bib

    def test_un_suono_alla_volta(self):
        ant = (ES / "anteprima.js").read_text()
        assert "import { startCardLive } from '../engine/synth';" in ant
        assert "export const ANTEPRIMA_SEC = 60;" in ant
        assert "const suonaDavvero = useCallback(async (s) => {\n    ferma();" in ant      # prima di suonare, si ferma l'altra
        assert "guard(suonaDavvero)" in ant                                                # il sipario prima del primo suono
        assert "if (sec >= ANTEPRIMA_SEC) ferma();" in ant
        barra = (ES / "BarraAnteprima.jsx").read_text()
        assert 'data-testid="barra-anteprima"' in barra and 'data-testid="barra-anteprima-ferma"' in barra


class TestSchedaEFondamenta:
    def test_scheda(self):
        src = (FQ / "SchedaBibliotecaPage.jsx").read_text()
        for tid in ("scheda-briciole", "scheda-testo", "scheda-lab", "scheda-sorelle", "scheda-ascolta", "scheda-famiglia", "scheda-torna-famiglia"):
            assert f'data-testid="{tid}"' in src, tid
        assert "onClick={() => anteprima.toggle(scheda)}" in src       # si ascolta qui, non si torna in biblioteca
        assert "<BarraAnteprima anteprima={anteprima}" in src and "{anteprima.curtain}" in src
        assert "meditazioni che" not in src.lower()                    # decisione 4: no

    def test_fondamenta_a_capitoli(self):
        src = (ES / "FondamentaPage.jsx").read_text()
        assert "import GuidaView from '../GuidaView';" in src           # la guida resta intatta
        assert "import { PERCORSO } from '../content/guida';" in src
        assert 'data-testid="fondamenta-capitoli"' in src and 'data-testid={`fondamenta-cap-${p.id}`}' in src
        assert "new IntersectionObserver(" in src and 'data-testid="fondamenta-prossimo"' in src
        assert "const glossario = /\\/glossario\\/?$/.test(pathname);" in src
        css = (ES / "esplora.css").read_text()
        assert ".fqz.fondamenta .gd-nav,.fqz.fondamenta .gd-path{display:none}" in css
        assert ".fqz .sel-tre{position:sticky" in css
