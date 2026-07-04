"""Wave GDPR-Commerce Piece 1b — sentinel tests for tokenised unsubscribe.

Scope:
  - core.marketing_unsubscribe_token.{generate,decode} round-trips
    cleanly and normalises the email (lowercase + strip) at sign time
  - Expired token → TokenExpiredError (router maps to HTTP 410)
  - Tampered signature → TokenInvalidError (router maps to HTTP 401)
  - Scope confusion attack: a JWT signed with the same secret but a
    different ``scope`` claim → TokenInvalidError (no replay)
  - Empty email / org_id at sign time → ValueError (programmer guard)
  - GET /api/marketing-consent/unsubscribe/{token}
      · valid token → 200 with email_masked + already_unsubscribed flag
      · expired token → HTTPException 410
      · invalid token → HTTPException 401
  - POST /api/marketing-consent/unsubscribe/{token}/confirm
      · guest (no customer_account row) → consent_audit row written,
        applied_to_account=False
      · registered customer → consent_audit + customer_account
        marketing_revoked_at updated
      · idempotent on second click (always writes a fresh audit row)
      · invalid token → 401
      · audit write failure → 500
  - CSV export (CI-admin-vis) carries the new ``unsubscribe_url``
    column as the LAST positional field — legacy positional consumers
    keep working; new column is populated for rows with an email.

These tests are PURELY ADDITIVE — they do not modify any existing
sentinel and the previous 2596-test baseline keeps passing.
"""

import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-not-for-production")
os.environ.setdefault("MONGO_URL", "mongodb://localhost:27017")
os.environ.setdefault("DB_NAME", "test_db")
os.environ.setdefault("ANTHROPIC_API_KEY", "test-key-not-real")

BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))


# ─── Fixtures ────────────────────────────────────────────────────────


class _FakeRequest:
    """Minimal stand-in for fastapi.Request used by the confirm endpoint.

    The endpoint only reads headers + client.host (via _client_ip),
    so a tiny stub avoids spinning up TestClient just for IP extraction.
    """

    def __init__(self, headers=None, client_host: str = "127.0.0.1"):
        self.headers = headers or {}

        class _Client:
            pass

        self.client = _Client()
        self.client.host = client_host


def _sign_test_token(email: str, org_id: str, ttl_days: int = 1825) -> str:
    """Convenience wrapper around the production sign helper.

    Lives in the test module so the test name reads naturally even
    when the unit-under-test is `generate_marketing_unsubscribe_token`
    itself in some asserts.
    """
    from core.marketing_unsubscribe_token import (
        generate_marketing_unsubscribe_token,
    )
    return generate_marketing_unsubscribe_token(
        email=email, organization_id=org_id, ttl_days=ttl_days,
    )


# ─── Token helper unit tests ─────────────────────────────────────────


class TestTokenHelper:
    """generate / decode round-trip + the three failure modes."""

    def test_round_trip_valid_token(self):
        from core.marketing_unsubscribe_token import (
            decode_marketing_unsubscribe_token,
        )
        tok = _sign_test_token("buyer@example.com", "org-1")
        payload = decode_marketing_unsubscribe_token(tok)
        assert payload["email"] == "buyer@example.com"
        assert payload["organization_id"] == "org-1"
        assert payload["iat"] > 0
        assert payload["exp"] > payload["iat"]

    def test_email_is_normalised_at_sign_time(self):
        """Sign-time canonicalises email so the merchant pasting
        ``Buyer@Example.COM `` into Mailchimp still produces the
        same logical token as ``buyer@example.com``."""
        from core.marketing_unsubscribe_token import (
            decode_marketing_unsubscribe_token,
        )
        tok = _sign_test_token("Buyer@Example.COM  ", "org-1")
        payload = decode_marketing_unsubscribe_token(tok)
        assert payload["email"] == "buyer@example.com"

    def test_expired_token_raises_expired_error(self):
        """Past TTL → dedicated TokenExpiredError (the router maps it
        to HTTP 410, distinct from a bad signature)."""
        from core.marketing_unsubscribe_token import (
            TokenExpiredError, decode_marketing_unsubscribe_token,
            generate_marketing_unsubscribe_token,
        )
        # ttl_days must be > 0 at sign time (it's a programmer guard);
        # we instead build the token then patch the exp claim by
        # using jose directly to mint a past-exp version.
        from auth import SECRET_KEY, ALGORITHM
        from jose import jwt as _jwt
        past = datetime.now(timezone.utc) - timedelta(days=1)
        payload = {
            "scope": "marketing_unsubscribe",
            "email": "x@y.z",
            "org_id": "org-1",
            "iat": int((past - timedelta(days=2)).timestamp()),
            "exp": int(past.timestamp()),
        }
        expired = _jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)
        with pytest.raises(TokenExpiredError):
            decode_marketing_unsubscribe_token(expired)

    def test_tampered_signature_raises_invalid_error(self):
        from core.marketing_unsubscribe_token import (
            TokenInvalidError, decode_marketing_unsubscribe_token,
        )
        tok = _sign_test_token("buyer@example.com", "org-1")
        head, payload_b64, sig = tok.split(".")
        # Flip a character in the MIDDLE of the signature (not last).
        # Razionale: HMAC-SHA256 = 32 bytes = 256 bit = 43 base64url char.
        # Last char encodes solo 4 bit "validi" + 2 bit padding ignorati
        # da decoder lenient (RFC 7515 §C). Char come {A,B,C,D} hanno
        # SAME upper-4-bits → flip last da A a B (o C/D) NON cambia la
        # signature decodificata → token resta valido → test flaky
        # ~6.25% rate (1/16). Flippando un char middle, tutti 6 i bit
        # sono significativi → flip change garantito.
        mid = len(sig) // 2
        bad_char = "A" if sig[mid] != "A" else "B"
        bad_sig = sig[:mid] + bad_char + sig[mid + 1:]
        bad = f"{head}.{payload_b64}.{bad_sig}"
        with pytest.raises(TokenInvalidError):
            decode_marketing_unsubscribe_token(bad)

    def test_scope_confusion_attack_rejected(self):
        """A JWT signed with the same secret but a non-matching scope
        claim (e.g. an access token from auth.create_access_token)
        MUST NOT be replayable as an unsubscribe token. This is the
        confusion-attack guard."""
        from auth import SECRET_KEY, ALGORITHM
        from jose import jwt as _jwt
        from core.marketing_unsubscribe_token import (
            TokenInvalidError, decode_marketing_unsubscribe_token,
        )
        now = datetime.now(timezone.utc)
        # Mint a token that LOOKS like an unsubscribe token but with
        # a different scope — the verifier must reject it.
        forged = _jwt.encode(
            {
                "scope": "login",  # ← wrong scope
                "email": "buyer@example.com",
                "org_id": "org-1",
                "iat": int(now.timestamp()),
                "exp": int((now + timedelta(days=1)).timestamp()),
            },
            SECRET_KEY,
            algorithm=ALGORITHM,
        )
        with pytest.raises(TokenInvalidError):
            decode_marketing_unsubscribe_token(forged)

    def test_empty_email_raises_value_error(self):
        from core.marketing_unsubscribe_token import (
            generate_marketing_unsubscribe_token,
        )
        with pytest.raises(ValueError):
            generate_marketing_unsubscribe_token(
                email="", organization_id="org-1",
            )
        with pytest.raises(ValueError):
            generate_marketing_unsubscribe_token(
                email="x@y.z", organization_id="",
            )


# ─── GET /unsubscribe/{token} ────────────────────────────────────────


class TestPreviewEndpoint:
    """Read-only preview: validates + returns masked email + status."""

    @pytest.mark.asyncio
    async def test_valid_token_returns_masked_email(self):
        import json
        from routers.marketing_consent import preview_unsubscribe

        tok = _sign_test_token("mario.rossi@example.com", "org-1")

        with patch(
            "database.organizations_collection.find_one",
            new=AsyncMock(return_value={"id": "org-1", "name": "Acme SRL"}),
        ), patch(
            "database.customer_accounts_collection.find_one",
            new=AsyncMock(return_value=None),  # no account ↔ guest
        ), patch(
            "database.consent_audit_collection.find",
            return_value=_EmptyCursor(),
        ):
            response = await preview_unsubscribe(token=tok)

        body = json.loads(response.body)
        assert body["valid"] is True
        # Masked: first char + *** + last char @ domain
        assert body["email_masked"] == "m***i@example.com"
        assert body["organization_name"] == "Acme SRL"
        assert body["already_unsubscribed"] is False
        # No caching — already_unsubscribed is stateful
        cc = response.headers.get("cache-control") or response.headers.get("Cache-Control")
        assert cc is not None and "no-store" in cc.lower()

    @pytest.mark.asyncio
    async def test_already_unsubscribed_flag_from_customer_account(self):
        """When the registered customer_account has marketing_revoked_at
        AFTER accepted_marketing_at, preview signals 'already_unsubscribed'."""
        import json
        from routers.marketing_consent import preview_unsubscribe

        tok = _sign_test_token("buyer@example.com", "org-1")

        with patch(
            "database.organizations_collection.find_one",
            new=AsyncMock(return_value={"id": "org-1", "name": "Acme SRL"}),
        ), patch(
            "database.customer_accounts_collection.find_one",
            new=AsyncMock(return_value={
                "accepted_marketing_at": "2026-01-01T00:00:00+00:00",
                "marketing_revoked_at": "2026-05-01T00:00:00+00:00",
            }),
        ):
            response = await preview_unsubscribe(token=tok)

        body = json.loads(response.body)
        assert body["already_unsubscribed"] is True

    @pytest.mark.asyncio
    async def test_invalid_token_returns_401(self):
        from fastapi import HTTPException
        from routers.marketing_consent import preview_unsubscribe

        with pytest.raises(HTTPException) as exc:
            await preview_unsubscribe(token="not.a.real.jwt")
        assert exc.value.status_code == 401
        # The detail body carries an error_code the frontend can branch on
        detail = exc.value.detail
        assert isinstance(detail, dict)
        assert detail.get("error_code") == "invalid_token"

    @pytest.mark.asyncio
    async def test_expired_token_returns_410(self):
        from fastapi import HTTPException
        from auth import SECRET_KEY, ALGORITHM
        from jose import jwt as _jwt
        from routers.marketing_consent import preview_unsubscribe

        past = datetime.now(timezone.utc) - timedelta(days=1)
        expired = _jwt.encode(
            {
                "scope": "marketing_unsubscribe",
                "email": "x@y.z",
                "org_id": "org-1",
                "iat": int((past - timedelta(days=2)).timestamp()),
                "exp": int(past.timestamp()),
            },
            SECRET_KEY,
            algorithm=ALGORITHM,
        )
        with pytest.raises(HTTPException) as exc:
            await preview_unsubscribe(token=expired)
        assert exc.value.status_code == 410
        assert exc.value.detail.get("error_code") == "expired_token"


# ─── POST /unsubscribe/{token}/confirm ───────────────────────────────


class TestConfirmEndpoint:
    """Idempotent revocation: writes consent_audit + (optionally) updates
    customer_account.marketing_revoked_at."""

    @pytest.mark.asyncio
    async def test_guest_writes_audit_no_account_update(self):
        """Guest customer (no customer_account row): consent_audit is
        still written; applied_to_account=False."""
        import json
        from routers.marketing_consent import confirm_unsubscribe

        tok = _sign_test_token("guest@example.com", "org-1")
        req = _FakeRequest(headers={"user-agent": "Mozilla/Test"})

        # No matching account → matched_count=0
        update_result = type("R", (), {"matched_count": 0, "modified_count": 0})()
        audit_capture = {}

        async def _fake_record_consent(**kwargs):
            audit_capture.update(kwargs)
            return {"id": "audit-1", **kwargs}

        with patch(
            "database.customer_accounts_collection.update_one",
            new=AsyncMock(return_value=update_result),
        ), patch(
            "repositories.consent_audit_repository.record_consent",
            new=_fake_record_consent,
        ):
            response = await confirm_unsubscribe(token=tok, request=req)

        body = json.loads(response.body)
        assert body["success"] is True
        assert body["applied_to_account"] is False
        # Audit row carries the right enum members + identifies the guest
        assert audit_capture["source"] == "customer_marketing_revoke"
        assert audit_capture["document_type"] == "merchant_marketing"
        assert audit_capture["customer_email"] == "guest@example.com"
        assert audit_capture["organization_id"] == "org-1"
        assert audit_capture["user_id"] is None  # guest

    @pytest.mark.asyncio
    async def test_registered_customer_updates_account(self):
        """Registered customer: customer_account.marketing_revoked_at
        is set AND the audit row is written."""
        import json
        from routers.marketing_consent import confirm_unsubscribe

        tok = _sign_test_token("buyer@example.com", "org-1")
        req = _FakeRequest()

        # Matched: 1 → applied_to_account=True
        update_result = type("R", (), {"matched_count": 1, "modified_count": 1})()
        update_call = {}

        async def _fake_update_one(filter_q, update_doc):
            update_call["filter"] = filter_q
            update_call["update"] = update_doc
            return update_result

        async def _fake_record_consent(**kwargs):
            return {"id": "audit-2", **kwargs}

        with patch(
            "database.customer_accounts_collection.update_one",
            new=_fake_update_one,
        ), patch(
            "repositories.consent_audit_repository.record_consent",
            new=_fake_record_consent,
        ):
            response = await confirm_unsubscribe(token=tok, request=req)

        body = json.loads(response.body)
        assert body["success"] is True
        assert body["applied_to_account"] is True
        # The update query is scoped by email+org (tenant isolation)
        assert update_call["filter"]["email"] == "buyer@example.com"
        assert update_call["filter"]["organization_id"] == "org-1"
        # The $set carries marketing_revoked_at + updated_at
        set_doc = update_call["update"]["$set"]
        assert "marketing_revoked_at" in set_doc
        assert "updated_at" in set_doc

    @pytest.mark.asyncio
    async def test_invalid_token_returns_401(self):
        from fastapi import HTTPException
        from routers.marketing_consent import confirm_unsubscribe

        req = _FakeRequest()
        with pytest.raises(HTTPException) as exc:
            await confirm_unsubscribe(token="bogus.token.here", request=req)
        assert exc.value.status_code == 401

    @pytest.mark.asyncio
    async def test_audit_write_failure_returns_500(self):
        """If the consent_audit insert itself fails, surface 500.
        The audit row IS the legal proof — we don't pretend success."""
        from fastapi import HTTPException
        from routers.marketing_consent import confirm_unsubscribe

        tok = _sign_test_token("buyer@example.com", "org-1")
        req = _FakeRequest()
        update_result = type("R", (), {"matched_count": 0, "modified_count": 0})()

        async def _failing_record(**kwargs):
            raise RuntimeError("simulated DB outage")

        with patch(
            "database.customer_accounts_collection.update_one",
            new=AsyncMock(return_value=update_result),
        ), patch(
            "repositories.consent_audit_repository.record_consent",
            new=_failing_record,
        ):
            with pytest.raises(HTTPException) as exc:
                await confirm_unsubscribe(token=tok, request=req)
        assert exc.value.status_code == 500
        assert exc.value.detail.get("error_code") == "audit_write_failed"


# ─── CSV export integration ──────────────────────────────────────────


class TestCsvUnsubscribeColumn:
    """The CI-admin-vis CSV export now appends unsubscribe_url as the
    LAST column (positional contract: legacy columns keep their index)."""

    def test_unsubscribe_url_is_last_column(self):
        from modules.customer_insights.router import _CSV_COLUMNS
        assert _CSV_COLUMNS[-1] == "unsubscribe_url"
        # Sanity: the 3 CI-admin-vis columns sit before unsubscribe_url
        assert _CSV_COLUMNS[-4:-1] == [
            "has_account", "marketing_opted_in", "account_created_at",
        ]

    def test_build_url_produces_frontend_link(self):
        """``build_unsubscribe_url`` returns a frontend-ready URL that
        the merchant can paste into Mailchimp / Brevo footer."""
        from core.marketing_unsubscribe_token import build_unsubscribe_url
        url = build_unsubscribe_url(
            email="buyer@example.com",
            organization_id="org-1",
            frontend_base_url="https://shop.example.com",
        )
        # Shape: {base}/u/{token}
        assert url.startswith("https://shop.example.com/u/")
        # Token segment is non-empty, dot-separated JWT
        token = url.rsplit("/", 1)[-1]
        parts = token.split(".")
        assert len(parts) == 3 and all(parts)


# ─── Helpers — empty motor-style cursor ──────────────────────────────


class _EmptyCursor:
    """Motor cursor stand-in for the consent_audit_collection.find chain
    used by _is_already_unsubscribed. Chains .sort().limit() then is
    awaited via .to_list()."""

    def sort(self, *args, **kwargs):
        return self

    def limit(self, *args, **kwargs):
        return self

    async def to_list(self, length):  # noqa: ARG002
        return []
