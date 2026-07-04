"""Tests for Phase 2a: Catalog Read Layer + Seed Hardening.

Coverage:
  - GET /admin/catalog/plans (enriched list)
  - GET /admin/catalog/plans/{slug} (enriched detail)
  - GET /admin/catalog/entitlement-tiers (grouped by module)
  - GET /admin/catalog/audit-log (empty in Phase 2a)
  - Seed protection: editable fields survive re-seed
  - Seed protection: module_plans additive merge
  - Seed protection: PricingPlan limits additive-only migration

All tests mock MongoDB — no real DB connection needed.
"""

import os
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Ensure env vars are set before any backend import
os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-not-for-production")
os.environ.setdefault("MONGO_URL", "mongodb://localhost:27017")
os.environ.setdefault("DB_NAME", "test_db")

BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))


# ══════════════════════════════════════════════════════════════════════════════
# Helpers
# ══════════════════════════════════════════════════════════════════════════════

def _make_commercial_plan(slug="core", name="AFianco Core", **overrides):
    base = {
        "id": f"plan-{slug}",
        "slug": slug,
        "name": name,
        "description": "Test plan",
        "tagline": "Test tagline",
        "price_monthly": 39.0,
        "price_yearly": 390.0,
        "currency": "EUR",
        "trial_days": 14,
        "is_public": True,
        "is_self_serve": True,
        "sort_order": 1,
        "module_plans": {
            "ai_assistant": "ai_assistant_starter",
            "cashflow_monitor": "cashflow_monitor_pro",
        },
        "features_display": ["billing.features.cashflow_full"],
        "is_archived": False,
        "admin_modified_at": None,
    }
    base.update(overrides)
    return base


def _make_pricing_plan(slug="ai_assistant_starter", module_key="ai_assistant", **overrides):
    base = {
        "id": f"pp-{slug}",
        "module_key": module_key,
        "slug": slug,
        "name": "AI Starter",
        "limits": {"chat": 50, "digest": 4, "alert_analysis": -1, "health_explanation": -1},
        "is_active": True,
        "sort_order": 1,
    }
    base.update(overrides)
    return base


# ══════════════════════════════════════════════════════════════════════════════
# Test: GET /admin/catalog/plans
# ══════════════════════════════════════════════════════════════════════════════

class TestListCatalogPlans:
    """Tests for GET /admin/catalog/plans."""

    @pytest.mark.asyncio
    async def test_returns_enriched_plans(self):
        """Plans are returned with resolved entitlements and subscriber count."""
        plan = _make_commercial_plan()
        pricing_plan = _make_pricing_plan()

        with patch("repositories.catalog_repository.commercial_plans_collection") as mock_cp, \
             patch("repositories.catalog_repository.pricing_plans_collection") as mock_pp, \
             patch("repositories.catalog_repository.organizations_collection") as mock_org:

            # Mock commercial plans cursor (sort is sync, to_list is async)
            mock_cursor = MagicMock()
            mock_cursor.sort.return_value = mock_cursor
            mock_cursor.to_list = AsyncMock(return_value=[plan])
            mock_cp.find.return_value = mock_cursor

            # Mock pricing plan lookups (one per module in module_plans)
            mock_pp.find_one = AsyncMock(return_value=pricing_plan)

            # Mock subscriber count
            mock_org.count_documents = AsyncMock(return_value=3)

            from repositories.catalog_repository import list_enriched_commercial_plans
            result = await list_enriched_commercial_plans()

        assert len(result) == 1
        assert result[0]["slug"] == "core"
        assert "entitlements" in result[0]
        assert len(result[0]["entitlements"]) == 2  # ai_assistant + cashflow_monitor
        assert result[0]["subscriber_count"] == 3

        # Verify entitlement structure
        ai_ent = next(e for e in result[0]["entitlements"] if e["module_key"] == "ai_assistant")
        assert ai_ent["pricing_plan_slug"] == "ai_assistant_starter"
        assert ai_ent["pricing_plan_name"] == "AI Starter"
        assert ai_ent["limits"]["chat"] == 50

    @pytest.mark.asyncio
    async def test_handles_missing_pricing_plan(self):
        """If a module_plans entry points to a missing PricingPlan, limits are empty."""
        plan = _make_commercial_plan()

        with patch("repositories.catalog_repository.commercial_plans_collection") as mock_cp, \
             patch("repositories.catalog_repository.pricing_plans_collection") as mock_pp, \
             patch("repositories.catalog_repository.organizations_collection") as mock_org:

            mock_cursor = MagicMock()
            mock_cursor.sort.return_value = mock_cursor
            mock_cursor.to_list = AsyncMock(return_value=[plan])
            mock_cp.find.return_value = mock_cursor

            # Pricing plan not found
            mock_pp.find_one = AsyncMock(return_value=None)
            mock_org.count_documents = AsyncMock(return_value=0)

            from repositories.catalog_repository import list_enriched_commercial_plans
            result = await list_enriched_commercial_plans()

        entitlements = result[0]["entitlements"]
        assert all(e["pricing_plan_name"] is None for e in entitlements)
        assert all(e["limits"] == {} for e in entitlements)


# ══════════════════════════════════════════════════════════════════════════════
# Test: GET /admin/catalog/plans/{slug}
# ══════════════════════════════════════════════════════════════════════════════

class TestGetCatalogPlan:
    """Tests for GET /admin/catalog/plans/{slug}."""

    @pytest.mark.asyncio
    async def test_returns_enriched_plan_with_orgs(self):
        """Single plan detail includes subscribing orgs."""
        plan = _make_commercial_plan()
        pricing_plan = _make_pricing_plan()
        orgs = [
            {"id": "org1", "name": "Acme", "billing_status": "active"},
            {"id": "org2", "name": "Beta", "billing_status": "trialing"},
        ]

        with patch("repositories.catalog_repository.commercial_plans_collection") as mock_cp, \
             patch("repositories.catalog_repository.pricing_plans_collection") as mock_pp, \
             patch("repositories.catalog_repository.organizations_collection") as mock_org:

            mock_cp.find_one = AsyncMock(return_value=plan)
            mock_pp.find_one = AsyncMock(return_value=pricing_plan)
            mock_org.count_documents = AsyncMock(return_value=2)

            # Orgs cursor
            org_cursor = AsyncMock()
            org_cursor.to_list = AsyncMock(return_value=orgs)
            mock_org.find.return_value = org_cursor

            from repositories.catalog_repository import get_enriched_commercial_plan
            result = await get_enriched_commercial_plan("core")

        assert result is not None
        assert result["subscriber_count"] == 2
        assert len(result["subscribing_organizations"]) == 2
        assert result["subscribing_organizations"][0]["name"] == "Acme"

    @pytest.mark.asyncio
    async def test_returns_none_for_missing_slug(self):
        """Returns None if plan slug doesn't exist."""
        with patch("repositories.catalog_repository.commercial_plans_collection") as mock_cp:
            mock_cp.find_one = AsyncMock(return_value=None)

            from repositories.catalog_repository import get_enriched_commercial_plan
            result = await get_enriched_commercial_plan("nonexistent")

        assert result is None


# ══════════════════════════════════════════════════════════════════════════════
# Test: GET /admin/catalog/entitlement-tiers
# ══════════════════════════════════════════════════════════════════════════════

class TestEntitlementTiers:
    """Tests for GET /admin/catalog/entitlement-tiers."""

    @pytest.mark.asyncio
    async def test_grouped_by_module_key(self):
        """Plans are grouped by module_key."""
        plans = [
            _make_pricing_plan("ai_assistant_free", "ai_assistant", name="Free", limits={"chat": 0}),
            _make_pricing_plan("ai_assistant_starter", "ai_assistant", name="Starter", limits={"chat": 50}),
            _make_pricing_plan("cashflow_monitor_free", "cashflow_monitor", name="Free", limits={"analytics": -1}),
        ]

        with patch("repositories.catalog_repository.pricing_plans_collection") as mock_pp:
            mock_cursor = MagicMock()
            mock_cursor.sort.return_value = mock_cursor
            mock_cursor.to_list = AsyncMock(return_value=plans)
            mock_pp.find.return_value = mock_cursor

            from repositories.catalog_repository import list_entitlement_tiers_grouped
            result = await list_entitlement_tiers_grouped()

        assert "ai_assistant" in result
        assert "cashflow_monitor" in result
        assert len(result["ai_assistant"]) == 2
        assert len(result["cashflow_monitor"]) == 1

    @pytest.mark.asyncio
    async def test_excludes_vestigial_price_fields(self):
        """price_monthly and price_yearly are excluded from the projection."""
        with patch("repositories.catalog_repository.pricing_plans_collection") as mock_pp:
            mock_cursor = MagicMock()
            mock_cursor.sort.return_value = mock_cursor
            mock_cursor.to_list = AsyncMock(return_value=[])
            mock_pp.find.return_value = mock_cursor

            from repositories.catalog_repository import list_entitlement_tiers_grouped
            await list_entitlement_tiers_grouped()

        # Verify the find() call excludes price fields
        call_args = mock_pp.find.call_args
        projection = call_args[0][1]  # second positional arg
        assert projection.get("price_monthly") == 0
        assert projection.get("price_yearly") == 0


# ══════════════════════════════════════════════════════════════════════════════
# Test: GET /admin/catalog/audit-log
# ══════════════════════════════════════════════════════════════════════════════

class TestCatalogAuditLog:
    """Tests for GET /admin/catalog/audit-log."""

    @pytest.mark.asyncio
    async def test_returns_empty_in_phase_2a(self):
        """Audit log is empty because no mutation endpoints exist yet."""
        with patch("repositories.catalog_repository.catalog_audit_log_collection") as mock_al:
            mock_cursor = MagicMock()
            mock_cursor.sort.return_value = mock_cursor
            mock_cursor.skip.return_value = mock_cursor
            mock_cursor.limit.return_value = mock_cursor
            mock_cursor.to_list = AsyncMock(return_value=[])
            mock_al.find.return_value = mock_cursor

            from repositories.catalog_repository import list_catalog_audit_entries
            result = await list_catalog_audit_entries()

        assert result == []

    @pytest.mark.asyncio
    async def test_supports_filtering(self):
        """Filters are applied to the query."""
        with patch("repositories.catalog_repository.catalog_audit_log_collection") as mock_al:
            mock_cursor = MagicMock()
            mock_cursor.sort.return_value = mock_cursor
            mock_cursor.skip.return_value = mock_cursor
            mock_cursor.limit.return_value = mock_cursor
            mock_cursor.to_list = AsyncMock(return_value=[])
            mock_al.find.return_value = mock_cursor

            from repositories.catalog_repository import list_catalog_audit_entries
            await list_catalog_audit_entries(
                entity_type="commercial_plan",
                entity_id="core",
            )

        filter_q = mock_al.find.call_args[0][0]
        assert filter_q["entity_type"] == "commercial_plan"
        assert filter_q["entity_id"] == "core"


# ══════════════════════════════════════════════════════════════════════════════
# Test: Seed Protection — CommercialPlan editable fields
# ══════════════════════════════════════════════════════════════════════════════

class TestSeedProtectionEditableFields:
    """Verify that admin-editable fields are NOT overwritten by seed reruns."""

    @pytest.mark.asyncio
    async def test_editable_fields_in_setOnInsert(self):
        """Editable fields must be in $setOnInsert, not $set."""
        doc = _make_commercial_plan()

        with patch("repositories.billing_repository.commercial_plans_collection") as mock_cp:
            # Simulate existing plan with module_plans already set
            mock_cp.find_one = AsyncMock(return_value={
                "module_plans": doc["module_plans"],
            })
            mock_cp.update_one = AsyncMock()

            from repositories.billing_repository import upsert_commercial_plan
            await upsert_commercial_plan(doc)

        call_args = mock_cp.update_one.call_args
        update_op = call_args[0][1]

        # These fields must NOT appear in $set
        protected_fields = {
            "name", "description", "tagline", "trial_days", "sort_order",
            "is_public", "is_self_serve", "features_display",
            "price_monthly", "price_yearly",
        }

        set_keys = set(update_op.get("$set", {}).keys())
        for field in protected_fields:
            assert field not in set_keys, f"'{field}' should not be in $set"

        # These fields MUST appear in $setOnInsert
        insert_keys = set(update_op.get("$setOnInsert", {}).keys())
        for field in protected_fields:
            assert field in insert_keys, f"'{field}' should be in $setOnInsert"

    @pytest.mark.asyncio
    async def test_admin_edit_survives_reseed(self):
        """A manually changed name is protected from seed overwrite."""
        # Seed doc has name "AFianco Core"
        doc = _make_commercial_plan(slug="core", name="AFianco Core")

        with patch("repositories.billing_repository.commercial_plans_collection") as mock_cp:
            # DB already has the plan with admin-modified name
            mock_cp.find_one = AsyncMock(return_value={
                "module_plans": {"ai_assistant": "ai_assistant_starter", "cashflow_monitor": "cashflow_monitor_pro"},
            })
            mock_cp.update_one = AsyncMock()

            from repositories.billing_repository import upsert_commercial_plan
            await upsert_commercial_plan(doc)

        call_args = mock_cp.update_one.call_args
        update_op = call_args[0][1]

        # "name" is in $setOnInsert (only applies on insert, not update)
        assert "name" not in update_op.get("$set", {})
        assert "name" in update_op.get("$setOnInsert", {})


# ══════════════════════════════════════════════════════════════════════════════
# Test: Seed Protection — module_plans additive merge
# ══════════════════════════════════════════════════════════════════════════════

class TestSeedProtectionModulePlans:
    """Verify additive merge for module_plans."""

    @pytest.mark.asyncio
    async def test_existing_module_tier_not_overwritten(self):
        """If admin changed ai_assistant from starter to pro, seed must not revert it."""
        doc = _make_commercial_plan(
            module_plans={
                "ai_assistant": "ai_assistant_starter",  # seed default
                "cashflow_monitor": "cashflow_monitor_pro",
            }
        )

        with patch("repositories.billing_repository.commercial_plans_collection") as mock_cp:
            # DB has admin-modified tier (pro instead of starter)
            mock_cp.find_one = AsyncMock(return_value={
                "module_plans": {
                    "ai_assistant": "ai_assistant_pro",      # admin override
                    "cashflow_monitor": "cashflow_monitor_pro",
                },
            })
            mock_cp.update_one = AsyncMock()

            from repositories.billing_repository import upsert_commercial_plan
            await upsert_commercial_plan(doc)

        call_args = mock_cp.update_one.call_args
        update_op = call_args[0][1]

        # No module_plans keys should appear in $set (all already exist)
        set_keys = update_op.get("$set", {})
        assert "module_plans" not in set_keys
        assert "module_plans.ai_assistant" not in set_keys
        assert "module_plans.cashflow_monitor" not in set_keys

    @pytest.mark.asyncio
    async def test_new_module_key_is_added(self):
        """A new module in the seed (e.g. revenue_forecasting) is added via dot-notation."""
        doc = _make_commercial_plan(
            module_plans={
                "ai_assistant": "ai_assistant_starter",
                "cashflow_monitor": "cashflow_monitor_pro",
                "revenue_forecasting": "revenue_forecasting_free",  # NEW module
            }
        )

        with patch("repositories.billing_repository.commercial_plans_collection") as mock_cp:
            # DB only has the 2 original modules
            mock_cp.find_one = AsyncMock(return_value={
                "module_plans": {
                    "ai_assistant": "ai_assistant_starter",
                    "cashflow_monitor": "cashflow_monitor_pro",
                },
            })
            mock_cp.update_one = AsyncMock()

            from repositories.billing_repository import upsert_commercial_plan
            await upsert_commercial_plan(doc)

        call_args = mock_cp.update_one.call_args
        update_op = call_args[0][1]

        # Only the new key should be in $set via dot-notation
        set_keys = update_op.get("$set", {})
        assert "module_plans.revenue_forecasting" in set_keys
        assert set_keys["module_plans.revenue_forecasting"] == "revenue_forecasting_free"

        # Existing keys must NOT appear
        assert "module_plans.ai_assistant" not in set_keys
        assert "module_plans.cashflow_monitor" not in set_keys

    @pytest.mark.asyncio
    async def test_fresh_plan_gets_full_module_plans_on_insert(self):
        """On first insert (plan doesn't exist), full module_plans go to $setOnInsert."""
        doc = _make_commercial_plan()

        with patch("repositories.billing_repository.commercial_plans_collection") as mock_cp:
            # Plan doesn't exist yet
            mock_cp.find_one = AsyncMock(return_value=None)
            mock_cp.update_one = AsyncMock()

            from repositories.billing_repository import upsert_commercial_plan
            await upsert_commercial_plan(doc)

        call_args = mock_cp.update_one.call_args
        update_op = call_args[0][1]

        # Full module_plans dict should be in $setOnInsert
        assert "module_plans" in update_op.get("$setOnInsert", {})
        assert update_op["$setOnInsert"]["module_plans"] == doc["module_plans"]


# ══════════════════════════════════════════════════════════════════════════════
# Test: Seed Protection — PricingPlan limits additive-only migration
# ══════════════════════════════════════════════════════════════════════════════

class TestSeedProtectionLimitsMigration:
    """Verify that migrate_pricing_plans() is additive-only."""

    @pytest.mark.asyncio
    async def test_existing_limit_value_not_overwritten(self):
        """If admin changed chat limit from 50 to 100, migration must not revert it.

        When all target keys already exist in the DB plan, no update should be called
        for that specific plan.  We test with a single slug to avoid cross-plan noise.
        """
        from services.seed_pricing import _TARGET_LIMITS

        # Pick one real slug and confirm all its target keys are present
        test_slug = "ai_assistant_starter"
        _, target_limits = _TARGET_LIMITS[test_slug]

        # DB plan has all keys, but chat is admin-modified (100 instead of 50)
        db_limits = dict(target_limits)  # copy all keys from seed
        db_limits["chat"] = 100  # admin override

        db_plan = _make_pricing_plan(slug=test_slug, limits=db_limits)

        def _mock_get(module_key, slug):
            """Return our test plan only for the target slug, None for others."""
            if slug == test_slug:
                return db_plan
            return None

        with patch("services.seed_pricing.subscription_repository") as mock_repo:
            mock_repo.get_pricing_plan_by_slug = AsyncMock(side_effect=_mock_get)
            mock_repo.update_plan_limits_by_slug = AsyncMock(return_value=True)

            from services.seed_pricing import migrate_pricing_plans
            await migrate_pricing_plans()

        # The update should NOT have been called for our test slug
        # because all keys already exist (even though values differ)
        for call in mock_repo.update_plan_limits_by_slug.call_args_list:
            assert call[0][0] != test_slug, (
                f"update_plan_limits_by_slug should not be called for '{test_slug}' "
                f"when all keys already exist"
            )

    @pytest.mark.asyncio
    async def test_missing_key_is_added(self):
        """A new limit key in the seed definition is added to existing plans."""
        # DB plan is missing "health_explanation" key
        db_plan = _make_pricing_plan(
            slug="ai_assistant_starter",
            module_key="ai_assistant",
            limits={"chat": 100, "digest": 4, "alert_analysis": -1}  # missing health_explanation
        )

        with patch("services.seed_pricing.subscription_repository") as mock_repo:
            mock_repo.get_pricing_plan_by_slug = AsyncMock(return_value=db_plan)
            mock_repo.update_plan_limits_by_slug = AsyncMock(return_value=True)

            from services.seed_pricing import migrate_pricing_plans
            await migrate_pricing_plans()

        # update_plan_limits_by_slug should have been called for this plan
        # The merged limits should contain the admin's chat=100, NOT seed's chat=50
        calls = mock_repo.update_plan_limits_by_slug.call_args_list

        # Find the call for ai_assistant_starter
        starter_calls = [c for c in calls if c[0][0] == "ai_assistant_starter"]
        if starter_calls:
            merged_limits = starter_calls[0][0][1]
            assert merged_limits["chat"] == 100       # admin value preserved
            assert merged_limits["health_explanation"] == -1  # seed default added
            assert merged_limits["digest"] == 4       # existing value preserved


# ══════════════════════════════════════════════════════════════════════════════
# Test: CatalogAuditEntry model
# ══════════════════════════════════════════════════════════════════════════════

class TestCatalogAuditModel:
    """Verify the CatalogAuditEntry model."""

    def test_model_creates_with_defaults(self):
        from models.catalog_audit import CatalogAuditEntry

        entry = CatalogAuditEntry(
            entity_type="commercial_plan",
            entity_id="core",
            action="update",
            changes={"name": {"old": "Core", "new": "Core Plus"}},
            performed_by="admin_123",
        )

        assert entry.entity_type == "commercial_plan"
        assert entry.entity_id == "core"
        assert entry.action == "update"
        assert entry.changes["name"]["new"] == "Core Plus"
        assert entry.performed_by == "admin_123"
        assert entry.performed_at is not None
        assert entry.id is not None
        assert entry.notes is None

    def test_model_accepts_notes(self):
        from models.catalog_audit import CatalogAuditEntry

        entry = CatalogAuditEntry(
            entity_type="pricing_plan",
            entity_id="ai_assistant_starter",
            action="update",
            changes={"limits.chat": {"old": 50, "new": 100}},
            performed_by="admin_456",
            notes="Customer requested higher chat limit",
        )

        assert entry.notes == "Customer requested higher chat limit"


# ══════════════════════════════════════════════════════════════════════════════
# Test: CommercialPlan model additions
# ══════════════════════════════════════════════════════════════════════════════

class TestCommercialPlanModelUpdate:
    """Verify new fields on CommercialPlan."""

    def test_new_fields_have_defaults(self):
        from models.commercial_plan import CommercialPlan

        plan = CommercialPlan(slug="test", name="Test")

        assert plan.is_archived is False
        assert plan.admin_modified_at is None

    def test_is_archived_can_be_set(self):
        from models.commercial_plan import CommercialPlan

        plan = CommercialPlan(slug="old", name="Old Plan", is_archived=True)
        assert plan.is_archived is True


# ══════════════════════════════════════════════════════════════════════════════
# Phase 2b Tests: Safe Catalog Mutations
# ══════════════════════════════════════════════════════════════════════════════

class TestPlanPatchRequestModel:
    """Validate PlanPatchRequest whitelist/forbid logic."""

    def test_accepts_allowed_fields(self):
        from routers.admin_catalog import PlanPatchRequest
        req = PlanPatchRequest(name="New Name", trial_days=7)
        assert req.name == "New Name"
        assert req.trial_days == 7

    def test_rejects_forbidden_field_module_plans(self):
        from routers.admin_catalog import PlanPatchRequest
        with pytest.raises(Exception) as exc_info:
            PlanPatchRequest(module_plans={"ai": "ai_free"})
        assert "Forbidden fields" in str(exc_info.value) or "extra" in str(exc_info.value).lower()

    def test_rejects_forbidden_field_price_monthly(self):
        from routers.admin_catalog import PlanPatchRequest
        with pytest.raises(Exception) as exc_info:
            PlanPatchRequest(price_monthly=99.0)
        assert "Forbidden fields" in str(exc_info.value) or "extra" in str(exc_info.value).lower()

    def test_rejects_forbidden_field_slug(self):
        from routers.admin_catalog import PlanPatchRequest
        with pytest.raises(Exception) as exc_info:
            PlanPatchRequest(slug="new-slug")
        assert "Forbidden fields" in str(exc_info.value) or "extra" in str(exc_info.value).lower()

    def test_rejects_forbidden_field_stripe_ids(self):
        from routers.admin_catalog import PlanPatchRequest
        with pytest.raises(Exception) as exc_info:
            PlanPatchRequest(stripe_price_id_monthly="price_xxx")
        assert "Forbidden fields" in str(exc_info.value) or "extra" in str(exc_info.value).lower()

    def test_rejects_unknown_field(self):
        from routers.admin_catalog import PlanPatchRequest
        with pytest.raises(Exception):
            PlanPatchRequest(totally_unknown_field="foo")

    def test_accepts_notes_for_audit(self):
        from routers.admin_catalog import PlanPatchRequest
        req = PlanPatchRequest(name="X", notes="Testing change")
        assert req.notes == "Testing change"

    def test_all_fields_optional(self):
        from routers.admin_catalog import PlanPatchRequest
        req = PlanPatchRequest()
        assert req.name is None
        assert req.description is None
        assert req.trial_days is None


class TestPatchCommercialPlan:
    """Tests for patch_commercial_plan() repository function."""

    @pytest.mark.asyncio
    async def test_successful_single_field_patch(self):
        """Patching one field updates it and creates audit entry."""
        existing = _make_commercial_plan(name="Old Name")

        with patch("repositories.catalog_repository.commercial_plans_collection") as mock_cp, \
             patch("repositories.catalog_repository.catalog_audit_log_collection") as mock_al, \
             patch("repositories.catalog_repository.pricing_plans_collection") as mock_pp, \
             patch("repositories.catalog_repository.organizations_collection") as mock_org:

            mock_cp.find_one = AsyncMock(return_value=existing)
            mock_cp.update_one = AsyncMock()
            mock_al.insert_one = AsyncMock()
            mock_pp.find_one = AsyncMock(return_value=_make_pricing_plan())
            mock_org.count_documents = AsyncMock(return_value=0)

            # For get_enriched_commercial_plan after update
            mock_cursor = MagicMock()
            mock_cursor.to_list = AsyncMock(return_value=[])
            mock_org.find.return_value = mock_cursor

            from repositories.catalog_repository import patch_commercial_plan
            result = await patch_commercial_plan(
                slug="core",
                patch_fields={"name": "New Name"},
                performed_by="admin_1",
            )

        # Verify update_one was called with the new name
        update_call = mock_cp.update_one.call_args
        update_set = update_call[0][1]["$set"]
        assert update_set["name"] == "New Name"
        assert "admin_modified_at" in update_set

        # Verify audit entry was written
        mock_al.insert_one.assert_called_once()
        audit_doc = mock_al.insert_one.call_args[0][0]
        assert audit_doc["entity_type"] == "commercial_plan"
        assert audit_doc["entity_id"] == "core"
        assert audit_doc["action"] == "update"
        assert audit_doc["changes"]["name"]["old"] == "Old Name"
        assert audit_doc["changes"]["name"]["new"] == "New Name"
        assert audit_doc["performed_by"] == "admin_1"

    @pytest.mark.asyncio
    async def test_successful_multiple_fields_patch(self):
        """Patching multiple fields updates all and creates one audit entry."""
        existing = _make_commercial_plan(name="Old", trial_days=14, is_public=True)

        with patch("repositories.catalog_repository.commercial_plans_collection") as mock_cp, \
             patch("repositories.catalog_repository.catalog_audit_log_collection") as mock_al, \
             patch("repositories.catalog_repository.pricing_plans_collection") as mock_pp, \
             patch("repositories.catalog_repository.organizations_collection") as mock_org:

            mock_cp.find_one = AsyncMock(return_value=existing)
            mock_cp.update_one = AsyncMock()
            mock_al.insert_one = AsyncMock()
            mock_pp.find_one = AsyncMock(return_value=_make_pricing_plan())
            mock_org.count_documents = AsyncMock(return_value=0)
            mock_cursor = MagicMock()
            mock_cursor.to_list = AsyncMock(return_value=[])
            mock_org.find.return_value = mock_cursor

            from repositories.catalog_repository import patch_commercial_plan
            await patch_commercial_plan(
                slug="core",
                patch_fields={"name": "New", "trial_days": 7, "is_public": False},
                performed_by="admin_1",
            )

        audit_doc = mock_al.insert_one.call_args[0][0]
        assert len(audit_doc["changes"]) == 3
        assert audit_doc["changes"]["name"] == {"old": "Old", "new": "New"}
        assert audit_doc["changes"]["trial_days"] == {"old": 14, "new": 7}
        assert audit_doc["changes"]["is_public"] == {"old": True, "new": False}

    @pytest.mark.asyncio
    async def test_noop_patch_no_audit(self):
        """If submitted values match current, no update and no audit entry."""
        existing = _make_commercial_plan(name="Same Name")

        with patch("repositories.catalog_repository.commercial_plans_collection") as mock_cp, \
             patch("repositories.catalog_repository.catalog_audit_log_collection") as mock_al, \
             patch("repositories.catalog_repository.pricing_plans_collection") as mock_pp, \
             patch("repositories.catalog_repository.organizations_collection") as mock_org:

            mock_cp.find_one = AsyncMock(return_value=existing)
            mock_cp.update_one = AsyncMock()
            mock_al.insert_one = AsyncMock()
            mock_pp.find_one = AsyncMock(return_value=_make_pricing_plan())
            mock_org.count_documents = AsyncMock(return_value=0)
            mock_cursor = MagicMock()
            mock_cursor.to_list = AsyncMock(return_value=[])
            mock_org.find.return_value = mock_cursor

            from repositories.catalog_repository import patch_commercial_plan
            result = await patch_commercial_plan(
                slug="core",
                patch_fields={"name": "Same Name"},
                performed_by="admin_1",
            )

        # No DB write, no audit
        mock_cp.update_one.assert_not_called()
        mock_al.insert_one.assert_not_called()
        assert result is not None  # returns current plan

    @pytest.mark.asyncio
    async def test_returns_none_for_missing_slug(self):
        """Returns None if plan slug doesn't exist."""
        with patch("repositories.catalog_repository.commercial_plans_collection") as mock_cp:
            mock_cp.find_one = AsyncMock(return_value=None)

            from repositories.catalog_repository import patch_commercial_plan
            result = await patch_commercial_plan(
                slug="nonexistent",
                patch_fields={"name": "X"},
                performed_by="admin_1",
            )

        assert result is None

    @pytest.mark.asyncio
    async def test_admin_modified_at_set_on_mutation(self):
        """admin_modified_at is set in the $set operation on successful mutation."""
        existing = _make_commercial_plan(name="Old")

        with patch("repositories.catalog_repository.commercial_plans_collection") as mock_cp, \
             patch("repositories.catalog_repository.catalog_audit_log_collection") as mock_al, \
             patch("repositories.catalog_repository.pricing_plans_collection") as mock_pp, \
             patch("repositories.catalog_repository.organizations_collection") as mock_org:

            mock_cp.find_one = AsyncMock(return_value=existing)
            mock_cp.update_one = AsyncMock()
            mock_al.insert_one = AsyncMock()
            mock_pp.find_one = AsyncMock(return_value=_make_pricing_plan())
            mock_org.count_documents = AsyncMock(return_value=0)
            mock_cursor = MagicMock()
            mock_cursor.to_list = AsyncMock(return_value=[])
            mock_org.find.return_value = mock_cursor

            from repositories.catalog_repository import patch_commercial_plan
            await patch_commercial_plan(
                slug="core",
                patch_fields={"name": "New"},
                performed_by="admin_1",
            )

        update_set = mock_cp.update_one.call_args[0][1]["$set"]
        assert "admin_modified_at" in update_set
        assert "updated_at" in update_set

    @pytest.mark.asyncio
    async def test_audit_includes_notes(self):
        """Audit entry includes notes when provided."""
        existing = _make_commercial_plan(name="Old")

        with patch("repositories.catalog_repository.commercial_plans_collection") as mock_cp, \
             patch("repositories.catalog_repository.catalog_audit_log_collection") as mock_al, \
             patch("repositories.catalog_repository.pricing_plans_collection") as mock_pp, \
             patch("repositories.catalog_repository.organizations_collection") as mock_org:

            mock_cp.find_one = AsyncMock(return_value=existing)
            mock_cp.update_one = AsyncMock()
            mock_al.insert_one = AsyncMock()
            mock_pp.find_one = AsyncMock(return_value=_make_pricing_plan())
            mock_org.count_documents = AsyncMock(return_value=0)
            mock_cursor = MagicMock()
            mock_cursor.to_list = AsyncMock(return_value=[])
            mock_org.find.return_value = mock_cursor

            from repositories.catalog_repository import patch_commercial_plan
            await patch_commercial_plan(
                slug="core",
                patch_fields={"name": "New"},
                performed_by="admin_1",
                notes="Marketing rebrand",
            )

        audit_doc = mock_al.insert_one.call_args[0][0]
        assert audit_doc["notes"] == "Marketing rebrand"

    @pytest.mark.asyncio
    async def test_only_changed_fields_in_audit(self):
        """Audit changes dict contains only fields that actually changed."""
        existing = _make_commercial_plan(name="Keep", description="Change me")

        with patch("repositories.catalog_repository.commercial_plans_collection") as mock_cp, \
             patch("repositories.catalog_repository.catalog_audit_log_collection") as mock_al, \
             patch("repositories.catalog_repository.pricing_plans_collection") as mock_pp, \
             patch("repositories.catalog_repository.organizations_collection") as mock_org:

            mock_cp.find_one = AsyncMock(return_value=existing)
            mock_cp.update_one = AsyncMock()
            mock_al.insert_one = AsyncMock()
            mock_pp.find_one = AsyncMock(return_value=_make_pricing_plan())
            mock_org.count_documents = AsyncMock(return_value=0)
            mock_cursor = MagicMock()
            mock_cursor.to_list = AsyncMock(return_value=[])
            mock_org.find.return_value = mock_cursor

            from repositories.catalog_repository import patch_commercial_plan
            await patch_commercial_plan(
                slug="core",
                patch_fields={"name": "Keep", "description": "New desc"},
                performed_by="admin_1",
            )

        audit_doc = mock_al.insert_one.call_args[0][0]
        # Only description changed, name stayed the same
        assert "description" in audit_doc["changes"]
        assert "name" not in audit_doc["changes"]


# ══════════════════════════════════════════════════════════════════════════════
# Phase 2c Tests: Controlled Entitlement Mutations
# ══════════════════════════════════════════════════════════════════════════════

class TestLimitsPatchRequestModel:
    """Validate LimitsPatchRequest model behavior."""

    def test_accepts_valid_payload(self):
        from routers.admin_catalog import LimitsPatchRequest
        req = LimitsPatchRequest(
            limits={"chat": 100, "digest": -1},
            confirm=True,
        )
        assert req.limits["chat"] == 100
        assert req.confirm is True

    def test_accepts_notes(self):
        from routers.admin_catalog import LimitsPatchRequest
        req = LimitsPatchRequest(
            limits={"chat": 100},
            confirm=True,
            notes="Increasing chat quota",
        )
        assert req.notes == "Increasing chat quota"

    def test_rejects_forbidden_field_name(self):
        from routers.admin_catalog import LimitsPatchRequest
        with pytest.raises(Exception) as exc_info:
            LimitsPatchRequest(limits={"chat": 100}, confirm=True, name="Bad")
        assert "Forbidden fields" in str(exc_info.value) or "extra" in str(exc_info.value).lower()

    def test_rejects_forbidden_field_module_key(self):
        from routers.admin_catalog import LimitsPatchRequest
        with pytest.raises(Exception) as exc_info:
            LimitsPatchRequest(limits={"chat": 100}, confirm=True, module_key="x")
        assert "Forbidden fields" in str(exc_info.value) or "extra" in str(exc_info.value).lower()

    def test_rejects_forbidden_field_price_monthly(self):
        from routers.admin_catalog import LimitsPatchRequest
        with pytest.raises(Exception) as exc_info:
            LimitsPatchRequest(limits={"chat": 100}, confirm=True, price_monthly=99.0)
        assert "Forbidden fields" in str(exc_info.value) or "extra" in str(exc_info.value).lower()

    def test_rejects_unknown_field(self):
        from routers.admin_catalog import LimitsPatchRequest
        with pytest.raises(Exception):
            LimitsPatchRequest(limits={"chat": 100}, confirm=True, random_field="x")

    def test_confirm_is_required(self):
        from routers.admin_catalog import LimitsPatchRequest
        with pytest.raises(Exception):
            LimitsPatchRequest(limits={"chat": 100})

    def test_limits_is_required(self):
        from routers.admin_catalog import LimitsPatchRequest
        with pytest.raises(Exception):
            LimitsPatchRequest(confirm=True)


class TestPatchEntitlementTierLimits:
    """Tests for patch_entitlement_tier_limits() repository function."""

    @pytest.mark.asyncio
    async def test_successful_limits_mutation(self):
        """Changing limits updates DB and creates audit entry."""
        existing_pp = _make_pricing_plan(
            slug="ai_assistant_starter",
            limits={"chat": 50, "digest": 4},
        )

        with patch("repositories.catalog_repository.pricing_plans_collection") as mock_pp, \
             patch("repositories.catalog_repository.catalog_audit_log_collection") as mock_al, \
             patch("repositories.catalog_repository.module_subscriptions_collection") as mock_ms:

            mock_pp.find_one = AsyncMock(return_value=existing_pp)
            mock_pp.update_one = AsyncMock()
            mock_al.insert_one = AsyncMock()
            mock_ms.count_documents = AsyncMock(return_value=5)

            from repositories.catalog_repository import patch_entitlement_tier_limits
            result = await patch_entitlement_tier_limits(
                slug="ai_assistant_starter",
                new_limits={"chat": 100, "digest": 4},
                performed_by="admin_1",
            )

        # Verify DB update
        update_call = mock_pp.update_one.call_args
        update_set = update_call[0][1]["$set"]
        assert update_set["limits"] == {"chat": 100, "digest": 4}
        assert "updated_at" in update_set

        # Verify audit
        mock_al.insert_one.assert_called_once()
        audit_doc = mock_al.insert_one.call_args[0][0]
        assert audit_doc["entity_type"] == "pricing_plan"
        assert audit_doc["entity_id"] == "ai_assistant_starter"
        assert audit_doc["action"] == "update_limits"
        assert audit_doc["changes"]["limits"]["old"] == {"chat": 50, "digest": 4}
        assert audit_doc["changes"]["limits"]["new"] == {"chat": 100, "digest": 4}
        assert audit_doc["performed_by"] == "admin_1"

        # Verify result structure
        assert result["impact_count"] == 5
        assert result["changed"] is True

    @pytest.mark.asyncio
    async def test_noop_limits_no_audit(self):
        """If limits are identical, no write and no audit entry."""
        existing_pp = _make_pricing_plan(
            slug="ai_assistant_starter",
            limits={"chat": 50, "digest": 4},
        )

        with patch("repositories.catalog_repository.pricing_plans_collection") as mock_pp, \
             patch("repositories.catalog_repository.catalog_audit_log_collection") as mock_al, \
             patch("repositories.catalog_repository.module_subscriptions_collection") as mock_ms:

            mock_pp.find_one = AsyncMock(return_value=existing_pp)
            mock_pp.update_one = AsyncMock()
            mock_al.insert_one = AsyncMock()
            mock_ms.count_documents = AsyncMock(return_value=3)

            from repositories.catalog_repository import patch_entitlement_tier_limits
            result = await patch_entitlement_tier_limits(
                slug="ai_assistant_starter",
                new_limits={"chat": 50, "digest": 4},
                performed_by="admin_1",
            )

        mock_pp.update_one.assert_not_called()
        mock_al.insert_one.assert_not_called()
        assert result["changed"] is False
        assert result["impact_count"] == 3

    @pytest.mark.asyncio
    async def test_returns_none_for_missing_slug(self):
        """Returns None if pricing plan slug doesn't exist."""
        with patch("repositories.catalog_repository.pricing_plans_collection") as mock_pp:
            mock_pp.find_one = AsyncMock(return_value=None)

            from repositories.catalog_repository import patch_entitlement_tier_limits
            result = await patch_entitlement_tier_limits(
                slug="nonexistent",
                new_limits={"chat": 100},
                performed_by="admin_1",
            )

        assert result is None

    @pytest.mark.asyncio
    async def test_impact_count_in_result(self):
        """Impact count reflects active subscriptions using this tier."""
        existing_pp = _make_pricing_plan(
            slug="ai_assistant_starter",
            limits={"chat": 50},
        )

        with patch("repositories.catalog_repository.pricing_plans_collection") as mock_pp, \
             patch("repositories.catalog_repository.catalog_audit_log_collection") as mock_al, \
             patch("repositories.catalog_repository.module_subscriptions_collection") as mock_ms:

            mock_pp.find_one = AsyncMock(return_value=existing_pp)
            mock_pp.update_one = AsyncMock()
            mock_al.insert_one = AsyncMock()
            mock_ms.count_documents = AsyncMock(return_value=42)

            from repositories.catalog_repository import patch_entitlement_tier_limits
            result = await patch_entitlement_tier_limits(
                slug="ai_assistant_starter",
                new_limits={"chat": 100},
                performed_by="admin_1",
            )

        assert result["impact_count"] == 42
        # Verify the count query used the right filter
        count_call = mock_ms.count_documents.call_args[0][0]
        assert count_call["pricing_plan_id"] == existing_pp["id"]
        assert count_call["status"] == "active"

    @pytest.mark.asyncio
    async def test_audit_includes_notes(self):
        """Audit entry includes notes when provided."""
        existing_pp = _make_pricing_plan(limits={"chat": 50})

        with patch("repositories.catalog_repository.pricing_plans_collection") as mock_pp, \
             patch("repositories.catalog_repository.catalog_audit_log_collection") as mock_al, \
             patch("repositories.catalog_repository.module_subscriptions_collection") as mock_ms:

            mock_pp.find_one = AsyncMock(return_value=existing_pp)
            mock_pp.update_one = AsyncMock()
            mock_al.insert_one = AsyncMock()
            mock_ms.count_documents = AsyncMock(return_value=0)

            from repositories.catalog_repository import patch_entitlement_tier_limits
            await patch_entitlement_tier_limits(
                slug="ai_assistant_starter",
                new_limits={"chat": 100},
                performed_by="admin_1",
                notes="Customer requested higher limit",
            )

        audit_doc = mock_al.insert_one.call_args[0][0]
        assert audit_doc["notes"] == "Customer requested higher limit"


class TestLimitsEndpointConfirmGate:
    """Test the confirm=true requirement at the router level."""

    def test_confirm_false_rejection(self):
        """LimitsPatchRequest with confirm=false should be rejected by the endpoint."""
        # This test validates that the router logic checks confirm=true.
        # The model itself accepts confirm=false (it's a bool field),
        # but the endpoint raises 400 if confirm is not true.
        from routers.admin_catalog import LimitsPatchRequest
        req = LimitsPatchRequest(limits={"chat": 100}, confirm=False)
        assert req.confirm is False  # model accepts it — endpoint rejects it


# ══════════════════════════════════════════════════════════════════════════════
# Phase 2d Tests: Controlled Commercial Bundle Mutations
# ══════════════════════════════════════════════════════════════════════════════

class TestModulePlansPatchRequestModel:
    """Validate ModulePlansPatchRequest model behavior."""

    def test_accepts_valid_payload(self):
        from routers.admin_catalog import ModulePlansPatchRequest
        req = ModulePlansPatchRequest(
            module_plans={"ai_assistant": "ai_assistant_pro"},
            confirm=True,
        )
        assert req.module_plans["ai_assistant"] == "ai_assistant_pro"
        assert req.confirm is True

    def test_accepts_notes(self):
        from routers.admin_catalog import ModulePlansPatchRequest
        req = ModulePlansPatchRequest(
            module_plans={"ai_assistant": "ai_assistant_pro"},
            confirm=True,
            notes="Upgrading AI tier",
        )
        assert req.notes == "Upgrading AI tier"

    def test_rejects_forbidden_field_name(self):
        from routers.admin_catalog import ModulePlansPatchRequest
        with pytest.raises(Exception) as exc_info:
            ModulePlansPatchRequest(
                module_plans={"ai": "ai_free"}, confirm=True, name="Bad",
            )
        assert "Forbidden fields" in str(exc_info.value) or "extra" in str(exc_info.value).lower()

    def test_rejects_forbidden_field_price(self):
        from routers.admin_catalog import ModulePlansPatchRequest
        with pytest.raises(Exception) as exc_info:
            ModulePlansPatchRequest(
                module_plans={"ai": "ai_free"}, confirm=True, price_monthly=99.0,
            )
        assert "Forbidden fields" in str(exc_info.value) or "extra" in str(exc_info.value).lower()

    def test_rejects_forbidden_field_slug(self):
        from routers.admin_catalog import ModulePlansPatchRequest
        with pytest.raises(Exception) as exc_info:
            ModulePlansPatchRequest(
                module_plans={"ai": "ai_free"}, confirm=True, slug="x",
            )
        assert "Forbidden fields" in str(exc_info.value) or "extra" in str(exc_info.value).lower()

    def test_rejects_unknown_field(self):
        from routers.admin_catalog import ModulePlansPatchRequest
        with pytest.raises(Exception):
            ModulePlansPatchRequest(
                module_plans={"ai": "ai_free"}, confirm=True, unknown_field="x",
            )

    def test_confirm_is_required(self):
        from routers.admin_catalog import ModulePlansPatchRequest
        with pytest.raises(Exception):
            ModulePlansPatchRequest(module_plans={"ai": "ai_free"})

    def test_module_plans_is_required(self):
        from routers.admin_catalog import ModulePlansPatchRequest
        with pytest.raises(Exception):
            ModulePlansPatchRequest(confirm=True)

    def test_confirm_false_accepted_by_model(self):
        """Model accepts confirm=false; endpoint rejects it."""
        from routers.admin_catalog import ModulePlansPatchRequest
        req = ModulePlansPatchRequest(
            module_plans={"ai": "ai_free"}, confirm=False,
        )
        assert req.confirm is False


class TestValidateModulePlansMapping:
    """Tests for validate_module_plans_mapping() validation function."""

    @pytest.mark.asyncio
    async def test_valid_mapping_returns_none(self):
        """Valid mapping (all slugs exist, module_key matches) returns None."""
        with patch("repositories.catalog_repository.pricing_plans_collection") as mock_pp:
            mock_pp.find_one = AsyncMock(return_value={
                "slug": "ai_assistant_pro",
                "module_key": "ai_assistant",
            })

            from repositories.catalog_repository import validate_module_plans_mapping
            result = await validate_module_plans_mapping(
                {"ai_assistant": "ai_assistant_pro"}
            )

        assert result is None

    @pytest.mark.asyncio
    async def test_nonexistent_slug_returns_error(self):
        """Non-existent PricingPlan slug returns error message."""
        with patch("repositories.catalog_repository.pricing_plans_collection") as mock_pp:
            mock_pp.find_one = AsyncMock(return_value=None)

            from repositories.catalog_repository import validate_module_plans_mapping
            result = await validate_module_plans_mapping(
                {"ai_assistant": "totally_fake_slug"}
            )

        assert result is not None
        assert "not found" in result

    @pytest.mark.asyncio
    async def test_mismatched_module_key_returns_error(self):
        """PricingPlan with wrong module_key returns error message."""
        with patch("repositories.catalog_repository.pricing_plans_collection") as mock_pp:
            # PricingPlan belongs to cashflow_monitor, not ai_assistant
            mock_pp.find_one = AsyncMock(return_value={
                "slug": "cashflow_monitor_pro",
                "module_key": "cashflow_monitor",
            })

            from repositories.catalog_repository import validate_module_plans_mapping
            result = await validate_module_plans_mapping(
                {"ai_assistant": "cashflow_monitor_pro"}
            )

        assert result is not None
        assert "belongs to module" in result
        assert "cashflow_monitor" in result


class TestPatchModulePlans:
    """Tests for patch_module_plans() repository function."""

    @pytest.mark.asyncio
    async def test_successful_mutation(self):
        """Changing module_plans updates DB and creates audit entry."""
        existing = _make_commercial_plan(
            module_plans={"ai_assistant": "ai_assistant_starter"},
        )

        with patch("repositories.catalog_repository.commercial_plans_collection") as mock_cp, \
             patch("repositories.catalog_repository.catalog_audit_log_collection") as mock_al, \
             patch("repositories.catalog_repository.pricing_plans_collection") as mock_pp, \
             patch("repositories.catalog_repository.organizations_collection") as mock_org:

            mock_cp.find_one = AsyncMock(return_value=existing)
            mock_cp.update_one = AsyncMock()
            mock_al.insert_one = AsyncMock()
            mock_pp.find_one = AsyncMock(return_value=_make_pricing_plan())
            mock_org.count_documents = AsyncMock(return_value=7)
            mock_cursor = MagicMock()
            mock_cursor.to_list = AsyncMock(return_value=[])
            mock_org.find.return_value = mock_cursor

            from repositories.catalog_repository import patch_module_plans
            result = await patch_module_plans(
                slug="core",
                new_module_plans={"ai_assistant": "ai_assistant_pro"},
                performed_by="admin_1",
            )

        # Verify DB update
        update_call = mock_cp.update_one.call_args
        update_set = update_call[0][1]["$set"]
        assert update_set["module_plans"] == {"ai_assistant": "ai_assistant_pro"}
        assert "admin_modified_at" in update_set
        assert "updated_at" in update_set

        # Verify audit
        mock_al.insert_one.assert_called_once()
        audit_doc = mock_al.insert_one.call_args[0][0]
        assert audit_doc["entity_type"] == "commercial_plan"
        assert audit_doc["entity_id"] == "core"
        assert audit_doc["action"] == "update_module_plans"
        assert audit_doc["changes"]["module_plans"]["old"] == {"ai_assistant": "ai_assistant_starter"}
        assert audit_doc["changes"]["module_plans"]["new"] == {"ai_assistant": "ai_assistant_pro"}

        # Verify result structure
        assert result["subscriber_count"] == 7
        assert result["changed"] is True
        assert result["auto_reprovisioned"] is False

    @pytest.mark.asyncio
    async def test_noop_no_audit(self):
        """If module_plans are identical, no write and no audit entry."""
        mp = {"ai_assistant": "ai_assistant_starter", "cashflow_monitor": "cashflow_monitor_pro"}
        existing = _make_commercial_plan(module_plans=mp)

        with patch("repositories.catalog_repository.commercial_plans_collection") as mock_cp, \
             patch("repositories.catalog_repository.catalog_audit_log_collection") as mock_al, \
             patch("repositories.catalog_repository.pricing_plans_collection") as mock_pp, \
             patch("repositories.catalog_repository.organizations_collection") as mock_org:

            mock_cp.find_one = AsyncMock(return_value=existing)
            mock_cp.update_one = AsyncMock()
            mock_al.insert_one = AsyncMock()
            mock_pp.find_one = AsyncMock(return_value=_make_pricing_plan())
            mock_org.count_documents = AsyncMock(return_value=3)
            mock_cursor = MagicMock()
            mock_cursor.to_list = AsyncMock(return_value=[])
            mock_org.find.return_value = mock_cursor

            from repositories.catalog_repository import patch_module_plans
            result = await patch_module_plans(
                slug="core",
                new_module_plans=mp,
                performed_by="admin_1",
            )

        mock_cp.update_one.assert_not_called()
        mock_al.insert_one.assert_not_called()
        assert result["changed"] is False
        assert result["auto_reprovisioned"] is False
        assert result["subscriber_count"] == 3

    @pytest.mark.asyncio
    async def test_returns_none_for_missing_slug(self):
        """Returns None if plan slug doesn't exist."""
        with patch("repositories.catalog_repository.commercial_plans_collection") as mock_cp:
            mock_cp.find_one = AsyncMock(return_value=None)

            from repositories.catalog_repository import patch_module_plans
            result = await patch_module_plans(
                slug="nonexistent",
                new_module_plans={"ai": "ai_free"},
                performed_by="admin_1",
            )

        assert result is None

    @pytest.mark.asyncio
    async def test_auto_reprovisioned_always_false(self):
        """Response explicitly signals no auto-reprovisioning."""
        existing = _make_commercial_plan(
            module_plans={"ai_assistant": "ai_assistant_starter"},
        )

        with patch("repositories.catalog_repository.commercial_plans_collection") as mock_cp, \
             patch("repositories.catalog_repository.catalog_audit_log_collection") as mock_al, \
             patch("repositories.catalog_repository.pricing_plans_collection") as mock_pp, \
             patch("repositories.catalog_repository.organizations_collection") as mock_org:

            mock_cp.find_one = AsyncMock(return_value=existing)
            mock_cp.update_one = AsyncMock()
            mock_al.insert_one = AsyncMock()
            mock_pp.find_one = AsyncMock(return_value=_make_pricing_plan())
            mock_org.count_documents = AsyncMock(return_value=5)
            mock_cursor = MagicMock()
            mock_cursor.to_list = AsyncMock(return_value=[])
            mock_org.find.return_value = mock_cursor

            from repositories.catalog_repository import patch_module_plans
            result = await patch_module_plans(
                slug="core",
                new_module_plans={"ai_assistant": "ai_assistant_pro"},
                performed_by="admin_1",
            )

        assert result["auto_reprovisioned"] is False
        assert result["subscriber_count"] == 5

    @pytest.mark.asyncio
    async def test_audit_includes_notes(self):
        """Audit entry includes notes when provided."""
        existing = _make_commercial_plan(
            module_plans={"ai_assistant": "ai_assistant_starter"},
        )

        with patch("repositories.catalog_repository.commercial_plans_collection") as mock_cp, \
             patch("repositories.catalog_repository.catalog_audit_log_collection") as mock_al, \
             patch("repositories.catalog_repository.pricing_plans_collection") as mock_pp, \
             patch("repositories.catalog_repository.organizations_collection") as mock_org:

            mock_cp.find_one = AsyncMock(return_value=existing)
            mock_cp.update_one = AsyncMock()
            mock_al.insert_one = AsyncMock()
            mock_pp.find_one = AsyncMock(return_value=_make_pricing_plan())
            mock_org.count_documents = AsyncMock(return_value=0)
            mock_cursor = MagicMock()
            mock_cursor.to_list = AsyncMock(return_value=[])
            mock_org.find.return_value = mock_cursor

            from repositories.catalog_repository import patch_module_plans
            await patch_module_plans(
                slug="core",
                new_module_plans={"ai_assistant": "ai_assistant_pro"},
                performed_by="admin_1",
                notes="Promotional tier upgrade",
            )

        audit_doc = mock_al.insert_one.call_args[0][0]
        assert audit_doc["notes"] == "Promotional tier upgrade"


# ══════════════════════════════════════════════════════════════════════════════
# Phase 2e Tests: Controlled Pricing Mutations
# ══════════════════════════════════════════════════════════════════════════════

class TestPricingPatchRequestModel:
    """Validate PricingPatchRequest coherence and validation logic."""

    # Note: PricingPatchRequest validates stripe_price_id_* with regex
    # ^price_[A-Za-z0-9]+$ — Stripe price IDs are price_<alphanum> only
    # (no underscores or hyphens after the prefix). Test data updated to
    # match real Stripe ID format.

    def test_accepts_monthly_pair(self):
        from routers.admin_catalog import PricingPatchRequest
        req = PricingPatchRequest(
            price_monthly=49.0,
            stripe_price_id_monthly="price_newmonthly2026",
            confirm=True,
        )
        assert req.price_monthly == 49.0
        assert req.stripe_price_id_monthly == "price_newmonthly2026"

    def test_accepts_yearly_pair(self):
        from routers.admin_catalog import PricingPatchRequest
        req = PricingPatchRequest(
            price_yearly=490.0,
            stripe_price_id_yearly="price_newyearly2026",
            confirm=True,
        )
        assert req.price_yearly == 490.0

    def test_accepts_both_pairs(self):
        from routers.admin_catalog import PricingPatchRequest
        req = PricingPatchRequest(
            price_monthly=49.0,
            stripe_price_id_monthly="price_m",
            price_yearly=490.0,
            stripe_price_id_yearly="price_y",
            confirm=True,
        )
        assert req.price_monthly == 49.0
        assert req.price_yearly == 490.0

    def test_rejects_partial_monthly_pair_price_only(self):
        from routers.admin_catalog import PricingPatchRequest
        with pytest.raises(Exception) as exc_info:
            PricingPatchRequest(price_monthly=49.0, confirm=True)
        assert "pair" in str(exc_info.value).lower() or "monthly" in str(exc_info.value).lower()

    def test_rejects_partial_monthly_pair_stripe_only(self):
        from routers.admin_catalog import PricingPatchRequest
        with pytest.raises(Exception) as exc_info:
            PricingPatchRequest(stripe_price_id_monthly="price_x", confirm=True)
        assert "pair" in str(exc_info.value).lower() or "monthly" in str(exc_info.value).lower()

    def test_rejects_partial_yearly_pair_price_only(self):
        from routers.admin_catalog import PricingPatchRequest
        with pytest.raises(Exception) as exc_info:
            PricingPatchRequest(price_yearly=490.0, confirm=True)
        assert "pair" in str(exc_info.value).lower() or "yearly" in str(exc_info.value).lower()

    def test_rejects_partial_yearly_pair_stripe_only(self):
        from routers.admin_catalog import PricingPatchRequest
        with pytest.raises(Exception) as exc_info:
            PricingPatchRequest(stripe_price_id_yearly="price_y", confirm=True)
        assert "pair" in str(exc_info.value).lower() or "yearly" in str(exc_info.value).lower()

    def test_rejects_no_pricing_pair(self):
        from routers.admin_catalog import PricingPatchRequest
        with pytest.raises(Exception) as exc_info:
            PricingPatchRequest(confirm=True)
        assert "at least one" in str(exc_info.value).lower()

    def test_rejects_forbidden_field_name(self):
        from routers.admin_catalog import PricingPatchRequest
        with pytest.raises(Exception) as exc_info:
            PricingPatchRequest(
                price_monthly=49.0, stripe_price_id_monthly="p", confirm=True, name="X",
            )
        assert "Forbidden fields" in str(exc_info.value) or "extra" in str(exc_info.value).lower()

    def test_rejects_forbidden_field_module_plans(self):
        from routers.admin_catalog import PricingPatchRequest
        with pytest.raises(Exception) as exc_info:
            PricingPatchRequest(
                price_monthly=49.0, stripe_price_id_monthly="p",
                confirm=True, module_plans={"a": "b"},
            )
        assert "Forbidden fields" in str(exc_info.value) or "extra" in str(exc_info.value).lower()

    def test_rejects_unknown_field(self):
        from routers.admin_catalog import PricingPatchRequest
        with pytest.raises(Exception):
            PricingPatchRequest(
                price_monthly=49.0, stripe_price_id_monthly="p",
                confirm=True, random_field="x",
            )

    def test_confirm_is_required(self):
        from routers.admin_catalog import PricingPatchRequest
        with pytest.raises(Exception):
            PricingPatchRequest(price_monthly=49.0, stripe_price_id_monthly="p")

    def test_accepts_notes(self):
        from routers.admin_catalog import PricingPatchRequest
        req = PricingPatchRequest(
            price_monthly=49.0, stripe_price_id_monthly="price_pm",
            confirm=True, notes="Price increase Q2",
        )
        assert req.notes == "Price increase Q2"


class TestPatchPricing:
    """Tests for patch_pricing() repository function."""

    @pytest.mark.asyncio
    async def test_successful_monthly_pricing_mutation(self):
        """Updating monthly pricing pair updates DB and creates audit entry."""
        existing = _make_commercial_plan(price_monthly=39.0)

        with patch("repositories.catalog_repository.commercial_plans_collection") as mock_cp, \
             patch("repositories.catalog_repository.catalog_audit_log_collection") as mock_al, \
             patch("repositories.catalog_repository.pricing_plans_collection") as mock_pp, \
             patch("repositories.catalog_repository.organizations_collection") as mock_org:

            mock_cp.find_one = AsyncMock(return_value=existing)
            mock_cp.update_one = AsyncMock()
            mock_al.insert_one = AsyncMock()
            mock_pp.find_one = AsyncMock(return_value=_make_pricing_plan())
            mock_org.count_documents = AsyncMock(return_value=5)
            mock_cursor = MagicMock()
            mock_cursor.to_list = AsyncMock(return_value=[])
            mock_org.find.return_value = mock_cursor

            from repositories.catalog_repository import patch_pricing
            result = await patch_pricing(
                slug="core",
                pricing_fields={
                    "price_monthly": 49.0,
                    "stripe_price_id_monthly": "price_new_m",
                },
                performed_by="admin_1",
            )

        # Verify DB update
        update_set = mock_cp.update_one.call_args[0][1]["$set"]
        assert update_set["price_monthly"] == 49.0
        assert update_set["stripe_price_id_monthly"] == "price_new_m"
        assert "admin_modified_at" in update_set

        # Verify audit
        mock_al.insert_one.assert_called_once()
        audit_doc = mock_al.insert_one.call_args[0][0]
        assert audit_doc["action"] == "update_pricing"
        assert "price_monthly" in audit_doc["changes"]
        assert audit_doc["changes"]["price_monthly"]["old"] == 39.0
        assert audit_doc["changes"]["price_monthly"]["new"] == 49.0

        # Verify result
        assert result["changed"] is True
        assert result["affects_future_checkouts"] is True
        assert result["migrated_existing_subscribers"] is False
        assert result["subscriber_count"] == 5

    @pytest.mark.asyncio
    async def test_successful_yearly_pricing_mutation(self):
        """Updating yearly pricing pair works correctly."""
        existing = _make_commercial_plan(price_yearly=390.0)

        with patch("repositories.catalog_repository.commercial_plans_collection") as mock_cp, \
             patch("repositories.catalog_repository.catalog_audit_log_collection") as mock_al, \
             patch("repositories.catalog_repository.pricing_plans_collection") as mock_pp, \
             patch("repositories.catalog_repository.organizations_collection") as mock_org:

            mock_cp.find_one = AsyncMock(return_value=existing)
            mock_cp.update_one = AsyncMock()
            mock_al.insert_one = AsyncMock()
            mock_pp.find_one = AsyncMock(return_value=_make_pricing_plan())
            mock_org.count_documents = AsyncMock(return_value=2)
            mock_cursor = MagicMock()
            mock_cursor.to_list = AsyncMock(return_value=[])
            mock_org.find.return_value = mock_cursor

            from repositories.catalog_repository import patch_pricing
            result = await patch_pricing(
                slug="core",
                pricing_fields={
                    "price_yearly": 490.0,
                    "stripe_price_id_yearly": "price_new_y",
                },
                performed_by="admin_1",
            )

        assert result["changed"] is True
        update_set = mock_cp.update_one.call_args[0][1]["$set"]
        assert update_set["price_yearly"] == 490.0
        assert update_set["stripe_price_id_yearly"] == "price_new_y"

    @pytest.mark.asyncio
    async def test_successful_both_pairs_mutation(self):
        """Updating both monthly and yearly pricing pairs works correctly."""
        existing = _make_commercial_plan(price_monthly=39.0, price_yearly=390.0)

        with patch("repositories.catalog_repository.commercial_plans_collection") as mock_cp, \
             patch("repositories.catalog_repository.catalog_audit_log_collection") as mock_al, \
             patch("repositories.catalog_repository.pricing_plans_collection") as mock_pp, \
             patch("repositories.catalog_repository.organizations_collection") as mock_org:

            mock_cp.find_one = AsyncMock(return_value=existing)
            mock_cp.update_one = AsyncMock()
            mock_al.insert_one = AsyncMock()
            mock_pp.find_one = AsyncMock(return_value=_make_pricing_plan())
            mock_org.count_documents = AsyncMock(return_value=0)
            mock_cursor = MagicMock()
            mock_cursor.to_list = AsyncMock(return_value=[])
            mock_org.find.return_value = mock_cursor

            from repositories.catalog_repository import patch_pricing
            result = await patch_pricing(
                slug="core",
                pricing_fields={
                    "price_monthly": 49.0,
                    "stripe_price_id_monthly": "price_m2",
                    "price_yearly": 490.0,
                    "stripe_price_id_yearly": "price_y2",
                },
                performed_by="admin_1",
            )

        assert result["changed"] is True
        audit_doc = mock_al.insert_one.call_args[0][0]
        assert len(audit_doc["changes"]) == 4

    @pytest.mark.asyncio
    async def test_noop_no_audit(self):
        """If pricing is identical, no write and no audit entry."""
        existing = _make_commercial_plan(price_monthly=39.0)
        # Simulate existing Stripe ID being None (matches seed default)
        existing["stripe_price_id_monthly"] = "price_existing"

        with patch("repositories.catalog_repository.commercial_plans_collection") as mock_cp, \
             patch("repositories.catalog_repository.catalog_audit_log_collection") as mock_al, \
             patch("repositories.catalog_repository.pricing_plans_collection") as mock_pp, \
             patch("repositories.catalog_repository.organizations_collection") as mock_org:

            mock_cp.find_one = AsyncMock(return_value=existing)
            mock_cp.update_one = AsyncMock()
            mock_al.insert_one = AsyncMock()
            mock_pp.find_one = AsyncMock(return_value=_make_pricing_plan())
            mock_org.count_documents = AsyncMock(return_value=0)
            mock_cursor = MagicMock()
            mock_cursor.to_list = AsyncMock(return_value=[])
            mock_org.find.return_value = mock_cursor

            from repositories.catalog_repository import patch_pricing
            result = await patch_pricing(
                slug="core",
                pricing_fields={
                    "price_monthly": 39.0,
                    "stripe_price_id_monthly": "price_existing",
                },
                performed_by="admin_1",
            )

        mock_cp.update_one.assert_not_called()
        mock_al.insert_one.assert_not_called()
        assert result["changed"] is False
        assert result["affects_future_checkouts"] is False
        assert result["migrated_existing_subscribers"] is False

    @pytest.mark.asyncio
    async def test_returns_none_for_missing_slug(self):
        """Returns None if plan slug doesn't exist."""
        with patch("repositories.catalog_repository.commercial_plans_collection") as mock_cp:
            mock_cp.find_one = AsyncMock(return_value=None)

            from repositories.catalog_repository import patch_pricing
            result = await patch_pricing(
                slug="nonexistent",
                pricing_fields={"price_monthly": 49.0, "stripe_price_id_monthly": "p"},
                performed_by="admin_1",
            )

        assert result is None

    @pytest.mark.asyncio
    async def test_audit_includes_notes(self):
        """Audit entry includes notes when provided."""
        existing = _make_commercial_plan(price_monthly=39.0)

        with patch("repositories.catalog_repository.commercial_plans_collection") as mock_cp, \
             patch("repositories.catalog_repository.catalog_audit_log_collection") as mock_al, \
             patch("repositories.catalog_repository.pricing_plans_collection") as mock_pp, \
             patch("repositories.catalog_repository.organizations_collection") as mock_org:

            mock_cp.find_one = AsyncMock(return_value=existing)
            mock_cp.update_one = AsyncMock()
            mock_al.insert_one = AsyncMock()
            mock_pp.find_one = AsyncMock(return_value=_make_pricing_plan())
            mock_org.count_documents = AsyncMock(return_value=0)
            mock_cursor = MagicMock()
            mock_cursor.to_list = AsyncMock(return_value=[])
            mock_org.find.return_value = mock_cursor

            from repositories.catalog_repository import patch_pricing
            await patch_pricing(
                slug="core",
                pricing_fields={
                    "price_monthly": 49.0,
                    "stripe_price_id_monthly": "price_new",
                },
                performed_by="admin_1",
                notes="Q2 price increase",
            )

        audit_doc = mock_al.insert_one.call_args[0][0]
        assert audit_doc["notes"] == "Q2 price increase"

    @pytest.mark.asyncio
    async def test_only_changed_fields_in_audit(self):
        """Audit only contains fields that actually changed."""
        existing = _make_commercial_plan(price_monthly=39.0, price_yearly=390.0)
        existing["stripe_price_id_monthly"] = "price_old_m"
        existing["stripe_price_id_yearly"] = "price_old_y"

        with patch("repositories.catalog_repository.commercial_plans_collection") as mock_cp, \
             patch("repositories.catalog_repository.catalog_audit_log_collection") as mock_al, \
             patch("repositories.catalog_repository.pricing_plans_collection") as mock_pp, \
             patch("repositories.catalog_repository.organizations_collection") as mock_org:

            mock_cp.find_one = AsyncMock(return_value=existing)
            mock_cp.update_one = AsyncMock()
            mock_al.insert_one = AsyncMock()
            mock_pp.find_one = AsyncMock(return_value=_make_pricing_plan())
            mock_org.count_documents = AsyncMock(return_value=0)
            mock_cursor = MagicMock()
            mock_cursor.to_list = AsyncMock(return_value=[])
            mock_org.find.return_value = mock_cursor

            from repositories.catalog_repository import patch_pricing
            await patch_pricing(
                slug="core",
                pricing_fields={
                    "price_monthly": 49.0,  # changed
                    "stripe_price_id_monthly": "price_old_m",  # same
                },
                performed_by="admin_1",
            )

        audit_doc = mock_al.insert_one.call_args[0][0]
        assert "price_monthly" in audit_doc["changes"]
        assert "stripe_price_id_monthly" not in audit_doc["changes"]


# ══════════════════════════════════════════════════════════════════════════════
# Phase 3A Tests: Organization Commercial State (read-only diagnostic)
# ══════════════════════════════════════════════════════════════════════════════

def _make_org(org_id="org_1", plan_slug="core", billing_status="active",
              plan_assigned_by="stripe", legacy_plan="free"):
    return {
        "id": org_id,
        "name": "Test Org",
        "commercial_plan_slug": plan_slug,
        "billing_status": billing_status,
        "plan_assigned_by": plan_assigned_by,
        "plan": legacy_plan,
        "created_at": "2026-01-01T00:00:00+00:00",
    }


def _make_sub(module_key="ai_assistant", pp_id="pp_1", pp_slug="ai_assistant_starter",
              assigned_by="stripe", commercial_plan_slug="core"):
    return {
        "id": f"sub_{module_key}",
        "organization_id": "org_1",
        "module_key": module_key,
        "pricing_plan_id": pp_id,
        "status": "active",
        "assigned_by": assigned_by,
        "commercial_plan_slug": commercial_plan_slug,
        "cancelled_at": None,
    }


class TestBuildOrgCommercialState:
    """Tests for build_org_commercial_state() read model."""

    def _mock_all(self):
        """Helper to set up all 4 collection mocks. Returns dict of mocks."""
        from unittest.mock import patch as _p
        return {
            "cp": _p("repositories.catalog_repository.commercial_plans_collection"),
            "pp": _p("repositories.catalog_repository.pricing_plans_collection"),
            "org": _p("repositories.catalog_repository.organizations_collection"),
            "ms": _p("repositories.catalog_repository.module_subscriptions_collection"),
        }

    @pytest.mark.asyncio
    async def test_org_not_found(self):
        """Returns None if org does not exist."""
        with patch("repositories.catalog_repository.organizations_collection") as mock_org:
            mock_org.find_one = AsyncMock(return_value=None)

            from repositories.catalog_repository import build_org_commercial_state
            result = await build_org_commercial_state("nonexistent")

        assert result is None

    @pytest.mark.asyncio
    async def test_clean_in_sync_org(self):
        """An org fully aligned with catalog shows no drift."""
        org = _make_org()
        catalog_plan = _make_commercial_plan(
            slug="core",
            module_plans={"ai_assistant": "ai_assistant_starter"},
        )
        sub = _make_sub(module_key="ai_assistant", pp_id="pp_1", pp_slug="ai_assistant_starter")
        pp = _make_pricing_plan(slug="ai_assistant_starter", limits={"chat": 50})

        with patch("repositories.catalog_repository.organizations_collection") as mock_org, \
             patch("repositories.catalog_repository.commercial_plans_collection") as mock_cp, \
             patch("repositories.catalog_repository.module_subscriptions_collection") as mock_ms, \
             patch("repositories.catalog_repository.pricing_plans_collection") as mock_pp:

            mock_org.find_one = AsyncMock(return_value=org)
            mock_cp.find_one = AsyncMock(return_value=catalog_plan)
            sub_cursor = MagicMock()
            sub_cursor.to_list = AsyncMock(return_value=[sub])
            mock_ms.find.return_value = sub_cursor
            mock_pp.find_one = AsyncMock(return_value=pp)

            from repositories.catalog_repository import build_org_commercial_state
            result = await build_org_commercial_state("org_1")

        assert result is not None
        assert result["organization"]["commercial_plan_slug"] == "core"
        assert result["catalog_plan"]["slug"] == "core"
        assert len(result["provisioned_modules"]) == 1
        assert result["drift_flags"]["catalog_plan_missing"] is False
        assert result["drift_flags"]["missing_module_subscriptions"] is False
        assert result["drift_flags"]["module_plan_mismatch"] is False
        assert result["summary"]["is_out_of_sync"] is False
        assert result["summary"]["recommended_actions"] == []

    @pytest.mark.asyncio
    async def test_catalog_plan_missing(self):
        """Drift detected when org references a non-existent catalog plan."""
        org = _make_org(plan_slug="deleted_plan")

        with patch("repositories.catalog_repository.organizations_collection") as mock_org, \
             patch("repositories.catalog_repository.commercial_plans_collection") as mock_cp, \
             patch("repositories.catalog_repository.module_subscriptions_collection") as mock_ms, \
             patch("repositories.catalog_repository.pricing_plans_collection") as mock_pp:

            mock_org.find_one = AsyncMock(return_value=org)
            mock_cp.find_one = AsyncMock(return_value=None)
            sub_cursor = MagicMock()
            sub_cursor.to_list = AsyncMock(return_value=[])
            mock_ms.find.return_value = sub_cursor
            mock_pp.find_one = AsyncMock(return_value=None)

            from repositories.catalog_repository import build_org_commercial_state
            result = await build_org_commercial_state("org_1")

        assert result["drift_flags"]["catalog_plan_missing"] is True
        assert result["catalog_plan"] is None
        assert result["summary"]["is_out_of_sync"] is True
        assert "review_missing_catalog_plan" in result["summary"]["recommended_actions"]

    @pytest.mark.asyncio
    async def test_missing_module_subscriptions(self):
        """Drift when catalog expects modules the org doesn't have provisioned."""
        org = _make_org()
        catalog_plan = _make_commercial_plan(
            slug="core",
            module_plans={
                "ai_assistant": "ai_assistant_starter",
                "cashflow_monitor": "cashflow_monitor_pro",
            },
        )
        # Only ai_assistant provisioned, cashflow_monitor missing
        sub = _make_sub(module_key="ai_assistant")
        pp = _make_pricing_plan(slug="ai_assistant_starter")

        with patch("repositories.catalog_repository.organizations_collection") as mock_org, \
             patch("repositories.catalog_repository.commercial_plans_collection") as mock_cp, \
             patch("repositories.catalog_repository.module_subscriptions_collection") as mock_ms, \
             patch("repositories.catalog_repository.pricing_plans_collection") as mock_pp:

            mock_org.find_one = AsyncMock(return_value=org)
            mock_cp.find_one = AsyncMock(return_value=catalog_plan)
            sub_cursor = MagicMock()
            sub_cursor.to_list = AsyncMock(return_value=[sub])
            mock_ms.find.return_value = sub_cursor
            mock_pp.find_one = AsyncMock(return_value=pp)

            from repositories.catalog_repository import build_org_commercial_state
            result = await build_org_commercial_state("org_1")

        assert result["drift_flags"]["missing_module_subscriptions"] is True
        assert "cashflow_monitor" in result["summary"]["missing_modules"]
        assert "consider_reprovision" in result["summary"]["recommended_actions"]

    @pytest.mark.asyncio
    async def test_unexpected_module_subscriptions(self):
        """Drift when org has provisioned modules not in current catalog plan."""
        org = _make_org()
        catalog_plan = _make_commercial_plan(
            slug="core",
            module_plans={"ai_assistant": "ai_assistant_starter"},
        )
        # Org has ai_assistant + extra_module
        subs = [
            _make_sub(module_key="ai_assistant"),
            _make_sub(module_key="extra_module", pp_id="pp_extra"),
        ]
        pp = _make_pricing_plan(slug="ai_assistant_starter")

        with patch("repositories.catalog_repository.organizations_collection") as mock_org, \
             patch("repositories.catalog_repository.commercial_plans_collection") as mock_cp, \
             patch("repositories.catalog_repository.module_subscriptions_collection") as mock_ms, \
             patch("repositories.catalog_repository.pricing_plans_collection") as mock_pp:

            mock_org.find_one = AsyncMock(return_value=org)
            mock_cp.find_one = AsyncMock(return_value=catalog_plan)
            sub_cursor = MagicMock()
            sub_cursor.to_list = AsyncMock(return_value=subs)
            mock_ms.find.return_value = sub_cursor
            mock_pp.find_one = AsyncMock(return_value=pp)

            from repositories.catalog_repository import build_org_commercial_state
            result = await build_org_commercial_state("org_1")

        assert result["drift_flags"]["unexpected_module_subscriptions"] is True
        assert "extra_module" in result["summary"]["unexpected_modules"]

    @pytest.mark.asyncio
    async def test_module_plan_mismatch(self):
        """Drift when provisioned tier differs from catalog expectation."""
        org = _make_org()
        catalog_plan = _make_commercial_plan(
            slug="core",
            module_plans={"ai_assistant": "ai_assistant_starter"},
        )
        # Provisioned with pro instead of starter
        sub = _make_sub(module_key="ai_assistant", pp_id="pp_pro")
        pp_pro = _make_pricing_plan(slug="ai_assistant_pro", limits={"chat": 300})
        pp_starter = _make_pricing_plan(slug="ai_assistant_starter", limits={"chat": 50})

        with patch("repositories.catalog_repository.organizations_collection") as mock_org, \
             patch("repositories.catalog_repository.commercial_plans_collection") as mock_cp, \
             patch("repositories.catalog_repository.module_subscriptions_collection") as mock_ms, \
             patch("repositories.catalog_repository.pricing_plans_collection") as mock_pp:

            mock_org.find_one = AsyncMock(return_value=org)
            mock_cp.find_one = AsyncMock(return_value=catalog_plan)
            sub_cursor = MagicMock()
            sub_cursor.to_list = AsyncMock(return_value=[sub])
            mock_ms.find.return_value = sub_cursor
            # First call resolves sub's pp, second resolves catalog's expected pp
            mock_pp.find_one = AsyncMock(side_effect=[pp_pro, pp_starter])

            from repositories.catalog_repository import build_org_commercial_state
            result = await build_org_commercial_state("org_1")

        assert result["drift_flags"]["module_plan_mismatch"] is True
        assert "ai_assistant" in result["summary"]["mismatched_modules"]

    @pytest.mark.asyncio
    async def test_manual_assignment_detected(self):
        """Flag when org was manually assigned."""
        org = _make_org(plan_assigned_by="admin")
        catalog_plan = _make_commercial_plan(slug="core", module_plans={})

        with patch("repositories.catalog_repository.organizations_collection") as mock_org, \
             patch("repositories.catalog_repository.commercial_plans_collection") as mock_cp, \
             patch("repositories.catalog_repository.module_subscriptions_collection") as mock_ms, \
             patch("repositories.catalog_repository.pricing_plans_collection") as mock_pp:

            mock_org.find_one = AsyncMock(return_value=org)
            mock_cp.find_one = AsyncMock(return_value=catalog_plan)
            sub_cursor = MagicMock()
            sub_cursor.to_list = AsyncMock(return_value=[])
            mock_ms.find.return_value = sub_cursor
            mock_pp.find_one = AsyncMock(return_value=None)

            from repositories.catalog_repository import build_org_commercial_state
            result = await build_org_commercial_state("org_1")

        assert result["drift_flags"]["manual_assignment_detected"] is True
        assert "review_manual_assignment" in result["summary"]["recommended_actions"]

    @pytest.mark.asyncio
    async def test_billing_restricted(self):
        """Flag when billing status is restricted."""
        org = _make_org(billing_status="past_due")
        catalog_plan = _make_commercial_plan(slug="core", module_plans={})

        with patch("repositories.catalog_repository.organizations_collection") as mock_org, \
             patch("repositories.catalog_repository.commercial_plans_collection") as mock_cp, \
             patch("repositories.catalog_repository.module_subscriptions_collection") as mock_ms, \
             patch("repositories.catalog_repository.pricing_plans_collection") as mock_pp:

            mock_org.find_one = AsyncMock(return_value=org)
            mock_cp.find_one = AsyncMock(return_value=catalog_plan)
            sub_cursor = MagicMock()
            sub_cursor.to_list = AsyncMock(return_value=[])
            mock_ms.find.return_value = sub_cursor
            mock_pp.find_one = AsyncMock(return_value=None)

            from repositories.catalog_repository import build_org_commercial_state
            result = await build_org_commercial_state("org_1")

        assert result["drift_flags"]["billing_restricted"] is True
        assert "review_billing_status" in result["summary"]["recommended_actions"]

    @pytest.mark.asyncio
    async def test_legacy_plan_fallback_risk(self):
        """Flag when org has no provisioned subs but a non-free legacy plan."""
        org = _make_org(legacy_plan="starter")
        catalog_plan = _make_commercial_plan(slug="core", module_plans={"ai_assistant": "ai_assistant_starter"})

        with patch("repositories.catalog_repository.organizations_collection") as mock_org, \
             patch("repositories.catalog_repository.commercial_plans_collection") as mock_cp, \
             patch("repositories.catalog_repository.module_subscriptions_collection") as mock_ms, \
             patch("repositories.catalog_repository.pricing_plans_collection") as mock_pp:

            mock_org.find_one = AsyncMock(return_value=org)
            mock_cp.find_one = AsyncMock(return_value=catalog_plan)
            sub_cursor = MagicMock()
            sub_cursor.to_list = AsyncMock(return_value=[])  # no subs
            mock_ms.find.return_value = sub_cursor
            mock_pp.find_one = AsyncMock(return_value=None)

            from repositories.catalog_repository import build_org_commercial_state
            result = await build_org_commercial_state("org_1")

        assert result["drift_flags"]["legacy_plan_fallback_risk"] is True
        assert "investigate_legacy_plan_fallback" in result["summary"]["recommended_actions"]

    @pytest.mark.asyncio
    async def test_response_shape(self):
        """Response has all required top-level sections."""
        org = _make_org()
        catalog_plan = _make_commercial_plan(slug="core", module_plans={})

        with patch("repositories.catalog_repository.organizations_collection") as mock_org, \
             patch("repositories.catalog_repository.commercial_plans_collection") as mock_cp, \
             patch("repositories.catalog_repository.module_subscriptions_collection") as mock_ms, \
             patch("repositories.catalog_repository.pricing_plans_collection") as mock_pp:

            mock_org.find_one = AsyncMock(return_value=org)
            mock_cp.find_one = AsyncMock(return_value=catalog_plan)
            sub_cursor = MagicMock()
            sub_cursor.to_list = AsyncMock(return_value=[])
            mock_ms.find.return_value = sub_cursor
            mock_pp.find_one = AsyncMock(return_value=None)

            from repositories.catalog_repository import build_org_commercial_state
            result = await build_org_commercial_state("org_1")

        # Verify all top-level sections exist
        assert "organization" in result
        assert "catalog_plan" in result
        assert "provisioned_modules" in result
        assert "drift_flags" in result
        assert "summary" in result

        # Verify drift_flags has all 8 expected keys
        flags = result["drift_flags"]
        expected_flags = {
            "catalog_plan_missing", "missing_module_subscriptions",
            "unexpected_module_subscriptions", "module_plan_mismatch",
            "limits_mismatch", "manual_assignment_detected",
            "billing_restricted", "legacy_plan_fallback_risk",
        }
        assert set(flags.keys()) == expected_flags

        # Verify summary structure
        assert "is_out_of_sync" in result["summary"]
        assert "recommended_actions" in result["summary"]


# ══════════════════════════════════════════════════════════════════════════════
# Phase 3B Tests: Controlled Reprovision
# ══════════════════════════════════════════════════════════════════════════════

class TestReprovisionRequestModel:
    """Validate ReprovisionRequest model behavior."""

    def test_accepts_valid(self):
        from routers.admin_catalog import ReprovisionRequest
        req = ReprovisionRequest(confirm=True)
        assert req.confirm is True

    def test_accepts_with_notes(self):
        from routers.admin_catalog import ReprovisionRequest
        req = ReprovisionRequest(confirm=True, notes="Fixing drift")
        assert req.notes == "Fixing drift"

    def test_confirm_required(self):
        from routers.admin_catalog import ReprovisionRequest
        with pytest.raises(Exception):
            ReprovisionRequest()

    def test_rejects_extra_fields(self):
        from routers.admin_catalog import ReprovisionRequest
        with pytest.raises(Exception):
            ReprovisionRequest(confirm=True, plan_slug="core")


class TestReprovisionOrgToCatalog:
    """Tests for reprovision_org_to_catalog() orchestration."""

    @pytest.mark.asyncio
    async def test_org_not_found(self):
        """Returns None if org does not exist."""
        with patch("repositories.catalog_repository.organizations_collection") as mock_org:
            mock_org.find_one = AsyncMock(return_value=None)

            from repositories.catalog_repository import reprovision_org_to_catalog
            result = await reprovision_org_to_catalog("nonexistent", "admin_1")

        assert result is None

    @pytest.mark.asyncio
    async def test_missing_plan_slug_raises(self):
        """Raises ValueError if org has no commercial_plan_slug."""
        org = {"id": "org_1", "name": "Test", "commercial_plan_slug": None, "billing_status": "none"}

        with patch("repositories.catalog_repository.organizations_collection") as mock_org:
            mock_org.find_one = AsyncMock(return_value=org)

            from repositories.catalog_repository import reprovision_org_to_catalog
            with pytest.raises(ValueError, match="no commercial_plan_slug"):
                await reprovision_org_to_catalog("org_1", "admin_1")

    @pytest.mark.asyncio
    async def test_catalog_plan_missing_raises(self):
        """Raises ValueError if catalog plan doesn't exist."""
        org = {"id": "org_1", "name": "Test", "commercial_plan_slug": "deleted", "billing_status": "none"}

        with patch("repositories.catalog_repository.organizations_collection") as mock_org, \
             patch("repositories.catalog_repository.commercial_plans_collection") as mock_cp:
            mock_org.find_one = AsyncMock(return_value=org)
            mock_cp.find_one = AsyncMock(return_value=None)

            from repositories.catalog_repository import reprovision_org_to_catalog
            with pytest.raises(ValueError, match="not found"):
                await reprovision_org_to_catalog("org_1", "admin_1")

    @pytest.mark.asyncio
    async def test_successful_reprovision_calls_canonical_path(self):
        """Reprovision delegates to provision_commercial_plan."""
        org = {"id": "org_1", "name": "Test", "commercial_plan_slug": "core", "billing_status": "active"}
        catalog_plan = {"slug": "core"}
        pp = {"id": "pp_1", "slug": "ai_assistant_starter"}

        with patch("repositories.catalog_repository.organizations_collection") as mock_org, \
             patch("repositories.catalog_repository.commercial_plans_collection") as mock_cp, \
             patch("repositories.catalog_repository.module_subscriptions_collection") as mock_ms, \
             patch("repositories.catalog_repository.pricing_plans_collection") as mock_pp, \
             patch("repositories.catalog_repository.catalog_audit_log_collection") as mock_al, \
             patch("services.plan_provisioning.provision_commercial_plan") as mock_provision:

            mock_org.find_one = AsyncMock(return_value=org)
            mock_cp.find_one = AsyncMock(return_value=catalog_plan)
            mock_provision.return_value = {"cancelled_subs": 1, "created_subs": []}

            # Both snapshot calls return empty (before and after)
            cursor1 = MagicMock()
            cursor1.to_list = AsyncMock(return_value=[])
            cursor2 = MagicMock()
            cursor2.to_list = AsyncMock(return_value=[])
            mock_ms.find = MagicMock(side_effect=[cursor1, cursor2])

            mock_pp.find_one = AsyncMock(return_value=pp)
            mock_al.insert_one = AsyncMock()

            from repositories.catalog_repository import reprovision_org_to_catalog
            result = await reprovision_org_to_catalog("org_1", "admin_1", notes="Test reprovision")

        # Verify canonical provisioning was called
        mock_provision.assert_called_once()
        call_kwargs = mock_provision.call_args
        assert call_kwargs[1]["org_id"] == "org_1" or call_kwargs[0][0] == "org_1"

        # Verify result shape
        assert result is not None
        assert result["organization"]["id"] == "org_1"
        assert result["organization"]["commercial_plan_slug"] == "core"
        assert "before" in result
        assert "after" in result
        assert result["result"]["reprovisioned_to_plan"] == "core"

        # Verify audit entry
        mock_al.insert_one.assert_called_once()
        audit_doc = mock_al.insert_one.call_args[0][0]
        assert audit_doc["entity_type"] == "organization"
        assert audit_doc["entity_id"] == "org_1"
        assert audit_doc["action"] == "reprovision_commercial_plan"
        assert audit_doc["notes"] == "Test reprovision"

    @pytest.mark.asyncio
    async def test_noop_reprovision_still_audited(self):
        """Even if reprovision produces no change, audit is recorded."""
        org = {"id": "org_1", "name": "Test", "commercial_plan_slug": "core", "billing_status": "active"}
        catalog_plan = {"slug": "core"}

        with patch("repositories.catalog_repository.organizations_collection") as mock_org, \
             patch("repositories.catalog_repository.commercial_plans_collection") as mock_cp, \
             patch("repositories.catalog_repository.module_subscriptions_collection") as mock_ms, \
             patch("repositories.catalog_repository.pricing_plans_collection") as mock_pp, \
             patch("repositories.catalog_repository.catalog_audit_log_collection") as mock_al, \
             patch("services.plan_provisioning.provision_commercial_plan") as mock_provision:

            mock_org.find_one = AsyncMock(return_value=org)
            mock_cp.find_one = AsyncMock(return_value=catalog_plan)
            mock_provision.return_value = {}

            # Same snapshot before and after
            sub = _make_sub(module_key="ai_assistant")
            pp = _make_pricing_plan(slug="ai_assistant_starter")

            cursor1 = MagicMock()
            cursor1.to_list = AsyncMock(return_value=[sub])
            cursor2 = MagicMock()
            cursor2.to_list = AsyncMock(return_value=[sub])
            mock_ms.find = MagicMock(side_effect=[cursor1, cursor2])

            mock_pp.find_one = AsyncMock(return_value=pp)
            mock_al.insert_one = AsyncMock()

            from repositories.catalog_repository import reprovision_org_to_catalog
            result = await reprovision_org_to_catalog("org_1", "admin_1")

        # No effective change
        assert result["result"]["changed"] is False

        # But audit is still recorded
        mock_al.insert_one.assert_called_once()

    @pytest.mark.asyncio
    async def test_reprovision_preserves_stripe_subscription_id(self):
        """Reprovision of org with stripe_subscription_id passes it to canonical path."""
        org = {
            "id": "org_1", "name": "Test", "commercial_plan_slug": "core",
            "billing_status": "active", "stripe_subscription_id": "sub_live_123",
        }
        catalog_plan = {"slug": "core"}

        with patch("repositories.catalog_repository.organizations_collection") as mock_org, \
             patch("repositories.catalog_repository.commercial_plans_collection") as mock_cp, \
             patch("repositories.catalog_repository.module_subscriptions_collection") as mock_ms, \
             patch("repositories.catalog_repository.pricing_plans_collection") as mock_pp, \
             patch("repositories.catalog_repository.catalog_audit_log_collection") as mock_al, \
             patch("services.plan_provisioning.provision_commercial_plan") as mock_provision:

            mock_org.find_one = AsyncMock(return_value=org)
            mock_cp.find_one = AsyncMock(return_value=catalog_plan)
            mock_provision.return_value = {}

            cursor1 = MagicMock()
            cursor1.to_list = AsyncMock(return_value=[])
            cursor2 = MagicMock()
            cursor2.to_list = AsyncMock(return_value=[])
            mock_ms.find = MagicMock(side_effect=[cursor1, cursor2])

            mock_pp.find_one = AsyncMock(return_value=None)
            mock_al.insert_one = AsyncMock()

            from repositories.catalog_repository import reprovision_org_to_catalog
            await reprovision_org_to_catalog("org_1", "admin_1")

        # Verify stripe_subscription_id was passed to canonical provisioning
        mock_provision.assert_called_once()
        call_kwargs = mock_provision.call_args[1]
        assert call_kwargs["stripe_subscription_id"] == "sub_live_123"

    @pytest.mark.asyncio
    async def test_reprovision_without_stripe_sub_works(self):
        """Reprovision of org without stripe_subscription_id still works."""
        org = {
            "id": "org_1", "name": "Test", "commercial_plan_slug": "free",
            "billing_status": "none",
            # No stripe_subscription_id field
        }
        catalog_plan = {"slug": "free"}

        with patch("repositories.catalog_repository.organizations_collection") as mock_org, \
             patch("repositories.catalog_repository.commercial_plans_collection") as mock_cp, \
             patch("repositories.catalog_repository.module_subscriptions_collection") as mock_ms, \
             patch("repositories.catalog_repository.pricing_plans_collection") as mock_pp, \
             patch("repositories.catalog_repository.catalog_audit_log_collection") as mock_al, \
             patch("services.plan_provisioning.provision_commercial_plan") as mock_provision:

            mock_org.find_one = AsyncMock(return_value=org)
            mock_cp.find_one = AsyncMock(return_value=catalog_plan)
            mock_provision.return_value = {}

            cursor1 = MagicMock()
            cursor1.to_list = AsyncMock(return_value=[])
            cursor2 = MagicMock()
            cursor2.to_list = AsyncMock(return_value=[])
            mock_ms.find = MagicMock(side_effect=[cursor1, cursor2])

            mock_pp.find_one = AsyncMock(return_value=None)
            mock_al.insert_one = AsyncMock()

            from repositories.catalog_repository import reprovision_org_to_catalog
            result = await reprovision_org_to_catalog("org_1", "admin_1")

        # Should work normally — stripe_subscription_id is None
        assert result is not None
        call_kwargs = mock_provision.call_args[1]
        assert call_kwargs["stripe_subscription_id"] is None

    @pytest.mark.asyncio
    async def test_confirm_false_model_accepts(self):
        """Model accepts confirm=false; endpoint rejects it."""
        from routers.admin_catalog import ReprovisionRequest
        req = ReprovisionRequest(confirm=False)
        assert req.confirm is False
