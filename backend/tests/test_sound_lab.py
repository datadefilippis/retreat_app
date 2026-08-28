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
        """STEP 5: il fermo non e' piu' del pannello ma del banco. Qui
        resta la meta' che riguarda l'oscilloscopio: da fermi si
        smette di ACQUISIRE ma si continua a ridipingere l'ultimo
        campione, cosi' un cambio di misura non cancella la traccia."""
        src = (LAB / "Oscilloscopio.jsx").read_text()
        assert "if (analisi && !fermo) {" in src, \
            "da fermi l'oscilloscopio acquisisce lo stesso"
        assert "c2d.stroke();" in src.split("if (analisi && !fermo)")[1], \
            "da fermi non ridipinge: al ridimensionamento perde la traccia"

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
        # OGNI pannello riceve LA STESSA presa, e una sola volta:
        # dallo STEP 5 e' una callback stabile, non un'arrow nel JSX
        assert src.count("ottieniAnalisi={ottieniAnalisi}") \
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
        assert src.count("ottieniAnalisi={ottieniAnalisi}") == 3, \
            "i tre strumenti non ricevono la stessa analisi"

    def test_il_motore_resta_invariato_anche_allo_step_4(self):
        """Nessuna API nuova: `spettro()` serviva a due pannelli e ne
        serve tre."""
        src = (LAB / "motore.js").read_text()
        assert "spettro(buf)" in src and "hzPerBin" in src
        assert "spettrogramma" not in src.lower(), \
            "il motore ha imparato a conoscere un pannello"


class TestBancoUnico:
    """STEP 5 (26/8): un segnale, un tempo, tre letture.

    Il congelamento e' del BANCO, non dei pannelli: il tempo VISIVO
    vive nel quadro — che e' gia' l'unico padrone del tempo di
    rendering — e il suono non lo sfiora."""

    def test_il_tempo_fermo_ha_un_padrone_solo(self):
        quadro = (LAB / "quadro.js").read_text()
        assert "let tempoFermo = false;" in quadro, \
            "il tempo visivo non abita nel quadro"
        for nome in ("congela", "eFermo", "ascoltaFermo"):
            assert f"export function {nome}" in quadro, f"manca {nome}()"
        # i pittori ricevono il fermo dal quadro, non se lo inventano
        assert "p(tempoFermo)" in quadro

    def test_nessun_pannello_tiene_un_fermo_suo(self):
        """Tre freeze indipendenti erano tre verita' possibili sullo
        stesso istante. Ora i pannelli LEGGONO il fermo: come
        parametro del pittore (per disegnare) e come prop (per
        dirlo) — nessuno lo possiede."""
        for nome in ("Oscilloscopio.jsx", "Spettro.jsx", "Spettrogramma.jsx"):
            src = (LAB / nome).read_text()
            assert "freezeRef" not in src, f"{nome}: ha ancora un fermo suo"
            assert "setFreeze" not in src, f"{nome}: ha ancora uno stato di fermo"
            assert "congela(" not in src, f"{nome}: comanda il fermo del banco"
            assert "const dipingi = (fermo) =>" in src, \
                f"{nome}: il pittore non riceve il tempo dal quadro"

    def test_il_comando_e_del_banco_e_uno_solo(self):
        pagina = (LAB / "SoundLabPage.js").read_text()
        assert 'data-testid="lab-congela"' in pagina
        assert pagina.count("data-testid=\"lab-congela\"") == 1, \
            "il comando e' duplicato"
        # sta FRA la sorgente e le letture: e' li' che passa il confine
        assert pagina.index("<Generatore") < pagina.index('data-testid="lab-banco"') \
            < pagina.index("<Oscilloscopio"), \
            "il comando non sta fra il generatore e le sue letture"
        # Evoluta con LB1 (27/8): il divieto riguarda i comandi di
        # TEMPO (congela/riprendi restano del banco, uno solo). Un
        # selettore di MODO di lettura (Tempo/XY nell'oscilloscopio,
        # role="radio") e' un'altra cosa: cambia cosa si guarda, non
        # quando. Ogni <button> nei pannelli deve essere un radio.
        for nome in ("Oscilloscopio.jsx", "Spettro.jsx", "Spettrogramma.jsx"):
            src = (LAB / nome).read_text()
            assert "lab-congela" not in src and "lab-freeze" not in src, \
                f"{nome}: ha un comando di tempo suo"
            assert src.count("<button") == src.count('role="radio"'), \
                f"{nome}: ha un pulsante che non e' un selettore di modo"

    def test_la_pagina_si_iscrive_invece_di_copiare(self):
        """Lo stato React del pulsante e' una SOTTOSCRIZIONE al quadro,
        non una seconda verita' da tenere allineata a mano."""
        pagina = (LAB / "SoundLabPage.js").read_text()
        assert "useState(eFermo())" in pagina and "ascoltaFermo(setFermo)" in pagina
        assert "congela(!fermo)" in pagina, "il pulsante non parla col quadro"

    def test_la_presa_e_stabile(self):
        """Difetto trovato leggendo (26/8): la presa era un'arrow
        scritta nel JSX, quindi NUOVA a ogni render della pagina —
        i tre pittori si disiscrivevano e riscrivevano per nulla.
        Con uno stato di pagina (il fermo) sarebbe successo a ogni
        clic, e lo spettrogramma ci moriva dentro (vedi sotto)."""
        pagina = (LAB / "SoundLabPage.js").read_text()
        assert "useCallback(() => labRef.current?.analisi || null, [])" in pagina, \
            "la presa non e' stabile fra un render e l'altro"
        assert "ottieniAnalisi={() => " not in pagina, \
            "e' tornata un'arrow nel JSX"

    def test_lo_spettrogramma_sopravvive_a_una_ri_iscrizione(self):
        """Il difetto latente: tinte, passo e colonna nascevano solo
        dentro lo svuotamento, che gira SOLO al cambio di misura. Un
        pittore ri-iscritto senza resize ripartiva senza colori e
        moriva alla prima riga — in silenzio, perche' il quadro non
        fa cadere il banco per un pittore rotto."""
        src = (LAB / "Spettrogramma.jsx").read_text()
        assert "const allestisci = (" in src and "const svuota = (" in src, \
            "allestire e svuotare sono ancora la stessa cosa"
        assert "} else if (!tinte) {" in src, \
            "senza questo, un pittore ri-iscritto muore muto"
        # e svuotare resta legato al SOLO cambio di misura
        assert "svuota(W, H);" in src.split("tela.height = H;")[1][:200]

    def test_il_fermo_non_tocca_il_suono(self):
        """La prova di principio, in codice: nel quadro (dove vive il
        fermo) non si nomina il motore; e il congelamento non passa
        mai dal generatore."""
        quadro = (LAB / "quadro.js").read_text()
        importati = re.findall(r"^import .*?from '([^']+)'", quadro, re.M)
        assert not importati, f"il quadro ha imparato a conoscere qualcuno: {importati}"
        pagina = (LAB / "SoundLabPage.js").read_text()
        blocco = pagina.split('data-testid="lab-banco"')[1][:400]
        assert "generatore" not in blocco.lower(), \
            "il comando del banco tocca il generatore: non e' piu' un fermo visivo"

    def test_il_quadro_dorme_ancora_a_pagina_nascosta(self):
        """Il fermo condiviso non deve aver intaccato la regola di
        prima: niente rAF quando la pagina non si vede."""
        quadro = (LAB / "quadro.js").read_text()
        assert "document.hidden" in quadro and "visibilitychange" in quadro
        assert "if (!pittori.size || document.hidden) return;" in quadro


class TestSweep:
    """STEP 6 (26/8): la corsa di frequenza.

    Una rampa VERA sull'AudioParam, non un orologio che ritocca la
    frequenza. Il motivo per cui la scelta non e' di gusto: il quadro
    muore a pagina nascosta e un timer JavaScript dorme con lo
    schermo, mentre l'audio continua — uno sweep guidato da loro si
    inchioderebbe a meta'. La rampa la calcola il motore audio,
    campione per campione, e non se ne accorge nemmeno."""

    def test_la_corsa_e_una_rampa_non_un_orologio(self):
        src = (LAB / "motore.js").read_text()
        assert "exponentialRampToValueAtTime(stato.freq, t + secondi)" in src, \
            "lo sweep non e' una rampa sull'AudioParam"
        codice = re.sub(r"/\*.*?\*/|//[^\n]*", "", src, flags=re.S)
        for orologio in ("setInterval", "setTimeout", "requestAnimationFrame"):
            assert orologio not in codice, f"il motore pilota la corsa con {orologio}"

    def test_una_sola_verita_sulla_frequenza(self):
        """Il numero scritto e il suono devono essere la stessa cosa
        letta due volte: `freqOra()` usa la STESSA formula della rampa
        del browser, v(t) = da · (a/da)^u."""
        src = (LAB / "motore.js").read_text()
        assert "const freqOra = () =>" in src
        assert "corsa.da * Math.pow(corsa.a / corsa.da, u)" in src, \
            "la frequenza mostrata non segue la curva della rampa"
        assert "freq: freqOra()" in src, \
            "stato() non dice la frequenza che suona adesso"
        # e il generatore LEGGE quella, non ne tiene una sua
        ui = (LAB / "Generatore.jsx").read_text()
        assert "lab.generatore.stato()" in ui
        codice = re.sub(r"/\*.*?\*/|//[^\n]*", "", ui, flags=re.S)
        for orologio in ("setInterval", "setTimeout", "requestAnimationFrame"):
            assert orologio not in codice, f"il generatore usa {orologio}"
        assert "iscrivi(" in ui, \
            "il numero non segue il giro del banco (si e' fatto un orologio suo)"

    def test_imposta_senza_secondi_non_e_cambiata(self):
        """Il gesto di sempre deve restare identico: senza `secondi`
        si scivola col setTargetAtTime di prima."""
        src = (LAB / "motore.js").read_text()
        assert "p.setTargetAtTime(stato.freq, t, DK / 3);" in src
        assert "const secondi = Math.max(0, +patch.secondi || 0);" in src

    def test_interrompere_non_lascia_niente_dietro(self):
        """Non ci sono timer da spegnere perche' non ce n'e' mai stato
        uno: cancellare la programmazione basta."""
        src = (LAB / "motore.js").read_text()
        assert "p.cancelScheduledValues(t);" in src
        ui = (LAB / "Generatore.jsx").read_text()
        assert "imposta({ freq: lab.generatore.stato().freq })" in ui, \
            "fermare la corsa non tiene la nota dove si trova"
        # e spegnere il generatore chiude anche la corsa (il come sta
        # nella guardia A1 dello STEP 7: prima si fissa dove siamo)
        blocco = src.split("ferma() {")[1][:700]
        assert "corsa = null;" in blocco

    def test_la_voce_nuova_eredita_la_corsa(self):
        """Cambiare forma a meta' sweep crea un oscillatore nuovo: se
        nascesse alla meta', la rampa sarebbe persa."""
        src = (LAB / "motore.js").read_text()
        blocco = src.split("const nuovaVoce")[1][:700]
        assert "const ora = freqOra();" in blocco
        assert "exponentialRampToValueAtTime(corsa.a" in blocco, \
            "la voce nuova non riprende il pezzo di rampa che resta"

    def test_i_pannelli_non_sanno_nulla_dello_sweep(self):
        """La prova che la catena regge: le tre tele vedono la
        diagonale perche' la diagonale C'E', non perche' qualcuno
        gliel'ha detta."""
        for nome in ("Oscilloscopio.jsx", "Spettro.jsx", "Spettrogramma.jsx"):
            src = (LAB / nome).read_text()
            # si giudica il CODICE spogliato dei commenti: «corsa
            # libera» e' lo stato del trigger da sempre, e lo
            # spettrogramma misura la sua finestra «in secondi» —
            # parole innocenti che non c'entrano con lo sweep
            codice = re.sub(r"/\*.*?\*/|//[^\n]*", "", src, flags=re.S)
            assert "sweep" not in codice.lower(), f"{nome}: sa dello sweep"
            assert "imposta(" not in codice and "secondi:" not in codice, \
                f"{nome}: tocca la frequenza invece di leggere il segnale"

    def test_lo_sweep_e_nel_generatore_non_altrove(self):
        ui = (LAB / "Generatore.jsx").read_text()
        assert 'data-testid="lab-sweep"' in ui
        for campo in ("lab-sweep-da", "lab-sweep-a", "lab-sweep-durata",
                      "lab-sweep-avvia"):
            assert campo in ui, f"manca il campo {campo}"
        pagina = (LAB / "SoundLabPage.js").read_text()
        assert "lab-sweep" not in pagina and "secondi:" not in pagina, \
            "i comandi dello sweep sono usciti dal generatore"


class TestRifinitura:
    """STEP 7 (26/8): le quattro correzioni uscite dall'audit. Nessuna
    funzione nuova — solo cose che mentivano."""

    def test_spegnere_non_fa_saltare_la_frequenza_alla_meta(self):
        """A1. Prima `ferma()` azzerava la corsa e basta: `stato.freq`
        restava la META, cosi' fermare uno sweep a 1092 Hz faceva dire
        allo stato «100» — mai suonata — e alla ripartenza il
        generatore attaccava di li'."""
        src = (LAB / "motore.js").read_text()
        blocco = src.split("ferma() {")[1][:700]
        assert "stato.freq = freqOra();" in blocco, \
            "spegnendo non si fissa la frequenza corrente"
        assert blocco.index("stato.freq = freqOra();") < blocco.index("corsa = null"), \
            "si azzera la corsa PRIMA di leggerla: freqOra() direbbe la meta'"

    def test_il_numerone_resiste_alla_regola_globale(self):
        """B1. index.css impone input{font-size:16px!important} sotto
        i 767 (difesa anti-zoom iOS): schiacciava il protagonista
        della pagina. Si riprende la misura con la stessa forza, e la
        finestra dev'essere quella della regola globale (767), non 640
        — o fra i due valori il numerone tornerebbe piccolo."""
        css = (LAB / "lab.css").read_text()
        blocco = css.split("@media screen and (max-width:767px)")[1][:200]
        assert ".lab-freq-num input{font-size:32px !important}" in blocco
        # 32 e' sopra la soglia dei 16: la difesa anti-zoom regge
        globale = (FRONTEND_SRC / "index.css").read_text()
        assert "font-size: 16px !important;" in globale, \
            "la regola globale e' cambiata: rivedere la difesa del Lab"

    def test_lo_spettrogramma_a_riposo_mostra_la_sua_scala(self):
        """B2. Prima del primo Genera era un rettangolo nero muto,
        mentre gli altri due strumenti mostravano la griglia."""
        src = (LAB / "Spettrogramma.jsx").read_text()
        blocco = src.split("if (!analisi) {")[1][:400]
        assert "etichette(W, H, dpr);" in blocco, \
            "a riposo non disegna gli assi"
        # e lo DICE, come fa l'oscilloscopio
        assert "'in attesa di un segnale'" in src
        # ma non inventa dati: nessuna traccia finta a riposo
        assert "putImageData" not in blocco and "Math.random" not in src

    def test_la_striscia_non_promette_suono_che_non_ce(self):
        """B4. Congelando a generatore spento diceva «il suono
        continua». Ora il generatore avvisa quando si accende e si
        spegne, e la striscia dice la verita' in entrambi i casi."""
        pagina = (LAB / "SoundLabPage.js").read_text()
        assert "const [suona, setSuona] = useState(false);" in pagina
        assert "onSuono={setSuona}" in pagina
        assert "? 'le tre letture sono ferme — il suono continua'" in pagina
        # l'avviso fa RIDISEGNARE, ma la verita' si chiede al motore:
        # cosi' regge anche se il suono si spegnesse fuori dal pulsante
        assert "labRef.current.generatore.stato().attivo" in pagina
        assert "suonaDavvero" in pagina
        assert ": 'le tre letture sono ferme'" in pagina
        ui = (LAB / "Generatore.jsx").read_text()
        assert "const suono = (acceso) => { setAttivo(acceso); onSuono?.(acceso); };" in ui, \
            "il generatore non avvisa piu' il banco"
        assert "setAttivo(true)" not in ui and "setAttivo(false)" not in ui, \
            "c'e' ancora una via che accende il suono senza avvisare"

    def test_lo_slider_resta_libero_durante_la_corsa(self):
        """B3 e' stato ESCLUSO dal founder: prendere il volante a
        meta' sweep resta possibile, senza indicatori."""
        ui = (LAB / "Generatore.jsx").read_text()
        freq = ui.split('className="lab-freq"')[1].split('</div>')[0]
        assert "disabled" not in freq, \
            "il campo/slider della frequenza e' stato bloccato: B3 non si fa"


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
        # NV3 (27/8, BUSSOLA): il Lab non e' piu' una voce di menu —
        # e' una STANZA nella barra unica (StanzeSound), condivisa con
        # la biblioteca. La passerella non lo nomina.
        topbar = (FRONTEND_SRC / "features" / "frequenze" / "SoundTopbar.jsx").read_text()
        assert "'/sound/lab'" not in topbar, "il Lab e' tornato in passerella"
        barra = (FRONTEND_SRC / "features" / "frequenze" / "StanzeSound.jsx").read_text()
        assert "'/sound/lab'" in barra, "il Lab non e' fra le stanze"
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

class TestSecondaVoceLb1:
    """LB1 (27/8/2026) — la seconda sorgente. Le promesse misurate al
    collaudo strumentale (via __fqzLab, pagina nascosta):
    solo A = 0.177 RMS (ampiezza onesta), costruttiva 0.353,
    controfase 0.0004, battimenti 440+444 con RMS che respira."""

    def test_le_voci_sono_gemelle_di_una_fabbrica(self):
        """Una macchina sola (creaSorgente) costruisce A e B: la A non
        puo' cambiare comportamento senza che la B la segua."""
        src = (LAB / "motore.js").read_text()
        assert src.count("function creaSorgente") == 1
        assert "generatore: creaSorgente()" in src
        assert "generatore2: creaSorgente()" in src

    def test_dove_suona_e_un_interruttore_non_un_pan(self):
        """Trappola pagata al collaudo: lo StereoPanner a potenza
        costante toglie 3 dB al centro (ampiezza 25% → picco 0.177) e
        lo strumento MENTIVA sull'ampiezza. I canali sono guadagni
        espliciti: al centro 1 e 1, di lato 1 e 0."""
        src = (LAB / "motore.js").read_text()
        assert "createStereoPanner" not in src, \
            "il pan-law e' tornato: l'ampiezza mente di 3 dB"
        assert "entrambe: [1, 1]" in src
        assert "sinistra: [1, 0]" in src and "destra: [0, 1]" in src

    def test_il_phase_lock_esiste(self):
        """Misurato: senza riferimento comune, «fase 180°» e' 180°
        rispetto al caso (RMS giu' 4:1 invece che a zero). Ogni voce
        parte a un istante PROGRAMMATO e la sua onda e' ruotata di
        2π·f·tS: la fase e' riferita all'origine del contesto, e la
        cancellazione misura -59 dB."""
        src = (LAB / "motore.js").read_text()
        assert "osc.start(tS)" in src, "la partenza non e' piu' programmata"
        assert "stato.fase + DUE_PI * ora * tS" in src, \
            "manca la rotazione di compensazione: la fase torna casuale"

    def test_il_ponte_chiude_con_l_ultima_voce(self):
        """Con due voci il rilascio del ponte non puo' piu' essere
        cieco: si chiude solo quando TUTTE tacciono (lezione iOS del
        22/8: l'<audio> su stream muto loopa l'ultimo buffer)."""
        src = (LAB / "motore.js").read_text()
        assert "qualcunoSuona" in src
        assert "if (!qualcunoSuona()) ponte.rilascia();" in src

    def test_l_xy_legge_le_voci_separate(self):
        """Le figure di Lissajous vogliono i DUE segnali: ogni voce ha
        il suo rubinetto (tap pre-canali), e l'oscilloscopio riceve la
        presa XY dalla pagina senza conoscere il generatore."""
        motore = (LAB / "motore.js").read_text()
        assert "tap.getFloatTimeDomainData(buf)" in motore
        pagina = (LAB / "SoundLabPage.js").read_text()
        assert "ottieniXY" in pagina
        scope = (LAB / "Oscilloscopio.jsx").read_text()
        assert "ottieniXY" in scope
        assert "Lissajous" in scope, "il modo XY ha perso la didascalia"
        assert "creaLaboratorio" not in scope   # il contratto regge

    def test_la_seconda_voce_rispetta_i_contratti(self):
        """SecondaVoce: React e' la mano, il suono sta nel motore —
        niente nodi audio nel componente; e la didascalia c'e' (regola
        LB: nessun modulo muto)."""
        src = (LAB / "SecondaVoce.jsx").read_text()
        assert "generatore2" in src
        assert "createOscillator" not in src and "AudioContext" not in src
        assert "lab-didascalia" in src
        assert "interferenza" in src.lower()

    def test_il_generatore_a_dice_la_verita_nuova(self):
        """La nota della fase prometteva il futuro («contera' quando le
        sorgenti saranno due»): ora le sorgenti sono due e la nota
        insegna il gesto della cancellazione. E anche la A sceglie
        dove suonare."""
        src = (LAB / "Generatore.jsx").read_text()
        assert "conterà quando" not in src, "la nota promette ancora il futuro"
        assert "180°" in src
        assert 'data-testid="lab-orecchio"' in src

