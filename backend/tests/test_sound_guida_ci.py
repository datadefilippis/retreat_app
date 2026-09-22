"""CI-F1 (22/9/2026) — LA GUIDA DEL RESPIRO: i clip registrati dal founder
(libreria, categoria `respiro`, campi `guida`/`ciclo_sec`) montati su una
partitura a round dallo strato `kind:'guida'` (score v5).

Tenuto fermo qui:
  1. i clip: vocabolario `guida` in parita' fra modello e engine/guida.js,
     `ciclo_sec` solo nei limiti, proiezione pubblica con i due campi;
  2. lo strato: v5 solo se c'e', numeri riportati nei limiti (gli stessi
     del motore), le parole di svolta solo per id noti; una ricetta
     senza guida resta identica a ieri;
  3. il motore: una partitura sola (partituraGuida) per vivo, master e
     continuo; il master la piazza a blocchi con l'offset; gli strati
     risolti arrivano dalla libreria (resolveGuidaLayers) in Crea, nel
     player pubblico e nell'ascolto continuo;
  4. Crea: «+ guida» sui cicli, le parole non si aggiungono come basi,
     la riga della guida ricalcola la fine.
"""
import json
import re
from pathlib import Path

from models.audio_asset import GUIDA_TIPI, clean_guida, clean_ciclo_sec
from models.frequency_track import (
    SCORE_VERSION_GUIDA, SCORE_VERSION_SPACE, GUIDA_RESPIRI_MAX, GUIDA_ROUND_MAX,
    GUIDA_VUOTO_MAX, GUIDA_PIENO_MAX, GUIDA_RECUPERO_MAX, clean_score)

BACKEND = Path(__file__).resolve().parents[1]
FQ = BACKEND.parent / "frontend" / "src" / "features" / "frequenze"
GUIDA = (FQ / "engine" / "guida.js").read_text(encoding="utf-8")
ASSETS = (FQ / "engine" / "assets.js").read_text(encoding="utf-8")
SYNTH = (FQ / "engine" / "synth.js").read_text(encoding="utf-8")
RENDER = (FQ / "engine" / "render.js").read_text(encoding="utf-8")
CONTINUO = (FQ / "engine" / "continuo.js").read_text(encoding="utf-8")
PAGE = (FQ / "FrequenzePage.js").read_text(encoding="utf-8")
PUBLIC = (FQ / "PublicFrequencyPage.js").read_text(encoding="utf-8")
ROUTER = (BACKEND / "routers" / "frequencies.py").read_text(encoding="utf-8")


def _score(layers, **extra):
    return {"score_version": 1, "duration_sec": 600, "layers": layers, **extra}


AUDIO = {"kind": "audio", "asset_id": "a1", "start": 0, "end": 600, "gain": 0.7}
GUIDA_L = {"kind": "guida", "asset_id": "g1", "start": 10, "end": 300, "gain": 0.9,
           "respiri": 20, "round": 2, "vuoto_sec": 60, "pieno_sec": 15, "recupero_sec": 20,
           "parole": {"inspira": "p1", "espira": "p2"}}


class TestClipInLibreria:
    def test_vocabolario_in_parita_col_motore(self):
        js = re.search(r"export const GUIDA_TIPI = \[([^\]]*)\]", GUIDA).group(1)
        assert tuple(re.findall(r"'(\w+)'", js)) == GUIDA_TIPI

    def test_guida_e_ciclo_puliti(self):
        assert clean_guida("ciclo") == "ciclo" and clean_guida(" Inspira ") == "inspira"
        assert clean_guida("giostra") is None and clean_guida(3) is None
        assert clean_ciclo_sec("8.4") == 8.4 and clean_ciclo_sec(6.8) == 6.8
        assert clean_ciclo_sec(0.5) is None and clean_ciclo_sec("x") is None

    def test_la_proiezione_pubblica_porta_i_due_campi(self):
        blocco = ROUTER.split("_SOUND_PROJECTION = {")[1].split("}")[0]
        assert '"guida": 1' in blocco and '"ciclo_sec": 1' in blocco

    def test_gli_script_esistono_e_scrivono_la_categoria_giusta(self):
        prep = (BACKEND / "scripts" / "prepara_respiro.py").read_text(encoding="utf-8")
        imp = (BACKEND / "scripts" / "importa_respiro.py").read_text(encoding="utf-8")
        assert "afconvert" in prep and "normalizza(" in prep
        assert '"category": "respiro"' in imp and '"guida": guida' in imp and '"ciclo_sec": ciclo' in imp
        csv_ = (BACKEND.parent / "docs" / "sound" / "respiro_founder_2026-09-22.csv").read_text(encoding="utf-8")
        assert csv_.count("\n") >= 10 and ",ciclo,8.4," in csv_


class TestStratoGuida:
    def test_v5_solo_se_qualcuno_lo_chiede(self):
        s = clean_score(_score([AUDIO, GUIDA_L]))
        assert s["score_version"] == SCORE_VERSION_GUIDA
        g = [l for l in s["layers"] if l["kind"] == "guida"][0]
        assert g["respiri"] == 20 and g["round"] == 2 and g["vuoto_sec"] == 60
        assert g["pieno_sec"] == 15 and g["recupero_sec"] == 20 and g["campana"] is True
        assert g["parole"] == {"inspira": "p1", "espira": "p2"}
        s2 = clean_score(_score([{**AUDIO, "space": {"preset": "orbita"}}]))
        assert s2["score_version"] == SCORE_VERSION_SPACE

    def test_ricetta_di_ieri_identica(self):
        prima = clean_score(_score([AUDIO]))
        assert "guida" not in json.dumps(prima) and prima["score_version"] == 1

    def test_i_numeri_si_riportano_nei_limiti(self):
        s = clean_score(_score([{**GUIDA_L, "respiri": 9999, "round": 99, "vuoto_sec": -5,
                                 "pieno_sec": 999, "recupero_sec": 999}]))
        g = s["layers"][0]
        assert g["respiri"] == GUIDA_RESPIRI_MAX and g["round"] == GUIDA_ROUND_MAX
        assert g["vuoto_sec"] == 0 and g["pieno_sec"] == GUIDA_PIENO_MAX
        assert g["recupero_sec"] == GUIDA_RECUPERO_MAX
        assert GUIDA_VUOTO_MAX == 300

    def test_limiti_in_parita_col_motore(self):
        blocco = GUIDA.split("export const GUIDA_LIMITI")[1].split("});")[0]
        lim = {m.group(1): [int(x) for x in m.group(2).split(",")]
               for m in re.finditer(r"(\w+): \[([^\]]*)\]", blocco)}
        assert lim["respiri"][1] == GUIDA_RESPIRI_MAX and lim["round"][1] == GUIDA_ROUND_MAX
        assert lim["vuoto_sec"][1] == GUIDA_VUOTO_MAX and lim["pieno_sec"][1] == GUIDA_PIENO_MAX
        assert lim["recupero_sec"][1] == GUIDA_RECUPERO_MAX

    def test_parole_solo_note_e_sensate(self):
        s = clean_score(_score([{**GUIDA_L, "parole": {"inspira": "p1", "trattieni": "x", "espira": 5}}]))
        assert s["layers"][0]["parole"] == {"inspira": "p1"}
        s2 = clean_score(_score([{**GUIDA_L, "parole": "no"}]))
        assert "parole" not in s2["layers"][0]
        assert clean_score(_score([{**GUIDA_L, "asset_id": ""}])) is None


class TestMotore:
    def test_una_partitura_sola(self):
        assert "export function partituraGuida(l, ciclo" in GUIDA
        assert "export function montaGuida(ctx, dest, g, { da, a, quando })" in GUIDA
        # vivo e master passano dalla stessa porta
        assert "montaGuida(ctx, gg, g, { da: uA, a: span, quando: (u) => at(s0 + u) })" in SYNTH
        assert "montaGuida(off, gg, g, {" in RENDER
        assert "da: cs - g.start, a: Math.min(cs + len, fineStrato) - g.start" in RENDER
        assert "guidaLayers = []" in SYNTH and "guidaLayers = []" in RENDER

    def test_la_campana_e_sintetica_e_deterministica(self):
        assert "export function campanaBuffer(ctx)" in GUIDA
        assert "528" in GUIDA and "WeakMap" in GUIDA

    def test_gli_strati_risolti_arrivano_dalla_libreria(self):
        assert "export async function resolveGuidaLayers(ctx, score, soundsById)" in ASSETS
        blocco = ASSETS.split("export async function resolveGuidaLayers")[1].split("export async function")[0]
        assert "ciclo: asset.ciclo_sec ||" in blocco and "parole[k] = await loadAssetBuffer" in blocco
        # i tre chiamanti
        assert PAGE.count("resolveGuidaLayers(ctx, ") >= 3          # vivo, export, master
        assert "resolveGuidaLayers(ctx, track.score, soundsRef.current)" in PUBLIC
        assert "guidaLayers" in CONTINUO.split("export async function preparaContinuo")[1][:900]

    def test_la_guida_non_passa_da_spazio_ne_duck(self):
        ramo = SYNTH.split("guidaLayers.filter(")[1].split("(score.layers || [])")[0]
        assert "spazializza(" not in ramo and "duckBus" not in ramo and "uG.connect(sess)" in ramo


class TestCrea:
    def test_piu_guida_sui_cicli_e_niente_basi_dalle_parole(self):
        assert "fq-guida-add-${s.id}" in PAGE
        # 22/9 sera (founder): OGNI clip del respiro si aggiunge anche da solo,
        # senza loop, dove stai ascoltando; i cicli hanno in piu' «+ guida»
        assert "s.guida === 'ciclo' && (" in PAGE and "fq-sound-add-${s.id}" in PAGE
        assert "const eClipBreve = (asset) => !!asset.guida" in PAGE
        assert "loop: !breve" in PAGE and "'+ clip' : '+ sessione'" in PAGE
        assert "const addGuidaToSession = (asset, schema = 'continuo')" in PAGE

    def test_la_riga_ricalcola_la_fine_e_dice_la_versione(self):
        assert "const patchGuida = (l, patch) => {" in PAGE
        assert "l.start + durataGuida(next, ciclo)" in PAGE
        assert "score_version: hasGuida ? 5 :" in PAGE
        assert "fq-guida-schema-${l.id}" in PAGE and "fq-guida-riassunto-${l.id}" in PAGE
        assert "'bar guida'" in PAGE
