"""
AgentDefinition — Wave 4 (2026-05) primitive for the multi-agent framework.

Today's only agent is "financial_analyst" (the chat AI we shipped from
day 1). Wave 4 makes it possible to add HR, Marketing, Compliance,
etc. agents without touching the chat_service code path. Each agent
has:

  - a stable `agent_id` slug (URL-safe, human-readable)
  - a `name` shown to users
  - a `persona_prompt_id` pointing into the ai_prompts collection
    (Wave 4.3 — versioned prompts in DB instead of hardcoded strings)
  - `tool_scopes` — which modules' AI tools the agent may invoke
  - `default_model` — provider+model the agent prefers
  - `module_dependencies` — modules that MUST be active for the agent
    to function (e.g. the financial_analyst depends on
    cashflow_monitor)
  - `description` — system_admin-facing text for the agent catalogue
  - `enabled_default` — whether the agent is on by default for new orgs

Design choices
--------------
- AgentDefinition is a CONFIG, not state. There's one definition per
  agent_id in the registry (services/agents/registry.py), populated
  at import time. Activating/deactivating an agent for a specific
  org is a separate concern (organization_modules_collection).

- We keep prompt content OUT of this struct — prompts live in the
  ai_prompts collection (DB, versioned). The struct holds just the
  `persona_prompt_id` reference so prompt updates don't require a
  redeploy.

- Backwards compat: until Wave 4 fully lands, the default agent
  ("financial_analyst") is auto-registered with the current hardcoded
  prompts wrapped as a prompt v1 in the DB. Chat endpoints without
  an explicit agent_id resolve to financial_analyst.
"""
from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field


class AgentDefinition(BaseModel):
    """Static configuration for one AI agent persona.

    Registered at platform boot via services.agents.registry.register_agent.
    Immutable once registered — changing an agent's behaviour means
    publishing a new prompt version in the ai_prompts collection (Wave 4.3).
    """
    model_config = ConfigDict(extra="ignore")

    agent_id: str = Field(
        ...,
        pattern=r"^[a-z][a-z0-9_]{2,30}$",
        description="URL-safe slug. Used in endpoints and AIUsageEvent.agent_id.",
    )
    name: str = Field(..., min_length=1, max_length=80)
    description: str = Field(default="", max_length=500)

    # Prompt reference (Wave 4.3 stores the content in ai_prompts collection)
    persona_prompt_id: str = Field(
        ...,
        description=(
            "ID of the prompt record in ai_prompts collection. The "
            "registry resolves this to the active version at request time."
        ),
    )

    # Which AFianco modules this agent's tools belong to.
    # The tool registry filters tools to this list when the agent is
    # asked for its tools (Wave 4.8).
    tool_scopes: List[str] = Field(
        default_factory=list,
        description="module_key strings (cashflow_monitor, customers_light, ...)",
    )

    # Modules that MUST be active for the agent to be usable.
    # If an org doesn't have these, the agent endpoint returns 403.
    module_dependencies: List[str] = Field(
        default_factory=list,
        description="module_key strings that must be enabled for the org.",
    )

    # Default model — overridable per request later if needed.
    default_model: Optional[str] = Field(
        default=None,
        description=(
            "model_version slug (e.g. claude-sonnet-4-20250514). None means "
            "use the provider's default."
        ),
    )

    # Whether the agent appears in the standard agent list for an org
    # without explicit opt-in. Today financial_analyst is enabled_default
    # = True; future internal agents may start hidden.
    enabled_default: bool = True
