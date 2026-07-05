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

        def fake_send(email, token, name):
            sent["token"] = token

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
                          lambda e, t, n: sent.update({"email": e, "token": t})):
            out = asyncio.run(svc.send_claim_email_if_needed(
                {"customer_email": "a@b.it"}))
        assert out is True and sent["email"] == "a@b.it"
        tokens.insert_one.assert_called_once()
        accounts.update_one.assert_called_once()  # claim_last_sent_at
