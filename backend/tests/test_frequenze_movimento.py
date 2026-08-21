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
