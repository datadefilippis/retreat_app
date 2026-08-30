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
            # Evoluta con LB4: la destination di un OFFLINE context non
            # e' una via verso l'altoparlante — e' il file del render
            # (il silenziatore iOS non c'entra). L'unica forma ammessa
            # e' quella della fonderia dentro renderizzaWav.
            codice = codice.replace("campana(ctx, ctx.destination", "")
            # LB6: i WAV di cimatica.js nascono in un contesto OFFLINE
            # (g.connect(ctx.destination) dentro tonoWav/sweepWav):
            # anche li' la destination e' il file del render
            if f.name == "cimatica.js":
                codice = codice.replace("g.connect(ctx.destination)", "")
            # LB7: 'destination-out' e' un modo di COMPOSIZIONE del
            # canvas (la scia al fosforo), non un nodo audio
            codice = codice.replace("'destination-out'", "")
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
        # Migrata col ciclo LU (28/8): la pagina unica e' diventata la
        # casa con le stanze — la verita' vive in LabBanco/LettureBanco
        # e nel hook usaLab, uno per tutte le stanze.
        src = (LAB / "LabBanco.jsx").read_text()
        assert src.index("<Generatore") < src.index("<LettureBanco"), \
            "la gerarchia del banco e' SORGENTI poi LETTURE"
        assert "labRef.current?.analisi" in (LAB / "usaLab.js").read_text(), \
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
        for f in list(LAB.glob("*.jsx")) + [LAB / "usaLab.js",
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
        # Migrata col ciclo LU (28/8): la pagina unica e' diventata la
        # casa con le stanze — la verita' vive in LabBanco/LettureBanco
        # e nel hook usaLab, uno per tutte le stanze.
        src = (LAB / "LettureBanco.jsx").read_text()
        assert src.index("<Oscilloscopio") < src.index("<Spettro "), \
            "l'ordine delle letture e' tempo, poi frequenze"
        # OGNI pannello riceve LA STESSA presa, e una sola volta —
        # in TUTTE le stanze (callback stabile, mai arrow nel JSX)
        for stanza in LAB.glob("Lab*.jsx"):
            pag = stanza.read_text()
            assert pag.count("ottieniAnalisi={ottieniAnalisi}") \
                == pag.count("ottieniAnalisi="), \
                f"{stanza.name}: una presa diversa dalle altre"

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
        # Migrata col ciclo LU (28/8): la pagina unica e' diventata la
        # casa con le stanze — la verita' vive in LabBanco/LettureBanco
        # e nel hook usaLab, uno per tutte le stanze.
        src = (LAB / "LettureBanco.jsx").read_text()
        assert src.index("<Oscilloscopio") < src.index("<Spettro ") \
            < src.index("<Spettrogramma"), \
            "l'ordine delle letture: tempo, frequenze, frequenze nel tempo"
        # ogni stanza che ascolta o misura riceve la presa dell'analisi
        for stanza in ("LabBanco.jsx", "LabOrecchio.jsx",
                       "LabMeraviglie.jsx", "LabRisonanze.jsx"):
            assert "ottieniAnalisi" in (LAB / stanza).read_text(), \
                f"{stanza}: ha perso la presa dell'analisi"

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
        # Migrata col ciclo LU (28/8): la pagina unica e' diventata la
        # casa con le stanze — la verita' vive in LabBanco/LettureBanco
        # e nel hook usaLab, uno per tutte le stanze.
        blocco = (LAB / "LettureBanco.jsx").read_text()
        assert blocco.count("data-testid=\"lab-congela\"") == 1, \
            "il comando e' duplicato (o sparito)"
        # sta FRA la sorgente e le letture: prima delle tele nel blocco
        assert blocco.index('data-testid="lab-banco"') \
            < blocco.index("<Oscilloscopio"), \
            "il comando non sta prima delle letture"
        pagina = (LAB / "LabBanco.jsx").read_text()
        assert pagina.index("<Generatore") < pagina.index("<LettureBanco")
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
        hook = (LAB / "usaLab.js").read_text()
        assert "useState(eFermo())" in hook and "ascoltaFermo(setFermo)" in hook
        blocco = (LAB / "LettureBanco.jsx").read_text()
        assert "congela(!fermo)" in blocco, "il pulsante non parla col quadro"

    def test_la_presa_e_stabile(self):
        """Difetto trovato leggendo (26/8): la presa era un'arrow
        scritta nel JSX, quindi NUOVA a ogni render della pagina —
        i tre pittori si disiscrivevano e riscrivevano per nulla.
        Con uno stato di pagina (il fermo) sarebbe successo a ogni
        clic, e lo spettrogramma ci moriva dentro (vedi sotto)."""
        hook = (LAB / "usaLab.js").read_text()
        assert "useCallback(() => labRef.current?.analisi || null, [])" in hook, \
            "la presa non e' stabile fra un render e l'altro"
        for stanza in LAB.glob("Lab*.jsx"):
            assert "ottieniAnalisi={() => " not in stanza.read_text(), \
                f"{stanza.name}: e' tornata un'arrow nel JSX"

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
        blocco = (LAB / "LettureBanco.jsx").read_text() \
            .split('data-testid="lab-banco"')[1][:400]
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
        # Evoluta FA1 (FARO, 30/8): fermare la corsa non «tiene la
        # nota» — CATTURA la frequenza (cancella la rampa) e fa
        # SILENZIO. La decisione RZ del founder vale ovunque.
        assert "const qui = lab.generatore.stato().freq;" in ui
        assert "imposta({ freq: qui })" in ui, \
            "il fermo deve cancellare la rampa sul punto catturato"
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
        for stanza in LAB.glob("Lab*.jsx"):
            pag = stanza.read_text()
            assert "lab-sweep" not in pag and "secondi:" not in pag, \
                f"{stanza.name}: i comandi dello sweep sono usciti dal generatore"


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
        hook = (LAB / "usaLab.js").read_text()
        assert "const [suona, setSuona] = useState(false);" in hook
        assert "onSuono={setSuona}" in (LAB / "LabBanco.jsx").read_text()
        blocco = (LAB / "LettureBanco.jsx").read_text()
        assert "? 'le letture sono ferme — il suono continua'" in blocco
        # l'avviso fa RIDISEGNARE, ma la verita' si chiede al motore:
        # cosi' regge anche se il suono si spegnesse fuori dal pulsante
        assert "labRef.current" in hook and ".stato().attivo" in hook
        assert "suonaDavvero" in hook
        assert ": 'le letture sono ferme'" in blocco
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
        # LU (28/8): la casa con le stanze — sei rotte lazy, tutte
        # prima del catch-all
        for stanza in ("LabSala", "LabBanco", "LabOrecchio",
                       "LabRitratto", "LabMeraviglie", "LabRisonanze"):
            assert f'lazy(() => import("./features/frequenze/lab/{stanza}"))' in src, \
                f"manca la rotta lazy di {stanza}"
        assert src.index('path="/sound/lab"') < src.index('path="/sound/*"'), \
            "il catch-all mangia il Lab"
        assert src.index('path="/sound/lab/risonanze"') < src.index('path="/sound/*"')

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
        assert "stanze" in meta.get("content_html", "").lower(), \
            "la Sala non racconta le stanze ai crawler"
        # LU (28/8): OGNI stanza ha il suo indirizzo e la sua meta —
        # la trappola di /sound/visual non si paga per sei
        for stanza in ("banco", "orecchio", "ritratto",
                       "meraviglie", "risonanze"):
            m = await shell.resolve_meta(f"/sound/lab/{stanza}")
            assert m is not None, f"la shell non conosce la stanza {stanza}"
            assert m["canonical"].endswith(f"/sound/lab/{stanza}")
            assert m.get("content_html"), f"{stanza}: senza corpo per i crawler"
        # e una stanza inventata e' un 404 vero
        assert await shell.resolve_meta("/sound/lab/inventata") is None

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
        telaio = (LAB / "Stanza.jsx").read_text()
        assert "SafetyCurtain" in telaio and "SafetyLine" in telaio, \
            "le controindicazioni non valgono nelle stanze"

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
        assert "ottieniXY" in (LAB / "usaLab.js").read_text()
        assert "ottieniXY={ottieniXY}" in (LAB / "LabBanco.jsx").read_text()
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

class TestOrecchioLb2:
    """LB2 (27/8/2026) — il microfono entra nel Lab. Collaudato con
    buffer sintetici (armoniche + 5% rumore): 110→109.94,
    137.42→137.35, 440→440.08, 1750→1750.14 — entro ±0.1 Hz; il
    silenzio e il rumore puro rispondono null."""

    def test_i_filtri_da_videochiamata_sono_spenti(self):
        """Qui si vince o si perde: echo cancellation, noise
        suppression e auto gain mangiano code di risonanza, parziali
        acuti e dinamica — esattamente cio' che si vuole misurare."""
        src = (LAB / "motore.js").read_text()
        assert "echoCancellation: false" in src
        assert "noiseSuppression: false" in src
        assert "autoGainControl: false" in src

    def test_il_mic_e_un_osservato_mai_una_sorgente_sonora(self):
        """La privacy e' un fatto di GRAFO: il nodo del microfono va
        solo all'analyser (via analisi.sorgente) — mai verso master o
        ponte. Niente feedback, niente audio in uscita."""
        src = (LAB / "motore.js").read_text()
        a = src.index("orecchio: {")
        blocco = src[a:src.index("analisi: {", a)]
        assert "createMediaStreamSource" in blocco
        assert ".connect(master" not in blocco and ".connect(ponte" not in blocco
        # e chiudere ferma DAVVERO la cattura (la spia del browser si spegne)
        assert "getTracks().forEach((t) => t.stop())" in blocco
        # spegnere il banco chiude anche l'orecchio
        assert "lab.orecchio.chiudi();" in src

    def test_l_accordatore_e_matematica_pura(self):
        """React-free, senza nodi audio: riceve campioni, risponde
        Hz. Anti-ottava (primo picco ≥90% del max), vertice
        parabolico, normalizzazione per sovrapposizione (senza, i lag
        lunghi partono svantaggiati: misurato 137.42→137.72)."""
        src = (LAB / "accordatore.js").read_text()
        codice = re.sub(r"/\*.*?\*/", " ", src, flags=re.S)
        codice = re.sub(r"^\s*//.*$", " ", codice, flags=re.M)
        assert "react" not in codice.lower()
        assert "createOscillator" not in src and "AudioContext" not in src
        assert "QUASI_MASSIMO" in src, "l'anti-ottava e' sparito"
        assert "(acc / conta) / energiaMedia" in src, \
            "la normalizzazione per sovrapposizione e' sparita: bias sui lag lunghi"
        assert "return null" in src, "un accordatore che inventa numeri non e' uno strumento"

    def test_le_note_hanno_una_tabella_sola(self):
        """notaVicina e' nata nel Generatore e l'Orecchio la usa:
        fonte unica in note.js, niente doppioni."""
        gen = (LAB / "Generatore.jsx").read_text()
        orecchio = (LAB / "Orecchio.jsx").read_text()
        assert "from './note'" in gen and "from './note'" in orecchio
        assert "const NOTE = [" not in gen, "la tabella e' tornata doppia"

    def test_il_pannello_rispetta_i_contratti(self):
        """Niente nodi audio nel componente; l'errore del permesso ha
        una voce garbata; la didascalia c'e' e dice la verita' sulla
        privacy; la lettura passa dal giro del banco (iscrivi), non da
        un orologio suo."""
        src = (LAB / "Orecchio.jsx").read_text()
        assert "createMediaStreamSource" not in src and "getUserMedia" not in src
        assert "NotAllowedError" in src
        assert "lab-didascalia" in src
        assert "non lascia" in src, "la promessa di privacy e' sparita dal pannello"
        assert "iscrivi(" in src and "setInterval" not in src
        # smontare il pannello chiude il microfono
        assert "orecchio.chiudi()" in src

class TestRitrattoLb3:
    """LB3 (27-28/8/2026) — il Ritratto. Collaudato con una campana
    sintetica (doppietto 220/221.8, rapporti 1·2.7·4.9, T60 8/4/2 s,
    rumore): fondamentale 220.00, battito 1.80 Hz, T60 8.12/4.01/2.06
    in 105 ms; e end-to-end vivo: registrate le voci del banco a
    330 e 700.5 Hz → il ritratto legge 330.00 e 700.50."""

    def test_il_ritrattista_e_matematica_pura(self):
        """FFT nostra (radix-2), Goertzel per gli inviluppi, vertice
        parabolico: niente dipendenze, niente nodi audio, niente
        React nel codice."""
        src = (LAB / "ritrattista.js").read_text()
        codice = re.sub(r"/\*.*?\*/", " ", src, flags=re.S)
        codice = re.sub(r"^\s*//.*$", " ", codice, flags=re.M)
        assert "react" not in codice.lower()
        assert "createOscillator" not in codice and "AudioContext" not in codice
        assert "export function fft" in src
        assert "goertzel" in src
        assert "DOPPIETTO_HZ" in src, "i doppietti sono spariti dal ritratto"

    def test_il_nome_schiva_la_collisione_del_mac(self):
        """Trappola pagata: Ritratto.jsx e ritratto.js COLLIDONO sul
        filesystem case-insensitive del Mac e CRA rifiuta l'import
        («Cannot find module»). Il modulo matematico si chiama
        ritrattista.js — e ritratto.js non deve rinascere."""
        assert (LAB / "ritrattista.js").exists()
        assert not (LAB / "ritratto.js").exists(), \
            "ritratto.js e' rinato: collide con Ritratto.jsx sul Mac"

    def test_il_suono_tenuto_ha_il_suo_ramo(self):
        """In un suono continuo il «picco» cade dove capita: se dopo
        resta meno di un secondo si analizza la parte lunga e il
        fondo-stanza tace (non c'e' un prima del colpo)."""
        src = (LAB / "ritrattista.js").read_text()
        assert "continuo = true" in src
        assert "continuo," in src               # il ritratto lo dichiara

    def test_la_registrazione_cattura_l_osservato(self):
        """analisi.registra prende i campioni CRUDI di cio' che il
        banco guarda (mic o voci) — l'uscita dello ScriptProcessor
        va nel master a guadagno ZERO (deve battere, non suonare):
        mai ctx.destination."""
        src = (LAB / "motore.js").read_text()
        a = src.index("registra(secondi")
        blocco = src[a:a + 2200]
        assert "createScriptProcessor" in blocco
        assert "muto.gain.value = 0" in blocco
        assert "ctx.destination" not in blocco
        # il tetto: mai piu' di 12 secondi in RAM
        assert "12" in blocco

    def test_il_pannello_rispetta_i_contratti(self):
        """Niente matematica nel componente (vive nel ritrattista),
        tabella dentro uno scroll orizzontale (telefono), la nota di
        onesta' sul microfono c'e', la didascalia pure."""
        src = (LAB / "Ritratto.jsx").read_text()
        assert "from './ritrattista'" in src
        assert "createScriptProcessor" not in src and "fft" not in src
        assert "lab-ritratto-scroll" in src
        assert "colora lo spettro" in src, "la nota di onesta' e' sparita"
        assert "lab-didascalia" in src
        css = (LAB / "lab.css").read_text()
        assert "overflow-x:auto" in css.split(".lab-ritratto-scroll")[1][:60]

class TestFonderiaLb4:
    """LB4 (28/8/2026) — la campana rifatta. La prova del CERCHIO,
    misurata al collaudo: ritratto → fonderia → ritratto restituisce
    gli stessi numeri (220 Hz col doppietto a 1.80, T60 8.11/4.01/2.10
    su 8/4/2) — la rifusione e' fedele per costruzione."""

    def test_la_fonderia_e_matematica_pura(self):
        """React-free, nessun contesto proprio: riceve ctx e USCITA —
        nel Lab e' lab.ingresso (→ master → ponte), nell'export
        l'OfflineAudioContext. La regola del ponte resta intatta."""
        src = (LAB / "fonderia.js").read_text()
        codice = re.sub(r"/\*.*?\*/", " ", src, flags=re.S)
        codice = re.sub(r"^\s*//.*$", " ", codice, flags=re.M)
        assert "react" not in codice.lower()
        assert "new AudioContext" not in src and "webkitAudioContext" not in src
        assert "ctx.destination" not in codice.replace(
            "campana(ctx, ctx.destination", ""), \
            "la fonderia decide lei dove va il suono"

    def test_il_doppietto_rinasce_da_coppia_vera(self):
        """Il battimento non e' un effetto: e' la COPPIA di
        oscillatori del doppietto (il ritratto porta anche il db del
        gemello, aggiunto apposta in LB4)."""
        fond = (LAB / "fonderia.js").read_text()
        assert "p.doppietto" in fond and "doppietto.hz" in fond
        rit = (LAB / "ritrattista.js").read_text()
        assert "db: +p.doppietto.db.toFixed(1)" in rit, \
            "il doppietto ha perso la sua ampiezza: la rifusione suonera' finta"

    def test_colpo_e_tenuto_e_il_tetto_di_uscita(self):
        """Due modi dichiarati; la somma delle ampiezze non supera il
        tetto (USCITA_PICCO): due campane rifuse non fanno clipping."""
        src = (LAB / "fonderia.js").read_text()
        assert "'colpo'" in src and "ATTACCO_TENUTO" in src
        assert "USCITA_PICCO" in src
        assert "exponentialRampToValueAtTime" in src, \
            "il decadere del colpo non e' piu' esponenziale"

    def test_l_ingresso_del_banco(self):
        """lab.ingresso: la presa per i suonatori di banco (rifusione,
        A/B dell'originale) — entra nel master, quindi ponte e
        analyser la vedono come tutto il resto."""
        src = (LAB / "motore.js").read_text()
        assert "ingresso.connect(master)" in src
        assert "ingresso," in src           # esposto sul lab

    def test_il_pannello_ha_l_ab_e_l_onesta(self):
        """A/B originale/colpo/tenuto, parziali accendibili, respiro,
        WAV per tutti; la consegna in libreria SOLO per il system
        admin (la scrittura della libreria e' sua per contratto FQ2).
        E la didascalia dice cosa la rifusione NON cattura."""
        src = (LAB / "Ritratto.jsx").read_text()
        for tid in ("lab-ab-originale", "lab-ab-colpo", "lab-ab-tenuto",
                    "lab-fonderia-wav"):
            assert f'data-testid="{tid}"' in src
        # FA3 (FARO, 30/8): la consegna in libreria e' USCITA dalla
        # stanza — il gesto e' il quaderno; l'admin carica da
        # /admin/sound. (Era gia' solo-admin: il founder la vedeva
        # perche' loggato da admin.)
        assert "lab-fonderia-libreria" not in src, \
            "la consegna in libreria e' tornata nella stanza (FA3)"
        assert "uploadSound" not in src
        # riformulata col caso «aummm»: l'onesta' su cio' che la
        # rifusione non cattura resta, con parole nuove
        assert "non cattura" in src, "l'onesta' sui limiti e' sparita"

class TestVestitoLb7:
    """LB7 (28/8/2026) — il vestito degli strumenti: estetica da
    strumentazione vera, tutta canvas+CSS, zero dipendenze."""

    def test_l_oscilloscopio_ha_la_scia_al_fosforo(self):
        """La scia non e' decorazione, e' informazione (un segnale
        stabile lascia una scia sottile): livello fuori schermo che
        sbiadisce con destination-out, traccia viva col bagliore."""
        src = (LAB / "Oscilloscopio.jsx").read_text()
        assert "destination-out" in src, "la scia al fosforo e' sparita"
        assert "shadowBlur" in src, "il bagliore della traccia e' sparito"

    def test_lo_spettro_ha_velo_e_quota(self):
        """L'area sotto la cresta si spegne in GRADIENTE verso il
        fondo (non piu' un velo piatto), e il picco porta la sua
        quota in Hz accanto alla tacca d'oro."""
        src = (LAB / "Spettro.jsx").read_text()
        assert "createLinearGradient" in src
        assert "fillText(testo" in src, "la quota del picco e' sparita"

    def test_lo_spettrogramma_canta_in_oro(self):
        """La rampa del mondo: NOTTE → acqua → ORO → osso. Quattro
        fermate della casa, niente arcobaleni; l'oro arriva solo dove
        l'energia canta (misurato: 440 Hz a mezza ampiezza sta
        sull'acqua, il fondo e' notte [10,22,30])."""
        src = (LAB / "Spettrogramma.jsx").read_text()
        assert "NOTTE" in src
        assert "tinte.lamp" in src, "la rampa ha perso la fermata d'oro"

    def test_le_micro_transizioni(self):
        """I comandi si muovono con la calma delle rampe del suono:
        transizioni brevi su bottoni e selettori, l'ombra interna
        delle tele, il respiro del numerone."""
        css = (LAB / "lab.css").read_text()
        assert "transition:color .18s ease" in css
        assert "inset 0 2px 14px" in css, "le tele hanno perso l'ombra interna"

class TestMeraviglieLb5:
    """LB5 (28/8/2026) — le meraviglie oneste. Collaudate una per una
    (RMS acceso/spento): tutte suonano e tutte tacciono al secondo
    click; le didascalie si aprono con l'esperimento."""

    def test_i_fenomeni_sono_react_free_e_dal_ponte(self):
        """fenomeni.js: matematica e nodi, niente React; il suono
        entra SOLO da lab.ingresso o dalle voci del banco — mai
        ctx.destination. (Si chiama fenomeni.js e non meraviglie.js:
        la trappola case-insensitive del Mac non si paga due volte.)"""
        src = (LAB / "fenomeni.js").read_text()
        codice = re.sub(r"/\*.*?\*/", " ", src, flags=re.S)
        codice = re.sub(r"^\s*//.*$", " ", codice, flags=re.M)
        assert "react" not in codice.lower()
        assert "ctx.destination" not in codice
        assert "lab.ingresso" in src
        assert not (LAB / "meraviglie.js").exists(), \
            "meraviglie.js collide con Meraviglie.jsx sul Mac"

    def test_ogni_meraviglia_ha_il_cartellino_e_la_didascalia(self):
        """La regola LB: nessun modulo muto — e nessuna meraviglia
        senza cartellino di verita' (A documentato / C tradizione)."""
        src = (LAB / "fenomeni.js").read_text()
        import json as _
        voci = re.findall(r"cartellino: '([AC])'", src)
        didascalie = src.count("didascalia: '")
        righe = src.count("riga: '")
        assert len(voci) >= 12, "il catalogo si e' svuotato"
        assert didascalie == len(voci) and righe == len(voci), \
            "una meraviglia e' rimasta muta"
        # phi porta il cartellino C: il simbolo e' tradizione
        a = src.index("id: 'phi'")
        assert "cartellino: 'C'" in src[a:a + 200]

    def test_l_orbita_vive_nel_motore_audio(self):
        """Il vortice non e' un timer: due LFO in QUADRATURA ESATTA
        (coseno via PeriodicWave) sugli AudioParam del panner — il
        moto continua a schermo spento. L'unico orologio dichiarato
        e' quello di Shepard, e la didascalia lo dice."""
        src = (LAB / "fenomeni.js").read_text()
        assert "lfoQuadratura" in src
        assert "panningModel = 'HRTF'" in src
        a = src.index("function vortice")
        assert "setInterval" not in src[a:src.index("function rotazioneTesta")]
        b = src.index("id: 'shepard'")
        assert "orologio" in src[b:b + 700].lower()

    def test_la_corda_non_esplode(self):
        """Trappola pagata DUE volte: nel lowpass di WebAudio il Q e'
        in DECIBEL — il default e' un picco sopra l'unita' e l'anello
        di Karplus-Strong si autoalimentava (RMS 2e28). Q a -10 dB e
        ritorno sotto l'unita': misurato 0.022 → 0.0014 in 4 s."""
        src = (LAB / "fenomeni.js").read_text()
        a = src.index("function cordaPizzicata")
        blocco = src[a:a + 1600]
        assert "filtro.Q.value = -10" in blocco, \
            "il Q del biquad e' tornato risonante: l'anello esplode"
        m = re.search(r"ritorno\.gain\.value = (0\.\d+)", blocco)
        assert m and float(m.group(1)) < 1

    def test_i_rapporti_pilotano_il_banco(self):
        """Ottava, quinta e phi non hanno oscillatori propri: parlano
        alle DUE VOCI del banco (il telaio LB1), cosi' il modo XY
        disegna la figura di Lissajous dell'intervallo."""
        src = (LAB / "fenomeni.js").read_text()
        a = src.index("function rapporto")
        blocco = src[a:a + 700]
        assert "generatore.imposta" in blocco and "generatore2.imposta" in blocco
        assert "createOscillator" not in blocco

    def test_il_pannello_e_la_mano(self):
        src = (LAB / "Meraviglie.jsx").read_text()
        assert "from './fenomeni'" in src
        assert "createOscillator" not in src and "AudioContext" not in src
        assert "lab-mer-onesta" in src, \
            "la dichiarazione contro le «frequenze 3D» e' sparita"

class TestCimaticaLb6:
    """LB6 (28/8/2026) — verso la cimatica. Collaudo: trovaPicchi su
    curva sintetica (risonanze iniettate a 220/+8dB e 513/+14dB →
    trovate 221.7 e 509.3, entro il passo della griglia); WAV al byte
    esatto; il passo fine muove la frequenza di 0,1."""

    def test_gli_attrezzi_sono_react_free(self):
        src = (LAB / "cimatica.js").read_text()
        codice = re.sub(r"/\*.*?\*/", " ", src, flags=re.S)
        codice = re.sub(r"^\s*//.*$", " ", codice, flags=re.M)
        assert "react" not in codice.lower()
        # i WAV escono da un contesto OFFLINE (un file, non un altoparlante)
        assert "OfflineAudioContext" in src
        assert "linearRampToValueAtTime" in src, \
            "i toni per gli ampli hanno perso la rampa: fronte secco"

    def test_il_quaderno_e_dichiarato_e_mai_bloccante(self):
        """Gli esperimenti restano SU QUESTO DISPOSITIVO (localStorage
        dentro try/catch: un browser che lo nega non rompe il banco) —
        e il pannello lo dice."""
        src = (LAB / "cimatica.js").read_text()
        assert "localStorage" in src
        assert src.count("try {") >= 3, "il quaderno puo' bloccare il banco"
        pann = (LAB / "Risonanze.jsx").read_text()
        assert "su questo dispositivo" in pann

    def test_il_cercatore_chiude_il_cerchio(self):
        """Genera (sweep della voce A) → eccita → ascolta (il mic e'
        OBBLIGATORIO: senza, si sentirebbe solo se stessi, e il
        pannello lo dice) → misura (Goertzel alla frequenza CORRENTE
        dello sweep, letta dal motore: una sola verita')."""
        # Evoluta col ciclo RZ (28/8): il microfono non e' piu'
        # OBBLIGATORIO — senza, la misura passa alla via A OCCHIO
        # (sweep + gli occhi dell'utente), il metodo della moneta.
        src = (LAB / "Risonanze.jsx").read_text()
        assert "orecchio.attivo()" in src and "orecchio.apri()" in src
        assert "goertzel" in src
        assert "generatore.stato()" in src, \
            "la frequenza della misura non viene piu' dal motore"
        assert "iscrivi(" in src and "setInterval" not in src

    def test_l_onesta_dell_altoparlante(self):
        """Sotto i ~200 Hz l'altoparlante di un telefono non muove
        niente: il WAV per gli ampli esiste APPOSTA, e la nota c'e'."""
        src = (LAB / "Risonanze.jsx").read_text()
        assert "non muove niente" in src
        assert "lab-ris-wav-sweep" in src

    def test_il_passo_fine_della_cimatica(self):
        """I pattern di Chladni vivono in finestre strette: ±0,1 Hz
        e' un gesto sul Generatore, non un numero da riscrivere."""
        src = (LAB / "Generatore.jsx").read_text()
        assert "lab-passofine" in src
        assert "[-1, -0.1, 0.1, 1]" in src

class TestOlisticaLb8:
    """LB8, RISCRITTA col ciclo LU (28/8): l'olistica non e' piu'
    l'indice di una pagina-magazzino — e' la CASA. La Sala accoglie
    (carte con la domanda di ogni stanza, «da dove parto» per
    profili), i percorsi attraversano le stanze con link veri.
    Collaudo dal DOM vivo: 5 carte, 3 profili, 3 percorsi, zero
    link rotti."""

    ROTTE = ("/sound/lab/banco", "/sound/lab/orecchio",
             "/sound/lab/ritratto", "/sound/lab/meraviglie",
             "/sound/lab/risonanze")

    def test_la_sala_accoglie(self):
        src = (LAB / "LabSala.jsx").read_text()
        # niente strumenti nella Sala: accoglie, non suona
        assert "usaLab" not in src and "creaLaboratorio" not in src
        assert 'data-testid="lab-sala-stanze"' in src
        # ogni carta porta a una rotta vera e dice la sua DOMANDA
        for rotta in self.ROTTE:
            assert f"via: '{rotta}'" in src, f"manca la carta di {rotta}"
        assert src.count("domanda:") == 5
        assert 'data-testid="lab-sala-profili"' in src, \
            "il «da dove parto?» per profili e' sparito"

    def test_i_percorsi_attraversano_le_stanze(self):
        """I passi portano alle stanze con <Link> veri (non piu'
        ancore di pagina), e il filo si ricorda con sessionStorage
        dentro try/catch (mai bloccante)."""
        src = (LAB / "Percorsi.jsx").read_text()
        assert "createOscillator" not in src and "AudioContext" not in src
        assert src.count("id: '") == 3, "un percorso e' sparito"
        assert "from 'react-router-dom'" in src
        for rotta in set(re.findall(r"'(/sound/lab/[a-z]+)'", src)):
            assert rotta in self.ROTTE, f"passo verso una stanza che non c'e': {rotta}"
        assert "sessionStorage" in src and "catch" in src

    def test_ogni_stanza_risponde_alla_sua_domanda(self):
        """Il telaio (Stanza.jsx) impone la testata didattica: la
        DOMANDA, il «perche' ti interessa» per il neofita, le tre
        azioni concrete — PRIMA degli strumenti. E il ponte col
        glossario c'e' in ogni stanza."""
        telaio = (LAB / "Stanza.jsx").read_text()
        assert 'data-testid="lab-domanda"' in telaio
        assert "Perché ti interessa" in telaio
        assert "Cosa puoi fare qui" in telaio
        assert "/sound/impara/glossario" in telaio, \
            "il ponte col glossario e' sparito dal telaio"
        assert 'data-testid="lab-ritorno-sala"' in telaio, \
            "da una stanza non si torna alla Sala"
        for stanza in ("LabBanco", "LabOrecchio", "LabRitratto",
                       "LabMeraviglie", "LabRisonanze"):
            pag = (LAB / f"{stanza}.jsx").read_text()
            assert "domanda=" in pag and "perche=" in pag, \
                f"{stanza}: senza testata didattica"
            assert "azioni={[" in pag, f"{stanza}: senza azioni concrete"

    def test_il_ciclo_di_vita_e_uno_per_tutte_le_stanze(self):
        """usaLab: il motore nasce al gesto, si spegne allo
        smontaggio, scongela — UNA disciplina, non cinque copie."""
        hook = (LAB / "usaLab.js").read_text()
        assert "labRef.current?.spegni(); congela(false);" in hook
        for stanza in ("LabBanco", "LabOrecchio", "LabRitratto",
                       "LabMeraviglie", "LabRisonanze"):
            pag = (LAB / f"{stanza}.jsx").read_text()
            assert "useLab()" in pag, f"{stanza}: non usa il ciclo di vita comune"
            assert "creaLaboratorio" not in pag, \
                f"{stanza}: si fabbrica il motore da sola"

class TestVoceDelFounder:
    """Consolidamento 28/8 — il caso vero del founder: registrava
    «aummm» e il Lab rispondeva «troppo piano». Due difetti trovati e
    curati con evidenza:
    1) il microfono era chiuso e il banco ritraeva il silenzio delle
       sorgenti spente (riprodotto: stesso messaggio del founder);
    2) una voce con vibrato mette nello spettro le BANDE LATERALI
       (146 con satelliti a 136/151/156) che sporcavano la tabella.
    Dopo: aummm sintetico → 146/292/438/584 esatti; campana col
    doppietto 1.8 intatta; verdetto del silenzio dedicato."""

    def test_il_ritratto_apre_l_orecchio_da_solo(self):
        """Se nessuna sorgente suona, registrare significa VOLERE il
        microfono: lo si apre senza chiedere un click in un altro
        pannello; se viene negato lo si dice SUBITO, senza sprecare
        sei secondi di conto."""
        src = (LAB / "Ritratto.jsx").read_text()
        assert "orecchio.apri()" in src
        a = src.index("const suonaBanco")
        blocco = src[a:a + 700]
        assert "generatore2.stato().attivo" in src[a - 200:a + 200]
        assert "return;" in blocco, "il mic negato non ferma il conto"
        assert "serve il microfono" in src

    def test_i_verdetti_sono_onesti(self):
        """Il silenzio ha una cura diversa dal «troppo piano»: si
        guarda il picco della cattura e si dice il vero."""
        src = (LAB / "Ritratto.jsx").read_text()
        assert "Ho ascoltato solo silenzio" in src
        assert "troppo piano o troppo breve" in src
        assert "picco < 0.003" in src, \
            "il verdetto non distingue piu' il silenzio dal piano"

    def test_le_bande_laterali_restano_fuori_dal_ritratto(self):
        """Il vibrato di una voce mette picchi VERI a ±(4-10) Hz dal
        parziale: sono la firma della modulazione, non modi. Un picco
        ≥6 dB piu' debole e vicino (fra i doppietti e 15 Hz) a uno
        forte si lascia fuori; i doppietti veri (<5 Hz) e i modi
        distinti (>15 Hz) non si toccano — la campana resta intatta."""
        src = (LAB / "ritrattista.js").read_text()
        assert "q.db > p.db + 6" in src
        assert ">= DOPPIETTO_HZ" in src and "< 15" in src

    def test_l_orecchio_non_possiede_lo_stato(self):
        """Il microfono puo' aprirlo anche il Ritratto: il pannello
        Orecchio LEGGE lo stato dal motore a ogni giro e si allinea
        (accordatore vivo anche se l'ha aperto qualcun altro).
        ottieniVivo non crea mai il lab: il gesto resta sovrano."""
        src = (LAB / "Orecchio.jsx").read_text()
        assert "ottieniVivo" in src
        assert "attivo !== accesoRef.current" in src, \
            "il pannello e' tornato a possedere lo stato del mic"
        hook = (LAB / "usaLab.js").read_text()
        assert "const ottieniVivo = useCallback(() => labRef.current, [])" in hook
        # e le stanze con l'orecchio la passano
        for stanza in ("LabOrecchio.jsx", "LabRitratto.jsx"):
            assert "ottieniVivo={ottieniVivo}" in (LAB / stanza).read_text(), \
                f"{stanza}: l'orecchio non riceve il lab vivo"

class TestViaArmonica:
    """28/8, seconda visita del caso «aummm»: il founder sentiva la
    rifusione «diversa, anche gli Hz». Vero: una voce con vibrato
    (±1,2%) spezzava le armoniche in bande di modulazione
    (432.8/438/443.2 attorno alla terza) e la copia era stonata e
    immobile. La cura e' un CAMBIO DI STRUMENTO per i suoni intonati.
    Evidenze del collaudo: voce vibrata → armoniche ESATTE
    146.06/292.11/438.17… con vibrato misurato ±1.24 a 4.7 Hz; voce
    ferma → vibrato null; bordone 330+700.5 → resta modale; campana →
    intatta (220, doppietto 1.8, T60 8.13); e il CERCHIO: la
    rifusione tenuta ritratta di nuovo da' 146.00 col vibrato vivo."""

    def test_la_via_si_tenta_sempre_coi_suoi_cancelli(self):
        """Primo giro sbagliato e pagato: la via era agganciata al
        ramo «continuo», che dipende da DOVE cade il picco — una voce
        tenuta col picco a meta' passava dalla via del colpo. Ora si
        tenta sempre, e decidono i TRE cancelli: 60% dei fotogrammi
        intonati, picchi forti sulla serie armonica, almeno due
        armoniche."""
        src = (LAB / "ritrattista.js").read_text()
        assert "_viaArmonica" in src
        assert "if (continuo) {\n    const armonico" not in src, \
            "la via armonica e' tornata prigioniera del ramo continuo"
        assert "intonati.length < quanti * 0.6" in src
        assert "sopra.length / forti.length < 0.7" in src
        assert "tenute.length < 2" in src

    def test_le_armoniche_inseguono_la_fondamentale(self):
        """Il Goertzel non misura a k·f0 fisso: insegue la
        fondamentale DEL FOTOGRAMMA (k·traccia[f]) — cosi' il vibrato
        non diluisce l'ampiezza. E la fondamentale viene
        dall'accordatore: una matematica sola per orecchio e
        ritratto."""
        src = (LAB / "ritrattista.js").read_text()
        assert "k * traccia[f]" in src
        assert "from './accordatore'" in src

    def test_il_vibrato_e_un_dato_e_la_fonderia_lo_risuona(self):
        """profondita' (p95-p5)/2 e velocita' (giri di segno / 2t);
        sotto ±0,3 Hz non si dichiara. La fonderia nel TENUTO monta
        UN LFO alla velocita' misurata e scala la profondita' per il
        rapporto di ogni armonica — misurato sul render: ±0.91 a
        4.5 Hz, armoniche esatte."""
        rit = (LAB / "ritrattista.js").read_text()
        assert "profonditaHz" in rit and "rateHz" in rit
        assert "profonditaHz >= 0.3" in rit
        fond = (LAB / "fonderia.js").read_text()
        assert "ritratto.vibrato" in fond
        assert "* (v.hz / ritratto.fondamentaleHz)" in fond, \
            "il vibrato non scala piu' con l'armonica"

    def test_il_pannello_spiega_colpo_e_tenuto(self):
        """La domanda del founder («ma tenuto cosa sarebbe? e
        colpo?») e' la diagnosi: i due modi ora si spiegano nel
        pannello, e le attese per una voce sono dette («non sara'
        mai te: e' il tuo spettro suonato da onde pure»)."""
        src = (LAB / "Ritratto.jsx").read_text()
        assert 'data-testid="lab-fonderia-spiega"' in src
        assert "oggetto percosso" in src and "strofinata" in src
        assert "non sarà mai «te»" in src
        assert 'data-testid="lab-ritratto-vibrato"' in src, \
            "il vibrato misurato non si mostra"

class TestConsolidamentoRitratto:
    """28/8 — consolidamento del Ritratto su richiesta del founder
    («siamo in grado di registrare e sintetizzare qualsiasi suono?»).
    La risposta onesta e' NO, e il Ritratto ora CLASSIFICA la natura
    del suono e insegna: modi (campana, lattina), intonato (voce, con
    vibrato), melodia (la nota viaggia), soffio (vento, respiro — non
    ha modi da mettere in tabella). Evidenze del collaudo: campana e
    lattina 4/4 modi (doppietto e vite intatti), voce intonata con
    vibrato, melodia 164.7→220.1; il rumore sintetico ~75-80% soffio
    (il classificatore e' probabilistico e lo si dice)."""

    def test_le_quattro_nature_esistono(self):
        src = (LAB / "ritrattista.js").read_text()
        for natura in ("'soffio'", "'melodia'", "'intonato'", "'modi'"):
            assert f"natura: {natura}" in src, f"manca la natura {natura}"

    def test_l_ordine_dei_giudici(self):
        """La via armonica parla PRIMA del giudice del soffio: chi e'
        intonato esce subito, e il giudice puo' essere severo senza
        bocciare una voce."""
        src = (LAB / "ritrattista.js").read_text()
        assert src.index("_viaArmonica(campioni") \
            < src.index("_qualcosaDiFermo(campioni"), \
            "il giudice del soffio parla prima della via armonica"

    def test_il_giudice_del_soffio_e_fisica_non_soglie(self):
        """Cinque giri di collaudo per arrivarci (tutti nel codice):
        STABILITA' fra finestre ADIACENTI (i modi di una lattina
        muoiono presto; il periodogramma del rumore e' indipendente
        anche fra finestre attaccate) + COERENZA del decadere
        (residuo dal fit lineare, con la serie TRONCATA al ginocchio
        dove il modo muore nel rumore)."""
        src = (LAB / "ritrattista.js").read_text()
        assert "_qualcosaDiFermo" in src
        assert "cime(da + W)" in src, \
            "le finestre non sono piu' adiacenti: la lattina torna soffio"
        assert "massimo - 40" in src, \
            "il troncamento al ginocchio e' sparito: la lattina torna soffio"
        assert "<= 2.6" in src

    def test_i_verdetti_maestro_nel_pannello(self):
        """Soffio e melodia non sono errori: sono lezioni — col dato
        misurato (picco in dB, da nota a nota) e il gesto giusto da
        provare."""
        src = (LAB / "Ritratto.jsx").read_text()
        assert 'data-testid="lab-ritratto-soffio"' in src
        assert 'data-testid="lab-ritratto-melodia"' in src
        assert "colpirlo" in src, "il soffio non insegna il gesto del colpo"
        assert "una sola altezza" in src, \
            "la melodia non insegna il gesto della nota ferma"

    def test_la_griglia_e_le_corde(self):
        """Desktop: l'esito in DUE colonne (scena a sinistra, tabella
        e rifusione a destra) — la picture e' immediata; sotto i
        1080px si torna in colonna. Le corde: un canvas col contratto
        dei pannelli (iscrivi, niente nodi audio, niente rAF suo)."""
        src = (LAB / "Ritratto.jsx").read_text()
        assert "lab-ritratto-griglia" in src
        assert "<RitrattoVisual" in src
        assert 'data-testid="lab-ritratto-lettura"' in src
        vis = (LAB / "RitrattoVisual.jsx").read_text()
        assert "iscrivi(" in vis
        assert "createOscillator" not in vis and "AudioContext" not in vis
        assert "requestAnimationFrame" not in vis
        css = (LAB / "lab.css").read_text()
        assert "grid-template-columns:minmax(320px,5fr) minmax(360px,6fr)" in css
        assert "@media (max-width:1080px)" in css

class TestSottoperiodo:
    """28/8, esperimento del founder: rifusione col solo parziale a
    4884 Hz e l'accordatore diceva «1628» — 4884/3 esatto. Un tono
    sopra maxHz ha il periodo vero FUORI dal campo di ricerca e
    l'autocorrelazione aggancia un multiplo. Cura: il controllo del
    sottoperiodo (lag/2..lag/8 anche sotto il campo, promosso se la
    correlazione regge all'85%). Evidenze: 4884.31→4884.8 (era 1628),
    2500→2499.7 (era 1250), e i timbri ricchi NON vengono promossi
    all'ottava (146 e 220 con armoniche restano 145.9/219.9); il
    cerchio del founder: rifusione a un parziale → letta 4885."""

    def test_il_controllo_esiste_e_promuove_il_periodo_vero(self):
        src = (LAB / "accordatore.js").read_text()
        assert "SOTTOPERIODO" in src
        assert "lagFine / k" in src, "il controllo dei sottoperiodi e' sparito"
        assert ">= 0.85 * b" in src, \
            "la soglia di promozione e' cambiata: rischio ottave promosse"
        # dal piu' corto che regge: k parte da 8 e scende
        assert "let k = 8; k >= 2; k--" in src

    def test_lo_strumento_non_mente_fuori_campo(self):
        """La regola scritta nel codice: uno strumento risponde
        giusto o tace — mai un numero sbagliato con la faccia
        sicura."""
        src = (LAB / "accordatore.js").read_text()
        assert "mai un numero sbagliato" in src

class TestCicloRz:
    """Ciclo RZ (28/8/2026) — le Risonanze come ciclo vivo, dal caso
    della moneta del founder (fermava lo sweep quando la vedeva
    danzare e il momento andava perso). Collaudo end-to-end: sweep a
    occhio → fermo a 78.0 (=freqOra esatta) col TONO CHE RESTA (RMS
    0.353) → passo fine (due tocchi rapidi si SOMMANO: 79.2) →
    scoperta «moneta sul telefono» nel quaderno → riaperta dal
    quaderno dopo un reload → fermata."""

    def test_il_fermo_e_una_misura(self):
        """Rivista col founder (28/8, stessa giornata): «quando
        stoppiamo il suono si deve fermare». Il fermo CATTURA la
        frequenza (prima si legge, poi si spegne) e fa SILENZIO —
        risentirla e' un gesto esplicito (▶ Tienila). Misurato:
        cattura 73,1 → fine +1 → Tienila suona 74,1 nello stesso
        tick (il numero vive in un ref sincrono); ✕ chiude e tace."""
        src = (LAB / "Risonanze.jsx").read_text()
        assert "fermaLoSweep" in src
        assert "'■ Ferma QUI'" in src
        a = src.index("const fermaLoSweep")
        blocco = src[a:a + 600]
        assert "generatore.ferma()" in blocco, \
            "il fermo non spegne: il founder ha chiesto silenzio"
        assert blocco.index("stato().freq") < blocco.index("generatore.ferma()"), \
            "si spegne PRIMA di leggere: la frequenza catturata e' persa"
        assert 'data-testid="lab-rz-tienila"' in src
        assert 'data-testid="lab-rz-chiudi"' in src
        assert "tonoHzRef" in src, \
            "il numero e' tornato solo stato React: i tocchi rapidi si perdono"

    def test_il_tono_in_mano_ha_le_sue_tre_porte(self):
        """Dal fermo dello sweep, dal ▶ di un picco, dal ▶ del
        quaderno — stessa barra: numerone, passo fine, ampiezza,
        etichetta, salva, ferma."""
        src = (LAB / "Risonanze.jsx").read_text()
        assert 'data-testid="lab-rz-tono"' in src
        assert "`lab-rz-fine-${d}`" in src, \
            "il passo fine ha perso le sue chips"
        # lab-rz-ferma-tono e' diventato lab-rz-tienila (il fermo del
        # founder: ▶/■ un solo interruttore, ✕ per chiudere)
        for tid in ("lab-rz-salva-scoperta", "lab-rz-tienila",
                    "lab-rz-chiudi", "lab-rz-etichetta"):
            assert tid in src, f"manca {tid} nella barra del tono"
        # evoluto con gli interruttori sul posto: il gesto e' alternaQui
        assert "alternaQui(p.hz)" in src, "i picchi hanno perso l'interruttore"
        assert "alternaQui(hz)" in src, "il quaderno ha perso l'interruttore"

    def test_il_passo_fine_parte_dal_motore(self):
        """Due tocchi rapidi leggevano lo stesso stato React e il
        secondo cancellava il primo (misurato: +1 e +0,1 da 78 davano
        78,1). La base viene dal motore, che aggiorna stato.freq in
        modo sincrono."""
        src = (LAB / "Risonanze.jsx").read_text()
        a = src.index("const aggiusta")
        blocco = src[a:a + 600]
        assert "lab.generatore.stato().freq" in blocco
        assert "(tonoHz || 0) + dHz" not in blocco

    def test_la_via_a_occhio_esiste_e_si_dichiara(self):
        """Senza microfono la misura non si nega: sweep a occhio, il
        numerone dice dove sei, e la didascalia consacra il metodo
        («i tuoi occhi sono lo strumento»)."""
        src = (LAB / "Risonanze.jsx").read_text()
        assert "aOcchio = true" in src
        assert "serve il microfono" not in src, \
            "la misura e' tornata a esigere il microfono"
        assert "i tuoi occhi sono lo" in src
        assert 'data-testid="lab-rz-viva"' in src, \
            "il numerone dello sweep e' sparito"

    def test_gli_interruttori_sul_posto_e_il_cruscotto_che_segue(self):
        """UX del founder (28/8): «dai salvataggi clicco play ma per
        stoppare devo tornare su al cruscotto». Ogni ▶ (picchi e
        quaderno) e' un interruttore sul posto (misurato: play dal
        quaderno → chip ■ → stop da li' → silenzio); e la barra del
        tono e' STICKY e OPACA (il pattern del createbar — la regola
        del 27/8: cio' che galleggia non e' mai una finestra)."""
        src = (LAB / "Risonanze.jsx").read_text()
        assert "staSuonando" in src and "alternaQui" in src
        assert src.count("alternaQui(") >= 2, \
            "un ▶ ha perso l'interruttore sul posto"
        css = (LAB / "lab.css").read_text()
        blocco = css.split(".fqz .lab-rz-tono{position:sticky")
        assert len(blocco) == 2, "la barra del tono non e' piu' sticky"
        assert "linear-gradient(168deg,#375B63" in blocco[1][:300], \
            "la barra sticky ha perso l'opacita': finestra sul contenuto"

    def test_il_quaderno_vivo(self):
        """Due tipi di voce (sweep e scoperta etichettata), ogni
        frequenza risuonabile con un tocco, e i quattro passi del
        ciclo in testata."""
        src = (LAB / "Risonanze.jsx").read_text()
        assert "tipo: 'scoperta'" in src and "tipo: 'sweep'" in src
        assert "lab-quaderno-hz" in src
        assert 'data-testid="lab-rz-passi"' in src



class TestOndaViva:
    """L'ONDA VIVA (29/8/2026) — la forma d'onda della fonderia.

    Desiderio del founder: «dopo che si e' sintetizzato un suono e lo
    si ascolta, mostrare l'onda di quel suono in movimento in maniera
    professionale e stilosa». Professionale = campioni veri dal master
    (analisi.tempo) agganciati col TRIGGER dell'Oscilloscopio —
    importato, mai ricopiato. Collaudato nel pane: tenuto → classe
    viva + «agganciata» + 49k pixel fuori asse; colpo → si richiude
    da sola alla morte del suono.
    """

    def test_l_onda_viva_usa_le_verita_del_banco(self):
        """Trigger dell'Oscilloscopio + quadro: una verita', un ciclo."""
        src = (LAB / "OndaViva.jsx").read_text()
        assert "import { trigger } from './Oscilloscopio'" in src, \
            "l'aggancio deve essere UNO: si importa, non si ricopia"
        assert "import { iscrivi } from './quadro'" in src, \
            "un solo requestAnimationFrame per tutto il banco"
        assert "analisi.tempo(" in src, \
            "l'onda deve venire dai campioni VERI del master"
        osc = (LAB / "Oscilloscopio.jsx").read_text()
        assert "export function trigger" in osc, \
            "Oscilloscopio non esporta piu' il trigger — OndaViva orfana"

    def test_l_onda_appare_nel_ritratto_quando_suona(self):
        """Nel Ritratto, legata a inSuono: si apre col suono e basta."""
        src = (LAB / "Ritratto.jsx").read_text()
        assert "import OndaViva from './OndaViva'" in src
        # Evoluta col quaderno dei ritratti (29/8): la tela della
        # fonderia segue SOLO i suoi tre gesti (il quaderno ha la sua)
        assert "['orig', 'colpo', 'tenuto'].includes(inSuono) ? inSuono : null" in src, \
            "l'onda della fonderia deve seguire solo orig/colpo/tenuto"
        assert "ottieniAnalisi={ottieniAnalisi}" in src
        assert "__fqzRitratto" in src, \
            "senza il gancio di collaudo la fonderia non si prova senza mic"

    def test_il_vestito_si_apre_e_si_chiude(self):
        """CSS: chiusa nel silenzio (max-height 0), aperta da viva,
        con la transizione che rende il gesto fluido."""
        css = (LAB / "lab.css").read_text()
        base = css.split(".fqz .lab-ondaviva{")
        assert len(base) == 2, "manca (o e' doppia) la regola base"
        assert "max-height:0" in base[1][:200], "da spenta deve essere chiusa"
        viva = css.split(".fqz .lab-ondaviva.viva{")
        assert len(viva) == 2 and "max-height:200px" in viva[1][:80], \
            "da viva deve aprirsi"
        assert "transition:max-height" in base[1][:300], \
            "senza transizione l'apertura e' uno scatto"


class TestQuadernoRitratti:
    """IL QUADERNO DEI RITRATTI (29/8/2026) — il registro del Ritratto.

    Desiderio del founder: «salvare dei toni come nelle risonanze, un
    registro anche li'». La voce e' un ritratto INTERO (esito + spenti
    + respiro): salvi la campana una volta, la rifondi quando vuoi
    senza microfono. Collaudato nel pane: salva → riga «campana di
    prova · 220 Hz · 3 modi», tenuto dal quaderno → chip ■ + onda viva
    del quaderno con l'etichetta, stop sul posto, Apri → Originale
    disabilitato con l'onesta' («ricorda la tabella, non la voce»),
    sopravvive al cambio pagina, x pulisce lo store.
    """

    def test_lo_storage_vive_in_fonderia_con_chiave_propria(self):
        """Chiave separata dal quaderno RZ, letture mai bloccanti."""
        src = (LAB / "fonderia.js").read_text()
        assert "'fqz_lab_ritratti'" in src, "manca la chiave del quaderno"
        for fn in ("leggiRitratti", "salvaRitratto", "cancellaRitratto"):
            assert f"export function {fn}" in src, f"manca {fn}"
        assert src.count("try {") >= 3, \
            "lo storage deve essere try/catch: mai bloccare il banco"
        # la chiave RZ resta in cimatica.js e non si confonde
        assert "'fqz_lab_quaderno'" not in src, \
            "il quaderno dei ritratti NON deve rubare la chiave delle Risonanze"

    def test_la_voce_ricorda_come_la_sentivi(self):
        """Si salva esito + spenti + respiro: la rifusione salvata
        suona come quando l'hai salvata."""
        src = (LAB / "Ritratto.jsx").read_text()
        assert "esito, spenti, respiro," in src, \
            "la voce deve portare anche spenti e respiro"
        assert "lab-ritratto-etichetta" in src and "lab-ritratto-salva" in src

    def test_il_registro_suona_sul_posto_e_vive_da_solo(self):
        """La lezione RZ: ogni ▶ e' un interruttore sul posto; e il
        quaderno si vede anche senza un ritratto appena fatto."""
        src = (LAB / "Ritratto.jsx").read_text()
        assert "suonaDalQuaderno" in src and "apriDalQuaderno" in src
        assert "if (inSuono === chiave) { zittisci(); return; }" in src, \
            "il ▶ del quaderno deve fermare SUL POSTO (toggle, non solo play)"
        assert "lab-ritratto-quaderno" in src
        # fuori dal blocco {esito && ...}: il quaderno viene DOPO la
        # chiusura della griglia e prima della didascalia finale
        assert src.index("lab-ritratto-quaderno") > src.index("lab-ritratto-onesta"), \
            "il quaderno deve vivere fuori dal blocco dell'esito"

    def test_l_onesta_dell_originale_mancante(self):
        """Aperto dal quaderno, l'Originale non esiste: il bottone si
        spegne e il messaggio dice il perche'."""
        src = (LAB / "Ritratto.jsx").read_text()
        assert "disabled={!presaRef.current}" in src, \
            "senza presa l'Originale deve spegnersi, non mentire"
        assert "ricorda la tabella, non la voce" in src

    def test_l_onda_del_quaderno_porta_l_etichetta(self):
        """OndaViva accetta `nome`: la tela del quaderno dice CHI suona."""
        onda = (LAB / "OndaViva.jsx").read_text()
        assert "nome = null" in onda and "nome ||" in onda
        src = (LAB / "Ritratto.jsx").read_text()
        assert src.count("<OndaViva") == 2, \
            "due tele: una per la fonderia, una accanto al quaderno"


class TestFaroFondamenta:
    """FARO FA1-FA3 (30/8/2026) — gli attriti tolti dal mondo gratuito.

    FA1: nel Banco «interrompere lo sweep = tenere la nota» era la
    scelta vecchia gia' bocciata dal founder nelle Risonanze («quando
    stoppiamo il suono si DEVE fermare», 28/8) — sopravviveva in una
    stanza e lo sweep continuava a suonare dopo lo stop. FA2: la via
    del ritorno era una riga di testo invisibile su mobile.
    """

    def test_fa1_lo_sweep_si_ferma_e_cattura(self):
        src = (LAB / "Generatore.jsx").read_text()
        blocco = src[src.index("const alternaSweep"):]
        assert "lab.generatore.ferma()" in blocco[:1600], \
            "fermare lo sweep deve fare SILENZIO (decisione RZ)"
        assert "setFermatoA" in blocco[:1600], \
            "il fermo e' una misura: la frequenza si cattura"
        assert "interrompere = tenere la nota" not in src, \
            "la scelta vecchia e' tornata"
        assert "Fermato a" in src, "il numero catturato va mostrato"

    def test_fa2_il_ritorno_e_una_pill_sticky(self):
        css = (LAB / "lab.css").read_text()
        blocco = css[css.index(".fqz .lab-ritorno{"):]
        assert "position:sticky" in blocco[:200]
        assert "linear-gradient" in blocco[:900], \
            "cio' che galleggia sul contenuto e' OPACO (regola di casa)"
        tela = (LAB / "Stanza.jsx").read_text()
        assert 'data-testid="lab-ritorno-sala"' in tela
