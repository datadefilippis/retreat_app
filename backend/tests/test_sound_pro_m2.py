"""Sound Professional M2 — i percorsi (26/8/2026).

La lezione strutturale di Unyte con la nostra onestà: un percorso ha
dose, cadenza e progressione; ogni tappa cita un protocollo del
catalogo; la sessione che si dichiara «tappa N» viene verificata dal
server — il registro non può mentire nemmeno per sbaglio.
"""
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

os.environ.setdefault("JWT_SECRET_KEY", "test")
os.environ.setdefault("MONGO_URL", "mongodb://localhost:27017")
os.environ.setdefault("DB_NAME", "test_database")

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))
FRONTEND_SRC = BACKEND_DIR.parent / "frontend" / "src"
FQ = FRONTEND_SRC / "features" / "frequenze"
PRO = FQ / "pro"

from fastapi import HTTPException  # noqa: E402
from routers import sound_sessions  # noqa: E402

_NODE = shutil.which("node") or \
    "/Users/davidedefilippis/.nvm/versions/node/v22.13.1/bin/node"
node_c_e = pytest.mark.skipif(not Path(_NODE).exists(),
                              reason="node non disponibile")

PREFIX = "test_m2_"
ORG = PREFIX + "org"
UTENTE = {"user_id": PREFIX + "user", "organization_id": ORG,
          "role": "org_admin", "email": "m2@example.com"}


def _senza_commenti(testo: str) -> str:
    testo = re.sub(r"/\*.*?\*/", " ", testo, flags=re.S)
    return re.sub(r"^\s*//.*$", " ", testo, flags=re.M)


def _esegui_percorsi(corpo: str, tmp_path):
    files = {"percorsi.js": PRO / "percorsi.js",
             "catalogo.js": PRO / "catalogo.js",
             "esperienze.js": FQ / "content" / "esperienze.js",
             "calm.js": FQ / "content" / "calm.js",
             "ground.js": FQ / "content" / "ground.js",
             "protocolli.js": FQ / "content" / "protocolli.js"}
    for nome, sorgente in files.items():
        testo = sorgente.read_text()
        testo = testo.replace("from '../content/", "from './")
        testo = re.sub(r"from '(\./[a-z]+)'", r"from '\1.js'", testo)
        (tmp_path / nome).write_text(testo)
    script = (f"import {{ PERCORSI }} from {json.dumps(str(tmp_path / 'percorsi.js'))};\n"
              f"import {{ CATALOGO }} from {json.dumps(str(tmp_path / 'catalogo.js'))};\n"
              + corpo)
    r = subprocess.run([_NODE, "--input-type=module", "-e", script],
                       capture_output=True, text=True, timeout=60)
    assert r.returncode == 0, f"node è morto: {r.stderr[:500]}"
    return json.loads(r.stdout.strip().splitlines()[-1])


@pytest.fixture
async def banco(monkeypatch):
    import uuid as _uuid
    try:
        from motor.motor_asyncio import AsyncIOMotorClient
        client = AsyncIOMotorClient(
            os.environ.get("MONGO_URL", "mongodb://localhost:27017"),
            serverSelectionTimeoutMS=2000)
        await client.admin.command("ping")
    except Exception as e:
        pytest.skip(f"MongoDB non raggiungibile: {e}")
    nome_db = f"test_m2_{_uuid.uuid4().hex[:8]}"
    db = client[nome_db]
    import database as db_mod
    import repositories.audit_repository as audit_mod
    for attr, coll in (("sound_sessions_collection", db.sound_sessions),
                       ("sound_protocols_collection", db.sound_protocols),
                       ("organizations_collection", db.organizations),
                       ("customers_collection", db.customers),
                       ("issued_bookings_collection", db.issued_bookings)):
        monkeypatch.setattr(db_mod, attr, coll)
    monkeypatch.setattr(audit_mod, "audit_logs_collection", db.audit_logs)
    await db.organizations.insert_one(
        {"id": ORG, "name": "Org", "sound_professional": True})
    try:
        yield db
    finally:
        try:
            await client.drop_database(nome_db)
        except Exception:
            pass
        client.close()


async def _apri(**campi):
    base = {"protocollo_tipo": "core", "protocollo_id": "ground"}
    base.update(campi)
    return await sound_sessions.apri_sessione(
        sound_sessions.SessioneApri(**base), UTENTE)


# ── 1-3 · i dati: percorsi onesti che citano il catalogo ───────────────────
@node_c_e
class TestIDati:
    def test_01_ogni_tappa_cita_un_protocollo_del_catalogo(self, tmp_path):
        out = _esegui_percorsi("""
const ids = new Set(CATALOGO.map(c => c.id));
console.log(JSON.stringify(PERCORSI.map(p => ({
  id: p.id, titolo: !!p.titolo, sottotitolo: !!p.sottotitolo,
  racconto: !!p.racconto, indicazioni: !!p.indicazioni,
  settimane: p.durata?.settimane, aSettimana: p.durata?.a_settimana,
  revisione: p.revisione, tappe: p.tappe.length,
  orfane: p.tappe.filter(t => !ids.has(t.protocollo)).length,
  senzaNota: p.tappe.filter(t => !t.nota).length,
}))));""", tmp_path)
        assert len(out) == 3
        for pc in out:
            assert pc["orfane"] == 0, f"{pc['id']}: tappe verso protocolli inesistenti"
            assert pc["tappe"] >= 4, f"{pc['id']}: troppo corto per essere un percorso"
            assert pc["settimane"] and pc["aSettimana"], \
                f"{pc['id']}: senza dose e cadenza non è un programma"
            assert pc["senzaNota"] == 0, f"{pc['id']}: tappe mute"
            for campo in ("titolo", "sottotitolo", "racconto",
                          "indicazioni", "revisione"):
                assert pc[campo], f"{pc['id']}: manca {campo}"

    def test_02_dose_dichiarata_uguale_dose_reale(self, tmp_path):
        """settimane × a_settimana = numero di tappe: la cadenza non
        promette sessioni che il percorso non ha."""
        out = _esegui_percorsi("""
console.log(JSON.stringify(PERCORSI.map(p => ({
  id: p.id, attese: p.durata.settimane * p.durata.a_settimana,
  tappe: p.tappe.length }))));""", tmp_path)
        for pc in out:
            assert pc["attese"] == pc["tappe"], \
                f"{pc['id']}: cadenza {pc['attese']} ≠ tappe {pc['tappe']}"

    def test_03_niente_claim_nei_percorsi(self, tmp_path):
        # SENZA i commenti: la testata nega («non cura») e una guardia
        # che legge la prosa della negazione inciampa su se stessa —
        # la lezione pagata ormai quattro volte in questo modulo
        testo = _senza_commenti((PRO / "percorsi.js").read_text()).lower()
        assert not re.search(r"\bcur(a|e|are)\b", testo)
        for veleno in ("guarig", "ripara", "riequilibr", "diagnos",
                       "terapeutic", "insonnia clinica migliora",
                       "biorisonanza", "528", "chakra"):
            assert veleno not in testo, f"i percorsi dicono «{veleno}»"
        # la nota onesta di Dormire vale per tutto il percorso serale
        assert "non è un trattamento" in testo


# ── 4 · lo specchio è gemello ──────────────────────────────────────────────
@node_c_e
class TestLoSpecchio:
    def test_04_parita_percorsi_js_vs_python(self, tmp_path):
        out = _esegui_percorsi("""
console.log(JSON.stringify(PERCORSI.map(p =>
  [p.id, p.titolo, p.tappe.map(t => t.protocollo)])));""", tmp_path)
        js = {v[0]: (v[1], v[2]) for v in out}
        from models.sound_catalog import PERCORSI_CORE
        py = {k: (t, list(tappe)) for k, (t, tappe) in PERCORSI_CORE.items()}
        assert js == py, f"i gemelli divergono:\nJS: {js}\nPY: {py}"


# ── 5-7 · il server verifica la tappa ──────────────────────────────────────
class TestLaTappaOnesta:
    async def test_05_tappa_valida_registrata(self, banco):
        s = await _apri(percorso_id="radicamento", percorso_tappa=1)
        assert s["percorso"] == {"id": "radicamento", "titolo": "Radicamento",
                                 "tappa": 1, "totale": 8}
        # e la lista la porta
        lista = await sound_sessions.lista_sessioni(None, None, UTENTE)
        assert lista["items"][0]["percorso"]["tappa"] == 1

    async def test_06_la_tappa_non_puo_mentire(self, banco):
        # tappa 2 di radicamento è Rilassare, non GROUND
        with pytest.raises(HTTPException) as e:
            await _apri(percorso_id="radicamento", percorso_tappa=2)
        assert e.value.status_code == 400
        assert "altro protocollo" in e.value.detail
        # fuori range
        with pytest.raises(HTTPException) as e:
            await _apri(percorso_id="radicamento", percorso_tappa=99)
        assert "8 tappe" in e.value.detail
        # percorso inventato
        with pytest.raises(HTTPException) as e:
            await _apri(percorso_id="inventato", percorso_tappa=1)
        assert e.value.status_code == 400
        # a metà: solo uno dei due campi
        with pytest.raises(HTTPException) as e:
            await _apri(percorso_id="radicamento")
        assert "insieme" in e.value.detail
        # niente sessioni nate da questi rifiuti
        import database as db_mod
        assert await db_mod.sound_sessions_collection.count_documents(
            {"organization_id": ORG}) == 0

    async def test_07_senza_percorso_tutto_come_prima(self, banco):
        s = await _apri()
        assert s["percorso"] is None


# ── 8-10 · l'interfaccia ───────────────────────────────────────────────────
class TestInterfaccia:
    def test_08_scaffale_scheda_e_progresso(self):
        src = _senza_commenti((PRO / "SoundProPage.jsx").read_text())
        assert 'data-testid="pro-percorsi"' in src
        assert 'data-testid="pc-tappe"' in src
        # il progresso viene dal registro VERO: sessioni completate di
        # quel cliente in quel percorso
        assert "stato: 'completata'" in src
        assert "x.percorso?.id === pc.id" in src
        assert "Prossima tappa" in src
        # e la riga del registro dice la tappa
        assert 'data-testid="reg-percorso"' in src

    def test_09_il_rito_dichiara_la_tappa(self):
        src = _senza_commenti((PRO / "Rito.jsx").read_text())
        assert "percorso_id: percorso.id" in src
        assert "percorso_tappa: percorso.tappa" in src
        assert 'data-testid="rito-tappa"' in src
        assert 'data-testid="rito-nota-tappa"' in src

    def test_10_le_guardie_reggono(self):
        """Percorsi = dati puri; la pagina ancora non tocca l'audio;
        nessun backend oltre specchio e validazione."""
        perc = _senza_commenti((PRO / "percorsi.js").read_text()).lower()
        for vietato in ("import react", "audiocontext", "layer("):
            assert vietato not in perc
        pagina = _senza_commenti((PRO / "SoundProPage.jsx").read_text()).lower()
        for vietato in ("creaascolto", "startpreview", "audiocontext"):
            assert vietato not in pagina


# ── fix 26/8 · il 422 non ammazza più la pagina ────────────────────────────
@node_c_e
class TestErroreSempreUnaFrase:
    """Il bug trovato dal founder al play dei percorsi: il backend
    stantio rispondeva 422 e il `detail` di FastAPI — un ARRAY di
    oggetti — finiva dritto in un <p>: React moriva («Objects are not
    valid as a React child») e al posto del rito compariva «Qualcosa
    è andato storto». Da qui la regola: ogni catch passa dal
    normalizzatore, e dal normalizzatore esce SEMPRE una stringa."""

    def test_11_il_normalizzatore_dice_sempre_una_frase(self, tmp_path):
        import shutil as _sh
        _sh.copy(PRO / "errori.js", tmp_path / "errori.js")
        script = (
            f"import {{ messaggio }} from "
            f"{json.dumps(str(tmp_path / 'errori.js'))};\n"
            """
const casi = [
  { e: { response: { data: { detail: 'Limite raggiunto.' } } }, atteso: 'Limite raggiunto.' },
  // il 422 vero di FastAPI: array di oggetti {loc, msg, type}
  { e: { response: { data: { detail: [
      { loc: ['body', 'percorso_id'], msg: 'Extra inputs are not permitted', type: 'extra_forbidden' },
      { loc: ['body', 'x'], msg: 'Field required', type: 'missing' },
    ] } } }, atteso: 'Extra inputs are not permitted · Field required' },
  { e: { response: { data: { detail: [{ strano: 1 }] } } }, atteso: 'fallback' },
  { e: { response: { data: { detail: { oggetto: 'nudo' } } } }, atteso: 'fallback' },
  { e: undefined, atteso: 'fallback' },
  { e: new Error('rete giu'), atteso: 'fallback' },
];
const esiti = casi.map(c => {
  const out = messaggio(c.e, 'fallback');
  return { ok: out === c.atteso, tipo: typeof out, out };
});
console.log(JSON.stringify(esiti));
""")
        import subprocess as _sp
        r = _sp.run([_NODE, "--input-type=module", "-e", script],
                    capture_output=True, text=True, timeout=30)
        assert r.returncode == 0, r.stderr[:300]
        esiti = json.loads(r.stdout.strip().splitlines()[-1])
        for i, e in enumerate(esiti):
            assert e["tipo"] == "string", f"caso {i}: uscito un {e['tipo']}"
            assert e["ok"], f"caso {i}: «{e['out']}»"

    def test_12_nessun_detail_crudo_nel_jsx(self):
        """La regola strutturale: `e?.response?.data?.detail` non
        compare più in NESSUN file del modulo pro — si passa dal
        normalizzatore, sempre."""
        for f in sorted(PRO.glob("*.jsx")):
            src = _senza_commenti(f.read_text())
            assert "e?.response?.data?.detail" not in src, \
                f"{f.name}: un detail crudo può ancora crashare il render"
        err = _senza_commenti((PRO / "errori.js").read_text())
        assert "import" not in err.split("export")[0], \
            "il normalizzatore deve restare puro"
