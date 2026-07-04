"""AI Chat router — session management + messaging endpoints."""
import logging
import uuid
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Request, Depends, Query, status
from pydantic import BaseModel, Field
from auth import get_current_user, get_verified_user, get_verified_user
from routers.auth import limiter
from repositories import organization_repository
from repositories import usage_repository
from repositories import chat_session_repository
from services.module_access import check_module_access, build_module_access_status

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/ai", tags=["AI Chat"])


# ── Request / Response models ──────────────────────────────────────────────

class PeriodContext(BaseModel):
    label: Optional[str] = None
    start: Optional[str] = None
    end: Optional[str] = None


class ChatRequest(BaseModel):
    # Wave 10.A.7 — per-message cap. _MAX_HISTORY_CHARS (100k) is the
    # cumulative session cap; a single message is bounded at 10k chars
    # to stop one user from saturating the worker via a 5MB paste in
    # one POST. Together they bound both per-call cost and worker memory.
    message: str = Field(..., min_length=1, max_length=10_000)
    session_id: str = Field(..., max_length=100)
    period_context: Optional[PeriodContext] = None


class ChatResponse(BaseModel):
    reply: str
    session_id: str


class ChatHistoryMessage(BaseModel):
    role: str
    content: str


class ChatHistoryResponse(BaseModel):
    session_id: str
    messages: List[ChatHistoryMessage]


class SessionInfo(BaseModel):
    session_id: str
    title: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class RenameRequest(BaseModel):
    title: str


# Wave 5.5 (2026-05) — feedback channel
class FeedbackRequest(BaseModel):
    """User feedback on a specific chat reply.

    rating: 1 (thumbs down) or 5 (thumbs up). Other values rejected
    at the validator level so we get clean signal not free-form
    1-5 noise.

    reason: optional short text the user can leave to explain
    why they disliked / liked the answer. Capped to 500 chars.
    """
    session_id: str
    message_index: int  # 0-based position in the session's messages array
    rating: int  # 1 or 5
    reason: Optional[str] = None


# ── Access status ──────────────────────────────────────────────────────────

@router.get("/access-status")
async def ai_access_status(
    current_user: dict = Depends(get_verified_user),
):
    """Return AI entitlements, limits, and current usage for the caller's org."""
    org_doc = await organization_repository.find_by_id(
        current_user["organization_id"]
    )
    if not org_doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found",
        )
    result = await build_module_access_status(org_doc["id"], "ai_assistant", org_doc=org_doc)
    # Remap "enabled" → "ai_enabled" to preserve frontend contract (useAiAccess hook)
    result["ai_enabled"] = result.pop("enabled")
    return result


# ── Session management ─────────────────────────────────────────────────────

@router.get("/chat/sessions")
async def list_sessions(
    current_user: dict = Depends(get_verified_user),
):
    """List chat sessions for the current user (metadata only)."""
    sessions = await chat_session_repository.list_sessions(
        current_user["organization_id"],
        current_user["user_id"],
    )
    result = []
    for s in sessions:
        result.append({
            "session_id": s["session_id"],
            "title": s.get("title"),
            "created_at": s["created_at"].isoformat() if s.get("created_at") else None,
            "updated_at": s["updated_at"].isoformat() if s.get("updated_at") else None,
        })
    return result


@router.post("/chat/sessions")
async def create_session(
    current_user: dict = Depends(get_verified_user),
):
    """Create a new empty chat session. Returns the session_id."""
    session_id = str(uuid.uuid4())
    return {"session_id": session_id}


@router.delete("/chat/sessions/{session_id}")
async def delete_session(
    session_id: str,
    current_user: dict = Depends(get_verified_user),
):
    """Delete a chat session (user_id isolation enforced)."""
    deleted = await chat_session_repository.delete_session(
        current_user["organization_id"],
        current_user["user_id"],
        session_id,
    )
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found",
        )
    return {"ok": True}


@router.patch("/chat/sessions/{session_id}/title")
async def rename_session(
    session_id: str,
    body: RenameRequest,
    current_user: dict = Depends(get_verified_user),
):
    """Rename a chat session's title (user-scoped — Wave 1.5)."""
    title = body.title.strip()[:100]
    if not title:
        raise HTTPException(status_code=400, detail="Title cannot be empty")
    # Wave 1.5: pass user_id so a user can't rename another user's
    # session just by knowing the session_id.
    updated = await chat_session_repository.update_title(
        current_user["organization_id"],
        session_id,
        title,
        user_id=current_user.get("user_id") or current_user.get("id"),
    )
    if not updated:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found",
        )
    return {"ok": True, "title": title}


# ── Chat history & messaging ──────────────────────────────────────────────

@router.get("/chat/history", response_model=ChatHistoryResponse)
async def ai_chat_history(
    session_id: str = Query(..., description="Session ID to retrieve history for"),
    current_user: dict = Depends(get_verified_user),
):
    """Retrieve conversation history for a given session (user-scoped — Wave 1.5).

    Only returns user/assistant text messages (tool_use exchanges are stripped).
    """
    org_id = current_user["organization_id"]
    # Wave 1.5: pass user_id so a user can't read another user's chat
    # history by passing their session_id back. Cross-tenant was already
    # safe via org_id; this closes the intra-tenant gap.
    session_doc = await chat_session_repository.find_session(
        org_id, session_id,
        user_id=current_user.get("user_id") or current_user.get("id"),
    )

    if not session_doc:
        return ChatHistoryResponse(session_id=session_id, messages=[])

    # Extract only user/assistant text messages — skip tool_use/tool_result pairs
    display_messages = []
    for msg in session_doc.get("messages", []):
        role = msg.get("role")
        content = msg.get("content")
        if role not in ("user", "assistant"):
            continue
        # Skip tool-use content blocks (content is a list of dicts, not plain text)
        if isinstance(content, list):
            # Extract only text blocks from assistant responses
            texts = [b["text"] for b in content if isinstance(b, dict) and b.get("type") == "text" and b.get("text")]
            if texts and role == "assistant":
                display_messages.append({"role": role, "content": " ".join(texts)})
            continue
        if isinstance(content, str) and content.strip():
            display_messages.append({"role": role, "content": content})

    return ChatHistoryResponse(session_id=session_id, messages=display_messages)


# ── Wave 5.3 (2026-05): prompt injection guard ─────────────────────────────
# Defence in depth: detect obvious prompt-injection patterns and soft-block
# them at the router before they reach the LLM. Cannot prevent ALL such
# attacks (model robustness is the actual line of defence), but it makes
# the simplest attempts visible in logs + Sentry so we spot patterns.
#
# Soft block = return 400 with a clear message; the merchant can rephrase.
# We use SOFT block (not silent strip) so legitimate questions that
# happen to contain a suspicious phrase get a chance to clarify.

import re as _re

_INJECTION_PATTERNS = [
    # Common prompt-extraction attempts
    _re.compile(r"ignore\s+(all\s+)?(previous|prior)\s+(instructions?|system)", _re.IGNORECASE),
    _re.compile(r"disregard\s+(the\s+)?(above|previous|prior|system)", _re.IGNORECASE),
    _re.compile(r"show\s+(me\s+)?(your\s+)?(system|hidden|internal)\s+prompt", _re.IGNORECASE),
    _re.compile(r"reveal\s+(your\s+)?(system|hidden|internal)\s+(prompt|instructions?)", _re.IGNORECASE),
    _re.compile(r"what\s+(are|is)\s+your\s+(system\s+)?(instructions?|prompt)", _re.IGNORECASE),
    _re.compile(r"list\s+(all\s+)?(your\s+)?(tools?|functions?|capabilities)\s+(and\s+their\s+)?schemas?", _re.IGNORECASE),
    # Role override
    _re.compile(r"you\s+are\s+now\s+(a\s+)?(?:different|new|jailbreak)", _re.IGNORECASE),
    _re.compile(r"act\s+as\s+(if\s+you\s+were\s+)?(?:DAN|jailbreak|developer\s+mode)", _re.IGNORECASE),
]


def _detect_injection(message: str) -> str | None:
    """Return the matched pattern (as string) when injection is detected,
    or None when the message looks legitimate. Used for logging in
    addition to the boolean gate."""
    if not message:
        return None
    for pat in _INJECTION_PATTERNS:
        m = pat.search(message)
        if m:
            return m.group(0)
    return None


# ── Wave 3.5 (2026-05): per-user rate limit ─────────────────────────────────
# IP-based rate limiting (slowapi default) doesn't fit a B2B SaaS where
# multiple users sit behind one NAT. We add a (org_id, user_id) scope:
# at most LLM_PER_USER_MINUTE messages per user per minute, plus a
# daily token budget of LLM_PER_USER_DAILY_TOKENS. Both are env-
# configurable so the system admin can raise/lower without redeploy.
#
# Implementation: count documents in ai_usage_events_collection within
# a rolling window. Adds 1-2ms per chat call, far less than the
# Anthropic round-trip — acceptable cost for the abuse protection.

import os as _os
from datetime import datetime as _dt, timedelta as _td, timezone as _tz

_PER_USER_LIMIT_PER_MINUTE = int(_os.environ.get("LLM_PER_USER_MINUTE", "30"))
_PER_USER_DAILY_TOKEN_BUDGET = int(_os.environ.get("LLM_PER_USER_DAILY_TOKENS", "200000"))


async def _check_per_user_rate_limit(org_id: str, user_id: str, locale: str) -> None:
    """Enforce the per-(org,user) rate limit + daily token budget.

    Raises HTTPException(429) with a localised message when either
    cap is exceeded. Returns silently when within budget.

    Both windows are rolling (not aligned to wall-clock minute/day)
    so the user can't game the system by burst-sending at boundaries.
    """
    if not user_id:
        # No user_id (legacy call path) -> skip per-user limit. Wave
        # 1.3 wired user_id; future callers should always have it.
        return

    from database import ai_usage_events_collection

    now = _dt.now(_tz.utc)
    minute_ago = (now - _td(minutes=1)).isoformat()
    day_ago = (now - _td(hours=24)).isoformat()

    # Per-minute count — count distinct conversation_id (= user messages).
    # Wave 8A.2 splits an agentic chat into N round-trip events; without
    # this distinct count, a single user message firing 3 tool calls
    # would consume 3 slots of the per-minute window. We want users to
    # be rate-limited by what THEY did (send a message), not by what
    # the model did internally (call tools).
    minute_pipeline = [
        {"$match": {
            "organization_id": org_id,
            "user_id": user_id,
            "feature": "chat",
            "created_at": {"$gte": minute_ago},
        }},
        {"$group": {"_id": {"$ifNull": ["$conversation_id", "$id"]}}},
        {"$count": "total"},
    ]
    minute_agg = await ai_usage_events_collection.aggregate(
        minute_pipeline,
    ).to_list(1)
    minute_count = minute_agg[0]["total"] if minute_agg else 0

    if minute_count >= _PER_USER_LIMIT_PER_MINUTE:
        msgs = {
            "it": f"Hai superato il limite di {_PER_USER_LIMIT_PER_MINUTE} messaggi/minuto. Riprova tra poco.",
            "en": f"You exceeded the limit of {_PER_USER_LIMIT_PER_MINUTE} messages/minute. Please retry shortly.",
            "de": f"Sie haben das Limit von {_PER_USER_LIMIT_PER_MINUTE} Nachrichten/Minute überschritten.",
            "fr": f"Vous avez dépassé la limite de {_PER_USER_LIMIT_PER_MINUTE} messages/minute.",
        }
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=msgs.get(locale, msgs["it"]),
        )

    # Daily token budget (sums tokens_prompt + tokens_completion across last 24h)
    daily_pipeline = [
        {"$match": {
            "organization_id": org_id,
            "user_id": user_id,
            "feature": "chat",
            "created_at": {"$gte": day_ago},
        }},
        {"$group": {
            "_id": None,
            "total_tokens": {
                "$sum": {
                    "$add": [
                        {"$ifNull": ["$tokens_prompt", 0]},
                        {"$ifNull": ["$tokens_completion", 0]},
                    ]
                }
            },
        }},
    ]
    agg = await ai_usage_events_collection.aggregate(daily_pipeline).to_list(1)
    daily_tokens = agg[0]["total_tokens"] if agg else 0

    if daily_tokens >= _PER_USER_DAILY_TOKEN_BUDGET:
        msgs = {
            "it": (
                "Hai esaurito il budget AI giornaliero "
                f"({_PER_USER_DAILY_TOKEN_BUDGET:,} token). Il limite si "
                "azzera automaticamente."
            ).replace(",", "."),
            "en": (
                f"You exhausted the daily AI budget ({_PER_USER_DAILY_TOKEN_BUDGET:,} tokens). "
                "It resets automatically."
            ),
            "de": (
                f"Sie haben das tägliche KI-Budget ({_PER_USER_DAILY_TOKEN_BUDGET:,} Token) erschöpft."
            ),
            "fr": (
                f"Vous avez épuisé le budget IA quotidien ({_PER_USER_DAILY_TOKEN_BUDGET:,} jetons)."
            ),
        }
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=msgs.get(locale, msgs["it"]),
        )


@router.post("/chat", response_model=ChatResponse)
@limiter.limit("60/minute")  # Wave 3.5: bumped IP limit; real cap is per-user below
async def ai_chat(
    request: Request,
    body: ChatRequest,
    current_user: dict = Depends(get_verified_user),
):
    """Send a message to the AI financial advisor."""
    # ── Quota gating (403 / 429) ────────────────────────────────────────────
    org_doc = await organization_repository.find_by_id(current_user["organization_id"])
    if not org_doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organization not found")
    await check_module_access(org_doc["id"], "ai_assistant", "chat", org_doc=org_doc)

    # Wave 3.5: per-user rate limit (sliding minute + daily token budget)
    user_id_ = current_user.get("user_id") or current_user.get("id") or ""
    locale_ = (current_user.get("locale") or "it").lower()
    await _check_per_user_rate_limit(org_doc["id"], user_id_, locale_)

    # Wave 5.3: prompt injection soft-block
    injection_match = _detect_injection(body.message)
    if injection_match:
        logger.warning(
            "ai_chat: prompt injection pattern blocked (org=%s user=%s pattern=%r)",
            current_user["organization_id"], user_id_, injection_match,
        )
        msgs = {
            "it": "La tua domanda contiene istruzioni di sistema che non posso elaborare. Riformulala come domanda sui tuoi dati di business.",
            "en": "Your message contains system instructions I can't process. Please rephrase as a question about your business data.",
            "de": "Ihre Nachricht enthält Systemanweisungen, die ich nicht verarbeiten kann. Bitte formulieren Sie sie als Frage zu Ihren Geschäftsdaten.",
            "fr": "Votre message contient des instructions système que je ne peux pas traiter. Reformulez en question sur vos données.",
        }
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=msgs.get(locale_, msgs["it"]),
        )

    from services.chat_service import chat
    from services.claude_client import ClaudeUnavailableError

    try:
        # Build period context dict for system prompt grounding
        period_ctx = None
        if body.period_context:
            period_ctx = body.period_context.model_dump(exclude_none=True) or None

        # Wave 13.2 — log the raw period_context received from the
        # frontend. This is the canonical entry point for forensic
        # period reconstruction: ("user said X, frontend sent Y, we
        # resolved to Z"). The chat service layer logs the resolved
        # form; here we log what came in over the wire.
        logger.info(
            "ai_chat: org=%s user=%s session=%s period_context=%r",
            current_user.get("organization_id"),
            current_user.get("user_id"),
            body.session_id,
            period_ctx,
        )

        reply = await chat(
            org_id=current_user["organization_id"],
            session_id=body.session_id,
            user_message=body.message,
            locale=current_user.get("locale", "it"),
            user_id=current_user.get("user_id", ""),
            period_context=period_ctx,
            # No agent_id -> defaults to financial_analyst (Wave 4)
        )
        # Usage tracking (with token counts) is handled inside chat_service.chat()
        return ChatResponse(reply=reply, session_id=body.session_id)
    except Exception as gov_exc:
        # Wave 8B — governance refusal (kill switch / budget / throttle).
        # Caught BEFORE the generic ClaudeUnavailableError handler since
        # GovernanceError is its own family. Translates to HTTP 429/503
        # with a stable error_code in the response body so the frontend
        # can render the right banner.
        from services.llm.budget_guard import (
            GovernanceError, AIDisabledError, AIThrottledError, BudgetExceededError,
        )
        if not isinstance(gov_exc, GovernanceError):
            raise  # re-raise to fall into the existing handlers below

        locale = (current_user.get("locale") or "it").lower()
        if isinstance(gov_exc, BudgetExceededError):
            messages = {
                "it": "Budget AI esaurito per questo periodo. Contatta l'amministratore.",
                "en": "AI budget exhausted for this period. Contact your administrator.",
                "de": "KI-Budget für diesen Zeitraum erschöpft. Kontaktieren Sie Ihren Administrator.",
                "fr": "Budget IA épuisé pour cette période. Contactez votre administrateur.",
            }
        elif isinstance(gov_exc, AIDisabledError):
            messages = {
                "it": "Le funzioni AI sono temporaneamente disabilitate dall'amministratore di sistema.",
                "en": "AI features are temporarily disabled by the system administrator.",
                "de": "KI-Funktionen sind vom Systemadministrator vorübergehend deaktiviert.",
                "fr": "Les fonctionnalités IA sont temporairement désactivées par l'administrateur système.",
            }
        else:  # AIThrottledError or generic GovernanceError
            messages = {
                "it": "Servizio AI sotto carico. Riprova tra qualche istante.",
                "en": "AI service under load. Please retry shortly.",
                "de": "KI-Dienst unter Last. Bitte versuchen Sie es bald erneut.",
                "fr": "Service IA sous charge. Réessayez bientôt.",
            }
        raise HTTPException(
            status_code=gov_exc.http_status,
            detail={
                "error_code": gov_exc.error_code,
                "message": messages.get(locale, messages["it"]),
                "context": gov_exc.context,
            },
        )
    except ClaudeUnavailableError as e:
        # Wave 3.8 (2026-05): localised error UX.
        #
        # The 503 used to surface the raw exception message ("Anthropic
        # API error: <stack>") — useless to the merchant. We now classify
        # by exception subtype and emit a human Italian message.
        # CircuitOpenError is a subclass of LLMUnavailableError; we
        # detect it by name to avoid an import cycle.
        exc_cls_name = type(e).__name__
        locale = (current_user.get("locale") or "it").lower()
        if exc_cls_name == "CircuitOpenError":
            messages = {
                "it": "Il servizio AI sta avendo problemi temporanei. Riprova tra qualche secondo.",
                "en": "The AI service is experiencing temporary issues. Please try again in a few seconds.",
                "de": "Der KI-Dienst hat vorübergehende Probleme. Bitte versuchen Sie es in wenigen Sekunden erneut.",
                "fr": "Le service IA rencontre des problèmes temporaires. Réessayez dans quelques secondes.",
            }
        else:
            messages = {
                "it": "Servizio AI non disponibile al momento. Riprova tra qualche istante.",
                "en": "AI service unavailable. Please retry shortly.",
                "de": "KI-Dienst nicht verfügbar. Bitte versuchen Sie es bald erneut.",
                "fr": "Service IA indisponible. Réessayez bientôt.",
            }
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=messages.get(locale, messages["it"]),
        )
    except Exception as e:
        logger.error("ai_chat error: %s", e, exc_info=True)
        locale = (current_user.get("locale") or "it").lower()
        fallback = {
            "it": "Errore nel servizio di chat AI. Prova a riformulare la domanda.",
            "en": "AI chat service error. Try rephrasing your question.",
            "de": "Fehler im KI-Chat-Dienst. Versuchen Sie, Ihre Frage neu zu formulieren.",
            "fr": "Erreur dans le service de chat IA. Essayez de reformuler.",
        }
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=fallback.get(locale, fallback["it"]),
        )


# Wave 3.4 streaming endpoint (POST /chat/stream) REMOVED in Wave 9.A.
# It bypassed every Wave 8 governance layer: no record_usage(), no
# budget pre-flight check, no kill switch coverage, no
# conversation_id. The frontend never adopted it (grep "EventSource"
# / "/chat/stream" in frontend/src returns zero hits), so it was a
# dormant attack surface — anyone with a valid JWT could consume
# Anthropic illimitatamente via curl and the dashboard would see
# nothing. Removed entirely; if streaming is needed again later it
# MUST go through the same path (record_usage + budget check + kill
# switch).


# ─────────────────────────────────────────────────────────────────────────────
# Wave 4 (2026-05) — multi-agent endpoints
#
# /ai/agents               GET — list agents available for the org
# /ai/agents/{id}/chat     POST — chat scoped to a specific agent
#
# /ai/chat (existing) routes to the default agent (financial_analyst)
# for backward compatibility. The frontend can migrate gradually.
# ─────────────────────────────────────────────────────────────────────────────


# ── Wave 5.5 (2026-05) — feedback endpoint ──────────────────────────────────


@router.post(
    "/chat/feedback",
    summary="Submit feedback (thumbs up/down) on an AI reply — Wave 5.5",
)
@limiter.limit("30/minute")
async def submit_feedback(
    request: Request,
    body: FeedbackRequest,
    current_user: dict = Depends(get_verified_user),
):
    """Persist a feedback rating + optional reason for a specific AI reply.

    Stored in ai_feedback_collection with (org_id, user_id, session_id,
    message_index, rating, reason, created_at). Used for:
      - Regression tests on agent behaviour (Wave 5.6 golden tests
        seed from real downvoted exchanges)
      - System admin dashboard "low-quality reply patterns"
      - Future: prompt tuning based on feedback

    Validation:
      - rating must be 1 or 5 (binary thumbs) — anything else is 400
      - reason is capped to 500 chars
      - session_id ownership is checked via find_session(user_id=...)
        so a user can only rate their own sessions
    """
    if body.rating not in (1, 5):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="rating must be 1 (thumbs down) or 5 (thumbs up)",
        )
    reason = (body.reason or "").strip()[:500] if body.reason else None

    # Verify the session belongs to this user (uses Wave 1.5 isolation)
    user_id_ = current_user.get("user_id") or current_user.get("id") or ""
    session_doc = await chat_session_repository.find_session(
        current_user["organization_id"], body.session_id, user_id=user_id_,
    )
    if not session_doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found",
        )

    # Persist into a dedicated collection
    from database import db as _db
    from datetime import datetime, timezone
    feedback_coll = _db.ai_feedback
    doc = {
        "id": str(uuid.uuid4()),
        "organization_id": current_user["organization_id"],
        "user_id": user_id_,
        "session_id": body.session_id,
        "message_index": body.message_index,
        "rating": body.rating,
        "reason": reason,
        "created_at": datetime.now(timezone.utc),
    }
    await feedback_coll.insert_one(doc)
    return {"ok": True, "feedback_id": doc["id"]}


@router.get(
    "/agents",
    summary="List AI agents available to the caller's org — Wave 4",
)
async def list_org_agents(
    current_user: dict = Depends(get_verified_user),
):
    """Return the AgentDefinitions whose module dependencies are
    satisfied for this org. Used by the frontend agent picker.
    """
    from services.agents import list_agents_for_org
    agents = await list_agents_for_org(current_user["organization_id"])
    return {
        "agents": [
            {
                "agent_id": a.agent_id,
                "name": a.name,
                "description": a.description,
                "tool_scopes": a.tool_scopes,
            }
            for a in agents
        ],
    }


@router.post(
    "/agents/{agent_id}/chat",
    response_model=ChatResponse,
    summary="Send a message to a specific AI agent — Wave 4",
)
@limiter.limit("60/minute")
async def ai_chat_agent(
    agent_id: str,
    request: Request,
    body: ChatRequest,
    current_user: dict = Depends(get_verified_user),
):
    """Per-agent chat endpoint. Same contract as /ai/chat but routes
    the call through the named agent's persona + tool scope.

    When the agent_id is unknown or its module_dependencies aren't
    satisfied for this org, returns 404. The chat_service falls back
    to default_agent when given an unknown id, but here at the
    endpoint we want a hard error so the frontend can surface the
    misconfiguration.
    """
    from services.agents import get_agent, AgentNotFoundError

    try:
        agent_def = get_agent(agent_id)
    except AgentNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Unknown agent '{agent_id}'.",
        )

    # Org gate check (same as /chat)
    org_doc = await organization_repository.find_by_id(current_user["organization_id"])
    if not org_doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organization not found")
    await check_module_access(org_doc["id"], "ai_assistant", "chat", org_doc=org_doc)

    # Check the agent's module_dependencies are satisfied for this org
    from services.module_access import get_module_entitlements
    for dep in agent_def.module_dependencies:
        ent = await get_module_entitlements(org_doc["id"], dep)
        if not ent.get("enabled"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=(
                    f"Agent '{agent_id}' requires module '{dep}' which "
                    f"is not active for this organization."
                ),
            )

    user_id_ = current_user.get("user_id") or current_user.get("id") or ""
    locale_ = (current_user.get("locale") or "it").lower()
    await _check_per_user_rate_limit(org_doc["id"], user_id_, locale_)

    from services.chat_service import chat
    from services.claude_client import ClaudeUnavailableError

    try:
        period_ctx = None
        if body.period_context:
            period_ctx = body.period_context.model_dump(exclude_none=True) or None

        # Wave 13.2 — log period context received over the wire. See
        # ai_chat() for the rationale.
        logger.info(
            "ai_chat_agent: org=%s user=%s session=%s agent=%s period_context=%r",
            current_user.get("organization_id"),
            user_id_,
            body.session_id,
            agent_def.agent_id,
            period_ctx,
        )

        reply = await chat(
            org_id=current_user["organization_id"],
            session_id=body.session_id,
            user_message=body.message,
            locale=locale_,
            user_id=user_id_,
            period_context=period_ctx,
            agent_id=agent_def.agent_id,
        )
        return ChatResponse(reply=reply, session_id=body.session_id)
    except ClaudeUnavailableError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(e),
        )
    except Exception as e:
        logger.error("ai_chat_agent[%s] error: %s", agent_id, e, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Errore nel servizio di chat AI. Prova a riformulare.",
        )


# POST /ai/chat/stream — REMOVED in Wave 9.A (see comment block at line ~501).
# If streaming is needed again it MUST go through chat_service.chat() so it
# inherits record_usage + budget guard + kill switch + conversation_id.
