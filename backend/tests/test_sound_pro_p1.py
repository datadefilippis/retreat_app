"""Sound Professional P1 — modello + compilatore (26/8/2026).

Il principio sotto guardia:

    il professionista progetta protocolli;
    il compilatore li traduce;
    il motore li suona;
    il motore NON sa nulla del professionista.

Questi test non simulano il compilatore: LO ESEGUONO (Node sul file
vero, `pro/compilatore.js`) e passano il risultato a `clean_score` —
il validatore del server, la fonte della verita'. La proprieta' che
governa tutto: compila(steps) == clean_score(compila(steps)), senza
la minima correzione.
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
COMPILATORE = FQ / "pro" / "compilatore.js"

_NODE = shutil.which("node") or "/Users/davidedefilippis/.nvm/versions/node/v22.13.1/bin/node"
node_c_e = pytest.mark.skipif(not Path(_NODE).exists(),
                              reason="node non disponibile su questa macchina")


def _esegui(steps, funzione="compila"):
    """Esegue il compilatore VERO. Ritorna (score, None) o (None, errore)."""
    script = f"""
import {{ compila, durataTotale }} from {json.dumps(str(COMPILATORE))};
const steps = {json.dumps(steps)};
try {{
  const out = {funzione}(steps);
  console.log(JSON.stringify({{ ok: out }}));
}} catch (e) {{
  console.log(JSON.stringify({{ errore: e.message, indice: e.indice ?? null }}));
}}
"""
    r = subprocess.run([_NODE, "--input-type=module", "-e", script],
                       capture_output=True, text=True, timeout=30)
    assert r.returncode == 0, f"node è morto: {r.stderr[:400]}"
    out = json.loads(r.stdout.strip().splitlines()[-1])
    return out.get("ok"), out.get("errore")


def _pulito(score):
    import sys
    sys.path.insert(0, str(BACKEND_DIR))
    from models.frequency_track import clean_score
    return clean_score(score)


# ── fixture: i tre protocolli d'esempio dell'analisi ────────────────────────
TONO_SINGOLO = [
    {"metodo": "tone", "hz": 220, "durata_sec": 180, "gain": 0.3},
]
SEQUENZA_CON_PAUSA = [
    {"metodo": "tone", "hz": 220, "durata_sec": 180, "pausa_dopo_sec": 30, "gain": 0.3},
    {"metodo": "tone", "hz": 180, "durata_sec": 300, "gain": 0.3},
]
MISTO = [
    {"metodo": "drone", "hz": 110, "durata_sec": 120, "pausa_dopo_sec": 15, "gain": 0.25},
    {"metodo": "bin", "hz": 400, "battito_hz": 10, "battito_fine_hz": 6,
     "durata_sec": 240, "pausa_dopo_sec": 20, "gain": 0.2},
    {"metodo": "iso", "hz": 180, "battito_hz": 8, "durata_sec": 180, "gain": 0.22},
]


@node_c_e
class TestCompilazione:
    def test_1_un_singolo_passo(self):
        score, err = _esegui(TONO_SINGOLO)
        assert err is None
        assert score["duration_sec"] == 180
        (l,) = score["layers"]
        assert l["method"] == "tone" and l["carrier"] == 220
        assert (l["start"], l["end"]) == (0, 180)
        assert l["curve"] == "lin"                    # il tono e' fisso
        # i campi che il metodo non usa hanno il default del contratto
        assert l["f0"] == 10 and l["f1"] == 10

    def test_2_due_passi_consecutivi(self):
        score, err = _esegui([
            {"metodo": "tone", "hz": 220, "durata_sec": 60, "gain": 0.3},
            {"metodo": "tone", "hz": 330, "durata_sec": 60, "gain": 0.3},
        ])
        assert err is None
        a, b = score["layers"]
        assert (a["start"], a["end"]) == (0, 60)
        assert (b["start"], b["end"]) == (60, 120)    # attaccati, senza buchi

    def test_3_la_pausa_e_un_buco(self):
        """L'esempio del founder, alla lettera: 220×180 + pausa 30 +
        180×300 → finestre 0-180 e 210-510, durata 510."""
        score, err = _esegui(SEQUENZA_CON_PAUSA)
        assert err is None
        a, b = score["layers"]
        assert (a["start"], a["end"]) == (0, 180)
        assert (b["start"], b["end"]) == (210, 510)
        assert score["duration_sec"] == 510

    def test_3b_nessuna_sovrapposizione_mai(self):
        score, _ = _esegui(MISTO)
        finestre = [(l["start"], l["end"]) for l in score["layers"]]
        for (s0, e0), (s1, e1) in zip(finestre, finestre[1:]):
            assert e0 <= s1, f"sovrapposizione: {e0} > {s1}"

    def test_3c_la_pausa_finale_si_ignora(self):
        con = [{"metodo": "tone", "hz": 220, "durata_sec": 90,
                "pausa_dopo_sec": 300, "gain": 0.3}]
        score, _ = _esegui(con)
        assert score["duration_sec"] == 90, "coda di silenzio inutile"

    def test_4_transizione_battito(self):
        score, _ = _esegui(MISTO)
        bin_ = score["layers"][1]
        assert bin_["f0"] == 10 and bin_["f1"] == 6
        assert bin_["curve"] == "exp", \
            "la transizione e' sempre esponenziale (decisione del compilatore)"
        iso = score["layers"][2]
        assert iso["f0"] == iso["f1"] == 8 and iso["curve"] == "lin"

    def test_5_il_gain_passa_intatto(self):
        score, _ = _esegui(MISTO)
        assert [l["gain"] for l in score["layers"]] == [0.25, 0.2, 0.22]

    def test_6_durata_totale(self):
        score, _ = _esegui(MISTO)
        assert score["duration_sec"] == 120 + 15 + 240 + 20 + 180  # = 575

    def test_7_e_12_deterministico_byte_per_byte(self):
        uno = json.dumps(_esegui(MISTO)[0], sort_keys=True)
        due = json.dumps(_esegui(MISTO)[0], sort_keys=True)
        assert uno == due


@node_c_e
class TestIlContrattoNonCorregge:
    """LA proprieta': clean_score accetta lo score compilato SENZA
    toccare un solo valore. Se questa salta, il compilatore mente."""

    @pytest.mark.parametrize("nome,steps", [
        ("tono singolo", TONO_SINGOLO),
        ("sequenza con pausa", SEQUENZA_CON_PAUSA),
        ("misto", MISTO),
        ("24 passi (limite)", [
            {"metodo": "tone", "hz": 100 + i, "durata_sec": 60, "gain": 0.2}
            for i in range(24)
        ]),
        ("estremi del contratto", [
            {"metodo": "tone", "hz": 20, "durata_sec": 30, "gain": 0.05},
            {"metodo": "bin", "hz": 2000, "battito_hz": 0.05,
             "battito_fine_hz": 60, "durata_sec": 30, "gain": 1.0},
        ]),
        ("decimali", [
            {"metodo": "tone", "hz": 432.5, "durata_sec": 90.5,
             "pausa_dopo_sec": 12.25, "gain": 0.33},
            {"metodo": "iso", "hz": 181.25, "battito_hz": 7.83,
             "durata_sec": 60.25, "gain": 0.4},
        ]),
    ])
    def test_identita_con_clean_score(self, nome, steps):
        score, err = _esegui(steps)
        assert err is None, f"{nome}: {err}"
        ripulito = _pulito(score)
        assert ripulito is not None, f"{nome}: rifiutato dal contratto"
        assert ripulito == score, (
            f"{nome}: il contratto ha corretto qualcosa.\n"
            f"compilato: {json.dumps(score, sort_keys=True)[:400]}\n"
            f"ripulito:  {json.dumps(ripulito, sort_keys=True)[:400]}")


@node_c_e
class TestRifiuti:
    """MAI uno score «quasi giusto»: input invalido = errore parlante."""

    @pytest.mark.parametrize("steps,pezzo", [
        ([], "almeno un passo"),
        ([{"metodo": "tone", "hz": 220, "durata_sec": 60, "gain": 0.3}] * 25, "massimo è 24"),
        ([{"metodo": "breath", "hz": 220, "durata_sec": 60, "gain": 0.3}], "non previsto"),
        ([{"metodo": "tone", "hz": 10, "durata_sec": 60, "gain": 0.3}], "fuori da 20"),
        ([{"metodo": "tone", "hz": 5000, "durata_sec": 60, "gain": 0.3}], "fuori da 20"),
        ([{"metodo": "tone", "hz": 220, "durata_sec": 0.2, "gain": 0.3}], "minimo è 1"),
        ([{"metodo": "tone", "hz": 220, "durata_sec": 60, "gain": 0}], "volume"),
        ([{"metodo": "tone", "hz": 220, "durata_sec": 60, "gain": 1.5}], "volume"),
        ([{"metodo": "bin", "hz": 400, "durata_sec": 60, "gain": 0.3}], "battito"),
        ([{"metodo": "bin", "hz": 400, "battito_hz": 90, "durata_sec": 60, "gain": 0.3}], "fuori da 0.05"),
        ([{"metodo": "tone", "hz": 220, "battito_hz": 7, "durata_sec": 60, "gain": 0.3}], "non ha un battito"),
        ([{"metodo": "tone", "hz": 220, "durata_sec": 60,
           "pausa_dopo_sec": -5, "gain": 0.3}], "pausa"),
        ([{"metodo": "tone", "hz": 220, "durata_sec": 30, "gain": 0.3}], "minimo è 60"),
        ([{"metodo": "tone", "hz": 220, "durata_sec": 1900, "gain": 0.3}], "massimo è 1800"),
    ])
    def test_rifiutato_con_messaggio(self, steps, pezzo):
        score, err = _esegui(steps)
        assert score is None and err, f"accettato: {steps[:1]}"
        assert pezzo in err, f"messaggio muto: «{err}»"


class TestParitaDeiGemelli:
    """Le costanti JS del compilatore devono essere QUELLE del
    contratto Python — il pattern di casa delle tassonomie doppie."""

    def test_costanti_identiche(self):
        import sys
        sys.path.insert(0, str(BACKEND_DIR))
        from models import frequency_track as ft
        js = COMPILATORE.read_text()
        attese = {
            "PASSI_MAX": ft.LAYERS_MAX,
            "DURATA_MIN": ft.DURATION_MIN,
            "DURATA_MAX": ft.DURATION_MAX,
            "PORTANTE_MIN": ft.CARRIER_MIN,
            "PORTANTE_MAX": ft.CARRIER_MAX,
            "BATTITO_MIN": ft.BEAT_MIN,
            "BATTITO_MAX": ft.BEAT_MAX,
        }
        for nome, valore in attese.items():
            m = re.search(rf"export const {nome} = ([\d.]+);", js)
            assert m, f"manca {nome} nel compilatore"
            assert float(m.group(1)) == float(valore), \
                f"{nome}: JS dice {m.group(1)}, il contratto dice {valore}"

    def test_metodi_del_sequencer_sono_un_sottoinsieme_del_contratto(self):
        import sys
        sys.path.insert(0, str(BACKEND_DIR))
        from models.frequency_track import METHODS
        from models.sound_protocol import STEP_METHODS
        assert set(STEP_METHODS) <= set(METHODS)
        js = COMPILATORE.read_text()
        m = re.search(r"METODI_PASSO = Object\.freeze\(\[([^\]]+)\]\)", js)
        js_metodi = set(re.findall(r"'(\w+)'", m.group(1)))
        assert js_metodi == set(STEP_METHODS), \
            f"i gemelli divergono: JS {js_metodi}, Python {set(STEP_METHODS)}"


class TestModelloBackend:
    def test_clean_steps_accetta_i_validi_e_rifiuta_il_resto(self):
        import sys
        sys.path.insert(0, str(BACKEND_DIR))
        from models.sound_protocol import clean_steps
        assert clean_steps(MISTO) is not None
        assert clean_steps(SEQUENZA_CON_PAUSA) is not None
        # rifiuti netti, mai correzioni silenziose (un protocollo
        # «aggiustato» non e' piu' quello che l'operatore ha progettato)
        assert clean_steps([]) is None
        assert clean_steps([{"metodo": "tone", "hz": 5000,
                             "durata_sec": 60, "gain": 0.3}]) is None
        assert clean_steps([{"metodo": "tone", "hz": 220, "durata_sec": 60,
                             "gain": 0.3, "battito_hz": 7}]) is None
        assert clean_steps([{"metodo": "tone", "hz": 220,
                             "durata_sec": 30, "gain": 0.3}]) is None  # < 60s

    def test_il_modello_esiste_e_non_parla_di_salute(self):
        import sys
        sys.path.insert(0, str(BACKEND_DIR))
        from models import sound_protocol
        src = (BACKEND_DIR / "models" / "sound_protocol.py").read_text().lower()
        for bugia in ("patolog", "diagnos", "terap", "malatt", "cura",
                      "biofeedback", "biorisonanza", "sintom"):
            assert bugia not in src, f"il modello parla di «{bugia}»"
        assert sound_protocol.SoundProtocol is not None


@node_c_e
class TestCalmEGround:
    """§8 del brief: rappresentabilita'. La risposta e' NO per
    entrambe, e il motivo giusto non sono le frequenze: e' il
    PARALLELISMO. Le esperienze sono composizioni con livelli
    sovrapposti; il sequencer e' sequenziale per costruzione. In piu'
    usano metodi fuori DSL (breath, noise, bil). Non si estende il DSL
    per farcele entrare: sono prodotti diversi."""

    def _sovrapposti(self, costruisci_js, tmp_path):
        """Node non risolve gli import SENZA estensione (lezione del
        banco di GROUND): si copiano i protocolli in tmp aggiungendo
        `.js` agli import, e si esegue quella copia."""
        nome = costruisci_js.replace("costruisci", "").lower() + ".js"
        for f in ("protocolli.js", nome):
            testo = (FQ / "content" / f).read_text()
            testo = testo.replace("from './protocolli'", "from './protocolli.js'")
            (tmp_path / f).write_text(testo)
        script = f"""
import {{ {costruisci_js} as c }} from {json.dumps(str(tmp_path / nome))};
const s = c();
const fin = s.layers.map(l => [l.start, l.end]).sort((a, b) => a[0] - b[0]);
let overlap = false;
for (let i = 1; i < fin.length; i++) if (fin[i][0] < fin[i-1][1]) overlap = true;
console.log(JSON.stringify({{ overlap, metodi: s.layers.map(l => l.method) }}));
"""
        r = subprocess.run([_NODE, "--input-type=module", "-e", script],
                           capture_output=True, text=True, timeout=30)
        assert r.returncode == 0, r.stderr[:300]
        return json.loads(r.stdout.strip().splitlines()[-1])

    @pytest.mark.parametrize("costruisci,fuori_dsl", [
        ("costruisciCalm", {"breath"}),
        ("costruisciGround", {"noise", "bil"}),
    ])
    def test_non_rappresentabile_e_il_motivo_e_documentato(self, costruisci, fuori_dsl, tmp_path):
        import sys
        sys.path.insert(0, str(BACKEND_DIR))
        from models.sound_protocol import STEP_METHODS
        info = self._sovrapposti(costruisci, tmp_path)
        assert info["overlap"] is True, \
            "i livelli non si sovrappongono piu': ricontrollare la risposta del §8"
        assert fuori_dsl - set(STEP_METHODS) == fuori_dsl, \
            "un metodo 'da esperienza' e' entrato nel sequencer"
