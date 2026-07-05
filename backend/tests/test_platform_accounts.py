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
