"""CI-F2 (22/9/2026) — LO SPAZIO in Crea: panner HRTF per strato e Stanza
per sessione, unica verita' in engine/spazio.js per anteprima, master e
ascolto continuo.

Le regole decise col founder, tenute ferme qui:
  1. la VOCE non ruota di default: «fermo» e' il default e non si scrive;
     ha i suoi preset («vicina», «a lato») e non ha «orbita»/«avvolge»;
  2. i BINAURALI non passano MAI dal panner: gli strati `neuro` non
     accettano `space` (backend) e nel motore non c'e' spazializzazione
     sul ramo neuro (statico);
  3. `space` e `stanza` ASSENTI = ricetta identica a ieri (nessuna chiave
     in piu', versione invariata) e nessun nodo in piu' nel motore;
  4. parita' dei vocabolari fra backend e engine/spazio.js;
  5. il master a blocchi riporta la coda (Stanza) al blocco successivo.
"""
import json
import re
from pathlib import Path

from models.frequency_track import (SCORE_VERSION_SPACE, SCORE_VERSION_VOICE, SCORE_VERSION,
                                    SPACE_PRESETS, STANZE, clean_score, clean_space, clean_stanza)

BACKEND = Path(__file__).resolve().parents[1]
FQ = BACKEND.parent / "frontend" / "src" / "features" / "frequenze"
SPAZIO = (FQ / "engine" / "spazio.js").read_text(encoding="utf-8")
SYNTH = (FQ / "engine" / "synth.js").read_text(encoding="utf-8")
RENDER = (FQ / "engine" / "render.js").read_text(encoding="utf-8")
PAGE = ((FQ / "FrequenzePage.js").read_text(encoding="utf-8") + (FQ / "crea" / "CreaVista.jsx").read_text(encoding="utf-8") + (FQ / "crea" / "TracceVista.jsx").read_text(encoding="utf-8"))


def _score(layers, **extra):
    return {"score_version": 1, "duration_sec": 600, "layers": layers, **extra}


AUDIO = {"kind": "audio", "asset_id": "a1", "start": 0, "end": 600, "gain": 0.7}
VOICE = {"kind": "voice", "asset_id": "v1", "start": 10, "end": 60, "gain": 0.9}
BIN = {"method": "bin", "carrier": 200, "f0": 10, "start": 0, "end": 600, "gain": 0.5}


class TestModelloSpazio:
    def test_assente_e_fermo_non_lasciano_traccia(self):
        s = clean_score(_score([AUDIO, VOICE]))
        assert "stanza" not in s and all("space" not in l for l in s["layers"])
        assert s["score_version"] == SCORE_VERSION_VOICE
        s2 = clean_score(_score([{**AUDIO, "space": {"preset": "fermo"}}], stanza="asciutta"))
        assert "stanza" not in s2 and "space" not in s2["layers"][0]
        assert s2["score_version"] == SCORE_VERSION

    def test_ricetta_di_ieri_identica(self):
        prima = clean_score(_score([AUDIO, VOICE, BIN]))
        dopo = clean_score(_score([AUDIO, VOICE, BIN]))
        assert json.dumps(prima, sort_keys=True) == json.dumps(dopo, sort_keys=True)
        assert "space" not in json.dumps(prima) and "stanza" not in json.dumps(prima)

    def test_v4_solo_se_qualcuno_lo_chiede(self):
        s = clean_score(_score([{**AUDIO, "space": {"preset": "orbita_lenta"}}]))
        assert s["score_version"] == SCORE_VERSION_SPACE
        assert s["layers"][0]["space"] == {"preset": "orbita_lenta"}
        s2 = clean_score(_score([AUDIO], stanza="tempio"))
        assert s2["score_version"] == SCORE_VERSION_SPACE and s2["stanza"] == "tempio"

    def test_la_voce_ha_i_suoi_preset_e_non_orbita_larga(self):
        assert clean_space("voice", {"preset": "vicina"}) == {"preset": "vicina"}
        assert clean_space("voice", {"preset": "a_lato"}) == {"preset": "a_lato"}
        assert clean_space("voice", {"preset": "orbita"}) is None
        assert clean_space("voice", {"preset": "avvolge"}) is None
        assert clean_space("audio", {"preset": "vicina"}) is None
        assert clean_space("audio", {"preset": "avvolge"}) == {"preset": "avvolge"}

    def test_i_binaurali_non_hanno_spazio(self):
        s = clean_score(_score([{**BIN, "space": {"preset": "orbita"}}]))
        assert "space" not in s["layers"][0]
        assert s["score_version"] == SCORE_VERSION
        assert "neuro" not in SPACE_PRESETS

    def test_stanza_e_immondizia(self):
        assert clean_stanza("cattedrale") == "cattedrale"
        assert clean_stanza("asciutta") is None and clean_stanza("garage") is None
        assert clean_stanza(42) is None
        assert clean_space("audio", "orbita") is None        # deve essere un dict
        assert clean_space("audio", {"preset": "giostra"}) is None


class TestParitaConIlMotore:
    def _js_presets(self):
        blocco = SPAZIO.split("export const SPACE_PRESETS")[1].split("});")[0]
        out = {}
        for m in re.finditer(r"^\s*(\w+): \{ label: '[^']*', kinds: \[([^\]]*)\]", blocco, re.M):
            out[m.group(1)] = re.findall(r"'(\w+)'", m.group(2))
        return out

    def test_preset_e_tipi_in_parita(self):
        js = self._js_presets()
        for kind, presets in SPACE_PRESETS.items():
            assert tuple(k for k, kinds in js.items() if kind in kinds) == presets, (kind, js)

    def test_stanze_in_parita(self):
        blocco = SPAZIO.split("export const STANZE")[1].split("});")[0]
        assert tuple(re.findall(r"^\s*(\w+): \{", blocco, re.M)) == STANZE

    def test_regole_nei_commenti_e_nei_default(self):
        assert "fermo: { label: 'fermo'" in SPAZIO
        assert "MAX_PANNER_VIVI = 6" in SPAZIO
        assert "panningModel = economico ? 'equalpower' : 'HRTF'" in SPAZIO


class TestMotore:
    def test_solo_basi_e_voce_passano_dal_panner(self):
        # due chiamate: una per le basi, una per la voce — mai sul ramo neuro
        assert SYNTH.count("spazializza(l, 'audio'") == 1
        assert SYNTH.count("spazializza(l, 'voice'") == 1
        ramo_neuro = SYNTH.split("(l.kind || 'neuro') === 'neuro'")[1]
        assert "spazializza(" not in ramo_neuro and "createPanner" not in ramo_neuro

    def test_senza_spazio_nessun_nodo(self):
        assert "if (!spaceValido(kind, l.space?.preset)) { from.connect(to); return; }" in SYNTH
        assert "stanzaValida(score.stanza)" in SYNTH

    def test_master_riporta_la_coda(self):
        assert "tailFrames" in RENDER and "carryL" in RENDER
        assert "new OfflineAudioContext(2, frames + tailFrames, sr)" in RENDER
        assert "creaSpazio(off, l.space.preset" in RENDER
        # la voce spaziale nel pre-render del clip wet
        assert "spaceValido('voice', l.space?.preset)" in RENDER

    def test_lo_strato_risolto_porta_lo_spazio(self):
        """IL BUG (22/9 sera): resolveAudioLayers/resolveVoiceLayers
        ricostruiscono lo strato campo per campo e `space` restava fuori
        — il motore legge `l.space` dallo strato RISOLTO, quindi nessun
        panner e' mai nato e il founder non ha sentito niente."""
        assets = (FQ / "engine" / "assets.js").read_text(encoding="utf-8")
        basi = assets.split("export async function resolveAudioLayers")[1].split("export async function")[0]
        voce = assets.split("export async function resolveVoiceLayers")[1].split("export async function")[0]
        assert "space: l.space" in basi
        assert "space: l.space" in voce

    def test_il_rinforzo_e_unico_per_vivo_e_master(self):
        """CI-F2b (22/9 sera, founder: «non ho notato differenze, anche
        con le cuffie»): l'HRTF da solo sui tappeti gravi e larghi non
        si sente. Il rimedio (downmix mono + StereoPanner che segue lo
        stesso angolo) vive in UN punto, creaSpazio, e i tre consumatori
        passano tutti di li' — mai un panner nudo fuori da spazio.js."""
        assert "export function creaSpazio(ctx, preset" in SPAZIO
        assert "pan.channelCount = 1; pan.channelCountMode = 'explicit';" in SPAZIO
        assert "createStereoPanner" in SPAZIO
        assert "export function lato(preset, u)" in SPAZIO
        for src in (SYNTH, RENDER):
            assert "creaPanner(" not in src and "creaSpazio(" in src
        for preset in ("orbita_lenta", "orbita", "avvolge", "respira"):
            riga = SPAZIO.split(f"  {preset}: {{")[1].split("hint:")[0]
            assert "mono: true" in riga and "rinforzo:" in riga, preset
        # la voce «vicina» non ha rinforzo: si avvicina, non gira
        assert "rinforzo" not in SPAZIO.split("  vicina: {")[1].split("hint:")[0]

    def test_la_compensazione_del_volume(self):
        """22/9 sera (founder: «nei suoni spaziali il volume diventa molto
        piu' basso»): ogni preset che muove o allontana porta un `comp`
        che riporta la potenza media di un giro a quella di «fermo»;
        applicato in creaSpazio, quindi identico dal vivo e nel master."""
        for preset in ("respira", "orbita_lenta", "orbita", "avvolge", "vicina", "a_lato"):
            riga = SPAZIO.split(f"  {preset}: {{")[1].split("hint:")[0]
            assert "comp:" in riga, preset
        assert "comp:" not in SPAZIO.split("  fermo: {")[1].split("hint:")[0]
        assert "comp.gain.value = p.comp;" in SPAZIO
        assert "output.connect(comp);" in SPAZIO
        # senza spazio: coda zero, percorso di ieri
        assert "const tailSec = conSpazio ?" in RENDER

    def test_stessa_traiettoria_ovunque(self):
        # la posizione e' una funzione del tempo dello strato, non un LFO
        assert "export function posizione(preset, u)" in SPAZIO
        assert "uA: t0 - l.start, uB: tE - l.start" in RENDER


class TestCrea:
    def test_selettori_in_pagina(self):
        assert "fq-space-${l.id}" in PAGE
        assert 'data-testid="fq-stanza"' in PAGE
        assert "presetPerTipo('audio')" in PAGE and "presetPerTipo('voice')" in PAGE
        assert "hasSpace ? 4 :" in PAGE      # CI-F1: davanti c'e' la guida (v5)
        assert "setStanza('asciutta')" in PAGE          # reset sessione
        assert 'data-testid="fq-nota-spazio"' in PAGE   # in cuffia, e i binaurali non girano

    def test_spazio_e_stanza_si_sentono_subito(self):
        """CI-F2b: cambiare spazio o Stanza mentre suona fa ripartire
        la sessione dal punto in cui era (il grafo si costruisce alla
        partenza: non c'e' altro modo onesto di farlo sentire)."""
        assert "const riavviaSeSuona = () => {" in PAGE
        assert "if (patch.space !== undefined) riavviaSeSuona();" in PAGE
        blocco_stanza = PAGE.split('data-testid="fq-stanza"')[1][:300]
        assert "riavviaSeSuona();" in blocco_stanza
        assert "riparte dal punto in cui era" in PAGE
