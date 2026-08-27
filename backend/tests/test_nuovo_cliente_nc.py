"""Ciclo NC (27/8/2026) — «Nuovo cliente» nel registro.

Deciso dal founder: il registro (Customer Insights, la voce «Clienti»
del menu snello) smette di essere solo specchio — un bottone crea il
cliente a mano. La promessa da guardare e' la FONTE UNICA: il cliente
creato dal registro e' lo stesso che ScegliPersona trova nel foglio
dei link riservati di Sound, senza sincronizzazioni.

Due piani di prova:
- statiche: il bottone esiste nel registro, il componente e' isolato,
  registro e foglio leggono la STESSA api;
- la catena viva (banco Mongo effimero): POST /customers → il cliente
  e' nella lista (attivo) → uno share su una riservata lo accetta e
  ne fotografa il nome; un contatto di un'altra org resta fuori.
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
CI = FRONTEND_SRC / "features" / "customer-insights"


def _senza_commenti(testo: str) -> str:
    testo = re.sub(r"/\*.*?\*/", " ", testo, flags=re.S)
    return re.sub(r"^\s*//.*$", " ", testo, flags=re.M)


class TestLaPorta:
    def test_01_il_bottone_vive_nel_registro(self):
        src = _senza_commenti((CI / "CustomerInsightsPage.jsx").read_text())
        assert "import NuovoCliente from './components/NuovoCliente'" in src
        assert "<NuovoCliente onCreato={onRefresh} />" in src, \
            "il registro deve ricaricarsi dopo la creazione"

    def test_02_il_componente_e_isolato(self):
        """Bottone + dialogo autonomi: parla con la pagina solo via
        onCreato, e scrive tramite la stessa api della rubrica."""
        src = _senza_commenti(
            (CI / "components" / "NuovoCliente.jsx").read_text())
        assert "customersAPI.create" in src
        assert "onCreato" in src
        assert 'data-testid="ci-nuovo-cliente"' in src
        assert 'data-testid="ci-nuovo-salva"' in src
        # il nome e' obbligatorio, il resto facoltativo
        assert "!form.name.trim()" in src
        # niente stato importato dalla pagina: solo props
        assert "useContext" not in src and "useSelector" not in src

    def test_03_fonte_unica_col_foglio_dei_link(self):
        """La promessa M-CRM: registro e ScegliPersona leggono la
        STESSA api — un cliente creato qui appare la', senza sync."""
        nuovo = (CI / "components" / "NuovoCliente.jsx").read_text()
        persona = (FRONTEND_SRC / "features" / "frequenze" / "pro"
                   / "ScegliPersona.jsx").read_text()
        assert "from '../../../api/customers'" in nuovo
        assert "from '../../../api/customers'" in persona
        assert "customersAPI.list" in persona


class TestIlTrattino:
    """27/8, founder: i clienti creati a mano mostravano «status.null»
    (chiave i18n grezza) e la stringa letterale «\\u2014» — in un nodo
    di testo JSX gli escape non esistono. Il valore assente si dice
    con UN TRATTINO, sempre."""

    def test_07_niente_escape_ne_chiavi_grezze(self):
        for nome in ("components/CustomerTable.jsx",
                     "components/CustomerProfileSlide.jsx",
                     "CustomerInsightsPage.jsx"):
            src = (CI / nome).read_text()
            assert "u2014" not in src, f"{nome}: trattino scritto come escape"
        tabella = (CI / "components" / "CustomerTable.jsx").read_text()
        # lo stato assente non passa da t(): niente «status.null»
        assert "row.customer_status ? (" in tabella
        assert tabella.count("—") >= 3


PREFIX = "test_nc_"
ORG = PREFIX + "org"
ALTRA = PREFIX + "altra"


def _user(org_id=ORG):
    return {"id": PREFIX + "u", "email": "nc@example.com",
            "organization_id": org_id, "email_verified": True}


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

    nome_db = f"test_nc_{_uuid.uuid4().hex[:8]}"
    db = client[nome_db]
    import database as db_mod
    for attr, coll in (("customers_collection", db.customers),
                       ("frequency_tracks_collection", db.frequency_tracks),
                       ("sound_shares_collection", db.sound_shares)):
        monkeypatch.setattr(db_mod, attr, coll)
    # il repository lega la collezione all'import: si punta anche lui
    from repositories import customer_repository
    monkeypatch.setattr(customer_repository, "customers_collection",
                        db.customers)

    await db.frequency_tracks.insert_one({
        "id": PREFIX + "traccia", "organization_id": ORG,
        "title": "Riservata di prova", "status": "published",
        "visibility": "private", "score": {"layers": []},
    })

    class Banco:
        clienti = db.customers
        share = db.sound_shares

    try:
        yield Banco()
    finally:
        await client.drop_database(nome_db)
        client.close()


class TestLaCatenaViva:
    @pytest.mark.asyncio
    async def test_04_creato_nel_registro_appare_in_rubrica(self, banco):
        """POST /customers (quello che il bottone chiama) → il
        cliente e' ATTIVO e in lista: la rubrica che ScegliPersona
        legge (stessa api, active_only) lo contiene."""
        from models.customer import CustomerCreate
        from routers import customers as rc
        creato = await rc.create_customer(
            CustomerCreate(name="Marco Dal Registro",
                           email="marco@example.com"),
            current_user=_user())
        assert creato.name == "Marco Dal Registro"
        assert creato.is_active is True
        in_lista = await rc.list_customers(
            active_only=True, limit=200, current_user=_user())
        assert any(c.id == creato.id for c in in_lista)

    @pytest.mark.asyncio
    async def test_05_e_il_foglio_dei_link_lo_accetta(self, banco):
        """La catena intera del founder: creo il cliente dal registro
        e CREO UN LINK RISERVATO per lui — lo share nasce col suo
        nome fotografato."""
        from models.customer import CustomerCreate
        from routers import customers as rc
        from routers import sound_shares as rs
        creato = await rc.create_customer(
            CustomerCreate(name="Marco Dal Registro"),
            current_user=_user())
        share = await rs.crea_condivisione(
            PREFIX + "traccia",
            rs.ShareCreate(contact_id=creato.id),
            current_user=_user())
        assert share["contact_name"] == "Marco Dal Registro"
        assert share["stato"] == "attivo"
        assert len(share["token"]) >= 24
        doc = await banco.share.find_one({"id": share["id"]})
        assert doc and doc["contact_id"] == creato.id

    @pytest.mark.asyncio
    async def test_06_il_contatto_altrui_resta_fuori(self, banco):
        """Isolamento org: un contatto creato in un'ALTRA org non
        puo' ricevere link dalle mie tracce (400, id inventato)."""
        from fastapi import HTTPException
        from models.customer import CustomerCreate
        from routers import customers as rc
        from routers import sound_shares as rs
        altrui = await rc.create_customer(
            CustomerCreate(name="Estraneo"),
            current_user=_user(ALTRA))
        with pytest.raises(HTTPException) as e:
            await rs.crea_condivisione(
                PREFIX + "traccia",
                rs.ShareCreate(contact_id=altrui.id),
                current_user=_user())
        assert e.value.status_code == 400
