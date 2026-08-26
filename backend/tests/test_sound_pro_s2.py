"""Sound Professional S2 — il registro delle sessioni (26/8/2026).

Cosa dimostrano, in ordine di importanza:

1. LO SNAPSHOT NON PUO' MENTIRE: sessione su protocollo operatore →
   fotografa lo score dal database; sessione su protocollo core →
   riferimento {id, versione} verificato sullo specchio, e lo
   specchio e' GEMELLO del catalogo vero (eseguito in Node).
2. Nessun percorso cross-org, come per i protocolli.
3. Il tempo e' del server: l'ascolto dichiarato viene cappato.
4. La privacy del registro: MAI customer_id, feedback o note negli
   audit log. La sessione riguarda una persona.
5. Il registro non si cancella: nessuna rotta DELETE.
"""
import json
import re
import shutil
import subprocess
import sys
from datetime import timedelta
from pathlib import Path

import pytest

import os
os.environ.setdefault("JWT_SECRET_KEY", "test")
os.environ.setdefault("MONGO_URL", "mongodb://localhost:27017")
os.environ.setdefault("DB_NAME", "test_database")

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))
FRONTEND_SRC = BACKEND_DIR.parent / "frontend" / "src"
FQ = FRONTEND_SRC / "features" / "frequenze"

from fastapi import HTTPException  # noqa: E402
from routers import sound_sessions  # noqa: E402
from routers import sound_pro  # noqa: E402

PREFIX = "test_s2_"
ORG_A, ORG_B = PREFIX + "orgA", PREFIX + "orgB"
UTENTE_A = {"user_id": PREFIX + "userA", "organization_id": ORG_A,
            "role": "org_admin", "email": "a@example.com"}
UTENTE_B = {"user_id": PREFIX + "userB", "organization_id": ORG_B,
            "role": "org_admin", "email": "b@example.com"}

PASSI = [
    {"metodo": "tone", "hz": 220, "durata_sec": 300, "gain": 0.3},
]

_NODE = shutil.which("node") or \
    "/Users/davidedefilippis/.nvm/versions/node/v22.13.1/bin/node"


@pytest.fixture
async def banco(monkeypatch):
    """Database effimero: protocolli, sessioni, clienti, audit."""
    import uuid as _uuid
    try:
        from motor.motor_asyncio import AsyncIOMotorClient
        client = AsyncIOMotorClient(
            os.environ.get("MONGO_URL", "mongodb://localhost:27017"),
            serverSelectionTimeoutMS=2000)
        await client.admin.command("ping")
    except Exception as e:
        pytest.skip(f"MongoDB non raggiungibile: {e}")

    nome_db = f"test_s2_{_uuid.uuid4().hex[:8]}"
    db = client[nome_db]
    import database as db_mod
    import repositories.audit_repository as audit_mod
    for attr, coll in (("sound_protocols_collection", db.sound_protocols),
                       ("sound_sessions_collection", db.sound_sessions),
                       ("organizations_collection", db.organizations),
                       ("customers_collection", db.customers),
                       ("issued_bookings_collection", db.issued_bookings)):
        monkeypatch.setattr(db_mod, attr, coll)
    monkeypatch.setattr(audit_mod, "audit_logs_collection", db.audit_logs)

    await db.organizations.insert_many([
        {"id": ORG_A, "name": "Org A", "sound_professional": True},
        {"id": ORG_B, "name": "Org B", "sound_professional": True},
    ])
    await db.customers.insert_one(
        {"id": PREFIX + "cliente", "organization_id": ORG_A,
         "name": "Maria Prova"})

    class Banco:
        sessioni = db.sound_sessions
        audit = db.audit_logs
        clienti = db.customers

    try:
        yield Banco()
    finally:
        try:
            await client.drop_database(nome_db)
        except Exception:
            pass
        client.close()


async def _protocollo_operatore(utente=UTENTE_A):
    return await sound_pro.create_protocollo(
        sound_pro.ProtocolloCreate(nome="Mio protocollo", steps=PASSI),
        utente)


async def _apri(utente=UTENTE_A, **campi):
    base = {"protocollo_tipo": "core", "protocollo_id": "calm"}
    base.update(campi)
    return await sound_sessions.apri_sessione(
        sound_sessions.SessioneApri(**base), utente)


# ── 1-4 · apertura: il riferimento che non mente ───────────────────────────
class TestApertura:
    async def test_01_core_riferimento_senza_snapshot(self, banco):
        s = await _apri(feedback_pre=4)
        assert s["stato"] == "in_corso"
        assert s["protocollo"] == {"tipo": "core", "id": "calm",
                                   "versione": 1, "titolo": "CALM"}
        assert s["score_snapshot"] is None, \
            "il catalogo e' in git: il riferimento E' lo snapshot"
        assert s["durata_prevista_sec"] == 360
        assert s["feedback_pre"] == 4 and s["feedback_post"] is None
        assert s["organization_id"] == ORG_A
        assert s["operator_user_id"] == UTENTE_A["user_id"]

    async def test_02_operatore_snapshot_intero(self, banco):
        p = await _protocollo_operatore()
        s = await _apri(protocollo_tipo="operatore", protocollo_id=p["id"])
        assert s["protocollo"]["tipo"] == "operatore"
        assert s["protocollo"]["versione"] == 1
        assert s["protocollo"]["titolo"] == "Mio protocollo"
        assert s["score_snapshot"] == p["score"], \
            "lo snapshot deve essere lo score ESATTO del protocollo"
        assert s["durata_prevista_sec"] == p["durata_sec"]
        # e se il protocollo poi CAMBIA, la sessione no
        await sound_pro.update_protocollo(
            p["id"], sound_pro.ProtocolloUpdate(steps=[
                {"metodo": "tone", "hz": 300, "durata_sec": 600,
                 "gain": 0.2}]), UTENTE_A)
        riletta = await sound_sessions.leggi_sessione(s["id"], UTENTE_A)
        assert riletta["score_snapshot"] == p["score"], \
            "la versione eseguita e' cambiata sotto i piedi del registro"

    async def test_03_core_sconosciuto_e_archiviato_rifiutati(self, banco):
        with pytest.raises(HTTPException) as e:
            await _apri(protocollo_id="inventato")
        assert e.value.status_code == 400
        p = await _protocollo_operatore()
        await sound_pro.archive_protocollo(p["id"], UTENTE_A)
        with pytest.raises(HTTPException) as e:
            await _apri(protocollo_tipo="operatore", protocollo_id=p["id"])
        assert e.value.status_code == 400
        assert "archiviato" in e.value.detail

    async def test_04_legami_solo_della_propria_org(self, banco):
        s = await _apri(customer_id=PREFIX + "cliente")
        assert s["customer_id"] == PREFIX + "cliente"
        # cliente inesistente e cliente d'altra org: indistinguibili
        with pytest.raises(HTTPException) as e:
            await _apri(customer_id="fantasma")
        assert e.value.status_code == 400
        with pytest.raises(HTTPException) as e:
            await _apri(utente=UTENTE_B, customer_id=PREFIX + "cliente")
        assert e.value.status_code == 400
        with pytest.raises(HTTPException) as e:
            await _apri(booking_id="appuntamento-fantasma")
        assert e.value.status_code == 400


# ── 5-7 · chiusura: il tempo onesto ────────────────────────────────────────
class TestChiusura:
    async def test_05_chiusura_completata(self, banco):
        s = await _apri()
        dopo = await sound_sessions.chiudi_sessione(
            s["id"], sound_sessions.SessioneChiudi(
                esito="completata", ascolto_sec=1.0, feedback_post=8),
            UTENTE_A)
        assert dopo["stato"] == "completata"
        assert dopo["feedback_post"] == 8
        assert dopo["terminata_il"] is not None
        assert dopo["ascolto_sec"] <= 1.0

    async def test_06_ascolto_dichiarato_viene_cappato(self, banco):
        """Il client dice 99999: il server risponde con l'orologio di
        muro. Una sessione appena aperta non puo' aver ascoltato ore."""
        s = await _apri()
        dopo = await sound_sessions.chiudi_sessione(
            s["id"], sound_sessions.SessioneChiudi(
                esito="completata", ascolto_sec=99999),
            UTENTE_A)
        assert dopo["ascolto_sec"] < 60, \
            f"cap mancato: ascolto_sec={dopo['ascolto_sec']}"

    async def test_06b_il_muro_vale_anche_per_sessioni_vecchie(self, banco):
        """Sessione aperta 'ieri' e chiusa ora: il cap NON e' il muro
        (enorme) ma la durata prevista — nessuna delle due bugie."""
        s = await _apri()   # calm: 360s
        await banco.sessioni.update_one(
            {"id": s["id"]},
            {"$set": {"iniziata_il": (await banco.sessioni.find_one(
                {"id": s["id"]}))["iniziata_il"] - timedelta(hours=20)}})
        dopo = await sound_sessions.chiudi_sessione(
            s["id"], sound_sessions.SessioneChiudi(
                esito="completata", ascolto_sec=99999),
            UTENTE_A)
        assert dopo["ascolto_sec"] <= 360 + 2

    async def test_07_non_si_chiude_due_volte_e_non_si_cancella(self, banco):
        s = await _apri()
        await sound_sessions.chiudi_sessione(
            s["id"], sound_sessions.SessioneChiudi(esito="interrotta"),
            UTENTE_A)
        with pytest.raises(HTTPException) as e:
            await sound_sessions.chiudi_sessione(
                s["id"], sound_sessions.SessioneChiudi(esito="completata"),
                UTENTE_A)
        assert e.value.status_code == 404
        # il registro non si cancella: la rotta non esiste proprio
        src = (BACKEND_DIR / "routers" / "sound_sessions.py").read_text()
        assert "@router.delete" not in src
        # ma il vissuto si puo' completare dopo
        dopo = await sound_sessions.aggiorna_sessione(
            s["id"], sound_sessions.SessioneAggiorna(feedback_post=6),
            UTENTE_A)
        assert dopo["feedback_post"] == 6 and dopo["stato"] == "interrotta"


# ── 8-10 · isolamento e lista ──────────────────────────────────────────────
class TestIsolamento:
    async def test_08_org_b_non_vede_ne_chiude(self, banco):
        s = await _apri()
        with pytest.raises(HTTPException) as e:
            await sound_sessions.leggi_sessione(s["id"], UTENTE_B)
        assert e.value.status_code == 404
        with pytest.raises(HTTPException):
            await sound_sessions.chiudi_sessione(
                s["id"], sound_sessions.SessioneChiudi(esito="completata"),
                UTENTE_B)
        lista = await sound_sessions.lista_sessioni(None, None, UTENTE_B)
        assert lista["items"] == []
        # e il protocollo di A non apre sessioni per B
        p = await _protocollo_operatore(UTENTE_A)
        with pytest.raises(HTTPException) as e:
            await _apri(utente=UTENTE_B, protocollo_tipo="operatore",
                        protocollo_id=p["id"])
        assert e.value.status_code == 404

    async def test_09_lista_filtri_e_leggerezza(self, banco):
        p = await _protocollo_operatore()
        a = await _apri(customer_id=PREFIX + "cliente")
        await _apri(protocollo_tipo="operatore", protocollo_id=p["id"])
        await sound_sessions.chiudi_sessione(
            a["id"], sound_sessions.SessioneChiudi(esito="completata"),
            UTENTE_A)
        tutte = await sound_sessions.lista_sessioni(None, None, UTENTE_A)
        assert len(tutte["items"]) == 2
        riga = tutte["items"][0]
        assert "score_snapshot" not in riga, "la lista porta gli score: pesa"
        assert "note_operative" not in riga, \
            "le note sono private: si aprono sulla singola sessione"
        solo_chiuse = await sound_sessions.lista_sessioni(
            "completata", None, UTENTE_A)
        assert [i["id"] for i in solo_chiuse["items"]] == [a["id"]]
        del_cliente = await sound_sessions.lista_sessioni(
            None, PREFIX + "cliente", UTENTE_A)
        assert [i["id"] for i in del_cliente["items"]] == [a["id"]]

    async def test_10_ogni_query_passa_da_mio(self):
        src = (BACKEND_DIR / "routers" / "sound_sessions.py").read_text()
        query = list(re.finditer(
            r"(sound_sessions_collection|sound_protocols_collection|"
            r"customers_collection|issued_bookings_collection)\s*\.\s*"
            r"(find_one_and_update|find_one|find|count_documents|"
            r"update_one|delete_one|delete_many)\s*\(", src))
        assert len(query) >= 7, f"solo {len(query)} query: il test mente"
        for m in query:
            coda = src[m.end():m.end() + 120]
            assert "_mio(" in coda, f"query fuori da _mio: ...{coda[:80]}"
        assert src.count("Depends(require_sound_professional)") == \
            src.count("@router."), "una rotta senza portiere"


# ── 11-12 · privacy del registro e autorita' ───────────────────────────────
class TestPrivacyEAutorita:
    async def test_11_audit_senza_persona(self, banco):
        s = await _apri(customer_id=PREFIX + "cliente", feedback_pre=3,
                        note_operative="Nota riservata su Maria")
        await sound_sessions.chiudi_sessione(
            s["id"], sound_sessions.SessioneChiudi(
                esito="completata", feedback_post=9,
                note_operative="Altra nota riservata"),
            UTENTE_A)
        righe = await banco.audit.find({"resource_id": s["id"]}).to_list(10)
        assert len(righe) >= 2, "open e close vanno auditati"
        testo = json.dumps([r["details"] for r in righe])
        for proibito in (PREFIX + "cliente", "Maria", "riservata",
                         '"3"', '"9"', "feedback"):
            assert proibito not in testo, \
                f"l'audit porta la persona nel log: {proibito}"

    async def test_12_il_client_non_decide_niente(self, banco):
        for campo, valore in (("organization_id", ORG_B),
                              ("score_snapshot", {"finto": 1}),
                              ("durata_prevista_sec", 999),
                              ("stato", "completata"),
                              ("ascolto_sec", 999),
                              ("operator_user_id", "altro")):
            with pytest.raises(Exception):
                sound_sessions.SessioneApri(
                    protocollo_tipo="core", protocollo_id="calm",
                    **{campo: valore})
        with pytest.raises(Exception):
            sound_sessions.SessioneChiudi(esito="completata",
                                          terminata_il="2020-01-01")
        with pytest.raises(Exception):
            sound_sessions.SessioneApri(protocollo_tipo="core",
                                        protocollo_id="calm",
                                        feedback_pre=11)

    def test_12b_niente_salute_nel_modello(self):
        import io
        import tokenize
        for f in ("models/sound_session.py", "models/sound_catalog.py",
                  "routers/sound_sessions.py"):
            testo = (BACKEND_DIR / f).read_text()
            pezzi = []
            attesa = True
            for tok in tokenize.generate_tokens(io.StringIO(testo).readline):
                if tok.type == tokenize.COMMENT:
                    continue
                if tok.type == tokenize.STRING and attesa:
                    attesa = False
                    continue
                if tok.type == tokenize.NEWLINE:
                    attesa = False
                if tok.type == tokenize.INDENT:
                    attesa = True
                if tok.type in (tokenize.NAME, tokenize.OP, tokenize.NUMBER,
                                tokenize.STRING):
                    pezzi.append(tok.string)
                    if tok.type == tokenize.NAME and tok.string in ("def",
                                                                    "class"):
                        attesa = True
            codice = " ".join(pezzi).lower()
            for parola in ("patolog", "diagnos", "terap", "sintom",
                           "condizione_clinica", "cartella", "misure",
                           "biofeedback", "sensore", "hrv"):
                assert parola not in codice, f"{f} parla di «{parola}»"


# ── 13-14 · lo specchio e lo sweep ─────────────────────────────────────────
@pytest.mark.skipif(not Path(_NODE).exists(), reason="node non disponibile")
class TestSpecchioESweep:
    def test_13_lo_specchio_e_gemello_del_catalogo(self, tmp_path):
        """models/sound_catalog.py deve dire ESATTAMENTE cio' che dice
        pro/catalogo.js: id, titolo, versione, durata. Eseguendo il
        catalogo vero, non leggendone il testo."""
        files = {
            "catalogo.js": FQ / "pro" / "catalogo.js",
            "esperienze.js": FQ / "content" / "esperienze.js",
            "calm.js": FQ / "content" / "calm.js",
            "ground.js": FQ / "content" / "ground.js",
            "respiro.js": FQ / "content" / "respiro.js",
        "respiro.js": FQ / "content" / "respiro.js",
            "protocolli.js": FQ / "content" / "protocolli.js",
        }
        for nome, sorgente in files.items():
            testo = sorgente.read_text()
            testo = testo.replace("from '../content/", "from './")
            testo = re.sub(r"from '(\./[a-z]+)'", r"from '\1.js'", testo)
            (tmp_path / nome).write_text(testo)
        script = (f"import {{ CATALOGO }} from "
                  f"{json.dumps(str(tmp_path / 'catalogo.js'))};\n"
                  "console.log(JSON.stringify(CATALOGO.map(p => "
                  "[p.id, p.titolo, p.versione, p.durata_sec])));")
        r = subprocess.run([_NODE, "--input-type=module", "-e", script],
                           capture_output=True, text=True, timeout=60)
        assert r.returncode == 0, r.stderr[:400]
        js = {tuple(v[:1])[0]: tuple(v[1:])
              for v in json.loads(r.stdout.strip().splitlines()[-1])}
        from models.sound_catalog import CATALOGO_CORE
        assert js == CATALOGO_CORE, (
            f"i gemelli divergono:\nJS:     {js}\nPython: {CATALOGO_CORE}")

    def test_14_il_mondo_sound_pro_muore_con_l_org(self):
        src = (BACKEND_DIR / "services" / "hard_delete_service.py").read_text()
        assert '"sound_protocols"' in src and '"sound_sessions"' in src, \
            "lo sweep non conosce Sound Professional: dati orfani"
