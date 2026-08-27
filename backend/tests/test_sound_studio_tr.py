"""IL MURO del ciclo TR (27/8/2026) — Crea Studio col piano Pro.

Le sette prove del piano (docs/CREA_TRACCE_RISERVATE_PLAN_2026-08.md
§6), scritte PRIMA di ogni deploy. La prima si chiama «il test di
Valentina»: chi ha la chiave 1 (concessione manuale) deve vivere il
flusso di oggi, byte per byte — e' la promessa al founder che
l'attuale non si rompe.
"""
import sys
from pathlib import Path

import pytest

import os
os.environ.setdefault("JWT_SECRET_KEY", "test")
os.environ.setdefault("MONGO_URL", "mongodb://localhost:27017")
os.environ.setdefault("DB_NAME", "test_database")

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

from fastapi import HTTPException  # noqa: E402

from routers import frequencies  # noqa: E402
from routers import sound_shares  # noqa: E402
from services.studio_access import studio_attivo  # noqa: E402

PREFIX = "test_tr_"
ORG_VALE = PREFIX + "valentina"     # chiave 1, nessun abbonamento
ORG_PRO = PREFIX + "pro"            # solo chiave 2 (abbonata)
ORG_FREE = PREFIX + "free"          # nessuna chiave
UTENTE = {"id": PREFIX + "u", "email": "tr@example.com"}


def _user(org_id):
    return {**UTENTE, "organization_id": org_id}


@pytest.fixture
async def banco(monkeypatch, tmp_path):
    """Database effimero + cartella master effimera."""
    import uuid as _uuid
    try:
        from motor.motor_asyncio import AsyncIOMotorClient
        client = AsyncIOMotorClient(
            os.environ.get("MONGO_URL", "mongodb://localhost:27017"),
            serverSelectionTimeoutMS=2000)
        await client.admin.command("ping")
    except Exception as e:
        pytest.skip(f"MongoDB non raggiungibile: {e}")

    nome_db = f"test_tr_{_uuid.uuid4().hex[:8]}"
    db = client[nome_db]
    import database as db_mod
    for attr, coll in (("frequency_tracks_collection", db.frequency_tracks),
                       ("organizations_collection", db.organizations),
                       ("customers_collection", db.customers),
                       ("sound_shares_collection", db.sound_shares)):
        monkeypatch.setattr(db_mod, attr, coll)
    monkeypatch.setattr(frequencies, "MASTERS_DIR", tmp_path)

    await db.organizations.insert_many([
        {"id": ORG_VALE, "name": "Valentina", "sound_composer": True},
        {"id": ORG_PRO, "name": "Studio Pro",
         "plan": "pro", "billing_status": "active"},
        {"id": ORG_FREE, "name": "Base", "plan": "free",
         "billing_status": "none"},
    ])
    await db.customers.insert_one(
        {"id": PREFIX + "marco", "organization_id": ORG_PRO,
         "name": "Marco Cliente"})

    class Banco:
        tracce = db.frequency_tracks
        org = db.organizations
        share = db.sound_shares

    try:
        yield Banco()
    finally:
        await client.drop_database(nome_db)
        client.close()


SCORE = {"duration_sec": 120,
         "layers": [{"method": "drone", "carrier": 110, "gain": 0.2}]}


async def _bozza(banco, org_id, titolo="Prova TR"):
    utente = _user(org_id)
    utente["_sound_composer"] = False   # lo riscrive il portiere vero
    creato = await frequencies.create_track(
        frequencies.TrackCreate(title=titolo, score=SCORE), utente)
    return creato["id"]


async def _porta(org_id):
    """Il portiere VERO, con l'org letta dal database effimero."""
    return await frequencies.require_sound_crea(_user(org_id))


# ── 1 · il test di Valentina: la chiave 1 vive come oggi ──────────────────
class TestChiave1Invariata:
    async def test_compone_e_pubblica_in_pubblico_come_oggi(self, banco):
        utente = await _porta(ORG_VALE)
        assert utente["_sound_composer"] is True
        tid = await _bozza(banco, ORG_VALE)
        esito = await frequencies.publish_track(tid, None, utente)
        # senza body la via storica: PUBBLICA, in catalogo
        assert esito["visibility"] == "public"
        doc = await banco.tracce.find_one({"id": tid})
        assert doc["status"] == "published"
        assert doc["visibility"] == "public"
        # e la pagina per slug la trova (il muro non la tocca)
        t = await frequencies._trova_pubblicata(esito["slug"], {"_id": 0, "id": 1})
        assert t and t["id"] == tid

    async def test_puo_scegliere_il_riservato(self, banco):
        utente = await _porta(ORG_VALE)
        tid = await _bozza(banco, ORG_VALE)
        esito = await frequencies.publish_track(
            tid, frequencies.PublishBody(visibility="private"), utente)
        assert esito["visibility"] == "private"


# ── 2 · la chiave 2: compone, MAI in pubblico ─────────────────────────────
class TestChiave2:
    async def test_pro_compone_ma_pubblica_riservato(self, banco):
        utente = await _porta(ORG_PRO)
        assert utente["_sound_composer"] is False
        tid = await _bozza(banco, ORG_PRO)
        esito = await frequencies.publish_track(tid, None, utente)
        assert esito["visibility"] == "private", \
            "senza chiave 1 il publish DEVE essere riservato"

    async def test_chiedere_il_pubblico_e_un_403(self, banco):
        utente = await _porta(ORG_PRO)
        tid = await _bozza(banco, ORG_PRO)
        with pytest.raises(HTTPException) as e:
            await frequencies.publish_track(
                tid, frequencies.PublishBody(visibility="public"), utente)
        assert e.value.status_code == 403

    async def test_la_riservata_non_esce_dal_muro(self, banco):
        utente = await _porta(ORG_PRO)
        tid = await _bozza(banco, ORG_PRO)
        esito = await frequencies.publish_track(tid, None, utente)
        slug = esito["slug"]
        # la pagina per slug NON la trova
        assert await frequencies._trova_pubblicata(slug, {"_id": 0}) is None
        # il filtro del catalogo la esclude
        quante = await banco.tracce.count_documents(
            frequencies.solo_pubbliche({"status": "published"}))
        assert quante == 0
        # il contatore ascolti pubblico non la incrementa
        await frequencies.register_play(slug)
        doc = await banco.tracce.find_one({"id": tid})
        assert doc.get("plays_total", 0) == 0


# ── 3 · senza chiavi: la porta resta chiusa ───────────────────────────────
class TestSenzaChiavi:
    async def test_free_non_entra(self, banco):
        with pytest.raises(HTTPException) as e:
            await _porta(ORG_FREE)
        assert e.value.status_code == 403

    async def test_anche_il_cancello_pubblico_resta_chiuso(self, banco):
        with pytest.raises(HTTPException) as e:
            await frequencies.require_sound_composer(_user(ORG_FREE))
        assert e.value.status_code == 403


# ── 4-5 · gli share: revoca chirurgica e link che si spengono ─────────────
class TestShare:
    async def _traccia_condivisa(self, banco):
        utente = await _porta(ORG_PRO)
        tid = await _bozza(banco, ORG_PRO)
        await frequencies.publish_track(tid, None, utente)
        await banco.tracce.update_one(
            {"id": tid}, {"$set": {"master_file": "m.mp3"}})
        share = await sound_shares.crea_condivisione(
            tid, sound_shares.ShareCreate(contact_id=PREFIX + "marco"),
            utente)
        return utente, tid, share

    async def test_il_link_suona_e_conta(self, banco):
        _, _, share = await self._traccia_condivisa(banco)
        out = await sound_shares.ascolta_condivisa(share["token"])
        assert out["title"] == "Prova TR" and out["master_pronto"]
        doc = await banco.share.find_one({"id": share["id"]})
        assert doc["accessi"] == 1 and doc["ultimo_accesso"] is not None

    async def test_revoca_chirurgica(self, banco):
        utente, tid, share1 = await self._traccia_condivisa(banco)
        from database import customers_collection
        await customers_collection.insert_one(
            {"id": PREFIX + "giulia", "organization_id": ORG_PRO,
             "name": "Giulia"})
        share2 = await sound_shares.crea_condivisione(
            tid, sound_shares.ShareCreate(contact_id=PREFIX + "giulia"),
            utente)
        await sound_shares.revoca_condivisione(share1["id"], utente)
        with pytest.raises(HTTPException) as e:
            await sound_shares.ascolta_condivisa(share1["token"])
        assert e.value.status_code == 404
        # il messaggio e' NEUTRO: mai la contabilita' dell'operatore
        assert "abbonamento" not in str(e.value.detail).lower()
        # Giulia continua
        assert (await sound_shares.ascolta_condivisa(share2["token"]))["title"]

    async def test_pro_decaduto_spegne_i_link(self, banco):
        """Deciso dal founder (v3): se l'operatore smette di pagare i
        link si spengono SUBITO — e alla riattivazione riprendono
        senza rigenerare niente."""
        _, _, share = await self._traccia_condivisa(banco)
        await banco.org.update_one(
            {"id": ORG_PRO}, {"$set": {"billing_status": "past_due"}})
        with pytest.raises(HTTPException) as e:
            await sound_shares.ascolta_condivisa(share["token"])
        assert e.value.status_code == 403
        assert "abbonamento" not in str(e.value.detail).lower()
        # e anche il comporre si chiude
        with pytest.raises(HTTPException):
            await _porta(ORG_PRO)
        # riattivazione: lo STESSO link riprende
        await banco.org.update_one(
            {"id": ORG_PRO}, {"$set": {"billing_status": "active"}})
        assert (await sound_shares.ascolta_condivisa(share["token"]))["title"]

    async def test_niente_share_su_tracce_pubbliche(self, banco):
        utente = await _porta(ORG_VALE)
        tid = await _bozza(banco, ORG_VALE)
        await frequencies.publish_track(tid, None, utente)   # public
        from database import customers_collection
        await customers_collection.insert_one(
            {"id": PREFIX + "anna", "organization_id": ORG_VALE,
             "name": "Anna"})
        with pytest.raises(HTTPException) as e:
            await sound_shares.crea_condivisione(
                tid, sound_shares.ShareCreate(contact_id=PREFIX + "anna"),
                utente)
        assert e.value.status_code == 400

    async def test_il_contatto_e_della_mia_org(self, banco):
        """Un contact_id di un'altra org e' indistinguibile da uno
        inventato: 400, senza dire di piu' (lezione S2)."""
        utente = await _porta(ORG_PRO)
        tid = await _bozza(banco, ORG_PRO)
        await frequencies.publish_track(tid, None, utente)
        with pytest.raises(HTTPException) as e:
            await sound_shares.crea_condivisione(
                tid, sound_shares.ShareCreate(contact_id=PREFIX + "anna"),
                utente)   # anna e' di ORG_VALE
        assert e.value.status_code == 400


# ── 6-7 · la funzione della verita': trial, override, kill switch ─────────
class TestStudioAttivo:
    def test_gli_stati_del_billing(self):
        base = {"plan": "pro"}
        for stato, atteso in (("active", True), ("trialing", True),
                              ("manual", True), ("past_due", False),
                              ("canceled", False), ("none", False)):
            assert studio_attivo({**base, "billing_status": stato}) is atteso
        assert studio_attivo({"plan": "starter",
                              "billing_status": "active"}) is False
        assert studio_attivo({}) is False
        assert studio_attivo(None) is False

    def test_le_chiavi_e_il_kill_switch(self):
        assert studio_attivo({"sound_composer": True}) is True
        assert studio_attivo({"sound_studio_override": "on"}) is True
        # il kill switch vince su TUTTO: abbonamento e chiave manuale
        assert studio_attivo({"sound_studio_override": "off", "plan": "pro",
                              "billing_status": "active"}) is False
        assert studio_attivo({"sound_studio_override": "off",
                              "sound_composer": True}) is False


# ── il muro STATICO: le superfici passano dal filtro ──────────────────────
class TestMuroStatico:
    def test_le_superfici_pubbliche_usano_il_filtro(self):
        src = (BACKEND_DIR / "routers" / "frequencies.py").read_text()
        # catalogo (filtro + conteggio teaser), pagina per slug,
        # contatore ascolti, preferite: almeno 5 usi del muro
        assert src.count("solo_pubbliche(") >= 5
        seo = (BACKEND_DIR / "routers" / "seo.py").read_text()
        assert '"visibility": {"$ne": "private"}' in seo, "sitemap senza muro"
        shell = (BACKEND_DIR / "routers" / "seo_shell.py").read_text()
        assert '"visibility": {"$ne": "private"}' in shell, "shell senza muro"
        trk = (BACKEND_DIR / "routers" / "tracking.py").read_text()
        assert '"visibility": {"$ne": "private"}' in trk, "tracking senza muro"

    def test_il_registro_conosce_ascolta_come_servizio(self):
        import json
        rotte = json.loads(
            (BACKEND_DIR / "config" / "rotte.json").read_text())
        assert "ascolta" in rotte["servizio"], \
            "/ascolta e' una pagina a token: servizio, mai indicizzata"
        assert "ascolta" not in rotte.get("pubblica", [])

    def test_il_token_e_opaco_non_jwt(self):
        import re
        src = (BACKEND_DIR / "routers" / "sound_shares.py").read_text()
        assert "secrets.token_urlsafe" in src
        # il CODICE (senza docstring e commenti: la prosa che spiega
        # «non un JWT» non deve far scattare la guardia che lo vieta)
        codice = re.sub(r'""".*?"""', " ", src, flags=re.S)
        codice = re.sub(r"^\s*#.*$", " ", codice, flags=re.M)
        assert "jwt" not in codice.lower(), \
            "la revoca deve essere immediata: token in DB, non JWT"
