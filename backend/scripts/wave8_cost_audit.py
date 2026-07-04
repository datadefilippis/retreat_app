"""Wave 8 — forensic audit of hidden / excessive AI costs.

Run with:
    cd backend && ./venv/bin/python -m scripts.wave8_cost_audit

Produces a single consolidated report on stdout covering 12 dimensions:

  Coverage           how much of the spend is tracked
  Underbilling       gaps in the cost formula vs Anthropic billing
  Cache efficiency   what % of input is cache-served (prompt cache ROI)
  Prompt cost shape  input vs output token ratio
  Hot spenders       top 10 orgs / users / features by tracked $
  Conversation cost  avg / max cost of a chat conversation
  Dead code spend    events from supposedly-dead paths
  Test pollution     events from smoke / test runs polluting real numbers
  Multi-turn ratio   avg rounds per chat (Wave 8A.2)
  Idle agents        agent_ids registered but never used
  Failed calls       events with error_code populated
  Time pattern       hourly histogram (catches cron over-firing)

Read-only — never writes to the database.
"""
import asyncio
from datetime import datetime, timedelta, timezone
from collections import defaultdict


async def main():
    from database import ai_usage_events_collection

    now = datetime.now(timezone.utc)
    cutoff_30d = (now - timedelta(days=30)).isoformat()
    cutoff_all = "1900-01-01"

    print()
    print("=" * 78)
    print("WAVE 8 — FORENSIC COST AUDIT")
    print(f"As of: {now.isoformat()}")
    print("=" * 78)

    # ── Baseline counts ─────────────────────────────────────────────────────

    total_all = await ai_usage_events_collection.count_documents({})
    total_30d = await ai_usage_events_collection.count_documents({
        "created_at": {"$gte": cutoff_30d},
    })
    total_ai = await ai_usage_events_collection.count_documents({
        "module_key": "ai_assistant",
    })

    print()
    print(f"┌─ Collection size")
    print(f"│  Total events (all time)        : {total_all:,}")
    print(f"│  Last 30 days                   : {total_30d:,}")
    print(f"│  module_key=ai_assistant (AI only): {total_ai:,}")

    if total_all == 0:
        print()
        print("No events in the collection. Nothing to audit. Stopping.")
        return

    # ── 1. COVERAGE: cost_usd present vs null ───────────────────────────────

    with_cost = await ai_usage_events_collection.count_documents({
        "cost_usd": {"$ne": None, "$exists": True},
    })
    cost_coverage = round(with_cost / total_all * 100, 1) if total_all else 0

    print()
    print(f"┌─ 1. COVERAGE — tracked cost_usd")
    print(f"│  Events with cost_usd present   : {with_cost:,} / {total_all:,} ({cost_coverage}%)")
    if cost_coverage < 90:
        print(f"│  ⚠ {100 - cost_coverage:.1f}% of events have NULL cost_usd")
        print(f"│    → Pre-Wave-1 legacy or unknown model. Tokens may still be present.")

    # ── 2. UNDERBILLING gap: cache_creation_tokens recorded but uncosted ───

    agg = ai_usage_events_collection.aggregate([
        {"$match": {"module_key": "ai_assistant"}},
        {"$group": {
            "_id": None,
            "total_cost":    {"$sum": {"$ifNull": ["$cost_usd", 0]}},
            "total_input":   {"$sum": {"$ifNull": ["$tokens_prompt", 0]}},
            "total_output":  {"$sum": {"$ifNull": ["$tokens_completion", 0]}},
            "total_cache_r": {"$sum": {"$ifNull": ["$cache_read_tokens", 0]}},
            "total_cache_w": {"$sum": {"$ifNull": ["$cache_creation_tokens", 0]}},
        }},
    ])
    totals = {"total_cost": 0, "total_input": 0, "total_output": 0,
              "total_cache_r": 0, "total_cache_w": 0}
    async for doc in agg:
        totals = doc

    # Estimate the corrected cost (the bug-free formula):
    #   input × $3/M  +  output × $15/M  +  cache_r × $0.30/M  +  cache_w × $3.75/M
    # (Sonnet 4 pricing. Cost numbers in USD.)
    SONNET_IN = 3.00 / 1_000_000
    SONNET_OUT = 15.00 / 1_000_000
    SONNET_CACHE_R = 0.30 / 1_000_000
    SONNET_CACHE_W = 3.75 / 1_000_000

    true_input_cost = totals["total_input"] * SONNET_IN
    true_output_cost = totals["total_output"] * SONNET_OUT
    true_cache_r_cost = totals["total_cache_r"] * SONNET_CACHE_R
    true_cache_w_cost = totals["total_cache_w"] * SONNET_CACHE_W
    true_total = true_input_cost + true_output_cost + true_cache_r_cost + true_cache_w_cost

    tracked = totals["total_cost"]
    delta = true_total - tracked
    delta_pct = round(delta / tracked * 100, 1) if tracked > 0 else 0

    print()
    print(f"┌─ 2. UNDERBILLING — tracked cost vs recomputed true cost")
    print(f"│  Tracked total cost_usd          : ${tracked:>10.4f}")
    print(f"│  Recomputed (correct formula)    : ${true_total:>10.4f}")
    print(f"│  Delta (hidden)                  : ${delta:>10.4f} ({delta_pct:+.1f}%)")
    print(f"│  Breakdown of recomputed cost:")
    print(f"│    input tokens   ({totals['total_input']:>10,}) × $3.00/M  = ${true_input_cost:>9.4f}")
    print(f"│    output tokens  ({totals['total_output']:>10,}) × $15.00/M = ${true_output_cost:>9.4f}")
    print(f"│    cache_read     ({totals['total_cache_r']:>10,}) × $0.30/M  = ${true_cache_r_cost:>9.4f}")
    print(f"│    cache_create   ({totals['total_cache_w']:>10,}) × $3.75/M  = ${true_cache_w_cost:>9.4f}")
    cache_w_pct_of_delta = round(true_cache_w_cost / delta * 100, 1) if delta > 0 else 0
    if delta > 0:
        print(f"│  → ${true_cache_w_cost:.4f} of the delta is cache_creation cost the")
        print(f"│    current calculator silently drops ({cache_w_pct_of_delta}% of total gap).")

    # ── 3. CACHE EFFICIENCY ────────────────────────────────────────────────

    total_input_billable = totals["total_input"] + totals["total_cache_r"] + totals["total_cache_w"]
    cache_hit_ratio = round(totals["total_cache_r"] / total_input_billable * 100, 1) if total_input_billable > 0 else 0

    print()
    print(f"┌─ 3. CACHE EFFICIENCY — prompt cache ROI")
    print(f"│  Total input-side tokens         : {total_input_billable:>10,}")
    print(f"│  Of which served from cache      : {totals['total_cache_r']:>10,} ({cache_hit_ratio}%)")
    if cache_hit_ratio >= 50:
        print(f"│  ✓ Healthy: most prompts hit the cache. Wave 1 caching is paying off.")
    elif cache_hit_ratio >= 20:
        print(f"│  ⚠ Sub-optimal: many calls miss the cache. Check that the system")
        print(f"│    prompt is stable + the cache_control directive is in place.")
    else:
        print(f"│  ✗ Very low: cache is not delivering. The system prompt may be")
        print(f"│    changing per-call (locale/period leaking in) → cache invalidated.")

    # ── 4. PROMPT COST SHAPE — input vs output ─────────────────────────────

    ratio_in_out = round(totals["total_input"] / totals["total_output"], 1) if totals["total_output"] > 0 else 0
    print()
    print(f"┌─ 4. PROMPT SHAPE — input vs output token ratio")
    print(f"│  Input / Output ratio            : {ratio_in_out}:1")
    if ratio_in_out > 30:
        print(f"│  ⚠ Very prompt-heavy. The system prompt + tool defs dominate.")
        print(f"│    Optimisation: trim unused tool definitions per-org based on")
        print(f"│    active modules (already done) + shorter system prompt.")

    # ── 5. HOT SPENDERS — top 5 orgs / users / features ────────────────────

    print()
    print(f"┌─ 5. HOT SPENDERS (last 30 days)")

    async def _top(group_field, label, limit=5):
        pipeline = [
            {"$match": {"module_key": "ai_assistant", "created_at": {"$gte": cutoff_30d}}},
            {"$group": {
                "_id": f"${group_field}",
                "events": {"$sum": 1},
                "cost":   {"$sum": {"$ifNull": ["$cost_usd", 0]}},
            }},
            {"$sort": {"cost": -1}},
            {"$limit": limit},
        ]
        rows = []
        async for r in ai_usage_events_collection.aggregate(pipeline):
            rows.append(r)
        if rows:
            print(f"│  Top {limit} by {label}:")
            for r in rows:
                _id = r["_id"] or "<null>"
                _id_str = str(_id)[-12:] if isinstance(_id, str) and len(_id) > 12 else str(_id)
                print(f"│    {_id_str:>14}  {r['events']:>6} events  ${r['cost']:>8.4f}")
        else:
            print(f"│  Top {limit} by {label}: (no data)")

    await _top("organization_id", "organization")
    await _top("user_id", "user")
    await _top("feature", "feature", limit=10)
    await _top("agent_id", "agent")

    # ── 6. CONVERSATION COST — avg vs max ──────────────────────────────────

    conv_pipeline = [
        {"$match": {"feature": "chat", "conversation_id": {"$ne": None}}},
        {"$group": {
            "_id": "$conversation_id",
            "rounds": {"$sum": 1},
            "cost":   {"$sum": {"$ifNull": ["$cost_usd", 0]}},
        }},
        {"$group": {
            "_id": None,
            "conv_count": {"$sum": 1},
            "avg_cost":   {"$avg": "$cost"},
            "max_cost":   {"$max": "$cost"},
            "avg_rounds": {"$avg": "$rounds"},
            "max_rounds": {"$max": "$rounds"},
        }},
    ]
    conv_stats = None
    async for doc in ai_usage_events_collection.aggregate(conv_pipeline):
        conv_stats = doc

    print()
    print(f"┌─ 6. CONVERSATION COST (chat sessions with conversation_id)")
    if conv_stats:
        print(f"│  Total chat conversations        : {conv_stats['conv_count']:,}")
        print(f"│  Avg rounds per chat             : {conv_stats['avg_rounds']:.2f}")
        print(f"│  Max rounds in a single chat     : {conv_stats['max_rounds']}")
        print(f"│  Avg cost per chat               : ${conv_stats['avg_cost']:.4f}")
        print(f"│  Max cost in a single chat       : ${conv_stats['max_cost']:.4f}")
        if conv_stats["max_cost"] > 0.1:
            print(f"│  ⚠ One conversation cost ${conv_stats['max_cost']:.4f}. Investigate via")
            print(f"│    dashboard → forensic event view.")
    else:
        print(f"│  No chats with conversation_id yet (pre-Wave-8A.2 events lack this).")

    # ── 7. DEAD CODE SPEND — ai_insight_service events ─────────────────────

    dead_spend = ai_usage_events_collection.aggregate([
        {"$match": {"feature": "insight"}},
        {"$group": {"_id": None, "n": {"$sum": 1},
                    "cost": {"$sum": {"$ifNull": ["$cost_usd", 0]}}}},
    ])
    insight_stats = {"n": 0, "cost": 0}
    async for doc in dead_spend:
        insight_stats = doc

    print()
    print(f"┌─ 7. DEAD CODE SPEND")
    print(f"│  ai_insight_service events      : {insight_stats['n']:,}")
    print(f"│  ai_insight_service spend       : ${insight_stats['cost']:.4f}")
    if insight_stats["n"] == 0:
        print(f"│  ✓ Dead code path correctly silent.")
    else:
        print(f"│  ⚠ Dead code path is being invoked despite endpoint 410-Gone.")
        print(f"│    Investigate: who's calling generate_cashflow_insight()?")

    # ── 8. TEST POLLUTION — smoke / test session events ────────────────────

    test_org_match = {
        "$or": [
            {"organization_id": {"$regex": "^smoke-"}},
            {"organization_id": {"$regex": "^test-"}},
            {"organization_id": {"$regex": "smoke", "$options": "i"}},
        ]
    }
    test_count = await ai_usage_events_collection.count_documents(test_org_match)
    test_cost_agg = ai_usage_events_collection.aggregate([
        {"$match": test_org_match},
        {"$group": {"_id": None, "cost": {"$sum": {"$ifNull": ["$cost_usd", 0]}}}},
    ])
    test_cost = 0
    async for doc in test_cost_agg:
        test_cost = doc["cost"]

    print()
    print(f"┌─ 8. TEST POLLUTION — smoke/test events still in collection")
    print(f"│  Events from test orgs           : {test_count:,}")
    print(f"│  Spend from test orgs            : ${test_cost:.4f}")
    if test_cost > 0.01:
        print(f"│  ⚠ Test runs are polluting production aggregations.")
        print(f"│    Recommend: filter test orgs out of governance dashboard by default.")

    # ── 9. MULTI-TURN RATIO — chats with rounds > 1 ────────────────────────

    print()
    print(f"┌─ 9. MULTI-TURN AGENTIC LOOP STATS")
    if conv_stats:
        print(f"│  Avg rounds per chat: {conv_stats['avg_rounds']:.2f}  Max: {conv_stats['max_rounds']}")
        if conv_stats["avg_rounds"] > 2.5:
            print(f"│  ⚠ Chats are doing many round-trips. Each round-trip = 1 Anthropic")
            print(f"│    call. Check if the tool registry encourages multi-step plans")
            print(f"│    when a single one would suffice.")

    # ── 10. IDLE AGENTS ─────────────────────────────────────────────────────

    agents_pipeline = [
        {"$match": {"module_key": "ai_assistant"}},
        {"$group": {"_id": "$agent_id", "n": {"$sum": 1}}},
    ]
    seen_agents = set()
    async for r in ai_usage_events_collection.aggregate(agents_pipeline):
        if r["_id"]:
            seen_agents.add(r["_id"])

    KNOWN_AGENTS = {
        "financial_analyst",        # Wave 7 default
        "digest_builder",           # Wave 8A.0
        "digest_report_builder",    # Wave 8A.0
        "health_explanation",       # Wave 8A.0
        "ai_insight_service",       # Wave 8A.0 (dead code)
    }
    idle = KNOWN_AGENTS - seen_agents
    unknown = seen_agents - KNOWN_AGENTS

    print()
    print(f"┌─ 10. AGENT INVENTORY")
    print(f"│  Agents seen in events           : {len(seen_agents)} ({', '.join(sorted(seen_agents)) or 'none'})")
    print(f"│  Registered but never used       : {len(idle)} ({', '.join(sorted(idle)) or 'none'})")
    if unknown:
        print(f"│  ⚠ Unknown agent_id observed     : {', '.join(sorted(unknown))}")

    # ── 11. FAILED CALLS — events with error_code ──────────────────────────

    failed_count = await ai_usage_events_collection.count_documents({
        "error_code": {"$ne": None, "$exists": True},
    })
    print()
    print(f"┌─ 11. FAILED / REFUSED CALLS")
    print(f"│  Events with error_code set      : {failed_count}")
    if failed_count == 0:
        print(f"│  (Wave 8B governance refusals would populate error_code.")
        print(f"│   Zero events means no budget block or kill-switch event has been hit yet.)")

    # ── 12. TIME PATTERN — hourly histogram (last 7 days) ──────────────────

    cutoff_7d = (now - timedelta(days=7)).isoformat()
    hourly_pipeline = [
        {"$match": {"module_key": "ai_assistant", "created_at": {"$gte": cutoff_7d}}},
        {"$group": {
            "_id": {"$substr": ["$created_at", 11, 2]},
            "n": {"$sum": 1},
            "cost": {"$sum": {"$ifNull": ["$cost_usd", 0]}},
        }},
        {"$sort": {"_id": 1}},
    ]
    by_hour = []
    async for r in ai_usage_events_collection.aggregate(hourly_pipeline):
        by_hour.append((r["_id"], r["n"], r["cost"]))

    print()
    print(f"┌─ 12. HOURLY PATTERN (UTC, last 7 days)")
    if by_hour:
        max_n = max(r[1] for r in by_hour)
        for hour, n, cost in by_hour:
            bar_width = int(40 * n / max_n) if max_n > 0 else 0
            bar = "█" * bar_width
            print(f"│  {hour}:00  {bar:40}  {n:>5}  ${cost:>7.4f}")
    else:
        print(f"│  (no events in the last 7 days)")

    print()
    print("=" * 78)
    print("AUDIT COMPLETE")
    print("=" * 78)
    print()


if __name__ == "__main__":
    asyncio.run(main())
