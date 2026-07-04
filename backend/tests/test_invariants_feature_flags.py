"""Sentinel tests for Feature Flag infrastructure (Phase 0 Step 9).

Pin del contract di:
  - ``models.organization.OrganizationFeatureFlags``
  - ``services.feature_flag_service`` (get_all_flags, is_enabled, set_flag,
    clear_cache, KNOWN_FLAGS, FLAG_* constants)
  - ``routers.admin_feature_flags`` (GET/PUT con auth system_admin)

Invariants pinned
=================
  INV-FF-1  Tutti i flag canonici default False (zero rollout fino a opt-in)
  INV-FF-2  is_enabled(org_id, flag) ritorna False per org sconosciute
  INV-FF-3  Cache TTL = 60 secondi (propagazione modifiche admin)
  INV-FF-4  Cache invalidata automaticamente dopo set_flag
  INV-FF-5  KNOWN_FLAGS contiene i 4 flag Phase 0 (Stream A + B + persistent_cart)
  INV-FF-6  Admin endpoint richiede role == system_admin (403 altrimenti)
  INV-FF-7  PUT con flag_name sconosciuto → 400 (no sandbox escape via typo)
"""

import asyncio
import inspect
import os
import sys
import time
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# ── Env bootstrap ────────────────────────────────────────────────────────
os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-not-for-production")
os.environ.setdefault("MONGO_URL", "mongodb://localhost:27017")
os.environ.setdefault("DB_NAME", "test_db")
os.environ.setdefault("ANTHROPIC_API_KEY", "test-key-not-real")

BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))


# ─── Module contract ───────────────────────────────────────────────────


class TestFeatureFlagModule:
    def test_service_importable(self):
        from services import feature_flag_service
        assert feature_flag_service is not None

    def test_service_public_api(self):
        from services import feature_flag_service
        # Public API surface — chiavi che ogni call site del codebase
        # deve poter chiamare.
        for name in ("is_enabled", "get_all_flags", "set_flag", "clear_cache"):
            assert hasattr(feature_flag_service, name), (
                f"feature_flag_service.{name} is part of the public API and "
                "MUST remain available. Removing it breaks consumers."
            )

    def test_canonical_flag_constants(self):
        """Le costanti string sono usate dal codice → NON rinominare."""
        from services import feature_flag_service as ff
        assert ff.FLAG_PERSISTENT_CART == "persistent_cart_enabled"
        assert ff.FLAG_EMBED_WIDGET == "embed_widget_enabled"
        assert ff.FLAG_CUSTOM_DOMAIN == "custom_domain_enabled"
        assert ff.FLAG_AI_SITE_BUILDER == "ai_site_builder_enabled"


# ─── INV-FF-5 — KNOWN_FLAGS completeness ────────────────────────────────


class TestINV_FF_5_KnownFlags:
    def test_known_flags_contains_phase0_flags(self):
        from services.feature_flag_service import (
            KNOWN_FLAGS,
            FLAG_PERSISTENT_CART,
            FLAG_EMBED_WIDGET,
            FLAG_CUSTOM_DOMAIN,
            FLAG_AI_SITE_BUILDER,
        )
        for f in (FLAG_PERSISTENT_CART, FLAG_EMBED_WIDGET,
                  FLAG_CUSTOM_DOMAIN, FLAG_AI_SITE_BUILDER):
            assert f in KNOWN_FLAGS, (
                f"KNOWN_FLAGS missing '{f}'. Admin endpoint validation "
                "userà KNOWN_FLAGS per rejectare arbitrary keys; un flag "
                "non listato qui non sarà mai settabile via UI."
            )

    def test_known_flags_size_minimum(self):
        from services.feature_flag_service import KNOWN_FLAGS
        # Almeno i 4 flag Phase 0. Stream successivi possono aggiungere.
        assert len(KNOWN_FLAGS) >= 4


# ─── INV-FF-1 — Default False ──────────────────────────────────────────


class TestINV_FF_1_DefaultsFalse:
    """Ogni nuovo flag deve default False (zero rollout finché admin opt-in)."""

    def test_organization_feature_flags_defaults(self):
        from models.organization import OrganizationFeatureFlags
        ff = OrganizationFeatureFlags()
        assert ff.persistent_cart_enabled is False
        assert ff.embed_widget_enabled is False
        assert ff.custom_domain_enabled is False
        assert ff.ai_site_builder_enabled is False

    def test_organization_has_feature_flags_field(self):
        """Il campo deve esistere sul modello Organization."""
        from models.organization import Organization
        org_fields = Organization.model_fields
        assert "feature_flags" in org_fields, (
            "Organization.feature_flags field missing. Senza questo campo "
            "il service feature_flag_service NON può leggere lo stato per-org."
        )


# ─── INV-FF-2 — is_enabled fail-safe ───────────────────────────────────


class TestINV_FF_2_IsEnabledFailSafe:
    """is_enabled ritorna False per qualsiasi input invalido / org sconosciuta."""

    def setup_method(self):
        from services import feature_flag_service
        feature_flag_service.clear_cache()

    @pytest.mark.asyncio
    async def test_unknown_org_returns_false(self):
        from services import feature_flag_service

        async def fake_find_one(*args, **kwargs):
            return None  # org not found

        with patch.object(
            __import__("database"), "organizations_collection",
            MagicMock(find_one=fake_find_one),
        ):
            feature_flag_service.clear_cache()
            assert await feature_flag_service.is_enabled(
                "ghost-org", "embed_widget_enabled"
            ) is False

    @pytest.mark.asyncio
    async def test_empty_inputs_return_false(self):
        from services import feature_flag_service
        assert await feature_flag_service.is_enabled("", "embed_widget_enabled") is False
        assert await feature_flag_service.is_enabled("org-1", "") is False

    @pytest.mark.asyncio
    async def test_unset_flag_returns_false(self):
        """Org esistente ma feature_flags vuoto/None → False per ogni flag."""
        from services import feature_flag_service

        async def fake_find_one(*args, **kwargs):
            return {"feature_flags": {}}  # tutti unset

        with patch.object(
            __import__("database"), "organizations_collection",
            MagicMock(find_one=fake_find_one),
        ):
            feature_flag_service.clear_cache()
            assert await feature_flag_service.is_enabled(
                "org-1", "embed_widget_enabled"
            ) is False

    @pytest.mark.asyncio
    async def test_explicit_true_returns_true(self):
        from services import feature_flag_service

        async def fake_find_one(*args, **kwargs):
            return {"feature_flags": {"embed_widget_enabled": True}}

        with patch.object(
            __import__("database"), "organizations_collection",
            MagicMock(find_one=fake_find_one),
        ):
            feature_flag_service.clear_cache()
            assert await feature_flag_service.is_enabled(
                "org-1", "embed_widget_enabled"
            ) is True

    @pytest.mark.asyncio
    async def test_db_failure_fails_safe(self):
        """Eccezione DB lookup → False (fail-safe, mai True per default)."""
        from services import feature_flag_service

        async def boom(*args, **kwargs):
            raise RuntimeError("DB unreachable")

        with patch.object(
            __import__("database"), "organizations_collection",
            MagicMock(find_one=boom),
        ):
            feature_flag_service.clear_cache()
            assert await feature_flag_service.is_enabled(
                "org-1", "embed_widget_enabled"
            ) is False


# ─── INV-FF-3 — Cache TTL ──────────────────────────────────────────────


class TestINV_FF_3_CacheTTL:
    def test_cache_ttl_60_seconds(self):
        from services import feature_flag_service
        assert feature_flag_service._CACHE_TTL_SECONDS == 60, (
            f"Cache TTL changed to {feature_flag_service._CACHE_TTL_SECONDS}s. "
            "Long TTL → admin toggle slow propagation. Short TTL → hot path "
            "extra DB load. 60s è il compromesso documentato."
        )


# ─── INV-FF-4 — Cache invalidation after set_flag ───────────────────────


class TestINV_FF_4_CacheInvalidatedOnWrite:
    """set_flag deve invalidare la cache per org_id, altrimenti
    is_enabled può ritornare stale value per fino 60s."""

    def setup_method(self):
        from services import feature_flag_service
        feature_flag_service.clear_cache()

    @pytest.mark.asyncio
    async def test_set_flag_clears_org_cache(self):
        from services import feature_flag_service

        # Mock find_one + update_one
        state = {"feature_flags": {"embed_widget_enabled": False}}

        async def fake_find_one(*args, **kwargs):
            return dict(state)

        async def fake_update_one(*args, **kwargs):
            # Apply update to mocked state
            update_op = args[1] if len(args) > 1 else kwargs.get("update")
            if update_op and "$set" in update_op:
                for key, value in update_op["$set"].items():
                    # key = "feature_flags.embed_widget_enabled"
                    if key.startswith("feature_flags."):
                        flag = key.split(".", 1)[1]
                        state["feature_flags"][flag] = value
            res = MagicMock()
            res.matched_count = 1
            return res

        with patch.object(
            __import__("database"), "organizations_collection",
            MagicMock(find_one=fake_find_one, update_one=fake_update_one),
        ):
            # 1. Prime cache → False
            assert await feature_flag_service.is_enabled(
                "org-x", "embed_widget_enabled"
            ) is False

            # 2. Set True
            ok = await feature_flag_service.set_flag(
                "org-x", "embed_widget_enabled", True
            )
            assert ok is True

            # 3. Re-read: cache deve essere stata invalidata → True
            assert await feature_flag_service.is_enabled(
                "org-x", "embed_widget_enabled"
            ) is True


# ─── Admin endpoint registration ──────────────────────────────────────


class TestAdminFeatureFlagsRouter:
    def test_router_module_importable(self):
        from routers import admin_feature_flags
        assert admin_feature_flags.router is not None

    def test_router_prefix_canonical(self):
        from routers.admin_feature_flags import router
        assert router.prefix == "/admin/feature-flags", (
            f"Router prefix changed to '{router.prefix}'. URL contract "
            "client-facing — change breaks UI admin panel."
        )

    def test_server_includes_router(self):
        import server
        source = inspect.getsource(server)
        assert "admin_feature_flags_router" in source, (
            "Server non importa admin_feature_flags_router. Endpoint NON raggiungibile."
        )
        assert "app.include_router(admin_feature_flags_router.router" in source


# ─── INV-FF-6 — System admin authorization ────────────────────────────


class TestINV_FF_6_RequiresSystemAdmin:
    """GET e PUT richiedono entrambi require_system_admin."""

    def test_get_endpoint_requires_system_admin(self):
        from routers import admin_feature_flags
        sig = inspect.signature(admin_feature_flags.get_feature_flags)
        params = list(sig.parameters.values())
        # Cerca il dependency
        deps = [str(p.default) for p in params if p.default is not inspect.Parameter.empty]
        assert any("require_system_admin" in d for d in deps), (
            "GET /admin/feature-flags/{org_id} non protetto da require_system_admin. "
            "Org admin potrebbero leggere/modificare flag di altri tenant."
        )

    def test_put_endpoint_requires_system_admin(self):
        from routers import admin_feature_flags
        sig = inspect.signature(admin_feature_flags.set_feature_flag)
        params = list(sig.parameters.values())
        deps = [str(p.default) for p in params if p.default is not inspect.Parameter.empty]
        assert any("require_system_admin" in d for d in deps), (
            "PUT /admin/feature-flags/{org_id} non protetto da require_system_admin. "
            "Write access esposto a non-system-admin → escalation di privilegio."
        )


# ─── INV-FF-7 — Unknown flag rejected ─────────────────────────────────


class TestINV_FF_7_UnknownFlagRejected:
    """PUT con flag_name ∉ KNOWN_FLAGS → 400. Mitigates typos / sandbox escape."""

    @pytest.mark.asyncio
    async def test_set_unknown_flag_raises_400(self):
        from fastapi import HTTPException
        from routers.admin_feature_flags import set_feature_flag, FeatureFlagUpdate

        body = FeatureFlagUpdate(flag_name="totally_made_up_flag", value=True)
        with pytest.raises(HTTPException) as exc_info:
            await set_feature_flag(
                org_id="org-1",
                body=body,
                current_user={"user_id": "sys-1", "role": "system_admin"},
            )
        assert exc_info.value.status_code == 400
        assert "Unknown flag_name" in exc_info.value.detail


# ─── Cache helper API ─────────────────────────────────────────────────


class TestCacheClearHelper:
    def test_clear_cache_all(self):
        from services import feature_flag_service
        feature_flag_service._CACHE["o1"] = ({}, time.monotonic())
        feature_flag_service._CACHE["o2"] = ({}, time.monotonic())
        feature_flag_service.clear_cache()
        assert len(feature_flag_service._CACHE) == 0

    def test_clear_cache_single_org(self):
        from services import feature_flag_service
        feature_flag_service._CACHE.clear()
        feature_flag_service._CACHE["o1"] = ({}, time.monotonic())
        feature_flag_service._CACHE["o2"] = ({}, time.monotonic())
        feature_flag_service.clear_cache("o1")
        assert "o1" not in feature_flag_service._CACHE
        assert "o2" in feature_flag_service._CACHE
        feature_flag_service.clear_cache()
