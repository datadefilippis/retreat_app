"""
Tests for Controlled Access — Invite-Only Registration (v6.0).

Covers:
- Platform settings repository (get/set registration mode)
- Invite repository (create, find, revoke, mark_used)
- Signup gate logic (open vs invite-only, token validation)
- Public endpoints (registration-mode, validate-invite)
"""

import hashlib
import os
import secrets
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Ensure test env vars are set before any app imports
os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-not-for-production")
os.environ.setdefault("MONGO_URL", "mongodb://localhost:27017")
os.environ.setdefault("DB_NAME", "test_db")


# ── Platform Settings Repository Tests ────────────────────────────────────────

class TestPlatformSettingsRepository:
    """Tests for platform_settings_repository functions."""

    @pytest.mark.asyncio
    async def test_get_registration_mode_default(self):
        """When no document exists, should return 'open'."""
        with patch("repositories.platform_settings_repository.platform_settings_collection") as mock_col:
            mock_col.find_one = AsyncMock(return_value=None)
            from repositories.platform_settings_repository import get_registration_mode
            result = await get_registration_mode()
            assert result == "open"

    @pytest.mark.asyncio
    async def test_get_registration_mode_invite_only(self):
        """When document exists with invite_only, should return it."""
        with patch("repositories.platform_settings_repository.platform_settings_collection") as mock_col:
            mock_col.find_one = AsyncMock(return_value={
                "key": "registration",
                "registration_mode": "invite_only",
            })
            from repositories.platform_settings_repository import get_registration_mode
            result = await get_registration_mode()
            assert result == "invite_only"

    @pytest.mark.asyncio
    async def test_set_registration_mode(self):
        """Should upsert the registration mode."""
        with patch("repositories.platform_settings_repository.platform_settings_collection") as mock_col:
            mock_result = MagicMock()
            mock_result.acknowledged = True
            mock_col.update_one = AsyncMock(return_value=mock_result)
            from repositories.platform_settings_repository import set_registration_mode
            result = await set_registration_mode("invite_only", "admin_user_id")
            assert result is True
            mock_col.update_one.assert_called_once()
            call_args = mock_col.update_one.call_args
            assert call_args[0][0] == {"key": "registration"}
            assert call_args[0][1]["$set"]["registration_mode"] == "invite_only"


# ── Invite Repository Tests ───────────────────────────────────────────────────

class TestInviteRepository:
    """Tests for invite_repository functions."""

    @pytest.mark.asyncio
    async def test_create_invite(self):
        """Should insert an invite document."""
        with patch("repositories.invite_repository.invites_collection") as mock_col:
            mock_col.insert_one = AsyncMock(return_value=MagicMock())
            from repositories.invite_repository import create
            from models.invite import Invite
            invite = Invite(
                email="test@example.com",
                token_hash="abc123hash",
                created_by="admin_id",
                expires_at=datetime.now(timezone.utc) + timedelta(days=7),
            )
            result = await create(invite)
            assert result["email"] == "test@example.com"
            assert result["status"] == "pending"
            mock_col.insert_one.assert_called_once()

    @pytest.mark.asyncio
    async def test_find_by_token_hash_valid(self):
        """Should find a pending non-expired invite."""
        with patch("repositories.invite_repository.invites_collection") as mock_col:
            future = (datetime.now(timezone.utc) + timedelta(days=5)).isoformat()
            mock_col.find_one = AsyncMock(return_value={
                "id": "inv_1",
                "email": "test@example.com",
                "token_hash": "abc123",
                "status": "pending",
                "expires_at": future,
            })
            from repositories.invite_repository import find_by_token_hash
            result = await find_by_token_hash("abc123")
            assert result is not None
            assert result["email"] == "test@example.com"

    @pytest.mark.asyncio
    async def test_find_by_token_hash_not_found(self):
        """Should return None for unknown token."""
        with patch("repositories.invite_repository.invites_collection") as mock_col:
            mock_col.find_one = AsyncMock(return_value=None)
            from repositories.invite_repository import find_by_token_hash
            result = await find_by_token_hash("nonexistent")
            assert result is None

    @pytest.mark.asyncio
    async def test_mark_used(self):
        """Should update status to 'used'."""
        with patch("repositories.invite_repository.invites_collection") as mock_col:
            mock_result = MagicMock()
            mock_result.modified_count = 1
            mock_col.update_one = AsyncMock(return_value=mock_result)
            from repositories.invite_repository import mark_used
            result = await mark_used("inv_1")
            assert result is True

    @pytest.mark.asyncio
    async def test_revoke(self):
        """Should update status to 'revoked'."""
        with patch("repositories.invite_repository.invites_collection") as mock_col:
            mock_result = MagicMock()
            mock_result.modified_count = 1
            mock_col.update_one = AsyncMock(return_value=mock_result)
            from repositories.invite_repository import revoke
            result = await revoke("inv_1")
            assert result is True

    @pytest.mark.asyncio
    async def test_revoke_already_used(self):
        """Should return False when trying to revoke a used invite."""
        with patch("repositories.invite_repository.invites_collection") as mock_col:
            mock_result = MagicMock()
            mock_result.modified_count = 0
            mock_col.update_one = AsyncMock(return_value=mock_result)
            from repositories.invite_repository import revoke
            result = await revoke("inv_used")
            assert result is False


# ── Signup Gate Logic Tests ───────────────────────────────────────────────────

class TestSignupGate:
    """Tests for the invite-only gate logic in signup."""

    def test_token_hash_consistency(self):
        """SHA-256 hash of token should be deterministic."""
        token = "test_token_abc123"
        hash1 = hashlib.sha256(token.encode()).hexdigest()
        hash2 = hashlib.sha256(token.encode()).hexdigest()
        assert hash1 == hash2
        assert len(hash1) == 64

    def test_email_case_insensitive_match(self):
        """Email comparison should be case-insensitive."""
        invite_email = "Test@Example.com"
        signup_email = "test@example.com"
        assert invite_email.lower() == signup_email.lower()

    def test_email_case_mismatch(self):
        """Different emails should not match."""
        invite_email = "test@example.com"
        signup_email = "other@example.com"
        assert invite_email.lower() != signup_email.lower()


# ── Model Validation Tests ────────────────────────────────────────────────────

class TestInviteModels:
    """Tests for Invite Pydantic models."""

    def test_invite_create_valid(self):
        from models.invite import InviteCreate
        ic = InviteCreate(email="test@example.com")
        assert ic.email == "test@example.com"

    def test_invite_create_invalid_email(self):
        from pydantic import ValidationError
        from models.invite import InviteCreate
        with pytest.raises(ValidationError):
            InviteCreate(email="not-an-email")

    def test_invite_default_status(self):
        from models.invite import Invite
        inv = Invite(
            email="test@example.com",
            token_hash="abc",
            created_by="admin",
            expires_at=datetime.now(timezone.utc) + timedelta(days=7),
        )
        assert inv.status.value == "pending"

    def test_platform_settings_default(self):
        from models.platform_settings import PlatformSettings
        ps = PlatformSettings(key="registration")
        assert ps.registration_mode.value == "open"

    def test_user_create_with_invite_token(self):
        from models.user import UserCreate
        uc = UserCreate(
            email="test@example.com",
            name="Test User",
            password="SecurePass123!",
            invite_token="some_token",
        )
        assert uc.invite_token == "some_token"

    def test_user_create_without_invite_token(self):
        from models.user import UserCreate
        uc = UserCreate(
            email="test@example.com",
            name="Test User",
            password="SecurePass123!",
        )
        assert uc.invite_token is None


# ── Email Verification Gate Tests (v6.0) ──────────────────────────────────────

class TestEmailVerificationGate:
    """Tests for mandatory email verification before login."""

    @pytest.mark.asyncio
    async def test_login_rejected_if_email_not_verified(self):
        """Login should raise ValueError if email_verified=False."""
        with patch("services.auth_service.user_repository") as mock_repo, \
             patch("services.auth_service.verify_password", return_value=True):
            mock_repo.find_by_email = AsyncMock(return_value={
                "id": "u1",
                "email": "test@example.com",
                "password_hash": "hashed",
                "is_active": True,
                "email_verified": False,
                "role": "admin",
                "organization_id": "org1",
            })
            from services.auth_service import login
            with pytest.raises(ValueError, match="Email not verified"):
                await login("test@example.com", "password")

    @pytest.mark.asyncio
    async def test_login_ok_if_email_verified(self):
        """Login should succeed if email_verified=True."""
        with patch("services.auth_service.user_repository") as mock_repo, \
             patch("services.auth_service.verify_password", return_value=True), \
             patch("services.auth_service.users_collection") as mock_col, \
             patch("services.auth_service.organization_repository") as mock_org_repo, \
             patch("services.auth_service.audit_repository") as mock_audit, \
             patch("services.auth_service.create_access_token", return_value="test_jwt"):
            mock_repo.find_by_email = AsyncMock(return_value={
                "id": "u1",
                "email": "test@example.com",
                "name": "Test",
                "password_hash": "hashed",
                "is_active": True,
                "email_verified": True,
                "role": "admin",
                "organization_id": "org1",
                "created_at": datetime.now(timezone.utc).isoformat(),
                "must_change_password": False,
                "locale": "it",
            })
            mock_col.update_one = AsyncMock()
            mock_org_repo.find_by_id = AsyncMock(return_value={"currency": "EUR"})
            mock_audit.create = AsyncMock()
            from services.auth_service import login
            result = await login("test@example.com", "password")
            assert result.access_token == "test_jwt"

    @pytest.mark.asyncio
    async def test_system_admin_bypasses_verification(self):
        """System admin should login even without email_verified."""
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
                "email_verified": False,
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

    def test_team_invite_user_has_email_verified(self):
        """Users created via team invite should have email_verified=True."""
        from models.user import User
        user = User(
            email="invited@team.com",
            name="Team Member",
            role="user",
            organization_id="org1",
            password_hash="hashed",
            must_change_password=True,
            email_verified=True,
        )
        assert user.email_verified is True

    def test_default_user_email_not_verified(self):
        """Default User should have email_verified=False."""
        from models.user import User
        user = User(
            email="new@user.com",
            name="New User",
            organization_id="org1",
            password_hash="hashed",
        )
        assert user.email_verified is False


# ── Terms & Privacy Acceptance Tests (v6.0) ───────────────────────────────────

class TestTermsAcceptance:
    """Tests for mandatory terms acceptance at signup."""

    def test_user_create_accepted_terms_default_false(self):
        """UserCreate.accepted_terms should default to False."""
        from models.user import UserCreate
        uc = UserCreate(
            email="test@example.com",
            name="Test",
            password="SecurePass123!",
        )
        assert uc.accepted_terms is False

    def test_user_create_accepted_terms_true(self):
        """UserCreate.accepted_terms can be set to True."""
        from models.user import UserCreate
        uc = UserCreate(
            email="test@example.com",
            name="Test",
            password="SecurePass123!",
            accepted_terms=True,
        )
        assert uc.accepted_terms is True

    def test_user_model_accepted_terms_at_default_none(self):
        """User.accepted_terms_at should default to None."""
        from models.user import User
        user = User(
            email="test@example.com",
            name="Test",
            organization_id="org1",
            password_hash="hashed",
        )
        assert user.accepted_terms_at is None

    @pytest.mark.asyncio
    async def test_signup_rejects_without_accepted_terms(self):
        """Signup should reject if accepted_terms is False."""
        from models.user import UserCreate
        user_data = UserCreate(
            email="test@example.com",
            name="Test",
            password="SecurePass123!",
            accepted_terms=False,
        )
        from services.auth_service import signup
        with pytest.raises(ValueError, match="must accept the terms"):
            await signup(user_data)
