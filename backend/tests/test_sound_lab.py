"""SOUND LAB — STEP 0+1 (25/8/2026): il telaio e il Generatore.

Il Lab e' un motore solo che crescera' (oscilloscopio, spettro, sweep,
poi il microfono): queste guardie tengono le TRE regole architetturali
che rendono possibile quel futuro, piu' le trappole gia' pagate una
volta (il 404 della shell su /sound/visual, il canale iOS).

Piano: docs/SOUND_LAB_PIANO_2026-08.md
"""
import re
from pathlib import Path

import pytest

BACKEND_DIR = Path(__file__).resolve().parents[1]
FRONTEND_SRC = BACKEND_DIR.parent / "frontend" / "src"
LAB = FRONTEND_SRC / "features" / "frequenze" / "lab"


class TestArchitettura:
    """Le tre regole del motore: React fuori, il ponte come unico
    sbocco, l'analisi come ospite."""

    def test_il_motore_e_libero_da_react(self):
        """Il suono vive in un modulo JS puro (come prototipo.js):
        se React entra nel motore, ogni render puo' toccare il grafo
        e il Lab smette di essere estendibile fuori dalla pagina."""
        src = (LAB / "motore.js").read_text()
        # si giudicano gli IMPORT, non la prosa dei commenti
        importati = re.findall(r"^import .*?from '([^']+)'", src, re.M)
        assert all(i.startswith('.') for i in importati), \
            f"motore.js importa moduli non locali: {importati}"

    def test_il_suono_esce_solo_dal_ponte(self):
        """La lezione iOS del 22/8: il grafo su ctx.destination e'
        suono «di contorno», azzerabile dal silenziatore. Tutto il
        Lab deve sfociare nel ponte — MAI in ctx.destination."""
        for f in LAB.glob("*.js*"):
            # si giudica il CODICE, non la prosa: i commenti (che
            # citano il divieto per spiegarlo) si tolgono prima
            codice = re.sub(r"/\*.*?\*/|//[^\n]*", "", f.read_text(),
                            flags=re.S)
            assert "destination" not in codice.replace(
                "createMediaStreamDestination", ""), \
                f"{f.name}: collega ctx.destination invece del ponte"
        motore = (LAB / "motore.js").read_text()
        assert "creaPonte" in motore and "ponte.nodo" in motore, \
            "il motore non passa dal ponte"
        assert "ponte.rilascia" in motore, \
            "senza rilascio, su iOS lo stop lascia un ronzio perpetuo"

    def test_l_analisi_e_un_ospite_input_agnostico(self):
        """La presa del futuro: `sorgente(nodo)` accetta qualsiasi
        nodo. Il microfono sara' un MediaStreamSource passato qui —
        se la firma sparisce, il futuro del Lab trova la porta murata."""
        src = (LAB / "motore.js").read_text()
        assert "sorgente(nodo)" in src, "manca la presa per l'input futuro"
        assert "getFloatTimeDomainData" in src and "getFloatFrequencyData" in src, \
            "l'analisi non espone i dati grezzi (servono float, non byte)"

    def test_niente_dipendenze_nuove(self):
        """Web Audio nativa e basta: il Lab non porta librerie (e
        three.js, che esiste per i visual, non deve entrarci)."""
        for f in LAB.glob("*.js*"):
            for imp in re.findall(r"^import .*?from '([^']+)'",
                                  f.read_text(), re.M):
                assert imp.startswith('.') or imp.startswith('../') \
                    or imp in ("react", "react-router-dom"), \
                    f"{f.name}: dipendenza esterna '{imp}'"
            assert "three" not in f.read_text().lower() or f.suffix == ".css", \
                f"{f.name}: three.js nel chunk del Lab"


class TestGeneratore:
    """Il cuore dello STEP 1: segnale vero, parametri senza salti."""

    def test_le_quattro_forme_e_la_fase(self):
        src = (LAB / "motore.js").read_text()
        for forma in ("sine", "square", "triangle", "sawtooth"):
            assert f"'{forma}'" in src, f"manca la forma {forma}"
        # la fase esiste solo via PeriodicWave (l'oscillatore nativo
        # non ce l'ha): serie di Fourier ruotata di k·fase
        assert "createPeriodicWave" in src and "Math.sin(k * fase)" in src, \
            "la fase non e' implementata con la rotazione delle armoniche"

    def test_nessun_parametro_salta(self):
        """DK = 12 ms su ampiezza e frequenza; il cambio di forma e'
        un crossfade fra due oscillatori, non un `type` a caldo."""
        src = (LAB / "motore.js").read_text()
        assert "DK = 0.012" in src, "la costante declick di casa e' cambiata"
        assert "setTargetAtTime" in src, "i parametri si muovono a gradini"
        assert "rimpiazza" in src and "linearRampToValueAtTime" in src, \
            "il cambio forma non e' un crossfade"

    def test_il_limite_e_nyquist_vero(self):
        """Il tetto viene dal sample rate del dispositivo, non da un
        numero scritto a mano."""
        src = (LAB / "motore.js").read_text()
        assert "ctx.sampleRate / 2" in src, "Nyquist cablato invece che misurato"

    def test_la_frequenza_accetta_i_decimali(self):
        """137.42 Hz e' un caso d'uso dichiarato: il campo tollera la
        virgola (correzione parlante, come il campo tempo di Crea)."""
        src = (LAB / "Generatore.jsx").read_text()
        assert "replace(',', '.')" in src and "parseFloat" in src
        assert 'inputMode="decimal"' in src

    def test_la_riga_di_sicurezza_sul_volume(self):
        """Il Lab genera toni puri: il volume prudente e' parte del
        prodotto, non un optional (ampiezza default bassa + la riga)."""
        motore = (LAB / "motore.js").read_text()
        assert "amp: 0.25" in motore, "l'ampiezza di partenza non e' prudente"
        ui = (LAB / "Generatore.jsx").read_text()
        assert "lab-volume" in ui and "volume basso" in ui


class TestTelaio:
    """STEP 0: la rotta, la shell, la sitemap — le trappole gia' viste."""

    def test_rotta_lazy_prima_del_catchall(self):
        """/sound/lab deve stare PRIMA di /sound/* o FrequenzePage se
        lo mangia; e il Lab resta un chunk lazy (il main non cresce)."""
        src = (FRONTEND_SRC / "App.js").read_text()
        assert 'lazy(() => import("./features/frequenze/lab/SoundLabPage"))' in src
        assert src.index('path="/sound/lab"') < src.index('path="/sound/*"'), \
            "il catch-all mangia il Lab"

    @pytest.mark.asyncio
    async def test_la_shell_conosce_il_lab(self):
        """La trappola di /sound/visual (22/8): un sotto-percorso che
        la shell non conosce e' un 404 per chi arriva da fuori. Il Lab
        e' pubblico e indicizzabile, col suo corpo per i crawler."""
        import sys
        sys.path.insert(0, str(BACKEND_DIR))
        from routers import seo_shell as shell
        meta = await shell.resolve_meta("/sound/lab")
        assert meta is not None, "la shell non conosce /sound/lab: 404"
        assert not meta.get("noindex"), "il Lab e' pubblico, non workspace"
        assert meta["canonical"].endswith("/sound/lab")
        assert "generatore" in meta.get("content_html", "").lower(), \
            "il corpo per i crawler non racconta il generatore"

    def test_sitemap_e_navigazione(self):
        seo = (BACKEND_DIR / "routers" / "seo.py").read_text()
        assert "/sound/lab" in seo, "il Lab non e' in sitemap"
        topbar = (FRONTEND_SRC / "features" / "frequenze" / "SoundTopbar.jsx").read_text()
        assert "'/sound/lab'" in topbar, "il Lab non e' nella passerella"
        landing = (FRONTEND_SRC / "features" / "frequenze" / "SoundLandingPage.js").read_text()
        assert "sld-lab" in landing, "la landing non porta al Lab"

    def test_la_biblioteca_non_si_tocca(self):
        """Il vincolo del founder: la parte educativa resta com'e'.
        Il Lab la LINKA (e' la biblioteca che si tocca), non la sposta."""
        src = (LAB / "Generatore.jsx").read_text()
        assert "CAT_LINK" in src, "il ponte Lab → biblioteca e' sparito"
        pagina = (LAB / "SoundLabPage.js").read_text()
        assert "SafetyCurtain" in pagina and "SafetyLine" in pagina, \
            "le controindicazioni non valgono nel Lab"
