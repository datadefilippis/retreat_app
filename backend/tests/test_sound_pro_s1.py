"""Sound Professional S1 — il catalogo e la potatura (26/8/2026).

La decisione di prodotto sotto guardia (audit 26/8, piano in
docs/SOUND_PROFESSIONAL_PIANO_2026-08.md):

    l'operatore SCEGLIE, non compone.

Il catalogo e' contenuto editoriale in git (pro/catalogo.js) che
AVVOLGE le ricette esistenti senza copiarle; ogni scheda dichiara
origine, evidenza e limiti; la home di /sound/pro e' il catalogo, non
l'editor. Questi test eseguono il catalogo VERO in Node e passano ogni
score prodotto al validatore VERO del server (clean_score).
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
CATALOGO = FQ / "pro" / "catalogo.js"
PAGINA = FQ / "pro" / "SoundProPage.jsx"

_NODE = shutil.which("node") or \
    "/Users/davidedefilippis/.nvm/versions/node/v22.13.1/bin/node"
node_c_e = pytest.mark.skipif(not Path(_NODE).exists(),
                              reason="node non disponibile")


def _senza_commenti(testo: str) -> str:
    testo = re.sub(r"/\*.*?\*/", " ", testo, flags=re.S)
    return re.sub(r"^\s*//.*$", " ", testo, flags=re.M)


def _esegui_catalogo(corpo: str, tmp_path):
    """Il catalogo vero in Node: copie in tmp con gli import estesi
    (.js e appiattiti) — la lezione dei banchi precedenti."""
    files = {
        "catalogo.js": FQ / "pro" / "catalogo.js",
        "esperienze.js": FQ / "content" / "esperienze.js",
        "calm.js": FQ / "content" / "calm.js",
        "ground.js": FQ / "content" / "ground.js",
        "respiro.js": FQ / "content" / "respiro.js",
        "protocolli.js": FQ / "content" / "protocolli.js",
    }
    for nome, sorgente in files.items():
        testo = sorgente.read_text()
        testo = testo.replace("from '../content/", "from './")
        testo = re.sub(r"from '(\./[a-z]+)'", r"from '\1.js'", testo)
        (tmp_path / nome).write_text(testo)
    script = (f"import {{ CATALOGO, ORIGINI, protocolloCore }} "
              f"from {json.dumps(str(tmp_path / 'catalogo.js'))};\n" + corpo)
    r = subprocess.run([_NODE, "--input-type=module", "-e", script],
                       capture_output=True, text=True, timeout=60)
    assert r.returncode == 0, f"node è morto: {r.stderr[:500]}"
    return json.loads(r.stdout.strip().splitlines()[-1])


def _clean_score(score):
    import sys
    sys.path.insert(0, str(BACKEND_DIR))
    from models.frequency_track import clean_score
    return clean_score(score)


# ── 1-3 · il catalogo e' completo e ogni score e' valido ───────────────────
@node_c_e
class TestCatalogo:
    def test_01_otto_voci_con_tutti_i_metadati(self, tmp_path):
        out = _esegui_catalogo("""
console.log(JSON.stringify(CATALOGO.map(p => ({
  id: p.id, titolo: !!p.titolo, sottotitolo: !!p.sottotitolo,
  racconto: !!p.racconto, indicazioni: !!p.indicazioni,
  durata: p.durata_sec, livello: p.livello, cuffie: p.cuffie,
  origine: p.origine, grado: p.evidenza?.grado ?? null,
  nota: !!p.evidenza?.nota, revisione: p.evidenza?.revisione,
  stato: p.stato, versione: p.versione,
  costruisce: typeof p.costruisci === 'function',
}))));""", tmp_path)
        assert len(out) == 9
        assert [p["id"] for p in out] == [
            "calm", "respiro", "ground", "rilassare", "dormire",
            "meditare", "elaborare", "concentrare", "energizzare"]
        for p in out:
            for campo in ("titolo", "sottotitolo", "racconto",
                          "indicazioni", "nota", "costruisce"):
                assert p[campo], f"{p['id']}: manca {campo}"
            assert p["cuffie"] in ("necessarie", "consigliate"), p["id"]
            assert p["origine"] in ("benessere", "letteratura"), p["id"]
            assert p["revisione"], f"{p['id']}: scheda senza data di revisione"
            assert p["stato"] == "attivo" and p["versione"] == 1
            assert p["durata"] >= 300, f"{p['id']}: durata sospetta"

    def test_02_ogni_score_e_valido_per_il_contratto(self, tmp_path):
        """La prova che conta: ogni voce del catalogo produce uno score
        che il validatore DEL SERVER accetta, con la durata dichiarata
        dalla scheda. Un catalogo che promette ciò che il contratto
        rifiuta sarebbe una vetrina rotta."""
        out = _esegui_catalogo("""
console.log(JSON.stringify(CATALOGO.map(p => ({
  id: p.id, durata: p.durata_sec, score: p.costruisci(),
}))));""", tmp_path)
        for voce in out:
            pulito = _clean_score(voce["score"])
            assert pulito is not None, f"{voce['id']}: score RIFIUTATO dal contratto"
            assert pulito["duration_sec"] == voce["durata"], \
                f"{voce['id']}: la scheda dice {voce['durata']}s, " \
                f"lo score {pulito['duration_sec']}s"
            assert pulito["layers"], f"{voce['id']}: score senza livelli"

    def test_03_cuffie_oneste_dove_il_metodo_lo_impone(self, tmp_path):
        """bin e bil esistono solo in cuffia. Se la ricetta li usa, la
        scheda deve o dirle NECESSARIE, o dirle consigliate SPIEGANDO
        cosa si perde senza (e' il caso di CALM e GROUND: il binaurale
        e' un accento, non l'essenza — il registro del founder dice
        «percepisci ANCHE un battito»). Cio' che non e' ammesso e'
        tacere. Derivato dagli score veri, non da un elenco a mano."""
        out = _esegui_catalogo("""
console.log(JSON.stringify(CATALOGO.map(p => ({
  id: p.id, cuffie: p.cuffie, testo: !!p.cuffie_testo,
  metodi: [...new Set(p.costruisci().layers.map(l => l.method))],
}))));""", tmp_path)
        for voce in out:
            if {"bin", "bil"} & set(voce["metodi"]):
                assert voce["cuffie"] == "necessarie" or voce["testo"], \
                    f"{voce['id']} usa {voce['metodi']}, dice " \
                    f"«{voce['cuffie']}» e NON spiega cosa si perde"


# ── 4-6 · niente copie, niente claim ───────────────────────────────────────
class TestOnesta:
    def test_04_il_catalogo_avvolge_e_non_copia(self):
        """Se qui dentro comparisse una layer(...) o una lista di
        layers, sarebbe una copia che diverge dalle ricette vere."""
        src = _senza_commenti(CATALOGO.read_text())
        assert "from '../content/esperienze'" in src
        assert "from '../content/protocolli'" in src
        assert "layer(" not in src, "una ricetta copiata nel catalogo"
        assert "carrier" not in src and "f0" not in src, \
            "matematica sulla scheda: i due strati si sono mescolati"

    def test_05_le_parole_proibite_non_entrano(self):
        """Sul catalogo la guardia distingue: le parole del VELENO
        (promesse) non compaiono mai; le parole CLINICHE possono
        comparire solo dentro una negazione — e' il patto di onesta',
        le note dicono cosa i protocolli NON sono."""
        testo = CATALOGO.read_text().lower()
        # «cura» come CLAIM (la cura, curare) — non «curato» (curatela
        # editoriale): confine di parola, la lezione delle guardie che
        # inciampano sulla propria prosa
        assert not re.search(r"\bcur(a|e|are)\b", testo), \
            "il catalogo promette una cura"
        for veleno in ("guarig", "ripara", "riequilibr", "diagnos",
                       "528", "chakra", "biorisonanza", "biofeedback",
                       "paziente", "terapeutic"):
            assert veleno not in testo, f"il catalogo dice «{veleno}»"
        # le note che toccano il clinico devono negare, non promettere
        note = re.findall(r"ev:\s*\"([^\"]+)\"",
                          (FQ / "content" / "protocolli.js").read_text())
        assert len(note) == 6
        for nota in note:
            if re.search(r"trattament|clinic|EMDR|terap", nota):
                assert re.search(r"NON |non lo sostituisce|non è", nota), \
                    f"nota clinica senza negazione: «{nota[:80]}»"

    def test_06_il_catalogo_avvolge_ricette_che_vivono_altrove(self):
        """L'invariante durevole (la lista-fotografia e' caduta con C2,
        che AGGIUNGE ricette per mestiere): ogni voce del catalogo cita
        una ricetta che vive in content/ — il catalogo non ne ospita
        nessuna, e il Lab resta fuori da tutto questo."""
        import subprocess as sp
        src = _senza_commenti(CATALOGO.read_text())
        # le sole fabbriche di score sono i due avvolgitori
        assert src.count("costruisci:") == 2, \
            "una voce si fabbrica lo score da sola invece di avvolgere"
        assert "daEsperienza" in src and "daIntento" in src
        r = sp.run(["git", "diff", "--name-only", "HEAD", "--",
                    "frontend/src/features/frequenze/lab"],
                   cwd=BACKEND_DIR.parent, capture_output=True, text=True)
        if r.returncode != 0:
            pytest.skip("git non disponibile")
        assert not r.stdout.strip(), f"il Lab e' stato toccato: {r.stdout}"


# ── 7-9 · la potatura: la home e' il catalogo, e non suona niente ─────────
class TestPotatura:
    def test_07_la_home_mostra_catalogo_e_poi_i_tuoi(self):
        src = _senza_commenti(PAGINA.read_text())
        cat = src.find('data-testid="pro-catalogo"')
        tuoi = src.find('data-testid="pro-scaffale-tuoi"')
        assert cat != -1 and tuoi != -1
        # nel render della home il catalogo precede i protocolli propri
        home = src.find("<Catalogo ")
        lista = src.find("<Lista chiave=")
        assert home != -1 and lista != -1 and home < lista

    def test_08_l_editor_resta_raggiungibile_ma_non_e_la_casa(self):
        src = _senza_commenti(PAGINA.read_text())
        assert "<Editor id={id}" in src, "l'editor e' sparito: era una porta, non una demolizione"
        # M-URL: l'editor vive su /sound/pro/protocollo/:id (e i vecchi
        # /sound/pro/:id valgono ancora, risolti dalla pagina)
        assert "'protocollo'" in src and "seg[0] === 'protocollo'" in src

    def test_09_ancora_nessun_suono_in_questa_pagina(self):
        """S1 non suona: l'ascolto arriva col rito (S3) e passera' dal
        player condiviso. Qui la guardia si allarga anche a quello."""
        src = _senza_commenti(PAGINA.read_text()).lower()
        for vietato in ("creaascolto", "startpreview", "audiocontext",
                        "creaponte", "esperienze/ascolto"):
            assert vietato not in src, f"la pagina importa «{vietato}»"
        cat = _senza_commenti(CATALOGO.read_text()).lower()
        for vietato in ("audiocontext", "startpreview", "import react"):
            assert vietato not in cat, f"il catalogo non e' piu' dati puri: «{vietato}»"

    def test_10_il_piano_e_scritto(self):
        doc = (BACKEND_DIR.parent / "docs"
               / "SOUND_PROFESSIONAL_PIANO_2026-08.md")
        assert doc.exists(), "il piano non e' committato"
        testo = doc.read_text()
        for pezzo in ("sceglie, non compone", "S9", "general wellness",
                      "Polar H10", "setLayerBeat"):
            assert pezzo in testo, f"il piano ha perso: {pezzo}"
