"""Ciclo ONDA (21/8/2026) — il catalogo delle frequenze prende movimento.

Analisi: docs/FREQUENZE_CATALOGO_ANALISI_2026-08.md

ONDA 1 — le schede di Esplora percorrono il TRAGITTO che hanno scritto
nei dati. Prima il player ne leggeva solo `f0` e lo teneva fisso: la
scheda Delta dichiarava «da 4 a 2,5 Hz» e suonava 4 Hz per sempre.
`f1`, la curva e il respiro esistevano nel motore ma vivevano solo
dentro una sessione composta.

Misurato in browser dopo il fix (Delta, isocronico): 240 passi da 3,99
a 2,50 Hz in 179 s, respiro a 26 s esatti come envAt.
"""
import re
from pathlib import Path

FRONTEND_SRC = Path(__file__).resolve().parents[2] / "frontend" / "src"
FQ_DIR = FRONTEND_SRC / "features" / "frequenze"
SYNTH = FQ_DIR / "engine" / "synth.js"
MODEL = Path(__file__).resolve().parents[1] / "models" / "frequency_track.py"
PAGE = FQ_DIR / "FrequenzePage.js"
BIB = FQ_DIR / "content" / "biblioteca.js"


class TestLeSchedeSiMuovonoOnda1:

    def test_il_motore_riceve_il_tragitto_non_un_numero(self):
        """La scheda passa il suo cfg intero: se il player estraesse di
        nuovo solo f0, il movimento tornerebbe a esistere solo nei dati."""
        src = SYNTH.read_text()
        fn = src.split("export function startCardLive")[1].split("\nexport ")[0]
        assert "cfg.f1" in fn, "il motore non guarda il valore d'arrivo"
        assert "cfg.curve" in fn, "il motore ignora la curva della scheda"
        assert "freqAt(" in fn, \
            "il tragitto non usa la stessa matematica delle sessioni"

    def test_il_tono_puro_resta_fermo(self):
        """Un tono puro non ha battito: 174 Hz sono 174 Hz. Il tragitto
        vale solo per i metodi ritmici."""
        src = SYNTH.read_text()
        fn = src.split("export function startCardLive")[1].split("\nexport ")[0]
        riga = [l for l in fn.splitlines() if "sweepTo =" in l][0]
        assert "!== 'tone'" in riga, "anche i toni puri prenderebbero un tragitto"

    def test_il_respiro_e_lo_stesso_delle_sessioni(self):
        """Stessa ampiezza e stesso periodo di envAt, o la stessa
        frequenza respira in due modi diversi a seconda di dove la
        ascolti."""
        src = SYNTH.read_text()
        env = src.split("export function envAt")[1].split("\n}")[0]
        periodo = re.search(r"/ (\d+) \+", env).group(1)
        ampiezza = re.search(r"1 \+ ([\d.]+) \* Math\.sin", env).group(1)
        fn = src.split("export function startCardLive")[1].split("\nexport ")[0]
        assert f"1 / {periodo}" in fn, \
            f"la scheda non respira col periodo di envAt ({periodo} s)"
        assert f"ba.gain.value = {ampiezza}" in fn, \
            f"la scheda non respira con l'ampiezza di envAt ({ampiezza})"
        assert "cfg.breath !== false" in fn, \
            "breath:false non spegne piu' il respiro"

    def test_il_respiro_moltiplica_non_somma(self):
        """envAt lo definisce RELATIVO (±8%). Un LFO sommato a un gain
        di 0,25 darebbe ±32%: serve un nodo in serie."""
        src = SYNTH.read_text()
        fn = src.split("export function startCardLive")[1].split("\nexport ")[0]
        assert "ba.connect(out.gain)" in fn, \
            "il respiro e' agganciato al volume invece che a un nodo in serie"
        assert "out.gain.value = 1" in fn

    def test_l_utente_puo_riprendere_il_comando(self):
        """Chi tocca il battito comanda: il tragitto si ferma dov'e'
        arrivato (mai un salto) e la scheda smette di dire che si sta
        muovendo."""
        src = SYNTH.read_text()
        fn = src.split("export function startCardLive")[1].split("\nexport ")[0]
        setbeat = fn.split("setBeat(v)")[1].split("},")[0]
        assert "fermaIlTragitto()" in setbeat
        ferma = fn.split("const fermaIlTragitto")[1].split("};")[0]
        assert "cancelScheduledValues" in ferma and "setValueAtTime" in ferma, \
            "senza fissare il valore corrente il parametro salta"
        page = PAGE.read_text()
        # C4: setBeat ora converte i respiri/min, quindi l'ancora e'
        # la chiamata, non la firma esatta
        onchange = page.split("live.setBeat(")[1][:700]
        assert "setLiveKeys(Object.keys(liveCardsRef.current))" in onchange, \
            "la scheda continuerebbe a dire «in movimento» a comando preso"
        # `handles` e' una variabile locale di toggleCard: usarla qui
        # sarebbe un ReferenceError dentro l'onChange (successo davvero).
        # Si guarda il CODICE, non i commenti che lo spiegano.
        codice = "\n".join(l.split("//")[0] for l in onchange.splitlines())
        assert "Object.keys(handles)" not in codice, \
            "`handles` non e' in scope nella scheda: ReferenceError"

    def test_la_scheda_dichiara_il_movimento(self):
        page = PAGE.read_text()
        assert 'data-testid="fq-card-sweep"' in page
        blocco = page.split('data-testid="fq-card-sweep"')[0][-600:]
        assert "live.sweepTo != null" in blocco, \
            "l'indicazione comparirebbe anche sulle frequenze ferme"

    def test_le_quattro_schede_col_tragitto_esistono_ancora(self):
        """Se domani qualcuno «pulisce» i dati appiattendo f1 su f0, il
        catalogo torna immobile senza che nessuno se ne accorga."""
        src = BIB.read_text()
        coppie = re.findall(r"f0:([\d.]+),f1:([\d.]+)", src)
        mobili = [c for c in coppie if c[0] != c[1]]
        assert len(mobili) >= 4, \
            f"solo {len(mobili)} schede hanno un tragitto: erano 4"


class TestLaMareaOnda2:
    """ONDA 2 — la curva `wave`: il battito va da f0 a f1 e TORNA, per
    sempre. Le altre tre curve vanno da un valore all'altro una volta
    sola. Misurato: il render analitico segue la formula entro lo 0,3%
    su ogni finestra oltre l'attacco."""

    def test_la_forma_vive_in_un_posto_solo(self):
        """Render analitico e anteprima WebAudio leggono entrambi da
        freqAt: una seconda implementazione della marea suonerebbe
        diversa all'export — il bug che si sente solo dopo."""
        src = SYNTH.read_text()
        fn = src.split("export function freqAt")[1].split("\n}")[0]
        assert "l.curve === 'wave'" in fn, "la marea non e' nella matematica condivisa"
        assert "Math.cos" in fn, "la marea non e' derivabile: si sentirebbe uno scatto"
        # Nessun altro punto ricalcola la MAREA per conto suo. Si cerca
        # la sua firma — il coseno sul periodo — non un generico
        # `1 - Math.cos`: quello compare anche nella salita del respiro
        # (ONDA 6), che e' un'altra forma e ha diritto al suo coseno.
        fuori = src.replace(fn, "")
        assert "(TAU * u) / T" not in fuori, \
            "la formula della marea e' scritta due volte: divergeranno"

    def test_il_campionamento_segue_il_periodo(self):
        """Una marea di 40 s campionata ogni 10 s e' un'ALTRA onda.
        L'anteprima disegna la curva punto per punto: i punti devono
        bastare al periodo, non alla durata."""
        src = SYNTH.read_text()
        blocco = src.split("const passi =")[1].split(";")[0]
        assert "l.curve === 'wave'" in blocco and "l.period" in blocco, \
            "i passi non guardano il periodo della marea"
        assert "120" in blocco, "persa la densita' delle curve monotone"
        assert "Math.min(" in blocco, \
            "senza tetto una marea corta su due ore schedulerebbe decine di migliaia di eventi"
        assert "rampCurve(o.frequency, s0, span, (u) => Math.max(1, fFn(u) * m), passi" in src
        assert src.count("(u) => beat(u), passi, now)") == 3, \
            "un metodo ritmico campiona ancora a densita' fissa"

    def test_nelle_schede_la_marea_si_genera_non_si_disegna(self):
        """Un ascolto di scheda non finisce: disegnare la marea
        vorrebbe dire schedulare rampe all'infinito. Un oscillatore
        -cos sommato al valore centrale E' la stessa formula, con due
        nodi e per sempre."""
        src = SYNTH.read_text()
        fn = src.split("export function startCardLive")[1].split("\nexport ")[0]
        assert "createPeriodicWave" in fn, "la marea infinita non e' generata"
        assert "new Float32Array([0, -1])" in fn, \
            "forma d'onda sbagliata: serve -cos per partire da f0 (freqAt)"
        assert "(beat + sweepTo) / 2" in fn and "(sweepTo - beat) / 2" in fn, \
            "centro e ampiezza non corrispondono alla formula"

    def test_la_versione_sale_solo_dove_serve(self):
        """Stessa regola della voce: una ricetta salvata ieri deve
        restare byte per byte quella di ieri."""
        src = MODEL.read_text()
        assert "SCORE_VERSION_WAVE = 3" in src
        assert '"wave"' in src.split("CURVES =")[1].split(")")[0]
        blocco = src.split('"score_version":')[1].split(",\n")[0]
        assert "has_wave" in blocco, "la marea non alza la versione"
        assert "SCORE_VERSION_VOICE" in blocco and "else SCORE_VERSION" in blocco, \
            "persa la scala delle versioni precedenti"

    def test_il_periodo_esiste_solo_per_la_marea(self):
        """Sugli altri livelli sarebbe un campo muto: chi legge il
        documento non deve chiedersi cosa faccia."""
        src = MODEL.read_text()
        assert 'if layer["curve"] == "wave":' in src
        assert "PERIOD_MIN, PERIOD_MAX, PERIOD_DEFAULT" in src
        riga = [l for l in src.splitlines() if "PERIOD_MIN, PERIOD_MAX" in l and "=" in l][0]
        assert "2.0" in riga, "sotto i 2 s non e' un movimento ma un vibrato"

    def test_la_marea_e_raggiungibile_dal_compositore(self):
        page = PAGE.read_text()
        assert "WAVE_PERIOD_SEC" in page, "il periodo non ha un default nell'editor"
        assert 'data-testid="fq-layer-period"' in page
        blocco = page.split('data-testid="fq-layer-period"')[0][-500:]
        assert "l.curve === 'wave'" in blocco, \
            "il campo periodo comparirebbe anche sulle curve monotone"


class TestRitmiDelCorpoOnda3:
    """ONDA 3 — la categoria dove l'evidenza e' dalla nostra parte,
    ma riguarda la PRATICA (respirare lentamente, muoversi a tempo) e
    non il suono. Misurato sul render: 6,0 · 4,1 · 60,0 · 120,0 cicli
    al minuto, scarto max 1,4%."""

    def test_il_pavimento_del_battito_lascia_entrare_il_respiro(self):
        """Un respiro lento e' 0,1 Hz: meta' del vecchio minimo (0,2).
        Il motore reggeva gia' 0,05 — era il modello a chiudere."""
        src = MODEL.read_text()
        riga = [l for l in src.splitlines()
                if l.startswith("BEAT_MIN, BEAT_MAX")][0]
        minimo = float(riga.split("=")[1].split(",")[0])
        assert minimo <= 0.05, \
            f"il battito minimo e' {minimo} Hz: i ritmi del respiro non entrano"
        page = PAGE.read_text()
        assert 'min="0.2"' not in page, \
            "l'editor blocca ancora i ritmi lenti che il modello accetta"

    def test_la_categoria_esiste_e_ha_il_suo_indirizzo(self):
        """LN — ogni vista ha il suo URL. Una categoria senza slug non
        si apre: il clic scrive `?categoria=` vuoto e la tab torna alla
        prima. Successo davvero il 21/8, le due mappe vanno gemelle."""
        bib = BIB.read_text()
        assert "'Ritmi del corpo':[" in bib
        page = PAGE.read_text()
        slug = page.split("const CAT_SLUG =")[1].split("};")[0]
        inverso = page.split("const SLUG_CAT =")[1].split("};")[0]
        assert "'ritmi-del-corpo'" in slug and "'ritmi-del-corpo'" in inverso, \
            "la categoria non ha uno slug: la tab non si aprirebbe"
        nomi_slug = re.findall(r"'([^']+)': '([a-z-]+)'", slug)
        nomi_inv = re.findall(r"'([a-z-]+)': '([^']+)'", inverso)
        assert {v: k for k, v in nomi_slug} == dict(nomi_inv), \
            "CAT_SLUG e SLUG_CAT non sono piu' gemelle"

    def test_ogni_ritmo_e_quello_che_dichiara(self):
        """Il titolo dice «sei respiri al minuto»: il cfg deve produrli
        davvero. 0,1 Hz = 6/min, 1 Hz = 60/min, 2 Hz = 120/min."""
        bib = BIB.read_text()
        blocco = bib.split("'Ritmi del corpo':[")[1].split("'Metodi':[")[0]
        attesi = {"Respiro lento": 0.1, "Respiro pi": 0.07,
                  "Passo del cuore": 1, "Cadenza del cammino": 2}
        for titolo, hz in attesi.items():
            scheda = [b for b in blocco.split("{t:'") if b.startswith(titolo)]
            assert scheda, f"manca la scheda {titolo}"
            f0 = float(re.search(r"f0:([\d.]+)", scheda[0]).group(1))
            assert abs(f0 - hz) < 1e-9, \
                f"{titolo}: dichiara {hz} Hz ma il cfg suona {f0} Hz"

    def test_l_onesta_della_categoria_e_scritta(self):
        """Il patto della biblioteca: qui l'effetto documentato e'
        della pratica, non del suono. Se questa distinzione sparisce,
        la categoria diventa la promessa che non vogliamo fare."""
        bib = BIB.read_text()
        blocco = bib.split("'Ritmi del corpo':[")[1].split("'Metodi':[")[0]
        assert "non del suono" in blocco, \
            "sparita la distinzione tra effetto della pratica ed effetto del suono"
        assert "class=\"warn\"" in blocco, "nessun avvertimento nelle schede"
        # e il cuore non si fa inseguire da un altoparlante
        cuore = blocco.split("Passo del cuore")[1][:2500]
        assert "Il cuore non insegue" in cuore, \
            "manca la smentita esplicita dell'entrainment cardiaco"
        page = PAGE.read_text()
        intro = page.split("'Ritmi del corpo': {")[1][:600]
        assert "riguarda la pratica" in intro


class TestTimbroOnda4:
    """ONDA 4 — il bordone armonico e il colore del soffio. Misurato:
    il bordone suona 110 · 165 · 137,5 Hz (fondamentale, quinta 3/2,
    terza 5/4); i tre colori hanno livelli pari (0,42-0,49 RMS) e
    contenuto di acuti crescente 0,196 · 0,594 · 1,416."""

    def test_il_bordone_e_un_accordo_non_una_nota(self):
        """Il tono puro da' la fondamentale con due armoniche: una nota.
        Il bordone da' quinta e terza NATURALI: rapporti 3/2 e 5/4, i
        soli che non battono tra loro."""
        src = SYNTH.read_text()
        parti = src.split("const DRONE_PARTS =")[1].split(";")[0]
        assert "1.5" in parti and "1.25" in parti, \
            "il bordone non usa quinta e terza naturali"
        assert "drone: 'bordone armonico'" in src, "il metodo non ha etichetta"
        # e vive in ENTRAMBE le sintesi, o l'export suona diverso
        assert "l.method === 'drone'" in src, "manca nel render analitico"
        assert src.count("DRONE_PARTS.forEach") >= 2, \
            "il bordone non e' in tutte e due le anteprime (scheda e sessione)"

    def test_il_bordone_non_ha_battito_nell_editor(self):
        page = PAGE.read_text()
        assert "(l.method === 'tone' || l.method === 'drone')" in page, \
            "l'editor chiede un battito a un bordone, che non ne ha"

    def test_i_colori_del_soffio_sono_pareggiati(self):
        """Cambiare colore deve cambiare la GRANA, non il volume: senza
        pareggio si sentirebbe la differenza sbagliata. Il rosa resta
        1 — e' il riferimento storico e le ricette salvate devono
        suonare identiche."""
        src = SYNTH.read_text()
        assert "NOISE_GAIN" in src
        gain = src.split("export const NOISE_GAIN =")[1].split(";")[0]
        assert "pink: 1" in gain, \
            "toccato il livello del rosa: le ricette gia' salvate cambierebbero suono"
        assert "brown:" in gain and "white:" in gain
        # la stessa matematica nei due gemelli
        assert "NOISE_GAIN.brown" in src and "NOISE_GAIN.white" in src
        assert src.count("br = (br + 0.02 * w) / 1.02") + \
               src.count("l._br = (l._br + 0.02 * w) / 1.02") == 2, \
            "il marrone e' calcolato in un modo solo: anteprima ed export divergono"

    def test_il_colore_vale_solo_per_il_soffio_e_il_rosa_e_il_default(self):
        src = MODEL.read_text()
        assert 'if layer["method"] == "noise":' in src
        blocco = src.split('if layer["method"] == "noise":')[1][:300]
        assert '"pink"' in blocco, \
            "senza default rosa le ricette vecchie cambierebbero colore"
        assert '"drone"' in src.split("METHODS =")[1].split(")")[0]

    def test_i_suoni_naturali_veri_non_si_imitano(self):
        """Decisione founder (21/8): per mare, pioggia e vento ci sono
        le registrazioni VERE in libreria (61 basi, 12 di natura). Il
        rumore sintetico porta un ritmo, non racconta un paesaggio — e
        la scheda deve dirlo, o l'utente confonde le due cose."""
        bib = BIB.read_text()
        scheda = bib.split("{t:'Il colore del soffio'")[1].split("cfg:")[0]
        assert "non sono suoni della natura" in scheda
        assert "libreria" in scheda, \
            "la scheda non manda alle registrazioni vere"
        # e da nessuna parte esiste un metodo che finge di essere il mare
        src = SYNTH.read_text()
        assert "surf" not in src, \
            "e' rientrato un metodo che imita la natura invece di usarla"


class TestDiscesaInfinitaOnda5:
    """ONDA 5 — la scala di Shepard-Risset: sette voci a un'ottava di
    distanza che scendono insieme. Misurato in browser: 37,2 · 74,5 ·
    148,9 · 297,9 · 595,8 · 1191,5 · 2383,1 Hz (ottave esatte), tutte
    in discesa dello stesso fattore. E sui numeri: ogni voce scende
    (156 → 78 → 39 Hz) ma l'insieme dopo un giro e' identico."""

    def test_le_voci_sono_ottave_e_la_campana_le_nasconde(self):
        src = SYNTH.read_text()
        assert "const SHEPARD_N" in src and "SHEPARD_BELL" in src
        bell = src.split("const SHEPARD_BELL =")[1].split(";")[0]
        assert "Math.sin(Math.PI * x)" in bell, \
            "senza una campana che va a ZERO agli estremi si sente il rientro"
        # la posizione e' modulare: e' il wrap a rendere la discesa infinita
        analitico = src.split("if (l.method === 'shepard')")[1].split("\n  }")[0]
        assert "% SHEPARD_N" in analitico, "senza il giro la discesa finisce"
        assert "Math.pow(2, pos)" in analitico, "le voci non distano un'ottava"

    def test_vive_in_tutte_e_tre_le_strade(self):
        """Render analitico, anteprima della sessione, scheda live: se
        ne manca una, quel percorso suona un'altra cosa."""
        src = SYNTH.read_text()
        assert src.count("SHEPARD_BELL(") >= 3, \
            "la discesa non e' in tutte e tre le sintesi"
        assert "method === 'shepard'" in src and "l.method === 'shepard'" in src

    def test_l_orizzonte_della_scheda_e_dichiarato(self):
        """In una scheda la discesa e' programmata, non generata: dopo
        l'orizzonte le voci restano ferme. E' una scelta, e va scritta
        dove qualcuno la leggera' — non scoperta a caso tra un anno."""
        src = SYNTH.read_text()
        assert "CARD_SHEPARD_SEC" in src
        commento = src.split("else if (method === 'shepard')")[1][:900]
        assert "restano ferme" in commento or "immobile" in commento, \
            "l'orizzonte non e' spiegato: sembrera' un bug"
        assert "SESSIONI" in commento, \
            "non e' detto che nelle sessioni composte la discesa e' esatta"

    def test_la_discesa_non_ha_battito_ne_curva(self):
        """f0 qui e' «ottave al minuto», non un battito: chiedere un
        valore d'arrivo e una curva sarebbe chiedere il nulla."""
        page = PAGE.read_text()
        assert "'ottave/min'" in page, "l'etichetta mente sul significato di f0"
        assert "l.method !== 'shepard' && (" in page \
            or "&& l.method !== 'shepard'" in page, \
            "l'editor offre valore d'arrivo e curva a una discesa infinita"

    def test_la_scheda_dice_cosa_e_documentato_e_cosa_no(self):
        bib = BIB.read_text()
        scheda = bib.split("{t:'Discesa infinita'")[1].split("cfg:")[0]
        assert "psicoacustica" in scheda
        assert "Non esistono evidenze" in scheda, \
            "manca il limite: l'illusione e' documentata, gli effetti no"
        # e la scheda di mestiere sulla portante
        portante = bib.split("{t:'Scegliere la portante'")[1].split("cfg:")[0]
        assert "400" in portante and "180" in portante, \
            "la scheda non spiega i due valori predefiniti veri"


class TestRespiroVeroOnda6:
    """ONDA 6 (founder: «non sembrano respiri veri, sembra il mare») —
    ed era esatto: il soffio modulato e' una sinusoide, sale e scende
    uguale, senza pause, e comincia a meta' corsa. Il respiro guidato
    e' un'altra forma: asimmetrica, con la pausa, e con le due fasi
    distinguibili al timbro.

    Misurato: render 3,3 in / 4,5 out / 2,8 pausa, timbro 1,42x;
    anteprima (reso offline) 3,5 / 4,3 / 2,8, timbro 1,96x."""

    def test_l_espirazione_e_piu_lunga_dell_inspirazione(self):
        src = SYNTH.read_text()
        inn = float(src.split("export const BREATH_IN =")[1].split(";")[0])
        out = float(src.split("export const BREATH_OUT =")[1].split(";")[0])
        assert out > inn, \
            "si espira per meno di quanto si inspira: non e' un respiro"
        assert inn + out < 1, "senza pausa non si sa dove ricomincia il ciclo"

    def test_il_ciclo_parte_dal_silenzio_e_finisce_in_pausa(self):
        """Una sinusoide comincia a meta': non dice mai «adesso». La
        forma del respiro parte da zero e torna a zero."""
        src = SYNTH.read_text()
        fn = src.split("export function breathEnv")[1].split("\n}")[0]
        assert "1 - Math.cos" in fn, "l'inspirazione non parte dal silenzio"
        assert "return 0;" in fn, "manca la pausa"

    def test_la_coda_dell_espirazione_resta_udibile(self):
        """Con un coseno puro l'ultimo secondo e' gia' muto e si
        confonde con la pausa: non si sa piu' quando smettere."""
        src = SYNTH.read_text()
        fn = src.split("export function breathEnv")[1].split("\n}")[0]
        assert "Math.pow(" in fn, \
            "la coda dell'espirazione sprofonda nel silenzio troppo presto"

    def test_le_due_fasi_si_distinguono_al_timbro(self):
        """A occhi chiusi la forma da sola non basta: serve un segno
        che dica in che meta' del respiro sei. AUDIT §5: il segno sono
        le ARMONICHE della stessa nota (2ª e 3ª) che si aprono
        inspirando — non piu' un filtro su un rumore che fingeva di
        essere aria (misurato 1,26x di apertura, forma 3,5/4,8/1,8)."""
        src = SYNTH.read_text()
        assert "export function breathBright" in src
        analitico = src.split("if (l.method === 'breath')")[1].split("\n  }")[0]
        assert "breathBright(ph" in analitico
        assert "Math.sin(th * 2)" in analitico and "Math.sin(th * 3)" in analitico, \
            "le armoniche che aprono la voce sono sparite"
        # e niente rumore: la guida e' dichiaratamente un tono
        assert "Math.random" not in analitico, \
            "il respiro e' tornato a fingere di essere aria"
        # nell'anteprima: stesse forme in loop
        assert src.count("breathBright(u") >= 2, \
            "l'anteprima non cambia timbro: le due fasi diventano uguali"

    def test_il_passo_del_respiro_segue_il_battito_ovunque(self):
        """La «marea del respiro» rallenta: se rallentasse solo nel
        render, anteprima ed export sarebbero due pratiche diverse."""
        src = SYNTH.read_text()
        assert "ritmoRespiro" in src, "la scheda non fa seguire il passo"
        assert "rateDaHz" in src
        sessione = src.split("if (l.method === 'breath')")[2] if src.count("if (l.method === 'breath')") > 1 else ""
        assert "playbackRate" in sessione and "freqAt(l, u, span)" in sessione, \
            "nella sessione il passo del respiro non segue la curva"

    def test_il_soffio_modulato_resta_quello_di_prima(self):
        """`noise` non si tocca: e' un'onda e va bene che lo sia. Le
        ricette gia' salvate devono suonare identiche."""
        src = SYNTH.read_text()
        assert "const gate = (1 + Math.sin(pb)) / 2;" in src, \
            "cambiata la porta del soffio: le ricette salvate cambiano suono"
        model = MODEL.read_text()
        assert '"breath"' in model.split("METHODS =")[1].split(")")[0]
        assert '"noise"' in model.split("METHODS =")[1].split(")")[0]

    def test_la_pausa_non_si_puo_azzerare(self):
        src = MODEL.read_text()
        blocco = src.split('if layer["method"] == "breath":')[1][:600]
        assert "0.95" in blocco, \
            "inspirazione + espirazione possono mangiarsi tutta la pausa"

    def test_le_schede_del_respiro_usano_il_respiro(self):
        bib = BIB.read_text()
        blocco = bib.split("'Ritmi del corpo':[")[1].split("'Metodi':[")[0]
        respiri = [b for b in blocco.split("{t:'") if b.startswith("Respiro") or b.startswith("Marea")]
        assert len(respiri) == 3
        for r in respiri:
            assert "method:'breath'" in r, \
                "una scheda del respiro suona ancora come un'onda del mare"
        # e il testo non promette piu' un'onda
        assert "non di un’onda" in blocco or "non di un'onda" in blocco


class TestAuditPreGoLive:
    """Audit di consistenza (21/8, docs/SOUND_CONSISTENZA_AUDIT_2026-08.md):
    niente comandi finti, niente promesse plurali con audio singolare,
    e un respiro che non finge."""

    def test_c4_nessun_campo_morto_sulle_schede_live(self):
        """Bordone, discesa e respiro mostravano un «battito» collegato
        a niente: un comando finto fa sembrare finto tutto il resto."""
        page = PAGE.read_text()
        assert "live.method !== 'shepard' && (" in page, \
            "la discesa mostra un campo che non comanda nulla"
        assert "'respiri/min'" in page and "v / 60" in page, \
            "il respiro non ha il suo comando (o non converte da respiri/min)"
        src = SYNTH.read_text()
        assert "droneVoices" in src, \
            "setCarrier sul bordone muoverebbe solo la fondamentale"
        setbeat = src.split("setBeat(v)")[1].split("},")[0]
        assert "ritmoRespiro" in setbeat, \
            "il campo del respiro sulla scheda e' di nuovo un comando finto"

    def test_c5_il_muto_agisce_al_vivo_e_il_resto_e_dichiarato(self):
        page = PAGE.read_text()
        patch = page.split("const patchLayer")[1].split("};")[0]
        assert "patch.mute !== undefined" in patch, \
            "il muto cambia lo stato ma il livello continua a suonare"
        assert 'data-testid="fq-live-hint"' in page, \
            "nessuno dice quali modifiche agiscono subito e quali no"

    def test_c6_ogni_metodo_dice_se_serve_la_cuffia(self):
        page = PAGE.read_text()
        listen = page.split("const LISTEN = {")[1].split("};")[0]
        for m in ("bin", "iso", "mono", "bil", "noise", "tone",
                  "drone", "shepard", "breath"):
            assert f"{m}:" in listen, f"il metodo {m} non dice cuffie/altoparlante"

    def test_c1_le_armoniche_di_schumann_suonano_la_serie(self):
        """La riga prometteva quattro modi e l'audio ne suonava uno:
        ora attraversa la serie a gradini (14,3 → 33) e il testo dice
        cosa si ascolta."""
        bib = BIB.read_text()
        scheda = bib.split("{t:'Armoniche di Schumann'")[1].split("},")[0]
        assert "curve:'steps'" in scheda and "f1:33" in scheda, \
            "la scheda promette i modi al plurale e ne suona uno"
        assert "Cosa ascolti qui" in scheda

    def test_c2_gamma_e_40hz_dichiarano_lo_stesso_stimolo(self):
        bib = BIB.read_text()
        assert bib.count("Nota di trasparenza") >= 2, \
            "due schede suonano identiche senza dirlo"

    def test_s4_i_metodi_dicono_cosa_si_ascolta(self):
        """Un metodo non E' una frequenza, ma la scheda SUONA un esempio
        preciso: i suoi numeri vanno detti, come ovunque nel catalogo."""
        bib = BIB.read_text()
        metodi = bib.split("'Metodi':[")[1]
        righe = re.findall(r"hz:'((?:[^'\\]|\\.)*)'", metodi)
        senza = [r for r in righe if "in ascolto" not in r]
        assert not senza, f"schede Metodi senza i numeri in ascolto: {senza}"

    def test_s5_la_guida_del_respiro_non_finge(self):
        bib = BIB.read_text()
        scheda = bib.split("{t:'Respiro lento'")[1].split("},")[0]
        assert "Non imita un respiro" in scheda
        assert "astratto" in scheda, \
            "il testo non dichiara la natura del suono"
        # tutte e tre le guide hanno la loro nota
        blocco = bib.split("'Ritmi del corpo':[")[1].split("'Metodi':[")[0]
        for r in [b for b in blocco.split("{t:'")
                  if b.startswith(("Respiro", "Marea"))]:
            assert "carrier:110" in r, "una guida e' rimasta senza la sua nota"
