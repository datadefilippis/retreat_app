"""
Cleanup legacy alert duplicates (v14.1 — Pillar 1.7).

Background
----------
The diagnostic on Demo Restaurant surfaced groups of 3-8 alerts with
identical title and payload, all stuck in ``status="new"`` or
``status="acknowledged"``. Investigation traced them to the legacy
``alert_rules.py`` v2 engine (now dead code, retired in favour of the
v3 ``alert_engine.py``). The legacy rules never populated the
``entity_key`` field, so the v3 dedup logic in
``alert_repository.find_active_dedup_keys_v3`` cannot match them — the
fallback `(alert_type, date_reference)` key changes with every tick.

Why these duplicates are SAFE to bulk-resolve
---------------------------------------------
- The legacy engine that produced them is no longer wired into the
  module-registry dispatch (verified by grep). They cannot regenerate.
- The v3 engine emits new alerts WITH a proper entity_key, so any
  ongoing condition still surfaces with the correct dedup-aware
  semantics.
- ``status="resolved"`` plus ``auto_resolved=True`` and a clear
  ``resolution_note`` preserves audit trail — no data is deleted.

What this script does
---------------------
Idempotent migration:
  1. Find alerts with NULL/empty ``entity_key`` AND status in
     {new, acknowledged}.
  2. For each (org_id, alert_type) group, keep the MOST RECENT one as
     ``new`` (so the merchant still sees the current state of the
     issue) and resolve the older N-1 duplicates.
  3. Log the count per org for verification.

Run
---
    cd backend
    ./venv/bin/python scripts/cleanup_legacy_alert_duplicates.py            # report only
    ./venv/bin/python scripts/cleanup_legacy_alert_duplicates.py --apply    # commit changes
"""
from __future__ import annotations

import argparse
import asyncio
import os
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

# Boot the .env so MONGO_URL / DB_NAME resolve when run standalone
sys.path.insert(0, str(Path(__file__).parent.parent))
from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent / ".env", override=True)


async def main(apply: bool) -> int:
    from motor.motor_asyncio import AsyncIOMotorClient

    client = AsyncIOMotorClient(os.environ["MONGO_URL"])
    db = client[os.environ["DB_NAME"]]

    # 1. Find candidates — open alerts missing entity_key. Two passes
    #    to cover docs where the field is absent vs. explicitly None.
    candidates = []
    async for doc in db.alerts.find(
        {
            "status": {"$in": ["new", "acknowledged"]},
            "$or": [
                {"entity_key": {"$exists": False}},
                {"entity_key": None},
                {"entity_key": ""},
            ],
        },
        {"_id": 0, "id": 1, "organization_id": 1, "metric_payload": 1,
         "title": 1, "created_at": 1, "status": 1},
    ):
        candidates.append(doc)

    if not candidates:
        print("No legacy duplicates found — DB is clean.")
        return 0

    # 2. Group by (org_id, alert_type). Title used as fallback when
    #    alert_type missing (very old records).
    groups: dict = defaultdict(list)
    for c in candidates:
        org = c["organization_id"]
        atype = (c.get("metric_payload") or {}).get("alert_type") or _title_prefix(c.get("title"))
        groups[(org, atype)].append(c)

    # 3. For each group with >1 alert, keep the newest open one, resolve the rest.
    to_resolve_ids: list[str] = []
    summary_per_org: dict[str, dict] = defaultdict(lambda: {"groups": 0, "to_resolve": 0})

    for (org, atype), items in groups.items():
        if len(items) <= 1:
            continue
        items.sort(key=lambda x: x.get("created_at") or "", reverse=True)
        keep = items[0]
        resolve = items[1:]
        to_resolve_ids.extend(r["id"] for r in resolve)
        summary_per_org[org]["groups"] += 1
        summary_per_org[org]["to_resolve"] += len(resolve)

    # 4. Report
    total_candidates = sum(len(v) for v in groups.values())
    total_groups = sum(1 for v in groups.values() if len(v) > 1)
    total_to_resolve = len(to_resolve_ids)
    print(f"Candidates inspected:   {len(candidates)}")
    print(f"Groups with duplicates: {total_groups}")
    print(f"Alerts to auto-resolve: {total_to_resolve}")
    print()
    for org, stats in summary_per_org.items():
        print(f"  {org[:8]}... : {stats['groups']} groups → {stats['to_resolve']} legacy duplicates")

    if not apply:
        print()
        print("Dry run — pass --apply to commit the auto-resolve.")
        return 0

    if not to_resolve_ids:
        print("Nothing to apply.")
        return 0

    now_iso = datetime.now(timezone.utc).isoformat()
    result = await db.alerts.update_many(
        {"id": {"$in": to_resolve_ids}},
        {"$set": {
            "status": "resolved",
            "resolved_at": now_iso,
            "auto_resolved": True,
            "resolution_note": (
                "Legacy alert cleanup (v14.1 Pillar 1.7) — pre-v3 alert "
                "without entity_key; superseded by a more recent instance "
                "of the same alert_type."
            ),
        }},
    )
    print()
    print(f"Applied: modified {result.modified_count} alert(s).")
    return 0


def _title_prefix(title) -> str:
    """Fallback grouping key when alert_type is missing in the payload."""
    if not isinstance(title, str):
        return "<unknown>"
    return title.lower().split()[0] if title else "<empty>"


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Actually update the alerts collection (default: dry run).",
    )
    args = parser.parse_args()
    sys.exit(asyncio.run(main(apply=args.apply)))
