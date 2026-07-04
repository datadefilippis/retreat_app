"""Wave GDPR-Commerce Phase CG-4 — sentinel tests for customer signup
consent capture and the re-consent flow.

Scope:
  - CustomerAccount model carries the new Optional consent snapshot
    fields (terms/privacy/marketing) without breaking legacy
    deserialization
  - CustomerAccountResponse exposes the snapshot + computed
    ``consent_needs_refresh`` so the customer portal can drive the
    blocking re-consent modal
  - customer_signup REJECTS signup with 400 when:
      a) accepted_terms is False
      b) accepted_privacy is False
      c) the merchant has not published their legal docs yet
  - customer_signup SUCCEEDS when both flags are True AND the
    merchant has published: the customer doc carries the snapshot,
    2-3 audit records are written (privacy + terms + optional
    marketing) with source="customer_signup" / "customer_marketing_optin"
    and document_type="merchant_privacy"/"merchant_terms"/"merchant_marketing"
  - GET /customer/me surfaces consent_needs_refresh correctly:
      · matches current version → False
      · accepted version is stale → True
      · legacy account without accepted version → True
  - POST /customer/me/re-consent records new audit + updates the
    customer doc; idempotent in the sense that multiple acceptances
    are recorded but the modal stops appearing
  - Router wiring: /customer/me/re-consent is registered
"""

import os
import sys
from datetime import datetime, timezone
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


def _store_published() -> dict:
    """Store with a fully published legal bundle (IT display)."""
    from services.merchant_legal_versioning import compute_legal_hash
    s = {
        "id": "store-1",
        "organization_id": "org-1",
        "slug": "acme",
        "name": "Acme Store",
        "is_published": True,
        "is_active": True,
        "visibility": "public",
        "storefront_languages": ["it"],
        "merchant_legal_display_locale": "it",
        "merchant_privacy_content_it": "# Privacy IT v1",
        "merchant_terms_content_it": "# Terms IT v1",
        "merchant_legal_published_at": "2026-05-18T10:00:00+00:00",
        "merchant_legal_last_edited_at": "2026-05-18T09:00:00+00:00",
        "merchant_legal_version_tag": "v1.0",
    }
    s["merchant_legal_version_hash"] = compute_legal_hash(s)
    return s


def _store_not_configured() -> dict:
    return {
        "id": "store-1",
        "organization_id": "org-1",
        "slug": "acme",
        "name": "Acme Store",
        "is_published": True,
        "is_active": True,
        "visibility": "public",
        "storefront_languages": ["it"],
    }


# ─── CustomerAccount model ───────────────────────────────────────────


class TestCustomerAccountModelFields:
    def test_has_new_consent_fields_default_none(self):
        from models.customer_account import CustomerAccount

        a = CustomerAccount(
            organization_id="org-1",
            email="x@example.com",
            name="X",
            password_hash="hash",
        )
        for field in (
            "accepted_store_terms_version",
            "accepted_store_terms_locale",
            "accepted_store_terms_at",
            "accepted_store_privacy_version",
            "accepted_store_privacy_locale",
            "accepted_store_privacy_at",
            "accepted_marketing_at",
            "marketing_revoked_at",
        ):
            assert hasattr(a, field)
            assert getattr(a, field) is None

    def test_accepts_explicit_consent_block(self):
        from models.customer_account import CustomerAccount

        a = CustomerAccount(
            organization_id="org-1",
            email="x@example.com",
            name="X",
            password_hash="hash",
            accepted_store_terms_version="v1.0:abc",
            accepted_store_terms_locale="it",
            accepted_store_terms_at="2026-05-18T10:00:00+00:00",
            accepted_store_privacy_version="v1.0:abc",
            accepted_store_privacy_locale="it",
            accepted_store_privacy_at="2026-05-18T10:00:00+00:00",
            accepted_marketing_at="2026-05-18T10:00:00+00:00",
        )
        assert a.accepted_store_terms_version == "v1.0:abc"
        assert a.accepted_marketing_at is not None


class TestCustomerAccountResponseFields:
    def test_response_has_consent_needs_refresh(self):
        from datetime import datetime
        from models.customer_account import CustomerAccountResponse

        r = CustomerAccountResponse(
            id="c-1",
            organization_id="org-1",
            email="x@example.com",
            name="X",
            is_active=True,
            email_verified=True,
            locale="it",
            created_at=datetime.now(timezone.utc),
        )
        assert hasattr(r, "consent_needs_refresh")
        assert r.consent_needs_refresh is False  # default safe
        assert r.accepted_store_terms_version is None


# ─── customer_signup: enforcement of consent flags ──────────────────


class TestCustomerSignupConsentEnforcement:
    @pytest.mark.asyncio
    async def test_signup_rejects_missing_terms(self):
        from services import customer_auth_service

        with pytest.raises(ValueError, match="Termini"):
            await customer_auth_service.customer_signup(
                org_id="org-1",
                email="x@example.com",
                name="X",
                password="StrongPass12",
                signup_slug="acme",
                accepted_terms=False,
                accepted_privacy=True,
            )

    @pytest.mark.asyncio
    async def test_signup_rejects_missing_privacy(self):
        from services import customer_auth_service

        with pytest.raises(ValueError, match="Privacy"):
            await customer_auth_service.customer_signup(
                org_id="org-1",
                email="x@example.com",
                name="X",
                password="StrongPass12",
                signup_slug="acme",
                accepted_terms=True,
                accepted_privacy=False,
            )

    @pytest.mark.asyncio
    async def test_signup_rejects_when_merchant_not_published(self):
        """If the merchant has not yet published their legal docs,
        signup is REJECTED with 400 — we cannot lawfully capture
        acceptance of a non-existent document."""
        from services import customer_auth_service

        with patch(
            "services.customer_auth_service.customer_account_repository.find_by_email",
            new=AsyncMock(return_value=None),
        ), patch(
            "database.stores_collection.find_one",
            new=AsyncMock(return_value=_store_not_configured()),
        ):
            with pytest.raises(ValueError, match="legale|pubblicato"):
                await customer_auth_service.customer_signup(
                    org_id="org-1",
                    email="x@example.com",
                    name="X",
                    password="StrongPass12",
                    signup_slug="acme",
                    accepted_terms=True,
                    accepted_privacy=True,
                )

    @pytest.mark.asyncio
    async def test_signup_rejects_when_store_not_found(self):
        from services import customer_auth_service

        with patch(
            "services.customer_auth_service.customer_account_repository.find_by_email",
            new=AsyncMock(return_value=None),
        ), patch(
            "database.stores_collection.find_one",
            new=AsyncMock(return_value=None),  # no store
        ):
            with pytest.raises(ValueError, match="legale|venditore"):
                await customer_auth_service.customer_signup(
                    org_id="org-1",
                    email="x@example.com",
                    name="X",
                    password="StrongPass12",
                    signup_slug="acme",
                    accepted_terms=True,
                    accepted_privacy=True,
                )


# ─── customer_signup: success path persists consent snapshot ────────


class TestCustomerSignupSuccess:
    @pytest.mark.asyncio
    async def test_signup_writes_audit_for_privacy_terms(self):
        """Two audit records are written on every successful signup
        (privacy + terms). Marketing record only when accepted."""
        from services import customer_auth_service

        captured_audit_calls = []
        captured_account = {}

        async def _fake_record(**kwargs):
            captured_audit_calls.append(kwargs)
            return {"id": f"audit-{len(captured_audit_calls)}", **kwargs}

        async def _fake_create(doc):
            captured_account.update(doc)
            return doc

        async def _fake_link(*a, **kw):
            return None

        with patch(
            "services.customer_auth_service.customer_account_repository.find_by_email",
            new=AsyncMock(return_value=None),
        ), patch(
            "services.customer_auth_service.customer_account_repository.create",
            new=_fake_create,
        ), patch(
            "services.customer_auth_service._link_account_to_existing_customers",
            new=_fake_link,
        ), patch(
            "database.stores_collection.find_one",
            new=AsyncMock(return_value=_store_published()),
        ), patch(
            "repositories.consent_audit_repository.record_consent",
            new=_fake_record,
        ), patch(
            # The signup path also tries to send a welcome email. Stub
            # that out so the test doesn't depend on email infra.
            "services.customer_auth_service._load_email_context",
            new=AsyncMock(return_value={
                "sender_name": "",
                "reply_to": "",
                "store_name": "",
            }),
        ), patch(
            "services.customer_auth_service.resolve_slug_for_org",
            new=AsyncMock(return_value="acme"),
        ), patch(
            "services.customer_auth_service.send_customer_welcome",
            new=lambda *a, **kw: None,
        ):
            result = await customer_auth_service.customer_signup(
                org_id="org-1",
                email="newuser@example.com",
                name="New User",
                password="StrongPass12",
                signup_slug="acme",
                accepted_terms=True,
                accepted_privacy=True,
                accepted_marketing=False,
                request_ip="9.9.9.9",
                user_agent="pytest/0",
            )

        assert result["status"] == "verification_required"
        # Customer doc carries snapshot
        assert captured_account["accepted_store_terms_version"].startswith("v1.0:")
        assert captured_account["accepted_store_terms_locale"] == "it"
        assert captured_account["accepted_marketing_at"] is None
        # Two audit records — no marketing
        assert len(captured_audit_calls) == 2
        sources = [c["source"] for c in captured_audit_calls]
        doc_types = [c["document_type"] for c in captured_audit_calls]
        assert sources == ["customer_signup", "customer_signup"]
        assert set(doc_types) == {"merchant_privacy", "merchant_terms"}
        # IP + UA captured
        assert captured_audit_calls[0]["ip_address"] == "9.9.9.9"
        assert captured_audit_calls[0]["user_agent"] == "pytest/0"
        # Store scope present
        assert captured_audit_calls[0]["store_id"] == "store-1"

    @pytest.mark.asyncio
    async def test_signup_writes_third_audit_when_marketing_accepted(self):
        from services import customer_auth_service

        captured = []

        async def _fake_record(**kwargs):
            captured.append(kwargs)

        with patch(
            "services.customer_auth_service.customer_account_repository.find_by_email",
            new=AsyncMock(return_value=None),
        ), patch(
            "services.customer_auth_service.customer_account_repository.create",
            new=AsyncMock(),
        ), patch(
            "services.customer_auth_service._link_account_to_existing_customers",
            new=AsyncMock(),
        ), patch(
            "database.stores_collection.find_one",
            new=AsyncMock(return_value=_store_published()),
        ), patch(
            "repositories.consent_audit_repository.record_consent",
            new=_fake_record,
        ), patch(
            "services.customer_auth_service._load_email_context",
            new=AsyncMock(return_value={
                "sender_name": "", "reply_to": "", "store_name": "",
            }),
        ), patch(
            "services.customer_auth_service.resolve_slug_for_org",
            new=AsyncMock(return_value="acme"),
        ), patch(
            "services.customer_auth_service.send_customer_welcome",
            new=lambda *a, **kw: None,
        ):
            await customer_auth_service.customer_signup(
                org_id="org-1",
                email="newuser2@example.com",
                name="N",
                password="StrongPass12",
                signup_slug="acme",
                accepted_terms=True,
                accepted_privacy=True,
                accepted_marketing=True,
            )

        assert len(captured) == 3
        sources = [c["source"] for c in captured]
        assert "customer_marketing_optin" in sources
        # Marketing record references merchant_marketing doc type
        marketing_record = next(
            c for c in captured
            if c["source"] == "customer_marketing_optin"
        )
        assert marketing_record["document_type"] == "merchant_marketing"


# ─── GET /customer/me: consent_needs_refresh logic ───────────────────


class TestCustomerMeConsentRefresh:
    """The /customer/me endpoint computes consent_needs_refresh by
    comparing the customer's snapshot against the live store version."""

    @pytest.mark.asyncio
    async def test_matching_version_no_refresh(self):
        from routers.customer_portal import get_me
        from services.merchant_legal_versioning import current_version_string

        store = _store_published()
        live_version = current_version_string(store)

        account = {
            "id": "c-1",
            "email": "x@example.com",
            "name": "X",
            "organization_id": "org-1",
            "locale": "it",
            "email_verified": True,
            "created_at": "2026-05-18T10:00:00+00:00",
            "signup_slug": "acme",
            "accepted_store_terms_version": live_version,
            "accepted_store_privacy_version": live_version,
        }

        with patch(
            "repositories.customer_account_repository.find_by_id",
            new=AsyncMock(return_value=account),
        ), patch(
            "routers.customer_portal.organizations_collection.find_one",
            new=AsyncMock(return_value={"name": "Acme", "public_slug": "acme"}),
        ), patch(
            "database.stores_collection.find_one",
            new=AsyncMock(return_value=store),
        ):
            res = await get_me(current_customer={
                "customer_account_id": "c-1",
                "organization_id": "org-1",
            })

        assert res["consent_needs_refresh"] is False
        assert res["current_store_legal_version"] == live_version

    @pytest.mark.asyncio
    async def test_stale_version_triggers_refresh(self):
        from routers.customer_portal import get_me

        store = _store_published()  # current = v1.0:...
        account = {
            "id": "c-1",
            "email": "x@example.com",
            "name": "X",
            "organization_id": "org-1",
            "locale": "it",
            "email_verified": True,
            "created_at": "2026-05-18T10:00:00+00:00",
            "signup_slug": "acme",
            # Customer accepted an earlier version (different hash)
            "accepted_store_terms_version": "v0.9:somethingoldhash",
            "accepted_store_privacy_version": "v0.9:somethingoldhash",
        }

        with patch(
            "repositories.customer_account_repository.find_by_id",
            new=AsyncMock(return_value=account),
        ), patch(
            "routers.customer_portal.organizations_collection.find_one",
            new=AsyncMock(return_value={"name": "Acme", "public_slug": "acme"}),
        ), patch(
            "database.stores_collection.find_one",
            new=AsyncMock(return_value=store),
        ):
            res = await get_me(current_customer={
                "customer_account_id": "c-1",
                "organization_id": "org-1",
            })

        assert res["consent_needs_refresh"] is True

    @pytest.mark.asyncio
    async def test_legacy_account_without_version_triggers_refresh(self):
        from routers.customer_portal import get_me

        store = _store_published()
        # Account with NO accepted_store_*_version fields at all
        account = {
            "id": "c-legacy",
            "email": "legacy@example.com",
            "name": "L",
            "organization_id": "org-1",
            "locale": "it",
            "email_verified": True,
            "created_at": "2026-05-18T10:00:00+00:00",
            "signup_slug": "acme",
        }

        with patch(
            "repositories.customer_account_repository.find_by_id",
            new=AsyncMock(return_value=account),
        ), patch(
            "routers.customer_portal.organizations_collection.find_one",
            new=AsyncMock(return_value={"name": "Acme", "public_slug": "acme"}),
        ), patch(
            "database.stores_collection.find_one",
            new=AsyncMock(return_value=store),
        ):
            res = await get_me(current_customer={
                "customer_account_id": "c-legacy",
                "organization_id": "org-1",
            })

        assert res["consent_needs_refresh"] is True

    @pytest.mark.asyncio
    async def test_unpublished_store_does_not_force_refresh(self):
        """If the merchant un-published or never published, we don't
        synthesise a re-consent — there's nothing to bind to."""
        from routers.customer_portal import get_me

        store = _store_not_configured()
        account = {
            "id": "c-1",
            "email": "x@example.com",
            "name": "X",
            "organization_id": "org-1",
            "locale": "it",
            "email_verified": True,
            "created_at": "2026-05-18T10:00:00+00:00",
            "signup_slug": "acme",
            "accepted_store_terms_version": "v0.9:hash",
            "accepted_store_privacy_version": "v0.9:hash",
        }

        with patch(
            "repositories.customer_account_repository.find_by_id",
            new=AsyncMock(return_value=account),
        ), patch(
            "routers.customer_portal.organizations_collection.find_one",
            new=AsyncMock(return_value={"name": "Acme", "public_slug": "acme"}),
        ), patch(
            "database.stores_collection.find_one",
            new=AsyncMock(return_value=store),
        ):
            res = await get_me(current_customer={
                "customer_account_id": "c-1",
                "organization_id": "org-1",
            })

        # Store is not_configured → no live version, no refresh prompt
        assert res["consent_needs_refresh"] is False
        assert res["current_store_legal_version"] is None


# ─── POST /customer/me/re-consent ───────────────────────────────────


class TestCustomerReConsent:
    @pytest.mark.asyncio
    async def test_re_consent_writes_audit_and_updates_account(self):
        from routers.customer_portal import customer_re_consent
        from services.merchant_legal_versioning import current_version_string

        store = _store_published()
        live_version = current_version_string(store)

        captured_audit = []
        captured_update = {}

        async def _fake_record(**kw):
            captured_audit.append(kw)

        async def _fake_update(query, update):
            captured_update["query"] = query
            captured_update["update"] = update

        account = {
            "id": "c-1",
            "email": "x@example.com",
            "name": "X",
            "organization_id": "org-1",
            "signup_slug": "acme",
            "accepted_store_terms_version": "v0.9:OLD",
            "accepted_store_privacy_version": "v0.9:OLD",
        }

        with patch(
            "repositories.customer_account_repository.find_by_id",
            new=AsyncMock(return_value=account),
        ), patch(
            "database.stores_collection.find_one",
            new=AsyncMock(return_value=store),
        ), patch(
            "repositories.consent_audit_repository.record_consent",
            new=_fake_record,
        ), patch(
            "database.customer_accounts_collection.update_one",
            new=_fake_update,
        ):
            result = await customer_re_consent(current_customer={
                "customer_account_id": "c-1",
                "organization_id": "org-1",
            })

        # 2 audit records (privacy + terms)
        assert len(captured_audit) == 2
        sources = [c["source"] for c in captured_audit]
        assert sources == ["customer_re_acceptance", "customer_re_acceptance"]
        # Account doc was patched with the live version
        assert captured_update["update"]["$set"]["accepted_store_terms_version"] == live_version
        assert captured_update["update"]["$set"]["accepted_store_privacy_version"] == live_version
        # Result envelope
        assert result["consent_needs_refresh"] is False
        assert result["accepted_terms_version"] == live_version

    @pytest.mark.asyncio
    async def test_re_consent_422_when_legacy_no_signup_slug(self):
        from fastapi import HTTPException
        from routers.customer_portal import customer_re_consent

        account_no_slug = {
            "id": "c-1",
            "email": "x@example.com",
            "name": "X",
            "organization_id": "org-1",
            # No signup_slug — legacy account
        }
        with patch(
            "repositories.customer_account_repository.find_by_id",
            new=AsyncMock(return_value=account_no_slug),
        ):
            with pytest.raises(HTTPException) as exc:
                await customer_re_consent(current_customer={
                    "customer_account_id": "c-1",
                    "organization_id": "org-1",
                })
        assert exc.value.status_code == 422


# ─── Router wiring ───────────────────────────────────────────────────


class TestRouteRegistration:
    def _paths(self):
        from server import app
        return {
            (r.path, frozenset(getattr(r, "methods") or set()))
            for r in app.routes
            if getattr(r, "methods", None) is not None
        }

    def test_re_consent_route_registered(self):
        assert (
            "/api/customer/me/re-consent",
            frozenset({"POST"}),
        ) in self._paths()


# ─── SignupRequest schema ────────────────────────────────────────────


class TestSignupRequestSchema:
    """The Pydantic SignupRequest exposes the new consent fields with
    safe defaults (False) so older clients that don't send them get a
    clean 400 from the service layer instead of a 422 from Pydantic."""

    def test_signup_request_has_consent_fields(self):
        from routers.customer_auth import SignupRequest

        body = SignupRequest(
            slug="acme",
            email="x@example.com",
            name="X",
            password="StrongPass12",
        )
        assert body.accepted_terms is False
        assert body.accepted_privacy is False
        assert body.accepted_marketing is False

    def test_signup_request_accepts_explicit_consents(self):
        from routers.customer_auth import SignupRequest

        body = SignupRequest(
            slug="acme",
            email="x@example.com",
            name="X",
            password="StrongPass12",
            accepted_terms=True,
            accepted_privacy=True,
            accepted_marketing=True,
        )
        assert body.accepted_terms is True
        assert body.accepted_marketing is True
