"""Seed initial pricing plans into the database.

Called once at startup.  Idempotent: skips if plans already exist for a module.

Each module defines its own feature_keys in the `limits` dict:
  - ai_assistant: "chat", "digest", "alert_analysis", "health_explanation"
  - cashflow_monitor: "analytics", "data_rows", "export", "email_alerts", "email_digest", "alert_config"
  - product_catalog: "analytics", "products"
  - customers_light: "analytics"
  - commerce_signals: "analytics"
  - commerce: "analytics", "orders_monthly", "stores_max", "checkout_stripe"   (Onda 1)

These feature_keys are NOT global concepts — they are scoped to the module
that defines them.  The module_access service treats them opaquely.

Limit values:
  -1 = unlimited (access granted, no counting)
   0 = feature disabled
  >0 = monthly quota (usage metering)
"""

import logging
from typing import Dict, List

from models.pricing_plan import PricingPlan
from repositories import subscription_repository

logger = logging.getLogger(__name__)


# ── Seed definitions ────────────────────────────────────────────────────────
# Each entry maps to a PricingPlan document.
# Prices are placeholder — admin can modify them later via admin endpoints.

AI_ASSISTANT_PLANS: List[dict] = [
    {
        "module_key": "ai_assistant",
        "slug": "ai_assistant_free",
        "name": "Free",
        "price_monthly": 0.0,
        "currency": "EUR",
        "limits": {
            # Feature keys specific to ai_assistant module:
            #   "chat"               — chat messages per month
            #   "digest"             — digest generations per month
            #   "alert_analysis"     — AI root-cause analysis on alerts (-1 = access flag)
            #   "health_explanation" — AI health-score explanation (-1 = access flag)
            "chat": 3,        # 3 AI chats/month (taste the value)
            "digest": 0,
            "alert_analysis": 0,
            "health_explanation": 0,
        },
        "sort_order": 0,
    },
    {
        "module_key": "ai_assistant",
        "slug": "ai_assistant_starter_lite",
        "name": "AI Starter Lite",
        "price_monthly": 19.0,
        "currency": "EUR",
        "limits": {
            "chat": 20,       # 20 AI chats/month (~5/week)
            "digest": 0,
            "alert_analysis": 0,
            "health_explanation": 0,
        },
        "sort_order": 1,
    },
    {
        "module_key": "ai_assistant",
        "slug": "ai_assistant_starter",
        "name": "AI Starter",
        "price_monthly": 29.0,
        "currency": "EUR",
        "limits": {
            "chat": 80,       # 80 AI chats/month (~3-4/day)
            "digest": 4,
            "alert_analysis": -1,
            "health_explanation": -1,
        },
        "sort_order": 2,
    },
    {
        "module_key": "ai_assistant",
        "slug": "ai_assistant_pro",
        "name": "AI Business",
        "price_monthly": 79.0,
        "currency": "EUR",
        "limits": {
            "chat": 200,      # 200 AI chats/month (~7/day)
            "digest": -1,
            "alert_analysis": -1,
            "health_explanation": -1,
        },
        "sort_order": 3,
    },
    {
        "module_key": "ai_assistant",
        "slug": "ai_assistant_enterprise",
        "name": "AI Enterprise",
        "price_monthly": 199.0,
        "currency": "EUR",
        "limits": {
            # -1 means unlimited
            "chat": -1,
            "digest": -1,
            "alert_analysis": -1,
            "health_explanation": -1,
        },
        "sort_order": 4,
    },
]


# ── Cashflow Monitor plans ─────────────────────────────────────────────────
# Cashflow uses a mix of access gating and usage metering:
#   -1 = access granted (no counting)
#    0 = feature not available
#   >0 = monthly quota (usage metering)
#
# "data_rows" is usage-metered: free tier gets 100 rows/month, pro unlimited.

CASHFLOW_MONITOR_PLANS: List[dict] = [
    {
        "module_key": "cashflow_monitor",
        "slug": "cashflow_monitor_free",
        "name": "Free",
        "price_monthly": 0.0,
        "currency": "EUR",
        "limits": {
            # Feature keys specific to cashflow_monitor module:
            #   "analytics"     — KPIs, charts, categories, forecast, health, aging
            #   "data_rows"     — monthly row insertion quota
            #   "export"        — report export as CSV/PDF
            #   "email_alerts"  — email notification for HIGH severity alerts
            #   "email_digest"  — weekly digest email
            #   "alert_config"  — configure alert thresholds/presets
            "analytics": -1,      # all current features, unlimited
            "data_rows": 200,     # 200 rows/month free (upgraded from 100)
            "export": 0,          # not available in free tier
            "email_alerts": 0,    # no email alerts in free tier
            "email_digest": 0,    # no digest email in free tier
            "alert_config": 0,    # no threshold config in free tier
        },
        "sort_order": 0,
    },
    {
        "module_key": "cashflow_monitor",
        "slug": "cashflow_monitor_starter",
        "name": "Cashflow Starter",
        "price_monthly": 19.0,
        "currency": "EUR",
        "limits": {
            "analytics": -1,
            "data_rows": 1000,    # 1000 rows/month
            "export": -1,         # unlocked
            "email_alerts": -1,   # email alerts enabled
            "email_digest": -1,   # digest email enabled (KPI-only, no AI)
            "alert_config": -1,   # threshold config enabled
        },
        "sort_order": 1,
    },
    {
        "module_key": "cashflow_monitor",
        "slug": "cashflow_monitor_pro",
        "name": "Cashflow Pro",
        "price_monthly": 29.0,
        "currency": "EUR",
        "limits": {
            "analytics": -1,
            "data_rows": -1,      # unlimited
            "export": -1,         # unlocked
            "email_alerts": -1,   # email alerts enabled
            "email_digest": -1,   # digest email enabled (AI report)
            "alert_config": -1,   # threshold config enabled
        },
        "sort_order": 2,
    },
]


# ── Customers Light plans ─────────────────────────────────────────────────
# Feature keys:
#   "analytics" — customer intelligence, segments, concentration (-1 = access flag)

# Wave 7A (2026-05): commerce_signals module removed from the platform.
# COMMERCE_SIGNALS_PLANS dict and its _seed_module_plans call deleted.


PRODUCT_CATALOG_PLANS: List[dict] = [
    {
        # v5.8 / Onda 9.N — "Disabled" tier: zero everything. Used by Free
        # and Solo plans (cashflow-only positioning post-Onda 9.N rebrand).
        # The frontend hides the products UI entirely when analytics=0.
        # Catalog is conceptually paired with commerce; without commerce,
        # there's no use case for managing products. Splitting the tiers
        # explicitly (vs reusing product_catalog_free with limit=0) keeps
        # admin UI / migration tracking clear.
        "module_key": "product_catalog",
        "slug": "product_catalog_disabled",
        "name": "Catalog Disabled",
        "price_monthly": 0.0,
        "currency": "EUR",
        "limits": {
            "analytics": 0,   # hide product UI entirely
            "products": 0,    # zero products allowed
        },
        "sort_order": 0,  # ranks before product_catalog_free in lists
    },
    {
        "module_key": "product_catalog",
        "slug": "product_catalog_free",
        "name": "Free",
        "price_monthly": 0.0,
        "currency": "EUR",
        "limits": {
            "analytics": -1,  # all product analytics, unlimited
            "products": 50,   # max 50 products in catalog
        },
        "sort_order": 1,
    },
    {
        "module_key": "product_catalog",
        "slug": "product_catalog_starter",
        "name": "Product Starter",
        "price_monthly": 19.0,
        "currency": "EUR",
        "limits": {
            "analytics": -1,
            "products": 200,
        },
        "sort_order": 2,
    },
    {
        "module_key": "product_catalog",
        "slug": "product_catalog_pro",
        "name": "Product Pro",
        "price_monthly": 39.0,
        "currency": "EUR",
        "limits": {
            "analytics": -1,
            "products": -1,  # unlimited
        },
        "sort_order": 3,
    },
]


# ── Commerce module plans ─────────────────────────────────────────────────
# v5.8 / Onda 1 — extended from a single `commerce_free` to 5 tiers that
# back the new commercial plans (Free, Solo, Commerce Starter, Commerce Pro,
# Custom). Each tier expresses 4 feature_keys:
#
#   "analytics"        — module gate. -1 = module visible & usable, 0 = hidden.
#                        `commerce_disabled` uses 0 so the "Solo" plan
#                        (cashflow-only customers) can hide the storefront UI
#                        entirely without losing the module subscription record.
#
#   "orders_monthly"   — quota of storefront orders per month. -1 = unlimited.
#                        Soft-enforced (Onda 4): when reached, a UI paywall
#                        invites the merchant to upgrade or buy an add-on.
#                        Email transactional sends are NEVER blocked even when
#                        the orders quota is exceeded.
#
#   "stores_max"       — number of stores publishable. -1 = unlimited.
#                        Hard-enforced at store creation time (Onda 4).
#                        Add-on `addon_extra_store` (Onda 3) extends this.
#
#   "checkout_stripe"  — flag: -1 = Stripe Connect checkout enabled,
#                        0 = orders go through "richiesta contatto" (a
#                        non-paying contact request emailed to the merchant).
#                        Onda 4 wires the storefront UI + order_request flow
#                        to honor this flag.
#
# ADDITIVE migration: `migrate_pricing_plans()` (defined below) adds the new
# keys to the existing `commerce_free` row WITHOUT overwriting `analytics=-1`.
# `ensure_pricing_plans_exist()` inserts the 4 new slugs if missing.
# Existing orgs with module_subscriptions pointing at `commerce_free` keep
# working unchanged — they just gain 3 new keys in their effective limits.

COMMERCE_PLANS: List[dict] = [
    {
        "module_key": "commerce",
        "slug": "commerce_free",
        "name": "Commerce Free",
        "price_monthly": 0.0,
        "currency": "EUR",
        "limits": {
            "analytics": -1,           # module visible
            "orders_monthly": 30,      # 30 contact-requests/month (no Stripe)
            "stores_max": 1,           # 1 store
            "checkout_stripe": 0,      # NO Stripe Connect — contact_request flow
        },
        "sort_order": 0,
    },
    {
        # Used by "Solo" commercial plan (cashflow_monitor only, no storefront).
        # The `analytics=0` setting is what tells the UI to hide the commerce
        # nav entry entirely. ModuleSubscription record still exists so the
        # admin can upgrade later without losing history.
        "module_key": "commerce",
        "slug": "commerce_disabled",
        "name": "Commerce Disabled",
        "price_monthly": 0.0,
        "currency": "EUR",
        "limits": {
            "analytics": 0,
            "orders_monthly": 0,
            "stores_max": 0,
            "checkout_stripe": 0,
        },
        "sort_order": 1,
    },
    {
        # Used by "Commerce Starter" commercial plan (€39/mo).
        # Real ecommerce: Stripe Connect on, 200 orders/month, 1 store.
        "module_key": "commerce",
        "slug": "commerce_starter",
        "name": "Commerce Starter",
        "price_monthly": 0.0,          # priced via the commercial plan bundle
        "currency": "EUR",
        "limits": {
            "analytics": -1,
            "orders_monthly": 200,
            "stores_max": 1,
            "checkout_stripe": -1,
        },
        "sort_order": 2,
    },
    {
        # Used by "Commerce Pro" commercial plan (€89/mo).
        # Multi-store + higher orders quota.
        "module_key": "commerce",
        "slug": "commerce_pro",
        "name": "Commerce Pro",
        "price_monthly": 0.0,
        "currency": "EUR",
        "limits": {
            "analytics": -1,
            "orders_monthly": 1000,
            "stores_max": 3,
            "checkout_stripe": -1,
        },
        "sort_order": 3,
    },
    {
        # Used by "Custom" commercial plan (system_admin assigns ad-hoc).
        # Unlimited everything; system_admin can override per-org via Onda 8
        # CustomPricingPlan flow.
        "module_key": "commerce",
        "slug": "commerce_unlimited",
        "name": "Commerce Unlimited",
        "price_monthly": 0.0,
        "currency": "EUR",
        "limits": {
            "analytics": -1,
            "orders_monthly": -1,
            "stores_max": -1,
            "checkout_stripe": -1,
        },
        "sort_order": 4,
    },
]


CUSTOMERS_LIGHT_PLANS: List[dict] = [
    {
        "module_key": "customers_light",
        "slug": "customers_light_free",
        "name": "Free",
        "price_monthly": 0.0,
        "currency": "EUR",
        "limits": {
            "analytics": -1,  # all customer analytics, unlimited
        },
        "sort_order": 0,
    },
    {
        "module_key": "customers_light",
        "slug": "customers_light_pro",
        "name": "Customers Pro",
        "price_monthly": 19.0,
        "currency": "EUR",
        "limits": {
            "analytics": -1,
        },
        "sort_order": 1,
    },
]


# ── Target limits for migration ────────────────────────────────────────────
# Maps slug -> (module_key, target_limits). Used by migrate_pricing_plans()
# to update existing plans in DB to match current seed definitions.

_TARGET_LIMITS: Dict[str, tuple] = {
    p["slug"]: (p["module_key"], p["limits"])
    for p in AI_ASSISTANT_PLANS + CASHFLOW_MONITOR_PLANS + PRODUCT_CATALOG_PLANS + COMMERCE_PLANS + CUSTOMERS_LIGHT_PLANS
}


async def seed_pricing_plans_if_empty() -> None:
    """Seed pricing plans for all modules.  Idempotent per module_key.

    For each module, checks if plans already exist.  If not, inserts the
    full set of seed plans.  Safe to call on every startup.
    """
    await _seed_module_plans("ai_assistant", AI_ASSISTANT_PLANS)
    await _seed_module_plans("cashflow_monitor", CASHFLOW_MONITOR_PLANS)
    await _seed_module_plans("product_catalog", PRODUCT_CATALOG_PLANS)
    await _seed_module_plans("commerce", COMMERCE_PLANS)
    await _seed_module_plans("customers_light", CUSTOMERS_LIGHT_PLANS)
    # Wave 7A (2026-05): commerce_signals removed from platform.


async def _seed_module_plans(module_key: str, plans: List[dict]) -> None:
    """Seed plans for a single module.  Skips if any plans already exist."""
    count = await subscription_repository.count_plans_by_module(module_key)
    if count > 0:
        logger.info(
            "Pricing plans for '%s' already exist (%d plans) — skipping seed.",
            module_key, count,
        )
        return

    logger.info("Seeding %d pricing plans for module '%s'...", len(plans), module_key)

    for plan_data in plans:
        plan = PricingPlan(**plan_data)
        doc = plan.model_dump()
        doc["created_at"] = doc["created_at"].isoformat()
        doc["updated_at"] = doc["updated_at"].isoformat()
        await subscription_repository.insert_pricing_plan(doc)

    logger.info("Seeded %d pricing plans for '%s'.", len(plans), module_key)


async def migrate_pricing_plans() -> None:
    """Migrate existing pricing plan limits — ADDITIVE ONLY.

    Phase 2a hardening: this migration only ADDS missing limit keys.
    It never overwrites existing limit values.  This protects admin edits
    made via the catalog UI (e.g. changing chat limit from 50 to 100).

    Use case: when a new feature_key is added to a module (e.g. "digest"
    is added to ai_assistant), this migration ensures existing plans get
    the new key with its seed-defined default value.

    Idempotent: no-op if all keys already present.  Safe on every startup.
    """
    updated = 0
    for slug, (module_key, target_limits) in _TARGET_LIMITS.items():
        plan = await subscription_repository.get_pricing_plan_by_slug(
            module_key=module_key,
            slug=slug,
        )
        if plan is None:
            # Plan doesn't exist yet — will be created by seed
            continue

        current_limits = plan.get("limits", {})

        # Compute additive diff: only keys present in target but missing in current
        missing_keys = {
            k: v for k, v in target_limits.items()
            if k not in current_limits
        }

        if not missing_keys:
            continue

        # Merge: existing values preserved, missing keys added
        merged_limits = {**current_limits, **missing_keys}

        did_update = await subscription_repository.update_plan_limits_by_slug(
            slug, merged_limits,
        )
        if did_update:
            updated += 1
            logger.info(
                "Migrated plan '%s': added keys %s (existing values preserved)",
                slug, list(missing_keys.keys()),
            )

    if updated > 0:
        logger.info("Migrated limits on %d pricing plans (additive only).", updated)
    else:
        logger.info("Pricing plan limits already up to date — no migration needed.")


async def ensure_pricing_plans_exist() -> None:
    """Insert any seed-defined PricingPlans that are missing from the DB.

    Unlike seed_pricing_plans_if_empty() which skips an entire module if
    ANY plans exist, this function checks each individual slug and inserts
    only the missing ones.  Safe and idempotent on every startup.

    Needed because adding a new PricingPlan (e.g. cashflow_monitor_starter)
    to an existing module won't be picked up by the module-level seed.
    """
    # v5.8 / Onda 1 fix: COMMERCE_PLANS was previously missing from this list,
    # which meant the 5 new `commerce_*` plans (commerce_disabled, _starter,
    # _pro, _unlimited) introduced in Onda 1 would never be auto-inserted on
    # startup. Adding it here is the prerequisite for the new plans rollout.
    all_plans = (
        AI_ASSISTANT_PLANS + CASHFLOW_MONITOR_PLANS
        + PRODUCT_CATALOG_PLANS + COMMERCE_PLANS
        + CUSTOMERS_LIGHT_PLANS
    )
    inserted = 0
    for plan_data in all_plans:
        slug = plan_data["slug"]
        module_key = plan_data["module_key"]
        existing = await subscription_repository.get_pricing_plan_by_slug(
            module_key=module_key, slug=slug,
        )
        if existing is not None:
            continue

        plan = PricingPlan(**plan_data)
        doc = plan.model_dump()
        doc["created_at"] = doc["created_at"].isoformat()
        doc["updated_at"] = doc["updated_at"].isoformat()
        await subscription_repository.insert_pricing_plan(doc)
        inserted += 1
        logger.info("ensure_pricing: inserted missing plan '%s'", slug)

    if inserted > 0:
        logger.info("ensure_pricing: inserted %d missing pricing plans.", inserted)
    else:
        logger.info("ensure_pricing: all pricing plans already exist.")


async def migrate_plan_redesign_v1() -> None:
    """One-time migration for plan redesign v1.

    Changes that cannot be propagated by the existing additive-only migration:
    - Upgrade Free data_rows from 100 to 200
    - Hide Enterprise from public catalog
    - Update sort_orders for commercial plans
    - Update Free features_display

    Idempotent: checks a flag in the migrations collection.
    """
    from database import db

    migrations = db["migrations"]
    flag = await migrations.find_one({"_id": "plan_redesign_v1"})
    if flag:
        logger.info("migrate_plan_redesign_v1: already applied — skipping.")
        return

    logger.info("migrate_plan_redesign_v1: applying...")

    # 1. Upgrade Free cashflow_monitor data_rows 100 → 200 (safe: upgrade only)
    result = await db["pricing_plans"].update_one(
        {"slug": "cashflow_monitor_free", "limits.data_rows": 100},
        {"$set": {"limits.data_rows": 200}},
    )
    if result.modified_count:
        logger.info("  - Updated cashflow_monitor_free data_rows: 100 → 200")

    # 2. Hide Enterprise from public catalog
    result = await db["commercial_plans"].update_one(
        {"slug": "enterprise"},
        {"$set": {"is_public": False}},
    )
    if result.modified_count:
        logger.info("  - Set enterprise is_public=false")

    # 3. Update sort_orders (Starter=1 is set by seed insert)
    for slug, order in [("free", 0), ("starter", 1), ("core", 2), ("pro", 3), ("enterprise", 4)]:
        await db["commercial_plans"].update_one(
            {"slug": slug},
            {"$set": {"sort_order": order}},
        )

    # 4. Update Free features_display
    await db["commercial_plans"].update_one(
        {"slug": "free"},
        {"$set": {"features_display": [
            "billing.features.cashflow_basic",
            "billing.features.data_rows_200",
            "billing.features.basic_analytics",
            "billing.features.ai_chat_3",
        ]}},
    )

    # 5. Mark migration as applied
    await migrations.insert_one({"_id": "plan_redesign_v1", "applied_at": "auto"})
    logger.info("migrate_plan_redesign_v1: done.")


async def migrate_trial_only_core() -> None:
    """One-time migration: trial only on Core plan.

    Starter and Pro: trial_days set to 0.
    Core: keeps trial_days=14.
    """
    from database import db

    migrations = db["migrations"]
    flag = await migrations.find_one({"_id": "trial_only_core"})
    if flag:
        logger.info("migrate_trial_only_core: already applied — skipping.")
        return

    logger.info("migrate_trial_only_core: applying...")

    for slug, days in [("starter", 0), ("pro", 0)]:
        result = await db["commercial_plans"].update_one(
            {"slug": slug},
            {"$set": {"trial_days": days}},
        )
        if result.modified_count:
            logger.info("  - Set %s trial_days=%d", slug, days)

    await migrations.insert_one({"_id": "trial_only_core", "applied_at": "auto"})
    logger.info("migrate_trial_only_core: done.")


async def migrate_plan_limits_v2() -> None:
    """One-time migration: update AI chat limits and add starter_lite.

    - ai_assistant_free: chat 0→3
    - ai_assistant_starter: chat 50→80
    - ai_assistant_pro: chat 300→200
    - Insert ai_assistant_starter_lite (via ensure_pricing_plans_exist)
    - Update Starter commercial plan module_plans
    - Update features_display for all 4 public plans
    """
    from database import db

    migrations = db["migrations"]
    flag = await migrations.find_one({"_id": "plan_limits_v2"})
    if flag:
        logger.info("migrate_plan_limits_v2: already applied — skipping.")
        return

    logger.info("migrate_plan_limits_v2: applying...")

    # 1. Update AI limits
    for slug, chat_val in [
        ("ai_assistant_free", 3),
        ("ai_assistant_starter", 80),
        ("ai_assistant_pro", 200),
    ]:
        result = await db["pricing_plans"].update_one(
            {"slug": slug},
            {"$set": {"limits.chat": chat_val}},
        )
        if result.modified_count:
            logger.info("  - %s chat → %d", slug, chat_val)

    # 2. Insert ai_assistant_starter_lite (handled by ensure_pricing_plans_exist)
    # Just need to make sure it runs before this migration

    # 3. Update Starter commercial plan: ai_assistant mapping
    await db["commercial_plans"].update_one(
        {"slug": "starter"},
        {"$set": {"module_plans.ai_assistant": "ai_assistant_starter_lite"}},
    )
    logger.info("  - Starter ai_assistant → ai_assistant_starter_lite")

    # 4. Update features_display for all plans
    await db["commercial_plans"].update_one(
        {"slug": "free"},
        {"$set": {"features_display": [
            "billing.features.cashflow_basic",
            "billing.features.data_rows_200",
            "billing.features.basic_analytics",
            "billing.features.ai_chat_3",
        ]}},
    )
    await db["commercial_plans"].update_one(
        {"slug": "starter"},
        {"$set": {"features_display": [
            "billing.features.cashflow_full",
            "billing.features.data_rows_1000",
            "billing.features.ai_chat_20",
            "billing.features.email_alerts",
            "billing.features.email_digest_kpi",
            "billing.features.alert_config",
            "billing.features.export",
            "billing.features.team_2",
        ]}},
    )
    await db["commercial_plans"].update_one(
        {"slug": "core"},
        {"$set": {"features_display": [
            "billing.features.cashflow_full",
            "billing.features.data_rows_unlimited",
            "billing.features.ai_chat_80",
            "billing.features.ai_digest_4",
            "billing.features.ai_alerts",
            "billing.features.email_alerts",
            "billing.features.email_digest_ai",
            "billing.features.alert_config",
            "billing.features.export",
            "billing.features.team_5",
            "billing.features.email_support",
        ]}},
    )
    await db["commercial_plans"].update_one(
        {"slug": "pro"},
        {"$set": {"features_display": [
            "billing.features.everything_in_core",
            "billing.features.data_rows_unlimited",
            "billing.features.ai_chat_200",
            "billing.features.ai_digest_unlimited",
            "billing.features.ai_alerts",
            "billing.features.ai_health",
            "billing.features.team_15",
            "billing.features.priority_support",
        ]}},
    )
    logger.info("  - Updated features_display for all 4 plans")

    await migrations.insert_one({"_id": "plan_limits_v2", "applied_at": "auto"})
    logger.info("migrate_plan_limits_v2: done.")


async def migrate_plan_relaunch_v5() -> None:
    """One-time migration for the v5.8 plan relaunch (Onda 5).

    Two atomic concerns, executed in sequence:

      A) Rebrand the 5 commercial_plan rows in place. Slugs unchanged.
         Touches:
           · `name`           Free / Solo / Commerce Starter / Commerce Pro / Custom
           · `description`, `tagline` — short copy refreshed
           · `module_plans["commerce"]` — point at the new commerce_*
             PricingPlan slugs introduced in Onda 1
           · `sort_order` — re-aligned (free=0, starter=1, core=2, pro=3, ent=4)
           · `is_public` — Custom plan flipped to false (system_admin only)
         Prices, trial_days, features_display, Stripe IDs are NOT touched
         here — they remain admin-editable through the Catalog UI / endpoint
         and through the seed's $setOnInsert path for fresh installs.

      B) Lock every existing org with an active Stripe subscription onto
         their current price (the "grandfather" guarantee). For each org
         where `stripe_subscription_id` is set:
           · `legacy_pricing_lock = True`
           · `legacy_pricing_locked_at = now`
           · `legacy_price_ids = {plan_slug: stripe_price_id_from_sub}`
              read from Stripe live so the snapshot survives any future
              CommercialPlan reseed.
         Best-effort on the Stripe call — a network blip during the
         snapshot still flips the lock so the customer is protected;
         `legacy_price_ids` may be left None and the existing Stripe
         subscription_item keeps its current price (Stripe.modify with
         no price change is the natural fallback).

    Idempotent: checks the `plan_relaunch_v5` flag in the migrations
    collection. Re-running is a no-op.
    """
    from database import db

    migrations = db["migrations"]
    flag = await migrations.find_one({"_id": "plan_relaunch_v5"})
    if flag:
        logger.info("migrate_plan_relaunch_v5: already applied — skipping.")
        return

    logger.info("migrate_plan_relaunch_v5: applying...")

    # ────────────────────────────────────────────────────────────────────
    # A) Rebrand the 5 commercial_plan rows
    # ────────────────────────────────────────────────────────────────────

    REBRAND = [
        {
            "slug": "free",
            "name": "Free",
            "description": "Inizia gratis con le funzionalita' base.",
            "tagline": "Sandbox utile, sempre gratis",
            "sort_order": 0,
            "is_public": True,
            "is_self_serve": False,
            "commerce": "commerce_free",
        },
        {
            "slug": "starter",
            "name": "Solo",
            "description": "Solo cashflow, senza ecommerce.",
            "tagline": "Per chi vuole capire i flussi (no shop)",
            "sort_order": 1,
            "is_public": True,
            "is_self_serve": True,
            "commerce": "commerce_disabled",
        },
        {
            "slug": "core",
            "name": "Commerce Starter",
            "description": "Cashflow completo + storefront con Stripe Connect.",
            "tagline": "Per chi vende online ed esce dalla sandbox",
            "sort_order": 2,
            "is_public": True,
            "is_self_serve": True,
            "commerce": "commerce_starter",
        },
        {
            "slug": "pro",
            "name": "Commerce Pro",
            "description": "Multi-store + AI illimitata + AI digest unlimited.",
            "tagline": "Per chi scala su piu' canali",
            "sort_order": 3,
            "is_public": True,
            "is_self_serve": True,
            "commerce": "commerce_pro",
        },
        {
            "slug": "enterprise",
            "name": "Custom",
            "description": "Configurazione su misura — system_admin only.",
            "tagline": "Casi speciali / partner / consulenti",
            "sort_order": 4,
            "is_public": False,           # hidden from public pricing page
            "is_self_serve": False,
            "commerce": "commerce_unlimited",
        },
    ]

    for spec in REBRAND:
        slug = spec["slug"]
        update_doc = {
            "name": spec["name"],
            "description": spec["description"],
            "tagline": spec["tagline"],
            "sort_order": spec["sort_order"],
            "is_public": spec["is_public"],
            "is_self_serve": spec["is_self_serve"],
            "module_plans.commerce": spec["commerce"],
        }
        result = await db["commercial_plans"].update_one(
            {"slug": slug},
            {"$set": update_doc},
        )
        if result.modified_count:
            logger.info(
                "  - rebranded '%s' → name='%s' commerce='%s'",
                slug, spec["name"], spec["commerce"],
            )

    # ────────────────────────────────────────────────────────────────────
    # B) Grandfather lock — snapshot legacy Stripe price_ids per org
    # ────────────────────────────────────────────────────────────────────

    locked_count = 0
    snapshotted_count = 0
    no_snapshot_count = 0

    cursor = db["organizations"].find(
        {
            "stripe_subscription_id": {"$ne": None, "$exists": True},
            "legacy_pricing_lock": {"$ne": True},
        },
        {"_id": 0, "id": 1, "stripe_subscription_id": 1, "commercial_plan_slug": 1},
    )

    # Lazy-import Stripe so this migration runs even on backends without
    # `stripe` installed (e.g. a worker DB-only role). Errors are
    # downgraded to "lock without snapshot" — never block the migration.
    stripe_module = None
    try:
        from services import stripe_service
        stripe_module = stripe_service._get_stripe()
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "migrate_plan_relaunch_v5: Stripe SDK unavailable (%s) — "
            "orgs will be locked WITHOUT legacy_price_ids snapshot.",
            exc,
        )

    import asyncio
    from datetime import datetime, timezone

    async for org in cursor:
        org_id = org["id"]
        sub_id = org["stripe_subscription_id"]
        slug = org.get("commercial_plan_slug")

        legacy_price_ids = None
        if stripe_module is not None and sub_id:
            try:
                sub = await asyncio.to_thread(
                    stripe_module.Subscription.retrieve, sub_id,
                )
                items = (sub.get("items") or {}).get("data") or []
                # Only snapshot the MAIN plan's price (no add-on items —
                # Onda 3 add-on items are tracked in their own collection).
                main_price_id = None
                for it in items:
                    md = (it or {}).get("metadata") or {}
                    if md.get("is_addon") == "true":
                        continue
                    main_price_id = (it.get("price") or {}).get("id")
                    if main_price_id:
                        break
                if main_price_id and slug:
                    legacy_price_ids = {slug: main_price_id}
                    snapshotted_count += 1
                else:
                    no_snapshot_count += 1
            except Exception as exc:  # noqa: BLE001
                logger.warning(
                    "migrate_plan_relaunch_v5: org=%s Stripe sub fetch failed: %s "
                    "— locking WITHOUT snapshot.",
                    org_id, exc,
                )
                no_snapshot_count += 1
        else:
            no_snapshot_count += 1

        await db["organizations"].update_one(
            {"id": org_id},
            {"$set": {
                "legacy_pricing_lock": True,
                "legacy_pricing_locked_at": datetime.now(timezone.utc).isoformat(),
                "legacy_price_ids": legacy_price_ids,
            }},
        )
        locked_count += 1

    logger.info(
        "migrate_plan_relaunch_v5: locked %d orgs (%d with legacy_price_ids snapshot, %d without).",
        locked_count, snapshotted_count, no_snapshot_count,
    )

    # ────────────────────────────────────────────────────────────────────
    # Mark migration applied
    # ────────────────────────────────────────────────────────────────────
    from datetime import datetime, timezone as _tz
    await migrations.insert_one({
        "_id": "plan_relaunch_v5",
        "applied_at": datetime.now(_tz.utc).isoformat(),
        "rebranded_plans": [s["slug"] for s in REBRAND],
        "locked_orgs": locked_count,
        "snapshotted_legacy_price_ids": snapshotted_count,
    })
    logger.info("migrate_plan_relaunch_v5: done.")
