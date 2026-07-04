"""Concrete LLM provider implementations.

Each file in this directory implements LLMProvider for a specific
provider (Anthropic, OpenAI, ...). The factory in services/llm/factory.py
imports the one selected by the LLM_PROVIDER env var.

Adding a new provider:
    1. Create services/llm/providers/<name>.py with a class
       inheriting from services.llm.provider.LLMProvider
    2. Add a branch to services/llm/factory.py:get_provider()
    3. Add pricing to services/ai_cost_calculator._PRICING_TABLE
       under the new provider key
    4. Document in docs/architecture/llm-provider-adapter.md
"""
