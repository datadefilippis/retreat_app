"""
Agent registry — in-memory registry of AgentDefinition instances.

Wave 4 (2026-05). Pattern mirrors core.module_registry.

Concurrency: the registry is intentionally simple (a dict) and only
mutated at import time (when modules register their agents). Read
operations are concurrent-safe.

Adding a new agent:
    services/agents/<slug>.py:
        from models.agent import AgentDefinition
        from services.agents.registry import register_agent

        HR_ASSISTANT = AgentDefinition(
            agent_id="hr_assistant",
            name="HR Assistant",
            persona_prompt_id="hr_assistant_v1",
            tool_scopes=["hr"],
            module_dependencies=["hr"],
            description="Helps with employee questions, shift planning, ...",
        )
        register_agent(HR_ASSISTANT)

    services/agents/__init__.py adds the side-effect import to wire it up.
"""
from __future__ import annotations

import logging
from typing import Dict, List

from models.agent import AgentDefinition

logger = logging.getLogger(__name__)


# The default agent — what /api/ai/chat routes to when no agent_id is
# specified. Matches today's behaviour 1:1.
DEFAULT_AGENT_ID = "financial_analyst"


class AgentNotFoundError(Exception):
    """Raised by get_agent when the requested agent_id isn't registered."""
    pass


# ── Internal registry ──────────────────────────────────────────────────────

_REGISTRY: Dict[str, AgentDefinition] = {}


def register_agent(agent_def: AgentDefinition) -> None:
    """Add an agent definition to the registry. Idempotent.

    Called at module-import time from services/agents/<slug>.py files.
    Raises ValueError if a different definition is already registered
    under the same agent_id (config drift — fix the caller).
    """
    existing = _REGISTRY.get(agent_def.agent_id)
    if existing is not None and existing != agent_def:
        raise ValueError(
            f"agent_registry: conflicting registration for '{agent_def.agent_id}'. "
            f"Existing: {existing!r} vs new: {agent_def!r}"
        )
    _REGISTRY[agent_def.agent_id] = agent_def
    logger.info("agent_registry: registered agent_id=%s name=%r",
                agent_def.agent_id, agent_def.name)


def get_agent(agent_id: str) -> AgentDefinition:
    """Return the AgentDefinition for the given agent_id.

    Raises AgentNotFoundError if the agent isn't registered.
    """
    if agent_id not in _REGISTRY:
        raise AgentNotFoundError(
            f"Unknown agent_id '{agent_id}'. "
            f"Registered: {sorted(_REGISTRY.keys())}"
        )
    return _REGISTRY[agent_id]


def list_agents() -> List[AgentDefinition]:
    """All registered agents, regardless of org context."""
    return list(_REGISTRY.values())


async def list_agents_for_org(org_id: str) -> List[AgentDefinition]:
    """Agents whose module_dependencies are satisfied for the given org.

    Used by the frontend agent picker so users only see agents they
    can actually invoke (no point showing "HR Assistant" to an org
    without the HR module).

    Falls back to "all enabled_default agents" when entitlement
    resolution fails — fail-open so a misconfigured environment
    doesn't hide the chat entirely.
    """
    try:
        from services.module_access import get_module_entitlements
        # Resolve once per module needed — cache across the call
        cache: Dict[str, bool] = {}

        async def _module_enabled(module_key: str) -> bool:
            if module_key in cache:
                return cache[module_key]
            ent = await get_module_entitlements(org_id, module_key)
            ok = bool(ent.get("enabled"))
            cache[module_key] = ok
            return ok

        result: List[AgentDefinition] = []
        for agent in _REGISTRY.values():
            if not agent.enabled_default:
                continue
            if all([await _module_enabled(m) for m in agent.module_dependencies]):
                result.append(agent)
        return result
    except Exception as exc:
        logger.warning(
            "agent_registry: list_agents_for_org failed (%s) — falling back to all defaults",
            exc,
        )
        return [a for a in _REGISTRY.values() if a.enabled_default]


def reset_for_tests() -> None:
    """Clear the registry. ONLY for tests."""
    _REGISTRY.clear()
