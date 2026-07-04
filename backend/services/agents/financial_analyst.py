"""
Default agent — financial_analyst.

This is the AI persona AFianco has shipped since v1. Wave 4 wraps it
into the AgentDefinition format so future agents (HR, Marketing, etc.)
register the same way.

Behaviour is unchanged from pre-Wave-4: the chat endpoint without an
explicit agent_id resolves here, and the persona_prompt continues to
be assembled at runtime by chat_service._build_system_prompt (the
hardcoded prompt strings will move to the DB-versioned ai_prompts
collection in a future Wave 4 follow-up; for now the
persona_prompt_id "financial_analyst_v1" is a stable handle even
though the assembly logic still lives in chat_service).
"""
from models.agent import AgentDefinition
from services.agents.registry import register_agent

FINANCIAL_ANALYST = AgentDefinition(
    agent_id="financial_analyst",
    name="Analista Finanziario",
    description=(
        "Risponde a domande su fatturato, costi, margini, clienti, fornitori "
        "e operations. Cita sempre i dati e segnala quando la copertura non "
        "è sufficiente per conclusioni definitive."
    ),
    persona_prompt_id="financial_analyst_v1",
    # The agent can invoke tools from any of the 4 currently-shipped
    # AFianco modules. Tools are filtered at request time by the
    # org's active modules (the agent doesn't get tools the org
    # can't use).
    tool_scopes=[
        "cashflow_monitor",
        "customers_light",
        "product_catalog",
    ],
    # The financial_analyst needs cashflow_monitor as its minimum
    # to be useful. Other tools are optional add-ons.
    module_dependencies=["cashflow_monitor"],
    default_model=None,  # use provider default (CLAUDE_MODEL env or built-in)
    enabled_default=True,
)


# Register at import time (services/agents/__init__.py imports this module)
register_agent(FINANCIAL_ANALYST)
