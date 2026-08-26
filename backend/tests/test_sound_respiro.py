"""RESPIRO — la guida che si può anticipare (C2, 26/8/2026).

La scheda con le basi più solide del catalogo, e la prima dove il
suono non è la pratica ma il METRONOMO della pratica: si respira a
sei atti al minuto, con l'espirazione più lunga.

Il difetto che questa onda ripara, detto dal founder e confermato
dalla letteratura sui pacer: un inviluppo dice DOVE SEI, non QUANDO
CAMBIERÀ — e chi respira insegue invece di anticipare. Le due cure,
misurate qui: l'altezza che scivola (pendenza prevedibile) e il tocco
alla svolta. Entrambe OPT-IN: il respiro-texture di CALM non cambia.
"""
import json
import re
import subprocess
from pathlib import Path

import pytest

BACKEND_DIR = Path(__file__).resolve().parents[1]
FRONTEND_SRC = BACKEND_DIR.parent / "frontend" / "src"
FQ = FRONTEND_SRC / "features" / "frequenze"
RICETTA = FQ / "content" / "respiro.js"
SYNTH = FQ / "engine" / "synth.js"

from nodo import NODE as _NODE, node_c_e  # noqa: F401


def _senza_commenti(testo: str) -> str:
    testo = re.sub(r"/\*.*?\*/", " ", testo, flags=re.S)
    return re.sub(r"^\s*//.*$", " ", testo, flags=re.M)


def _testo(percorso: Path) -> str:
    t = _senza_commenti(percorso.read_text())
    return re.sub(r"'\s*\n\s*\+\s*'", "", t)


def _motore(corpo: str, tmp_path):
    """Le forme VERE del motore, eseguite in Node."""
    for f in FQ.glob("engine/*.js"):
        testo = f.read_text()
        testo = re.sub(r"from '(\./[a-z]+)'", r"from '\1.js'", testo)
        (tmp_path / f.name).write_text(testo)
    script = (f"import * as S from {json.dumps(str(tmp_path / 'synth.js'))};\n"
              + corpo)
    r = subprocess.run([_NODE, "--input-type=module", "-e", script],
                       capture_output=True, text=True, timeout=60)
    assert r.returncode == 0, f"node è morto: {r.stderr[:500]}"
    return json.loads(r.stdout.strip().splitlines()[-1])


def _ricetta(corpo: str, tmp_path):
    """La ricetta vera (respiro.js + la sua fabbrica di livelli)."""
    for nome in ("respiro.js", "protocolli.js"):
        testo = (FQ / "content" / nome).read_text()
        testo = re.sub(r"from '(\./[a-z]+)'", r"from '\1.js'", testo)
        (tmp_path / nome).write_text(testo)
    script = (f"import * as R from {json.dumps(str(tmp_path / 'respiro.js'))};\n"
              + corpo)
    r = subprocess.run([_NODE, "--input-type=module", "-e", script],
                       capture_output=True, text=True, timeout=60)
    assert r.returncode == 0, f"node è morto: {r.stderr[:500]}"
    return json.loads(r.stdout.strip().splitlines()[-1])


# ── 1-4 · le forme: si può anticipare la svolta ────────────────────────────
@node_c_e
class TestLeForme:
    def test_01_il_rapporto_e_quattro_a_sei(self, tmp_path):
        """La raccomandazione per massimizzare la variabilità
        cardiaca. A sei atti al minuto: 3,6 s dentro, 5,4 s fuori."""
        out = _ricetta("""
console.log(JSON.stringify({
  inspira: R.RESPIRO_INSPIRA, espira: R.RESPIRO_ESPIRA,
  alMinuto: R.RESPIRO_AL_MINUTO, hz: R.alMinuto(R.RESPIRO_AL_MINUTO),
}));""", tmp_path)
        i, e = out["inspira"], out["espira"]
        assert round(i / (i + e), 3) == 0.4, f"rapporto {i}:{e}, non 4:6"
        assert out["alMinuto"] == 6
        assert abs(out["hz"] - 0.1) < 1e-9, "sei al minuto sono 0,1 Hz"
        per = 60 / out["alMinuto"]
        assert abs(i * per - 3.6) < 0.01 and abs(e * per - 5.4) < 0.01
        assert 1 - i - e > 0.05, "senza pausa il ciclo non ha un fondo"

    def test_02_l_altezza_culmina_esattamente_alla_svolta(self, tmp_path):
        """È il cue dell'anticipazione: la pendenza dice dove si sta
        andando, e il picco cade sul cambio di fase."""
        out = _motore("""
const IN = 0.36, OUT = 0.54, N = 400;
let picco = { u: -1, v: -1 };
const su = [], giu = [];
for (let k = 0; k < N; k++) {
  const u = k / N, v = S.breathPitch(u, IN, OUT);
  if (v > picco.v) picco = { u, v };
  if (u < IN) su.push(v); else if (u < IN + OUT) giu.push(v);
}
const cresce = su.every((v, i) => i === 0 || v >= su[i - 1] - 1e-9);
const cala = giu.every((v, i) => i === 0 || v <= giu[i - 1] + 1e-9);
console.log(JSON.stringify({ piccoA: picco.u, piccoV: picco.v,
  cresce, cala, inizio: S.breathPitch(0, IN, OUT),
  pausa: S.breathPitch(0.95, IN, OUT) }));""", tmp_path)
        assert abs(out["piccoA"] - 0.36) < 0.01, \
            f"l'altezza culmina a {out['piccoA']}, non alla svolta"
        assert out["piccoV"] > 0.99
        assert out["cresce"] and out["cala"], \
            "la salita o la discesa non è monotona: la pendenza mente"
        assert out["inizio"] == 0 and out["pausa"] == 0

    def test_03_i_tocchi_cadono_sulle_due_svolte(self, tmp_path):
        out = _motore("""
const IN = 0.36, OUT = 0.54, N = 400;
const dove = (quale) => {
  let best = { u: -1, v: -1 };
  for (let k = 0; k < N; k++) {
    const u = k / N, v = S.breathTick(u, IN, OUT, quale);
    if (v > best.v) best = { u, v };
  }
  return best;
};
const larghezza = (quale) => {
  let n = 0;
  for (let k = 0; k < N; k++) if (S.breathTick(k / N, IN, OUT, quale) > 0) n++;
  return n / N;
};
console.log(JSON.stringify({ inA: dove('in').u, outA: dove('out').u,
  largo: larghezza('in'), semitoni: S.BREATH_GLIDE_SEMI }));""", tmp_path)
        assert out["inA"] < 0.01, "il tocco dell'inspirazione non è all'inizio"
        assert abs(out["outA"] - 0.36) < 0.01, \
            "il tocco dell'espirazione non è sulla svolta"
        assert 0.02 < out["largo"] < 0.12, \
            "il tocco è un accenno, non una nota lunga"
        assert 1 <= out["semitoni"] <= 5, "l'escursione non è musicale"

    def test_04_la_guida_e_opt_in(self, tmp_path):
        """Il respiro-texture (CALM) non deve cambiare: senza `guida`
        niente glissando e niente tocchi."""
        src = _senza_commenti(SYNTH.read_text())
        assert "l.guida" in src
        assert "const gl = l.guida" in src, "il glissando non è condizionato"
        assert "if (l.guida) {" in src, "i tocchi non sono condizionati"
        # e CALM non la chiede
        calm = _senza_commenti((FQ / "content" / "calm.js").read_text())
        assert "guida" not in calm, "CALM è diventata un pacer"


# ── 5-7 · la ricetta ───────────────────────────────────────────────────────
@node_c_e
class TestLaRicetta:
    def test_05_due_voci_e_un_ritmo_costante(self, tmp_path):
        out = _ricetta("""
const s = R.costruisciRespiro();
console.log(JSON.stringify({
  durata: s.duration_sec, voci: s.layers.length,
  metodi: s.layers.map(l => l.method),
  guida: s.layers.find(l => l.method === 'breath'),
}));""", tmp_path)
        assert out["durata"] == 600
        assert out["voci"] == 2, "l'attenzione deve avere un posto solo"
        assert out["metodi"] == ["drone", "breath"]
        g = out["guida"]
        assert g["guida"] is True, "la guida non è accesa nella ricetta"
        assert g["f0"] == g["f1"], "il ritmo deve essere COSTANTE"
        assert abs(g["f0"] - 0.1) < 1e-9
        assert abs(g["inhale"] - 0.36) < 1e-9 and abs(g["exhale"] - 0.54) < 1e-9, \
            "le quote 4:6 non sono arrivate al livello"
        assert g["gain"] > 0.2, "la guida deve stare sopra il fondo"

    def test_06_il_contratto_del_server_conserva_la_guida(self, tmp_path):
        """Se `guida` non sopravvive a clean_score, una traccia
        pubblicata tornerebbe texture: si ascolterebbe una cosa e se ne
        pubblicherebbe un'altra."""
        import sys
        sys.path.insert(0, str(BACKEND_DIR))
        from models.frequency_track import clean_score
        score = _ricetta("console.log(JSON.stringify(R.costruisciRespiro()));",
                         tmp_path)
        pulito = clean_score(score)
        assert pulito is not None, "il contratto rifiuta RESPIRO"
        g = [l for l in pulito["layers"] if l["method"] == "breath"][0]
        assert g.get("guida") is True, "il contratto ha perso la guida"
        assert g["inhale"] == 0.36 and g["exhale"] == 0.54

    def test_07_niente_promesse_e_niente_misure(self, tmp_path):
        """Si può essere precisi senza promettere. E finché non c'è un
        sensore, qui si GUIDA soltanto: non si misura niente."""
        basso = _testo(RICETTA).lower()
        for veleno in ("guarig", "cura", "riequilibr", "abbassa la",
                       "riduce lo stress", "misura", "biofeedback"):
            assert veleno not in basso, f"la ricetta dice «{veleno}»"
        # i numeri veri invece ci sono
        for numero in ("6", "4:6", "0.36", "0.54"):
            assert numero in _testo(RICETTA)


# ── 8-9 · il posto nel sistema ─────────────────────────────────────────────
class TestNelSistema:
    def test_08_registro_catalogo_specchio_rotta_sitemap(self):
        reg = _senza_commenti((FQ / "content" / "esperienze.js").read_text())
        assert "respiro:" in reg and "costruisciRespiro" in reg
        cat = _testo(FQ / "pro" / "catalogo.js")
        assert "daEsperienza('respiro'" in cat
        assert "Lehrer" in cat and "4:6" in cat
        from models.sound_catalog import CATALOGO_CORE
        assert CATALOGO_CORE["respiro"] == ("RESPIRO", 1, 600)
        app = (FRONTEND_SRC / "App.js").read_text()
        assert 'path="/sound/respiro"' in app
        seo = (BACKEND_DIR / "routers" / "seo.py").read_text()
        assert "/sound/respiro" in seo
        shell = (BACKEND_DIR / "routers" / "seo_shell.py").read_text()
        assert '"respiro"' in shell and "_respiro_content_html" in shell

    def test_09_la_scheda_dichiara_grado_e_confine(self):
        cat = _testo(FQ / "pro" / "catalogo.js")
        blocco = cat[cat.find("daEsperienza('respiro'"):cat.find("daEsperienza('ground'")]
        assert "grado: 'A'" in blocco, \
            "è la scheda con le basi più solide: il grado deve dirlo"
        assert "Lehrer" in blocco and "Gevirtz" in blocco
        assert "come:" in blocco and "cuffia" in blocco.lower()
        # e la voce resta quella di casa: nessuna promessa
        for veleno in ("guarisce", "riequilibra", "garantis"):
            assert veleno not in blocco.lower()
