"""Sound Professional P2 — CRUD, isolamento, versioni (26/8/2026).

Cosa dimostrano questi test, in ordine di importanza:

1. NON ESISTE UN PERCORSO CROSS-ORG. Non «gli endpoint filtrano per
   org»: si prova che l'Org B, chiamando le funzioni vere con la
   propria identita', non legge, non modifica e non archivia nulla
   dell'Org A — e che nemmeno puo' DICHIARARSI di un'altra org,
   perche' il campo e' rifiutato dal modello di richiesta.
2. Il server e' l'autorita': score, appartenenza, autore e versione
   non arrivano mai dal client.
3. I due compilatori — Python (autorita') e JavaScript (specchio del
   Builder) — dicono la stessa cosa, provato ESEGUENDOLI entrambi.

I test chiamano le funzioni del router direttamente, con un
`current_user` finto della forma che ritorna get_current_user: e' lo
stile di test_tickets_router.py, e tiene fuori login e rate limit. Il
database e' quello vero di test, con prefisso e pulizia.
"""
import json
import os
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
COMPILATORE_JS = (FRONTEND_SRC / "features" / "frequenze" / "pro"
                  / "compilatore.js")

from fastapi import HTTPException  # noqa: E402
from models.frequency_track import clean_score  # noqa: E402
from routers import sound_pro  # noqa: E402
from services.sound_compiler import ErrorePasso, compila  # noqa: E402

PREFIX = "test_p2_"
ORG_A, ORG_B, ORG_MUTO = PREFIX + "orgA", PREFIX + "orgB", PREFIX + "orgMuto"
UTENTE_A = {"user_id": PREFIX + "userA", "organization_id": ORG_A,
            "role": "org_admin", "email": "a@example.com"}
UTENTE_B = {"user_id": PREFIX + "userB", "organization_id": ORG_B,
            "role": "org_admin", "email": "b@example.com"}
UTENTE_MUTO = {"user_id": PREFIX + "userM", "organization_id": ORG_MUTO,
               "role": "org_admin", "email": "m@example.com"}

PASSI = [
    {"metodo": "drone", "hz": 110, "durata_sec": 120,
     "pausa_dopo_sec": 15, "gain": 0.25},
    {"metodo": "bin", "hz": 400, "battito_hz": 10, "battito_fine_hz": 6,
     "durata_sec": 240, "pausa_dopo_sec": 20, "gain": 0.2},
    {"metodo": "iso", "hz": 180, "battito_hz": 8, "durata_sec": 180,
     "gain": 0.22},
]
PASSI_ALTRI = [
    {"metodo": "tone", "hz": 220, "durata_sec": 300, "gain": 0.3},
]


class Banco:
    """Le collezioni del test: il router legge queste, non la produzione."""

    def __init__(self, db):
        self.protocolli = db.sound_protocols
        self.audit = db.audit_logs

    async def audit_di(self, azione, risorsa_id):
        return await self.audit.find_one({"action": azione,
                                          "resource_id": risorsa_id})

    async def quanti(self, org_id):
        return await self.protocolli.count_documents(
            {"organization_id": org_id})


@pytest.fixture
async def banco(monkeypatch):
    """Database effimero + due organizzazioni col privilegio, una senza.

    Un client per test, legato al loop del test: e' il pattern gia' in
    casa (test_r5_coupon_per_customer.py, test_f1_newsletter_backend.py)
    — motor si lega al loop, e un client condiviso muore al secondo test.
    """
    import uuid as _uuid
    try:
        from motor.motor_asyncio import AsyncIOMotorClient
        client = AsyncIOMotorClient(
            os.environ.get("MONGO_URL", "mongodb://localhost:27017"),
            serverSelectionTimeoutMS=2000)
        await client.admin.command("ping")
    except Exception as e:
        pytest.skip(f"MongoDB non raggiungibile: {e}")

    nome_db = f"test_p2_{_uuid.uuid4().hex[:8]}"
    db = client[nome_db]
    # gli indici veri: la lista deve poter fare la stessa query
    await db.sound_protocols.create_index(
        [("organization_id", 1), ("stato", 1), ("updated_at", -1)])
    await db.sound_protocols.create_index("id", unique=True)

    import database as db_mod
    import repositories.audit_repository as audit_mod
    monkeypatch.setattr(db_mod, "sound_protocols_collection",
                        db.sound_protocols)
    monkeypatch.setattr(db_mod, "organizations_collection", db.organizations)
    monkeypatch.setattr(audit_mod, "audit_logs_collection", db.audit_logs)

    await db.organizations.insert_many([
        {"id": ORG_A, "name": "Org A", "sound_professional": True},
        {"id": ORG_B, "name": "Org B", "sound_professional": True},
        {"id": ORG_MUTO, "name": "Org senza privilegio"},
    ])
    try:
        yield Banco(db)
    finally:
        try:
            await client.drop_database(nome_db)
        except Exception:
            pass
        client.close()


async def _crea(utente, nome="Protocollo", passi=None):
    return await sound_pro.create_protocollo(
        sound_pro.ProtocolloCreate(
            nome=nome, steps=PASSI if passi is None else passi), utente)


# ── 1-6 · il ciclo di vita ─────────────────────────────────────────────────
class TestCicloDiVita:
    async def test_01_create_valido(self, banco):
        p = await _crea(UTENTE_A, "Radicamento")
        assert p["nome"] == "Radicamento"
        assert p["organization_id"] == ORG_A
        assert p["created_by"] == UTENTE_A["user_id"]
        assert p["versione"] == 1 and p["stato"] == "bozza"
        assert len(p["score"]["layers"]) == 3
        # il documento salvato e' valido secondo il modello P1
        from models.sound_protocol import SoundProtocol
        assert SoundProtocol(**p).id == p["id"]

    async def test_02_lista_solo_org_corrente(self, banco):
        await _crea(UTENTE_A, "Mio")
        await _crea(UTENTE_B, "Suo")
        lista = await sound_pro.list_protocolli(None, UTENTE_A)
        assert [i["nome"] for i in lista["items"]] == ["Mio"]
        # la lista e' leggera: niente score, i passi sono un numero
        assert "score" not in lista["items"][0]
        assert lista["items"][0]["passi"] == 3

    async def test_03_get_del_proprio(self, banco):
        p = await _crea(UTENTE_A)
        letto = await sound_pro.get_protocollo(p["id"], UTENTE_A)
        assert letto["id"] == p["id"] and letto["score"] == p["score"]

    async def test_04_update_senza_versione_nuova(self, banco):
        p = await _crea(UTENTE_A)
        dopo = await sound_pro.update_protocollo(
            p["id"], sound_pro.ProtocolloUpdate(nome="Altro nome"), UTENTE_A)
        assert dopo["nome"] == "Altro nome"
        assert dopo["versione"] == 1, "rinominare non e' una versione nuova"
        assert dopo["score"] == p["score"]

    async def test_05_i_passi_nuovi_fanno_una_versione(self, banco):
        p = await _crea(UTENTE_A)
        dopo = await sound_pro.update_protocollo(
            p["id"], sound_pro.ProtocolloUpdate(steps=PASSI_ALTRI), UTENTE_A)
        assert dopo["versione"] == 2
        assert dopo["durata_sec"] == 300 and len(dopo["score"]["layers"]) == 1
        # la versione precedente resta recuperabile, non sovrascritta
        (vecchia,) = dopo["versioni_precedenti"]
        assert vecchia["versione"] == 1 and vecchia["score"] == p["score"]
        assert vecchia["durata_sec"] == p["durata_sec"]
        # rimandare gli STESSI passi non gonfia le versioni (e non e'
        # un errore: il Builder rimanda tutto il modulo a ogni salva)
        ancora = await sound_pro.update_protocollo(
            p["id"], sound_pro.ProtocolloUpdate(steps=PASSI_ALTRI), UTENTE_A)
        assert ancora["versione"] == 2
        assert len(ancora["versioni_precedenti"]) == 1
        # una PATCH davvero vuota, invece, resta un errore
        with pytest.raises(HTTPException) as e:
            await sound_pro.update_protocollo(
                p["id"], sound_pro.ProtocolloUpdate(), UTENTE_A)
        assert e.value.status_code == 400

    async def test_06_archivia_e_sparisce_dalla_lista(self, banco):
        p = await _crea(UTENTE_A)
        await sound_pro.archive_protocollo(p["id"], UTENTE_A)
        attivi = await sound_pro.list_protocolli(None, UTENTE_A)
        assert attivi["items"] == []
        archiviati = await sound_pro.list_protocolli("archiviato", UTENTE_A)
        assert [i["id"] for i in archiviati["items"]] == [p["id"]]
        # archiviare non distrugge: il documento si legge ancora
        assert (await sound_pro.get_protocollo(p["id"], UTENTE_A))["stato"] \
            == "archiviato"
        # e non si archivia due volte
        with pytest.raises(HTTPException) as e:
            await sound_pro.archive_protocollo(p["id"], UTENTE_A)
        assert e.value.status_code == 404


# ── 7-9 · audit ────────────────────────────────────────────────────────────
class TestAudit:
    async def test_07_audit_create(self, banco):
        p = await _crea(UTENTE_A, "Tracciato")
        riga = await banco.audit_di("sound_pro_create", p["id"])
        assert riga and riga["organization_id"] == ORG_A
        assert riga["user_id"] == UTENTE_A["user_id"]
        assert riga["details"]["passi"] == 3

    async def test_08_audit_update(self, banco):
        p = await _crea(UTENTE_A)
        await sound_pro.update_protocollo(
            p["id"], sound_pro.ProtocolloUpdate(steps=PASSI_ALTRI), UTENTE_A)
        riga = await banco.audit_di("sound_pro_update", p["id"])
        assert riga and riga["details"]["versione_dopo"] == 2
        assert riga["details"]["nuova_versione"] is True

    async def test_09_audit_archive(self, banco):
        p = await _crea(UTENTE_A)
        await sound_pro.archive_protocollo(p["id"], UTENTE_A)
        assert await banco.audit_di("sound_pro_archive", p["id"])

    async def test_09b_audit_non_registra_il_lavoro(self, banco):
        """Gli step e le note operative sono il lavoro dell'operatore,
        non materiale da log."""
        p = await sound_pro.create_protocollo(sound_pro.ProtocolloCreate(
            nome="Con note", steps=PASSI,
            note_operative="Riservato: appunti clinici dell'operatore"),
            UTENTE_A)
        righe = await banco.audit.find(
            {"resource_id": p["id"]}).to_list(10)
        testo = json.dumps([r["details"] for r in righe])
        assert "Riservato" not in testo and "metodo" not in testo


# ── 10-13 · IL PUNTO: nessun percorso cross-org ────────────────────────────
class TestIsolamento:
    async def test_10_403_senza_privilegio(self, banco):
        with pytest.raises(HTTPException) as e:
            await sound_pro.require_sound_professional(UTENTE_MUTO)
        assert e.value.status_code == 403
        # e nemmeno un'org inesistente entra
        with pytest.raises(HTTPException):
            await sound_pro.require_sound_professional(
                {"organization_id": "org_che_non_esiste"})

    async def test_10b_il_portiere_e_su_tutte_le_rotte(self):
        """Nessun endpoint dimenticato: la guardia legge il sorgente."""
        src = (BACKEND_DIR / "routers" / "sound_pro.py").read_text()
        rotte = src.count("@router.")
        assert rotte == 5, f"{rotte} rotte: P2 ne prevede cinque"
        assert src.count("Depends(require_sound_professional)") == rotte

    async def test_11_org_b_non_vede(self, banco):
        p = await _crea(UTENTE_A, "Segreto di A")
        with pytest.raises(HTTPException) as e:
            await sound_pro.get_protocollo(p["id"], UTENTE_B)
        assert e.value.status_code == 404, "404, non 403: B non deve nemmeno " \
                                           "sapere che quell'id esiste"
        lista = await sound_pro.list_protocolli(None, UTENTE_B)
        assert lista["items"] == []

    async def test_12_org_b_non_modifica(self, banco):
        p = await _crea(UTENTE_A, "Segreto di A")
        with pytest.raises(HTTPException) as e:
            await sound_pro.update_protocollo(
                p["id"], sound_pro.ProtocolloUpdate(nome="Rubato"), UTENTE_B)
        assert e.value.status_code == 404
        assert (await sound_pro.get_protocollo(p["id"], UTENTE_A))["nome"] \
            == "Segreto di A"

    async def test_13_org_b_non_archivia(self, banco):
        p = await _crea(UTENTE_A)
        with pytest.raises(HTTPException) as e:
            await sound_pro.archive_protocollo(p["id"], UTENTE_B)
        assert e.value.status_code == 404
        assert (await sound_pro.get_protocollo(p["id"], UTENTE_A))["stato"] \
            == "bozza"

    async def test_13b_ogni_query_porta_l_org(self):
        """La prova strutturale, oltre a quella funzionale: nel router
        non esiste una query alla collezione senza organization_id."""
        import re
        src = _codice("routers/sound_pro.py")
        query = list(re.finditer(
            r"sound_protocols_collection\s*\.\s*(find_one_and_update|find_one|"
            r"find|count_documents|update_one|delete_one|delete_many)\s*\(",
            src))
        assert len(query) >= 6, f"solo {len(query)} query trovate: il test mente"
        for m in query:
            coda = src[m.end():m.end() + 120]
            assert "_mio (" in coda, f"query fuori da _mio: ...{coda[:100]}"
        # e _mio prende l'org dall'identita', non da un argomento
        assert 'return { "organization_id" : current_user [ "organization_id" ] ' \
            in src


# ── 14-19 · il server e' l'autorita' ───────────────────────────────────────
class TestAutorita:
    async def test_14_organization_id_non_e_del_client(self, banco):
        with pytest.raises(Exception) as e:
            sound_pro.ProtocolloCreate(nome="X", steps=PASSI,
                                       organization_id=ORG_B)
        assert "extra" in str(e.value).lower() or "forbid" in str(e.value).lower()
        # e il documento creato porta comunque l'org dell'identita'
        p = await _crea(UTENTE_A)
        assert p["organization_id"] == ORG_A

    async def test_15_created_by_non_e_del_client(self, banco):
        with pytest.raises(Exception):
            sound_pro.ProtocolloCreate(nome="X", steps=PASSI,
                                       created_by="chiunque")
        p = await _crea(UTENTE_A)
        assert p["created_by"] == UTENTE_A["user_id"]

    async def test_16_lo_score_del_client_e_rifiutato(self, banco):
        """Non ignorato: RIFIUTATO (preferenza esplicita del founder)."""
        bugia = {"score_version": 1, "duration_sec": 999, "layers": [],
                 "phases": []}
        with pytest.raises(Exception):
            sound_pro.ProtocolloCreate(nome="X", steps=PASSI, score=bugia)
        with pytest.raises(Exception):
            sound_pro.ProtocolloUpdate(score=bugia)
        for campo, valore in (("versione", 7), ("durata_sec", 1),
                              ("versioni_precedenti", []), ("origine", {})):
            with pytest.raises(Exception):
                sound_pro.ProtocolloCreate(**{"nome": "X", "steps": PASSI,
                                              campo: valore})

    @pytest.mark.parametrize("passi,pezzo", [
        ([], "almeno un passo"),
        ([{"metodo": "breath", "hz": 220, "durata_sec": 90, "gain": 0.3}],
         "non previsto"),
        ([{"metodo": "tone", "hz": 9000, "durata_sec": 90, "gain": 0.3}],
         "fuori da 20"),
        ([{"metodo": "bin", "hz": 400, "durata_sec": 90, "gain": 0.3}],
         "battito"),
        ([{"metodo": "tone", "hz": 220, "durata_sec": 30, "gain": 0.3}],
         "minimo è 60"),
    ])
    async def test_17_passi_invalidi_rifiutati_con_messaggio(
            self, banco, passi, pezzo):
        with pytest.raises(HTTPException) as e:
            await _crea(UTENTE_A, passi=passi)
        assert e.value.status_code == 400
        assert pezzo in e.value.detail, f"messaggio muto: «{e.value.detail}»"
        assert await banco.quanti(ORG_A) == 0

    async def test_18_score_non_stabile_sotto_clean_score_e_500(self, banco,
                                                                monkeypatch):
        """Se il compilatore producesse uno score che il contratto
        deve correggere, il server NON salva: e' un errore suo, non di
        chi ha scritto i passi — 500, e il documento non nasce."""
        def compila_bugiardo(steps):
            score = compila(steps)
            score["fade_in_sec"] = 4321        # il contratto lo riportera'
            return score
        monkeypatch.setattr(sound_pro, "compila", compila_bugiardo)
        with pytest.raises(HTTPException) as e:
            await _crea(UTENTE_A)
        assert e.value.status_code == 500
        assert await banco.quanti(ORG_A) == 0

    async def test_19_tetto_per_organizzazione(self, banco, monkeypatch):
        monkeypatch.setattr(sound_pro, "PROTOCOLLI_MAX_PER_ORG", 2)
        await _crea(UTENTE_A, "uno")
        secondo = await _crea(UTENTE_A, "due")
        with pytest.raises(HTTPException) as e:
            await _crea(UTENTE_A, "tre")
        assert e.value.status_code == 400 and "Limite" in e.value.detail
        # il tetto e' PER ORG: B non ne risente
        assert (await _crea(UTENTE_B, "suo"))["organization_id"] == ORG_B
        # e l'archivio non consuma il tetto
        await sound_pro.archive_protocollo(secondo["id"], UTENTE_A)
        assert (await _crea(UTENTE_A, "tre davvero"))["nome"] == "tre davvero"


# ── 20-22 · la catena e i gemelli ──────────────────────────────────────────
class TestCatenaECompilatori:
    async def test_20_durata_derivata(self, banco):
        p = await _crea(UTENTE_A)
        atteso = 120 + 15 + 240 + 20 + 180
        assert p["durata_sec"] == atteso == p["score"]["duration_sec"]

    async def test_21_compilazione_deterministica(self, banco):
        uno = await _crea(UTENTE_A, "uno")
        due = await _crea(UTENTE_A, "due")
        assert uno["score"] == due["score"]

    async def test_22_lo_score_salvato_e_gia_valido(self, banco):
        """La proprieta' di P1, ora sul documento in database."""
        p = await _crea(UTENTE_A)
        salvato = await banco.protocolli.find_one({"id": p["id"]})
        assert clean_score(salvato["score"]) == salvato["score"]


from nodo import NODE as _NODE


@pytest.mark.skipif(not Path(_NODE).exists(), reason="node non disponibile")
class TestGemelliDeiCompilatori:
    """LA guardia che rende lecito avere due compilatori: si eseguono
    tutti e due sulle stesse fixture e devono dire la stessa cosa —
    score compilati e messaggi d'errore. Se divergono, l'operatore
    salverebbe un protocollo diverso da quello che ha sentito
    nell'anteprima del Builder."""

    FIXTURE = [
        PASSI, PASSI_ALTRI,
        [{"metodo": "tone", "hz": 20, "durata_sec": 30, "gain": 0.05},
         {"metodo": "bin", "hz": 2000, "battito_hz": 0.05,
          "battito_fine_hz": 60, "durata_sec": 30, "gain": 1.0}],
        [{"metodo": "tone", "hz": 432.5, "durata_sec": 90.5,
          "pausa_dopo_sec": 12.25, "gain": 0.33},
         {"metodo": "iso", "hz": 181.25, "battito_hz": 7.83,
          "durata_sec": 60.25, "gain": 0.4}],
        [{"metodo": "drone", "hz": 73.42, "durata_sec": 61.0005,
          "pausa_dopo_sec": 0.0005, "gain": 0.26}],
        [{"metodo": "tone", "hz": 100 + i, "durata_sec": 60, "gain": 0.2}
         for i in range(24)],
    ]
    ERRORI = [
        [], [{"metodo": "breath", "hz": 220, "durata_sec": 90, "gain": 0.3}],
        [{"metodo": "tone", "hz": 9000, "durata_sec": 90, "gain": 0.3}],
        [{"metodo": "bin", "hz": 400, "durata_sec": 90, "gain": 0.3}],
        [{"metodo": "iso", "hz": 400, "battito_hz": 90,
          "durata_sec": 90, "gain": 0.3}],
        [{"metodo": "tone", "hz": 220, "durata_sec": 30, "gain": 0.3}],
        [{"metodo": "tone", "hz": 220, "durata_sec": 1900, "gain": 0.3}],
        [{"metodo": "tone", "hz": 220, "battito_hz": 7,
          "durata_sec": 90, "gain": 0.3}],
        [{"metodo": "tone", "hz": 220, "durata_sec": 90, "gain": 2}],
        [{"metodo": "tone", "hz": 220, "durata_sec": 60, "gain": 0.3}] * 25,
    ]

    def _js(self, casi):
        script = f"""
import {{ compila }} from {json.dumps(str(COMPILATORE_JS))};
const casi = {json.dumps(casi)};
console.log(JSON.stringify(casi.map((steps) => {{
  try {{ return {{ ok: compila(steps) }}; }}
  catch (e) {{ return {{ errore: e.message }}; }}
}})));
"""
        r = subprocess.run([_NODE, "--input-type=module", "-e", script],
                           capture_output=True, text=True, timeout=60)
        assert r.returncode == 0, f"node è morto: {r.stderr[:400]}"
        return json.loads(r.stdout.strip().splitlines()[-1])

    def _py(self, casi):
        out = []
        for steps in casi:
            try:
                out.append({"ok": compila(steps)})
            except ErrorePasso as e:
                out.append({"errore": str(e)})
        return out

    def test_gli_score_coincidono(self):
        js, py = self._js(self.FIXTURE), self._py(self.FIXTURE)
        for i, (a, b) in enumerate(zip(js, py)):
            assert "ok" in a and "ok" in b, f"fixture {i}: {a} / {b}"
            assert a["ok"] == b["ok"], (
                f"i gemelli divergono sulla fixture {i}\n"
                f"JS:     {json.dumps(a['ok'], sort_keys=True)[:400]}\n"
                f"Python: {json.dumps(b['ok'], sort_keys=True)[:400]}")

    def test_anche_i_rifiuti_dicono_la_stessa_frase(self):
        js, py = self._js(self.ERRORI), self._py(self.ERRORI)
        for i, (a, b) in enumerate(zip(js, py)):
            assert "errore" in a and "errore" in b, \
                f"caso {i}: uno dei due ha ACCETTATO — {a} / {b}"
            assert a["errore"] == b["errore"], \
                f"caso {i}: JS «{a['errore']}» ≠ Python «{b['errore']}»"

    def test_le_costanti_restano_gemelle(self):
        """La guardia di P1 continua a valere anche ora che l'autorita'
        e' Python: i tre livelli (contratto, autorita', specchio) non
        possono scollarsi."""
        import re
        from models import frequency_track as ft
        from services import sound_compiler as sc
        js = COMPILATORE_JS.read_text()
        for nome_js, valore in (("PASSI_MAX", sc.PASSI_MAX),
                                ("DURATA_MIN", ft.DURATION_MIN),
                                ("DURATA_MAX", ft.DURATION_MAX),
                                ("PORTANTE_MIN", ft.CARRIER_MIN),
                                ("PORTANTE_MAX", ft.CARRIER_MAX),
                                ("BATTITO_MIN", ft.BEAT_MIN),
                                ("BATTITO_MAX", ft.BEAT_MAX)):
            m = re.search(rf"export const {nome_js} = ([\d.]+);", js)
            assert m and float(m.group(1)) == float(valore), \
                f"{nome_js}: JS {m and m.group(1)} ≠ {valore}"


def _codice(relativo: str) -> str:
    """Il file SENZA commenti e senza docstring.

    Le guardie che cercano parole proibite devono leggere il CODICE:
    altrimenti inciampano sulla prosa che spiega perche' quella parola
    non c'e' — e' gia' successo, piu' di una volta."""
    import io
    import tokenize
    testo = (BACKEND_DIR / relativo).read_text()
    pezzi = []
    attesa_docstring = True
    for tok in tokenize.generate_tokens(io.StringIO(testo).readline):
        if tok.type == tokenize.COMMENT:
            continue
        if tok.type == tokenize.STRING and attesa_docstring:
            attesa_docstring = False
            continue
        if tok.type == tokenize.NEWLINE:
            attesa_docstring = False
        if tok.type == tokenize.INDENT:
            attesa_docstring = True
        if tok.type in (tokenize.NAME, tokenize.OP, tokenize.NUMBER,
                        tokenize.STRING):
            pezzi.append(tok.string)
            if tok.type == tokenize.NAME and tok.string in ("def", "class"):
                attesa_docstring = True
    return " ".join(pezzi)


class TestNienteCheNonDeveEsserci:
    def test_p2_non_conosce_i_clienti_ne_la_salute(self):
        """Il legame protocollo → sessione → cliente arriva in P5/P6, e
        i claim sanitari non arrivano mai."""
        for f in ("routers/sound_pro.py", "services/sound_compiler.py",
                  "models/sound_protocol.py"):
            src = _codice(f).lower()
            for parola in ("customer_id", "patolog", "diagnos", "terap",
                           "biofeedback", "biorisonanza", "sintom",
                           "efficac", "guarig"):
                assert parola not in src, f"{f} parla di «{parola}»"

    def test_p2_non_tocca_le_tracce(self):
        src = _codice("routers/sound_pro.py")
        assert "frequency_tracks" not in src, "collezione separata: D1"
        assert "sound_composer" not in src, \
            "il privilegio del comporre e' un'altra cosa"
