"""CR0 (8/10/2026 sera) — LA VIA PER AGGIUNGERE.

docs/PIANO_CREA_RESTYLING_2026-10-08.md. Dopo il lotto ES, /sound/esplora e'
la biblioteca pubblica (senza «+ sessione»): la biblioteca del compositore
(vista explore di FrequenzePage) ha un indirizzo suo, /sound/libreria, e i
link del compositore puntano li'. Il founder: «in Crea ho bisogno di un
facile accesso a suoni e tracce, altrimenti non posso fare mix».
"""
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
FRONTEND = BACKEND.parent / "frontend" / "src"
FQ = FRONTEND / "features" / "frequenze"


class TestLibreria:
    def test_la_libreria_ha_un_indirizzo(self):
        src = (FQ / "FrequenzePage.js").read_text()
        assert "const LIBRERIA = '/sound/libreria';" in src
        assert "const VIEW_PATH = { explore: 'libreria', create: 'crea', impara: 'impara', mine: 'tracce' };" in src
        assert "libreria: 'explore'" in src and "esplora: 'explore'" in src   # entrambi: il vecchio URL non muore
        # il compositore non naviga MAI verso la pubblica per comporre
        for vietato in ("'/sound/esplora?mondo=suoni'", "`/sound/esplora?categoria=", "navigate('/sound/esplora'"):
            assert vietato not in src, vietato
        assert "`${LIBRERIA}?mondo=suoni`" in src and "`${LIBRERIA}?categoria=${CAT_SLUG[cat] || ''}`" in src

    def test_le_fonti_a_un_tocco_in_crea(self):
        src = (FQ / "FrequenzePage.js").read_text()
        # (CR3) le fonti stanno nel banco del mix di CreaVista, non piu' in una riga:
        vista = (FQ / "crea" / "CreaVista.jsx").read_text()
        for tid in ("cr-banco-frequenze", "cr-banco-suoni", "cr-banco-voce", "cr-banco-tracce"):
            assert f'"{tid}"' in vista or f"'{tid.split('-')[-1]}'" in vista, tid
        assert "Torna a <b>Esplora</b>" not in src                      # il vuoto non manda piu' fuori

    def test_la_barra_delle_stanze_sa_della_libreria(self):
        barra = (FQ / "StanzeSound.jsx").read_text()
        assert "const LIBRERIA = ['esplora', 'Libreria', '/sound/libreria'];" in barra
        assert "libreria = false" in barra and "libreria ? [LIBRERIA, ...STANZE.slice(1)] : STANZE" in barra
        assert "'/sound/esplora'" in barra                                 # il pubblico (Lab) la tiene
        page = (FQ / "FrequenzePage.js").read_text()
        assert "<StanzeSound creaBadge={layers.length} libreria={canCompose}" in page
        # la pubblica non cambia
        assert "libreria" not in (FQ / "esplora" / "BibliotecaPage.jsx").read_text().lower().replace("biblioteca", "")

    def test_la_libreria_non_si_indicizza(self):
        shell = (BACKEND / "routers" / "seo_shell.py").read_text()
        assert 'if sub in ("crea", "tracce", "libreria", "visual", "pro"):' in shell
