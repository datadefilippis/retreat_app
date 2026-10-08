"""Lotto CS (8/10/2026 sera) — IL MOTORE DEI CONSIGLI della casa.

docs/PIANO_CASA_CONSIGLI_2026-10-08.md. Un motore a segnali, deterministico e
spiegabile (casa/consigli.js): un bacino, una carta una volta, sezioni col
perche', soglie che crescono col catalogo. Gli scenari girano DAVVERO sul
modulo JS (trasformato con Babel ed eseguito con node), cosi' i pesi e le
soglie sono pinzati dal comportamento, non dal testo.
"""
import json
import os
import subprocess
from pathlib import Path

import pytest
import requests

BACKEND = Path(__file__).resolve().parents[1]
FRONTEND = BACKEND.parent / "frontend"
SRC = FRONTEND / "src" / "features" / "frequenze"
CASA = SRC / "casa"
BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "http://localhost:8000")


def _esegui(scenario_js: str) -> dict:
    """Trasforma consigli.js in CommonJS e valuta lo scenario in node."""
    runner = f"""
const babel = require('@babel/core');
const fs = require('fs');
const code = babel.transformSync(fs.readFileSync({json.dumps(str(CASA / 'consigli.js'))}, 'utf8'),
  {{ presets: [[require.resolve('@babel/preset-env'), {{ targets: {{ node: 'current' }} }}]], babelrc: false, configFile: false }}).code;
const m = {{ exports: {{}} }};
new Function('module', 'exports', 'require', code)(m, m.exports, require);
const C = m.exports;
const out = (function () {{ {scenario_js} }})();
process.stdout.write(JSON.stringify(out));
"""
    r = subprocess.run(["node", "-e", runner], cwd=str(FRONTEND), capture_output=True, text=True, timeout=60)
    assert r.returncode == 0, r.stderr[-800:]
    return json.loads(r.stdout)


def _tracce(n, **extra):
    base = []
    for i in range(n):
        base.append({"slug": f"m{i}", "title": f"Med {i}", "duration_sec": 600 + i * 120,
                     "categoria": "meditazioni-guidate" if i % 2 == 0 else "respiro-guidato",
                     "intent": ["rilassare", "dormire", "meditare"][i % 3], "momento": ["sera", "notte", "mattina"][i % 3],
                     "plays_total": i, "published_at": "2026-09-01T00:00:00Z", **extra})
    return base


class TestMotore:
    def test_pesi_e_soglie_sono_una_tabella(self):
        src = (CASA / "consigli.js").read_text()
        assert "export const PESI = Object.freeze({" in src and "export const SOGLIE = Object.freeze({" in src
        assert "catalogoPiccolo: 5" in src and "minimoRiga: 3" in src

    def test_un_titolo_solo_una_carta_sola(self):
        """Il caso del founder: con una meditazione la casa non la ripete."""
        out = _esegui("""
          const tutte = [{slug:'a', title:'A', duration_sec:60, categoria:'meditazioni-guidate', intent:'rilassare', plays_total:7, published_at:'2026-10-01T00:00:00Z'}];
          const casa = C.componiCasa({ tutte, vetrina: tutte[0], persona: null, categorie: [{slug:'meditazioni-guidate', label:'Guidate'}] });
          return { piccolo: casa.piccolo, sezioni: casa.sezioni.length, categorie: casa.categorieRighe.length, altre: casa.altre.length, preferite: casa.preferite.length };
        """)
        assert out == {"piccolo": True, "sezioni": 0, "categorie": 0, "altre": 0, "preferite": 0}

    def test_catalogo_piccolo_solo_vetrina_e_le_altre(self):
        out = _esegui(f"""
          const tutte = {json.dumps(_tracce(4))};
          const casa = C.componiCasa({{ tutte, vetrina: tutte[0], persona: null, categorie: [{{slug:'meditazioni-guidate', label:'G'}}, {{slug:'respiro-guidato', label:'R'}}] }});
          return {{ piccolo: casa.piccolo, sezioni: casa.sezioni.length, categorie: casa.categorieRighe.length, altre: casa.altre.map(t => t.slug) }};
        """)
        assert out["piccolo"] is True and out["sezioni"] == 0 and out["categorie"] == 0
        assert out["altre"] == ["m1", "m2", "m3"]          # la vetrina non si ripete

    def test_catalogo_medio_una_carta_una_volta(self):
        out = _esegui(f"""
          const tutte = {json.dumps(_tracce(12))};
          const persona = C.persona({{ recenti: ['m0','m1'], riprendi: {{slug:'m2', secondo: 90}}, preferite: ['m3','m4'], abitudine: {{fascia:'sera', durata_media_sec: 700, completati: {{}}, ascoltati_oggi: ['m0'], ultimo_ascolto: {{}} }}, perSlug: Object.fromEntries(tutte.map(t => [t.slug, t])) }});
          const casa = C.componiCasa({{ tutte, vetrina: tutte[11], persona, categorie: [{{slug:'meditazioni-guidate', label:'G'}}, {{slug:'respiro-guidato', label:'R'}}], ora: new Date(2026, 9, 8, 20, 0) }});
          const viste = [];
          if (casa.riprendi) viste.push(casa.riprendi.t.slug);
          casa.sezioni.forEach(s => s.items.forEach(t => viste.push(t.slug)));
          casa.preferite.forEach(t => viste.push(t.slug));
          casa.categorieRighe.forEach(s => s.items.forEach(t => viste.push(t.slug)));
          casa.altre.forEach(t => viste.push(t.slug));
          return {{ piccolo: casa.piccolo, riprendi: casa.riprendi && casa.riprendi.t.slug, sezioni: casa.sezioni.map(s => [s.id, s.items.length, s.perche]), viste, vetrina: casa.vetrina.slug, copertura: new Set([...viste, casa.vetrina.slug]).size }};
        """)
        assert out["piccolo"] is False
        assert out["riprendi"] == "m2"
        assert len(out["viste"]) == len(set(out["viste"])), "una carta e' uscita due volte"
        assert out["vetrina"] not in out["viste"], "la vetrina si e' ripetuta in una riga"
        assert out["copertura"] == 12, "qualche meditazione non compare da nessuna parte"
        ids = [s[0] for s in out["sezioni"]]
        assert "momento" in ids and all(s[1] >= 3 for s in out["sezioni"])

    def test_il_perche_segue_l_ora_e_l_abitudine(self):
        out = _esegui(f"""
          const tutte = {json.dumps(_tracce(9))};
          const stats = C.statistiche(tutte);
          const sera = C.punteggio(tutte[0], {{ ora: new Date(2026, 9, 8, 20, 0), persona: null, stats }});   // momento 'sera'
          const notte = C.punteggio(tutte[0], {{ ora: new Date(2026, 9, 8, 2, 0), persona: null, stats }});
          const abit = C.punteggio(tutte[0], {{ ora: new Date(2026, 9, 8, 9, 0), persona: {{ fascia: 'sera' }}, stats }});
          return {{ sera: [sera.parti.momento, sera.perche], notte: notte.parti.momento, abit: [abit.parti.momento, abit.perche] }};
        """)
        assert out["sera"] == [3, "È sera: per lasciare andare"]
        assert out["notte"] == 0
        assert out["abit"][0] == pytest.approx(2.4) and out["abit"][1] == "Di solito ascolti di sera"

    def test_stanchezza_e_popolarita_bayesiana(self):
        out = _esegui("""
          const tutte = [
            {slug:'uno', title:'Uno', duration_sec:600, plays_total: 1, published_at:'2026-01-01T00:00:00Z'},
            {slug:'cento', title:'Cento', duration_sec:600, plays_total: 100, published_at:'2026-01-01T00:00:00Z'},
            {slug:'zero', title:'Zero', duration_sec:600, plays_total: 0, published_at:'2026-01-01T00:00:00Z'},
          ];
          const stats = C.statistiche(tutte);
          const p = (t, persona) => C.punteggio(t, { ora: new Date(2026, 9, 8, 14, 0), persona, stats });
          const uno = p(tutte[0], null).parti.popolarita, cento = p(tutte[1], null).parti.popolarita, zero = p(tutte[2], null).parti.popolarita;
          const stanca = p(tutte[1], { ascoltatiOggi: new Set(['cento']) });
          return { uno, cento, zero, stanca: stanca.parti.stanchezza, totaleStanca: stanca.totale < p(tutte[1], null).totale };
        """)
        assert out["cento"] > out["uno"] > out["zero"]
        assert out["uno"] - out["zero"] < 0.2, "un ascolto solo non deve fare la differenza"
        assert out["stanca"] == -3 and out["totaleStanca"] is True


class TestCasaEFiltri:
    def test_la_casa_usa_il_motore_dietro_il_flag(self):
        assert "export const CASA_CONSIGLI = true;" in (SRC / "stato.js").read_text()
        src = (CASA / "MeditazioniCasa.jsx").read_text()
        assert "import { componiCasa, persona as costruisciPersona, FASCE_DURATA, fasciaDurata } from './consigli';" in src
        assert "return componiCasa({ tutte, vetrina, persona: pers, categorie: categoriePresenti });" in src
        assert ") : casa ? (" in src
        # le sezioni composte, le altre (residue) e la mappa dietro un bottone
        for tid in ('id="altre"', 'data-testid="casa-mappa"', 'data-testid="casa-tutte-mappa"', 'data-testid="casa-filtri-durata"', 'data-testid={`casa-durata-${v}`}'):
            assert tid in src, tid
        assert "{casa.sezioni.map((sz) => (" in src and "sub={sz.perche || undefined}" in src

    def test_i_filtri(self):
        src = (CASA / "MeditazioniCasa.jsx").read_text()
        # categorie solo popolate (MR4), durata un livello sotto e solo se le fasce sono diverse, via la voce nel nuovo
        assert "const categoriePresenti = categorie.filter((c) => tutte.some((t) => t.categoria === c.slug));" in src
        assert "{CASA_CONSIGLI && fasceDurataPresenti.size >= 2 && (" in src
        assert "const cercando = !!(q.trim() || intent || durata || (!CASA_CONSIGLI && voce));" in src
        # la voce esiste SOLO nel ramo del vestito vecchio: dopo il marcatore, prima della durata nuova
        a = src.index("{!CASA_CONSIGLI && (")
        b = src.index("{CASA_CONSIGLI && fasceDurataPresenti.size >= 2 && (")
        assert a < src.index("'Con la voce'") < b and a < src.index("'Solo suono'") < b   # (il commento in testa li cita: non conta)
        assert src.count("'Con la voce'") == 1 and src.count("'Solo suono'") == 1
        # le righe di prima restano nel file (pin di SN1) ma dietro il ramo vecchio
        assert 'id="con-la-voce"' in src and 'id="solo-suono"' in src


class TestAbitudine:
    def test_il_profilo_porta_l_abitudine(self):
        src = (BACKEND / "routers" / "platform_accounts.py").read_text()
        assert 'out["sound_abitudine"] = await abitudine(account["id"])' in src
        serv = (BACKEND / "services" / "ascolti_regia.py").read_text()
        for k in ('"fascia"', '"durata_media_sec"', '"completati"', '"ascoltati_oggi"', '"ultimo_ascolto"'):
            assert k in serv, k
        assert 'ZoneInfo("Europe/Rome")' in serv                      # l'ora e' quella che la persona vive
        assert 'name="cs2_ascolti_persona"' in (BACKEND / "database.py").read_text()

    def test_abitudine_dal_vivo(self):
        """Dal server locale: il viaggiatore di prova ha tre ascolti serali finiti."""
        tok = Path("/private/tmp/claude-501/-Users-davidedefilippis-Desktop-BI-PMI/8e77c3c7-13d9-45f8-8159-d2aae3dd7044/scratchpad/platform-token.txt")
        if not tok.exists():
            pytest.skip("token locale assente")
        try:
            r = requests.get(f"{BASE_URL}/api/platform/me", headers={"Authorization": f"Bearer {tok.read_text().strip()}"}, timeout=5)
        except requests.RequestException:
            pytest.skip("server locale assente")
        if r.status_code != 200:
            pytest.skip("token scaduto")
        ab = r.json().get("sound_abitudine")
        assert ab is not None and set(ab) >= {"fascia", "durata_media_sec", "completati", "ascoltati_oggi", "ultimo_ascolto"}
