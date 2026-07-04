#!/usr/bin/env python3
"""
diagnose_data_rows_gate.py
==========================
Forensic diagnostic for `cashflow_monitor.data_rows` quota enforcement.

Run from the backend/ directory:

    cd backend
    python -m scripts.diagnose_data_rows_gate --org-id <ORG_ID>
    python -m scripts.diagnose_data_rows_gate --email <user_email>
    python -m scripts.diagnose_data_rows_gate --slug <org_slug>

Why this exists:
  Onda 9.Y.0 closed every router-level data_rows bypass we could find,
  but a tester reported they could STILL insert rows on a Free plan.
  The audit hypothesis was a stale `module_subscription` for
  cashflow_monitor that grants `data_rows: -1` and short-circuits the
  gate at services/module_access.py:218-230 (Step 1 of resolution).

  This script answers ONE question per org with full evidence:
    "Why is the data_rows gate behaving the way it is for THIS org?"

What it prints (everything in one shot):
  1. Org identity:        commercial_plan_slug, billing_status, plan, has_used_trial
  2. Module subscriptions: ALL rows for cashflow_monitor (active + cancelled)
                           with their pricing_plan_id and resolved limits.data_rows
  3. Effective limit:     what `get_effective_limit` returns RIGHT NOW
  4. Active addons:       any `addon_*` rows that contribute to data_rows
  5. Current usage:       how many rows the gate sees this calendar month
  6. Verdict:             EXPECTED-BLOCK / EXPECTED-PASS / DRIFT-DETECTED
  7. Mongo collection rows: actual count of sales/expenses/purchases/
                            fixed_costs/purchase_records for the org
                            (so you can compare with the gate's view)

Exit code:
  0 = no drift (gate behaviour matches expectation for the plan)
  1 = drift detected (stale module subscription, addon issue, etc.)

Read-only — never mutates anything.
"""

import argparse
import asyncio
import sys
from datetime import datetime, timezone
from pathlib import Path

# ── Add backend/ to sys.path so we can import project modules ────────────────
_BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_BACKEND_DIR))


async def _resolve_org_id(args) -> str:
    from database import organizations_collection, users_collection

    if args.org_id:
        org = await organizations_collection.find_one({"id": args.org_id})
        if not org:
            print(f"ERROR: org_id={args.org_id} not found", file=sys.stderr)
            sys.exit(2)
        return args.org_id

    if args.slug:
        org = await organizations_collection.find_one({"public_slug": args.slug})
        if not org:
            print(f"ERROR: slug={args.slug} not found", file=sys.stderr)
            sys.exit(2)
        return org["id"]

    if args.email:
        user = await users_collection.find_one({"email": args.email.lower().strip()})
        if not user or not user.get("organization_id"):
            print(f"ERROR: user email={args.email} has no organization", file=sys.stderr)
            sys.exit(2)
        return user["organization_id"]

    print("ERROR: provide --org-id, --slug or --email", file=sys.stderr)
    sys.exit(2)


def _fmt_limit(value):
    if value == -1:
        return "UNLIMITED (-1)"
    if value == 0:
        return "DISABLED (0)"
    return str(value)


async def _diagnose(org_id: str) -> int:
    """Returns 0 if no drift, 1 if drift detected."""
    from database import (
        organizations_collection,
        module_subscriptions_collection,
        pricing_plans_collection,
        sales_records_collection,
        expense_records_collection,
        purchase_records_collection,
        fixed_costs_collection,
    )
    from repositories import billing_repository
    from services.module_access import (
        get_effective_limit,
        get_module_entitlements,
    )
    from repositories.usage_repository import count_usage
    from services.module_access import get_current_period_range

    org = await organizations_collection.find_one({"id": org_id})
    if not org:
        print(f"ERROR: org {org_id} disappeared", file=sys.stderr)
        return 2

    print("=" * 78)
    print(f"DATA_ROWS GATE DIAGNOSTIC — org_id={org_id}")
    print("=" * 78)

    # ── 1. Org identity ─────────────────────────────────────────────────────
    print("\n[1] Org identity")
    print(f"    name                  = {org.get('name')!r}")
    print(f"    commercial_plan_slug  = {org.get('commercial_plan_slug')!r}")
    print(f"    plan (legacy field)   = {org.get('plan')!r}")
    print(f"    billing_status        = {org.get('billing_status')!r}")
    print(f"    is_active             = {org.get('is_active')}")
    print(f"    has_used_trial        = {org.get('has_used_trial', False)}")

    # ── 2. ALL module subscriptions for cashflow_monitor ────────────────────
    print("\n[2] Module subscriptions for cashflow_monitor (ALL statuses)")
    cursor = module_subscriptions_collection.find(
        {"organization_id": org_id, "module_key": "cashflow_monitor"},
    ).sort("created_at", -1)
    subs = await cursor.to_list(50)
    if not subs:
        print("    (none)")
    else:
        for sub in subs:
            plan = await pricing_plans_collection.find_one(
                {"id": sub.get("pricing_plan_id")},
            )
            plan_slug = (plan or {}).get("slug") or "<missing pricing_plan>"
            data_rows_limit = (plan or {}).get("limits", {}).get("data_rows", "?")
            print(
                f"    [{sub.get('status'):>10}] "
                f"sub_id={sub.get('id')[:12]}... "
                f"plan_slug={plan_slug!r:30} "
                f"data_rows_limit={_fmt_limit(data_rows_limit)} "
                f"updated_at={sub.get('updated_at')}"
            )

    # ── 3. Effective limit (what the gate uses right now) ───────────────────
    print("\n[3] Effective limit (gate's source of truth)")
    entitlements = await get_module_entitlements(org_id, "cashflow_monitor", org_doc=org)
    base_limit = entitlements.get("limits", {}).get("data_rows", 0)
    print(f"    base_plan_limit       = {_fmt_limit(base_limit)}")
    print(f"    plan_slug used        = {entitlements.get('plan_slug')!r}")
    print(f"    enabled               = {entitlements.get('enabled')}")
    print(f"    read_only             = {entitlements.get('read_only')}")

    effective_limit = await get_effective_limit(org_id, "cashflow_monitor", "data_rows")
    print(f"    effective_limit       = {_fmt_limit(effective_limit)}  ← THE GATE COMPARES AGAINST THIS")

    # ── 4. Active addons (none expected for data_rows currently) ────────────
    print("\n[4] Active addons")
    addons = await billing_repository.list_active_addons_for_org(org_id)
    if not addons:
        print("    (none)")
    else:
        for a in addons:
            plan = await billing_repository.get_commercial_plan(a.get("addon_slug", ""))
            cf_provides = ((plan or {}).get("addon_provides") or {}).get("cashflow_monitor") or {}
            print(
                f"    {a.get('addon_slug')!r} qty={a.get('quantity')} "
                f"status={a.get('status')!r} "
                f"data_rows_provides={cf_provides.get('data_rows', 0)}"
            )

    # ── 5. Current usage as the gate sees it ────────────────────────────────
    print("\n[5] Current usage (what count_usage returns — gate's source)")
    period_start, period_end = get_current_period_range()
    usage_via_gate = await count_usage(
        org_id, "cashflow_monitor", "data_rows", period_start, period_end,
    )
    print(f"    period                = {period_start} → {period_end}")
    print(f"    usage_via_gate        = {usage_via_gate}  (sums quantity in ai_usage_events)")

    # ── 6. Actual collection counts (independent reality check) ─────────────
    print("\n[6] Actual cashflow row counts in Mongo (this calendar month)")
    month_start_iso = datetime.now(timezone.utc).replace(
        day=1, hour=0, minute=0, second=0, microsecond=0,
    ).isoformat()
    sales_count = await sales_records_collection.count_documents({
        "organization_id": org_id, "created_at": {"$gte": month_start_iso},
    })
    expenses_count = await expense_records_collection.count_documents({
        "organization_id": org_id, "created_at": {"$gte": month_start_iso},
    })
    purchases_count = await purchase_records_collection.count_documents({
        "organization_id": org_id, "created_at": {"$gte": month_start_iso},
    })
    fixed_count = await fixed_costs_collection.count_documents({
        "organization_id": org_id, "created_at": {"$gte": month_start_iso},
    })
    actual_total = sales_count + expenses_count + purchases_count + fixed_count
    print(f"    sales_records         = {sales_count}")
    print(f"    expense_records       = {expenses_count}")
    print(f"    purchase_records      = {purchases_count}")
    print(f"    fixed_costs           = {fixed_count}")
    print(f"    TOTAL (this month)    = {actual_total}")

    # ── 7. Verdict ──────────────────────────────────────────────────────────
    print("\n[7] Verdict")
    drift = False
    expected_for_free = 200
    expected_for_starter = 1000

    if effective_limit == -1:
        # Unlimited — gate will never block. Verify this matches the plan.
        cps = (org.get("commercial_plan_slug") or "").lower()
        if cps in ("free", "starter"):
            print(f"    ❌ DRIFT — commercial_plan_slug={cps!r} should NOT have unlimited data_rows.")
            print(f"       Effective_limit is -1 because of an active module_subscription:")
            for sub in subs:
                if sub.get("status") == "active":
                    plan = await pricing_plans_collection.find_one({"id": sub.get("pricing_plan_id")})
                    print(f"         · sub_id={sub.get('id')} plan={plan.get('slug') if plan else '?'}")
            print(f"       This stale subscription bypasses the gate entirely.")
            print(f"       FIX: deprovision/cancel the stale module_subscription, OR run")
            print(f"            python -m scripts.audit_billing_consistency --fix --org-id {org_id}")
            drift = True
        else:
            print(f"    ✅ Plan {cps!r} legitimately has unlimited data_rows. Gate will pass.")
    elif effective_limit > 0:
        cps = (org.get("commercial_plan_slug") or "").lower()
        expected = {"free": 200, "starter": 1000}.get(cps)
        if expected and effective_limit != expected:
            print(f"    ❌ DRIFT — plan {cps!r} should have data_rows={expected}, "
                  f"got {effective_limit}.")
            drift = True
        else:
            print(f"    ✅ Effective limit {effective_limit} matches plan {cps!r}.")
        # Usage check
        if usage_via_gate >= effective_limit:
            print(f"    ⛔ Gate WILL BLOCK next insert (usage={usage_via_gate} >= limit={effective_limit}).")
        else:
            print(f"    ✅ Gate WILL ALLOW next insert (usage={usage_via_gate} < limit={effective_limit}).")
        # Counter-vs-reality drift
        if abs(actual_total - usage_via_gate) > 5:
            print(f"    ⚠️  COUNTER DRIFT — actual rows this month={actual_total} vs gate counter={usage_via_gate}.")
            print(f"       The gate will ENFORCE based on usage_via_gate, NOT the actual count.")
            print(f"       Likely cause: rows created via a path that bypassed record_module_usage")
            print(f"       (legacy data, manual DB insert, or a bypass that's now closed but left history).")
            drift = True
    else:
        # 0 — gate will block immediately
        print(f"    ⛔ Effective limit is 0. Gate will block ALL inserts.")

    print("\n" + ("=" * 78))
    return 1 if drift else 0


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--org-id", help="Organization id (UUID)")
    parser.add_argument("--slug", help="Organization public_slug")
    parser.add_argument("--email", help="A user's email belonging to the org")
    args = parser.parse_args()

    async def _run():
        org_id = await _resolve_org_id(args)
        return await _diagnose(org_id)

    rc = asyncio.run(_run())
    sys.exit(rc)


if __name__ == "__main__":
    main()
