"""
AI module E2E smoke test — Wave-based consolidation harness.

Same idea as scripts/smoke_pillar2_e2e.py for alerts: seed small
realistic orgs, exercise the chat AI pipeline end-to-end against the
live Anthropic API (only when SMOKE_SEND=1), assert expected
behaviour, clean up.

Each wave populates its own block of scenarios. The harness is
designed so a wave-block can be run in isolation while the others
are skipped (env var SMOKE_WAVE=1 / 2 / 3 / "all").

Scenarios per wave
------------------
  Wave 1 — Foundation & Observability (CURRENT)
    [W1.A] Multi-currency: CHF org -> chat response uses CHF, not EUR
    [W1.B] Multi-locale:  English user -> chat replies in English
    [W1.C] AIUsageEvent: latest event after chat has tokens populated
           AND backward-compat fields exist (user_id may be None until
           Wave 1.3 wires it — that surfaces the missing wiring)
    [W1.D] Session isolation: Mario cannot read Anna's session (Wave 1.5)

  Wave 2 — Provider Abstraction
    [W2.A] LLMProvider interface honoured by AnthropicProvider
    [W2.B] All 9 callers work via the shim
    [W2.C] Switching LLM_PROVIDER would route correctly

  Wave 3 — Reliability & Performance
    [W3.A] 30 concurrent chats: zero 503 user-facing
    [W3.B] Streaming: first chunk <1.5s
    [W3.C] Cache hit: same query 2x = cost halved
    [W3.D] Circuit breaker opens after 5x 529

  Wave 4 — Multi-agent
    [W4.A] Default endpoint = behaviour 1:1 pre-refactor (golden)
    [W4.B] /agents/financial_analyst/chat = same as /chat (alias)
    [W4.C] Adding stub agent_hr = zero modifications elsewhere
    [W4.D] prompt_version persisted in AIUsageEvent

  Wave 5 — Hardening
    [W5.A] Tool result never contains raw customer_name to Anthropic
    [W5.B] Prompt injection patterns soft-blocked
    [W5.C] /healthz/ai returns 200 when Anthropic reachable
    [W5.D] Feedback endpoint persists rating

Usage
-----
    cd backend
    set -a; source .env; set +a

    # Dry-run (no Anthropic calls; only wiring + DB checks):
    ./venv/bin/python -m scripts.smoke_ai_e2e

    # Real LLM calls (USES ANTHROPIC CREDITS):
    SMOKE_SEND=1 ./venv/bin/python -m scripts.smoke_ai_e2e

    # Specific wave:
    SMOKE_WAVE=1 ./venv/bin/python -m scripts.smoke_ai_e2e

    # Keep seeded data for manual inspection (don't wipe at end):
    SMOKE_KEEP=1 ./venv/bin/python -m scripts.smoke_ai_e2e

Idempotent
----------
All seeded docs tagged metadata.smoke_seed = "smoke_ai_v1".
Re-running wipes only tagged docs.
"""
from __future__ import annotations

import asyncio
import os
import sys
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

_BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_BACKEND_DIR))

# ── Module registry side-effect imports ─────────────────────────────────────
# AFianco's modules register themselves via side-effect when imported
# (modules/<name>/__init__.py calls register_module(...)). In server.py
# this happens implicitly through the import chain; for a standalone
# script we must import them explicitly, otherwise get_tools_for_chat
# returns an empty active_modules set and the smoke can't exercise the
# dispatcher properly.
import modules.cashflow_monitor  # noqa: F401
import modules.customer_insights  # noqa: F401
# commerce_signals module removed in Wave 7A (2026-05).
import modules.product_catalog  # noqa: F401
# Wave 7B.1: commerce module gained an AI tool surface (6 tools moved
# from cashflow_monitor). Must be imported explicitly here so the
# registry picks it up under SMOKE_SEND=1.
import modules.commerce  # noqa: F401


# ── Stable identifiers ──────────────────────────────────────────────────────
# Three orgs, one per scenario:
#   ORG_CHF_IT — Swiss bakery, currency CHF, locale it
#   ORG_EUR_EN — Italian SMB but admin set English locale + EUR currency
#   ORG_ISOL   — used for session isolation tests (Mario vs Anna intra-org)

ORG_CHF_IT = "smoke-ai-chf-it-00000000000000001"
ORG_EUR_EN = "smoke-ai-eur-en-00000000000000001"
ORG_ISOL   = "smoke-ai-isol-00000000000000000001"
SEED_TAG = "smoke_ai_v1"

USER_ADMIN_CHF_IT = "smoke-ai-admin-chf-it-00000000001"
USER_ADMIN_EUR_EN = "smoke-ai-admin-eur-en-00000000001"
USER_MARIO = "smoke-ai-mario-0000000000000000001"
USER_ANNA  = "smoke-ai-anna-00000000000000000001"

ADMIN_EMAIL_BASE = os.environ.get("BACKUP_ALERT_EMAIL", "davidedefilippis94@gmail.com")
_local, _domain = ADMIN_EMAIL_BASE.split("@", 1)
EMAIL_CHF_IT = f"{_local}+ai-smoke-chf@{_domain}"
EMAIL_EUR_EN = f"{_local}+ai-smoke-en@{_domain}"
EMAIL_MARIO  = f"{_local}+ai-smoke-mario@{_domain}"
EMAIL_ANNA   = f"{_local}+ai-smoke-anna@{_domain}"

# Whether to actually hit Anthropic (costs credits!)
SEND_REAL = os.environ.get("SMOKE_SEND", "0") == "1"
KEEP_DATA = os.environ.get("SMOKE_KEEP", "0") == "1"


# ─────────────────────────────────────────────────────────────────────────────
# Cleanup
# ─────────────────────────────────────────────────────────────────────────────

async def _wipe(org_ids: list[str]):
    """Remove every smoke-tagged document for the given orgs."""
    from database import (
        organizations_collection, users_collection,
        organization_modules_collection, datasets_collection,
        sales_records_collection, ai_usage_events_collection,
        chat_sessions_collection, module_configs_collection,
    )
    counts = {}
    for org in org_ids:
        for name, coll in [
            ("organizations", organizations_collection),
            ("users", users_collection),
            ("module_configs", module_configs_collection),
            ("org_modules", organization_modules_collection),
            ("datasets", datasets_collection),
            ("sales_records", sales_records_collection),
            ("ai_usage_events", ai_usage_events_collection),
            ("chat_sessions", chat_sessions_collection),
        ]:
            r = await coll.delete_many({"organization_id": org})
            counts[name] = counts.get(name, 0) + r.deleted_count
    return counts


# ─────────────────────────────────────────────────────────────────────────────
# Seed helpers
# ─────────────────────────────────────────────────────────────────────────────

async def _seed_org_with_user(
    org_id: str,
    org_name: str,
    currency: str,
    user_id: str,
    user_email: str,
    user_locale: str,
    role: str = "admin",
    enable_ai: bool = True,
):
    """Create an org + one user + (optional) ai_assistant module enabled."""
    from database import (
        organizations_collection, users_collection,
        organization_modules_collection, module_configs_collection,
    )
    from passlib.context import CryptContext

    pwd = CryptContext(schemes=["bcrypt"], deprecated="auto").hash("smoke-ai-throwaway")
    now = datetime.now(timezone.utc)

    await organizations_collection.insert_one({
        "id": org_id,
        "name": org_name,
        "slug": org_id.replace("smoke-ai-", "").replace("000000000000000", "")[:30],
        "industry": "Food & Beverage",
        "subscription_plan": "enterprise",
        "currency": currency,
        "locale": user_locale,
        "created_at": now,
        "updated_at": now,
        "is_active": True,
        "smoke_seed": SEED_TAG,
    })
    await users_collection.insert_one({
        "id": user_id,
        "email": user_email,
        "name": f"Smoke user {user_id[-4:]}",
        "role": role,
        "organization_id": org_id,
        "password_hash": pwd,
        "created_at": now,
        "updated_at": now,
        "is_active": True,
        "is_verified": True,
        "locale": user_locale,
        "smoke_seed": SEED_TAG,
    })
    if enable_ai:
        await organization_modules_collection.insert_one({
            "organization_id": org_id,
            "module_key": "ai_assistant",
            "enabled": True,
            "enabled_at": now,
            "smoke_seed": SEED_TAG,
        })
        await organization_modules_collection.insert_one({
            "organization_id": org_id,
            "module_key": "cashflow_monitor",
            "enabled": True,
            "enabled_at": now,
            "smoke_seed": SEED_TAG,
        })


async def _seed_simple_sales(org_id: str, total_amount: float, n_records: int = 10):
    """Seed n_records sales evenly summing to total_amount in the last 30d."""
    from database import sales_records_collection, datasets_collection

    dataset_id = f"smoke-ds-{org_id[-8:]}"
    now = datetime.now(timezone.utc)
    await datasets_collection.insert_one({
        "id": dataset_id, "organization_id": org_id,
        "name": "Smoke AI sales", "source": "smoke_seed",
        "created_at": now, "smoke_seed": SEED_TAG,
    })

    today = now.date()
    each = total_amount / n_records
    records = [{
        "id": str(uuid.uuid4()),
        "organization_id": org_id,
        "dataset_id": dataset_id,
        "date": (today - timedelta(days=2 + i * 2)).isoformat(),
        "amount": round(each, 2),
        "category": "Vendita banco",
        "source_label": SEED_TAG,
    } for i in range(n_records)]
    await sales_records_collection.insert_many(records)


# ─────────────────────────────────────────────────────────────────────────────
# Chat invocation (real Anthropic call gated by SMOKE_SEND=1)
# ─────────────────────────────────────────────────────────────────────────────

async def _ask_chat(
    org_id: str,
    user_id: str,
    user_message: str,
    locale: str,
) -> dict:
    """Hit the real chat pipeline. Returns dict with reply + usage event."""
    if not SEND_REAL:
        return {"reply": "(dry-run, no actual LLM call)", "usage_event": None}

    from services.chat_service import chat
    from database import ai_usage_events_collection

    session_id = str(uuid.uuid4())
    reply = await chat(
        org_id=org_id,
        session_id=session_id,
        user_message=user_message,
        locale=locale,
        user_id=user_id,
        period_context=None,
    )
    # Fetch the latest usage event for inspection
    cursor = ai_usage_events_collection.find(
        {"organization_id": org_id, "module_key": "ai_assistant"},
    ).sort("created_at", -1).limit(1)
    docs = await cursor.to_list(1)
    return {"reply": reply, "usage_event": docs[0] if docs else None}


# ─────────────────────────────────────────────────────────────────────────────
# Wave 1 scenarios
# ─────────────────────────────────────────────────────────────────────────────

async def run_wave_1():
    print("=" * 72)
    print("  Wave 1 — Foundation & Observability — smoke scenarios")
    print("=" * 72)
    print(f"  SMOKE_SEND     : {'YES (real Anthropic)' if SEND_REAL else 'NO (dry-run)'}")
    print(f"  SMOKE_KEEP     : {'YES (preserve data)' if KEEP_DATA else 'NO (wipe at end)'}")
    print()

    # ── Setup: wipe + seed 3 orgs ───────────────────────────────────────
    print("[setup] Wiping previous smoke data...")
    deleted = await _wipe([ORG_CHF_IT, ORG_EUR_EN, ORG_ISOL])
    non_zero = {k: v for k, v in deleted.items() if v > 0}
    if non_zero:
        print(f"    - deleted: {non_zero}")

    print("[setup] Seeding 3 orgs (CHF/it, EUR/en, isolation)...")
    await _seed_org_with_user(
        ORG_CHF_IT, "Pasticceria Lugano SA", currency="CHF",
        user_id=USER_ADMIN_CHF_IT, user_email=EMAIL_CHF_IT, user_locale="it",
    )
    await _seed_org_with_user(
        ORG_EUR_EN, "AFianco EN Bakery", currency="EUR",
        user_id=USER_ADMIN_EUR_EN, user_email=EMAIL_EUR_EN, user_locale="en",
    )
    # Isolation org has two users (Mario + Anna)
    await _seed_org_with_user(
        ORG_ISOL, "Isolation Test Org", currency="EUR",
        user_id=USER_MARIO, user_email=EMAIL_MARIO, user_locale="it",
    )
    # Add Anna manually (org already exists, just add the user)
    from database import users_collection
    pwd_hash = "$2b$12$dummy"
    await users_collection.insert_one({
        "id": USER_ANNA, "email": EMAIL_ANNA,
        "name": "Anna", "role": "admin",
        "organization_id": ORG_ISOL,
        "password_hash": pwd_hash, "is_active": True, "is_verified": True,
        "locale": "it", "smoke_seed": SEED_TAG,
    })

    print("[setup] Seeding sales data on CHF org (5000 CHF) + EUR org (5000 EUR)...")
    await _seed_simple_sales(ORG_CHF_IT, total_amount=5000.0, n_records=10)
    await _seed_simple_sales(ORG_EUR_EN, total_amount=5000.0, n_records=10)

    # ── W1.A: Currency injection at the dispatcher level (Wave 1.10) ────
    # Tests the DISPATCHER directly (not the agentic chat loop) so we
    # don't depend on the org having full entitlements seeded — which
    # is a separate concern from currency support.
    # The chat-level test would require a full subscription/entitlement
    # seed; we defer that to Wave 6 (launch verification) with a real
    # tier-2 org.
    print()
    print("─" * 72)
    print("[W1.A] Currency: dispatcher injects CHF for CHF-configured org")
    print("─" * 72)
    try:
        # Monkey-patch get_module_entitlements to enable all modules
        # for the smoke org (bypasses entitlement system which needs
        # subscription + commercial_plan seeded).
        from services import module_access
        _orig_entitlements = module_access.get_module_entitlements

        async def _bypass_entitlements(org_id, module_key, org_doc=None):
            return {"enabled": True, "read_only": False, "limits": {},
                    "plan_name": "smoke", "plan_slug": f"{module_key}_smoke"}

        module_access.get_module_entitlements = _bypass_entitlements
        try:
            from services.ai_tool_registry import get_tools_for_chat
            tools, dispatch, active = await get_tools_for_chat(ORG_CHF_IT)
            print(f"  → active modules with bypass: {sorted(active)}")
            print(f"  → tools available: {len(tools)}")

            # Test 1: cashflow tool — currency from build_unified_summary
            cf_result = await dispatch(
                ORG_CHF_IT, "query_business_summary", {"period": "30d"},
            )
            print(f"  → query_business_summary currency: {cf_result.get('currency')!r}")

            # Test 2: customer tool — currency injected by dispatcher wrapper
            ci_result = await dispatch(
                ORG_CHF_IT, "query_customer_summary", {"period": "30d"},
            )
            print(f"  → query_customer_summary currency: {ci_result.get('currency')!r}")

            # Assertions
            cf_ok = cf_result.get("currency") == "CHF"
            ci_ok = ci_result.get("currency") == "CHF"
            if cf_ok and ci_ok:
                print("  ✅ PASS: dispatcher returns CHF for both cashflow + "
                      "customer tools (Wave 1.10 fix verified)")
            else:
                print(f"  ❌ FAIL: cashflow={cf_ok} customer={ci_ok}")
        finally:
            module_access.get_module_entitlements = _orig_entitlements
    except Exception as e:
        print(f"  ⚠️  dispatcher test errored: {type(e).__name__}: {e}")

    # ── W1.B: Locale = en reflected in chat response ────────────────────
    print()
    print("─" * 72)
    print("[W1.B] Locale: English-locale user gets English reply")
    print("─" * 72)
    if SEND_REAL:
        result = await _ask_chat(
            ORG_EUR_EN, USER_ADMIN_EUR_EN,
            "What is my revenue for the last month?",
            locale="en",
        )
        reply = result["reply"]
        # Italian markers we should NOT see, English markers we should
        italian = sum(reply.lower().count(w) for w in ["fatturato", "scorso", "mese", "ricavi"])
        english = sum(reply.lower().count(w) for w in ["revenue", "month", "past", "sales"])
        print(f"  → reply (first 300 chars):")
        print(f"    {reply[:300]}")
        print()
        print(f"  → Italian markers: {italian}, English markers: {english}")
        if english > italian:
            print("  ✅ PASS: response is dominantly English")
        else:
            print("  ❌ FAIL: locale not honoured (Italian markers won)")
    else:
        print("  ⏭  skipped (set SMOKE_SEND=1 to actually call the LLM)")

    # ── W1.C: AIUsageEvent has Wave-1 fields populated ──────────────────
    # Note: until Wave 1.3 wires the callers, user_id will be None for new
    # events. This test surfaces the gap and starts passing fully when 1.3
    # lands. That's intentional.
    print()
    print("─" * 72)
    print("[W1.C] AIUsageEvent: Wave-1 fields readable, even if not yet wired")
    print("─" * 72)
    if SEND_REAL:
        from database import ai_usage_events_collection
        # The EUR/EN org is the one that actually fired a real chat in
        # W1.B (W1.A only tests the dispatcher directly). So we read
        # its event to verify Wave 1.3/1.4 wired correctly.
        latest = await ai_usage_events_collection.find_one(
            {"organization_id": ORG_EUR_EN, "module_key": "ai_assistant"},
            sort=[("created_at", -1)],
        )
        if not latest:
            print("  ⚠️  No AIUsageEvent found for CHF org — chat didn't record")
        else:
            print(f"  → event keys: {sorted(latest.keys())}")
            print(f"  → tokens_prompt={latest.get('tokens_prompt')} "
                  f"tokens_completion={latest.get('tokens_completion')}")
            print(f"  → user_id={latest.get('user_id')!r}")
            print(f"  → agent_id={latest.get('agent_id')!r}")
            print(f"  → provider={latest.get('provider')!r}")
            print(f"  → model_version={latest.get('model_version')!r}")
            print(f"  → cost_usd={latest.get('cost_usd')!r}")
            # Wave 1.1 + 1.2 should at LEAST have agent_id="financial_analyst"
            # and provider="anthropic" as defaults from the model.
            assert latest.get("agent_id") == "financial_analyst", (
                f"agent_id default broke — got {latest.get('agent_id')!r}"
            )
            assert latest.get("provider") == "anthropic", (
                f"provider default broke — got {latest.get('provider')!r}"
            )
            if latest.get("user_id") is None:
                print("  ℹ️  user_id None — expected until Wave 1.3 lands")
            else:
                print("  ✅ user_id populated — Wave 1.3 wiring confirmed")
            print("  ✅ PASS: defaults from model present, schema accepts Wave-1 fields")
    else:
        # Dry-run: just validate the schema accepts new fields
        from models.ai_usage import AIUsageEvent
        evt = AIUsageEvent(
            organization_id="test",
            feature="chat",
            user_id="test-user",
            cost_usd=0.01,
            model_version="claude-sonnet-4",
            prompt_version="v1",
        )
        assert evt.user_id == "test-user"
        assert evt.cost_usd == 0.01
        assert evt.agent_id == "financial_analyst"  # default
        assert evt.provider == "anthropic"  # default
        print("  ✅ PASS (dry-run): AIUsageEvent accepts all Wave-1 fields w/ defaults")

    # ── W1.D: Session isolation (Wave 1.5 will fix this) ────────────────
    # Sentinel test: TODAY this should DEMONSTRATE the bug. After Wave 1.5
    # the assertion flips to "must be 403 / None".
    print()
    print("─" * 72)
    print("[W1.D] Session isolation: Mario tries to read Anna's session")
    print("─" * 72)
    from repositories import chat_session_repository
    from database import chat_sessions_collection

    # Seed a session for Anna (manual, bypasses chat_service)
    anna_session_id = str(uuid.uuid4())
    await chat_sessions_collection.insert_one({
        "id": str(uuid.uuid4()),
        "organization_id": ORG_ISOL,
        "session_id": anna_session_id,
        "user_id": USER_ANNA,
        "messages": [
            {"role": "user", "content": "Private question by Anna"},
            {"role": "assistant", "content": "Private reply for Anna"},
        ],
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
        "smoke_seed": SEED_TAG,
    })

    # Simulate the real attack vector: Mario calls the chat API. The
    # backend's get_verified_user resolves his user_id (USER_MARIO) and
    # passes it to find_session along with Anna's session_id (which
    # Mario somehow learned). After Wave 1.5 this MUST return None.
    found_with_mario = await chat_session_repository.find_session(
        ORG_ISOL, anna_session_id, user_id=USER_MARIO,
    )
    if found_with_mario is None:
        print("  ✅ PASS: find_session(user_id=Mario) returns None — "
              "Wave 1.5 isolation working")
    else:
        print(f"  ❌ FAIL: Mario STILL sees Anna's session "
              f"(user_id={found_with_mario.get('user_id')!r}) — security regression!")

    # Sanity check: Anna with HER own user_id still finds it
    found_with_anna = await chat_session_repository.find_session(
        ORG_ISOL, anna_session_id, user_id=USER_ANNA,
    )
    if found_with_anna is not None and found_with_anna.get("user_id") == USER_ANNA:
        print("  ✅ PASS: Anna with her own user_id correctly finds her session "
              "(no false negative)")
    else:
        print("  ❌ FAIL: Anna lost access to her own session — too aggressive filter")

    # ── Cleanup ──────────────────────────────────────────────────────────
    print()
    if KEEP_DATA:
        print("[cleanup] SMOKE_KEEP=1 → preserving smoke data for manual inspection")
    else:
        print("[cleanup] Wiping smoke data...")
        await _wipe([ORG_CHF_IT, ORG_EUR_EN, ORG_ISOL])

    print()
    print("=" * 72)
    print("Wave 1 smoke complete.")
    print("=" * 72)


# ─────────────────────────────────────────────────────────────────────────────
# Dispatch
# ─────────────────────────────────────────────────────────────────────────────

async def main():
    wave = os.environ.get("SMOKE_WAVE", "1")
    if wave in ("0", "pre"):
        print("Wave 0 was pre-flight only (no scenarios). Use SMOKE_WAVE=1.")
        return
    if wave in ("1", "all"):
        await run_wave_1()
    if wave in ("2",):
        print("Wave 2 scenarios will be added when Wave 2 ships.")
    if wave in ("3",):
        print("Wave 3 scenarios will be added when Wave 3 ships.")


if __name__ == "__main__":
    asyncio.run(main())
