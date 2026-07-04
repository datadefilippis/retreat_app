#!/usr/bin/env python3
"""
reset_org_data.py — wipe every org-scoped collection for a single user's
organization while preserving the user account and the organization record
itself.

Use case: the developer running localhost wants to clear all commerce + test
data for davidedefilippis94@gmail.com so they can test flows from scratch
(no leftover products, orders, reservations, customers, stores, …).

Usage:
  # Safe preview — lists what WOULD be deleted, no writes.
  ./venv/bin/python scripts/reset_org_data.py --email davidedefilippis94@gmail.com

  # After reviewing the preview, to actually delete:
  ./venv/bin/python scripts/reset_org_data.py --email davidedefilippis94@gmail.com --execute

PRESERVED (never touched):
  * The user record in users
  * The organization record in organizations
  * Global seeds: pricing_plans, commercial_plans, platform_settings,
    schema_versions

DELETED (scoped to the user's organization_id):
  * stores, products, product_extras, service_options,
    event_occurrences, event_ticket_tiers, event_seat_reservations,
    issued_tickets, issued_bookings, issued_reservations,
    availability_rules, blocked_slots, coupons, customer_accounts,
    customers, suppliers, orders, sales_records, expense_records,
    purchase_records, fixed_costs, datasets, alerts, insights,
    audit_logs, column_mappings, dataset_column_profiles,
    data_validation_rules, kpi_snapshots, module_configs,
    temp_uploads, customer_metrics, product_metrics,
    payment_connections, digests, ai_usage_events, chat_sessions,
    organization_modules, module_subscriptions, billing_events,
    catalog_audit_log, invites

The script is idempotent: re-running after an execute is a no-op (counts=0).
"""

from __future__ import annotations

import argparse
import asyncio
import os
import sys

# Resolve backend root so database.py can be imported.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


# Collections scoped by organization_id. Keys are stable display names.
ORG_SCOPED_COLLECTIONS = [
    # commerce-core
    "stores",
    "products",
    "product_extras",
    "service_options",
    "event_occurrences",
    "event_ticket_tiers",
    "event_seat_reservations",
    "issued_tickets",
    "issued_bookings",
    "issued_reservations",
    "availability_rules",
    "blocked_slots",
    "coupons",
    "customer_accounts",
    "customers",
    "suppliers",
    "orders",
    # finance
    "sales_records",
    "expense_records",
    "purchase_records",
    "fixed_costs",
    # data pipeline
    "datasets",
    "column_mappings",
    "dataset_column_profiles",
    "data_validation_rules",
    "temp_uploads",
    # signals / analytics
    "alerts",
    "insights",
    "kpi_snapshots",
    "customer_metrics",
    "product_metrics",
    # audit + chat + ai
    "audit_logs",
    "ai_usage_events",
    "chat_sessions",
    "digests",
    "catalog_audit_log",
    # payments + modules + billing
    "payment_connections",
    "organization_modules",
    "module_configs",
    "module_subscriptions",
    "billing_events",
    "invites",
]


# Collections that are GLOBAL or that we never want to touch for safety.
# Kept here as a second-line defense so future changes can't accidentally
# include them via a typo in ORG_SCOPED_COLLECTIONS.
GLOBAL_COLLECTIONS_NEVER_DELETE = {
    "users",
    "organizations",
    "pricing_plans",
    "commercial_plans",
    "platform_settings",
    "schema_versions",
}


async def _resolve_user_and_org(users_collection, organizations_collection, email: str):
    user = await users_collection.find_one(
        {"email": email},
        {"_id": 0, "id": 1, "email": 1, "organization_id": 1, "name": 1},
    )
    if not user:
        raise SystemExit(f"No user found with email={email!r}. Aborting.")
    org_id = user.get("organization_id")
    if not org_id:
        raise SystemExit(f"User {email!r} has no organization_id. Aborting.")
    org = await organizations_collection.find_one(
        {"id": org_id}, {"_id": 0, "id": 1, "name": 1},
    )
    if not org:
        raise SystemExit(f"Organization id={org_id!r} not found. Aborting.")
    return user, org


async def _count_all(db, org_id: str):
    """Return [(collection_name, count), ...] for every org-scoped collection."""
    out = []
    for name in ORG_SCOPED_COLLECTIONS:
        if name in GLOBAL_COLLECTIONS_NEVER_DELETE:
            # Defensive: should never happen given the lists, but makes the
            # invariant explicit.
            continue
        coll = db[name]
        n = await coll.count_documents({"organization_id": org_id})
        out.append((name, n))
    return out


async def _delete_all(db, org_id: str):
    """Delete for every org-scoped collection. Returns [(name, deleted), ...]."""
    out = []
    for name in ORG_SCOPED_COLLECTIONS:
        if name in GLOBAL_COLLECTIONS_NEVER_DELETE:
            continue
        coll = db[name]
        res = await coll.delete_many({"organization_id": org_id})
        out.append((name, res.deleted_count))
    return out


def _print_summary(title: str, rows):
    total = sum(n for _, n in rows)
    width_name = max((len(n) for n, _ in rows), default=10)
    print(f"\n{title}")
    print("-" * (width_name + 12))
    nonzero = [(n, c) for n, c in rows if c > 0]
    if not nonzero:
        print("  (nothing)")
    else:
        for name, count in nonzero:
            print(f"  {name:<{width_name}}  {count}")
    print(f"  {'TOTAL':<{width_name}}  {total}")


async def main():
    parser = argparse.ArgumentParser(description="Wipe all org-scoped data for a single user's organization.")
    parser.add_argument("--email", required=True, help="Admin user email whose organization will be wiped.")
    parser.add_argument("--execute", action="store_true",
                        help="Actually perform the deletions. Without this flag the script runs in dry-run mode.")
    args = parser.parse_args()

    # Import lazily so the script is importable for testing without env setup.
    from database import db, users_collection, organizations_collection

    print(f"Target user email: {args.email}")
    user, org = await _resolve_user_and_org(users_collection, organizations_collection, args.email)
    print(f"  Resolved user:         id={user['id']}  name={user.get('name') or '—'}")
    print(f"  Resolved organization: id={org['id']}  name={org.get('name') or '—'}")

    counts = await _count_all(db, org["id"])
    _print_summary("Documents currently scoped to this organization:", counts)

    if not args.execute:
        print("\nDRY RUN — nothing was modified.")
        print("Re-run with --execute to perform the deletion.")
        print("\nPreserved (never deleted):")
        print(f"  users({args.email}), organizations(id={org['id']}),")
        print("  pricing_plans, commercial_plans, platform_settings, schema_versions")
        return

    print("\n⚠️  EXECUTING deletion. This is NOT reversible.")
    deleted = await _delete_all(db, org["id"])
    _print_summary("Documents deleted:", deleted)

    # Safety re-count — every collection should report 0 now.
    after = await _count_all(db, org["id"])
    leftovers = [(n, c) for n, c in after if c > 0]
    if leftovers:
        print("\n⚠️  Some collections still contain org documents. Investigate:")
        for name, count in leftovers:
            print(f"  {name}: {count}")
    else:
        print("\n✅ All org-scoped collections are empty. User account and organization preserved.")


if __name__ == "__main__":
    asyncio.run(main())
