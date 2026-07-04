"""Unit tests for services.ai_tool_registry.

Wave 1.6 (2026-05) added a hard-fail on tool name collisions. These
tests pin the new behaviour so a future revert (or a different module
accidentally re-introducing the silent-shadow logic) gets caught at CI.
"""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


pytestmark = pytest.mark.asyncio


def _fake_module(module_key: str, tool_names: list[str]):
    """Build a minimal fake ModuleDefinition-like object."""
    m = MagicMock()
    m.module_key = module_key
    m.ai_tool_definitions = [
        {"name": name, "description": f"desc {name}", "parameters": {}}
        for name in tool_names
    ]
    m.ai_tool_executor = AsyncMock(return_value={"ok": True})
    return m


# Wave 1.10 added a Mongo call to organization_repository.find_by_id
# inside get_tools_for_chat to resolve the org currency for the
# dispatcher's enrichment wrapper. Tests must mock that — otherwise a
# real Mongo connection is attempted, which fails when run in random
# order with other tests that prep the DB connection differently.
_FAKE_ORG_DOC = {"id": "org_test", "currency": "EUR"}


async def test_collision_between_modules_raises():
    """Wave 1.6: two modules registering the same tool_name MUST raise.

    This is the explicit acceptance test for B5 in the AI baseline.
    Pre-Wave 1.6 the second registration silently shadowed the first.
    """
    from services import ai_tool_registry

    mod_a = _fake_module("module_a", ["query_summary"])
    mod_b = _fake_module("module_b", ["query_summary"])  # collision

    with patch(
        "core.module_registry.get_all",
        return_value=[mod_a, mod_b],
    ), patch(
        "services.module_access.get_module_entitlements",
        new=AsyncMock(return_value={"enabled": True}),
    ), patch(
        "repositories.organization_repository.find_by_id",
        new=AsyncMock(return_value=_FAKE_ORG_DOC),
    ):
        with pytest.raises(ValueError) as exc_info:
            await ai_tool_registry.get_tools_for_chat("org_test")

        msg = str(exc_info.value)
        assert "query_summary" in msg
        assert "module_a" in msg
        assert "module_b" in msg


async def test_no_collision_when_unique_names():
    """Two modules with disjoint tool names: registration succeeds."""
    from services import ai_tool_registry

    mod_a = _fake_module("module_a", ["query_alpha"])
    mod_b = _fake_module("module_b", ["query_beta"])

    with patch(
        "core.module_registry.get_all",
        return_value=[mod_a, mod_b],
    ), patch(
        "services.module_access.get_module_entitlements",
        new=AsyncMock(return_value={"enabled": True}),
    ), patch(
        "repositories.organization_repository.find_by_id",
        new=AsyncMock(return_value=_FAKE_ORG_DOC),
    ):
        tools, dispatch, active = await ai_tool_registry.get_tools_for_chat("org_test")

    tool_names = {t["name"] for t in tools}
    assert tool_names == {"query_alpha", "query_beta"}
    assert active == {"module_a", "module_b"}


async def test_inactive_module_tool_not_a_collision():
    """When module_b is INACTIVE for the org, its tools are not loaded.

    If a tool name exists in both an active and an inactive module, only
    the active one wins — no collision because the inactive registration
    is filtered out earlier.
    """
    from services import ai_tool_registry

    mod_a = _fake_module("module_a", ["query_summary"])
    mod_b = _fake_module("module_b", ["query_summary"])

    async def fake_entitlements(org_id, module_key, org_doc=None):
        return {"enabled": module_key == "module_a"}

    with patch(
        "core.module_registry.get_all",
        return_value=[mod_a, mod_b],
    ), patch(
        "services.module_access.get_module_entitlements",
        new=AsyncMock(side_effect=fake_entitlements),
    ), patch(
        "repositories.organization_repository.find_by_id",
        new=AsyncMock(return_value=_FAKE_ORG_DOC),
    ):
        tools, _, active = await ai_tool_registry.get_tools_for_chat("org_test")

    assert {t["name"] for t in tools} == {"query_summary"}
    assert active == {"module_a"}


async def test_dispatcher_injects_currency_into_tool_result():
    """Wave 1.10 (B11, B12): dispatcher enriches tool results with currency.

    Most module ai_tools didn't include "currency" in their response.
    The dispatcher now resolves the org currency once and injects it
    into every dict-shaped tool result that doesn't already carry one.
    """
    from services import ai_tool_registry

    mod = _fake_module("module_x", ["query_anything"])
    # The executor returns a dict WITHOUT currency — the dispatcher
    # must inject it.
    mod.ai_tool_executor = AsyncMock(return_value={"total": 5000})

    chf_org = {"id": "org_test", "currency": "CHF"}

    with patch(
        "core.module_registry.get_all",
        return_value=[mod],
    ), patch(
        "services.module_access.get_module_entitlements",
        new=AsyncMock(return_value={"enabled": True}),
    ), patch(
        "repositories.organization_repository.find_by_id",
        new=AsyncMock(return_value=chf_org),
    ):
        tools, dispatch, active = await ai_tool_registry.get_tools_for_chat("org_test")
        result = await dispatch("org_test", "query_anything", {})

    assert result["currency"] == "CHF", (
        f"Wave 1.10 currency injection failed: got {result.get('currency')!r}"
    )
    assert result["total"] == 5000, "tool's own data was clobbered"


async def test_dispatcher_does_not_overwrite_existing_currency():
    """If the tool already returned currency, the dispatcher leaves it alone.

    Some tools (e.g. cashflow's build_unified_summary) explicitly set
    currency themselves. The wrapper should not overwrite.
    """
    from services import ai_tool_registry

    mod = _fake_module("module_x", ["query_anything"])
    mod.ai_tool_executor = AsyncMock(return_value={
        "total": 5000, "currency": "USD",  # tool knows
    })

    chf_org = {"id": "org_test", "currency": "CHF"}  # different

    with patch(
        "core.module_registry.get_all",
        return_value=[mod],
    ), patch(
        "services.module_access.get_module_entitlements",
        new=AsyncMock(return_value={"enabled": True}),
    ), patch(
        "repositories.organization_repository.find_by_id",
        new=AsyncMock(return_value=chf_org),
    ):
        tools, dispatch, active = await ai_tool_registry.get_tools_for_chat("org_test")
        result = await dispatch("org_test", "query_anything", {})

    # Tool's currency wins
    assert result["currency"] == "USD"
