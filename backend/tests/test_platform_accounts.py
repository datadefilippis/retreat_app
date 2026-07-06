"""P1 platform accounts — magic link, isolamento token, enumeration-safety.

Piano: docs/PLATFORM_ACCOUNT_PLAN.md. Le garanzie che questi test bloccano:
  - un token customer/admin NON entra dagli endpoint piattaforma (e viceversa)
  - il token magic e' salvato SOLO hashed, one-shot atomico, TTL
  - la richiesta magic-link non permette enumeration
  - feature flag: modulo spegnibile senza toccare il resto
"""

import asyncio
import os
import sys
from pathlib import Path
from unittest.mock import AsyncMock, patch

BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-not-for-production")
os.environ.setdefault("MONGO_URL", "mongodb://localhost:27017")
os.environ.setdefault("DB_NAME", "test_db")

import pytest
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials

from auth import (
    create_customer_token,
    create_platform_token,
    decode_token,
    get_current_platform_account,
)
from services import platform_account_service as svc


def _creds(token: str) -> HTTPAuthorizationCredentials:
    return HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)


class TestTokenIsolation:
    def test_platform_token_has_platform_type(self):
        t = create_platform_token({"sub": "acc-1", "email": "a@b.it"})
        assert decode_token(t)["type"] == "platform"

    def test_customer_token_rejected_by_platform_dependency(self):
        t = create_customer_token({"sub": "acc-1", "org_id": "org-1",
                                   "email": "a@b.it"})
        with pytest.raises(HTTPException) as exc:
            asyncio.run(get_current_platform_account(_creds(t)))
        assert exc.value.status_code == 401

    def test_platform_token_rejected_by_customer_dependency(self):
        from auth import get_current_customer
        t = create_platform_token({"sub": "acc-1", "email": "a@b.it"})
        with pytest.raises(HTTPException) as exc:
            asyncio.run(get_current_customer(_creds(t)))
        assert exc.value.status_code == 401

    def test_platform_token_rejected_by_admin_dependency_source(self):
        # get_current_user (admin/operatore) non deve mai accettare
        # type=platform: verifica che il payload non abbia i claim attesi
        t = create_platform_token({"sub": "acc-1", "email": "a@b.it"})
        payload = decode_token(t)
        assert payload.get("type") == "platform"
        assert "org_id" not in payload      # mai un tenant nel token piattaforma


class TestMagicLinkService:
    def test_email_normalized(self):
        assert svc._normalize_email("  Mario@EXAMPLE.com ") == "mario@example.com"

    def test_token_stored_only_hashed(self):
        inserted = {}

        async def fake_insert(doc):
            inserted.update(doc)

        sent = {}

        def fake_send(email, token, name, code=None, locale="it"):  # R2a: nuovo kwarg
            sent["token"] = token
            sent["code"] = code

        accounts = AsyncMock()
        accounts.find_one = AsyncMock(return_value={"id": "acc-1",
                                                    "email": "a@b.it"})
        tokens = AsyncMock()
        tokens.insert_one = AsyncMock(side_effect=fake_insert)

        with patch("database.platform_accounts_collection", accounts), \
             patch("database.platform_magic_tokens_collection", tokens), \
             patch.object(svc, "_send_magic_link_email", fake_send):
            asyncio.run(svc.request_magic_link("a@b.it"))

        assert sent["token"]                       # in chiaro solo nell'email
        assert inserted["token_hash"] == svc._hash_token(sent["token"])
        assert sent["token"] not in str(inserted)  # MAI in chiaro a DB
        # OTP: 6 cifre, in chiaro solo nell'email, a DB solo l'hash
        assert sent["code"] and len(sent["code"]) == 6 and sent["code"].isdigit()
        assert inserted["code_hash"] == svc._hash_token(sent["code"])
        assert sent["code"] not in str(inserted)

    def test_invalid_email_is_silent_noop(self):
        accounts = AsyncMock()
        with patch("database.platform_accounts_collection", accounts):
            asyncio.run(svc.request_magic_link("not-an-email"))
        accounts.find_one.assert_not_called()      # nessuna query → nessun segnale

    def test_consume_invalid_token_returns_none(self):
        tokens = AsyncMock()
        tokens.find_one_and_update = AsyncMock(return_value=None)
        with patch("database.platform_magic_tokens_collection", tokens):
            out = asyncio.run(svc.consume_magic_link("garbage"))
        assert out is None

    def test_consume_is_atomic_one_shot(self):
        # Il filtro DEVE includere used_at=None e la scadenza: e' quello
        # che rende il consumo one-shot anche sotto richieste concorrenti.
        captured = {}

        async def fake_fau(filt, update):
            captured.update(filt)
            return None

        tokens = AsyncMock()
        tokens.find_one_and_update = AsyncMock(side_effect=fake_fau)
        with patch("database.platform_magic_tokens_collection", tokens):
            asyncio.run(svc.consume_magic_link("tok"))
        assert captured["used_at"] is None
        assert "$gt" in captured["expires_at"]


class TestFeatureFlag:
    def test_flag_off_returns_404(self):
        from routers.platform_accounts import _flag_enabled
        os.environ["PLATFORM_ACCOUNTS_ENABLED"] = "false"
        try:
            with pytest.raises(HTTPException) as exc:
                _flag_enabled()
            assert exc.value.status_code == 404
        finally:
            os.environ.pop("PLATFORM_ACCOUNTS_ENABLED", None)

    def test_flag_default_on(self):
        from routers.platform_accounts import _flag_enabled
        os.environ.pop("PLATFORM_ACCOUNTS_ENABLED", None)
        _flag_enabled()   # nessuna eccezione


class TestP2OrderLinking:
    """P2 — stamp additivo su ordini + link CRM org. DoD: stessa email
    su DUE operatori diversi → UN solo platform account."""

    @staticmethod
    def _run_link(order, org_id, existing_account=None):
        captured = {"order_updates": [], "cust_updates": [], "inserted": None}

        accounts = AsyncMock()
        accounts.find_one = AsyncMock(return_value=existing_account)
        async def _ins(doc): captured["inserted"] = doc
        accounts.insert_one = AsyncMock(side_effect=_ins)

        orders = AsyncMock()
        async def _ou(f, u): captured["order_updates"].append((f, u))
        orders.update_one = AsyncMock(side_effect=_ou)

        customers = AsyncMock()
        async def _cu(f, u): captured["cust_updates"].append((f, u))
        customers.update_many = AsyncMock(side_effect=_cu)

        with patch("database.platform_accounts_collection", accounts), \
             patch("database.orders_collection", orders), \
             patch("database.customer_accounts_collection", customers):
            out = asyncio.run(svc.link_order_to_platform_account(order, org_id))
        return out, captured

    def test_same_email_two_orgs_one_account(self):
        # primo acquisto org A: account creato
        order_a = {"id": "ord-A", "customer_email": "Anna@Mail.IT",
                   "customer_name": "Anna"}
        aid, cap_a = self._run_link(order_a, "org-A")
        assert cap_a["inserted"]["email"] == "anna@mail.it"
        assert aid == cap_a["inserted"]["id"]

        # secondo acquisto org B, stessa email: NESSUN nuovo account
        existing = {"id": aid, "email": "anna@mail.it"}
        order_b = {"id": "ord-B", "customer_email": "anna@mail.it"}
        aid_b, cap_b = self._run_link(order_b, "org-B", existing_account=existing)
        assert aid_b == aid                      # stessa identita'
        assert cap_b["inserted"] is None         # niente doppioni

    def test_stamp_is_additive_and_never_overwrites(self):
        existing = {"id": "acc-1", "email": "a@b.it"}
        _, cap = self._run_link({"id": "o1", "customer_email": "a@b.it"},
                                "org-X", existing_account=existing)
        f_order, _ = cap["order_updates"][0]
        assert f_order["platform_account_id"] == {"$exists": False}
        f_cust, _ = cap["cust_updates"][0]
        assert f_cust["platform_account_id"] == {"$exists": False}

    def test_no_email_is_noop(self):
        out, cap = self._run_link({"id": "o1", "customer_email": ""}, "org-X")
        assert out is None and not cap["order_updates"]

    def test_hooks_are_best_effort_in_source(self):
        # I chiamanti DEVONO avvolgere in try/except: il Passaporto non
        # blocca mai un ordine ne' un incasso.
        import os
        for fname, marker in [
            ("services/order_creation_service.py", "link_order_to_platform_account"),
            ("services/payment_checkout_service.py", "send_claim_email_if_needed"),
        ]:
            src = open(os.path.join(os.path.dirname(__file__), "..", fname)).read()
            i = src.index(marker)
            assert "try:" in src[max(0, i-500):i], fname


class TestP2ClaimEmail:
    def test_verified_account_gets_no_claim_email(self):
        accounts = AsyncMock()
        accounts.find_one = AsyncMock(return_value={"id": "a1",
                                                    "email_verified": True})
        with patch("database.platform_accounts_collection", accounts):
            out = asyncio.run(svc.send_claim_email_if_needed(
                {"customer_email": "a@b.it"}))
        assert out is False

    def test_cooldown_blocks_repeat_within_24h(self):
        from models.common import utc_now
        accounts = AsyncMock()
        accounts.find_one = AsyncMock(return_value={
            "id": "a1", "email_verified": False,
            "claim_last_sent_at": utc_now().isoformat()})
        with patch("database.platform_accounts_collection", accounts):
            out = asyncio.run(svc.send_claim_email_if_needed(
                {"customer_email": "a@b.it"}))
        assert out is False

    def test_unverified_account_gets_email_and_timestamp(self):
        accounts = AsyncMock()
        accounts.find_one = AsyncMock(return_value={
            "id": "a1", "email": "a@b.it", "email_verified": False})
        accounts.update_one = AsyncMock()
        tokens = AsyncMock()
        tokens.insert_one = AsyncMock()
        sent = {}
        with patch("database.platform_accounts_collection", accounts), \
             patch("database.platform_magic_tokens_collection", tokens), \
             patch.object(svc, "_send_claim_email",
                          lambda e, t, n, locale="it": sent.update({"email": e, "token": t})):
            out = asyncio.run(svc.send_claim_email_if_needed(
                {"customer_email": "a@b.it"}))
        assert out is True and sent["email"] == "a@b.it"
        tokens.insert_one.assert_called_once()
        accounts.update_one.assert_called_once()  # claim_last_sent_at


class TestP3AccountArea:
    """P3 — /platform/me/orders: solo dati lato-cliente, pay link solo
    su righe pagabili, stati allineati al motore /pay."""

    def _endpoint_src(self):
        import os
        path = os.path.join(os.path.dirname(__file__), "..",
                            "routers", "platform_accounts.py")
        src = open(path).read()
        i = src.index('@router.get("/me/orders")')
        return src[i:i + 4000]

    def test_no_internal_fields_exposed(self):
        block = self._endpoint_src()
        # mai esporre dati interni operatore o fee piattaforma
        for banned in ("cost_price", "application_fee", "notes",
                       "internal", "customer_id"):
            assert f'"{banned}"' not in block, banned

    def test_payable_states_come_from_engine(self):
        # fonte di verita' unica: PAYABLE_STATES del motore /pay —
        # niente liste duplicate che divergono
        import os
        path = os.path.join(os.path.dirname(__file__), "..",
                            "routers", "platform_accounts.py")
        src = open(path).read()
        assert "from services.payment_schedule_service import PAYABLE_STATES" in src

    def test_cancelled_orders_excluded(self):
        block = self._endpoint_src()
        assert '"$ne": "cancelled"' in block

    def test_voided_tickets_excluded(self):
        block = self._endpoint_src()
        assert '"$ne": "voided"' in block


class TestP4RetroactiveClaim:
    def test_claim_links_accounts_and_orders_additively(self):
        calls = {}
        cust_acc = AsyncMock()
        async def _ca(f, u): calls["cust"] = f; return type("R", (), {"modified_count": 2})()
        cust_acc.update_many = AsyncMock(side_effect=_ca)

        class _Cursor:
            def __init__(self, docs): self._docs = docs
            def __aiter__(self): return self._gen()
            async def _gen(self):
                for d in self._docs: yield d
        customers = AsyncMock()
        customers.find = lambda *a, **k: _Cursor([{"id": "crm-1"}, {"id": "crm-2"}])

        orders = AsyncMock()
        async def _om(f, u): calls["orders"] = f; return type("R", (), {"modified_count": 3})()
        orders.update_many = AsyncMock(side_effect=_om)

        with patch("database.customer_accounts_collection", cust_acc), \
             patch("database.customers_collection", customers), \
             patch("database.orders_collection", orders):
            out = asyncio.run(svc.retroactive_claim(
                {"id": "acc-1", "email": "anna@mail.it"}))

        assert out == {"customer_accounts": 2, "orders": 3}
        # additivo: mai sovrascrivere link esistenti
        assert calls["cust"]["platform_account_id"] == {"$exists": False}
        assert calls["orders"]["platform_account_id"] == {"$exists": False}
        assert calls["orders"]["customer_id"] == {"$in": ["crm-1", "crm-2"]}

    def test_claim_is_best_effort_in_consume(self):
        import os
        path = os.path.join(os.path.dirname(__file__), "..",
                            "services", "platform_account_service.py")
        src = open(path).read()
        i = src.index("await retroactive_claim(account)")
        assert "try:" in src[max(0, i-300):i]


class TestP4Gdpr:
    def test_delete_unlinks_but_never_deletes_operator_data(self):
        orders = AsyncMock()
        captured = {}
        async def _om(f, u): captured["orders_update"] = u; return type("R", (), {"modified_count": 1})()
        orders.update_many = AsyncMock(side_effect=_om)
        orders.delete_many = AsyncMock()   # NON deve mai essere chiamata
        cust = AsyncMock()
        cust.update_many = AsyncMock(return_value=type("R", (), {"modified_count": 1})())
        cust.delete_many = AsyncMock()
        pa = AsyncMock(); pa.delete_one = AsyncMock()
        tok = AsyncMock(); tok.delete_many = AsyncMock()

        with patch("database.orders_collection", orders), \
             patch("database.customer_accounts_collection", cust), \
             patch("database.platform_accounts_collection", pa), \
             patch("database.platform_magic_tokens_collection", tok):
            out = asyncio.run(svc.delete_account({"id": "acc-1"}))

        assert "$unset" in captured["orders_update"]     # scollega, non cancella
        orders.delete_many.assert_not_called()           # MAI dati operatore
        cust.delete_many.assert_not_called()
        pa.delete_one.assert_called_once()               # identita' via
        tok.delete_many.assert_called_once()             # token via
        assert out["orders_unlinked"] == 1

    def test_export_contains_no_operator_internals(self):
        import os
        path = os.path.join(os.path.dirname(__file__), "..",
                            "services", "platform_account_service.py")
        src = open(path).read()
        i = src.index("async def export_account_data")
        block = src[i:i + 1500]
        for banned in ("cost_price", "application_fee", "notes"):
            assert banned not in block


class TestP4CrossOrgIsolation:
    def test_me_orders_filters_by_platform_account_only(self):
        # L'aggregazione DEVE filtrare per platform_account_id
        # dell'account autenticato: nessun parametro utente puo'
        # allargare il filtro (niente org_id/email dal client).
        import os
        path = os.path.join(os.path.dirname(__file__), "..",
                            "routers", "platform_accounts.py")
        src = open(path).read()
        i = src.index('@router.get("/me/orders")')
        block = src[i:i + 1500]
        assert '"platform_account_id": account["id"]' in block


class TestLoginCode:
    """OTP a 6 cifre (9/7): la strada immediata; il link resta fallback."""

    def _run_verify(self, *, find_update_result, email="a@b.it", code="123456",
                    account={"id": "acc-1", "email": "a@b.it", "is_active": True}):
        accounts = AsyncMock()
        accounts.find_one = AsyncMock(return_value=account)
        accounts.update_one = AsyncMock()
        tokens = AsyncMock()
        tokens.find_one_and_update = AsyncMock(return_value=find_update_result)
        tokens.update_one = AsyncMock()
        with patch("database.platform_accounts_collection", accounts), \
             patch("database.platform_magic_tokens_collection", tokens), \
             patch.object(svc, "retroactive_claim", AsyncMock()):
            out = asyncio.run(svc.verify_login_code(email, code))
        return out, tokens

    def test_codice_valido_logga(self):
        out, tokens = self._run_verify(
            find_update_result={"account_id": "acc-1"})
        assert out and out["id"] == "acc-1"
        # il match atomico include one-shot + tentativi + scadenza
        q = tokens.find_one_and_update.call_args[0][0]
        assert q["used_at"] is None
        assert q["code_attempts"] == {"$lt": 5}
        assert "expires_at" in q

    def test_codice_sbagliato_brucia_un_tentativo(self):
        out, tokens = self._run_verify(find_update_result=None)
        assert out is None
        upd = tokens.update_one.call_args[0][1]
        assert upd == {"$inc": {"code_attempts": 1}}

    def test_input_malformato_scartato_senza_db(self):
        for bad in ("", "12345", "abcdef", "1234567"):
            accounts = AsyncMock()
            with patch("database.platform_accounts_collection", accounts):
                out = asyncio.run(svc.verify_login_code("a@b.it", bad))
            assert out is None
            accounts.find_one.assert_not_called()
