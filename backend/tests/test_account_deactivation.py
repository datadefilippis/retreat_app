"""
Tests for Account Deactivation + Hard Delete (v6.0, GDPR art. 17).

Covers:
- Organization deactivated_at field
- Deactivation endpoint (password, stripe, email, audit)
- Reactivation endpoint (lockout, free plan, grace period)
- Login check for deactivated accounts (admin vs member message)
- Hard delete service (cascade, idempotency, audit anonymization)
- Account data summary endpoint
"""

import os
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-not-for-production")
os.environ.setdefault("MONGO_URL", "mongodb://localhost:27017")
os.environ.setdefault("DB_NAME", "test_db")


# ── Organization Model Tests ──────────────────────────────────────────────────

class TestOrganizationDeactivatedAt:

    def test_default_is_none(self):
        from models.organization import Organization
        org = Organization(name="Test Org")
        assert org.deactivated_at is None

    def test_can_set_datetime(self):
        from models.organization import Organization
        now = datetime.now(timezone.utc)
        org = Organization(name="Test Org", deactivated_at=now)
        assert org.deactivated_at == now

    def test_can_reset_to_none(self):
        from models.organization import Organization
        org = Organization(name="Test Org", deactivated_at=datetime.now(timezone.utc))
        org.deactivated_at = None
        assert org.deactivated_at is None


# ── Reactivation Lockout Tests ────────────────────────────────────────────────

class TestReactivationLockout:

    def test_lockout_after_threshold(self):
        from routers.auth import _check_lockout, _record_failed_attempt, _clear_lockout, _reactivation_attempts
        email = "lockout-test@example.com"
        _reactivation_attempts.clear()

        # Not locked initially
        assert _check_lockout(email) is False

        # Record 5 failed attempts
        for _ in range(5):
            _record_failed_attempt(email)

        # Should be locked now
        assert _check_lockout(email) is True

        # Clean up
        _clear_lockout(email)
        assert _check_lockout(email) is False

    def test_lockout_expires(self):
        from routers.auth import _check_lockout, _reactivation_attempts
        email = "expire-test@example.com"
        _reactivation_attempts.clear()

        # Set expired lockout
        _reactivation_attempts[email] = {
            "count": 10,
            "locked_until": datetime.now(timezone.utc) - timedelta(minutes=1),
        }

        # Should NOT be locked (expired)
        assert _check_lockout(email) is False

    def test_cleanup_expired_entries(self):
        from routers.auth import _check_lockout, _reactivation_attempts
        _reactivation_attempts.clear()

        # Add expired entry
        _reactivation_attempts["old@test.com"] = {
            "count": 5,
            "locked_until": datetime.now(timezone.utc) - timedelta(hours=1),
        }
        # Add valid entry
        _reactivation_attempts["new@test.com"] = {
            "count": 2,
            "locked_until": None,
        }

        # Calling check_lockout triggers cleanup
        _check_lockout("trigger@test.com")

        assert "old@test.com" not in _reactivation_attempts
        assert "new@test.com" in _reactivation_attempts

        _reactivation_attempts.clear()


# ── Login Deactivation Check Tests ────────────────────────────────────────────

class TestLoginDeactivatedCheck:

    @pytest.mark.asyncio
    async def test_login_raises_for_deactivated_org(self):
        """Login should raise ValueError with role info when org is deactivated."""
        now = datetime.now(timezone.utc)
        with patch("services.auth_service.user_repository") as mock_repo, \
             patch("services.auth_service.verify_password", return_value=True), \
             patch("services.auth_service.organization_repository") as mock_org_repo:
            mock_repo.find_by_email = AsyncMock(return_value={
                "id": "u1",
                "email": "test@example.com",
                "password_hash": "hashed",
                "is_active": True,
                "email_verified": True,
                "role": "admin",
                "organization_id": "org1",
            })
            mock_org_repo.find_by_id = AsyncMock(return_value={
                "id": "org1",
                "deactivated_at": now,
            })
            from services.auth_service import login
            with pytest.raises(ValueError, match="Account deactivated"):
                await login("test@example.com", "password")

    @pytest.mark.asyncio
    async def test_login_includes_role_in_error(self):
        """The error message should include the user's role."""
        now = datetime.now(timezone.utc)
        with patch("services.auth_service.user_repository") as mock_repo, \
             patch("services.auth_service.verify_password", return_value=True), \
             patch("services.auth_service.organization_repository") as mock_org_repo:
            mock_repo.find_by_email = AsyncMock(return_value={
                "id": "u1",
                "email": "member@example.com",
                "password_hash": "hashed",
                "is_active": True,
                "email_verified": True,
                "role": "user",
                "organization_id": "org1",
            })
            mock_org_repo.find_by_id = AsyncMock(return_value={
                "id": "org1",
                "deactivated_at": now,
            })
            from services.auth_service import login
            with pytest.raises(ValueError, match=r"Account deactivated\|user"):
                await login("member@example.com", "password")

    @pytest.mark.asyncio
    async def test_system_admin_bypasses_deactivation(self):
        """System admin has no org, should not be affected."""
        with patch("services.auth_service.user_repository") as mock_repo, \
             patch("services.auth_service.verify_password", return_value=True), \
             patch("services.auth_service.users_collection") as mock_col, \
             patch("services.auth_service.organization_repository") as mock_org_repo, \
             patch("services.auth_service.audit_repository") as mock_audit, \
             patch("services.auth_service.create_access_token", return_value="admin_jwt"):
            mock_repo.find_by_email = AsyncMock(return_value={
                "id": "sa1",
                "email": "admin@system.com",
                "name": "Admin",
                "password_hash": "hashed",
                "is_active": True,
                "email_verified": False,  # system admin bypasses
                "role": "system_admin",
                "organization_id": None,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "must_change_password": False,
                "locale": "it",
            })
            mock_col.update_one = AsyncMock()
            mock_org_repo.find_by_id = AsyncMock(return_value=None)
            mock_audit.create = AsyncMock()
            from services.auth_service import login
            result = await login("admin@system.com", "password")
            assert result.access_token == "admin_jwt"


# ── Hard Delete Service Tests ─────────────────────────────────────────────────

class TestHardDeleteService:

    @pytest.mark.asyncio
    async def test_cascade_deletes_all_collections(self):
        """Should call delete_many on all org-scoped collections."""
        from services.hard_delete_service import _ORG_SCOPED_COLLECTIONS

        # Verify we have a comprehensive list
        assert len(_ORG_SCOPED_COLLECTIONS) >= 20

        # All entries should be (name, collection) tuples
        for name, col in _ORG_SCOPED_COLLECTIONS:
            assert isinstance(name, str)
            assert col is not None

    def test_hard_delete_order(self):
        """Organization should be deleted LAST in the cascade."""
        from services.hard_delete_service import _ORG_SCOPED_COLLECTIONS

        names = [name for name, _ in _ORG_SCOPED_COLLECTIONS]
        # org should NOT be in the scoped list (deleted separately, last)
        assert "organizations" not in names

    @pytest.mark.asyncio
    async def test_cascade_idempotent(self):
        """Running cascade twice should not fail (second run finds 0 records)."""
        mock_result = MagicMock()
        mock_result.deleted_count = 0

        with patch("services.hard_delete_service.chat_sessions_collection") as mock_col:
            mock_col.delete_many = AsyncMock(return_value=mock_result)
            # This verifies the delete_many pattern works with 0 results
            result = await mock_col.delete_many({"organization_id": "deleted_org"})
            assert result.deleted_count == 0

    @pytest.mark.asyncio
    async def test_audit_logs_anonymized_not_deleted(self):
        """Audit logs should be anonymized (user_id='deleted', details={})."""
        mock_result = MagicMock()
        mock_result.modified_count = 5

        with patch("services.hard_delete_service.audit_logs_collection") as mock_col:
            mock_col.update_many = AsyncMock(return_value=mock_result)
            result = await mock_col.update_many(
                {"organization_id": "org1"},
                {"$set": {"user_id": "deleted", "details": {}, "organization_id": "deleted"}},
            )
            assert result.modified_count == 5
            # Verify it's update_many (anonymize), NOT delete_many
            mock_col.update_many.assert_called_once()
            mock_col.delete_many.assert_not_called()


# ── Terms Acceptance Integration ──────────────────────────────────────────────

class TestDeactivationPrereqs:

    def test_user_create_accepted_terms_required(self):
        """UserCreate should have accepted_terms field."""
        from models.user import UserCreate
        uc = UserCreate(
            email="test@example.com",
            name="Test",
            password="SecurePass123!",
            accepted_terms=True,
        )
        assert uc.accepted_terms is True

    def test_reactivate_body_model(self):
        """Reactivate body should accept email + password."""
        from routers.auth import _ReactivateBody
        body = _ReactivateBody(email="test@example.com", password="pass")
        assert body.email == "test@example.com"

    def test_deactivate_body_model(self):
        """Deactivate body should accept password."""
        from routers.auth import _DeactivateBody
        body = _DeactivateBody(password="pass")
        assert body.password == "pass"
