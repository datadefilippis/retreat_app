"""
AI Tool Registry — platform service for module-registered AI tools.

Collects provider-agnostic tool definitions from registered modules,
performs Anthropic-specific formatting, and builds a dispatch function
that routes tool calls to the correct module's executor.

Module-aware: filters tools to only include modules that are active
for the requesting organization. Returns active_modules set for
system prompt customization.

Public interface:
    get_tools_for_chat(org_id) -> (anthropic_tools, dispatch_fn, active_modules)
"""
import logging
import os
from typing import Any, Callable, Dict, List, Set, Tuple

logger = logging.getLogger(__name__)


def _to_anthropic_format(definitions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Convert tool definitions to Anthropic's tool format.

    Supports two input shapes:

    A) Flat (legacy):
        {"name", "description", "parameters": {param_name: {type, description}}, "required": [...]}

    B) JSON Schema (standard):
        {"name", "description", "parameters": {"type": "object", "properties": {...}, "required": [...]}}

    Output shape (per tool):
        {"name", "description", "input_schema": {"type": "object", "properties": {...}, "required": [...]}}
    """
    anthropic_tools = []
    for tool in definitions:
        params = tool.get("parameters", {})

        # Detect format: if params has "type"="object" and "properties", it's JSON Schema
        if params.get("type") == "object" and "properties" in params:
            # Already in JSON Schema format — use as input_schema directly
            input_schema = {
                "type": "object",
                "properties": params["properties"],
                "required": params.get("required", tool.get("required", [])),
            }
        else:
            # Flat format — convert param_name: {type, description} to properties
            properties = {}
            for param_name, param_def in params.items():
                if isinstance(param_def, dict):
                    properties[param_name] = {
                        "type": param_def.get("type", "string"),
                        "description": param_def.get("description", ""),
                    }
            input_schema = {
                "type": "object",
                "properties": properties,
                "required": tool.get("required", []),
            }

        anthropic_tools.append({
            "name": tool["name"],
            "description": tool["description"],
            "input_schema": input_schema,
        })
    return anthropic_tools


async def get_tools_for_chat(
    org_id: str,
) -> Tuple[List[Dict[str, Any]], Callable, Set[str]]:
    """Collect AI tools from active modules and return chat-ready resources.

    Module-aware: only includes tools from modules the org has access to.
    This reduces token usage (fewer tool definitions in context) and prevents
    the AI from attempting to use tools for inactive modules.

    Args:
        org_id: Organization ID used to determine active modules.

    Returns:
        (anthropic_tools, dispatch_fn, active_modules) where:
        - anthropic_tools: list of tool dicts in Anthropic format
        - dispatch_fn: async (org_id, tool_name, tool_input) -> dict
        - active_modules: set of module_key strings that are active
    """
    from core.module_registry import get_all as registry_get_all
    from services.module_access import get_module_entitlements

    # ── Determine which modules are active for this org ──────────────────
    active_modules: Set[str] = set()
    all_modules = list(registry_get_all())

    for module in all_modules:
        if module.ai_tool_definitions is None or module.ai_tool_executor is None:
            continue
        try:
            ent = await get_module_entitlements(org_id, module.module_key)
            if ent["enabled"]:
                active_modules.add(module.module_key)
        except Exception as exc:
            # On entitlement check failure, include module (fail-open for UX)
            logger.warning(
                "ai_tool_registry: entitlement check failed for %s, including tools: %s",
                module.module_key, exc,
            )
            active_modules.add(module.module_key)

    # ── Collect definitions only from active modules ─────────────────────
    all_definitions: List[Dict[str, Any]] = []
    tool_to_executor: Dict[str, Callable] = {}

    # Wave 1.6 (2026-05) — hard block on tool name collisions.
    #
    # Pre-Wave 1.6 we logged a warning and let the second registration
    # silently shadow the first. That's a latent bug: a new module
    # introducing a generic tool name (e.g. "query_summary") would
    # silently disable an existing tool with the same name. The user
    # sees the chat behave differently with no signal in the logs.
    #
    # Hard-failing at registration time (= at engine boot for the FIRST
    # chat after a deploy) is preferable: it's loud, immediate, and the
    # fix is mechanical (rename one of the colliding tools).
    #
    # We track which module originally registered each name so the
    # error message points to BOTH culprits, not just the second one.
    tool_to_module: Dict[str, str] = {}
    for module in all_modules:
        if module.ai_tool_definitions is None or module.ai_tool_executor is None:
            continue
        if module.module_key not in active_modules:
            continue

        for tool_def in module.ai_tool_definitions:
            tool_name = tool_def["name"]
            if tool_name in tool_to_executor:
                existing_module = tool_to_module.get(tool_name, "<unknown>")
                raise ValueError(
                    f"ai_tool_registry: tool name collision — '{tool_name}' is "
                    f"registered by BOTH module '{existing_module}' and module "
                    f"'{module.module_key}'. Rename one of them to disambiguate. "
                    f"This used to silently shadow (pre-Wave 1.6), causing "
                    f"unpredictable chat behaviour."
                )
            all_definitions.append(tool_def)
            tool_to_executor[tool_name] = module.ai_tool_executor
            tool_to_module[tool_name] = module.module_key

    logger.info(
        "ai_tool_registry: org=%s active_modules=%s tools=%d",
        org_id[:8], sorted(active_modules), len(all_definitions),
    )

    # Convert to Anthropic format at the platform layer
    anthropic_tools = _to_anthropic_format(all_definitions)

    # Build a dispatch function that routes by tool name.
    #
    # Wave 1.10 (2026-05) — currency enrichment.
    # Pre-Wave-1.10, 3 of 4 active modules' tools (customer_insights,
    # commerce_signals, product_catalog) never returned "currency" in
    # their response. For CHF/USD-configured orgs the AI defaulted to
    # citing EUR (the system-prompt fallback). The smoke harness
    # caught this (W1.A FAIL: CHF org → EUR in reply).
    #
    # Fixing every individual tool would require touching 20+ functions
    # and be fragile (new tools would need to remember). Instead we
    # enrich AT the dispatcher level: every tool result that is a dict
    # and doesn't already carry "currency" gets the org's currency
    # injected. This makes the property a platform contract, not a
    # per-tool concern. Existing tools that DO set currency keep
    # precedence (we never overwrite).
    #
    # Resolution is cached for the lifetime of the chat session: we
    # resolve once at registry build time and reuse for every tool
    # call in this chat. If the merchant changes currency mid-chat
    # (extremely rare), the next chat picks it up.
    from services.currency_service import get_currency_for_org
    from repositories import organization_repository
    _org_doc = await organization_repository.find_by_id(org_id)
    _org_currency = get_currency_for_org(_org_doc or {})

    # Wave 5.1 (2026-05) — PII redaction at the LLM boundary.
    # Read the env once at registry-build time so the cost is paid
    # only here (not per tool call). Default ON.
    from services.pii_redactor import redact_pii as _redact_pii
    _PII_ENABLED = os.environ.get("LLM_PII_REDACTION", "1") != "0"

    async def dispatch(call_org_id: str, tool_name: str, tool_input: dict) -> dict:
        executor = tool_to_executor.get(tool_name)
        if executor is None:
            logger.warning("ai_tool_registry: unknown tool '%s'", tool_name)
            return {"error": f"Tool sconosciuto: {tool_name}"}
        result = await executor(call_org_id, tool_name, tool_input)
        # Inject currency at the platform layer. We only set it when:
        #  - result is a dict (some tools may return lists in edge cases)
        #  - "currency" isn't already present (a tool that knows better
        #    keeps precedence — e.g. cashflow returning the period-
        #    snapshot currency vs the org current setting)
        if isinstance(result, dict) and "currency" not in result:
            result["currency"] = _org_currency
        # Wave 5.1: redact PII before the result leaves AFianco's
        # boundary. Customer emails, phones, IBANs, VAT numbers,
        # codice fiscale are masked. Business names (which the AI
        # needs for citations) are deliberately preserved — they're
        # public identifiers, not personal data.
        if _PII_ENABLED:
            result = _redact_pii(result)
        return result

    return anthropic_tools, dispatch, active_modules
