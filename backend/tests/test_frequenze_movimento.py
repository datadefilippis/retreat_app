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
        onchange = page.split("live.setBeat(v)")[1][:600]
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
        # nessun altro punto ricalcola la forma per conto suo
        fuori = src.replace(fn, "")
        assert "1 - Math.cos" not in fuori, \
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
