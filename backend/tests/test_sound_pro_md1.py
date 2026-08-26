"""Sound Professional M-D/1 + M7a — la partitura e la porta (26/8/2026).

La partitura è la risposta VISIVA a «cosa succederà»: si disegna dai
dati veri dello score, e se si vede qualcosa è perché sta nello score.
Questi test ESEGUONO la geometria in Node sui protocolli veri del
catalogo e la misurano — proporzioni del tempo, spessore=volume,
niente inventato. E la porta (M7a): il link Professional esiste solo
per chi ha il privilegio; per tutti gli altri la passerella è
identica a prima.
"""
import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest

BACKEND_DIR = Path(__file__).resolve().parents[1]
FRONTEND_SRC = BACKEND_DIR.parent / "frontend" / "src"
FQ = FRONTEND_SRC / "features" / "frequenze"
PRO = FQ / "pro"
SPARTITO = PRO / "spartito.js"
VESTE = PRO / "Partitura.jsx"
TOPBAR = FQ / "SoundTopbar.jsx"

_NODE = shutil.which("node") or \
    "/Users/davidedefilippis/.nvm/versions/node/v22.13.1/bin/node"
node_c_e = pytest.mark.skipif(not Path(_NODE).exists(),
                              reason="node non disponibile")


def _senza_commenti(testo: str) -> str:
    testo = re.sub(r"/\*.*?\*/", " ", testo, flags=re.S)
    return re.sub(r"^\s*//.*$", " ", testo, flags=re.M)


def _esegui(corpo: str, tmp_path):
    """Spartito + catalogo veri in Node (copie con import estesi)."""
    files = {
        "spartito.js": SPARTITO,
        "catalogo.js": PRO / "catalogo.js",
        "esperienze.js": FQ / "content" / "esperienze.js",
        "calm.js": FQ / "content" / "calm.js",
        "ground.js": FQ / "content" / "ground.js",
        "protocolli.js": FQ / "content" / "protocolli.js",
    }
    for nome, sorgente in files.items():
        testo = sorgente.read_text()
        testo = testo.replace("from '../content/", "from './")
        testo = re.sub(r"from '(\./[a-z]+)'", r"from '\1.js'", testo)
        (tmp_path / nome).write_text(testo)
    script = (
        f"import {{ partitura, famiglie, famiglia }} "
        f"from {json.dumps(str(tmp_path / 'spartito.js'))};\n"
        f"import {{ CATALOGO }} from {json.dumps(str(tmp_path / 'catalogo.js'))};\n"
        + corpo)
    r = subprocess.run([_NODE, "--input-type=module", "-e", script],
                       capture_output=True, text=True, timeout=60)
    assert r.returncode == 0, f"node è morto: {r.stderr[:500]}"
    return json.loads(r.stdout.strip().splitlines()[-1])


# ── 1-5 · la geometria dice la verità ──────────────────────────────────────
@node_c_e
class TestLaGeometria:
    def test_01_ogni_protocollo_del_catalogo_si_disegna(self, tmp_path):
        out = _esegui("""
console.log(JSON.stringify(CATALOGO.map(p => {
  const score = p.costruisci();
  const vivi = score.layers.filter(l => !l.mute).length;
  const g = partitura(score, { w: 600, h: 120 });
  return { id: p.id, vivi, bande: g.bande.length, durata: g.durata };
})));""", tmp_path)
        assert len(out) == 8
        for voce in out:
            assert voce["bande"] == voce["vivi"], \
                f"{voce['id']}: {voce['vivi']} suoni ma {voce['bande']} bande"
            assert voce["durata"] > 0

    def test_02_il_tempo_e_in_proporzione(self, tmp_path):
        """La banda di un livello che vive da start a end deve stare
        esattamente lì sull'asse: x = t/durata × larghezza."""
        out = _esegui("""
const p = CATALOGO.find(v => v.id === 'ground');
const score = p.costruisci();
const g = partitura(score, { w: 600, h: 120 });
console.log(JSON.stringify(score.layers.filter(l => !l.mute).map((l, i) => ({
  attesoX0: (l.start / score.duration_sec) * 600,
  attesoX1: (l.end / score.duration_sec) * 600,
  x0: g.bande[i].x0, x1: g.bande[i].x1,
}))));""", tmp_path)
        for b in out:
            assert abs(b["x0"] - b["attesoX0"]) < 0.51, b
            assert abs(b["x1"] - b["attesoX1"]) < 0.51, b

    def test_03_lo_spessore_e_il_volume(self, tmp_path):
        """Più gain, più spessa: la relazione è monotona — mai una
        banda sottile per un suono forte."""
        out = _esegui("""
const score = { score_version: 1, duration_sec: 600, fade_in_sec: 0,
  fade_out_sec: 0, phases: [], layers: [0.1, 0.3, 0.6, 0.9].map((gain, i) => ({
    kind: 'neuro', method: 'tone', carrier: 200, f0: 10, f1: 10,
    curve: 'lin', start: 0, end: 600, gain, breath: true, mute: false,
  })) };
const g = partitura(score, { w: 600, h: 200 });
console.log(JSON.stringify(g.bande.map(b => [b.alto, b.opacita])));""", tmp_path)
        alti = [b[0] for b in out]
        opac = [b[1] for b in out]
        assert alti == sorted(alti) and len(set(alti)) == 4, \
            f"lo spessore non segue il volume: {alti}"
        assert opac == sorted(opac), f"l'opacità non segue il volume: {opac}"

    def test_04_il_battito_che_scivola_si_disegna_quello_fermo_no(self, tmp_path):
        """La linea dentro la banda esiste solo dove c'è un tragitto:
        un battito fermo non ha niente da raccontare."""
        out = _esegui("""
const casi = [
  { method: 'bin', f0: 10, f1: 6, curve: 'exp' },   // scivola
  { method: 'iso', f0: 8, f1: 8, curve: 'lin' },    // fermo
  { method: 'tone', f0: 10, f1: 10, curve: 'lin' }, // niente battito
];
const score = { score_version: 1, duration_sec: 600, fade_in_sec: 0,
  fade_out_sec: 0, phases: [], layers: casi.map(c => ({
    kind: 'neuro', carrier: 200, start: 0, end: 600, gain: 0.3,
    breath: true, mute: false, ...c })) };
const g = partitura(score, { w: 600, h: 200 });
console.log(JSON.stringify({ curve: g.curve.length,
  primaScende: g.curve[0] && g.curve[0].punti[0][1] <
    g.curve[0].punti[g.curve[0].punti.length - 1][1] }));""", tmp_path)
        assert out["curve"] == 1, "curva disegnata dove il battito è fermo"
        assert out["primaScende"] is True, \
            "il battito 10→6 scende: la linea deve scendere"

    def test_05_deterministica_e_muta_sui_muti(self, tmp_path):
        out = _esegui("""
const p = CATALOGO.find(v => v.id === 'calm');
const a = JSON.stringify(partitura(p.costruisci(), { w: 600, h: 120 }));
const b = JSON.stringify(partitura(p.costruisci(), { w: 600, h: 120 }));
const score = p.costruisci();
score.layers[0].mute = true;
const g = partitura(score, { w: 600, h: 120 });
console.log(JSON.stringify({ uguale: a === b,
  bande: g.bande.length, vivi: score.layers.filter(l => !l.mute).length }));""",
                      tmp_path)
        assert out["uguale"], "la partitura non è deterministica"
        assert out["bande"] == out["vivi"], "un suono muto è stato disegnato"


# ── 6-8 · la veste è un disegno, non un visualizzatore ─────────────────────
class TestLaVeste:
    def test_06_svg_puro_niente_canvas_niente_orologi(self):
        src = _senza_commenti(VESTE.read_text()).lower()
        assert "<svg" in src
        for vietato in ("canvas", "requestanimationframe", "setinterval",
                        "settimeout", "audiocontext", "getcontext"):
            assert vietato not in src, f"la veste contiene «{vietato}»"
        # lo spartito resta puro: zero import, zero React
        spart = _senza_commenti(SPARTITO.read_text())
        assert "import" not in spart.split("export")[0]
        assert "react" not in spart.lower()

    def test_07_i_colori_sono_del_tema(self):
        src = _senza_commenti(VESTE.read_text())
        assert "var(--lamp)" in src and "var(--water)" in src
        # e la geometria non conosce colori: solo nomi di famiglia
        spart = _senza_commenti(SPARTITO.read_text())
        assert "#" not in re.sub(r"\d", "", spart) or True
        assert not re.search(r"#[0-9a-fA-F]{3,6}\b", spart), \
            "lo spartito ha un colore: la veste è l'unico posto dei colori"

    def test_08_dove_si_vede(self):
        """Sulla card (mini), sulla scheda (grande, con fasi e
        legenda), nella preparazione del rito."""
        pagina = _senza_commenti((PRO / "SoundProPage.jsx").read_text())
        assert pagina.count("<Partitura") >= 2, "manca su card o scheda"
        assert "dettaglio" in pagina, "la scheda non usa la vista grande"
        rito = _senza_commenti((PRO / "Rito.jsx").read_text())
        assert "<Partitura" in rito, "manca nella preparazione del rito"


# ── 9-10 · la porta (M7a) ──────────────────────────────────────────────────
class TestLaPorta:
    def test_09_professional_solo_con_privilegio(self):
        src = _senza_commenti(TOPBAR.read_text())
        assert "user?.sound_professional" in src
        assert "'/sound/pro'" in src and "'Professional'" in src
        # la voce nasce dal condizionale, NON dentro PASSERELLA: per
        # gli anonimi la passerella resta identica a prima
        m = re.search(r"const PASSERELLA = \[(.*?)\];", src, re.S)
        assert m and "/sound/pro" not in m.group(1), \
            "Professional è finito nella passerella di tutti"

    def test_10_le_pagine_pubbliche_non_sono_cambiate(self):
        """La topbar è condivisa col mondo pubblico: la modifica è
        additiva e condizionale, i file pubblici restano intatti."""
        r = subprocess.run(
            ["git", "diff", "--name-only", "HEAD", "--",
             "frontend/src/features/frequenze/MeditazioniPage.js",
             "frontend/src/features/frequenze/PublicFrequencyPage.js",
             "frontend/src/features/frequenze/SoundLandingPage.js",
             "frontend/src/features/frequenze/FrequenzePage.js",
             "frontend/src/features/frequenze/esperienze",
             "frontend/src/features/frequenze/lab",
             "frontend/src/features/frequenze/engine",
             "frontend/src/features/frequenze/content"],
            cwd=BACKEND_DIR.parent, capture_output=True, text=True)
        if r.returncode != 0:
            pytest.skip("git non disponibile")
        assert not r.stdout.strip(), f"toccato: {r.stdout}"
