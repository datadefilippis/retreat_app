# AFianco AI Platform — Architecture Reference

**Status:** post-Wave-5 (2026-05). Production-ready for the 150-user launch target.
**Owner:** davide
**Last update:** 2026-05-15

This is the single-page reference for the AI subsystem. If you change anything
under `backend/services/llm/`, `backend/services/agents/`, `backend/services/chat_service.py`,
or `backend/routers/chat.py`, update the relevant section here too.

---

## 1. Layered architecture (5 layers)

```
┌────────────────────────────────────────────────────────────────────────┐
│ Layer 1 — API Surface (routers/chat.py + routers/admin.py)             │
│   POST  /api/ai/chat                  default agent (financial)        │
│   POST  /api/ai/chat/stream           SSE streaming variant            │
│   POST  /api/ai/agents/{id}/chat      explicit agent routing           │
│   GET   /api/ai/agents                list available agents for org    │
│   GET   /api/ai/chat/sessions         session CRUD                     │
│   POST  /api/ai/chat/feedback         thumbs-up/down on a reply        │
│   GET   /api/health/ai                provider health + breaker state  │
│   GET   /api/admin/ai-usage/by-user   per-user cost monitoring         │
│   GET   /api/admin/ai-usage/summary   platform-wide rollup             │
└────────────────────────────────────────────────────────────────────────┘
             ↓
┌────────────────────────────────────────────────────────────────────────┐
│ Layer 2 — Chat orchestration (services/chat_service.py)                │
│   - resolves agent via services.agents.registry                        │
│   - builds module-aware system prompt                                  │
│   - injects period_context + locale + currency                         │
│   - calls get_tools_for_chat → dispatch (currency + PII enrichment)    │
│   - delegates to provider.send_messages_with_tools                     │
│   - persists session + records AIUsageEvent (cost, agent, model, user) │
└────────────────────────────────────────────────────────────────────────┘
             ↓
┌────────────────────────────────────────────────────────────────────────┐
│ Layer 3 — Module integration (services/ai_tool_registry.py + ...)      │
│   - get_tools_for_chat(org_id):                                        │
│       collects ai_tool_definitions from active modules                 │
│       HARD-FAILS on tool name collision (Wave 1.6)                     │
│       returns provider-agnostic tool list + dispatch fn                │
│   - dispatch wrapper enriches every tool result with:                  │
│       • currency (org's setting) — Wave 1.10                           │
│       • PII redaction — Wave 5.1                                       │
└────────────────────────────────────────────────────────────────────────┘
             ↓
┌────────────────────────────────────────────────────────────────────────┐
│ Layer 4 — LLM Provider abstraction (services/llm/)                     │
│   __init__.py    public surface (get_provider, LLMUnavailableError)    │
│   provider.py    abstract LLMProvider (send_message, send_messages,    │
│                   send_messages_with_tools, stream_messages,           │
│                   format_tools, calculate_cost_usd)                    │
│   factory.py     env-driven provider selection (LLM_PROVIDER)          │
│   providers/anthropic.py     concrete impl + retry + caching +        │
│                              backpressure semaphore + breaker          │
│   circuit_breaker.py         per-provider circuit breaker (3-state)    │
└────────────────────────────────────────────────────────────────────────┘
             ↓
┌────────────────────────────────────────────────────────────────────────┐
│ Layer 5 — Observability + Cost (models/ai_usage.py + admin/)           │
│   AIUsageEvent fields:                                                 │
│     organization_id, user_id, agent_id, provider, model_version        │
│     tokens_prompt, tokens_completion, cost_usd, prompt_version         │
│   services/ai_cost_calculator.py: pricing table per (provider, model)  │
│   /admin/ai-usage/* endpoints aggregate by user / org / model          │
│   Sentry tags on every LLM error: provider, model, round, error_type   │
└────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Adding a new agent (HR, Marketing, Compliance, ...)

Single file, no chat_service or router changes needed:

```python
# backend/services/agents/hr_assistant.py
from models.agent import AgentDefinition
from services.agents.registry import register_agent

register_agent(AgentDefinition(
    agent_id="hr_assistant",
    name="Assistente Risorse Umane",
    description="Risponde su dipendenti, turni, ferie, payroll",
    persona_prompt_id="hr_assistant_v1",
    tool_scopes=["hr"],              # which modules' tools the agent uses
    module_dependencies=["hr"],       # required for the agent to be available
    default_model=None,               # use provider default
    enabled_default=True,
))
```

Then add a side-effect import in `services/agents/__init__.py`:

```python
from services.agents import hr_assistant  # noqa: F401
```

Done. The new agent appears in `GET /api/ai/agents` for orgs with the `hr`
module active, and `POST /api/ai/agents/hr_assistant/chat` routes through it.

---

## 3. Adding a new LLM provider (OpenAI, xAI, Gemini, ...)

Single file in `backend/services/llm/providers/<name>.py`:

```python
from services.llm.provider import LLMProvider, LLMUnavailableError

class OpenAIProvider(LLMProvider):
    @property
    def name(self) -> str: return "openai"

    @property
    def default_model(self) -> str:
        return os.environ.get("OPENAI_MODEL", "gpt-4o-2024-08-06")

    def is_available(self) -> bool: ...
    def format_tools(self, definitions): ...  # OpenAI's functions schema
    async def send_message(...): ...
    async def send_messages(...): ...
    async def send_messages_with_tools(...): ...
    async def stream_messages(...): ...
    def calculate_cost_usd(...): ...
```

Then register in `services/llm/factory.py`:

```python
def _ensure_openai_registered():
    from services.llm.providers.openai import OpenAIProvider
    _PROVIDER_REGISTRY["openai"] = OpenAIProvider

_REGISTERS["openai"] = _ensure_openai_registered
```

And add pricing to `services/ai_cost_calculator._PRICING_TABLE`:

```python
("openai", "gpt-4o-2024-08-06"): {
    "input_usd_per_1m": 2.50,
    "output_usd_per_1m": 10.00,
    "cache_read_usd_per_1m": 1.25,
    "cache_write_usd_per_1m": 2.50,
},
```

Switch live with `LLM_PROVIDER=openai` env var. Zero changes to the 9 existing
callers (chat_service, ai_insight_service, alert_analysis, etc.).

---

## 4. Environment variables (operations reference)

| Variable | Default | Purpose |
|---|---|---|
| `ANTHROPIC_API_KEY` | (required) | Anthropic API auth |
| `LLM_PROVIDER` | `anthropic` | Which provider factory loads |
| `CLAUDE_MODEL` | `claude-sonnet-4-20250514` | Default model for Anthropic |
| `LLM_PROMPT_CACHE` | `1` | Set to `0` to disable Anthropic prompt caching (debug only) |
| `LLM_MAX_CONCURRENT` | `20` | Backpressure semaphore — in-flight calls per process |
| `LLM_CB_FAILURE_THRESHOLD` | `5` | Circuit breaker: failures to OPEN |
| `LLM_CB_FAILURE_WINDOW` | `60` | Circuit breaker: rolling window (sec) |
| `LLM_CB_OPEN_DURATION` | `30` | Circuit breaker: OPEN duration before HALF_OPEN probe |
| `LLM_PER_USER_MINUTE` | `30` | Per-(org,user) rate limit |
| `LLM_PER_USER_DAILY_TOKENS` | `200000` | Per-(org,user) token budget / day |
| `LLM_PII_REDACTION` | `1` | Set to `0` to disable PII redaction (debug only) |
| `MONGO_POOL_SIZE` | `200` | Max Mongo connections |
| `MONGO_MIN_POOL_SIZE` | `10` | Min idle Mongo connections |

---

## 5. Cost economics

Per chat session (avg 5-message conversation, with tools):

| Phase | Tokens in | Tokens out | Cost USD |
|---|---|---|---|
| Pre-Wave-3 | ~16,400 | ~600 | ~$0.052 |
| **Post-Wave-3 (caching)** | **~500** | **~200** | **~$0.0045** |

**~92% reduction verified live.** At 150 users × 20 chats/day × 30 days =
~90,000 chats/month, this is the difference between **$4,700/month** and
**$405/month**.

Anthropic tier requirements at this scale:
- **Tier 1** (50 rpm): supports ~5 concurrent active chats
- **Tier 2** (1000 rpm): supports up to ~150-200 concurrent active chats ← **required for launch**
- **Tier 3** (2000 rpm): comfortable headroom + tail latency

---

## 6. Bug baseline (Wave 0) — fully closed

All 12 bugs from `docs/operations/ai-baseline-2026-05.md` are now fixed:

| ID | Description | Closed in |
|---|---|---|
| B1-B4 | Session isolation intra-org | Wave 1.5 |
| B5 | Tool collision silent shadow | Wave 1.6 |
| B6 | Monitoring per-user impossibile | Wave 1.1+1.3+1.4 |
| B7 | No retry on 429/529 | Wave 3.1 |
| B8 | No prompt caching | Wave 3.3 |
| B9 | Locale hardcoded proactive_ctx | Wave 1.5 |
| B10 | Locale hardcoded tool dispatch | Wave 1.5 |
| B11, B12 | Currency missing in tool results | Wave 1.10 |

---

## 7. Smoke E2E (`backend/scripts/smoke_ai_e2e.py`)

Wave-by-wave acceptance scenarios. Run with:

```bash
cd backend
set -a; source .env; set +a
SMOKE_SEND=1 ./venv/bin/python -m scripts.smoke_ai_e2e
```

Current Wave-1 scenarios:
- W1.A — Currency: dispatcher returns CHF for CHF-configured org
- W1.B — Locale: English-locale user gets English reply
- W1.C — AIUsageEvent fields populated (user_id, cost_usd, agent_id, ...)
- W1.D — Session isolation: Mario can't read Anna's session

Future waves should add their own scenario blocks (Wave 4 multi-agent
golden tests, Wave 5 PII redaction, etc.).

---

## 8. Open work / future waves

**Wave 6 — Launch verification** (next):
- 30-user concurrent load test
- Final regression check on all 17 endpoints
- Anthropic Tier 2 confirmation
- Brevo IP whitelist confirmation
- Sentry alert rules

**Post-launch follow-ups:**
- Move hardcoded prompts from chat_service.py into `ai_prompts` collection
  (versioned per agent, A/B-test ready)
- Golden test suite per agent (seed from real thumbs-down feedback)
- Cache read tokens recorded explicitly in AIUsageEvent
- DPA Anthropic signed + archived in `docs/operations/`
- ToS AFianco updated with AI processing clause (legal review)
