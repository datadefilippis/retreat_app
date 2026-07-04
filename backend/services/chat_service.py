"""
AI Chat Service — conversational financial advisor with tool use.

The AI dynamically queries the database via function calling (tool use)
instead of receiving pre-computed KPIs.  This allows it to answer
specific questions about any period, category, or supplier.

Module-aware: the system prompt adapts to the org's active modules,
and only tools from active modules are exposed. This reduces token
usage and keeps the AI focused on available data.

Sessions are persisted to MongoDB (chat_sessions collection) so they
survive server restarts.  Per-document TTL based on commercial plan.

Public interface:
    chat(org_id, session_id, user_message, locale, user_id) -> str
"""
import logging
from datetime import datetime, timedelta, timezone
from typing import List, Optional, Set

logger = logging.getLogger(__name__)

_MAX_HISTORY = 30  # increased to accommodate tool_use/tool_result exchanges

# Wave 9.A.3 — cost-explosion guards
# ------------------------------------------------------------------
# Two complementary caps prevent a single chat from costing more than
# a few cents:
#
# _MAX_TOOL_RESULT_CHARS
#   Truncate any tool_dispatch return that serializes to more than N
#   chars. The truncated payload still carries the *shape* of the
#   result (first 2K + a clear "truncated" marker), so the model knows
#   to refine the query rather than re-issue the same tool. Forensic
#   evidence: a chat in April 2026 hit 33,531 input tokens because a
#   tool returned ~30KB of data and the loop re-fed it to Anthropic.
#
# _MAX_HISTORY_CHARS
#   Pre-flight guard before each agentic loop. If the serialized
#   history exceeds this, refuse early with a clear error. Acts as a
#   safety net under pathological conditions (multiple tool calls
#   each near the truncation limit). Roughly 25K tokens at the 4-char
#   heuristic, well under Sonnet's 200K context but well above the
#   $0.10 chat that triggered this guard.
import os as _os9a
# Wave 14.HOTFIX (2026-05-16) — raised default from 10000 to 30000.
# Pre-fix evidence: `query_business_summary` for a YTD window (4.5 months
# of data) serialised to 13_391 chars and was cut mid-JSON (literally
# inside a key name "fixed_co...") by the head-only truncation strategy.
# The chat model saw a corrupted, invalid JSON, declared "data truncated"
# and started fabricating numbers — observed in prod on the same date,
# Wave 13 audit BUG #A. Anthropic Sonnet can consume ~150K input tokens
# per round, so 30K chars of one tool result (~7.5K tokens) is well
# within budget. The env knob still lets ops tighten it under pressure.
_MAX_TOOL_RESULT_CHARS = int(_os9a.environ.get("CHAT_MAX_TOOL_RESULT_CHARS", "30000"))
_MAX_HISTORY_CHARS = int(_os9a.environ.get("CHAT_MAX_HISTORY_CHARS", "100000"))


def _truncate_tool_result(result: dict, tool_name: str) -> dict:
    """Cap tool_dispatch output size — Wave 9.A.3 + Wave 14.2 overhaul.

    If the JSON-serialised result exceeds ``_MAX_TOOL_RESULT_CHARS`` we
    progressively shrink it via STRUCTURED truncation, instead of the
    pre-Wave-14.2 head-only character cut that left the JSON sliced in
    the middle of a key (the exact root cause of the chat AI
    hallucination observed on 2026-05-16 in prod). The strategy is:

      Pass 1 — drop high-volume time-series arrays
               (``by_date``, ``daily_series``, ``daily_breakdown``).
               These are the heaviest payload by far on rich-data
               organisations; the AI usually has the aggregate via
               ``total`` / ``net_result`` / ``pnl`` and doesn't
               actually need the per-day breakdown.

      Pass 2 — cap any top-N list at 5 items
               (top_customers, top_suppliers, top_expense_categories,
               recent alerts, …). The model sees the top entries plus
               a count note saying how many were truncated.

      Pass 3 — drop nested ``epistemic`` and ``block_scopes`` blocks.
               These are advisory metadata the model has been trained
               on via the system prompt; under truncation pressure we
               recover their bytes.

      Pass 4 — drop ``diagnostics`` and ``breakdown`` sub-blocks
               (health-score internals; the score+label+top issues
               are enough for the model to reason about health).

      Pass 5 (last resort) — head-only character cut on the already-
               compacted result. This still produces a marker dict so
               the model is INSTRUCTED to retry with a narrower scope.

    Each pass records the fields it dropped in
    ``_truncated_fields`` so the model knows which sections of the
    response are no longer complete and can decide to call a more
    focused tool. This matches Wave 14.HOTFIX Rule 23 (TRUNCATION
    HANDLING) which tells the AI to NEVER read partial JSON and
    instead re-call with a tighter window.

    Backward compatibility:
      - Small results (<= cap) pass through unchanged.
      - Tools that already produce envelope-compliant results
        (Wave 14.1) keep their envelope metadata throughout.
      - The original ``_truncated`` / ``_original_size_chars`` /
        ``_cap_chars`` / ``_hint`` / ``head`` fields are still emitted
        in the last-resort branch, so existing consumers and tests
        that grep for them continue to work.
    """
    import json as _json9a
    try:
        serialized = _json9a.dumps(result, ensure_ascii=False, default=str)
    except (TypeError, ValueError):
        return result  # un-serializable input → let the agentic loop handle
    if len(serialized) <= _MAX_TOOL_RESULT_CHARS:
        return result

    original_size = len(serialized)
    logger.warning(
        "chat_service: tool result oversize (tool=%s size=%d > cap=%d) "
        "— running progressive structured truncation",
        tool_name, original_size, _MAX_TOOL_RESULT_CHARS,
    )

    # Non-dict results can't be structurally truncated. Fall straight
    # to the head-only path so we still produce a valid marker.
    if not isinstance(result, dict):
        return _head_only_truncate(result, serialized, tool_name, original_size, [])

    current = dict(result)  # copy — never mutate the caller's dict
    truncated_fields: List[str] = []

    # ── Pass 1: drop verbose time-series arrays ─────────────────────────
    current, dropped = _strip_verbose_time_series(current)
    truncated_fields.extend(dropped)
    serialized = _json9a.dumps(current, ensure_ascii=False, default=str)
    if len(serialized) <= _MAX_TOOL_RESULT_CHARS:
        return _mark_structurally_truncated(
            current, truncated_fields, tool_name, original_size,
        )

    # ── Pass 2: cap top-N lists ─────────────────────────────────────────
    current, dropped = _cap_top_lists(current, max_items=5)
    truncated_fields.extend(dropped)
    serialized = _json9a.dumps(current, ensure_ascii=False, default=str)
    if len(serialized) <= _MAX_TOOL_RESULT_CHARS:
        return _mark_structurally_truncated(
            current, truncated_fields, tool_name, original_size,
        )

    # ── Pass 3: drop epistemic / block_scopes metadata ──────────────────
    current, dropped = _drop_advisory_blocks(current)
    truncated_fields.extend(dropped)
    serialized = _json9a.dumps(current, ensure_ascii=False, default=str)
    if len(serialized) <= _MAX_TOOL_RESULT_CHARS:
        return _mark_structurally_truncated(
            current, truncated_fields, tool_name, original_size,
        )

    # ── Pass 4: drop diagnostics / breakdown ────────────────────────────
    current, dropped = _drop_deep_metadata(current)
    truncated_fields.extend(dropped)
    serialized = _json9a.dumps(current, ensure_ascii=False, default=str)
    if len(serialized) <= _MAX_TOOL_RESULT_CHARS:
        return _mark_structurally_truncated(
            current, truncated_fields, tool_name, original_size,
        )

    # ── Pass 5 (last resort): head-only on the compacted result ────────
    return _head_only_truncate(
        current, serialized, tool_name, original_size, truncated_fields,
    )


# ── Wave 14.2 — structured truncation helpers ─────────────────────────────


# Field names that hold verbose per-day arrays. When the model has
# the aggregate (total / pnl / summary), these can be dropped.
_VERBOSE_TIME_SERIES_KEYS = frozenset({
    "by_date", "daily_series", "by_day", "daily_breakdown",
    "monthly_series", "weekly_series", "hourly_series",
})

# Top-N list field name PATTERNS — we cap any list whose key starts
# with one of these prefixes. Conservative: only PUREly verbose lists.
_TOP_N_LIST_PREFIXES = (
    "top_", "recent_",
)

# Field names that carry advisory metadata the model doesn't need
# under truncation pressure.
_ADVISORY_BLOCK_KEYS = frozenset({
    "epistemic", "block_scopes", "data_caveats",
    "reasoning_contract",
})

# Deeper-priority metadata — only dropped at pass 4.
_DEEP_METADATA_KEYS = frozenset({
    "diagnostics", "breakdown", "data_warnings",
})


def _strip_verbose_time_series(payload: dict) -> tuple:
    """Pass 1: drop time-series arrays everywhere in the dict tree."""
    dropped: List[str] = []
    stripped = _walk_drop_keys(
        payload, _VERBOSE_TIME_SERIES_KEYS, dropped, max_depth=4,
    )
    return stripped, dropped


def _cap_top_lists(payload: dict, *, max_items: int) -> tuple:
    """Pass 2: cap list-valued fields whose key matches a top-N
    prefix. Lists are truncated to ``max_items`` and a sibling
    ``_<key>_truncated_from`` field is added to record the original
    length."""
    dropped: List[str] = []
    capped = _walk_cap_lists(payload, max_items, dropped, max_depth=4)
    return capped, dropped


def _drop_advisory_blocks(payload: dict) -> tuple:
    """Pass 3: drop nested epistemic / block_scopes / data_caveats."""
    dropped: List[str] = []
    stripped = _walk_drop_keys(
        payload, _ADVISORY_BLOCK_KEYS, dropped, max_depth=4,
    )
    return stripped, dropped


def _drop_deep_metadata(payload: dict) -> tuple:
    """Pass 4: drop diagnostics / breakdown / data_warnings."""
    dropped: List[str] = []
    stripped = _walk_drop_keys(
        payload, _DEEP_METADATA_KEYS, dropped, max_depth=4,
    )
    return stripped, dropped


def _walk_drop_keys(
    payload, drop_keys: frozenset, dropped: List[str],
    *, max_depth: int, path: str = "",
) -> dict:
    """Recursively rebuild ``payload`` dropping every entry whose key
    is in ``drop_keys``. Tracks the dotted paths of dropped fields in
    the ``dropped`` accumulator so we can report them to the model."""
    if max_depth <= 0 or not isinstance(payload, dict):
        return payload
    out = {}
    for key, value in payload.items():
        sub_path = f"{path}.{key}" if path else key
        if key in drop_keys:
            dropped.append(sub_path)
            continue
        if isinstance(value, dict):
            out[key] = _walk_drop_keys(
                value, drop_keys, dropped,
                max_depth=max_depth - 1, path=sub_path,
            )
        elif isinstance(value, list):
            out[key] = [
                _walk_drop_keys(
                    item, drop_keys, dropped,
                    max_depth=max_depth - 1, path=f"{sub_path}[*]",
                ) if isinstance(item, dict) else item
                for item in value
            ]
        else:
            out[key] = value
    return out


def _walk_cap_lists(
    payload, max_items: int, dropped: List[str],
    *, max_depth: int, path: str = "",
) -> dict:
    """Recursively cap lists whose key starts with a top-N prefix."""
    if max_depth <= 0 or not isinstance(payload, dict):
        return payload
    out = {}
    for key, value in payload.items():
        sub_path = f"{path}.{key}" if path else key
        if (
            isinstance(value, list)
            and len(value) > max_items
            and any(key.startswith(pfx) for pfx in _TOP_N_LIST_PREFIXES)
        ):
            out[key] = value[:max_items]
            out[f"_{key}_truncated_from"] = len(value)
            dropped.append(
                f"{sub_path}[{max_items}:{len(value)}]"
            )
        elif isinstance(value, dict):
            out[key] = _walk_cap_lists(
                value, max_items, dropped,
                max_depth=max_depth - 1, path=sub_path,
            )
        elif isinstance(value, list):
            out[key] = [
                _walk_cap_lists(
                    item, max_items, dropped,
                    max_depth=max_depth - 1, path=f"{sub_path}[*]",
                ) if isinstance(item, dict) else item
                for item in value
            ]
        else:
            out[key] = value
    return out


def _mark_structurally_truncated(
    result: dict,
    truncated_fields: List[str],
    tool_name: str,
    original_size: int,
) -> dict:
    """Tag a structurally-truncated result with the metadata the
    chat AI needs to apply Rule 23 (TRUNCATION HANDLING).

    Unlike the pre-Wave-14.2 head-only path, the result here is STILL
    a valid envelope: all envelope metadata stays intact, only deeply-
    nested verbose sections were dropped. The model can therefore
    reason about the response normally — but the explicit
    ``_truncated_fields`` list tells it which sections are partial,
    which is the signal to re-call with a narrower window IF the
    user's question depends on those sections.
    """
    out = dict(result)
    out["_truncated"] = True
    out["_truncated_by"] = "wave14_structured"
    out["_truncated_fields"] = list(truncated_fields)
    out["_original_size_chars"] = original_size
    out["_cap_chars"] = _MAX_TOOL_RESULT_CHARS
    out["_hint"] = (
        f"The {tool_name} result was {original_size:,} chars and exceeded "
        f"the {_MAX_TOOL_RESULT_CHARS:,} cap. We applied structured "
        f"truncation that preserved the aggregate KPIs but dropped the "
        f"following verbose / advisory sections: {sorted(set(truncated_fields))[:8]}"
        + ("..." if len(set(truncated_fields)) > 8 else "")
        + ". If the user's question depends on any of those sections, "
        "call a more focused tool with a narrower period; otherwise "
        "you can answer normally from the aggregates that remain."
    )
    return out


def _head_only_truncate(
    result,
    serialized: str,
    tool_name: str,
    original_size: int,
    structurally_dropped: List[str],
) -> dict:
    """Last-resort head-only truncation. Pre-Wave-14.2 this was the
    ONLY strategy; Wave 14.2 reaches it only after all four structured
    passes have failed to shrink the result below the cap.

    Returns the legacy marker shape (``_truncated`` / ``head`` / etc.)
    so existing consumers + tests keep working.
    """
    head_chars = max(2000, _MAX_TOOL_RESULT_CHARS // 4)
    return {
        "_truncated": True,
        "_truncated_by": "wave14_head_only_fallback",
        "_original_size_chars": original_size,
        "_cap_chars": _MAX_TOOL_RESULT_CHARS,
        "_structurally_dropped": list(structurally_dropped),
        "_hint": (
            f"The {tool_name} result was {original_size:,} chars (cap "
            f"{_MAX_TOOL_RESULT_CHARS:,}). Even after structured "
            f"truncation (dropped {len(structurally_dropped)} verbose / "
            f"advisory sections) the result was still oversize, so we "
            f"fell back to a head-only cut. Re-call with a narrower "
            f"period or a more focused tool — DO NOT attempt to parse "
            f"the partial JSON below."
        ),
        "head": serialized[:head_chars],
    }


def _estimate_history_chars(messages: list) -> int:
    """Sum the serialized length of every message (incl. tool_use blocks).

    Cheap approximation — does not need a tokenizer. ~4 chars per token
    is a conservative heuristic for the Latin alphabet.
    """
    import json as _json9a
    total = 0
    for msg in messages:
        content = msg.get("content")
        if isinstance(content, str):
            total += len(content)
        elif isinstance(content, list):
            try:
                total += len(_json9a.dumps(content, ensure_ascii=False, default=str))
            except (TypeError, ValueError):
                total += 1000  # opaque block → reasonable guess
    return total

# v5.8 / Onda 10 Step B.2 — Session retention (days) is now read from
# `commercial_plans.platform_limits.chat_session_ttl_days` so the
# system_admin can edit it via catalog UI without redeploy. The dict
# below remains as a defence-in-depth fallback for plans not yet
# migrated (also returned for unknown slugs to avoid silent default-7
# behaviour on a future plan slug not anyone remembered to seed).
_PLAN_TTL_DAYS_FALLBACK = {
    "free": 7,
    "starter": 30,
    "core": 90,
    "pro": 180,
    "enterprise": 365,
}

# Keywords that trigger extended max_tokens
_COMPLEX_KEYWORDS = {"analisi", "confronto", "report", "confronta", "analizza", "dettaglio", "approfond"}


async def _compute_expires_at(org_id: str) -> datetime:
    """Compute per-document expires_at based on the org's commercial plan.

    Order of resolution:
      1. `commercial_plans.{slug}.platform_limits.chat_session_ttl_days`
         (admin-editable via catalog — Onda 10 Step B.2)
      2. `_PLAN_TTL_DAYS_FALLBACK[slug]` (legacy hardcoded, for unmigrated)
      3. 7 days (most conservative default for unknown slugs)
    """
    from repositories import organization_repository, billing_repository
    ttl_days = 7  # default (free)
    try:
        org = await organization_repository.find_by_id(org_id)
        if org:
            slug = org.get("commercial_plan_slug", "free")
            # 1) Try catalog field
            try:
                plan = await billing_repository.get_commercial_plan(slug) or {}
                pl = plan.get("platform_limits") or {}
                catalog_ttl = pl.get("chat_session_ttl_days")
                if isinstance(catalog_ttl, int) and catalog_ttl > 0:
                    ttl_days = catalog_ttl
                else:
                    raise KeyError("not in catalog")
            except Exception:
                # 2) Fallback to legacy dict
                ttl_days = _PLAN_TTL_DAYS_FALLBACK.get(slug, 7)
    except Exception:
        pass
    return datetime.now(timezone.utc) + timedelta(days=ttl_days)


# ── Module-aware system prompt builder ──────────────────────────────────────

# Core prompt section — always present regardless of active modules
_PROMPT_CORE = """You are an AI financial advisor integrated into the AFianco platform for SMEs.
The user is an entrepreneur asking questions about their company data.

You have access to tools to query the company database in real time.
ALWAYS use tools to get data before responding — never make up numbers.

Financial model — the company has 4 cost buckets:
- Bucket A: Operating Expenses (spese operative)
- Bucket B: Supplier Purchases (acquisti fornitori)
- Bucket C: Fixed Costs (costi fissi — prorated to the period, approximate)
- Net Result = Revenue minus ALL three buckets (A+B+C)
When reporting net results, ALWAYS use the net_after_fixed field which includes all 4 buckets.

CONTEXTUAL RULE: respond ONLY based on the user's active modules.
Active modules: {active_modules_list}
Do NOT suggest analysis or tools from modules the user does not have active.
{cross_module_instruction}

Reasoning discipline — CRITICAL:
The query_business_summary response includes a "reasoning_contract" with an evidence hierarchy and claim rules. FOLLOW THEM:
- Rank 1 (factual): Cashflow P&L data. You may state as fact.
{reasoning_ranks}

Claim discipline:
- "factual" claims: state directly. ALWAYS read the "currency" field from the tool response and use that exact ISO code (EUR / CHF / USD / GBP) when citing monetary values. Example: '"currency": "CHF"' → say "45,200 CHF" or "CHF 45,200". Never assume EUR — every tool result carries the merchant's currency.
- "conditional" claims: qualify with data context. "No receivables data is available."
- "directional" claims: use hedging. "Your health score suggests attention is needed."
- NEVER claim causation between modules without evidence. Say "this may be related" not "this caused."

When answering, structure your response as a financial analyst:
1. State the factual situation (from pnl) with the date scope
2. Identify the driver or change (from drivers/period_comparison)
3. Assess the risk level (from risk_focus/status)
4. Recommend specific action (from action_focus)
Do not give generic financial advice — every recommendation must trace back to a specific data point.

Rules:
1. {respond_instruction}
2. Base your answers EXCLUSIVELY on data obtained from tools — never make up numbers
3. If a tool returns an error or empty data, say so clearly
4. Be concise and practical — maximum 5-8 sentences for complex analyses, 3-4 for simple lookups
5. Use a professional but approachable tone
6. Do not use emoji
7. When citing numbers, use {number_format_hint}
8. For dates, use {date_format_hint}
9. ALWAYS state the date range at the start of any data-driven answer.
   Today's date is provided in each user message under "TODAY:" — use
   it for relative-period reasoning ("last month", "this week").
10. If a metric cannot be computed or data is missing, explain why briefly
11. If the user's question is ambiguous about the time period AND no ACTIVE REPORT PERIOD context is available, ask them to clarify
12. Maintain period consistency within a conversation
13. When a tool returns has_data=false, explain briefly how the user can activate the module

— CROSS-TOOL COHERENCE (Wave 14.4 cluster — apply when multiple tools disagree, fail, or route the same question) —

14. CASHFLOW PRIMACY: when multiple tools return monetary metrics that disagree, the cashflow figure is the authoritative one. State it as the canonical answer, and note the discrepancy with the other source (do NOT silently pick one) — e.g. "Il fatturato per Maggio 2026 è €12.450 (cashflow). Il modulo Performance Prodotti riporta €11.890: scostamento di €560, probabilmente ordini non sincronizzati."
15. DISCREPANCY DETECTION: when the user asks about a monetary metric AND you have access to BOTH cashflow tools AND product/order tools, AND the numbers differ by more than 1%, you MUST proactively call `query_data_coherence` to investigate. The tool returns orphan records, missing sales_records, and payment_status mismatches that explain WHY the figures diverge. Report the cause to the user — do not let the discrepancy stand unexplained.
16. TOOL VACUUM: if for the user's question you have ZERO suitable tools available (e.g. the user asks about Customers but the org has not activated Analisi Clienti), do NOT invent numbers, do NOT simulate tool calls in text. Respond honestly: "Per rispondere a questa domanda mi servirebbe il modulo X, attualmente non attivo per la tua organizzazione. Contatta l'admin per attivarlo." Suggest the closest available alternative if one exists (e.g. "Posso però mostrarti l'analisi dei top customer dal cashflow se è di aiuto.").
17. NO HALLUCINATED TOOLS: never write the names of tools as fake function-call markup in your reply. If you need data, USE a tool (the agentic loop will execute it). If no tool fits, follow rule 16. Anything that looks like `<function_calls>` or `<invoke>` in your final text is a bug — your final answer to the user must be natural prose.

— TEMPORAL SCOPE & PERIOD HANDLING (Wave 14.4 cluster — every number must be scope-tagged before it leaves your mouth) —

18. TEMPORAL SCOPE DISCIPLINE (Wave 13.6): Every tool result carries a `_temporal_scope` field describing the temporal nature of its data:
    - `period_filtered`: data IS scoped to the request period. You MAY attribute it to "the period the user is viewing" / "il periodo richiesto".
    - `all_time`: data is a MATERIALISED lifetime aggregate (e.g. top customers all time, product margins lifetime). You MUST NOT attribute it to the user's period filter. Use qualifiers like "lifetime", "totale storico", "all-time".
    - `current_state`: data reflects the entity state NOW (open invoices, draft orders). You MUST NOT attribute it to a historical or future window. Use qualifiers like "attualmente", "stato corrente", "now".
    - `forward_looking`: data covers future dates (upcoming bookings, scheduled rentals). Use qualifiers like "in arrivo", "nei prossimi N giorni".
    - `meta`: tool returns metadata, no business data — do not quote as numbers.
    - When a tool result has a `_period_caveat` field, you MUST relay that caveat (or call the alternative tool it suggests) — never cite the data as if it answered the user's actual period.

— ANTI-HALLUCINATION CORE DISCIPLINE (Wave 14, mandatory — violations are bugs) —

19. SOURCE ATTRIBUTION (mandatory). EVERY number you cite to the user MUST be traceable to a specific tool result + field. When citing, mention the source EITHER inline ("secondo query_cashflow_summary, total_sales = 209.954 EUR") OR implicitly by ensuring the number appears verbatim in a tool result you have just seen. Numbers that DO NOT appear in any tool result you have observed are FORBIDDEN — they are by definition hallucinations.

20. HARD STOP ON TOOL ERROR. If a tool result contains an `error` field, an `_error` field, an `is_error: true` flag, or a `_hint` field describing failure, you MUST:
    (a) Inform the user that the specific tool failed and quote the error verbatim
    (b) Suggest concrete remediation (e.g. "call query_cashflow_summary directly with the same period")
    (c) NEVER synthesize the missing numbers, NEVER estimate, NEVER extrapolate from other tool results to fill the gap.
    Correct behaviour: when a sub-tool errors, tell the user the section failed (quoting the error) and call the suggested fallback tool. NEVER respond as if the section returned data — if you cannot read the number from a tool result, the number does not exist for you.
    CRITICAL ANTI-HALLUCINATION RULE: numbers used to illustrate examples in this prompt (including any monetary figure, percentage, or KPI you can see in these instructions) are NEVER real data. The ONLY numbers you may cite to the user are those that appear in the tool_use_result blocks you have observed THIS turn — never from this system prompt, never from your training, never from a previous unrelated session.

21. HAS_DATA BINDING. When ANY tool result contains `"has_data": false`:
    (a) Read the accompanying `_caveat` / `message` field — that's the authoritative explanation of why data is missing.
    (b) Cite the caveat to the user. NEVER produce numbers from that result.
    (c) Do NOT extrapolate "what the data might have been". If has_data=false and the user asked for a metric, say "non ho abbastanza dati per il periodo X per calcolare Y. Servono almeno N record di vendite/spese nella finestra".

22. NO ESTIMATION, NO EXTRAPOLATION. You are a financial analyst, not a forecaster. NEVER:
    - Estimate values you cannot read from a tool result ("probabilmente è circa 50K")
    - Fabricate a breakdown (e.g. monthly Gen/Feb/Mar/...) when no tool returned that breakdown
    - Compute YoY/MoM/trend percentages by hand — use the `yoy.pct.*` / `period_comparison.*` / `trends.*` blocks the tool already provides
    - Infer signs (positive/negative) from context — always read the explicit sign in the tool field
    - Combine numbers from different temporal scopes (e.g. 30d snapshot + YTD period_filtered) without a per-number scope tag
    When tempted to extrapolate, STOP and say "non posso rispondere senza chiamare il tool X con i parametri Y".

23. TRUNCATION HANDLING. If a tool result contains `"_truncated": true`, `_original_size_chars > _cap_chars`, or a JSON that is clearly cut off (incomplete brackets, mid-key text):
    (a) Do NOT attempt to read partial fields and infer the missing ones.
    (b) Re-call the SAME tool with a narrower scope (shorter period, fewer items, specific filter) OR call a more focused alternative tool (e.g. query_cashflow_summary instead of query_business_summary).
    (c) If still truncated after one retry, tell the user "ho dati parziali per la richiesta — posso analizzare un periodo più ristretto?" and stop.

24. CROSS-TURN PERIOD MEMORY. When the user EXPLICITLY sets a period in the conversation (e.g. "mostra YTD", "confronta Q1 vs Q2"), that period becomes the CONVERSATION FRAME for all follow-up questions UNTIL the user explicitly changes it. On follow-ups, ALWAYS emit explicit `start_date` and `end_date` in tool calls — do NOT omit them and rely on the system's default injection, because the default tracks the frontend filter (which may differ from the conversation frame).
    Example:
        Turn 1: User "fatturato YTD" → you call query_cashflow_summary(start_date=<YTD-start>, end_date=<TODAY>)
        Turn 2: User "e i costi?" → you call query_expenses(start_date=<YTD-start>, end_date=<TODAY>)  ← same dates, EXPLICIT
        ⚠ Do NOT call query_expenses() without dates — would default to 30d filter, breaking the YTD frame.

    PERIOD_COMPARISON SPECIAL CASE — query_period_comparison takes FOUR REQUIRED dates: `period_a_start`, `period_a_end`, `period_b_start`, `period_b_end`. NEVER call this tool with empty `{{}}` input or with only 2 of the 4 dates. If the user asks "YTD 2026 vs YTD 2025" you MUST emit ALL FOUR explicitly:
        period_a_start=<YTD-current-year-start>, period_a_end=<TODAY>,
        period_b_start=<same-day-last-year-Jan-1>, period_b_end=<same-MM-DD-last-year>
    Same rule for "Q1 vs Q2", "this month vs last month", etc. — ALWAYS emit the full 4-date contract, NEVER rely on dispatcher fallback (the fallback can only resolve 2 dates, not 4, and the tool will return a partial-input error).

    READING THE RESPONSE (Wave 14.HOTFIX5):
    The tool auto-detects which period is older and labels them
    `period_baseline` (older) vs `period_current` (newer). The delta
    is ALWAYS `(current - baseline)`, so positive pct means GROWTH,
    negative means DECLINE — regardless of which period you named "a"
    vs "b" in the call.
    For each metric, READ `_change_interpretation.<metric>.human_label`
    VERBATIM. Strings like "CRESCITA del +3%", "CALO del -2%", "PERDITA
    RIDOTTA del 42%", "PASSATO DA PERDITA A PROFITTO" already contain
    the correct direction. NEVER compute the direction yourself from
    raw delta_pct numbers — the tool has already disambiguated.

25. SIGN AND DIRECTION INTEGRITY. When citing trend / change percentages and YoY values:
    (a) Use ONLY the explicit sign returned by the tool (e.g. `yoy.pct.total_sales` field). NEVER infer signs from your model of what the business "should" look like.
    (b) If `yoy.pct.X = +1808.7`, that is GROWTH of +1808.7%. NEVER report this as a decline.
    (c) Read the tool's `direction` / `net_direction` / `biggest_change.direction` fields — they are authoritative.
    (d) When the tool returns both absolute values AND percentages (e.g. `yoy.total_sales = 11000`, `yoy.pct.total_sales = +1808.7`), they MUST be consistent with the current period values. Cross-check before citing."""

# Module-specific prompt sections — included only when module is active
_PROMPT_CASHFLOW = """

CASHFLOW TOOLS:
- For cross-module overview: query_business_summary (period or start_date+end_date)
- For cashflow deep-dive: query_cashflow_summary
- For P&L breakdown: query_revenue, query_expenses, query_purchases, query_fixed_costs, query_cashflow
- For receivables/payables: query_receivables_payables
- For top late payers (customer-level drill-down): query_late_payers (Wave 7D — for "chi devo sollecitare?")
- For data range: get_data_range
- For period comparison ("January vs February", "Q1 vs Q2"): query_period_comparison with explicit date ranges
- For monthly trend ("how is revenue trending"): query_monthly_trend
- For revenue projection ("quanto fatturero?"): query_revenue_forecast — ALWAYS qualify as estimate
- For anomaly detection ("giorni anomali", "outlier"): query_anomaly_detection
- For data integrity audit: query_data_coherence

Analyst blocks in cashflow summary — USE THEM:
- "drivers": dominant cost bucket, top expense category, supplier concentration
- "period_comparison": what changed most vs previous period
- "risk_focus": top 1-2 risks already prioritized
- "action_focus": data-grounded recommended actions

Block scope awareness:
- "period_filtered": specific to requested date range
- "current_state" (scadenzario, alerts): reflect NOW, not historical
- "mixed": qualify accordingly"""

_PROMPT_COMMERCE = """

COMMERCE OPERATIONS TOOLS:
Operational pipeline & state:
- Order pipeline: query_order_pipeline (status distribution, conversion rates)
- Fulfillment: query_fulfillment_status (delays, completion rate)
- Payments: query_payment_pipeline (cash at risk)
- Events: query_event_metrics (fill rates, underperforming)
- Bookings: query_booking_utilization (slot utilization)
- Rentals: query_rental_utilization (asset utilization)
Analytics & trends (Wave 7B.2):
- Orders dashboard: query_orders_dashboard (count, revenue, AOV, completion rate, by source — for "come va il mese?")
- AOV trend: query_aov_trend (current vs previous period basket value — for "i clienti spendono di piu?")
- Cancellations breakdown: query_cancellations_breakdown (lost revenue + top cancelled products — for "quanto perdo in cancellazioni?")
- Dormant products: query_dormant_products (no sales in N days — for "cosa non vendo piu?")
Channels, stores & catalog (Wave 7B.3):
- Channels performance: query_channels_performance (per-source revenue, AOV, conversion, cancellation — for "da dove arrivano le vendite?")
- Stores overview: query_stores_overview (all stores, lifetime + last 30d KPIs — for "quanti store ho e come vanno?")
- Single store performance: query_store_performance (single-store deep dive — for "come va lo store X?")
- Catalog health: query_catalog_health (missing prices/costs/descriptions, inactive products — for "il catalogo e' in ordine?")
- New vs Returning split: query_new_vs_returning_split (revenue by customer cohort — for "i clienti tornano?")
- Basket size distribution: query_basket_size_distribution (order size buckets 1/2-3/4-5/6+ — for "come sono fatti i carrelli?")
Agenda calendar (Wave 7C.1) — scope=agenda + globals only, excludes rentals:
- Today's agenda: query_agenda_today (confirmed bookings + blocks for today)
- Upcoming agenda: query_agenda_upcoming (next N days, default 7, max 30 — for "cosa ho questa settimana?")
- Agenda summary: query_agenda_summary (today/tomorrow/week KPIs + free_slots_today)
- Free slots: query_free_slots (rules − blocks − bookings, max 30-day range — for "quando sono libero?")
- Blocked periods: query_blocked_periods (personal/holiday/booking/event with reason filter)
Rentals calendar (Wave 7C.2) — asset-level, source: issued_reservations:
- Rentals today: query_rentals_today (asset currently out — for "cosa ho a noleggio adesso?")
- Rentals upcoming: query_rentals_upcoming (future rentals in N days, max 60 — for "cosa esce questa settimana?")
- Rentals returning: query_rentals_returning (rentals ending in N days, max 30 — for "cosa rientra domani?")
- Single asset availability: query_rental_availability (day-by-day for one product, max 30d — for "quando e' libera la bici X?")
- Rental pipeline: query_rental_pipeline (forward aggregate by asset — for "qual e' l'asset piu prenotato?")
For backward-looking rental utilization, use query_rental_utilization (period occupancy) and query_idle_rentals (catalog-level dormancy).
Events calendar (Wave 7C.3):
- Events calendar: query_events_calendar (operational forward view: name, date, location, capacity, booked, fill — for "che eventi ho la prossima settimana?")
For event analytics (fill rate, capacity, revenue), use query_event_metrics. For underperforming events at the catalog level, use query_underperforming_events.
Coupons & courses (Wave 7D):
- Coupon usage: query_coupon_usage (lifetime + windowed discount granted, top coupons — for "quanto sconto ho dato?")
- Course engagement: query_course_engagement (enrolled, active, recent_active_30d — for "i corsi vengono seguiti?")
Cross-module:
- Smart brief: query_smart_brief (concise overview of all active modules)"""

# Wave 7C.3 — reasoning rules for the calendar surface.
# AFianco has THREE distinct calendars sharing infrastructure but
# answering different mental models. Without this section the AI tends
# to grab whichever tool sounds vaguely relevant. With it, the model
# routes "cosa ho oggi?" to query_agenda_today vs query_rentals_today
# vs query_events_calendar deterministically, based on what the user is
# actually doing as a merchant.
_PROMPT_CALENDAR = """

CALENDAR DISCIPLINE (Wave 7C):
The merchant operates THREE calendars on shared infrastructure. Pick
the right one based on the SURFACE the question targets, not the word
"calendar":

1. AGENDA (services/consulenze) — slot-based bookings of the merchant's TIME.
   Surface: appointments with customers; the merchant IS the resource.
   Scope filter: scope=agenda OR null (global "person busy"). reason != rental.
   Today/tomorrow/week: query_agenda_today, query_agenda_summary
   Forward N days: query_agenda_upcoming
   Free time search: query_free_slots
   Why blocked: query_blocked_periods

2. RENTALS (asset-level reservations) — ASSETS rented to customers.
   Surface: physical asset out with a customer; the ASSET is the resource.
   Source: issued_reservations (status=active). reservation_flavor in {range, slot}.
   Currently out: query_rentals_today
   Future starts: query_rentals_upcoming
   Future ends (ritiri): query_rentals_returning
   Single asset: query_rental_availability (requires product_id)
   Aggregate pipeline: query_rental_pipeline
   Backward utilization (different question!): query_rental_utilization, query_idle_rentals

3. EVENTS (public events with seats) — events open to multiple attendees.
   Surface: many customers attending the same occurrence; capacity-bounded.
   Source: event_occurrences (status=published) + orders.items.occurrence_id.
   Operational forward view: query_events_calendar
   Analytics (fill rate, capacity): query_event_metrics
   Catalog-level underperformers: query_underperforming_events

Routing heuristics:
- "Cosa ho oggi?" → ambiguous: ask, OR if context makes it clear, use the
  dominant calendar (services-heavy org → agenda_today; rental-heavy →
  rentals_today; event-heavy → events_calendar).
- "Sono libero venerdi?" → query_free_slots (agenda).
- "La bici X e' libera sabato?" → query_rental_availability.
- "Quanti posti restano per il concerto?" → query_event_metrics or
  query_events_calendar (both show booked vs capacity).

NEVER mix tools across surfaces in one answer without explicitly labeling
which calendar each datum comes from. e.g. "L'agenda di oggi: 3 consulenze
(query_agenda_today). Inoltre 2 noleggi attivi (query_rentals_today)."
This isolation prevents the AI from blending an empty rental calendar
into a busy services agenda or vice versa."""

_PROMPT_CUSTOMERS = """

CUSTOMER TOOLS:
- Period summary: query_customer_summary (top customers, concentration, data quality)
- Top customers: query_top_customers
- Segments: query_customer_segments (top/active/occasional/inactive/new)
- Customer profile: query_customer_profile (for specific customer deep-dive)
- Churn risk: query_churn_risk (highest risk customers)
- Product affinity: query_customer_product_affinity
- Concentration: query_customer_concentration
- Acquisition trend: query_customer_acquisition_trend (Wave 7D — new customers per month, last N months, direction — for "sto acquisendo clienti?")

Check customer_id_coverage_pct — if below 50%, qualify customer claims."""

_PROMPT_PRODUCTS = """

PRODUCT TOOLS:
- Analytics overview: query_product_analytics (KPIs, ABC, top sellers)
- Margins: query_product_margins (by product or category)
- Trends: query_product_trend (growing/declining products)
- Recommendations: query_product_recommendations (stars, critical margin, declining — omnibus, all alerts at once)
- Focused alerts (use these when the user asks about one specific concern):
  - query_low_stock_products (threshold configurable, default 3)
  - query_underperforming_events (max_fill_rate_pct, default 30)
  - query_idle_rentals (max_utilization_pct, default 10)
  - query_high_cancellation_products (min_cancel_rate_pct, default 20)
Prefer the focused tools when the user names the concern (e.g. "cosa devo riordinare?" → query_low_stock_products); fall back to query_product_recommendations only for open-ended "give me all the issues" requests."""

_PROMPT_DATA_QUALITY = """

DATA QUALITY AWARENESS:
- Use query_data_quality_audit to check data completeness and reliability.
- When a tool returns data_quality flags or low coverage percentages, proactively mention it:
  "Nota: i dati cliente coprono il 45% delle transazioni — i numeri sui clienti sono parziali."
- When products are missing cost data, note that margins are incomplete.
- For any metric with coverage < 50%, always qualify your claims.

ACTION DISCIPLINE:
When suggesting actions:
- Always tie each action to a specific data point ("contattare X perche ha speso Y e non compra da Z giorni")
- Prioritize actions by revenue impact (highest first)
- Maximum 2-3 concrete, specific actions per response
- Never give generic advice ("monitora i costi") — always specific ("rivedere categoria Y cresciuta del 15%")
- When query_customer_profile or query_product_recommendations return suggested_actions, USE them as starting point
- Frame actions as: data point → risk/opportunity → specific action"""


def _build_system_prompt(
    active_modules: Set[str],
    locale_profile,
    today_str: Optional[str] = None,  # Wave 9.B.1: deprecated, kept for back-compat
) -> str:
    """Build a module-aware system prompt.

    Only includes tool instructions for modules the org has active.
    This keeps the prompt focused and reduces token usage.

    Wave 9.B.1 (2026-05): the ``today_str`` parameter is kept for
    backward compatibility with callers (e.g. test fixtures) but is
    NO LONGER injected into the system prompt. The dynamic ``today``
    value was invalidating the Anthropic prompt cache every midnight
    UTC for every org. Now today is appended to the user_message in
    chat() under a "TODAY:" prefix, keeping the system prompt 100%
    deterministic per (active_modules, locale) and the prompt cache
    valid across days.
    """
    # Determine which sections to include
    has_cashflow = "cashflow_monitor" in active_modules
    has_customers = "customers_light" in active_modules
    has_products = "product_catalog" in active_modules
    has_commerce = "commerce" in active_modules  # Wave 7B.1: commerce ops now gated separately

    # Build active modules description
    module_names = []
    if has_cashflow:
        module_names.append("Cashflow Monitor (P&L, scadenzario)")
    if has_commerce:
        module_names.append("Commerce (ordini, evasione, pagamenti, eventi, bookings, noleggi)")
    if has_customers:
        module_names.append("Analisi Clienti (segmentazione, churn, concentrazione)")
    if has_products:
        module_names.append("Catalogo Prodotti (margini, trend, raccomandazioni)")

    active_modules_list = ", ".join(module_names) if module_names else "Cashflow Monitor"

    # Cross-module instructions
    cross_parts = []
    if has_cashflow and has_customers:
        cross_parts.append(
            "When both cashflow and customer data are available, correlate revenue trends "
            "with top customer activity. Check if revenue changes are driven by specific customers."
        )
    if has_cashflow and has_products:
        cross_parts.append(
            "When both cashflow and product data are available, connect revenue to product margins "
            "and trends. Identify which products drive profitability."
        )
    if has_customers and has_products:
        cross_parts.append(
            "When both customer and product data are available, use product affinity "
            "to suggest targeted actions for at-risk customers."
        )
    cross_module_instruction = "\n".join(cross_parts) if cross_parts else ""

    # Reasoning ranks — adapt based on active modules
    ranks = ["- Rank 1 (factual): Cashflow P&L data. You may state as fact."]
    if has_customers:
        ranks.append("- Rank 2 (factual if quality OK): Customer period data. Check customer_id_coverage_pct.")
    ranks.append("- Rank 3 (conditional): Scadenzario. Check data_quality flags.")
    ranks.append("- Rank 4 (directional): Health score. Use for direction only.")

    # Assemble the prompt
    prompt = _PROMPT_CORE.format(
        active_modules_list=active_modules_list,
        cross_module_instruction=cross_module_instruction,
        reasoning_ranks="\n".join(ranks),
        respond_instruction=locale_profile.respond_instruction,
        number_format_hint=locale_profile.number_format_hint,
        date_format_hint=locale_profile.date_format_hint,
        # Wave 9.B.1: `today` no longer interpolated here — it lives in
        # the user message wrapper so the system prompt stays cacheable.
    )

    # Add module-specific sections
    if has_cashflow:
        prompt += _PROMPT_CASHFLOW
    if has_commerce:
        prompt += _PROMPT_COMMERCE  # Wave 7B.1: gated by commerce module entitlement
        prompt += _PROMPT_CALENDAR  # Wave 7C.3: calendar reasoning rules (agenda/rentals/events)
    if has_customers:
        prompt += _PROMPT_CUSTOMERS
    if has_products:
        prompt += _PROMPT_PRODUCTS

    # Data quality awareness — always included
    prompt += _PROMPT_DATA_QUALITY

    return prompt


def _compute_max_tokens(user_message: str, tool_count_hint: int = 0) -> int:
    """Compute dynamic max_tokens based on query complexity.

    Default 1500. Raised to 2048 for complex analyses or multi-tool queries.
    """
    msg_lower = user_message.lower()
    if any(kw in msg_lower for kw in _COMPLEX_KEYWORDS):
        return 2048
    if tool_count_hint >= 2:
        return 2048
    return 1500


async def chat(
    org_id: str,
    session_id: str,
    user_message: str,
    locale: str = "it",
    user_id: str = "",
    period_context: dict = None,
    agent_id: str = None,
) -> str:
    """Process a chat message and return AI response using tool use.

    Module-aware: only exposes tools from active modules and adapts
    the system prompt accordingly.

    Sessions are persisted to MongoDB.  On error the failed user message
    is never written to the database (only local list is mutated).

    period_context: optional dict with {label, start, end} from the
    cashflow module's active period selection.  Injected into the system
    prompt so Claude scopes tool calls to the correct date range.

    Wave 4 (2026-05) — agent_id parameter
    -------------------------------------
    agent_id specifies which agent persona to invoke. When None or
    "financial_analyst" the behaviour is identical to pre-Wave-4
    (default agent). Future agents (HR, marketing, ...) will use
    different persona_prompt + tool_scopes via the agent registry.
    For now non-default agent_ids resolve through the registry, get
    their tool_scopes intersected with the org's active modules, and
    are recorded in AIUsageEvent.agent_id for cost attribution.
    """
    from services.claude_client import send_messages_with_tools, ClaudeUnavailableError, is_available
    from services.ai_tool_registry import get_tools_for_chat
    from core.locale_utils import get_locale_profile
    from repositories import chat_session_repository
    from datetime import date

    if not is_available():
        raise ClaudeUnavailableError("Chat AI non disponibile. Configura ANTHROPIC_API_KEY.")

    # Wave 4 (2026-05) — agent resolution.
    # Default to financial_analyst when caller doesn't specify. The
    # registry import is local to avoid an import-cycle at module load
    # (services.agents imports services.chat_service indirectly through
    # the tools registry).
    from services.agents import DEFAULT_AGENT_ID, get_agent, AgentNotFoundError
    resolved_agent_id = agent_id or DEFAULT_AGENT_ID
    try:
        agent_def = get_agent(resolved_agent_id)
    except AgentNotFoundError:
        # Unknown agent_id from a malicious / outdated client — fall
        # back to default. We log a warning so the system_admin can
        # spot misuse patterns.
        logger.warning(
            "chat_service: unknown agent_id %r, falling back to %s",
            resolved_agent_id, DEFAULT_AGENT_ID,
        )
        resolved_agent_id = DEFAULT_AGENT_ID
        agent_def = get_agent(DEFAULT_AGENT_ID)

    # Load persisted history (or start fresh)
    # Wave 1.5 (2026-05): pass user_id so intra-org session hijack is
    # blocked at the repository level (find_session filters by user_id
    # when provided). If a peer in the same org guesses our session_id,
    # they see None — same as "not found".
    session_doc = await chat_session_repository.find_session(
        org_id, session_id, user_id=user_id or None,
    )
    history = list(session_doc["messages"]) if session_doc else []

    # Wave 9.B.1 — prefix the user message with TODAY. Pre-fix this
    # lived in the system prompt under rule 9; that invalidated the
    # Anthropic prompt cache every midnight UTC for every org. Moving
    # it into the user message preserves the date context (the model
    # still knows "today is X" for relative-period reasoning) without
    # busting the cache.
    _today_iso = date.today().isoformat()
    _user_message_with_today = f"TODAY: {_today_iso}\n\n{user_message}"
    history.append({"role": "user", "content": _user_message_with_today})

    # Truncate to keep within context limits
    if len(history) > _MAX_HISTORY:
        history = history[-_MAX_HISTORY:]

    # Get module-aware tools and active modules set
    tools, tool_dispatch, active_modules = await get_tools_for_chat(org_id)

    # Build dynamic system prompt based on active modules
    profile = get_locale_profile(locale)
    # Wave 9.B.1: do NOT pass today_str — the prompt is now cache-stable.
    # Wave 10.B.1: _build_system_prompt produces the STABLE prefix only.
    # Volatile parts (proactive_context for new sessions, period_context
    # for filter changes) are accumulated separately and shipped as a
    # second, NON-cached system block. This keeps the cached prefix
    # invariant across:
    #   - new vs returning sessions (proactive only fires for new)
    #   - period filter changes (was breaking cache on every filter click)
    #   - intra-org variance per filter
    # Forensic audit measured cache hit ratio at 12.3% pre-fix — most of
    # the gap came from period_context being concatenated into a single
    # 'system' string.
    system_stable = _build_system_prompt(active_modules, profile)

    system_dynamic_parts: List[str] = []

    # Proactive context injection for new sessions
    # Wave 1.5 (B9):  passes locale so the proactive context block
    #                 honours the user's chosen language.
    # Wave 13.3:      passes period_context so the health-score snapshot
    #                 is computed on the user's ACTIVE filter (e.g. YTD)
    #                 instead of the pre-Wave-13 hardcoded 30d window
    #                 that caused the model to misquote 30d health as
    #                 YTD health (BUG #2 of the Wave 13 audit).
    if session_doc is None:
        proactive_ctx = await _build_proactive_context(
            org_id, active_modules, locale=locale,
            period_context=period_context,
        )
        if proactive_ctx:
            system_dynamic_parts.append(proactive_ctx)

    # Inject active period context so Claude scopes tool calls correctly
    if period_context:
        p_label = period_context.get("label", "")
        p_start = period_context.get("start")
        p_end = period_context.get("end")
        if p_start and p_end:
            system_dynamic_parts.append(
                f"ACTIVE REPORT PERIOD: The user is currently viewing the cashflow report "
                f"for the period {p_start} to {p_end} (filter: {p_label}). "
                f"Unless the user explicitly asks about a different period, "
                f"use start_date={p_start} and end_date={p_end} for all tool calls."
            )
        elif p_label and p_label in ("7d", "30d", "90d"):
            system_dynamic_parts.append(
                f"ACTIVE REPORT PERIOD: The user is currently viewing the cashflow report "
                f"for the last {p_label}. Unless the user explicitly asks about a different period, "
                f"use period={p_label} for summary tool calls."
            )

    # Wave 10.B.1 — assemble the final 'system' payload. When there's
    # nothing dynamic, pass the stable string and let the provider wrap
    # it as a single cached block (current behaviour, no regression).
    # When dynamic parts exist, pass an explicit two-block list so the
    # cache marker lives only on the stable prefix.
    if system_dynamic_parts:
        system_dynamic = "\n\n".join(system_dynamic_parts)
        # NOTE: send_messages_with_tools accepts Union[str, list] for
        # system — the provider's _system_with_cache handles both shapes.
        system = [
            {"type": "text", "text": system_stable,
             "cache_control": {"type": "ephemeral"}},
            {"type": "text", "text": system_dynamic},
        ]
    else:
        system = system_stable

    # Resolve deterministic default dates from period_context.
    _ctx_start = period_context.get("start") if period_context else None
    _ctx_end = period_context.get("end") if period_context else None
    _ctx_label = period_context.get("label") if period_context else None

    # Wave 14.5 — Conversation period inheritance (intra-chat).
    #
    # When the model emits explicit ``start_date``/``end_date`` on a
    # tool call (typically the first call of a multi-round chat where
    # the user explicitly asked for a non-default window like YTD),
    # we capture those dates as the "conversation period" for the
    # REMAINDER of this chat() call. Subsequent tool calls that omit
    # dates then inherit the conversation period rather than falling
    # back to the frontend's period_context (which may be a different
    # filter, e.g. 30d while the conversation is about YTD).
    #
    # This implements Rule 24 (CROSS-TURN PERIOD MEMORY) at the
    # mechanical layer — the rule instructs the model to re-emit
    # dates, but the dispatcher now also remembers them so even if
    # the model forgets to re-emit, the FRAME is preserved.
    #
    # Scope: intra-chat only. Cross-turn persistence (across multiple
    # user messages within the same session) is a future extension —
    # the existing Rule 24 + period_audit (Wave 13.2) provide
    # sufficient coverage for the multi-user-message case.
    _conv_period = {"start": None, "end": None, "source": None}

    # Wave 13.2 — Period audit accumulator. We append one entry per
    # on_tool_call invocation; _on_round consumes (and clears) the list
    # at the end of each Anthropic round-trip. The accumulator captures
    # the model's raw input, whether injection was applied, and the
    # final resolved period — giving us a complete forensic trail of
    # WHICH period each tool was actually exercised on. Used for both
    # structured logging AND the AIUsageEvent.period_audit field.
    _pending_tool_audits: list = []

    # Wave 13.2 — Resolve the user-active period once (period_context
    # from the frontend) into a canonical audit dict so every event in
    # this chat carries the SAME "what the user was looking at" record.
    _active_period_audit = _resolve_active_period_audit(period_context)
    if _active_period_audit is not None:
        logger.info(
            "chat_service: org=%s user=%s session=%s active period=%s "
            "(start=%s end=%s source=%s)",
            org_id, user_id, session_id,
            _active_period_audit.get("label"),
            _active_period_audit.get("start"),
            _active_period_audit.get("end"),
            _active_period_audit.get("resolution_source"),
        )

    async def on_tool_call(tool_name: str, tool_input: dict) -> dict:
        # Wave 13.2 — capture the un-injected tool input BEFORE we
        # possibly mutate it below, so the audit shows what the model
        # actually emitted vs what the dispatcher rewrote it to.
        _audit_input_from_model = {
            k: v for k, v in tool_input.items()
            if k in ("period", "start_date", "end_date")
        }
        _audit_injection_applied = False

        # Wave 14.5 — capture the model's explicit dates BEFORE
        # injection. If the model emits both start_date and end_date
        # explicitly, they become the new "conversation period" for
        # subsequent tool calls within this chat() call. This is the
        # mechanical implementation of Rule 24 (CROSS-TURN PERIOD
        # MEMORY) — even if the model forgets to re-emit dates on a
        # follow-up tool call, the dispatcher remembers them.
        _model_start = tool_input.get("start_date")
        _model_end = tool_input.get("end_date")
        if _model_start and _model_end:
            # Model explicitly asked for a window — record it as the
            # conversation frame.
            _conv_period["start"] = _model_start
            _conv_period["end"] = _model_end
            _conv_period["source"] = "model_explicit"

        # Injection priority for the CURRENT tool call:
        #   1. Model's own explicit dates (highest — already in tool_input)
        #   2. Conversation period from a PRIOR tool call in this chat
        #   3. Frontend period_context (start+end, label, or token)
        # Each branch only fires when there's nothing higher in
        # tool_input already.
        if _conv_period["start"] and _conv_period["end"]:
            has_explicit = tool_input.get("start_date") and tool_input.get("end_date")
            if not has_explicit:
                # Inherit the conversation frame
                injected = {k: v for k, v in tool_input.items() if k != "period"}
                injected["start_date"] = _conv_period["start"]
                injected["end_date"] = _conv_period["end"]
                tool_input = injected
                _audit_injection_applied = True
        elif _ctx_start and _ctx_end:
            has_explicit = tool_input.get("start_date") and tool_input.get("end_date")
            if not has_explicit:
                injected = {k: v for k, v in tool_input.items() if k != "period"}
                injected["start_date"] = _ctx_start
                injected["end_date"] = _ctx_end
                tool_input = injected
                _audit_injection_applied = True
        elif _ctx_label and _ctx_label in ("7d", "30d", "90d"):
            has_explicit = tool_input.get("start_date") or tool_input.get("end_date") or tool_input.get("period")
            if not has_explicit:
                tool_input = {**tool_input, "period": _ctx_label}
                _audit_injection_applied = True

        # Wave 1.5 (B10): inject locale into tool_input so tools that
        # delegate to summary builders (build_unified_summary,
        # build_ai_summary) can honour the user's language. Tools that
        # ignore locale see no impact (extra dict key).
        if "locale" not in tool_input:
            tool_input = {**tool_input, "locale": locale}

        # Wave 13.2 — record the period the tool will actually see.
        # We resolve it now (cheap, pure function) so the audit reflects
        # what data the tool computed against, not what the model asked.
        _audit_resolved = _resolve_tool_period_audit(tool_input)

        # Wave 13.2 — push the audit entry; _on_round drains the list.
        _pending_tool_audits.append({
            "tool": tool_name,
            "input_from_model": _audit_input_from_model,
            "injection_applied": _audit_injection_applied,
            "resolved": _audit_resolved,
        })
        logger.info(
            "chat_service: tool=%s injection=%s resolved=%s",
            tool_name, _audit_injection_applied,
            (_audit_resolved or {}).get("label"),
        )

        # ── Wave 14.HOTFIX6 (F3) — period inversion validation ──────
        # Pre-HOTFIX6 if the model emitted start_date > end_date (a
        # typo or year-arithmetic mistake) the dispatcher passed it
        # through verbatim, the tool computed period_days = negative,
        # daily proration divided by a negative integer, and downstream
        # math produced sign-inverted KPIs that the AI then reported
        # as fact. The audit identified this as the only residual
        # silent-failure path after HOTFIX1-5.
        #
        # Now: any tool call with start_date > end_date (or
        # period_a_start > period_a_end / period_b_start > period_b_end
        # for the comparison tool) returns an explicit error envelope
        # that Rule 20 forces the model to surface. The model is
        # asked to re-emit with dates in chronological order.
        def _inverted(start_k: str, end_k: str) -> bool:
            s, e = tool_input.get(start_k), tool_input.get(end_k)
            return bool(s and e and s > e)

        inverted_pairs = []
        if _inverted("start_date", "end_date"):
            inverted_pairs.append(("start_date", "end_date"))
        if tool_name == "query_period_comparison":
            if _inverted("period_a_start", "period_a_end"):
                inverted_pairs.append(("period_a_start", "period_a_end"))
            if _inverted("period_b_start", "period_b_end"):
                inverted_pairs.append(("period_b_start", "period_b_end"))

        if inverted_pairs:
            pair_strs = ", ".join(f"{s}>{e}" for s, e in inverted_pairs)
            logger.warning(
                "chat_service: tool=%s called with inverted date "
                "pair(s): %s — refusing dispatch, returning error envelope",
                tool_name, pair_strs,
            )
            err_msg = (
                f"Date di periodo invertite per {tool_name}: {pair_strs}. "
                "Il dispatcher rifiuta di eseguire il tool con un "
                "intervallo negativo. Re-emettere con dates in ordine "
                "cronologico (start <= end)."
            )
            return {
                "error": err_msg,
                "_error": "inverted_period_dates",
                "_hint": (
                    "Verificare l'ordine delle date emesse. Per "
                    "query_period_comparison, ogni coppia "
                    "(period_a_start <= period_a_end) e "
                    "(period_b_start <= period_b_end) deve essere "
                    "cronologica."
                ),
                "has_data": False,
                "_temporal_scope": "period_filtered",
                "_data_integrity": {
                    "status": "error",
                    "message": err_msg,
                },
                "_source": "chat_service.dispatcher_validation",
                "_envelope_version": "14.0",
            }

        # Wave 14.HOTFIX2 — hard-fail for tools whose contract the
        # dispatcher cannot satisfy via period_context fallback.
        # query_period_comparison requires FOUR dates (period_a_start,
        # period_a_end, period_b_start, period_b_end). Pre-HOTFIX2
        # the model was emitting empty input for this tool, the
        # dispatcher injected only start_date+end_date as fallback
        # (2 of 4), the tool ran with partial input and the model
        # then hallucinated the answer (the 2026-05-16 prod incident
        # reproduced live on the second deploy day).
        #
        # The fix returns an explicit error envelope that Rule 20
        # (HARD STOP ON TOOL ERROR) FORCES the model to surface,
        # rather than silently fall back to partial data.
        if tool_name == "query_period_comparison":
            missing_required = [
                p for p in (
                    "period_a_start", "period_a_end",
                    "period_b_start", "period_b_end",
                ) if not tool_input.get(p)
            ]
            if missing_required:
                logger.warning(
                    "chat_service: query_period_comparison invoked with "
                    "missing required params %s — refusing dispatch, "
                    "returning error envelope (model must re-emit with "
                    "all 4 dates per Rule 24)",
                    missing_required,
                )
                err_msg = (
                    "query_period_comparison requires ALL 4 dates "
                    "(period_a_start, period_a_end, period_b_start, "
                    "period_b_end). Missing: " + ", ".join(missing_required)
                    + ". Per Rule 24 (CROSS-TURN PERIOD MEMORY) you "
                    "MUST emit the 4 dates explicitly — re-call with "
                    "period_a_start=<current-period-start>, "
                    "period_a_end=<current-period-end>, "
                    "period_b_start=<reference-period-start>, "
                    "period_b_end=<reference-period-end>."
                )
                result = {
                    "error": err_msg,
                    "_error": "missing_required_params",
                    "_hint": (
                        "Re-call query_period_comparison with all 4 "
                        "date params, OR call query_cashflow_summary "
                        "twice (once per period) and compare manually."
                    ),
                    "has_data": False,
                    "_temporal_scope": "period_filtered",
                    "_data_integrity": {
                        "status": "error",
                        "message": err_msg,
                    },
                    "_source": "chat_service.dispatcher_validation",
                    "_envelope_version": "14.0",
                }
                # Skip tool_dispatch and skip temporal_scope injection
                # — the error envelope is already complete.
                return result

        result = await tool_dispatch(org_id, tool_name, tool_input)

        # Wave 13.6 — inject the temporal scope marker so the model
        # can NEVER confuse a snapshot tool's output with period-
        # filtered data. The registry in core/tool_temporal_scope.py
        # declares scope per tool; the helper preserves any pre-
        # existing _temporal_scope a tool may have set itself
        # (e.g. query_product_trend uses the more precise label
        # "materialized_30d_vs_prior_30d"). Non-dict results and
        # unknown tools pass through unchanged.
        from core.tool_temporal_scope import attach_temporal_scope
        result = attach_temporal_scope(tool_name, result)

        # Wave 14.1.B — envelope wrapper at the dispatcher boundary.
        # After ``attach_temporal_scope`` injects the Wave 13.6 scope
        # marker (if missing), this pass completes the canonical
        # envelope by adding ``has_data``, ``_data_integrity``, and
        # ``_source`` to ANY tool result that isn't already an
        # envelope. The 5 tools migrated in Phase 14.1.A produce
        # envelopes directly so this is a no-op for them. Every
        # OTHER tool (~57) now gets envelope compliance for free
        # without a per-tool patch.
        from core.tool_envelope import wrap_tool_result_envelope
        result = wrap_tool_result_envelope(tool_name, result)

        # Wave 9.A.3 — defensive truncation. A single tool returning
        # 30K+ tokens of data inflates the NEXT round's input by the
        # same amount (the agentic loop sends the tool_result back to
        # Anthropic). Forensic Mongo evidence: a real chat in April
        # 2026 hit 33,531 input tokens ($0.10 in one call) because a
        # tool result was huge. Cap at _MAX_TOOL_RESULT_CHARS so a
        # single tool can't spike the conversation cost unbounded.
        return _truncate_tool_result(result, tool_name)

    # Compute dynamic max_tokens
    max_tokens = _compute_max_tokens(user_message, tool_count_hint=len(tools))

    # Wave 9.A.3 — pre-flight input guard. Refuse to start the agentic
    # loop if the history already exceeds _MAX_HISTORY_CHARS. Cheaper
    # than discovering the spike via a $0.10 Anthropic round-trip.
    history_size = _estimate_history_chars(history)
    if history_size > _MAX_HISTORY_CHARS:
        logger.warning(
            "chat_service: refusing chat for org=%s user=%s — history "
            "is %d chars (cap=%d). User should start a new chat session.",
            org_id, user_id, history_size, _MAX_HISTORY_CHARS,
        )
        # Translate to a localised user-facing message at the router
        # layer. Raising ClaudeUnavailableError reuses the existing
        # graceful error handling without inventing a new exception
        # type that the frontend doesn't know about.
        raise ClaudeUnavailableError(
            f"Chat history too large ({history_size:,} chars > "
            f"{_MAX_HISTORY_CHARS:,} cap). Please start a new chat session."
        )

    # Wave 8B — governance pre-flight. Blocks chat if kill switch is
    # active, the org/user/global budget has reached its hard limit,
    # or the load-shed throttle randomly rejects this call. Raises a
    # GovernanceError subclass (AIDisabledError / AIThrottledError /
    # BudgetExceededError) propagated to the API layer as HTTP 429/503.
    # The check is ONCE per chat — multi-turn loops within do not re-check
    # (acceptable race for MVP: at most one chat slips through after limit).
    from services.llm.budget_guard import check_budget_or_raise
    await check_budget_or_raise(
        organization_id=org_id,
        user_id=user_id or None,
        feature="chat",
        agent_id=resolved_agent_id,
    )

    # Wave 8A.2 — multi-turn tracking. Generate a stable conversation_id
    # so all events from this chat (potentially N round-trips) can be
    # grouped together in the governance dashboard. The agentic loop
    # invokes `on_round` after each Anthropic HTTP request, and we
    # write one AIUsageEvent per round (not 1 aggregate).
    import uuid
    from repositories import usage_repository as _usage_repo
    from services.claude_client import _MODEL as _CHAT_MODEL
    from services.ai_cost_calculator import compute_cost_usd as _compute_cost_usd

    conversation_id = uuid.uuid4().hex

    async def _on_round(round_index: int, round_usage: dict) -> None:
        """Write one AIUsageEvent per Anthropic round-trip in the loop.

        Failures here MUST NOT kill the chat — the agentic loop wraps
        this call in a try/except anyway, but we double-defend by
        catching here too.
        """
        try:
            tok_in = round_usage.get("input_tokens")
            tok_out = round_usage.get("output_tokens")
            cache_r = round_usage.get("cache_read_tokens")
            cache_w = round_usage.get("cache_creation_tokens")
            # Wave 8E.2 — pass cache_creation_tokens so the cost includes
            # the 1.25× premium for tokens being WRITTEN to cache. Pre-fix
            # those were silently dropped → 15-25% under-billing on cache-
            # heavy chats.
            round_cost = _compute_cost_usd(
                provider="anthropic",
                model_version=_CHAT_MODEL,
                tokens_prompt=tok_in,
                tokens_completion=tok_out,
                cache_read_tokens=cache_r or 0,
                cache_creation_tokens=cache_w or 0,
            )
            # Wave 13.2 — drain the period audit accumulator into the
            # event. The list captures one entry per tool_use that ran
            # during THIS round; we copy + clear so the next round
            # starts fresh.
            _round_tool_audits = list(_pending_tool_audits)
            _pending_tool_audits.clear()

            # Build the period_audit payload. ``active`` is the user's
            # period context (resolved once at chat() entry, identical
            # across all events of this conversation). ``tool_dispatches``
            # is per-round so the dashboard can see exactly which tool
            # used which window in each Anthropic round-trip.
            event_period_audit = None
            if _active_period_audit is not None or _round_tool_audits:
                event_period_audit = {}
                if _active_period_audit is not None:
                    event_period_audit["active"] = _active_period_audit
                if _round_tool_audits:
                    event_period_audit["tool_dispatches"] = _round_tool_audits

            await _usage_repo.record_usage(
                org_id, "ai_assistant", "chat",
                tokens_prompt=tok_in,
                tokens_completion=tok_out,
                cache_read_tokens=cache_r,
                cache_creation_tokens=cache_w,
                # Wave 10.B.6 — surface per-round latency so the
                # governance dashboard can plot a "p95 chat latency"
                # KPI and detect slow Anthropic responses.
                latency_ms=round_usage.get("latency_ms"),
                user_id=user_id or None,
                model_version=_CHAT_MODEL,
                provider="anthropic",
                cost_usd=round_cost,
                agent_id=resolved_agent_id,
                conversation_id=conversation_id,
                feature_metadata={
                    "round_index": round_index,
                    "session_id": session_id,
                },
                # Wave 13.2 — period audit trail (forensic).
                period_audit=event_period_audit,
            )
        except Exception as _e:
            logger.warning(
                "chat_service: per-round record_usage failed (round=%d): %s",
                round_index, _e,
            )

    try:
        assistant_text, updated_messages, token_usage = await send_messages_with_tools(
            system=system,
            messages=history,
            tools=tools,
            on_tool_call=on_tool_call,
            max_tokens=max_tokens,
            temperature=0.4,
            on_round=_on_round,  # Wave 8A.2 — per-round tracking
        )

        # Persist compacted history to MongoDB (refreshes TTL)
        compacted = _compact_history(updated_messages)
        expires_at = await _compute_expires_at(org_id)
        # Auto-title: use first user message (truncated) for new sessions
        auto_title = user_message[:60] if session_doc is None else None
        await chat_session_repository.upsert_messages(
            org_id, session_id, user_id, compacted,
            expires_at=expires_at,
            title=auto_title,
        )

        # Wave 8A.2 — per-round AIUsageEvent already written by _on_round
        # callback during the agentic loop. The previous aggregate event
        # written here under-counted multi-turn chats because token_usage
        # below is the SUM across all rounds — writing it as a single
        # event made N round-trips look like 1 in the dashboard. Now
        # each round is its own event, all linked by conversation_id.
        # token_usage is still useful as a sanity check + for the
        # function's return value, but no event is written from here.
        try:
            tok_in_total = token_usage.get("input_tokens", 0)
            tok_out_total = token_usage.get("output_tokens", 0)
            logger.debug(
                "chat_service: conversation=%s aggregate tokens %d in + %d out across rounds (per-round events written by _on_round)",
                conversation_id, tok_in_total, tok_out_total,
            )
        except Exception as e:
            logger.warning("chat_service: failed to record token usage: %s", e)

        return assistant_text
    except Exception:
        # Do NOT persist on failure — the failed user message stays local only
        raise


def _compact_history(messages: List[dict]) -> List[dict]:
    """Keep full messages for context but cap total size.

    Tool use/result exchanges are preserved so the model retains
    context about what data it already queried.  We only trim if
    the total count exceeds _MAX_HISTORY.

    Wave 14.CONSOLIDATE R1 — after truncation we run a pairing pass
    so the resulting message list NEVER contains a ``tool_result``
    block whose matching ``tool_use`` (by ``tool_use_id``) has been
    dropped. Anthropic's API rejects orphan tool_result blocks with
    a 400 error, which previously bubbled up as a generic chat
    failure on rare long-history sessions. The Wave 13.2 audit
    flagged this as a latent crash; we close the loop here.
    """
    if len(messages) <= _MAX_HISTORY:
        return messages
    truncated = messages[-_MAX_HISTORY:]
    return _strip_orphan_tool_blocks(truncated)


def _strip_orphan_tool_blocks(messages: List[dict]) -> List[dict]:
    """Remove tool_result blocks whose tool_use_id has no matching
    tool_use in the message list, AND remove tool_use blocks whose
    matching tool_result is missing.

    Wave 14.CONSOLIDATE R1.

    Anthropic's API contract: every ``tool_use`` block in an assistant
    message MUST be followed (in a subsequent user message) by a
    ``tool_result`` block carrying the same ``tool_use_id``. Truncation
    by message count can break this pairing in two directions:

      * head-side: an old tool_use is dropped, but its tool_result is
        in a message that survived → orphan ``tool_result``;
      * tail-side: a tool_use survives but its tool_result is the next
        message which got pushed out → orphan ``tool_use``.

    Both orphans cause Anthropic to reject the next round-trip with a
    400 error. The fix is to scan the truncated list once, build the
    set of valid pairings, and rebuild messages dropping any block on
    either side that lacks its partner.

    Text-only messages and text-only blocks are NEVER touched. If a
    message becomes empty after stripping, it's dropped entirely so
    the API never sees a message with empty content.

    Edge cases handled:
      - single-block ``content`` shorthand (string, not list): pass through
      - mixed assistant message (text + tool_use): only the orphan
        tool_use block is dropped, the text block survives
      - mixed user message (text + tool_result): same, only orphan
        tool_result blocks removed
    """
    # ── 1st pass: collect all tool_use_ids present in assistant messages
    tool_use_ids: Set[str] = set()
    tool_result_ids: Set[str] = set()
    for msg in messages:
        content = msg.get("content")
        if not isinstance(content, list):
            continue
        role = msg.get("role")
        for block in content:
            if not isinstance(block, dict):
                continue
            btype = block.get("type")
            if role == "assistant" and btype == "tool_use":
                tid = block.get("id")
                if tid:
                    tool_use_ids.add(tid)
            elif role == "user" and btype == "tool_result":
                tid = block.get("tool_use_id")
                if tid:
                    tool_result_ids.add(tid)

    # Valid pairings = ids that appear in BOTH sets
    valid_pairs = tool_use_ids & tool_result_ids
    if valid_pairs == tool_use_ids == tool_result_ids:
        # Common case: no orphans — return unchanged
        return messages

    # ── 2nd pass: rebuild messages, dropping orphan blocks
    cleaned: List[dict] = []
    dropped_blocks = 0
    for msg in messages:
        content = msg.get("content")
        if not isinstance(content, list):
            # String content (text-only message) — keep as-is
            cleaned.append(msg)
            continue
        role = msg.get("role")
        new_blocks = []
        for block in content:
            if not isinstance(block, dict):
                new_blocks.append(block)
                continue
            btype = block.get("type")
            if role == "assistant" and btype == "tool_use":
                if block.get("id") in valid_pairs:
                    new_blocks.append(block)
                else:
                    dropped_blocks += 1
            elif role == "user" and btype == "tool_result":
                if block.get("tool_use_id") in valid_pairs:
                    new_blocks.append(block)
                else:
                    dropped_blocks += 1
            else:
                # text blocks, image blocks, etc. — always preserved
                new_blocks.append(block)
        if new_blocks:
            cleaned.append({**msg, "content": new_blocks})
        # else: message had ONLY orphan tool blocks; drop entire msg

    if dropped_blocks:
        logger.info(
            "chat_service: _strip_orphan_tool_blocks removed %d orphan "
            "tool_use/tool_result block(s) after history truncation "
            "(Wave 14 R1 safety)",
            dropped_blocks,
        )
    return cleaned


# ── Wave 13.2 — Period audit helpers ─────────────────────────────────────────


def _resolve_active_period_audit(period_context) -> Optional[dict]:
    """Turn a frontend-supplied ``period_context`` into a canonical audit dict.

    ``period_context`` is the dict the frontend ships per chat request,
    in the shape ``{"label": "ytd", "start": "2026-01-01", "end": "2026-05-16"}``.
    We normalise it through ``core.period_resolver.resolve`` so every
    AIUsageEvent in this chat carries the SAME "what the user was on"
    record regardless of which path produced the dict.

    Returns None when no period_context was supplied OR when the
    resolver rejects the input — we log+swallow rather than blocking
    the chat, since period auditing is observability, never blocking.
    """
    if not period_context:
        return None
    try:
        # Lazy import — period_resolver is stdlib-only at import time
        # but keeping it local avoids any future circular-import risk.
        from core.period_resolver import resolve, InvalidPeriodError

        # The frontend often sends only label + dates; period_resolver
        # accepts both. ``allow_future`` is False to surface bad inputs.
        resolved = resolve(
            period=period_context.get("label"),
            start_date=period_context.get("start"),
            end_date=period_context.get("end"),
            strict=False,
        )
        return resolved.to_audit_dict()
    except Exception as exc:   # noqa: BLE001 — auditing must never block
        logger.warning(
            "chat_service: failed to resolve active period_context=%r: %s",
            period_context, exc,
        )
        return None


def _resolve_tool_period_audit(tool_input: dict) -> Optional[dict]:
    """Resolve the period a tool will actually see, post-injection.

    Mirrors what ``services.ai_analytics_service._get_date_range`` does
    inside the tool — but called here at audit time so we know what
    window the tool will compute against WITHOUT having to execute it
    or parse its result.

    Returns None on any failure (auditing never blocks the chat).
    """
    try:
        from core.period_resolver import resolve

        resolved = resolve(
            period=tool_input.get("period"),
            start_date=tool_input.get("start_date"),
            end_date=tool_input.get("end_date"),
            strict=False,
        )
        return resolved.to_audit_dict()
    except Exception as exc:   # noqa: BLE001
        logger.debug(
            "chat_service: tool period audit failed (input=%r): %s",
            tool_input, exc,
        )
        return None


async def _build_proactive_context(
    org_id: str,
    active_modules: Set[str],
    locale: str = "it",
    period_context: Optional[dict] = None,
) -> str:
    """Build a lightweight proactive context for new chat sessions.

    Fetches key metrics from active modules and formats them as a system
    prompt addendum. This helps the AI provide relevant, contextualized
    responses from the very first message without requiring a tool call.

    Wave 1.5 (B9): now accepts ``locale`` and passes it to the sub-summary
    builders that support localisation (today: build_ai_summary). Until
    Wave 1.5, this function hardcoded "it" — admin with locale="en" saw
    an Italian proactive context inside an otherwise English chat.

    Wave 13.3 (Period Integrity): now accepts ``period_context`` and uses
    it to scope the health score to the user's ACTIVE period instead of
    hardcoding 30d. Pre-fix this was BUG #2 of the Wave 13 audit: a user
    on a YTD filter would see the chat AI proactively claim
    "Health 48/100" (a 30d snapshot) and then, when asked "what is my
    health score", quote 48 as if it were the YTD answer — while the
    cashflow dashboard correctly showed 33/100 for YTD. The fix:
      * Compute the health score on the user's actual window.
      * Tag every period-scoped line with the explicit period in brackets
        so the model can never mistake a 30d snapshot for a YTD claim.
      * Add a discipline rule to the preamble: "snapshots are scoped to
        the bracketed period; for OTHER periods, CALL the tool".

    Returns empty string if no useful context is available.
    """
    parts = []

    try:
        # Alert summary — current state, not period-scoped. Tagged as
        # such below.
        #
        # Wave 13.3 — fixed a latent bug: pre-fix this branch called
        # ``alert_repository.find_active(...)`` which has NEVER existed
        # in the repository. The surrounding try/except silently swallowed
        # the AttributeError every time, so the alert line of the proactive
        # context was effectively dead code since the proactive context
        # was introduced (commit 4de23f7). We now use the real function
        # ``find_by_org`` and filter out resolved alerts in Python so the
        # model actually sees active alerts on session start.
        from repositories import alert_repository
        alerts_raw = await alert_repository.find_by_org(org_id, limit=50)
        alerts = [a for a in alerts_raw if a.get("status") != "resolved"]
        high = sum(1 for a in alerts if a.get("severity", "").lower() == "high")
        medium = sum(1 for a in alerts if a.get("severity", "").lower() == "medium")
        if high > 0 or medium > 0:
            parts.append(f"Alert attivi [stato corrente]: {high} critici, {medium} medi")
    except Exception:
        pass

    try:
        # Wave 13.3 — Health score, NOW scoped to the user's active
        # period rather than hardcoded to 30 days.
        if "cashflow_monitor" in active_modules:
            from modules.cashflow_monitor.cashflow_summary import build_ai_summary

            # Resolve which window to compute the snapshot on. Priority:
            #   1. period_context with explicit start+end → use them
            #      (frontend's pre-resolved YTD / MTD / custom).
            #   2. period_context with only a label (7d/30d/90d) → token.
            #   3. No period_context (e.g. user opened /ai standalone) →
            #      fall back to 30d but TAG IT as a default snapshot so
            #      the model sees it's not the user's active filter.
            pc_label = (period_context or {}).get("label")
            pc_start = (period_context or {}).get("start")
            pc_end = (period_context or {}).get("end")

            if pc_start and pc_end:
                # Pass token + dates: token wins as label, dates win as
                # math. The audit trail (Wave 13.2) records both.
                cs = await build_ai_summary(
                    org_id,
                    period=pc_label or "custom",
                    start_date=pc_start,
                    end_date=pc_end,
                    locale=locale,
                )
                period_tag = f"{pc_label or 'custom'} {pc_start}→{pc_end}"
            elif pc_label and pc_label in ("7d", "30d", "90d"):
                cs = await build_ai_summary(
                    org_id, period=pc_label, locale=locale,
                )
                period_tag = pc_label
            else:
                # No usable period context. Fall back to 30d but be
                # EXPLICIT about it so the model sees this is a default
                # snapshot, not the user's filter.
                cs = await build_ai_summary(
                    org_id, period="30d", locale=locale,
                )
                period_tag = "ultimi 30gg (default — l'utente non ha un filtro attivo)"

            # Wave 14.HOTFIX (2026-05-16) — explicit has_data + score
            # null check. Pre-fix, if ``build_ai_summary`` returned
            # ``{"has_data": False, "health_score": None, ...}`` (which
            # happens when the requested period contains insufficient
            # sales/expense records), the line `hs = cs.get(...)` could
            # legitimately produce hs=None, then ``hs.get("score")`` was
            # never reached due to the guard — but the proactive STILL
            # emitted nothing, AND there was zero signal to the model
            # explaining why. The model then hallucinated a plausible
            # health score from prior context. Now we EMIT an explicit
            # "insufficient data" line so the model SEES the absence
            # and does not improvise.
            if not (cs or {}).get("has_data", False):
                parts.append(
                    f"Health score [periodo: {period_tag}]: dati insufficienti "
                    f"per il periodo richiesto (il tool query_cashflow_summary "
                    f"con la stessa finestra restituisce has_data=False). "
                    f"NON inventare un numero — se l'utente chiede l'health, "
                    f"rispondi che servono più transazioni nel periodo."
                )
            else:
                hs = cs.get("health_score") or {}
                if hs.get("score") is not None:
                    parts.append(
                        f"Health score [periodo: {period_tag}]: "
                        f"{hs['score']}/100 "
                        f"({(cs.get('status') or {}).get('level', '?')})"
                    )
    except Exception as _hs_exc:
        # Wave 14.HOTFIX — log instead of silent pass so prod log analysis
        # can spot proactive failures (was the source of the smart_brief
        # latent crash being invisible for months).
        logger.warning(
            "_build_proactive_context: health snapshot failed: %s", _hs_exc,
        )

    try:
        # Churn risk — all-time materialised metric (customer_metrics
        # collection), NOT period-scoped. Tagged accordingly.
        if "customers_light" in active_modules:
            from database import customer_metrics_collection
            churn_high = await customer_metrics_collection.count_documents(
                {"organization_id": org_id, "churn_risk_score": {"$gte": 60}})
            if churn_high > 0:
                parts.append(
                    f"Clienti a rischio churn [snapshot all-time]: {churn_high}"
                )
    except Exception:
        pass

    try:
        # Draft orders (commerce) — current-state count.
        from database import orders_collection
        drafts = await orders_collection.count_documents(
            {"organization_id": org_id, "status": "draft"})
        if drafts > 0:
            parts.append(f"Ordini in bozza [stato corrente]: {drafts}")
    except Exception:
        pass

    if not parts:
        return ""

    # Wave 1.9 (2026-05) — removed a dead branch that built `context`
    # with broken f-string formatting (parts[1:] + parts[0] sequence),
    # only to be immediately overwritten by the "Clean up formatting"
    # block below. Two formulations of the same string with the second
    # winning, no logic change.
    #
    # Wave 13.3 — added the discipline rule about period-scoped snapshots
    # so the model never quotes a bracketed value as the answer to a
    # question about a DIFFERENT period.
    module_names = [m.replace("_", " ").title() for m in sorted(active_modules)]
    lines = [f"- {p}" for p in parts]
    context = (
        f"PROACTIVE CONTEXT (modules: {', '.join(module_names)}):\n"
        + "\n".join(lines) + "\n"
        "These are point-in-time snapshots, each tagged with its scope in brackets. "
        "If the user asks about a DIFFERENT period than the one tagged on a metric, "
        "you MUST call the appropriate tool with the requested period — do NOT "
        "cite these snapshot numbers as if they applied to that other period. "
        "If the user asks a generic question, proactively offer the most relevant observations. "
        "Do NOT mention modules that are not active."
    )
    return context
