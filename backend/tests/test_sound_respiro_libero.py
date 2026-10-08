"""25/9/2026 (founder) — Crea piu' libero e omogeneo:
  DL  durata libera: pavimento 3 secondi (non un minuto), campo che
      capisce «20», «0:20», «1.30», «20s»; chip 10″ 20″ 30″;
  RS  il respiro registrato ha effetto e spazio come la voce (opt-in:
      senza scelta il grafo e la ricetta sono quelli di ieri);
  TF  su telefono il bottone «Impostazioni» riassume cosa c'e' dentro.
"""
import re
from pathlib import Path

RADICE = Path(__file__).resolve().parents[2]
FQ_DIR = RADICE / "frontend" / "src" / "features" / "frequenze"
PAGE = ((FQ_DIR / "FrequenzePage.js").read_text(encoding="utf-8") + (FQ_DIR / "crea" / "CreaVista.jsx").read_text(encoding="utf-8") + (FQ_DIR / "crea" / "TracceVista.jsx").read_text(encoding="utf-8"))
SPAZIO = (FQ_DIR / "engine" / "spazio.js").read_text(encoding="utf-8")
SYNTH = (FQ_DIR / "engine" / "synth.js").read_text(encoding="utf-8")
RENDER = (FQ_DIR / "engine" / "render.js").read_text(encoding="utf-8")
ASSETS = (FQ_DIR / "engine" / "assets.js").read_text(encoding="utf-8")


class TestDurataLibera:
    def test_pavimento_e_campo(self):
        from models.frequency_track import DURATION_MIN, DURATION_MAX
        assert DURATION_MIN == 3 and DURATION_MAX == 5400
        assert "const DURATA_MIN_SEC = 3;" in PAGE
        assert "Math.min(DURATA_MAX_SEC, Math.max(DURATA_MIN_SEC," in PAGE
        assert "const [durataFissaSec, setDurataFissaSec] = useState(null);" in PAGE
        assert "setDurataFissaMin(" not in PAGE and "durataFissaMin ===" not in PAGE   # niente residui in minuti
        assert 'data-testid={`fq-durata-sec-${s}`}' in PAGE and "[10, 20, 30].map" in PAGE
        assert "fissaDurata(k.parseDurata(e.currentTarget.value))" in PAGE   # CR1: nel foglio della durata
        assert "mins > DURATA_MAX_MIN" in PAGE             # il tetto resta

    def test_parse_durata_come_lo_scrive_una_persona(self):
        """La stessa regola del JS, rifatta qui: numero = minuti, m:ss o
        m.ss = tempo, «20s» = secondi."""
        js = PAGE.split("const parseDurata = (raw) => {")[1].split("};")[0]
        assert "return (+m) * 60 + (+ss)" in js and "parseFloat(s) * 60" in js
        def parse(raw):
            s = str(raw).strip().lower().replace(",", ".")
            if re.fullmatch(r"\d+[:.]\d{1,2}", s):
                m, ss = re.split(r"[:.]", s); return int(m) * 60 + int(ss)
            if re.fullmatch(r"\d+(\.\d+)?\s*(s|sec|\"|″)", s):
                return float(re.match(r"\d+(\.\d+)?", s).group(0))
            if re.fullmatch(r"\d+(\.\d+)?\s*(m|min|′)?", s):
                return float(re.match(r"\d+(\.\d+)?", s).group(0)) * 60
            return None
        assert parse("20") == 1200 and parse("0:20") == 20 and parse("1.30") == 90
        assert parse("20s") == 20 and parse("7s") == 7 and parse("abc") is None

    def test_il_modello_accetta_sette_secondi(self):
        from models.frequency_track import clean_score
        s = clean_score({"duration_sec": 7, "layers": [{"kind": "neuro", "method": "tone", "name": "t", "carrier": 200,
                                                        "start": 0, "end": 7, "gain": 0.5}]})
        assert s["duration_sec"] == 7


class TestRespiroConEffettoESpazio:
    def test_parita_preset_guida(self):
        from models.frequency_track import SPACE_PRESETS, clean_space
        assert SPACE_PRESETS["guida"] == SPACE_PRESETS["voice"]
        js = SPAZIO.split("export const SPACE_PRESETS")[1].split("});")[0]
        con_guida = tuple(m.group(1) for m in re.finditer(r"^\s*(\w+): \{ label: '[^']*', kinds: \[([^\]]*)\]", js, re.M)
                          if "'guida'" in m.group(2))
        assert con_guida == SPACE_PRESETS["guida"]
        assert clean_space("guida", {"preset": "vicina"}) == {"preset": "vicina"}
        assert clean_space("guida", {"preset": "orbita"}) is None

    def test_la_ricetta_porta_fx_e_space_solo_se_scelti(self):
        from models.frequency_track import clean_score
        base = {"kind": "guida", "asset_id": "a1", "start": 0, "end": 60, "gain": 0.9, "respiri": 10}
        s = clean_score({"duration_sec": 60, "layers": [base]})
        l = s["layers"][0]
        assert "fx" not in l and "space" not in l                      # ieri = oggi
        s2 = clean_score({"duration_sec": 60, "layers": [{**base, "fx": "temple", "fx_amount": 0.4,
                                                          "space": {"preset": "respira"}}]})
        l2 = s2["layers"][0]
        assert l2["fx"] == "temple" and l2["fx_amount"] == 0.4 and l2["space"] == {"preset": "respira"}
        s3 = clean_score({"duration_sec": 60, "layers": [{**base, "fx": "giostra", "space": {"preset": "avvolge"}}]})
        assert "fx" not in s3["layers"][0] and "space" not in s3["layers"][0]

    def test_motore_vivo_master_e_risoluzione(self):
        ramo = SYNTH.split("guidaLayers.filter(")[1].split("(score.layers || [])")[0]
        assert "if (g.fx) {" in ramo and "spazializza(g, 'guida', uscitaG, uG, s0, span)" in ramo
        assert "montaGuida(ctx, gg, g, { da: uA, a: span, quando: (u) => at(s0 + u) })" in ramo
        blocco = RENDER.split("guide.forEach((g) => {")[1].split("});", 1)[0]
        assert "spaceValido('guida', g.space?.preset)" in blocco and "buildVoiceChain(off, g.fx" in blocco
        assert "uA: Math.max(0, cs - g.start)" in blocco
        ris = ASSETS.split("export async function resolveGuidaLayers")[1].split("export async function")[0]
        assert "fx: l.fx || null, fx_amount: l.fx_amount ?? 0.6, space: l.space," in ris

    def test_anche_il_clip_registrato_ha_l_effetto(self):
        from models.frequency_track import clean_score
        base = {"kind": "audio", "asset_id": "b1", "start": 0, "end": 30, "gain": 0.7}
        s = clean_score({"duration_sec": 30, "layers": [base]})
        assert "fx" not in s["layers"][0]                                   # ieri = oggi
        s2 = clean_score({"duration_sec": 30, "layers": [{**base, "fx": "temple", "fx_amount": 0.3}]})
        assert s2["layers"][0]["fx"] == "temple" and s2["layers"][0]["fx_amount"] == 0.3
        # motore vivo e master: catena solo se scelta, poi lo spazio come prima
        assert "spazializza(l, 'audio', uscitaA, uG, s0, span)" in SYNTH and SYNTH.count("spazializza(l, 'audio'") == 1
        blocco = RENDER.split("      audio.forEach((l) => {")[1].split("      });")[0]
        assert "buildVoiceChain(off, l.fx" in blocco and "uscitaA.connect(sp.input)" in blocco and "uscitaA.connect(off.destination)" in blocco
        ris = ASSETS.split("export async function resolveAudioLayers")[1].split("export async function")[0]
        assert "fx: l.fx || null, fx_amount: l.fx_amount ?? 0.6," in ris
        # nella riga, solo per i clip registrati (respiro, voce): le basi musicali no
        assert "['respiro', 'voce'].includes(soundsById[l.asset_id]?.category)" in PAGE
        assert 'data-testid={`fq-audio-fx-${l.id}`}' in PAGE

    def test_la_riga_ha_effetto_e_spazio(self):
        riga = PAGE.split("data-testid={`fq-guida-${l.id}`}")[1].split("l.kind === 'audio' ? (")[0]
        assert 'data-testid={`fq-guida-fx-${l.id}`}' in riga and '<option value="nessuno">Nessuno</option>' in riga
        assert "presetPerTipo('guida')" in riga and 'data-testid={`fq-space-${l.id}`}' in riga


class TestTelefono:
    def test_il_bottone_impostazioni_riassume(self):
        assert 'data-testid="fq-setup-riassunto"' in PAGE
        # CR1: il riassunto e' una const (`riassunto`) stampata nella riga sotto la barra
        blocco = PAGE.split("const riassunto = ")[1][:300]
        assert "STANZE[k.stanza]" in blocco and "fadeIn" in blocco and "fadeOut" in blocco
