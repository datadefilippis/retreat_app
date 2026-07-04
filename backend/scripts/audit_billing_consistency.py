#!/usr/bin/env python3
"""
audit_billing_consistency.py
============================
Scan all organizations for billing/subscription inconsistencies.

Run from the backend/ directory:

    cd backend

    # Dry-run (default) — report only, no mutations
    python -m scripts.audit_billing_consistency

    # Fix a single org
    python -m scripts.audit_billing_consistency --fix --org-id <ORG_ID>

    # Fix ALL inconsistent orgs (requires explicit --all flag)
    python -m scripts.audit_billing_consistency --fix --all

Checks performed per org:
  - Missing commercial_plan_slug field  (HIGH)
  - No active module_subscriptions      (MEDIUM)
  - Subscription/plan mismatch          (HIGH)
  - Orphaned paid subs on free org      (HIGH)

Fix action:
  Calls provision_commercial_plan(org_id, effective_plan_slug, assigned_by="audit:system")
  which cancels stale subs and creates fresh ones matching the plan catalog.
  Idempotent and reversible (cancelled subs remain in DB as historical records).
"""

import argparse
import asyncio
import sys
from pathlib import Path

# ── Add backend/ to sys.path so we can import project modules ────────────────
_BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_BACKEND_DIR))

from database import (  # noqa: E402
    organizations_collection,
    module_subscriptions_collection,
    commercial_plans_collection,
    pricing_plans_collection,
)


# ── Severity labels ──────────────────────────────────────────────────────────

class Severity:
    OK = "OK"
    INFO = "INFO"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


# Billing statuses managed by Stripe — never overwrite these blindly.
STRIPE_MANAGED_STATUSES = frozenset({"active", "trialing", "past_due"})


# ── Core audit logic ─────────────────────────────────────────────────────────

async def load_commercial_plans() -> dict:
    """Load all commercial plans → {slug: plan_doc}."""
    plans = {}
    async for doc in commercial_plans_collection.find({}, {"_id": 0}):
        plans[doc["slug"]] = doc
    return plans


async def load_pricing_plans() -> dict:
    """Load all pricing plans → {id: plan_doc}."""
    plans = {}
    async for doc in pricing_plans_collection.find({}, {"_id": 0}):
        plans[doc["id"]] = doc
    return plans


async def load_pricing_plans_by_slug() -> dict:
    """Load all pricing plans → {(module_key, slug): plan_doc}."""
    plans = {}
    async for doc in pricing_plans_collection.find({}, {"_id": 0}):
        key = (doc["module_key"], doc["slug"])
        plans[key] = doc
    return plans


async def get_active_subs(org_id: str) -> list:
    """Get all active module subscriptions for an org."""
    cursor = module_subscriptions_collection.find(
        {"organization_id": org_id, "status": "active"},
        {"_id": 0},
    )
    return await cursor.to_list(100)


async def audit_org(
    org: dict,
    commercial_plans: dict,
    pricing_plans_by_id: dict,
    pricing_plans_by_slug: dict,
) -> dict:
    """Audit a single organization. Returns a findings dict."""
    org_id = org["id"]
    org_name = org.get("name", "?")
    commercial_slug = org.get("commercial_plan_slug")
    legacy_plan = org.get("plan", "free")

    billing_status = org.get("billing_status", "none")
    has_stripe_sub = bool(org.get("stripe_subscription_id"))
    stripe_managed = has_stripe_sub or billing_status in STRIPE_MANAGED_STATUSES

    findings = {
        "org_id": org_id,
        "org_name": org_name,
        "commercial_plan_slug": commercial_slug,
        "legacy_plan": legacy_plan,
        "billing_status": billing_status,
        "has_stripe_sub": has_stripe_sub,
        "stripe_managed": stripe_managed,
        "issues": [],
        "consistent": True,
        "effective_slug": None,  # what we'd provision to
    }

    # Determine effective plan slug
    effective_slug = commercial_slug or legacy_plan or "free"
    # If the effective slug is not in the catalog, fall back to free
    if effective_slug not in commercial_plans:
        effective_slug = "free"
    findings["effective_slug"] = effective_slug

    # Check 1: Missing commercial_plan_slug
    if not commercial_slug:
        findings["issues"].append({
            "severity": Severity.HIGH,
            "message": f"commercial_plan_slug: MISSING (legacy plan=\"{legacy_plan}\")",
        })
        findings["consistent"] = False

    # Load active subs
    active_subs = await get_active_subs(org_id)
    findings["active_sub_count"] = len(active_subs)

    # Check 2: No active module_subscriptions
    if len(active_subs) == 0 and commercial_slug:
        findings["issues"].append({
            "severity": Severity.MEDIUM,
            "message": f"No active module_subscriptions (commercial_plan_slug=\"{commercial_slug}\")",
        })
        findings["consistent"] = False

    if len(active_subs) == 0 and not commercial_slug:
        findings["issues"].append({
            "severity": Severity.MEDIUM,
            "message": "No active module_subscriptions and no commercial_plan_slug",
        })
        findings["consistent"] = False

    # Load expected module_plans from the commercial plan catalog
    plan_doc = commercial_plans.get(effective_slug, {})
    expected_module_plans = plan_doc.get("module_plans", {})

    # Build a map of actual active subs: module_key → sub doc
    actual_subs_by_module = {}
    for sub in active_subs:
        mk = sub.get("module_key")
        if mk:
            actual_subs_by_module[mk] = sub

    if active_subs:
        # Check 3: Compare active subs against expected plan
        for expected_mk, expected_pp_slug in expected_module_plans.items():
            actual_sub = actual_subs_by_module.get(expected_mk)
            if not actual_sub:
                findings["issues"].append({
                    "severity": Severity.MEDIUM,
                    "message": f"Missing sub for {expected_mk} (expected {expected_pp_slug})",
                })
                findings["consistent"] = False
                continue

            # Resolve the actual pricing plan
            actual_pp_id = actual_sub.get("pricing_plan_id")
            actual_pp = pricing_plans_by_id.get(actual_pp_id, {})
            actual_pp_slug = actual_pp.get("slug", "?")

            if actual_pp_slug != expected_pp_slug:
                actual_price = actual_pp.get("price_monthly", "?")
                expected_pp = pricing_plans_by_slug.get(
                    (expected_mk, expected_pp_slug), {}
                )
                expected_price = expected_pp.get("price_monthly", "?")

                # Is this an orphaned paid sub on a free org?
                if effective_slug == "free" and actual_price and actual_price > 0:
                    findings["issues"].append({
                        "severity": Severity.HIGH,
                        "message": (
                            f"Orphaned paid sub: {expected_mk} → {actual_pp_slug} "
                            f"(€{actual_price}/mo) — expected {expected_pp_slug} "
                            f"(€{expected_price}/mo)"
                        ),
                    })
                else:
                    findings["issues"].append({
                        "severity": Severity.HIGH,
                        "message": (
                            f"Sub mismatch: {expected_mk} → {actual_pp_slug} "
                            f"(expected {expected_pp_slug})"
                        ),
                    })
                findings["consistent"] = False
            else:
                findings["issues"].append({
                    "severity": Severity.INFO,
                    "message": f"OK: {expected_mk} → {actual_pp_slug}",
                })

        # Check for extra subs not in the expected plan
        for mk, sub in actual_subs_by_module.items():
            if mk not in expected_module_plans:
                pp = pricing_plans_by_id.get(sub.get("pricing_plan_id"), {})
                findings["issues"].append({
                    "severity": Severity.MEDIUM,
                    "message": (
                        f"Extra sub not in plan: {mk} → {pp.get('slug', '?')} "
                        f"(€{pp.get('price_monthly', '?')}/mo)"
                    ),
                })
                findings["consistent"] = False

    # Compute fix description
    if not findings["consistent"]:
        cancel_count = len(active_subs)
        create_count = len(expected_module_plans)
        if stripe_managed:
            findings["fix_description"] = (
                f"⚠ STRIPE-MANAGED — cannot auto-fix. Use admin Stripe reconcile endpoint.\n"
                f"       POST /admin/organizations/{org_id}/billing/reconcile?apply=true"
            )
        else:
            findings["fix_description"] = (
                f"provision_commercial_plan(\"{effective_slug}\", assigned_by=\"audit:system\")\n"
                f"       → would cancel {cancel_count} active subs, create {create_count} {effective_slug}-tier subs"
            )

    return findings


async def fix_org(org_id: str, effective_slug: str, stripe_managed: bool = False) -> dict:
    """Apply canonical provisioning to fix an org.

    Stripe-managed orgs are REFUSED — use the Stripe reconcile endpoint
    (POST /admin/organizations/{id}/billing/reconcile?apply=true) instead,
    which reads the live Stripe state and provisions accordingly.
    """
    if stripe_managed:
        raise RuntimeError(
            f"Org {org_id} has an active Stripe subscription or Stripe-managed "
            f"billing status. Cannot safely reprovision via audit script — use "
            f"the admin Stripe reconcile endpoint instead."
        )

    from services.plan_provisioning import provision_commercial_plan
    return await provision_commercial_plan(
        org_id=org_id,
        plan_slug=effective_slug,
        assigned_by="audit:system",
        billing_status="none" if effective_slug == "free" else "manual",
    )


# ── Report formatting ────────────────────────────────────────────────────────

SEVERITY_MARKERS = {
    Severity.OK: "\033[32m[OK]\033[0m",       # green
    Severity.INFO: "\033[36m[INFO]\033[0m",    # cyan
    Severity.MEDIUM: "\033[33m[MEDIUM]\033[0m",  # yellow
    Severity.HIGH: "\033[31m[HIGH]\033[0m",    # red
}


def print_report(all_findings: list) -> None:
    """Pretty-print the audit report."""
    consistent_count = sum(1 for f in all_findings if f["consistent"])
    inconsistent_count = len(all_findings) - consistent_count

    print()
    print("=" * 60)
    print("  Billing Consistency Audit")
    print("=" * 60)
    print(f"  Scanned: {len(all_findings)} organizations")
    print(f"  Consistent: {consistent_count}  |  Inconsistent: {inconsistent_count}")
    print("=" * 60)

    for f in all_findings:
        org_id_short = f["org_id"][:12] + "..."
        status = "\033[32m[OK]\033[0m" if f["consistent"] else "\033[31m[INCONSISTENT]\033[0m"
        print(f"\n--- Org: {f['org_name']} ({org_id_short}) {status} ---")

        if f["consistent"] and not any(
            i["severity"] not in (Severity.OK, Severity.INFO) for i in f["issues"]
        ):
            slug = f["commercial_plan_slug"] or "?"
            print(f"  commercial_plan_slug=\"{slug}\", {f['active_sub_count']} active subs match plan")
            continue

        for issue in f["issues"]:
            marker = SEVERITY_MARKERS.get(issue["severity"], f"[{issue['severity']}]")
            print(f"  {marker} {issue['message']}")

        if "fix_description" in f:
            print(f"  Fix: {f['fix_description']}")

    print()


# ── Main ─────────────────────────────────────────────────────────────────────

async def main(args: argparse.Namespace) -> int:
    """Run the audit and optionally apply fixes."""
    # Load reference data
    commercial_plans = await load_commercial_plans()
    if not commercial_plans:
        print("ERROR: No commercial plans found in db.commercial_plans.")
        print("       Run the backend server at least once to seed the catalog.")
        return 1

    pricing_plans_by_id = await load_pricing_plans()
    pricing_plans_by_slug = await load_pricing_plans_by_slug()

    # Load all orgs
    orgs = []
    async for doc in organizations_collection.find({}, {"_id": 0}).sort("created_at", 1):
        orgs.append(doc)

    if not orgs:
        print("No organizations found.")
        return 0

    # Audit each org
    all_findings = []
    for org in orgs:
        findings = await audit_org(org, commercial_plans, pricing_plans_by_id, pricing_plans_by_slug)
        all_findings.append(findings)

    # Print report
    print_report(all_findings)

    # Identify inconsistent orgs
    inconsistent = [f for f in all_findings if not f["consistent"]]

    if not inconsistent:
        print("All organizations are consistent. Nothing to fix.")
        return 0

    # Fix mode
    if not args.fix:
        print("Run with --fix --org-id <ID> or --fix --all to apply corrections.")
        return 0

    # Determine target orgs
    targets = []
    if args.org_id:
        target = next((f for f in inconsistent if f["org_id"] == args.org_id), None)
        if not target:
            # Check if it exists but is consistent
            found = next((f for f in all_findings if f["org_id"] == args.org_id), None)
            if found and found["consistent"]:
                print(f"Org {args.org_id} is already consistent. Nothing to fix.")
                return 0
            print(f"ERROR: Org ID '{args.org_id}' not found or not inconsistent.")
            return 1
        targets = [target]
    elif args.all:
        targets = inconsistent
    else:
        print("ERROR: --fix requires either --org-id <ID> or --all.")
        return 1

    # Filter out Stripe-managed orgs (they need the admin reconcile endpoint)
    stripe_skipped = [t for t in targets if t.get("stripe_managed")]
    fixable = [t for t in targets if not t.get("stripe_managed")]

    if stripe_skipped:
        print(f"\n⚠ Skipping {len(stripe_skipped)} Stripe-managed org(s) — use admin reconcile endpoint:")
        for t in stripe_skipped:
            print(f"  - {t['org_name']} ({t['org_id'][:12]}...) billing_status={t.get('billing_status')}")

    if not fixable:
        print("\nNo fixable (non-Stripe) orgs. Nothing to do.")
        return 0

    # Confirmation prompt for --all (safety against accidental batch runs)
    if args.all and len(fixable) > 1 and sys.stdin.isatty():
        answer = input(
            f"\nAbout to reprovision {len(fixable)} organization(s). Continue? [y/N] "
        )
        if answer.strip().lower() not in ("y", "yes"):
            print("Aborted.")
            return 0

    # Apply fixes
    print(f"\nApplying fixes to {len(fixable)} organization(s)...\n")
    for t in fixable:
        org_id = t["org_id"]
        effective_slug = t["effective_slug"]
        print(f"  Fixing: {t['org_name']} ({org_id[:12]}...) → provision \"{effective_slug}\"")
        try:
            result = await fix_org(org_id, effective_slug, stripe_managed=t.get("stripe_managed", False))
            print(f"    ✓ Cancelled {result['cancelled']} subs, created {len(result['created'])} subs")
            for sub in result["created"]:
                print(f"      + {sub['module_key']} → {sub['plan_slug']}")
        except Exception as e:
            print(f"    ✗ ERROR: {e}")

    # Re-audit to confirm
    print("\n--- Post-fix verification ---")
    post_findings = []
    for t in fixable:
        org_doc = await organizations_collection.find_one(
            {"id": t["org_id"]}, {"_id": 0}
        )
        if org_doc:
            pf = await audit_org(
                org_doc, commercial_plans, pricing_plans_by_id, pricing_plans_by_slug,
            )
            post_findings.append(pf)
            status = "\033[32mCONSISTENT\033[0m" if pf["consistent"] else "\033[31mSTILL INCONSISTENT\033[0m"
            print(f"  {pf['org_name']}: {status}")

    still_broken = sum(1 for pf in post_findings if not pf["consistent"])
    if still_broken:
        print(f"\nWARNING: {still_broken} org(s) still inconsistent after fix.")
        return 1

    print("\nAll targeted orgs are now consistent.")
    return 0


def cli() -> None:
    parser = argparse.ArgumentParser(
        description="Audit billing consistency across all organizations.",
    )
    parser.add_argument(
        "--fix",
        action="store_true",
        help="Apply corrections (requires --org-id or --all).",
    )
    parser.add_argument(
        "--org-id",
        type=str,
        default=None,
        help="Fix only this org (use with --fix).",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Fix ALL inconsistent orgs (use with --fix).",
    )
    args = parser.parse_args()

    if args.fix and not args.org_id and not args.all:
        parser.error("--fix requires either --org-id <ID> or --all")

    exit_code = asyncio.run(main(args))
    sys.exit(exit_code)


if __name__ == "__main__":
    cli()
