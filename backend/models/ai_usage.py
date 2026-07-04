"""AI Usage Event — tracks each AI feature invocation per organization."""

from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from .common import generate_id, utc_now


class AIUsageEvent(BaseModel):
    """Tracks each feature invocation per organization per module.

    The module_key field scopes usage to a specific module, preventing
    feature_key collisions between modules (e.g. two modules both using
    "reports" as a feature_key).

    Default module_key is "ai_assistant" for backward compatibility with
    existing AI usage data.  New modules MUST pass their own module_key.

    Wave 1 additions (2026-05, AI consolidation plan)
    -------------------------------------------------
    Five new fields, ALL OPTIONAL with sensible defaults, so historic
    events (pre-Wave 1) remain readable and the database doesn't need
    a migration. New events from Wave 1 onward populate them:

      ``user_id``         which user inside the org triggered the event.
                          Unblocks per-user cost monitoring (the single
                          most-requested capability from the audit).
      ``agent_id``        which AI agent persona handled it. Default
                          "financial_analyst" to match today's only
                          agent — future agents (HR, marketing) get a
                          distinct slug in Wave 4.
      ``provider``        which LLM provider was used ("anthropic",
                          "openai", ...). Default "anthropic" since
                          that's what claude_client wraps today.
      ``model_version``   the exact model that produced the response
                          (e.g. "claude-sonnet-4-20250514"). Crucial
                          for retrospective cost auditing when models
                          get upgraded.
      ``cost_usd``        the computed USD cost of this event. We store
                          the cost in the LLM provider's billing
                          currency (Anthropic bills in USD, OpenAI in
                          USD, ...) as the universal source of truth.
                          The admin dashboard converts on the fly to
                          the org's display currency via
                          ``services.currency_service.get_currency_for_org``
                          and a current FX rate — never mix at storage
                          layer. Storing the resolved USD — not just
                          tokens — makes the admin dashboard trivial
                          and survives both future pricing changes and
                          FX-rate fluctuations.
      ``prompt_version``  the version of the system prompt used.
                          Populated by Wave 4 when prompts move from
                          hardcoded Python strings to a versioned DB
                          collection. None until then.
    """
    id: str = Field(default_factory=generate_id)
    organization_id: str
    module_key: str = "ai_assistant"   # scopes feature to a module
    feature: str                       # module-specific: "chat", "insights", etc.
    created_at: datetime = Field(default_factory=utc_now)
    quantity: int = 1                    # rows per event (>1 for bulk data_rows)
    tokens_prompt: Optional[int] = None
    tokens_completion: Optional[int] = None

    # ── Wave 1 additions ────────────────────────────────────────────
    user_id: Optional[str] = None
    agent_id: Optional[str] = "financial_analyst"
    provider: Optional[str] = "anthropic"
    model_version: Optional[str] = None
    cost_usd: Optional[float] = None
    prompt_version: Optional[str] = None

    # ── Wave 8A.1 additions (governance) ────────────────────────────
    #
    # These fields enable richer slicing in the sysadmin dashboard
    # (Wave 8C) and the multi-turn agentic-loop tracking (Wave 8A.2).
    # ALL OPTIONAL with None defaults so historic events stay readable.
    #
    # ``conversation_id``    Groups all events of the same chat turn /
    #                          agentic loop. Wave 8A.2 writes one event
    #                          per Anthropic round-trip; consumers sum
    #                          cost_usd by conversation_id to get the
    #                          total cost of a chat.
    # ``parent_event_id``    Nested calls — when feature A internally
    #                          triggers feature B, parent_event_id links
    #                          them so the dashboard can show call chains.
    # ``request_id``         Provider-issued request ID (Anthropic returns
    #                          this in response.headers["request-id"]).
    #                          Lets us correlate with Anthropic-side logs
    #                          and dedupe accidental double-writes.
    # ``cache_read_tokens``  Tokens served from the prompt cache (cheap).
    #                          Separated from tokens_prompt so the
    #                          dashboard can compute cache-hit ratio.
    # ``cache_creation_tokens`` Tokens written to the cache (1.25x cost
    #                          for Anthropic). Separated to surface the
    #                          "first-call premium" for new prompts.
    # ``latency_ms``         Wall-clock time of the API call. Useful for
    #                          spotting slow paths in the dashboard.
    # ``error_code``         When the call failed (or was throttled by
    #                          the governance layer in Wave 8B), this
    #                          carries a stable slug ("budget_exceeded",
    #                          "rate_limited", "provider_5xx", ...).
    #                          Successful calls have None.
    # ``feature_metadata``   Open dict for ad-hoc debug context (e.g.
    #                          {"prompt_length": 1234, "tool_count": 47}).
    #                          NEVER put PII here.
    conversation_id: Optional[str] = None
    parent_event_id: Optional[str] = None
    request_id: Optional[str] = None
    cache_read_tokens: Optional[int] = None
    cache_creation_tokens: Optional[int] = None
    latency_ms: Optional[int] = None
    error_code: Optional[str] = None
    feature_metadata: Optional[dict] = None

    # ── Wave 13.2 additions (Period Integrity audit) ────────────────
    #
    # ``period_audit`` captures the period context active when the
    # event was created — what the user was looking at, and what each
    # tool dispatched-to actually used. Shape (all sub-fields optional):
    #
    #     {
    #       "active": {                       # what the user was on
    #         "label": "ytd",
    #         "start": "2026-01-01",
    #         "end":   "2026-05-16",
    #         "days":  136,
    #         "resolution_source": "explicit_dates"
    #       },
    #       "tool_dispatches": [              # per tool_use in the round
    #         {
    #           "tool": "query_business_summary",
    #           "input_from_model":  {"period": "ytd"},
    #           "injection_applied": true,
    #           "resolved": {                 # ResolvedPeriod.to_audit_dict()
    #             "label":  "ytd",
    #             "start":  "2026-01-01",
    #             "end":    "2026-05-16",
    #             "days":   136,
    #             "resolution_source": "explicit_dates",
    #             "requested": {"period": "ytd", ...}
    #           }
    #         },
    #         ...
    #       ]
    #     }
    #
    # The shape is intentionally JSON-stable so dashboard queries can
    # rely on dot-notation:
    #   db.ai_usage_events.find({"period_audit.active.label": "ytd"})
    #   db.ai_usage_events.find({"period_audit.tool_dispatches.resolved.resolution_source": "fallback_unknown_token"})
    #
    # None for events that don't carry a period context (e.g. non-chat
    # features) — preserves storage for the 90 %+ of events that don't
    # need the audit. Backfilled to None on existing events; no migration.
    period_audit: Optional[dict] = None
