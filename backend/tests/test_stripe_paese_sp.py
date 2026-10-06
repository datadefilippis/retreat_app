"""Lotto S (6/10/2026) — il paese dell'account Stripe Express.

La piattaforma Stripe di Aurya e' svizzera e Account.create non passava
`country`: ogni Express nasceva CH (3 in prod, nessuno completato). Da
oggi il paese si sceglie PRIMA (Italia di default) e chi e' nato svizzero
senza volerlo «ricomincia col paese giusto» finche' l'account non ha mai
lavorato. Guardie:

  SP1  creazione: country + default_currency SEMPRE; IT senza TWINT, CH con
       TWINT; paese fuori lista → IT
  SP2  suggerimento dall'org: CHF o sede in Svizzera → CH, altrimenti IT
  SP3  start: paese scelto → scritto nella riga; account esistente → il
       paese non si tocca e non si ricrea nulla
  SP4  ricomincia: rifiutato su account operativi (dati inviati, addebiti,
       pronto, attivo) senza chiamare Stripe; accettato: Account.delete,
       riga archiviata con traccia, nuovo account col paese nuovo
  SP5  complete e webhook salvano country/default_currency dall'account
  SP6  router: body con paese, 400 fuori lista; endpoint paesi e ricomincia
  SP7  superfici: select del paese nella card, riga «registrato in», blocco
       ricomincia, righe archiviate nascoste; copia italiana
"""
from __future__ import annotations

import os
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

os.environ.setdefault("JWT_SECRET_KEY", "test")
os.environ.setdefault("STRIPE_SECRET_KEY", "sk_test_dummy")

BACKEND = Path(__file__).resolve().parents[1]
FRONTEND = BACKEND.parent / "frontend" / "src"
sys.path.insert(0, str(BACKEND))

from services import stripe_connect_express as X  # noqa: E402


def _stripe_finto(account_id="acct_nuovo"):
    fake = MagicMock()
    fake.Account.create = MagicMock(return_value=SimpleNamespace(id=account_id))
    fake.Account.delete = MagicMock(return_value=SimpleNamespace(id=account_id, deleted=True))
    fake.AccountLink.create = MagicMock(return_value=SimpleNamespace(url="https://connect.stripe.com/setup/x"))
    return fake


def _conn(**kw):
    base = {"id": "pc1", "organization_id": "org1", "provider": "stripe", "connect_type": "express",
            "external_account_id": "acct_vecchio", "status": "pending", "runtime_status": "needs_auth",
            "details_submitted": False, "charges_enabled": False, "country": "CH", "metadata": {}}
    base.update(kw)
    return base


# ── SP1 ─────────────────────────────────────────────────────────────────

class TestSP1Creazione:
    @pytest.mark.asyncio
    async def test_italia_senza_twint_con_paese_e_valuta(self):
        fake = _stripe_finto()
        with patch.object(X, "_get_stripe", return_value=fake):
            await X._create_express_account("org1", "a@b.it", country="IT")
        kw = fake.Account.create.call_args.kwargs
        assert kw["country"] == "IT" and kw["default_currency"] == "eur"
        assert set(kw["capabilities"]) == {"card_payments", "transfers"}

    @pytest.mark.asyncio
    async def test_default_e_italia_e_fuori_lista_torna_italia(self):
        fake = _stripe_finto()
        with patch.object(X, "_get_stripe", return_value=fake):
            await X._create_express_account("org1", None)
            await X._create_express_account("org1", None, country="US")
        for call in fake.Account.create.call_args_list:
            assert call.kwargs["country"] == "IT"

    @pytest.mark.asyncio
    async def test_svizzera_con_twint(self):
        fake = _stripe_finto()
        with patch.object(X, "_get_stripe", return_value=fake):
            await X._create_express_account("org1", None, country="ch")
        kw = fake.Account.create.call_args.kwargs
        assert kw["country"] == "CH" and kw["default_currency"] == "chf"
        assert kw["capabilities"]["twint_payments"] == {"requested": True}


# ── SP2 ─────────────────────────────────────────────────────────────────

class TestSP2Suggerimento:
    def test_chf_o_sede_svizzera(self):
        assert X.paese_suggerito({"currency": "CHF"}) == "CH"
        assert X.paese_suggerito({"public_profile": {"sedi": [{"citta": "Lugano", "paese": "Svizzera"}]}}) == "CH"
        assert X.paese_suggerito({"public_profile": {"sedi": [{"citta": "Bari", "paese": "Italia"}]}}) == "IT"
        assert X.paese_suggerito({"public_profile": {"city": "Roma"}}) == "IT"
        assert X.paese_suggerito(None) == "IT"

    def test_paesi_ammessi(self):
        assert X.paese_valido("it") == "IT" and X.paese_valido("CH") == "CH"
        assert X.paese_valido("US") is None and X.paese_valido("") is None and X.paese_valido(None) is None
        assert set(X.PAESI_STRIPE) == set(X.NOMI_PAESI)


# ── SP3 ─────────────────────────────────────────────────────────────────

class TestSP3Start:
    @pytest.mark.asyncio
    async def test_nuovo_account_col_paese_scelto(self):
        coll = MagicMock()
        coll.find_one = AsyncMock(return_value=None)
        coll.insert_one = AsyncMock()
        fake = _stripe_finto("acct_it")
        with patch.object(X, "_get_stripe", return_value=fake), \
             patch.object(X, "is_express_configured", return_value=True), \
             patch("database.payment_connections_collection", coll):
            out = await X.start_express_onboarding("org1", email="a@b.it", country="IT")
        assert out["status"] == "onboarding" and out["country"] == "IT" and out["account_id"] == "acct_it"
        doc = coll.insert_one.call_args.args[0]
        assert doc["country"] == "IT" and doc["default_currency"] == "eur"
        assert fake.Account.create.call_args.kwargs["country"] == "IT"

    @pytest.mark.asyncio
    async def test_account_esistente_non_si_ricrea_e_tiene_il_paese(self):
        coll = MagicMock()
        coll.find_one = AsyncMock(return_value=_conn())
        coll.update_one = AsyncMock()
        fake = _stripe_finto()
        with patch.object(X, "_get_stripe", return_value=fake), \
             patch.object(X, "is_express_configured", return_value=True), \
             patch("database.payment_connections_collection", coll):
            out = await X.start_express_onboarding("org1", country="IT")
        fake.Account.create.assert_not_called()
        assert out["account_id"] == "acct_vecchio" and out["country"] == "CH"
        setto = coll.update_one.call_args.args[1]["$set"]
        assert "country" not in setto, "il paese di un account esistente non si riscrive"

    @pytest.mark.asyncio
    async def test_senza_paese_si_suggerisce_dall_org(self):
        coll = MagicMock()
        coll.find_one = AsyncMock(return_value=None)
        coll.insert_one = AsyncMock()
        orgs = MagicMock()
        orgs.find_one = AsyncMock(return_value={"currency": "CHF"})
        fake = _stripe_finto()
        with patch.object(X, "_get_stripe", return_value=fake), \
             patch.object(X, "is_express_configured", return_value=True), \
             patch("database.payment_connections_collection", coll), \
             patch("database.organizations_collection", orgs):
            out = await X.start_express_onboarding("org1")
        assert out["country"] == "CH"
        assert fake.Account.create.call_args.kwargs["country"] == "CH"


# ── SP4 ─────────────────────────────────────────────────────────────────

class TestSP4Ricomincia:
    def test_regola(self):
        assert X.si_puo_ricominciare(_conn()) is True
        assert X.si_puo_ricominciare(_conn(details_submitted=True)) is False
        assert X.si_puo_ricominciare(_conn(charges_enabled=True)) is False
        assert X.si_puo_ricominciare(_conn(runtime_status="ready")) is False
        assert X.si_puo_ricominciare(_conn(status="active")) is False
        assert X.si_puo_ricominciare(None) is False
        assert X.si_puo_ricominciare(_conn(connect_type="standard")) is False

    @pytest.mark.asyncio
    async def test_rifiutato_su_account_operativo_senza_toccare_stripe(self):
        coll = MagicMock()
        coll.find_one = AsyncMock(return_value=_conn(details_submitted=True))
        fake = _stripe_finto()
        with patch.object(X, "_get_stripe", return_value=fake), \
             patch.object(X, "is_express_configured", return_value=True), \
             patch("database.payment_connections_collection", coll):
            out = await X.ricomincia_express("org1", "IT")
        assert out["status"] == "error" and "operativo" in out["error"]
        fake.Account.delete.assert_not_called()

    @pytest.mark.asyncio
    async def test_paese_fuori_lista_rifiutato(self):
        with patch.object(X, "is_express_configured", return_value=True):
            out = await X.ricomincia_express("org1", "US")
        assert out["status"] == "error" and "Paese" in out["error"]

    @pytest.mark.asyncio
    async def test_accettato_elimina_archivia_e_ricrea(self):
        coll = MagicMock()
        # 1ª find_one: la riga CH da rifare; 2ª (dentro start): nessuna riga viva
        coll.find_one = AsyncMock(side_effect=[_conn(), None])
        coll.update_one = AsyncMock()
        coll.insert_one = AsyncMock()
        fake = _stripe_finto("acct_it_nuovo")
        storia = AsyncMock()
        with patch.object(X, "_get_stripe", return_value=fake), \
             patch.object(X, "is_express_configured", return_value=True), \
             patch("database.payment_connections_collection", coll), \
             patch("services.payment_connection_history.record_transition", storia):
            out = await X.ricomincia_express("org1", "IT", email="a@b.it", actor_user_id="u1")
        fake.Account.delete.assert_called_once_with("acct_vecchio")
        archivio = coll.update_one.call_args_list[0].args[1]["$set"]
        assert archivio["archived"] is True and archivio["status"] == "disconnected" and archivio["is_default"] is False
        assert archivio["metadata"]["ricomincia"] == {
            **archivio["metadata"]["ricomincia"], "da": "CH", "a": "IT", "account_eliminato": True}
        assert fake.Account.create.call_args.kwargs["country"] == "IT"
        nuovo = coll.insert_one.call_args.args[0]
        assert nuovo["country"] == "IT" and nuovo["external_account_id"] == "acct_it_nuovo"
        assert out["status"] == "onboarding" and out["country"] == "IT"
        eventi = [c.kwargs["event"] for c in storia.call_args_list]
        assert X.EVENT_RICOMINCIATO in eventi

    @pytest.mark.asyncio
    async def test_account_gia_sparito_su_stripe_si_va_avanti(self):
        coll = MagicMock()
        coll.find_one = AsyncMock(side_effect=[_conn(), None])
        coll.update_one = AsyncMock()
        coll.insert_one = AsyncMock()
        fake = _stripe_finto()
        fake.Account.delete = MagicMock(side_effect=Exception("No such account: acct_vecchio"))
        with patch.object(X, "_get_stripe", return_value=fake), \
             patch.object(X, "is_express_configured", return_value=True), \
             patch("database.payment_connections_collection", coll):
            out = await X.ricomincia_express("org1", "IT")
        assert out["status"] == "onboarding"
        assert coll.update_one.call_args_list[0].args[1]["$set"]["metadata"]["ricomincia"]["account_eliminato"] is False


# ── SP5 ─────────────────────────────────────────────────────────────────

class TestSP5PaeseDaStripe:
    def test_helper(self):
        assert X._paese_e_valuta({"country": "it", "default_currency": "EUR"}) == {"country": "IT", "default_currency": "eur"}
        assert X._paese_e_valuta({}) == {}
        assert X._paese_e_valuta(SimpleNamespace(country="CH", default_currency="chf")) == {"country": "CH", "default_currency": "chf"}

    @pytest.mark.asyncio
    async def test_webhook_scrive_il_paese(self):
        coll = MagicMock()
        coll.find_one = AsyncMock(return_value=_conn(country=None))
        coll.update_one = AsyncMock()
        evento = {"id": "evt_1", "data": {"object": {"id": "acct_vecchio", "country": "IT", "default_currency": "eur",
                                                      "charges_enabled": False, "payouts_enabled": False,
                                                      "details_submitted": False, "requirements": {"currently_due": []}}}}
        with patch("database.payment_connections_collection", coll):
            out = await X.handle_account_updated(evento)
        assert out["status"] == "processed"
        setto = coll.update_one.call_args.args[1]["$set"]
        assert setto["country"] == "IT" and setto["default_currency"] == "eur"

    def test_complete_usa_lo_stesso_helper(self):
        src = (BACKEND / "services" / "stripe_connect_express.py").read_text()
        corpo = src[src.index("async def complete_express_onboarding("):src.index("async def handle_account_updated(")]
        assert "**_paese_e_valuta(account)" in corpo


# ── SP6 ─────────────────────────────────────────────────────────────────

class TestSP6Router:
    def test_endpoint_e_body(self):
        src = (BACKEND / "routers" / "payment_connections.py").read_text()
        assert '@router.post("/stripe/express/ricomincia")' in src
        assert '@router.get("/stripe/express/paesi")' in src
        assert "class ExpressStartBody" in src
        assert "start_express_onboarding(org_id, email=email, country=country)" in src
        assert "Paese non ammesso" in src

    def test_modello_con_paese(self):
        from models.payment_connection import PaymentConnection
        pc = PaymentConnection(organization_id="o", country="IT", default_currency="eur")
        assert pc.country == "IT"
        assert PaymentConnection(organization_id="o").country is None


# ── SP7 ─────────────────────────────────────────────────────────────────

class TestSP7Superfici:
    def test_card(self):
        c = (FRONTEND / "features" / "settings" / "PaymentConnectionsCard.js").read_text()
        for frag in ('data-testid="pc-paese-select"', "expressStart({ country: paese })", 'data-testid="pc-ricomincia"',
                     "expressRicomincia({ country: paeseNuovo })", "!conn.details_submitted && !conn.charges_enabled",
                     "connections.filter(c => !c.archived)", 'data-testid="pc-paese"'):
            assert frag in c, frag

    def test_api_e_copia(self):
        a = (FRONTEND / "api" / "paymentConnections.js").read_text()
        assert "/payment-connections/stripe/express/ricomincia" in a and "/payment-connections/stripe/express/paesi" in a
        import json
        pay = json.loads((FRONTEND / "locales" / "it" / "settings.json").read_text())["payments"]
        assert pay["ricomincia_btn"] == "Ricomincia col paese giusto"
        assert pay["connect_stripe"] == "Collega gli incassi con Stripe"
        assert "needs_auth" not in pay["runtime_needs_auth"]
