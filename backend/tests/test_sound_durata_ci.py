"""CI-F4 (22/9/2026, founder) — la sessione puo' durare fino a 90 minuti.

Il vincolo dei 30 nasceva dall'ascolto a schermo bloccato PRIMA della
pubblicazione (un WAV in memoria sul telefono) e dal render «in un
colpo» (PCM intero: 90 minuti = ~950 MB). Qui si tiene fermo il modo in
cui il tetto e' salito senza rompere niente:
  - modello e compilatore (JS/py) a 5400, in parita';
  - Crea: preset fino a 90', campo max 90, messaggi parlanti;
  - l'ascolto continuo (CI-F4b, 22/9 sera): WAV in memoria fino a 30
    (CONTINUO_WAV_MAX_SEC), MP3 a blocchi oltre, fino a 90
    (CONTINUO_MAX_SEC = DURATION_MAX) — «creo una melodia di 50 minuti,
    non posso ascoltarla intera? questo non va bene» (founder);
  - export e master oltre i 30 passano da renderMp3Streaming (render e
    codifica a blocchi), sotto i 30 il percorso di ieri e' intatto.
"""
import re
from pathlib import Path

from models.frequency_track import DURATION_MAX, clean_score

BACKEND = Path(__file__).resolve().parents[1]
FQ = BACKEND.parent / "frontend" / "src" / "features" / "frequenze"
PAGE = (FQ / "FrequenzePage.js").read_text(encoding="utf-8")
RENDER = (FQ / "engine" / "render.js").read_text(encoding="utf-8")
CONTINUO = (FQ / "engine" / "continuo.js").read_text(encoding="utf-8")
COMPILATORE = (FQ / "pro" / "compilatore.js").read_text(encoding="utf-8")


class TestTetto:
    def test_modello_e_compilatore_in_parita(self):
        assert DURATION_MAX == 5400
        assert "export const DURATA_MAX = 5400;" in COMPILATORE
        assert "novanta minuti" in COMPILATORE and "trenta minuti" not in COMPILATORE

    def test_una_sessione_da_un_ora_passa_e_novantuno_minuti_si_riportano(self):
        s = clean_score({"score_version": 1, "duration_sec": 3600,
                         "layers": [{"method": "iso", "carrier": 200, "f0": 10, "start": 0, "end": 3600, "gain": 0.5}]})
        assert s["duration_sec"] == 3600
        s2 = clean_score({"score_version": 1, "duration_sec": 5460,
                          "layers": [{"method": "iso", "carrier": 200, "f0": 10, "start": 0, "end": 5460, "gain": 0.5}]})
        assert s2["duration_sec"] == 5400

    def test_crea_offre_i_preset_lunghi(self):
        assert "[5, 10, 15, 20, 30, 45, 60, 90]" in PAGE
        assert "const CONTINUO_MIN = 30;" in PAGE
        # nessuna frase dice piu' che oltre i 30 non si ascolta
        assert "non è disponibile" not in PAGE.split("const fissaDurata")[1][:900]
        assert "nessun limite" in PAGE


class TestAscoltoContinuoFinoA90:
    def test_il_wav_in_memoria_ha_ancora_il_suo_tetto_e_oltre_si_comprime(self):
        assert "CONTINUO_WAV_MAX_SEC = 1800" in CONTINUO
        assert "CONTINUO_MAX_SEC = 5400" in CONTINUO
        assert "continuoDisponibile" in CONTINUO
        assert "if (d > CONTINUO_WAV_MAX_SEC) {" in CONTINUO
        assert "renderMp3Streaming(score, {" in CONTINUO
        assert "sampleRate: CONTINUO_SR" in CONTINUO.split("if (d > CONTINUO_WAV_MAX_SEC)")[1][:200]

    def test_il_tetto_del_continuo_e_quello_del_modello(self):
        assert DURATION_MAX == 5400
        assert "CONTINUO_MAX_SEC = 5400" in CONTINUO


class TestRenderABlocchi:
    def test_oltre_i_trenta_si_codifica_a_blocchi(self):
        assert "export async function renderMp3Streaming(" in RENDER
        assert "sink = null" in RENDER and "if (sink) sink(dest);" in RENDER
        assert "const pcm = sink ? null : new Int16Array(total * 2);" in RENDER
        # export e master scelgono la strada in base alla durata
        assert PAGE.count("> CONTINUO_MIN * 60") == 2
        assert PAGE.count("renderMp3Streaming(") == 2
        assert "import { renderPcm, mp3Blob, renderMp3Streaming } from './engine/render';" in PAGE

    def test_sotto_i_trenta_il_percorso_di_ieri_e_intatto(self):
        # renderPcm senza sink restituisce ancora il PCM intero, e mp3Blob esiste
        assert "return sink ? null : pcm;" in RENDER
        assert "export async function mp3Blob(" in RENDER
        assert re.search(r"const pcm = await renderPcm\(score, \{", PAGE)
