"""Wave 5.6 (2026-05) — golden tests for the agent platform.

These pin agent registry behaviour so regressions get caught at CI.

The full golden test suite per agent (chatbot-style "if asked X
must respond with Y including caveat Z") is a post-launch follow-up
once we have real thumbs-down feedback to seed scenarios. For now
this file covers the structural contract: agent registration, lookup,
and the default-agent fallback behaviour.
"""
import pytest


def test_default_agent_id_is_financial_analyst():
    """The platform default must always resolve to financial_analyst.

    If we ever change this slug, both the chat router fallback and the
    frontend agent picker need to update. This test makes that
    coordination explicit.
    """
    from services.agents.registry import DEFAULT_AGENT_ID
    assert DEFAULT_AGENT_ID == "financial_analyst"


def test_financial_analyst_is_registered():
    """The financial_analyst agent must register itself via side-effect
    import at module load. If this test fails, services/agents/__init__.py
    has lost its side-effect import.
    """
    from services.agents import get_agent
    agent = get_agent("financial_analyst")
    assert agent.agent_id == "financial_analyst"
    assert agent.name  # non-empty name
    assert "cashflow_monitor" in agent.module_dependencies


def test_unknown_agent_raises_agent_not_found():
    """get_agent raises AgentNotFoundError, not KeyError, on unknown id.

    The chat router catches AgentNotFoundError specifically to return
    a clean 404; if we raise KeyError instead, the router converts to
    500 and the frontend can't differentiate "user typo" from "server bug".
    """
    from services.agents import get_agent, AgentNotFoundError
    with pytest.raises(AgentNotFoundError):
        get_agent("nonexistent_agent_xyz")


def test_list_agents_returns_at_least_financial_analyst():
    """At least one agent must be registered at any given time."""
    from services.agents import list_agents
    agents = list_agents()
    assert len(agents) >= 1
    slugs = {a.agent_id for a in agents}
    assert "financial_analyst" in slugs


def test_register_agent_idempotent():
    """Registering the same AgentDefinition twice is a no-op.

    The financial_analyst module is imported with a side-effect that
    calls register_agent. If we ever re-import the module (e.g. in a
    hot-reload dev scenario), we should not raise.
    """
    from models.agent import AgentDefinition
    from services.agents.registry import register_agent, get_agent

    existing = get_agent("financial_analyst")
    # Build an identical definition (Pydantic equality)
    same = AgentDefinition(**existing.model_dump())
    # No exception
    register_agent(same)


def test_register_agent_conflict_raises():
    """Registering a DIFFERENT definition under the same agent_id
    is a config bug — must raise ValueError loudly so the deploy fails."""
    from models.agent import AgentDefinition
    from services.agents.registry import register_agent

    different = AgentDefinition(
        agent_id="financial_analyst",
        name="WRONG NAME",  # conflict
        persona_prompt_id="other_prompt",
        tool_scopes=[],
        module_dependencies=[],
    )
    with pytest.raises(ValueError):
        register_agent(different)


def test_agent_definition_validates_agent_id_slug():
    """agent_id must be URL-safe slug (lowercase, snake_case, 3-31 chars)."""
    from models.agent import AgentDefinition
    from pydantic import ValidationError

    # Valid
    AgentDefinition(
        agent_id="hr_assistant_v2",
        name="HR",
        persona_prompt_id="hr_v2",
    )

    # Invalid: starts with digit
    with pytest.raises(ValidationError):
        AgentDefinition(agent_id="2hr_assistant", name="X", persona_prompt_id="x")

    # Invalid: contains uppercase
    with pytest.raises(ValidationError):
        AgentDefinition(agent_id="HR_Assistant", name="X", persona_prompt_id="x")

    # Invalid: contains hyphen
    with pytest.raises(ValidationError):
        AgentDefinition(agent_id="hr-assistant", name="X", persona_prompt_id="x")
