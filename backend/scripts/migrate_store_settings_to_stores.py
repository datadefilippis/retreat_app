#!/usr/bin/env python3
"""
migrate_store_settings_to_stores.py
====================================
Phase 6 of the Store consolidation plan — one-shot backfill of
legacy `organizations.store_settings` into `stores_collection`.

Why this exists
---------------
Pre-Phase-6 the platform had two parallel storage paths for store
configuration:

  · LEGACY: `organizations.store_settings` (embedded dict)
            written by `PATCH /store-settings`
  · NEW:    `stores_collection` (document per store)
            written by `PATCH /stores/{id}`

Phase 6 introduces dual-write at the legacy endpoint so future updates
keep both in sync. But orgs that NEVER touched the new admin UI still
have data only in the legacy location — this script bootstraps a
default store entry in `stores_collection` for those orgs so the
storefront, email service, and admin UI all see consistent data.

Idempotent — safe to re-run.
  · Orgs with an existing default store: no action.
  · Orgs with active non-default stores: promote the first one.
  · Orgs with only legacy data: create a new default store from
    `org.store_settings`.
  · Orgs with empty store_settings: leave alone (new merchants in
    onboarding — they'll get a store via the admin UI).

Usage:
    cd backend
    python -m scripts.migrate_store_settings_to_stores            # apply
    python -m scripts.migrate_store_settings_to_stores --dry-run  # report only
    python -m scripts.migrate_store_settings_to_stores --org-id X # single org

Exit codes:
    0  Migration applied (or no work to do).
    1  Partial failure — see logs.
"""

import argparse
import asyncio
import sys
from pathlib import Path

_BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_BACKEND_DIR))


# Field map mirrors routers/store_settings.LEGACY_TO_STORE_FIELD_MAP.
# Duplicated here intentionally — we don't import from the router to
# avoid spinning up the FastAPI app at script time.
_FIELD_MAP = {
    "display_name": "name",
    "store_description": "description",
    "is_storefront_published": "is_published",
}


def _legacy_to_store_doc(org: dict, ss: dict) -> dict:
    """Translate a legacy `org.store_settings` dict into a full
    `stores_collection` document ready for insert_one.

    Same shape as the bootstrap logic in
    routers/stores._ensure_default_store + routers/store_settings.
    _dual_write_to_default_store — kept in sync manually because we
    DON'T want to import the FastAPI router at script time."""
    from models.common import generate_id, utc_now

    now = utc_now()
    return {
        "id": generate_id(),
        "organization_id": org["id"],
        "slug": org.get("public_slug"),
        "name": ss.get("display_name") or org.get("name", "My Store"),
        "description": ss.get("store_description"),
        "visibility": "public",
        "contact_email": ss.get("contact_email"),
        "contact_phone": ss.get("contact_phone"),
        "sender_display_name": ss.get("sender_display_name"),
        "reply_to_email": ss.get("reply_to_email"),
        "notification_email": ss.get("notification_email"),
        "email_delivery": ss.get("email_delivery", "platform"),
        "fulfillment_modes": ss.get("fulfillment_modes") or ["shipping"],
        "storefront_languages": ["it"],  # default; admin can change via /stores/{id}
        "logo_url": ss.get("logo_url"),
        "brand_color": ss.get("brand_color"),
        "brand_color_text": ss.get("brand_color_text"),
        "seo_title": ss.get("seo_title"),
        "seo_description": ss.get("seo_description"),
        "is_published": bool(ss.get("is_storefront_published")),
        "is_default": True,
        "is_active": True,
        "created_at": now,
        "updated_at": now,
    }


async def _audit_org(org_id: str) -> dict:
    """Classify an org's store-config state:
      - 'has_default'         : already has a default store
      - 'promote_existing'    : has active stores but none flagged default
      - 'bootstrap_from_legacy': has legacy store_settings but zero stores
      - 'empty'               : no legacy data, no stores — skip
      - 'missing_org'         : org id not found
    """
    from database import organizations_collection, stores_collection

    org = await organizations_collection.find_one(
        {"id": org_id},
        {"_id": 0, "id": 1, "name": 1, "public_slug": 1, "store_settings": 1},
    )
    if not org:
        return {"state": "missing_org", "org": None}

    default = await stores_collection.find_one(
        {"organization_id": org_id, "is_default": True, "is_active": True},
        {"_id": 0, "id": 1},
    )
    if default:
        return {"state": "has_default", "org": org, "default_id": default["id"]}

    any_active = await stores_collection.find_one(
        {"organization_id": org_id, "is_active": True},
        {"_id": 0, "id": 1},
    )
    if any_active:
        return {"state": "promote_existing", "org": org, "candidate_id": any_active["id"]}

    ss = org.get("store_settings") or {}
    if any(ss.get(k) for k in ("display_name", "contact_email", "store_description")):
        return {"state": "bootstrap_from_legacy", "org": org}

    return {"state": "empty", "org": org}


async def _apply_org(audit_result: dict, dry_run: bool) -> str:
    """Apply the migration action for a single audited org. Returns
    a human-readable status string."""
    from database import organizations_collection, stores_collection
    from models.common import utc_now

    state = audit_result["state"]
    org = audit_result.get("org")
    if not org:
        return "SKIP (org missing)"

    org_id = org["id"]
    org_name = org.get("name", "?")

    if state == "has_default":
        return f"OK (already has default store={audit_result['default_id']})"

    if state == "promote_existing":
        if dry_run:
            return f"WOULD PROMOTE store={audit_result['candidate_id']} as default"
        await stores_collection.update_one(
            {"id": audit_result["candidate_id"]},
            {"$set": {"is_default": True, "updated_at": utc_now()}},
        )
        return f"PROMOTED store={audit_result['candidate_id']} to default"

    if state == "bootstrap_from_legacy":
        ss = org.get("store_settings") or {}
        store_doc = _legacy_to_store_doc(org, ss)
        if dry_run:
            return (
                f"WOULD CREATE store from legacy: "
                f"name={store_doc['name']!r}, is_published={store_doc['is_published']}, "
                f"slug={store_doc['slug']!r}"
            )
        try:
            await stores_collection.insert_one(store_doc)
            return f"CREATED store={store_doc['id']} from legacy store_settings"
        except Exception as e:
            return f"FAIL: {type(e).__name__}: {e}"

    if state == "empty":
        return "SKIP (empty — onboarding org, no store config yet)"

    return f"UNKNOWN state={state}"


async def _run(args):
    from database import organizations_collection

    if args.org_id:
        org_ids = [args.org_id]
    else:
        cursor = organizations_collection.find({}, {"_id": 0, "id": 1})
        org_ids = [doc["id"] async for doc in cursor]

    print("=" * 70)
    mode = "DRY-RUN" if args.dry_run else "APPLY"
    print(f"migrate_store_settings_to_stores — {mode}")
    print("=" * 70)
    print(f"Target orgs: {len(org_ids)}")
    print()

    counts = {"OK": 0, "PROMOTED": 0, "CREATED": 0, "SKIP": 0, "FAIL": 0, "OTHER": 0}
    fail_details = []

    for org_id in org_ids:
        audit = await _audit_org(org_id)
        result = await _apply_org(audit, dry_run=args.dry_run)
        name = (audit.get("org") or {}).get("name", "?")
        print(f"  org={org_id} name={name!r}")
        print(f"     -> {result}")

        # Bucket the result for the summary
        if result.startswith("OK"):
            counts["OK"] += 1
        elif "PROMOTED" in result:
            counts["PROMOTED"] += 1
        elif "CREATED" in result:
            counts["CREATED"] += 1
        elif result.startswith("SKIP"):
            counts["SKIP"] += 1
        elif result.startswith("FAIL"):
            counts["FAIL"] += 1
            fail_details.append((org_id, result))
        else:
            counts["OTHER"] += 1

    print()
    print("=" * 70)
    print("Summary")
    print("=" * 70)
    for k, v in counts.items():
        if v:
            print(f"  {k:10s} {v}")

    if fail_details:
        print()
        print("Failures:")
        for org_id, msg in fail_details:
            print(f"  - {org_id}: {msg}")
        return 1
    return 0


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--dry-run", action="store_true",
                        help="Inspect only — no DB changes")
    parser.add_argument("--org-id", type=str, default=None,
                        help="Migrate a single org by id (default: all)")
    args = parser.parse_args()
    rc = asyncio.run(_run(args))
    sys.exit(rc)


if __name__ == "__main__":
    main()
