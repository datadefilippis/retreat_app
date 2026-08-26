"""Sound Professional M5 — i progressi (26/8/2026).

Il quadro della persona: sintesi onesta + il vissuto DISEGNATO — un
segmento dal prima al dopo per ogni sessione, la linea dei dopo come
andamento. La regola: niente punti inventati, niente medie, niente
interpretazione — è un grafico di dichiarazioni soggettive.
"""
import json
import re
import subprocess
from pathlib import Path

import pytest

BACKEND_DIR = Path(__file__).resolve().parents[1]
FRONTEND_SRC = BACKEND_DIR.parent / "frontend" / "src"
PRO = FRONTEND_SRC / "features" / "frequenze" / "pro"
ANDAMENTO = PRO / "andamento.js"
PAGINA = PRO / "SoundProPage.jsx"

from nodo import NODE as _NODE, node_c_e  # noqa: F401


def _senza_commenti(testo: str) -> str:
    testo = re.sub(r"/\*.*?\*/", " ", testo, flags=re.S)
    return re.sub(r"^\s*//.*$", " ", testo, flags=re.M)


def _esegui(corpo: str, tmp_path):
    import shutil as _sh
    _sh.copy(ANDAMENTO, tmp_path / "andamento.js")
    script = (f"import {{ andamento, sintesi }} from "
              f"{json.dumps(str(tmp_path / 'andamento.js'))};\n" + corpo)
    r = subprocess.run([_NODE, "--input-type=module", "-e", script],
                       capture_output=True, text=True, timeout=30)
    assert r.returncode == 0, f"node è morto: {r.stderr[:400]}"
    return json.loads(r.stdout.strip().splitlines()[-1])


@node_c_e
class TestLaGeometria:
    def test_01_un_segmento_per_sessione_dal_prima_al_dopo(self, tmp_path):
        out = _esegui("""
const sessioni = [
  { stato: 'completata', feedback_pre: 4, feedback_post: 7 },
  { stato: 'completata', feedback_pre: 5, feedback_post: 5 },
  { stato: 'interrotta', feedback_pre: 6, feedback_post: 3 },
];
const g = andamento(sessioni, { w: 600, h: 90 });
console.log(JSON.stringify({ segmenti: g.segmenti.map(s => s.verso),
  linea: g.linea.length, righe: g.righe.map(r => r.valore) }));""", tmp_path)
        assert out["segmenti"] == ["su", "pari", "giu"]
        assert out["linea"] == 3
        assert out["righe"] == [1, 5, 10]

    def test_02_niente_punti_inventati(self, tmp_path):
        """Sessione senza vissuto → NON compare; solo-pre → il punto è
        il pre, senza segmento (non c'è delta da mostrare)."""
        out = _esegui("""
const sessioni = [
  { stato: 'completata' },                                  // muta
  { stato: 'completata', feedback_pre: 4 },                 // solo prima
  { stato: 'completata', feedback_post: 8 },                // solo dopo
];
const g = andamento(sessioni, { w: 600, h: 90 });
console.log(JSON.stringify({ linea: g.linea.length,
  segmenti: g.segmenti.length }));""", tmp_path)
        assert out["linea"] == 2, "la sessione muta è stata disegnata"
        assert out["segmenti"] == 0, "un segmento senza entrambi i capi"

    def test_03_la_scala_e_ancorata_e_l_alto_e_meglio(self, tmp_path):
        """10 sta in alto, 1 in basso, sempre: la scala non si adatta
        ai dati (un grafico che si auto-scala drammatizza i deltas)."""
        out = _esegui("""
const piatti = andamento([
  { stato: 'completata', feedback_pre: 5, feedback_post: 6 },
  { stato: 'completata', feedback_pre: 5, feedback_post: 6 },
], { w: 600, h: 90 });
const pieni = andamento([
  { stato: 'completata', feedback_pre: 1, feedback_post: 10 },
], { w: 600, h: 90 });
console.log(JSON.stringify({
  y5piatti: piatti.righe.find(r => r.valore === 5).y,
  y5pieni: pieni.righe.find(r => r.valore === 5).y,
  suSale: pieni.segmenti[0].y1 < pieni.segmenti[0].y0,
}));""", tmp_path)
        assert out["y5piatti"] == out["y5pieni"], \
            "la scala si adatta ai dati: i delta si gonfiano"
        assert out["suSale"], "il «su» deve andare verso l'alto"

    def test_04_sintesi_onesta_e_tappe_solo_completate(self, tmp_path):
        out = _esegui("""
const sessioni = [
  { stato: 'completata', percorso: { id: 'radicamento', titolo: 'Radicamento', tappa: 1, totale: 8 } },
  { stato: 'interrotta', percorso: { id: 'radicamento', titolo: 'Radicamento', tappa: 2, totale: 8 } },
  { stato: 'completata', percorso: { id: 'radicamento', titolo: 'Radicamento', tappa: 1, totale: 8 } },
  { stato: 'persa' },
  { stato: 'in_corso' },
];
console.log(JSON.stringify(sintesi(sessioni)));""", tmp_path)
        assert out["totale"] == 4, "l'in_corso non è una sessione da contare"
        assert (out["completate"], out["interrotte"], out["perse"]) == (2, 1, 1)
        (pc,) = out["percorsi"]
        assert pc["fatte"] == 1, \
            "la tappa interrotta o ripetuta non avanza il percorso"

    def test_05_deterministico_e_puro(self, tmp_path):
        out = _esegui("""
const s = [{ stato: 'completata', feedback_pre: 3, feedback_post: 9 }];
console.log(JSON.stringify({
  uguale: JSON.stringify(andamento(s)) === JSON.stringify(andamento(s)) }));""",
                      tmp_path)
        assert out["uguale"]
        src = _senza_commenti(ANDAMENTO.read_text())
        assert "import" not in src.split("export")[0]
        assert "react" not in src.lower()


class TestIlQuadro:
    def test_06_solo_con_la_persona_scelta(self):
        """Un andamento aggregato di persone diverse non significa
        niente: il quadro compare solo col filtro persona."""
        src = _senza_commenti(PAGINA.read_text())
        assert "cliente && items?.length > 0" in src
        assert "<QuadroPersona" in src

    def test_07_niente_interpretazione(self):
        """La didascalia dice cos'è (dichiarato, 1-10) e cosa NON fa
        (medie, interpretazioni); e nel quadro non compaiono parole
        che trasformino un vissuto in una diagnosi."""
        src = _senza_commenti(PAGINA.read_text())
        blocco = src[src.find("function QuadroPersona"):src.find("function Registro()")]
        assert "Nessuna media, nessuna interpretazione" in blocco
        basso = blocco.lower()
        for vietato in ("migliorament", "peggiorament", "efficac",
                        "benessere medio", "punteggio di salute", "score"):
            assert vietato not in basso, f"il quadro dice «{vietato}»"

    def test_08_cronologia_ascendente_e_niente_in_corso(self):
        """La lista arriva DISCENDENTE dal server: il quadro la
        rovescia (il tempo va da sinistra a destra) e scarta le
        in_corso."""
        src = _senza_commenti(PAGINA.read_text())
        blocco = src[src.find("function QuadroPersona"):src.find("function Registro()")]
        assert ".reverse()" in blocco
        assert "!== 'in_corso'" in blocco

    def test_09_svg_senza_orologi(self):
        src = _senza_commenti(PAGINA.read_text())
        blocco = src[src.find("function QuadroPersona"):src.find("function Registro()")]
        for vietato in ("canvas", "requestAnimationFrame", "setInterval"):
            assert vietato.lower() not in blocco.lower()
        assert "recharts" not in src.lower(), \
            "il mondo Sound non importa librerie grafiche"
