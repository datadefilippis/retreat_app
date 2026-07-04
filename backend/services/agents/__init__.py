"""
AI agent platform — Wave 4 (2026-05).

Public surface:
    register_agent(agent_def: AgentDefinition) -> None
    get_agent(agent_id: str) -> AgentDefinition
    list_agents() -> list[AgentDefinition]
    list_agents_for_org(org_id: str) -> list[AgentDefinition]
        Returns agents whose module_dependencies are satisfied by the
        org's active modules. Used by the frontend agent picker.

Default agents auto-registered at import time:
    financial_analyst  (Wave 4 — mirrors today's chat behaviour)

Future agents register the same way:
    from services.agents.hr_assistant import HR_ASSISTANT
    register_agent(HR_ASSISTANT)

The registry is in-memory and populated at boot via side-effect of
importing services.agents. Adding an agent = drop a file in
services/agents/<slug>.py that calls register_agent at module load.
"""
from services.agents.registry import (
    register_agent,
    get_agent,
    list_agents,
    list_agents_for_org,
    AgentNotFoundError,
    DEFAULT_AGENT_ID,
)

# Side-effect import — registers the default financial_analyst agent
from services.agents import financial_analyst  # noqa: F401

__all__ = [
    "register_agent",
    "get_agent",
    "list_agents",
    "list_agents_for_org",
    "AgentNotFoundError",
    "DEFAULT_AGENT_ID",
]
