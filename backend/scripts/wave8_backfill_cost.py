"""Wave 8E.2 — backfill cost_usd on legacy ai_usage_events that have
token counts but no cost_usd.

Pre-Wave-8A.0 events were written before the cost calculator was wired
into the tracking path. They retain tokens_prompt + tokens_completion
(and, since 8A.1, cache_read_tokens + cache_creation_tokens) but
cost_usd is None.

This one-shot script recomputes cost_usd retroactively using the
CORRECTED formula (Wave 8E.2: disjoint counts + cache_creation
included) and writes it back. Idempotent — re-running on already-
backfilled events is a no-op because the filter excludes them.

Run with:
    cd backend && ./venv/bin/python -m scripts.wave8_backfill_cost
    cd backend && ./venv/bin/python -m scripts.wave8_backfill_cost --dry-run

Read-only when --dry-run is passed.
"""
import argparse
import asyncio
from datetime import datetime, timezone


async def main(dry_run: bool, include_existing: bool):
    from database import ai_usage_events_collection
    from services.ai_cost_calculator import compute_cost_usd

    print()
    print("=" * 70)
    print("WAVE 8E.2 — BACKFILL cost_usd ON LEGACY AI USAGE EVENTS")
    print(f"Mode: {'DRY-RUN (no writes)' if dry_run else 'WRITE'}")
    if include_existing:
        print("Scope: ALL events with tokens (including those with cost_usd set)")
        print("        — recomputes using corrected Wave 8E.2 formula.")
    else:
        print("Scope: events with cost_usd=None only")
        print("        — pass --include-existing to also recompute populated ones.")
    print(f"As of: {datetime.now(timezone.utc).isoformat()}")
    print("=" * 70)
    print()

    if include_existing:
        # Recompute every AI event that has tokens. Sometimes overwrites
        # a previously-set cost_usd computed with the buggy old formula.
        query = {
            "module_key": "ai_assistant",
            "tokens_prompt": {"$exists": True, "$ne": None},
        }
    else:
        # Filter: AI events that have tokens but no cost_usd.
        # We accept events with cost_usd=None OR cost_usd missing entirely.
        # Token-less events (cost can't be reconstructed) are skipped.
        query = {
            "module_key": "ai_assistant",
            "$or": [
                {"cost_usd": None},
                {"cost_usd": {"$exists": False}},
            ],
            "tokens_prompt": {"$exists": True, "$ne": None},
        }

    candidates = await ai_usage_events_collection.count_documents(query)
    print(f"Candidates: {candidates} events with tokens but no cost_usd.")
    if candidates == 0:
        print("Nothing to backfill. Exiting.")
        return

    backfilled = 0
    skipped_unknown_model = 0
    no_change = 0
    unchanged_already_correct = 0
    total_recovered_cost = 0.0
    total_old_cost = 0.0

    cursor = ai_usage_events_collection.find(query, no_cursor_timeout=True)
    async for doc in cursor:
        provider = doc.get("provider") or "anthropic"
        model_version = doc.get("model_version")
        previous_cost = doc.get("cost_usd")

        tokens_prompt = doc.get("tokens_prompt") or 0
        tokens_completion = doc.get("tokens_completion") or 0
        cache_read = doc.get("cache_read_tokens") or 0
        cache_create = doc.get("cache_creation_tokens") or 0

        cost = compute_cost_usd(
            provider=provider,
            model_version=model_version or "",
            tokens_prompt=tokens_prompt,
            tokens_completion=tokens_completion,
            cache_read_tokens=cache_read,
            cache_creation_tokens=cache_create,
        )

        if cost is None:
            skipped_unknown_model += 1
            continue
        if cost == 0:
            no_change += 1
            continue
        # In --include-existing mode, skip writes when the value is
        # already correct to the 6-decimal precision.
        if previous_cost is not None and abs(previous_cost - cost) < 1e-7:
            unchanged_already_correct += 1
            continue

        total_recovered_cost += cost
        if previous_cost is not None:
            total_old_cost += previous_cost
        backfilled += 1

        if not dry_run:
            await ai_usage_events_collection.update_one(
                {"id": doc["id"]},
                {"$set": {
                    "cost_usd": cost,
                    "cost_backfilled_at": datetime.now(timezone.utc).isoformat(),
                }},
            )

    print()
    print("─" * 70)
    print(f"Events processed             : {candidates}")
    print(f"Backfilled with cost_usd     : {backfilled}")
    print(f"Already-correct (skipped)    : {unchanged_already_correct}")
    print(f"Skipped (unknown model)      : {skipped_unknown_model}")
    print(f"Skipped (zero recovered cost): {no_change}")
    print(f"Total cost on rewritten docs : ${total_recovered_cost:.4f}")
    if total_old_cost > 0:
        delta = total_recovered_cost - total_old_cost
        print(f"  Previously stored (buggy)  : ${total_old_cost:.4f}")
        print(f"  Net correction             : ${delta:+.4f}")
    if dry_run:
        print()
        print("DRY-RUN: no documents were modified.")
        print("Re-run without --dry-run to apply.")
    else:
        print()
        print("Backfill complete. The 'cost_backfilled_at' field records when")
        print("each document was retroactively populated, for audit traceability.")
    print("=" * 70)
    print()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true",
                        help="Report what would change without writing.")
    parser.add_argument(
        "--include-existing", action="store_true",
        help=(
            "Also recompute events that already have cost_usd populated "
            "(corrects values written with the pre-Wave-8E.2 buggy formula). "
            "Use this once after deploying the calculator fix to clean up "
            "historic dashboard numbers."
        ),
    )
    args = parser.parse_args()
    asyncio.run(main(args.dry_run, args.include_existing))
