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


class TestOscilloscopio:
    """STEP 2: il dominio del tempo. Il contratto: la tela disegna i
    dati veri, non conosce il generatore, e il banco ha UN ciclo."""

    def test_disegna_i_dati_veri_senza_conoscere_il_generatore(self):
        """La tela riceve `ottieniAnalisi` e basta: niente motore,
        niente generatore, niente analyser proprio. E' il contratto
        che rendera' il microfono un cambio di sorgente, non di
        strumenti."""
        src = (LAB / "Oscilloscopio.jsx").read_text()
        importati = re.findall(r"^import .*?from '([^']+)'", src, re.M)
        assert "./motore" not in importati and "./Generatore" not in importati, \
            "l'oscilloscopio conosce il generatore: il microfono trovera' la porta murata"
        assert "createAnalyser" not in src, \
            "si e' fatto un analyser suo invece di osservare quello del motore"
        assert "analisi.tempo(" in src, \
            "non legge i campioni veri (getFloatTimeDomainData via analisi)"

    def test_il_trigger_esiste_ed_ha_l_isteresi(self):
        """Senza trigger la traccia scorre e lo strumento sembra
        rotto; senza isteresi il rumore fa scattare a vuoto."""
        src = (LAB / "Oscilloscopio.jsx").read_text()
        assert "function trigger(" in src
        assert "armato" in src and "picco * 0.08" in src, \
            "l'isteresi adattiva e' sparita dal trigger"

    def test_freeze_ferma_il_disegno_non_il_suono(self):
        src = (LAB / "Oscilloscopio.jsx").read_text()
        assert "freezeRef" in src and "lab-freeze" in src
        # da congelati si smette di ACQUISIRE ma si ridipinge l'ultimo
        # buffer: un resize non deve cancellare la traccia ferma
        assert "!freezeRef.current" in src

    def test_un_solo_ciclo_di_disegno_per_tutto_il_banco(self):
        """La regola vale per ogni strumento presente e futuro: il
        rAF vive SOLO nel quadro, i pannelli iscrivono pittori.
        E il quadro dorme quando la pagina non si vede."""
        quadro = (LAB / "quadro.js").read_text()
        assert "requestAnimationFrame" in quadro
        assert "visibilitychange" in quadro and "document.hidden" in quadro
        for f in LAB.glob("*.jsx"):
            assert "requestAnimationFrame" not in f.read_text(), \
                f"{f.name}: un ciclo suo invece del quadro condiviso"
        assert "iscrivi" in (LAB / "Oscilloscopio.jsx").read_text()

    def test_la_pagina_monta_la_tela_sotto_il_generatore(self):
        src = (LAB / "SoundLabPage.js").read_text()
        assert src.index("<Generatore") < src.index("<Oscilloscopio"), \
            "la gerarchia del banco e' GENERATORE poi OSCILLOSCOPIO"
        assert "labRef.current?.analisi" in src, \
            "alla tela non arriva l'analisi del motore"


class TestSpettro:
    """STEP 3: il dominio delle frequenze. Lo Spettro nasce con lo
    STESSO contratto dell'Oscilloscopio — e queste guardie lo dicono
    una volta per entrambi, cosi' vale anche per gli strumenti che
    verranno."""

    def test_ogni_tela_rispetta_il_contratto(self):
        """Nessun pannello conosce il generatore, si fabbrica nodi
        audio o apre un contesto: osservano e basta. E' la regola che
        rendera' il microfono un cambio di sorgente, non di
        strumenti."""
        for nome in ("Oscilloscopio.jsx", "Spettro.jsx", "Spettrogramma.jsx"):
            src = (LAB / nome).read_text()
            importati = re.findall(r"^import .*?from '([^']+)'", src, re.M)
            assert "./motore" not in importati, f"{nome}: importa il motore"
            assert "./Generatore" not in importati, f"{nome}: importa il Generatore"
            assert set(importati) <= {"react", "./quadro"}, \
                f"{nome}: importa altro dal contratto ({importati})"
            for vietato in ("createAnalyser", "AudioContext", "createGain",
                            "createOscillator"):
                assert vietato not in src, f"{nome}: si fabbrica {vietato}"

    def test_lo_spettro_legge_i_dati_veri(self):
        """getFloatFrequencyData attraverso l'analisi del motore: il
        motore aveva gia' `spettro()` e `hzPerBin` dallo STEP 1, non
        e' stato aggiunto nulla."""
        src = (LAB / "Spettro.jsx").read_text()
        assert "analisi.spettro(" in src and "analisi.hzPerBin" in src, \
            "lo spettro non legge i dati veri dell'analyser"
        # la scala verticale e' in dBFS, NON la finestra
        # min/maxDecibels dell'analyser: quelle governano solo l'API a
        # byte, e col tetto di fabbrica a -30 dB ogni ampiezza sopra un
        # quarto si schiacciava in cima (trovato misurando, 26/8)
        assert "DB_MIN = -96, DB_MAX = 0" in src
        assert "minDecibels" not in src.split("*/")[-1], \
            "la finestra a byte e' tornata a governare la scala float"

    def test_disegna_per_pixel_e_legge_il_picco_col_vertice(self):
        """Le due scelte che lo rendono uno strumento: il massimo dei
        bin per colonna (su scala log un picco stretto sparirebbe) e
        l'interpolazione parabolica (la FFT ha passo ~5 Hz: senza, il
        picco di 137,42 si leggerebbe 137,9)."""
        src = (LAB / "Spettro.jsx").read_text()
        assert "function vertice(" in src, "manca l'interpolazione parabolica"
        assert "for (let k = k0; k < k1; k++)" in src, \
            "non prende il massimo dei bin che competono alla colonna"
        assert "Math.log10" in src, "la scala delle frequenze non e' logaritmica"

    def test_un_solo_ciclo_di_disegno_in_tutto_il_banco(self):
        """La regola vale per OGNI pannello, presente e futuro: il rAF
        vive solo nel quadro."""
        for f in list(LAB.glob("*.jsx")) + [LAB / "SoundLabPage.js",
                                            LAB / "motore.js"]:
            assert "requestAnimationFrame" not in f.read_text(), \
                f"{f.name}: un ciclo suo invece del quadro condiviso"
        quadro = (LAB / "quadro.js").read_text()
        assert quadro.count("requestAnimationFrame") >= 1
        assert "iscrivi" in (LAB / "Spettro.jsx").read_text()

    def test_il_picco_non_re_iscrive_il_pittore(self):
        """Trappola React: se il picco (che cambia a ogni frame)
        finisse nelle dipendenze dell'effetto, il pittore si
        iscriverebbe e disiscriverebbe sessanta volte al secondo. Il
        disegno usa un ref, lo stato serve solo all'etichetta."""
        src = (LAB / "Spettro.jsx").read_text()
        assert "piccoRef" in src, "il picco non ha un ref per il disegno"
        assert "}, [ottieniAnalisi]);" in src, \
            "le dipendenze dell'effetto non sono stabili"

    def test_il_banco_e_in_ordine(self):
        src = (LAB / "SoundLabPage.js").read_text()
        assert src.index("<Generatore") < src.index("<Oscilloscopio") \
            < src.index("<Spettro"), \
            "l'ordine del banco e' generatore, tempo, frequenze"
        # OGNI pannello d'analisi riceve la stessa presa: il conteggio
        # esatto lo tiene la guardia del banco completo, che cresce a
        # ogni strumento nuovo
        assert src.count("ottieniAnalisi={() => labRef.current?.analisi") \
            == src.count("ottieniAnalisi="), \
            "un pannello riceve un'analisi diversa dagli altri"

    def test_il_motore_non_e_stato_toccato_per_lo_spettro(self):
        """Lo STEP 3 non doveva cambiare il motore: `spettro()` e
        `hzPerBin` c'erano gia'. Se qualcuno aggiunge un metodo
        dedicato allo spettro, e' segno che il contratto e' scivolato."""
        src = (LAB / "motore.js").read_text()
        assert "spettro(buf)" in src and "hzPerBin" in src
        assert "frequenza(" not in src, \
            "aggiunto un metodo nuovo al motore invece di riusare spettro()"


class TestSpettrogramma:
    """STEP 4: lo spettro nel tempo. Il contratto e' quello di tutti
    (verificato da TestSpettro.test_ogni_tela_rispetta_il_contratto,
    che ora include anche questo pannello); qui cio' che e' suo."""

    def test_la_mappa_delle_frequenze_e_gemella_dello_spettro(self):
        """I due pannelli si leggono INSIEME: stessa partenza a 20 Hz,
        stessa finestra in dBFS, stessa log fino a Nyquist. Le
        costanti sono ricopiate (i pannelli non si conoscono fra
        loro), quindi vanno tenute gemelle a mano — da qui."""
        sp = (LAB / "Spettro.jsx").read_text()
        sg = (LAB / "Spettrogramma.jsx").read_text()
        for costante in ("const F_MIN = 20;", "const DB_MIN = -96, DB_MAX = 0;"):
            assert costante in sp and costante in sg, \
                f"le scale si sono scollate: {costante}"
        assert "Math.log10" in sg, "l'asse delle frequenze non e' logaritmico"

    def test_le_colonne_vanno_a_tempo_non_a_fotogramma(self):
        """Se l'asse X fosse «un fotogramma per colonna», su un
        telefono lento la stessa immagine varrebbe un tempo diverso e
        la finestra dichiarata sarebbe una bugia."""
        src = (LAB / "Spettrogramma.jsx").read_text()
        assert "MS_COLONNA" in src and "performance.now()" in src
        assert "debito" in src, "il tempo trascorso non si accumula"
        assert "MAX_COLONNE" in src, \
            "dopo una pausa lunga si recupererebbe all'infinito"

    def test_scorre_invece_di_ridisegnare(self):
        """L'immagine E' la memoria: una traslazione e una colonna
        nuova, non la storia ricalcolata a ogni fotogramma."""
        src = (LAB / "Spettrogramma.jsx").read_text()
        assert "c2d.drawImage(tela" in src, "non trasla la storia"
        assert "putImageData" in src and "createImageData" in src, \
            "la colonna nuova non si scrive per pixel"
        assert "for (let k = k0; k < k1; k++)" in src, \
            "la riga non prende il massimo dei bin che le competono"

    def test_la_scala_di_colore_e_sobria(self):
        """Una sola famiglia di colori dalla palette del Lab: niente
        arcobaleno, niente neon, nessun colore cablato a mano."""
        src = (LAB / "Spettrogramma.jsx").read_text()
        assert "function rampa(" in src
        for tinta in ("--ink", "--water", "--bone"):
            assert tinta in src, f"la rampa non usa {tinta} della palette"
        assert "hsl(" not in src, "scala arcobaleno (hsl) nel Lab"

    def test_il_banco_e_in_ordine_e_completo(self):
        src = (LAB / "SoundLabPage.js").read_text()
        assert src.index("<Generatore") < src.index("<Oscilloscopio") \
            < src.index("<Spettro ") < src.index("<Spettrogramma"), \
            "l'ordine del banco: genera, tempo, frequenze, frequenze nel tempo"
        assert src.count("labRef.current?.analisi") == 3, \
            "i tre strumenti non ricevono la stessa analisi"

    def test_il_motore_resta_invariato_anche_allo_step_4(self):
        """Nessuna API nuova: `spettro()` serviva a due pannelli e ne
        serve tre."""
        src = (LAB / "motore.js").read_text()
        assert "spettro(buf)" in src and "hzPerBin" in src
        assert "spettrogramma" not in src.lower(), \
            "il motore ha imparato a conoscere un pannello"


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
