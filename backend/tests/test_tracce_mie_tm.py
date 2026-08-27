"""Ciclo TM (27/8/2026) — «Le mie tracce» consolidata.

Le onde di docs/TRACCE_MIE_REFINEMENT_2026-08.md sotto guardia:
il lessico dei gesti dice DOVE va la traccia (TM1), la scheda ha un
solo gesto primario per stato col pannello link ripiegabile (TM2),
il pulsante pubblico esiste solo per la chiave 1 e chiede conferma
(TM3), il cliente su /ascolta non incontra mai il cerchio/Lettera
(TM4), la campana d'uscita suona solo a sessione sporca (TM6), la
voce di passerella si chiama «Aurya Sound» (TM7, in sistema 06b),
gli spezzoni seguono la sessione come i livelli (TM8).
"""
import os
import re
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


def _senza_commenti(testo: str) -> str:
    testo = re.sub(r"/\*.*?\*/", " ", testo, flags=re.S)
    return re.sub(r"^\s*//.*$", " ", testo, flags=re.M)


def _pagina() -> str:
    return _senza_commenti((FQ / "FrequenzePage.js").read_text())


def _blocco_mine(src: str) -> str:
    """La porzione della scheda «Le mie tracce» (dal map dei drafts
    alla chiusura delle cards)."""
    a = src.find("drafts.map((d) => {")
    assert a > -1, "il map delle tracce non esiste piu'"
    b = src.find("{condividi && (", a)
    assert b > -1
    return src[a:b]


class TestLessicoTm1:
    def test_01_i_gesti_dicono_dove(self):
        blocco = _blocco_mine(_pagina())
        assert ">Nelle Meditazioni</button>" in blocco
        assert ">Riservata ai clienti</button>" in blocco
        assert ">Pubblica per i tuoi clienti</button>" in blocco
        assert ">Ritira dalle Meditazioni</button>" in blocco
        assert ">Riporta in bozza</button>" in blocco
        # mai piu' un «Pubblica» nudo o un «Ritira» senza provenienza
        assert ">Pubblica</button>" not in blocco
        assert ">Ritira</button>" not in blocco

    def test_02_lo_stato_in_scheda_parla(self):
        blocco = _blocco_mine(_pagina())
        assert "Nelle Meditazioni · " in blocco and "ascolti" in blocco
        assert "Riservata · " in blocco and "link attiv" in blocco
        assert "shares_attivi" in blocco

    def test_03_conferma_esplicita_sul_pubblico(self):
        """Il gesto verso la vetrina non e' mai un click distratto:
        passa da confermaMeditazioni, che dice dove va la traccia."""
        src = _pagina()
        assert "confermaMeditazioni" in src
        a = src.find("const confermaMeditazioni")
        corpo = src[a:a + 600]
        assert "Meditazioni pubbliche di Aurya" in corpo
        assert "visibile a tutti gli iscritti" in corpo
        # la conferma pubblica E infornera' il master (pubblicaDaLista)
        assert "pubblicaDaLista(d.id)" in corpo
        # e il pulsante pubblico chiama la conferma, non publishById
        blocco = _blocco_mine(src)
        riga = blocco[blocco.find("fq-pubblica-meditazioni") - 300:
                      blocco.find("fq-pubblica-meditazioni") + 300]
        assert "confermaMeditazioni(d)" in riga


class TestSchedaTm2:
    def test_04_un_pannello_ripiegabile(self):
        """TM2, rivisto dal founder (27/8 sera, «il riquadro si
        allunga troppo»): il pannello e' un FOGLIO (overlay gate) —
        la scheda mostra solo «Link riservati (N)» e non si allunga
        mai; dentro il foglio la lista SCORRE (max-height) e il nome
        lungo si tronca con l'ellissi invece di uscire dal riquadro."""
        src = _pagina()
        assert "setCondividi({ id: d.id" in src
        assert "Link riservati (" in src
        # il foglio e' montato UNA volta, fuori dalle carte
        assert re.search(r"condividi && \(\s*<CondivisioniTraccia", src)
        assert "linkAperti" not in src, "il pannello inline e' tornato"
        css = (FQ / "frequenze.css").read_text()
        assert "cond-lista" in css and "overflow-y:auto" in css
        assert "text-overflow:ellipsis" in css.split(".cond-chi b")[1][:200]

    def test_05_elimina_fuori_dalla_riga(self):
        src = _pagina()
        assert 'className="mine-del"' in src
        blocco = _blocco_mine(src)
        foot = blocco[blocco.find("mine-foot"):]
        assert "removeDraft" not in foot, "l'elimina e' tornato tra i gesti"

    def test_06_il_conteggio_arriva_col_server(self):
        rotte = (BACKEND_DIR / "routers" / "frequencies.py").read_text()
        a = rotte.find("async def list_tracks")
        corpo = rotte[a:rotte.find("@router", a + 10)]
        assert "shares_attivi" in corpo
        assert '"stato": "attivo"' in corpo, \
            "il conteggio deve contare SOLO i link attivi"


class TestMuroUiTm3:
    def test_07_pubblico_solo_nel_ramo_chiave_1(self):
        """Il pulsante verso le Meditazioni esiste UNA volta, dentro
        il ramo user?.sound_composer. Il 403 server resta la
        frontiera vera (gia' guardato in test_sound_studio_tr)."""
        src = _pagina()
        assert src.count("fq-pubblica-meditazioni") == 1
        blocco = _blocco_mine(src)
        ramo1_a = blocco.find("user?.sound_composer ? (")
        assert ramo1_a > -1
        ramo1_b = blocco.find(") : (", ramo1_a)
        assert "fq-pubblica-meditazioni" in blocco[ramo1_a:ramo1_b]
        # il ramo chiave-2 (dopo l'else) non nomina mai le Meditazioni
        ramo2 = blocco[ramo1_b:blocco.find(") : riservata", ramo1_b)]
        assert "Meditazioni" not in ramo2, \
            "la chiave 2 non deve mai leggere la parola Meditazioni"


class TestIsolamentoTm4:
    def test_08_ascolta_non_conosce_il_cerchio(self):
        """/ascolta/{token} e' il canale del CLIENTE dell'operatore:
        niente cerchio, niente Lettera, niente newsletter — i canali
        restano fisicamente separati."""
        src = _senza_commenti((FQ / "AscoltaPage.jsx").read_text())
        assert "lib/cerchio" not in src
        assert "cerchio" not in src.lower()
        assert "lettera" not in src.lower()
        assert "newsletter" not in src.lower()

    def test_09_gli_share_non_passano_dal_cancello(self):
        """I commenti possono SPIEGARE la separazione dal cerchio;
        il codice non deve attraversarla."""
        rotte = (BACKEND_DIR / "routers" / "sound_shares.py").read_text()
        codice = re.sub(r'\"\"\".*?\"\"\"', " ", rotte, flags=re.S)
        codice = re.sub(r"^\s*#.*$", " ", codice, flags=re.M)
        assert "_has_catalog_access" not in codice
        assert "cerchio" not in codice.lower()
        assert "newsletter" not in codice.lower()


class TestCampanaTm6:
    def test_10_il_dirty_vero(self):
        """La campana suona solo a sessione SPORCA: la firma salvata
        (stesso scorePayload del pubblicato) e' il segnale, non
        layers.length."""
        src = _pagina()
        assert "firmaSalvata" in src
        a = src.find("const sporca = ")
        assert a > -1
        corpo = src[a:a + 400]
        assert "firmaSalvata" in corpo
        # Salva bozza pulisce la firma
        assert "setFirmaSalvata(JSON.stringify(scorePayload()))" in src

    def test_11_tutte_le_uscite_passano_dalla_campana(self):
        src = _pagina()
        assert "primaDiUscire={chiediUscita}" in src, \
            "la guardia d'uscita non arriva a topbar/stanze"
        topbar = _senza_commenti((FQ / "SoundTopbar.jsx").read_text())
        assert "primaDiUscire" in topbar
        assert "e.preventDefault()" in topbar
        stanze = _senza_commenti((FQ / "StanzeSound.jsx").read_text())
        assert "primaDiUscire" in stanze
        assert "window.confirm" not in stanze, \
            "il dialogo nativo e' tornato nella barra delle stanze"

    def test_12_modale_proprio_e_rete_beforeunload(self):
        src = _pagina()
        a = src.find("const chiediUscita")
        corpo = src[a:a + 900]
        assert "setAsk" in corpo, "la campana deve usare il modale del mondo"
        assert "Salva ed esci" in src
        assert "Esci senza salvare" in src
        # beforeunload resta SOLO come rete del tab, e solo se sporca
        b = src.find("beforeunload")
        assert b > -1
        assert "sporcaRef.current" in src[b - 500:b + 500]


class TestSpezzoniTm8Frontend:
    def test_13_il_leggio_e_della_sessione(self):
        src = _pagina()
        assert "voiceClips.map(rigaClip)" in src
        assert "voiceSenza.map(rigaClip)" in src
        assert "Spezzoni senza sessione" in src
        # reset → leggio vuoto; bozza → i suoi spezzoni
        assert "clipsSessioneRef" in src
        a = src.find("const loadVoice")
        corpo = src[a:a + 700]
        assert "c.track_id === tid" in corpo
        assert "c.track_id == null" in corpo

    def test_14_la_registrazione_nasce_legata(self):
        api = (FRONTEND_SRC / "api" / "frequencies.js").read_text()
        assert "if (trackId) fd.append('track_id', trackId)" in api
        assert "updateVoice" in api
        src = _pagina()
        # al Salva bozza i legami si consolidano
        assert "updateVoice(cid, { track_id: idFinale })" in src


PREFIX = "test_tm_"
ORG = PREFIX + "org"
ALTRA = PREFIX + "altra"


def _user(org_id=ORG):
    return {"id": PREFIX + "u", "email": "tm@example.com",
            "organization_id": org_id}


@pytest.fixture
async def banco(monkeypatch, tmp_path):
    import uuid as _uuid
    try:
        from motor.motor_asyncio import AsyncIOMotorClient
        client = AsyncIOMotorClient(
            os.environ.get("MONGO_URL", "mongodb://localhost:27017"),
            serverSelectionTimeoutMS=2000)
        await client.admin.command("ping")
    except Exception as e:
        pytest.skip(f"MongoDB non raggiungibile: {e}")

    nome_db = f"test_tm_{_uuid.uuid4().hex[:8]}"
    db = client[nome_db]
    import database as db_mod
    for attr, coll in (("frequency_tracks_collection", db.frequency_tracks),
                       ("voice_assets_collection", db.voice_assets),
                       ("organizations_collection", db.organizations)):
        monkeypatch.setattr(db_mod, attr, coll)
    from services import voice_adoption
    monkeypatch.setattr(voice_adoption, "VOICE_DIR", tmp_path)

    await db.organizations.insert_one(
        {"id": ORG, "name": "Org", "sound_composer": True})
    await db.frequency_tracks.insert_many([
        {"id": PREFIX + "t1", "organization_id": ORG, "title": "Uno",
         "status": "draft",
         "score": {"layers": [{"kind": "voice",
                               "asset_id": PREFIX + "legacy_usato"}]}},
        {"id": PREFIX + "t2", "organization_id": ORG, "title": "Due",
         "status": "draft", "score": {"layers": []}},
        {"id": PREFIX + "t_altrui", "organization_id": ALTRA,
         "title": "Altrui", "status": "draft", "score": {"layers": []}},
    ])

    class Banco:
        tracce = db.frequency_tracks
        voce = db.voice_assets
        dir = tmp_path

    try:
        yield Banco()
    finally:
        await client.drop_database(nome_db)
        client.close()


def _clip(cid, **extra):
    from models.common import utc_now
    doc = {"id": cid, "organization_id": ORG, "title": cid,
           "duration_sec": 3.0, "size_bytes": 10,
           "stream_url": f"/uploads/voice/{ORG}/{cid}.webm",
           "created_at": utc_now()}
    doc.update(extra)
    return doc


class TestSpezzoniTm8Backend:
    @pytest.mark.asyncio
    async def test_15_i_filtri_del_leggio(self, banco):
        """?track_id=X da' gli spezzoni della sessione; ?senza=1 il
        ripiego — che prende sia i null (post-regola) sia i LEGACY
        (campo assente): in Mongo {track_id: null} li copre entrambi."""
        from routers import frequencies
        await banco.voce.insert_many([
            _clip(PREFIX + "della_t1", track_id=PREFIX + "t1"),
            _clip(PREFIX + "nullo", track_id=None),
            _clip(PREFIX + "legacy"),          # campo ASSENTE
        ])
        r = await frequencies.list_voice_clips(
            current_user=_user(), track_id=PREFIX + "t1", senza=None)
        assert [i["id"] for i in r["items"]] == [PREFIX + "della_t1"]
        r = await frequencies.list_voice_clips(
            current_user=_user(), track_id=None, senza=1)
        assert {i["id"] for i in r["items"]} == {
            PREFIX + "nullo", PREFIX + "legacy"}
        # senza parametri: il pool intero (risoluzione playback)
        r = await frequencies.list_voice_clips(
            current_user=_user(), track_id=None, senza=None)
        assert len(r["items"]) == 3

    @pytest.mark.asyncio
    async def test_16_adozione_solo_verso_tracce_mie(self, banco):
        """Il PATCH track_id (l'adozione del Salva bozza) rifiuta una
        traccia altrui: un id fuori org e' un id inventato → 400."""
        from fastapi import HTTPException
        from routers import frequencies
        await banco.voce.insert_one(_clip(PREFIX + "c", track_id=None))
        payload = frequencies.VoiceClipUpdate(track_id=PREFIX + "t2")
        await frequencies.update_voice_clip(
            PREFIX + "c", payload, current_user=_user())
        doc = await banco.voce.find_one({"id": PREFIX + "c"})
        assert doc["track_id"] == PREFIX + "t2"
        with pytest.raises(HTTPException) as e:
            await frequencies.update_voice_clip(
                PREFIX + "c",
                frequencies.VoiceClipUpdate(track_id=PREFIX + "t_altrui"),
                current_user=_user())
        assert e.value.status_code == 400

    @pytest.mark.asyncio
    async def test_17_adozione_una_tantum_e_scopa(self, banco):
        """All'avvio: i legacy referenziati da uno score vengono
        adottati dalla loro traccia; i post-regola orfani e vecchi si
        spazzano (file + documento); i LEGACY non referenziati non si
        toccano MAI — registrazioni di voce non si cancellano senza
        consenso."""
        from datetime import timedelta
        from models.common import utc_now
        from services.voice_adoption import adotta_spezzoni
        vecchio = utc_now() - timedelta(days=8)
        await banco.voce.insert_many([
            _clip(PREFIX + "legacy_usato"),                 # → adottato da t1
            _clip(PREFIX + "legacy_libero",                 # legacy: intoccabile
                  created_at=vecchio),
            _clip(PREFIX + "orfano_vecchio", track_id=None,  # → spazzato
                  created_at=vecchio,
                  stream_url=f"/uploads/voice/{ORG}/orfano.webm"),
            _clip(PREFIX + "orfano_fresco", track_id=None),  # troppo giovane
        ])
        cartella = banco.dir / ORG
        cartella.mkdir()
        (cartella / "orfano.webm").write_bytes(b"x")

        esito = await adotta_spezzoni()
        assert esito == {"adottati": 1, "spazzati": 1}

        adottato = await banco.voce.find_one({"id": PREFIX + "legacy_usato"})
        assert adottato["track_id"] == PREFIX + "t1"
        assert await banco.voce.find_one({"id": PREFIX + "legacy_libero"})
        assert await banco.voce.find_one({"id": PREFIX + "orfano_fresco"})
        assert not await banco.voce.find_one(
            {"id": PREFIX + "orfano_vecchio"})
        assert not (cartella / "orfano.webm").exists()

    def test_18_la_scopa_parte_con_il_server(self):
        server = (BACKEND_DIR / "server.py").read_text()
        assert "adotta_spezzoni" in server
